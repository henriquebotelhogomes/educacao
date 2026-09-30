"""Runnable, content-redacted Marco 3.5 Ragas evaluation."""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys
import tempfile
import time
from collections import Counter
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol, cast

from evals.benchmark.chunking import CanonicalChunkTokenizer, chunk_pages
from evals.benchmark.corpus import CachedCorpusExtractor
from evals.benchmark.embeddings import SentenceTransformerAdapter
from evals.benchmark.hashing import sha256_file
from evals.benchmark.publishability import assess_publishability
from evals.benchmark.registry import CANDIDATES
from evals.benchmark.retrieval import BenchmarkChunk, InMemoryCosineIndex
from evals.benchmark.runner import assess_embedding_inputs, load_golden_items
from evals.rag_triad import (
    RagTriadCase,
    RagTriadSummary,
    evaluate_rag_triad,
    require_eval_credentials,
)
from evals.schema import GoldenItem, ItemType

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_DATASET = REPO_ROOT / "evals" / "datasets" / "v1" / "golden.jsonl"
DEFAULT_MANIFEST = REPO_ROOT / "evals" / "datasets" / "v1" / "manifest.json"
DEFAULT_LOCK = REPO_ROOT / "evals" / "datasets" / "v1" / "lock.json"
DEFAULT_OUTPUT = REPO_ROOT / "evals" / "reports" / "rag-triad-v1.json"
DEFAULT_MARKDOWN = REPO_ROOT / "evals" / "reports" / "rag-triad-v1.md"
DEFAULT_CACHE = REPO_ROOT / "evals" / ".cache" / "rag-triad"
DEFAULT_CHECKPOINT = DEFAULT_CACHE / "responses-v1.jsonl"
MODEL_NAME = "llama-3.3-70b-versatile"
SCHEMA_VERSION = "marco-3.5-rag-triad-v1"
RAGAS_CONTENT_REDACTION = "ADR-014: no source text, contexts, prompts, identities, answers, or keys"
DEFAULT_MAX_RATE_LIMIT_WAIT_SECONDS = 3600.0
DEFAULT_RAGAS_BATCH_SIZE = 1
MAX_STRATIFIED_CACHED_SAMPLE_SIZE = 4
PROVISIONAL_CACHED_SAMPLE_NOTICE = (
    "PROVISIONAL only: limited to four cached cases, one per available document under "
    "the 100k TPD quota; cannot ratify ADR-009."
)


class SearchIndex(Protocol):
    def search(self, query_vector: Any, *, top_k: int = 10) -> list[Any]: ...


class PrefixAwareE5Embeddings:
    """Adapt a LangChain embedder to the E5 query/passage contract."""

    def __init__(self, embeddings: Any) -> None:
        self._embeddings = embeddings

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embeddings.embed_documents(
            [text if text.startswith("passage: ") else f"passage: {text}" for text in texts]
        )

    def embed_query(self, text: str) -> list[float]:
        prepared = text if text.startswith("query: ") else f"query: {text}"
        return self._embeddings.embed_query(prepared)


@dataclass(frozen=True)
class RunnerConfig:
    dataset_path: pathlib.Path
    manifest_path: pathlib.Path
    lock_path: pathlib.Path
    output_path: pathlib.Path
    markdown_path: pathlib.Path
    cache_dir: pathlib.Path
    max_items: int | None = None
    publish: bool = False
    device: str | None = "cpu"
    offline: bool = False
    checkpoint_path: pathlib.Path = DEFAULT_CHECKPOINT
    max_rate_limit_wait_seconds: float = DEFAULT_MAX_RATE_LIMIT_WAIT_SECONDS
    stratified_cached_sample_size: int | None = None
    ragas_batch_size: int = DEFAULT_RAGAS_BATCH_SIZE
    judge_model: str = MODEL_NAME


@dataclass
class RagTriadRunnerDependencies:
    """Inject provider boundaries so tests never call external services."""

    assess_publishability: Callable[..., Any] = assess_publishability
    load_items: Callable[[pathlib.Path], list[GoldenItem]] = load_golden_items
    load_corpus: Callable[[pathlib.Path], Any] | None = None
    chunk_pages: Callable[..., Any] = chunk_pages
    embedder_factory: Callable[[], Any] | None = None
    index_factory: Callable[[list[BenchmarkChunk], Any], SearchIndex] = InMemoryCosineIndex
    generate: Callable[[str], str] | None = None
    generation_factory: Callable[[Any, str], Callable[[str], str]] | None = None
    judge_factory: Callable[[Any, str], tuple[object, object]] | None = None
    evaluate: Callable[..., RagTriadSummary] = evaluate_rag_triad
    langfuse_client_factory: Callable[[Any], Any] | None = None
    langfuse_auth_check: Callable[[Any], bool] | None = None
    langfuse_record: Callable[[dict[str, object], dict[str, float]], None] | None = None
    ragas_version: Callable[[], str] | None = None
    sleep: Callable[[float], None] = time.sleep


def _prompt(question: str, contexts: list[str]) -> str:
    evidence = "\n\n".join(f"[Trecho {index}] {text}" for index, text in enumerate(contexts, 1))
    return (
        "Você é uma assistente educacional. Responda em português do Brasil. "
        "Responda somente com base nos trechos fornecidos. Se os trechos não forem "
        "suficientes, diga explicitamente que não há informação suficiente.\n\n"
        f"Trechos:\n{evidence}\n\nPergunta: {question}\nResposta:"
    )


def _load_checkpoint(checkpoint_path: pathlib.Path) -> dict[str, str]:
    if not checkpoint_path.exists():
        return {}
    responses: dict[str, str] = {}
    for line_number, line in enumerate(checkpoint_path.read_text(encoding="utf-8").splitlines(), 1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"invalid checkpoint JSON at line {line_number}: {checkpoint_path}"
            ) from exc
        if (
            not isinstance(row, dict)
            or set(row) != {"item_id", "response"}
            or not isinstance(row["item_id"], str)
            or not row["item_id"]
            or not isinstance(row["response"], str)
            or not row["response"].strip()
        ):
            raise ValueError(f"invalid checkpoint row at line {line_number}: {checkpoint_path}")
        item_id = row["item_id"]
        response = row["response"]
        previous = responses.get(item_id)
        if previous is not None and previous != response:
            raise ValueError(
                f"conflicting checkpoint responses for item {item_id}: {checkpoint_path}"
            )
        responses[item_id] = response
    return responses


def select_stratified_cached_items(
    items: list[GoldenItem],
    *,
    checkpoint_responses: Mapping[str, str],
    requested_count: int,
) -> list[GoldenItem]:
    """Select cached eligible items by least-used document, type, difficulty, then ID.

    Each greedy pick minimizes the already selected count for its logical document,
    then item type, then difficulty; its stable item ID breaks remaining ties. This
    deterministically maximizes broad document coverage before balancing the two
    eligible types and the three difficulty levels. Only non-empty checkpointed
    responses qualify, so callers make no generation requests.
    """
    if requested_count < 1:
        raise ValueError("--stratified-cached-sample-size must be at least 1")
    # This is deliberately capped at one case per available document under the
    # 100k TPD quota. It is a provisional safety sample, never ADR-009 evidence.
    if requested_count > MAX_STRATIFIED_CACHED_SAMPLE_SIZE:
        raise ValueError(
            "--stratified-cached-sample-size has a maximum of 4 cases for "
            "the provisional 100k TPD safety sample"
        )
    eligible = [
        item
        for item in items
        if item.tipo in {ItemType.ANSWERABLE, ItemType.AMBIGUOUS_PARTIAL}
        and bool(checkpoint_responses.get(item.id, "").strip())
    ]
    if len(eligible) < requested_count:
        raise ValueError(
            "stratified cached sample requested "
            f"{requested_count}, but checkpoint has only {len(eligible)} "
            "suitable checkpointed responses"
        )

    selected: list[GoldenItem] = []
    document_counts: Counter[str] = Counter()
    type_counts: Counter[ItemType] = Counter()
    difficulty_counts: Counter[str] = Counter()
    remaining = sorted(eligible, key=lambda item: item.id)
    while len(selected) < requested_count:
        item = min(
            remaining,
            key=lambda candidate: (
                document_counts[candidate.documento],
                type_counts[candidate.tipo],
                difficulty_counts[candidate.dificuldade.value],
                candidate.id,
            ),
        )
        selected.append(item)
        remaining.remove(item)
        document_counts[item.documento] += 1
        type_counts[item.tipo] += 1
        difficulty_counts[item.dificuldade.value] += 1
    return selected


def _stratum_summary(items: list[GoldenItem]) -> dict[str, object]:
    """Return aggregate-only strata, deliberately omitting document names and item IDs."""
    return {
        "document_count": len({item.documento for item in items}),
        "item_types": dict(sorted(Counter(item.tipo.value for item in items).items())),
        "difficulties": dict(sorted(Counter(item.dificuldade.value for item in items).items())),
    }


def _write_checkpoint(checkpoint_path: pathlib.Path, responses: Mapping[str, str]) -> None:
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=checkpoint_path.parent,
        prefix=f".{checkpoint_path.name}.",
        suffix=".tmp",
        delete=False,
    ) as temporary:
        temporary.write(
            "".join(
                json.dumps({"item_id": item_id, "response": response}, ensure_ascii=False) + "\n"
                for item_id, response in sorted(responses.items())
            )
        )
        temporary_path = pathlib.Path(temporary.name)
    try:
        os.replace(temporary_path, checkpoint_path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _is_rate_limited(exc: Exception) -> bool:
    response = getattr(exc, "response", None)
    return getattr(exc, "status_code", None) == 429 or getattr(response, "status_code", None) == 429


def _seconds_from_hint(value: object) -> float | None:
    if isinstance(value, (int, float)) and value >= 0:
        return float(value)
    if not isinstance(value, str):
        return None
    match = re.fullmatch(
        r"\s*(\d+(?:\.\d+)?)\s*(seconds?|minutes?|hours?|s|m|h)?\s*", value.lower()
    )
    if not match:
        return None
    amount = float(match.group(1))
    unit = match.group(2) or "s"
    multiplier = 3600 if unit.startswith("h") else 60 if unit.startswith("m") else 1
    return amount * multiplier


def _retry_after_seconds(exc: Exception) -> float | None:
    response = getattr(exc, "response", None)
    for source in (exc, response):
        if source is None:
            continue
        parsed = _seconds_from_hint(getattr(source, "retry_after", None))
        if parsed is not None:
            return parsed
        headers = getattr(source, "headers", None)
        if isinstance(headers, Mapping):
            for key, value in headers.items():
                if str(key).lower() == "retry-after":
                    parsed = _seconds_from_hint(value)
                    if parsed is not None:
                        return parsed
    match = re.search(
        r"(?:retry|try again).*?(\d+(?:\.\d+)?)\s*(seconds?|minutes?|hours?|s|m|h)\b",
        str(exc),
        flags=re.IGNORECASE,
    )
    return _seconds_from_hint(" ".join(match.groups())) if match else None


def _generate_with_rate_limit_retry(
    generate: Callable[[str], str],
    prompt: str,
    *,
    checkpoint_path: pathlib.Path,
    max_wait_seconds: float,
    sleep: Callable[[float], None],
) -> str:
    waited = 0.0
    attempt = 0
    while True:
        try:
            return generate(prompt)
        except Exception as exc:
            if not _is_rate_limited(exc):
                raise
            delay = _retry_after_seconds(exc)
            if delay is None:
                delay = min(60.0, 2.0**attempt)
            if waited + delay > max_wait_seconds:
                raise RuntimeError(
                    "Groq rate limit could not be recovered within "
                    f"{max_wait_seconds:g}s. Successful responses are checkpointed at "
                    f"{checkpoint_path}. Resume with: uv run python -m evals.rag_triad_runner "
                    f"--checkpoint {checkpoint_path}"
                ) from exc
            sleep(delay)
            waited += delay
            attempt += 1


def build_cases(
    items: list[GoldenItem],
    *,
    index: SearchIndex,
    embedder: Any,
    generate: Callable[[str], str],
    checkpoint_path: pathlib.Path | None = None,
    max_rate_limit_wait_seconds: float = DEFAULT_MAX_RATE_LIMIT_WAIT_SECONDS,
    sleep: Callable[[float], None] = time.sleep,
) -> list[RagTriadCase]:
    """Generate Ragas cases from only answerable benchmark items."""
    checkpoint = _load_checkpoint(checkpoint_path) if checkpoint_path is not None else {}
    eligible = [
        item for item in items if item.tipo in {ItemType.ANSWERABLE, ItemType.AMBIGUOUS_PARTIAL}
    ]
    cases: list[RagTriadCase] = []
    for item in eligible:
        hits = index.search(embedder.embed_queries([item.pergunta])[0], top_k=5)
        contexts = [str(hit.chunk.text) for hit in hits]
        if not contexts:
            raise RuntimeError(f"retrieval produced no contexts for item {item.id}")
        response = checkpoint.get(item.id)
        if response is None:
            response = _generate_with_rate_limit_retry(
                generate,
                _prompt(item.pergunta, contexts),
                checkpoint_path=checkpoint_path or DEFAULT_CHECKPOINT,
                max_wait_seconds=max_rate_limit_wait_seconds,
                sleep=sleep,
            )
            checkpoint[item.id] = response
            if checkpoint_path is not None:
                _write_checkpoint(checkpoint_path, checkpoint)
        reference = item.resposta_referencia
        if reference is None:
            raise RuntimeError(f"eligible item {item.id} has no reference")
        cases.append(
            RagTriadCase(
                item_id=item.id,
                user_input=item.pergunta,
                retrieved_contexts=contexts,
                response=response,
                reference=reference,
            )
        )
    if not cases:
        raise RuntimeError("frozen dataset contains no answerable Ragas items")
    return cases


def _default_corpus_loader(config: RunnerConfig) -> Any:
    return CachedCorpusExtractor(
        repo_root=REPO_ROOT,
        cache_dir=config.cache_dir,
    ).load_manifest(config.manifest_path)


def _default_embedder(config: RunnerConfig) -> SentenceTransformerAdapter:
    return SentenceTransformerAdapter(
        CANDIDATES["e5-small"],
        device=config.device,
        offline=config.offline,
    )


def _response_text(response: Any) -> str:
    content = getattr(response, "content", response)
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("ChatGroq returned an empty response")
    return content


def _default_generation(credentials: Any, generation_model: str) -> Callable[[str], str]:
    chat: Any
    if getattr(credentials, "openrouter_api_key", None):
        from langchain_openai import ChatOpenAI

        chat = ChatOpenAI(
            model=generation_model,
            temperature=0,
            api_key=credentials.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
        )
    else:
        from langchain_groq import ChatGroq

        chat = ChatGroq(
            model=generation_model,
            temperature=0,
            api_key=credentials.groq_api_key,
        )

    def generate(prompt: str) -> str:
        return _response_text(chat.invoke(prompt))

    return generate


def _cached_sample_generation(prompt: str) -> str:
    del prompt
    raise RuntimeError("cached sample must not generate responses")


def _default_judges(credentials: Any, judge_model: str) -> tuple[object, object]:
    from langchain_huggingface import HuggingFaceEmbeddings
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from ragas.llms import LangchainLLMWrapper

    chat: Any
    if getattr(credentials, "openrouter_api_key", None):
        from langchain_openai import ChatOpenAI

        chat = ChatOpenAI(
            model=judge_model,
            temperature=0,
            api_key=credentials.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
        )
    else:
        from langchain_groq import ChatGroq

        chat = ChatGroq(
            model=judge_model,
            temperature=0,
            api_key=credentials.groq_api_key,
        )
    judge_embeddings = PrefixAwareE5Embeddings(
        HuggingFaceEmbeddings(
            model_name=CANDIDATES["e5-small"].model_name,
            encode_kwargs={"normalize_embeddings": True},
        )
    )

    return LangchainLLMWrapper(chat), LangchainEmbeddingsWrapper(judge_embeddings)


def _default_langfuse_client(credentials: Any) -> Any:
    from langfuse import Langfuse

    return Langfuse(
        public_key=credentials.langfuse_public_key,
        secret_key=credentials.langfuse_secret_key,
    )


def _default_langfuse_auth_check(client: Any) -> bool:
    return bool(client.auth_check())


def _default_langfuse_record(client: Any) -> Callable[[dict[str, object], dict[str, float]], None]:
    """Record only aggregate, ADR-014-safe metadata and scores."""

    def record(metadata: dict[str, object], scores: dict[str, float]) -> None:
        try:
            span = client.start_span(name="marco-3.5-rag-triad", metadata=metadata)
            for name, value in scores.items():
                span.score_trace(name=name, value=value)
            span.end()
            client.flush()
        except Exception as exc:
            raise RuntimeError("Langfuse safe metadata/score recording failed") from exc

    return record


def _ragas_version() -> str:
    import ragas

    return str(getattr(ragas, "__version__", "unknown"))


def _result(
    config: RunnerConfig,
    *,
    manifest: Mapping[str, object],
    corpus_hash: str,
    summary: RagTriadSummary,
    publishability: Any,
    ragas_version: str,
    sample_metadata: Mapping[str, object] | None = None,
) -> dict[str, object]:
    result: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dataset": {
            "version": manifest.get("version"),
            "dataset_sha256": sha256_file(config.dataset_path),
            "manifest_sha256": sha256_file(config.manifest_path),
            "lock_sha256": sha256_file(config.lock_path),
            "corpus_sha256": corpus_hash,
        },
        "embedding": {
            "alias": "e5-small",
            "model_name": CANDIDATES["e5-small"].model_name,
            "chunking_version": "structural-v1-t512-o64",
        },
        "generation_model": MODEL_NAME,
        "judge_model": config.judge_model,
        "case_count": summary.item_count,
        "metrics": dict(summary.metrics),
        "ragas_version": ragas_version,
        "ragas_batch_size": config.ragas_batch_size,
        "publishability": "PROVISIONAL"
        if config.stratified_cached_sample_size is not None
        else publishability.label,
        "provisional": config.max_items is not None
        or config.stratified_cached_sample_size is not None,
        "content_redaction": RAGAS_CONTENT_REDACTION,
    }
    if sample_metadata is not None:
        result.update(sample_metadata)
    return result


def _write_outputs(
    result: Mapping[str, object],
    output_path: pathlib.Path,
    markdown_path: pathlib.Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    metrics = cast(Mapping[str, float], result["metrics"])
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(
        "\n".join(
            [
                "# Marco 3.5 RAG Triad",
                "",
                f"- Publishability: **{result['publishability']}**",
                f"- Cases: {result['case_count']}",
                *(
                    [
                        f"- Sample mode: {result['sample_mode']}",
                        "- Requested / selected: "
                        f"{result['requested_count']} / {result['selected_count']}",
                        f"- Strata: {json.dumps(result['stratum_summary'], sort_keys=True)}",
                        f"- Provisional scope: {result['provisional_scope']}",
                        f"- Judge scope: {result['judge_scope']}",
                    ]
                    if "sample_mode" in result
                    else []
                ),
                f"- Ragas: {result['ragas_version']}",
                f"- Cached answer generation model: {result['generation_model']}",
                f"- Ragas judge model: {result['judge_model']}",
                f"- Content redaction: {result['content_redaction']}",
                "",
                "| Metric | Mean |",
                "| --- | ---: |",
                *[f"| {name} | {value:.4f} |" for name, value in metrics.items()],
                "",
            ]
        ),
        encoding="utf-8",
    )


def run_evaluation(
    config: RunnerConfig,
    *,
    environment: Mapping[str, str] | None = None,
    dependencies: RagTriadRunnerDependencies | None = None,
) -> dict[str, object]:
    """Run a full frozen RAG evaluation; all default provider work is lazy."""
    if config.max_items is not None and config.max_items < 1:
        raise ValueError("--max-items must be at least 1")
    if (
        config.stratified_cached_sample_size is not None
        and config.stratified_cached_sample_size < 1
    ):
        raise ValueError("--stratified-cached-sample-size must be at least 1")
    if config.max_items is not None and config.stratified_cached_sample_size is not None:
        raise ValueError("--max-items cannot be combined with --stratified-cached-sample-size")
    if config.max_rate_limit_wait_seconds < 0:
        raise ValueError("--max-rate-limit-wait-seconds must not be negative")
    if config.ragas_batch_size < 1:
        raise ValueError("--ragas-batch-size must be at least 1")
    if not config.judge_model.strip():
        raise ValueError("--judge-model must be nonempty")
    if (
        config.max_items is not None or config.stratified_cached_sample_size is not None
    ) and config.publish:
        raise ValueError("--publish is refused when this run is PROVISIONAL")
    if config.publish and config.judge_model != MODEL_NAME:
        raise ValueError("--publish requires the judge model to match the generation model")
    env = environment if environment is not None else os.environ
    credentials = require_eval_credentials(
        groq_api_key=env.get("GROQ_API_KEY"),
        openrouter_api_key=env.get("OPENROUTER_API_KEY"),
        langfuse_public_key=env.get("LANGFUSE_PUBLIC_KEY"),
        langfuse_secret_key=env.get("LANGFUSE_SECRET_KEY"),
    )
    if not credentials.langfuse_enabled:
        raise ValueError("Langfuse configuration is required for this evaluation CLI")
    deps = dependencies or RagTriadRunnerDependencies()
    try:
        langfuse_client = (deps.langfuse_client_factory or _default_langfuse_client)(credentials)
        authenticated = (deps.langfuse_auth_check or _default_langfuse_auth_check)(langfuse_client)
    except Exception as exc:
        raise RuntimeError(
            "Langfuse authentication failed: check credentials and host configuration"
        ) from exc
    if not authenticated:
        raise RuntimeError(
            "Langfuse authentication failed: check credentials and host configuration"
        )
    publishability = deps.assess_publishability(
        dataset_path=config.dataset_path,
        manifest_path=config.manifest_path,
        lock_path=config.lock_path,
        repo_root=REPO_ROOT,
        # Smoke limits must not make a frozen corpus itself appear unfrozen.
        # They are represented explicitly as provisional in the output instead.
        max_items=None,
    )
    if not publishability.publishable:
        raise RuntimeError(
            "frozen dataset is not publishable: " + "; ".join(publishability.blocker_reasons)
        )
    manifest = json.loads(config.manifest_path.read_text(encoding="utf-8"))
    items = deps.load_items(config.dataset_path)
    if config.max_items is not None:
        items = items[: config.max_items]
    sample_metadata: dict[str, object] | None = None
    if config.stratified_cached_sample_size is not None:
        items = select_stratified_cached_items(
            items,
            checkpoint_responses=_load_checkpoint(config.checkpoint_path),
            requested_count=config.stratified_cached_sample_size,
        )
        sample_metadata = {
            "sample_mode": "stratified_cached",
            "requested_count": config.stratified_cached_sample_size,
            "selected_count": len(items),
            "stratum_summary": _stratum_summary(items),
            "provisional_scope": PROVISIONAL_CACHED_SAMPLE_NOTICE,
            "judge_scope": (
                "PROVISIONAL/non-ratifying: cached tutor answers were generated by "
                f"{MODEL_NAME} and judged by {config.judge_model}; "
                "this sample cannot ratify ADR-009."
            ),
        }
    corpus_loader = deps.load_corpus or (lambda path: _default_corpus_loader(config))
    corpus = corpus_loader(config.manifest_path)
    embedder = (deps.embedder_factory or (lambda: _default_embedder(config)))()
    chunked = deps.chunk_pages(
        corpus.pages,
        encode_fn=CanonicalChunkTokenizer().tokenize,
        chunk_size=512,
        overlap=64,
    )
    embedding_inputs = assess_embedding_inputs(
        chunks=chunked.chunks, embedder=embedder, candidate=CANDIDATES["e5-small"]
    )
    if not embedding_inputs.valid:
        raise RuntimeError("prepared passages are truncated; refusing Ragas evaluation")
    index = deps.index_factory(
        chunked.chunks, embedder.embed_passages([chunk.text for chunk in chunked.chunks])
    )
    generate: Callable[[str], str]
    if config.stratified_cached_sample_size is not None:
        generate = _cached_sample_generation
    elif deps.generate is not None:
        generate = deps.generate
    else:
        generate = (deps.generation_factory or _default_generation)(credentials, MODEL_NAME)

    if deps.judge_factory is not None:
        judge_llm, judge_embeddings = deps.judge_factory(credentials, config.judge_model)
    elif dependencies is not None and deps.generate is not None:
        # Test-injected generation avoids loading external Ragas providers.
        judge_llm = object()
        judge_embeddings = object()
    else:
        judge_llm, judge_embeddings = _default_judges(credentials, config.judge_model)
    cases = build_cases(
        items,
        index=index,
        embedder=embedder,
        generate=generate,
        checkpoint_path=config.checkpoint_path,
        max_rate_limit_wait_seconds=config.max_rate_limit_wait_seconds,
        sleep=deps.sleep,
    )
    summary = deps.evaluate(
        cases,
        llm=judge_llm,
        embeddings=judge_embeddings,
        batch_size=config.ragas_batch_size,
    )
    result = _result(
        config,
        manifest=manifest,
        corpus_hash=corpus.corpus_sha256,
        summary=summary,
        publishability=publishability,
        ragas_version=(deps.ragas_version or _ragas_version)(),
        sample_metadata=sample_metadata,
    )
    metadata = {
        "schema_version": SCHEMA_VERSION,
        "dataset_version": manifest.get("version"),
        "case_count": summary.item_count,
        "publishability": result["publishability"],
        "content_redaction": RAGAS_CONTENT_REDACTION,
        "ragas_batch_size": config.ragas_batch_size,
        "generation_model": MODEL_NAME,
        "judge_model": config.judge_model,
    }
    if sample_metadata is not None:
        metadata.update(sample_metadata)
    try:
        (deps.langfuse_record or _default_langfuse_record(langfuse_client))(
            metadata, summary.metrics
        )
    except Exception as exc:
        raise RuntimeError("Langfuse safe metadata/score recording failed") from exc
    _write_outputs(result, config.output_path, config.markdown_path)
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Marco 3.5 content-redacted Ragas/Langfuse evaluation"
    )
    parser.add_argument("--dataset", type=pathlib.Path, default=DEFAULT_DATASET)
    parser.add_argument("--manifest", type=pathlib.Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--lock", type=pathlib.Path, default=DEFAULT_LOCK)
    parser.add_argument("--output", type=pathlib.Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--markdown-output", type=pathlib.Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--cache-dir", type=pathlib.Path, default=DEFAULT_CACHE)
    parser.add_argument("--checkpoint", type=pathlib.Path, default=DEFAULT_CHECKPOINT)
    parser.add_argument(
        "--max-rate-limit-wait-seconds",
        type=float,
        default=DEFAULT_MAX_RATE_LIMIT_WAIT_SECONDS,
    )
    parser.add_argument("--max-items", type=int)
    parser.add_argument("--stratified-cached-sample-size", type=int)
    parser.add_argument(
        "--ragas-batch-size",
        type=int,
        default=DEFAULT_RAGAS_BATCH_SIZE,
        help="Ragas evaluation concurrency; defaults to 1 for provider quota safety",
    )
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--judge-model", default=MODEL_NAME)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--offline", action="store_true")
    return parser


def _load_runtime_environment() -> None:
    """Load local credentials only when the command is actually invoked."""
    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / ".env", override=False)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    config = RunnerConfig(
        args.dataset,
        args.manifest,
        args.lock,
        args.output,
        args.markdown_output,
        args.cache_dir,
        max_items=args.max_items,
        publish=args.publish,
        device=args.device,
        offline=args.offline,
        checkpoint_path=args.checkpoint,
        max_rate_limit_wait_seconds=args.max_rate_limit_wait_seconds,
        stratified_cached_sample_size=args.stratified_cached_sample_size,
        ragas_batch_size=args.ragas_batch_size,
        judge_model=args.judge_model,
    )
    try:
        _load_runtime_environment()
        run_evaluation(config)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"Wrote {config.output_path}")
    print(f"Wrote {config.markdown_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
