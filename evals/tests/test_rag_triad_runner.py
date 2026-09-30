from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import cast

import numpy as np
import pytest

import evals.rag_triad_runner as runner
from evals.benchmark.corpus import BenchmarkPage, ExtractedCorpus
from evals.benchmark.retrieval import BenchmarkChunk
from evals.rag_triad import RagTriadSummary
from evals.rag_triad_runner import (
    RAGAS_CONTENT_REDACTION,
    RagTriadRunnerDependencies,
    RunnerConfig,
    build_cases,
    run_evaluation,
)
from evals.schema import Difficulty, GoldenItem, ItemType, ReviewStatus


def _item(item_id: str, item_type: ItemType, reference: str | None) -> GoldenItem:
    return GoldenItem(
        id=item_id,
        pergunta="Qual é o conceito?",
        resposta_referencia=reference,
        documento="documento.pdf",
        paginas_esperadas=[] if item_type is ItemType.UNANSWERABLE else [1],
        evidence_quotes=[] if item_type is ItemType.UNANSWERABLE else ["conceito"],
        tipo=item_type,
        dificuldade=Difficulty.FACIL,
        review_status=ReviewStatus.APPROVED,
        notas="fora do corpus"
        if item_type is ItemType.UNANSWERABLE
        else ("parcial" if item_type is ItemType.AMBIGUOUS_PARTIAL else None),
    )


class FakeEmbedder:
    dimension = 2

    def tokenize(self, text: str) -> list[int]:
        return [1, 2]

    def prepare_passages(self, texts: list[str]) -> list[str]:
        return [f"passage: {text}" for text in texts]

    def embed_passages(self, texts: list[str]) -> np.ndarray:
        return np.array([[1.0, 0.0] for _ in texts], dtype=np.float32)

    def embed_queries(self, texts: list[str]) -> np.ndarray:
        return np.array([[1.0, 0.0] for _ in texts], dtype=np.float32)


def _false_auth_check(client: object) -> bool:
    del client
    return False


def _raising_auth_check(client: object) -> bool:
    del client
    raise ValueError("Invalid credentials. Confirm correct host.")


@pytest.mark.parametrize(
    "auth_check",
    [_false_auth_check, _raising_auth_check],
)
def test_run_evaluation_stops_before_expensive_work_when_langfuse_auth_is_unusable(
    tmp_path: Path,
    auth_check: Callable[[object], bool],
) -> None:
    output = tmp_path / "result.json"
    markdown = tmp_path / "result.md"
    expensive_work: list[str] = []

    def load_items(path: Path) -> list[GoldenItem]:
        del path
        expensive_work.append("items")
        return []

    def evaluate(cases: object, **kwargs: object) -> RagTriadSummary:
        del cases, kwargs
        expensive_work.append("evaluation")
        return RagTriadSummary(0, {}, provisional=False)

    dependencies = RagTriadRunnerDependencies(
        langfuse_client_factory=lambda credentials: object(),
        langfuse_auth_check=auth_check,
        assess_publishability=lambda **kwargs: expensive_work.append("publishability"),
        load_items=load_items,
        load_corpus=lambda path: expensive_work.append("corpus"),
        embedder_factory=lambda: expensive_work.append("embedder"),
        evaluate=evaluate,
    )
    config = RunnerConfig(
        tmp_path / "golden.jsonl",
        tmp_path / "manifest.json",
        tmp_path / "lock.json",
        output,
        markdown,
        tmp_path / "cache",
    )

    with pytest.raises(
        RuntimeError, match="Langfuse authentication failed: check credentials and host"
    ):
        run_evaluation(
            config,
            environment={
                "GROQ_API_KEY": "secret",
                "LANGFUSE_PUBLIC_KEY": "public",
                "LANGFUSE_SECRET_KEY": "private",
            },
            dependencies=dependencies,
        )

    assert expensive_work == []
    assert not output.exists()
    assert not markdown.exists()


def test_build_cases_excludes_unanswerable_and_uses_top_five_contexts() -> None:
    chunks = [
        BenchmarkChunk(f"chunk-{index}", "documento.pdf", 1, index, f"texto {index}", "h", 2)
        for index in range(6)
    ]
    observed_prompts: list[str] = []

    def generate(prompt: str) -> str:
        observed_prompts.append(prompt)
        return "resposta gerada"

    cases = build_cases(
        [
            _item("answerable", ItemType.ANSWERABLE, "referência"),
            _item("ambiguous", ItemType.AMBIGUOUS_PARTIAL, "referência parcial"),
            _item("unanswerable", ItemType.UNANSWERABLE, None),
        ],
        index=type(
            "Index",
            (),
            {
                "search": lambda self, vector, top_k: [
                    type("Result", (), {"chunk": chunk})() for chunk in chunks[:top_k]
                ]
            },
        )(),
        embedder=FakeEmbedder(),
        generate=generate,
    )

    assert [case.item_id for case in cases] == ["answerable", "ambiguous"]
    assert all(len(case.retrieved_contexts) == 5 for case in cases)
    assert len(observed_prompts) == 2
    assert "Responda somente com base nos trechos" in observed_prompts[0]


def test_run_evaluation_does_not_overwrite_reports_when_langfuse_delivery_fails(
    tmp_path: Path,
) -> None:
    dataset = tmp_path / "golden.jsonl"
    manifest = tmp_path / "manifest.json"
    lock = tmp_path / "lock.json"
    output = tmp_path / "result.json"
    markdown = tmp_path / "result.md"
    item = _item("answerable", ItemType.ANSWERABLE, "referência")
    dataset.write_text(json.dumps(item.model_dump(mode="json")) + "\n", encoding="utf-8")
    manifest.write_text(json.dumps({"version": "v1"}), encoding="utf-8")
    lock.write_text("{}", encoding="utf-8")
    output.write_text("previous JSON report", encoding="utf-8")
    markdown.write_text("previous Markdown report", encoding="utf-8")
    status = type(
        "Status", (), {"publishable": True, "label": "PUBLISHABLE", "blocker_reasons": []}
    )()

    def delivery_failure(metadata: dict[str, object], scores: dict[str, float]) -> None:
        del metadata, scores
        raise ValueError("batch export failed")

    dependencies = RagTriadRunnerDependencies(
        langfuse_client_factory=lambda credentials: object(),
        langfuse_auth_check=lambda client: True,
        assess_publishability=lambda **kwargs: status,
        load_items=lambda path: [item],
        load_corpus=lambda path: ExtractedCorpus(
            [BenchmarkPage("documento.pdf", 1, "corpus text", "x", 1)], "corpus-hash", 0.0
        ),
        chunk_pages=lambda pages, **kwargs: type(
            "Chunked",
            (),
            {"chunks": [BenchmarkChunk("chunk", "documento.pdf", 1, 0, "corpus text", "h", 2)]},
        )(),
        embedder_factory=lambda: FakeEmbedder(),
        index_factory=lambda chunks, vectors: type(
            "Index",
            (),
            {"search": lambda self, vector, top_k: [type("Result", (), {"chunk": chunks[0]})()]},
        )(),
        generate=lambda prompt: "response",
        judge_factory=lambda credentials, model: (object(), object()),
        evaluate=lambda cases, **kwargs: RagTriadSummary(
            1, {"faithfulness": 0.9}, provisional=False
        ),
        langfuse_record=delivery_failure,
        ragas_version=lambda: "0.2.15",
    )
    config = RunnerConfig(dataset, manifest, lock, output, markdown, tmp_path / "cache")

    with pytest.raises(RuntimeError, match="Langfuse safe metadata/score recording failed"):
        run_evaluation(
            config,
            environment={
                "GROQ_API_KEY": "secret",
                "LANGFUSE_PUBLIC_KEY": "public",
                "LANGFUSE_SECRET_KEY": "private",
            },
            dependencies=dependencies,
        )

    assert output.read_text(encoding="utf-8") == "previous JSON report"
    assert markdown.read_text(encoding="utf-8") == "previous Markdown report"


def test_run_evaluation_writes_redacted_result_and_safe_langfuse_metadata(tmp_path: Path) -> None:
    dataset = tmp_path / "golden.jsonl"
    manifest = tmp_path / "manifest.json"
    lock = tmp_path / "lock.json"
    output = tmp_path / "result.json"
    markdown = tmp_path / "result.md"
    checkpoint = tmp_path / "cache" / "responses.jsonl"
    item = _item("answerable", ItemType.ANSWERABLE, "referência secreta")
    dataset.write_text(json.dumps(item.model_dump(mode="json")) + "\n", encoding="utf-8")
    manifest.write_text(
        json.dumps(
            {
                "version": "v1",
                "status": "frozen",
                "item_count": 1,
                "composition": {
                    "answerable": 1,
                    "unanswerable": 0,
                    "ambiguous_partial": 0,
                },
                "documents": [],
            }
        ),
        encoding="utf-8",
    )
    lock.write_text("{}", encoding="utf-8")
    safe_events: list[dict[str, object]] = []
    publishability_calls: list[object] = []
    observed_batch_sizes: list[int] = []
    status = type(
        "Status",
        (),
        {"publishable": True, "label": "PUBLISHABLE", "blocker_reasons": []},
    )()

    def assess_publishability(**kwargs: object) -> object:
        publishability_calls.append(kwargs["max_items"])
        return status

    def evaluate(cases: object, **kwargs: object) -> RagTriadSummary:
        del cases
        observed_batch_sizes.append(cast(int, kwargs["batch_size"]))
        return RagTriadSummary(
            1,
            {
                "faithfulness": 0.9,
                "answer_relevancy": 0.8,
                "context_precision": 0.7,
                "context_recall": 0.6,
            },
            provisional=False,
        )

    dependencies = RagTriadRunnerDependencies(
        assess_publishability=assess_publishability,
        load_items=lambda path: [item],
        load_corpus=lambda path: ExtractedCorpus(
            [BenchmarkPage("documento.pdf", 1, "texto confidencial", "x", 1)],
            "corpus-hash",
            0.0,
        ),
        chunk_pages=lambda pages, **kwargs: type(
            "Chunked",
            (),
            {
                "chunks": [
                    BenchmarkChunk(
                        "chunk",
                        "documento.pdf",
                        1,
                        0,
                        "texto confidencial",
                        "h",
                        2,
                    )
                ]
            },
        )(),
        embedder_factory=lambda: FakeEmbedder(),
        generation_factory=lambda credentials, model: pytest.fail(
            "cached sample must not construct a generation provider"
        ),
        judge_factory=lambda credentials, model: (
            f"judge:{model}",
            f"judge-embeddings:{model}",
        ),
        index_factory=lambda chunks, vectors: type(
            "Index",
            (),
            {"search": lambda self, vector, top_k: [type("Result", (), {"chunk": chunks[0]})()]},
        )(),
        generate=lambda prompt: "resposta confidencial",
        evaluate=evaluate,
        langfuse_client_factory=lambda credentials: object(),
        langfuse_auth_check=lambda client: True,
        langfuse_record=lambda metadata, scores: safe_events.append(
            {"metadata": metadata, "scores": scores}
        ),
        ragas_version=lambda: "0.2.15",
    )
    config = RunnerConfig(
        dataset,
        manifest,
        lock,
        output,
        markdown,
        tmp_path / "cache",
        max_items=1,
        checkpoint_path=checkpoint,
        ragas_batch_size=3,
    )

    result = run_evaluation(
        config,
        environment={
            "GROQ_API_KEY": "secret",
            "LANGFUSE_PUBLIC_KEY": "public",
            "LANGFUSE_SECRET_KEY": "private",
        },
        dependencies=dependencies,
    )

    serialized = output.read_text(encoding="utf-8")
    assert result["publishability"] == "PUBLISHABLE"
    assert result["provisional"] is True
    assert publishability_calls == [None]
    assert result["content_redaction"] == RAGAS_CONTENT_REDACTION
    assert result["ragas_batch_size"] == 3
    assert observed_batch_sizes == [3]
    assert "texto confidencial" not in serialized
    assert "resposta confidencial" not in serialized
    assert "referência secreta" not in serialized
    assert "secret" not in serialized
    assert str(checkpoint) not in serialized
    assert checkpoint.read_text(encoding="utf-8") == (
        '{"item_id": "answerable", "response": "resposta confidencial"}\n'
    )
    assert safe_events == [
        {
            "metadata": {
                "schema_version": "marco-3.5-rag-triad-v1",
                "dataset_version": "v1",
                "case_count": 1,
                "publishability": "PUBLISHABLE",
                "content_redaction": RAGAS_CONTENT_REDACTION,
                "ragas_batch_size": 3,
                "generation_model": "llama-3.3-70b-versatile",
                "judge_model": "llama-3.3-70b-versatile",
            },
            "scores": {
                "faithfulness": 0.9,
                "answer_relevancy": 0.8,
                "context_precision": 0.7,
                "context_recall": 0.6,
            },
        }
    ]


def test_run_evaluation_rejects_smoke_publish_and_missing_langfuse(tmp_path: Path) -> None:
    config = RunnerConfig(
        tmp_path / "d",
        tmp_path / "m",
        tmp_path / "l",
        tmp_path / "o",
        tmp_path / "md",
        tmp_path / "c",
        max_items=1,
        publish=True,
    )
    with pytest.raises(ValueError, match="--publish"):
        run_evaluation(
            config,
            environment={
                "GROQ_API_KEY": "secret",
                "LANGFUSE_PUBLIC_KEY": "public",
                "LANGFUSE_SECRET_KEY": "private",
            },
        )
    config = RunnerConfig(
        tmp_path / "d",
        tmp_path / "m",
        tmp_path / "l",
        tmp_path / "o",
        tmp_path / "md",
        tmp_path / "c",
    )
    with pytest.raises(ValueError, match="Langfuse"):
        run_evaluation(
            config,
            environment={"GROQ_API_KEY": "secret"},
        )


def test_e5_judge_embeddings_apply_query_and_passage_prefixes() -> None:
    from evals.rag_triad_runner import PrefixAwareE5Embeddings

    observed: dict[str, list[str]] = {}

    class FakeEmbeddings:
        def embed_documents(self, texts: list[str]) -> list[list[float]]:
            observed["documents"] = texts
            return [[1.0] for _ in texts]

        def embed_query(self, text: str) -> list[float]:
            observed["query"] = [text]
            return [1.0]

    wrapped = PrefixAwareE5Embeddings(FakeEmbeddings())
    wrapped.embed_documents(["trecho"])
    wrapped.embed_query("pergunta")

    assert observed == {"documents": ["passage: trecho"], "query": ["query: pergunta"]}


def test_run_evaluation_rejects_non_positive_smoke_limit(tmp_path: Path) -> None:
    config = RunnerConfig(
        tmp_path / "d",
        tmp_path / "m",
        tmp_path / "l",
        tmp_path / "o",
        tmp_path / "md",
        tmp_path / "c",
        max_items=0,
    )
    with pytest.raises(ValueError, match="--max-items"):
        run_evaluation(config, environment={"GROQ_API_KEY": "secret"})


def test_ragas_batch_size_cli_defaults_to_one() -> None:
    assert runner._parser().parse_args([]).ragas_batch_size == 1


@pytest.mark.parametrize("batch_size", [0, -1])
def test_run_evaluation_rejects_non_positive_ragas_batch_size(
    tmp_path: Path, batch_size: int
) -> None:
    config = RunnerConfig(
        tmp_path / "d",
        tmp_path / "m",
        tmp_path / "l",
        tmp_path / "o",
        tmp_path / "md",
        tmp_path / "c",
        ragas_batch_size=batch_size,
    )

    with pytest.raises(ValueError, match="--ragas-batch-size"):
        run_evaluation(config, environment={"GROQ_API_KEY": "secret"})


def test_build_cases_checkpoints_successes_and_reuses_them_after_a_rate_limit(
    tmp_path: Path,
) -> None:
    chunks = [
        BenchmarkChunk("chunk", "documento.pdf", 1, 0, "texto", "h", 2),
    ]
    items = [
        _item("first", ItemType.ANSWERABLE, "referência"),
        _item("second", ItemType.ANSWERABLE, "referência"),
    ]
    checkpoint = tmp_path / "responses.jsonl"
    calls: list[str] = []

    class RateLimited(Exception):
        status_code = 429
        headers = {"retry-after": "120"}

    def rate_limited_generate(prompt: str) -> str:
        calls.append(prompt)
        if len(calls) == 1:
            return "primeira resposta"
        raise RateLimited("daily limit")

    index = type(
        "Index",
        (),
        {"search": lambda self, vector, top_k: [type("Result", (), {"chunk": chunks[0]})()]},
    )()

    with pytest.raises(RuntimeError, match="checkpoint"):
        build_cases(
            items,
            index=index,
            embedder=FakeEmbedder(),
            generate=rate_limited_generate,
            checkpoint_path=checkpoint,
            max_rate_limit_wait_seconds=60,
            sleep=lambda seconds: None,
        )

    assert [json.loads(line) for line in checkpoint.read_text(encoding="utf-8").splitlines()] == [
        {"item_id": "first", "response": "primeira resposta"}
    ]

    resumed_calls: list[str] = []

    def resumed_generate(prompt: str) -> str:
        resumed_calls.append(prompt)
        return "segunda resposta"

    cases = build_cases(
        items,
        index=index,
        embedder=FakeEmbedder(),
        generate=resumed_generate,
        checkpoint_path=checkpoint,
        max_rate_limit_wait_seconds=60,
        sleep=lambda seconds: None,
    )

    assert [case.response for case in cases] == ["primeira resposta", "segunda resposta"]
    assert len(resumed_calls) == 1


def test_retry_after_seconds_reads_headers_and_provider_message_safely() -> None:
    class HeaderRateLimit(Exception):
        headers = {"retry-after": "26m"}

    class MessageRateLimit(Exception):
        pass

    assert runner._retry_after_seconds(HeaderRateLimit()) == 1560
    assert runner._retry_after_seconds(MessageRateLimit("try again in 2.5 minutes")) == 150
    assert runner._retry_after_seconds(MessageRateLimit("no retry hint")) is None


def test_select_stratified_cached_items_favors_document_then_type_then_difficulty() -> None:
    """Selection cycles least-represented documents, types, difficulties, then stable IDs."""

    def sample(
        item_id: str, document: str, item_type: ItemType, difficulty: Difficulty
    ) -> GoldenItem:
        item = _item(item_id, item_type, "referência")
        return item.model_copy(update={"documento": document, "dificuldade": difficulty})

    items = [
        sample("a-answer-easy", "a.pdf", ItemType.ANSWERABLE, Difficulty.FACIL),
        sample("a-amb-hard", "a.pdf", ItemType.AMBIGUOUS_PARTIAL, Difficulty.DIFICIL),
        sample("b-answer-medium", "b.pdf", ItemType.ANSWERABLE, Difficulty.MEDIO),
        sample("c-amb-easy", "c.pdf", ItemType.AMBIGUOUS_PARTIAL, Difficulty.FACIL),
    ]

    selected = runner.select_stratified_cached_items(
        items,
        checkpoint_responses={item.id: "cached" for item in items},
        requested_count=3,
    )

    assert [item.id for item in selected] == [
        "a-amb-hard",
        "b-answer-medium",
        "c-amb-easy",
    ]


def test_select_stratified_cached_items_rejects_insufficient_suitable_responses() -> None:
    items = [
        _item("cached", ItemType.ANSWERABLE, "referência"),
        _item("not-cached", ItemType.AMBIGUOUS_PARTIAL, "referência"),
    ]

    with pytest.raises(ValueError, match="only 1 suitable checkpointed responses"):
        runner.select_stratified_cached_items(
            items, checkpoint_responses={"cached": "response"}, requested_count=2
        )


def test_select_stratified_cached_items_rejects_more_than_four_cases() -> None:
    with pytest.raises(ValueError, match="maximum of 4"):
        runner.select_stratified_cached_items(
            [_item("cached", ItemType.ANSWERABLE, "referência")],
            checkpoint_responses={"cached": "response"},
            requested_count=5,
        )


def test_cached_sample_reuses_responses_and_writes_only_provisional_safe_aggregates(
    tmp_path: Path,
) -> None:
    dataset = tmp_path / "golden.jsonl"
    manifest = tmp_path / "manifest.json"
    lock = tmp_path / "lock.json"
    output = tmp_path / "result.json"
    markdown = tmp_path / "result.md"
    checkpoint = tmp_path / "responses.jsonl"
    items = [
        _item("secret-a", ItemType.ANSWERABLE, "referência secreta").model_copy(
            update={"documento": "secret-a.pdf"}
        ),
        _item("secret-b", ItemType.AMBIGUOUS_PARTIAL, "referência secreta").model_copy(
            update={"documento": "secret-b.pdf"}
        ),
    ]
    dataset.write_text(
        "".join(json.dumps(item.model_dump(mode="json")) + "\n" for item in items), encoding="utf-8"
    )
    manifest.write_text(json.dumps({"version": "v1"}), encoding="utf-8")
    lock.write_text("{}", encoding="utf-8")
    checkpoint.write_text(
        "".join(
            json.dumps({"item_id": item.id, "response": f"response for {item.id}"}) + "\n"
            for item in items
        ),
        encoding="utf-8",
    )
    events: list[dict[str, object]] = []
    constructed_judge_models: list[str] = []
    status = type(
        "Status", (), {"publishable": True, "label": "PUBLISHABLE", "blocker_reasons": []}
    )()

    def judge_factory(credentials: object, model: str) -> tuple[object, object]:
        del credentials
        constructed_judge_models.append(model)
        return f"judge:{model}", f"judge-embeddings:{model}"

    dependencies = RagTriadRunnerDependencies(
        assess_publishability=lambda **kwargs: status,
        load_items=lambda path: items,
        load_corpus=lambda path: ExtractedCorpus(
            [BenchmarkPage("secret-a.pdf", 1, "classified corpus material", "x", 1)],
            "corpus-hash",
            0.0,
        ),
        chunk_pages=lambda pages, **kwargs: type(
            "Chunked",
            (),
            {
                "chunks": [
                    BenchmarkChunk(
                        "chunk", "secret-a.pdf", 1, 0, "classified corpus material", "h", 2
                    )
                ]
            },
        )(),
        embedder_factory=lambda: FakeEmbedder(),
        generation_factory=lambda credentials, model: pytest.fail(
            "cached sample must not construct a generation provider"
        ),
        judge_factory=judge_factory,
        index_factory=lambda chunks, vectors: type(
            "Index",
            (),
            {"search": lambda self, vector, top_k: [type("Result", (), {"chunk": chunks[0]})()]},
        )(),
        evaluate=lambda cases, **kwargs: RagTriadSummary(
            len(cases), {"faithfulness": 0.9}, provisional=False
        ),
        langfuse_client_factory=lambda credentials: object(),
        langfuse_auth_check=lambda client: True,
        langfuse_record=lambda metadata, scores: events.append(metadata),
        ragas_version=lambda: "0.2.15",
    )
    config = RunnerConfig(
        dataset,
        manifest,
        lock,
        output,
        markdown,
        tmp_path / "cache",
        checkpoint_path=checkpoint,
        stratified_cached_sample_size=2,
        ragas_batch_size=1,
        judge_model="llama-3.1-8b-instant",
    )

    result = run_evaluation(
        config,
        environment={
            "GROQ_API_KEY": "secret",
            "LANGFUSE_PUBLIC_KEY": "public",
            "LANGFUSE_SECRET_KEY": "private",
        },
        dependencies=dependencies,
    )

    serialized = output.read_text(encoding="utf-8") + markdown.read_text(encoding="utf-8")
    assert result["provisional"] is True
    assert result["publishability"] == "PROVISIONAL"
    assert result["sample_mode"] == "stratified_cached"
    assert result["generation_model"] == "llama-3.3-70b-versatile"
    assert result["judge_model"] == "llama-3.1-8b-instant"
    assert result["judge_scope"] == (
        "PROVISIONAL/non-ratifying: cached tutor answers were generated by "
        "llama-3.3-70b-versatile and judged by llama-3.1-8b-instant; "
        "this sample cannot ratify ADR-009."
    )
    assert constructed_judge_models == ["llama-3.1-8b-instant"]
    assert result["requested_count"] == result["selected_count"] == 2
    assert result["stratum_summary"] == {
        "document_count": 2,
        "item_types": {"ambiguous_partial": 1, "answerable": 1},
        "difficulties": {"facil": 2},
    }
    assert events == [
        {
            "schema_version": "marco-3.5-rag-triad-v1",
            "dataset_version": "v1",
            "case_count": 2,
            "publishability": "PROVISIONAL",
            "content_redaction": RAGAS_CONTENT_REDACTION,
            "generation_model": "llama-3.3-70b-versatile",
            "judge_model": "llama-3.1-8b-instant",
            "sample_mode": "stratified_cached",
            "requested_count": 2,
            "selected_count": 2,
            "stratum_summary": result["stratum_summary"],
            "ragas_batch_size": 1,
            "provisional_scope": (
                "PROVISIONAL only: limited to four cached cases, one per available document "
                "under the 100k TPD quota; cannot ratify ADR-009."
            ),
            "judge_scope": (
                "PROVISIONAL/non-ratifying: cached tutor answers were generated by "
                "llama-3.3-70b-versatile and judged by llama-3.1-8b-instant; "
                "this sample cannot ratify ADR-009."
            ),
        }
    ]
    for forbidden in (
        "secret-a",
        "secret-b",
        "classified corpus material",
        "referência secreta",
        "response for",
    ):
        assert forbidden not in serialized


def test_cached_sample_refuses_publish(tmp_path: Path) -> None:
    config = RunnerConfig(
        tmp_path / "d",
        tmp_path / "m",
        tmp_path / "l",
        tmp_path / "o",
        tmp_path / "md",
        tmp_path / "c",
        publish=True,
        stratified_cached_sample_size=1,
    )

    with pytest.raises(ValueError, match="--publish"):
        run_evaluation(config, environment={"GROQ_API_KEY": "secret"})


def test_judge_model_cli_defaults_to_generation_model_and_accepts_override() -> None:
    parser = runner._parser()

    assert parser.parse_args([]).judge_model == "llama-3.3-70b-versatile"
    assert parser.parse_args(["--judge-model", "llama-3.1-8b-instant"]).judge_model == (
        "llama-3.1-8b-instant"
    )


@pytest.mark.parametrize("judge_model", ["", "   "])
def test_run_evaluation_rejects_empty_judge_model(tmp_path: Path, judge_model: str) -> None:
    config = RunnerConfig(
        tmp_path / "d",
        tmp_path / "m",
        tmp_path / "l",
        tmp_path / "o",
        tmp_path / "md",
        tmp_path / "c",
        judge_model=judge_model,
    )

    with pytest.raises(ValueError, match="--judge-model"):
        run_evaluation(config, environment={"GROQ_API_KEY": "secret"})


def test_full_publish_rejects_different_judge_model(tmp_path: Path) -> None:
    config = RunnerConfig(
        tmp_path / "d",
        tmp_path / "m",
        tmp_path / "l",
        tmp_path / "o",
        tmp_path / "md",
        tmp_path / "c",
        publish=True,
        judge_model="llama-3.1-8b-instant",
    )

    with pytest.raises(ValueError, match="judge model"):
        run_evaluation(config, environment={"GROQ_API_KEY": "secret"})
