"""High-level ADR-018 benchmark runner."""

from __future__ import annotations

import json
import pathlib
import time
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Callable

import numpy as np

from evals.benchmark.chunking import (
    CANONICAL_CHUNK_TOKENIZER,
    CanonicalChunkTokenizer,
    ChunkedCorpus,
    ChunkTokenizer,
    chunk_pages,
)
from evals.benchmark.chunking_experiment import (
    ChunkingExperimentCorpus,
    ChunkingVariant,
    SemanticSplitter,
    build_chunked_corpus,
)
from evals.benchmark.corpus import CachedCorpusExtractor, PageExtractor
from evals.benchmark.embeddings import Embedder, SentenceTransformerAdapter, normalize_embeddings
from evals.benchmark.evaluator import evaluate_retrieval
from evals.benchmark.hashing import canonical_sha256, sha256_file
from evals.benchmark.publishability import (
    assess_publishability,
    effective_document_hashes,
    review_counts,
)
from evals.benchmark.registry import EmbeddingCandidate
from evals.benchmark.retrieval import BenchmarkChunk, InMemoryCosineIndex
from evals.benchmark.schemas import (
    BenchmarkConfig,
    BenchmarkResult,
    CorpusSummary,
    DatasetSummary,
    EmbeddingInputSummary,
    HashSummary,
    ModelResult,
    PublishabilityStatus,
    RunMetadata,
    TimingSummary,
)
from evals.schema import Difficulty, GoldenItem, ItemType, ReviewStatus


class PublishabilityError(RuntimeError):
    pass


def assess_embedding_inputs(
    *,
    chunks: list[BenchmarkChunk],
    embedder: Any,
    candidate: EmbeddingCandidate,
) -> EmbeddingInputSummary:
    texts = [chunk.text for chunk in chunks]
    prepare = getattr(embedder, "prepare_passages", None)
    prepared = prepare(texts) if callable(prepare) else texts
    lengths = [len(embedder.tokenize(text)) for text in prepared]
    max_prepared = max(lengths, default=0)
    truncated = sum(length > candidate.max_sequence_tokens for length in lengths)
    return EmbeddingInputSummary(
        max_sequence_tokens=candidate.max_sequence_tokens,
        max_prepared_tokens=max_prepared,
        truncated_chunk_count=truncated,
        valid=truncated == 0,
    )


def load_golden_items(
    dataset_path: pathlib.Path,
    *,
    max_items: int | None = None,
) -> list[GoldenItem]:
    items: list[GoldenItem] = []
    for line in dataset_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped:
            items.append(GoldenItem.model_validate(json.loads(stripped)))
            if max_items is not None and len(items) >= max_items:
                break
    return items


def dataset_summary(items: list[GoldenItem], manifest: dict[str, object]) -> DatasetSummary:
    type_counts = Counter(item.tipo.value for item in items)
    evidence_count = sum(len(item.evidence_quotes) for item in items)
    version_value = manifest.get("version")
    version = version_value if isinstance(version_value, str) else None
    return DatasetSummary(
        version=version,
        status=str(manifest.get("status", "unknown")),
        item_count=len(items),
        composition={
            "answerable": type_counts.get("answerable", 0),
            "unanswerable": type_counts.get("unanswerable", 0),
            "ambiguous_partial": type_counts.get("ambiguous_partial", 0),
        },
        review_counts=review_counts(items),
        evidence_quote_count=evidence_count,
    )


def make_config(
    *,
    candidate: EmbeddingCandidate,
    dataset_path: pathlib.Path,
    manifest_path: pathlib.Path,
    output_path: pathlib.Path | None,
    device: str | None,
    offline: bool,
    max_pages_per_document: int | None,
    max_items: int | None,
    publish_requested: bool,
    chunking_variant: ChunkingVariant | None = None,
) -> BenchmarkConfig:
    variant = chunking_variant or ChunkingVariant(
        strategy="structural",
        chunk_size=512,
        overlap=64,
    )
    return BenchmarkConfig(
        model_alias=candidate.alias,
        model_name=candidate.model_name,
        model_dimension=candidate.dimension,
        dataset_path=str(dataset_path),
        manifest_path=str(manifest_path),
        output_path=str(output_path) if output_path else None,
        device=device,
        offline=offline,
        max_pages_per_document=max_pages_per_document,
        max_items=max_items,
        publish_requested=publish_requested,
        chunk_size=variant.chunk_size,
        chunk_overlap=variant.overlap,
        chunking_strategy=variant.strategy,
        chunking_strategy_version=variant.strategy_version,
        experiment_type="chunking" if chunking_variant is not None else "embedding",
    )


def benchmark_result_identity(config: BenchmarkConfig) -> tuple[str, str, str]:
    if config.experiment_type == "chunking":
        return ("adr-012-benchmark-result-v1", "ADR-012", "chunking")
    return ("adr-018-benchmark-result-v1", "ADR-018", "embedding")


def run_benchmark(
    *,
    config: BenchmarkConfig,
    candidate: EmbeddingCandidate,
    repo_root: pathlib.Path,
    cache_dir: pathlib.Path,
    embedder: Embedder | None = None,
    extractor: PageExtractor | None = None,
    chunk_tokenizer: ChunkTokenizer | None = None,
    chunking_variant: ChunkingVariant | None = None,
    semantic_splitter_factory: Callable[[Any], SemanticSplitter] | None = None,
    lock_path: pathlib.Path | None = None,
) -> BenchmarkResult:
    """Run one candidate benchmark and return a typed result."""
    total_started = time.perf_counter()
    started_at = datetime.now(timezone.utc).isoformat()
    dataset_path = pathlib.Path(config.dataset_path)
    manifest_path = pathlib.Path(config.manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    document_hashes_sha256 = canonical_sha256(
        effective_document_hashes(manifest, repo_root=repo_root)
    )
    items = load_golden_items(dataset_path, max_items=config.max_items)

    publishability = assess_publishability(
        dataset_path=dataset_path,
        manifest_path=manifest_path,
        lock_path=lock_path,
        repo_root=repo_root,
        max_items=config.max_items,
        max_pages_per_document=config.max_pages_per_document,
    )
    if config.publish_requested and not publishability.publishable:
        raise PublishabilityError("; ".join(publishability.blocker_reasons))

    corpus = CachedCorpusExtractor(
        repo_root=repo_root,
        cache_dir=cache_dir,
        extractor=extractor,
    ).load_manifest(manifest_path, max_pages_per_document=config.max_pages_per_document)

    effective_embedder = embedder or SentenceTransformerAdapter(
        candidate,
        device=config.device,
        offline=config.offline,
    )
    effective_chunk_tokenizer = chunk_tokenizer or CanonicalChunkTokenizer()
    chunked: ChunkedCorpus | ChunkingExperimentCorpus
    if chunking_variant is None:
        chunked = chunk_pages(
            corpus.pages,
            encode_fn=effective_chunk_tokenizer.tokenize,
            chunk_size=config.chunk_size,
            overlap=config.chunk_overlap,
        )
    else:
        chunked = build_chunked_corpus(
            corpus.pages,
            variant=chunking_variant,
            tokenizer=effective_chunk_tokenizer,
            embedder=effective_embedder,
            semantic_splitter_factory=semantic_splitter_factory,
        )
    embedding_inputs = assess_embedding_inputs(
        chunks=chunked.chunks,
        embedder=effective_embedder,
        candidate=candidate,
    )
    if not embedding_inputs.valid:
        blockers = [
            *publishability.blocker_reasons,
            f"{embedding_inputs.truncated_chunk_count} prepared passages exceed the model "
            f"limit of {embedding_inputs.max_sequence_tokens} tokens.",
        ]
        publishability = PublishabilityStatus(
            publishable=False,
            label="PROVISIONAL",
            blocker_reasons=blockers,
            lock_path=publishability.lock_path,
        )
        if config.publish_requested:
            raise PublishabilityError(blockers[-1])

    encoding_started = time.perf_counter()
    passage_embeddings = effective_embedder.embed_passages([chunk.text for chunk in chunked.chunks])
    encoding_ms = (time.perf_counter() - encoding_started) * 1000

    index_started = time.perf_counter()
    index = InMemoryCosineIndex(chunked.chunks, passage_embeddings)
    index_ms = (time.perf_counter() - index_started) * 1000
    metrics = evaluate_retrieval(items=items, index=index, embedder=effective_embedder)

    timings = TimingSummary(
        extraction_ms=corpus.extraction_ms,
        chunking_ms=chunked.chunking_ms,
        corpus_encoding_ms=encoding_ms,
        index_build_ms=index_ms,
        total_ms=(time.perf_counter() - total_started) * 1000,
    )
    finished_at = datetime.now(timezone.utc).isoformat()
    config_hash = canonical_sha256(config.deterministic_payload())
    schema_version, adr, experiment_type = benchmark_result_identity(config)
    return BenchmarkResult(
        schema_version=schema_version,
        adr=adr,
        experiment_type=experiment_type,
        model=ModelResult(
            alias=candidate.alias,
            model_name=candidate.model_name,
            dimension=candidate.dimension,
            family=candidate.family,
        ),
        config=config,
        hashes=HashSummary(
            config_sha256=config_hash,
            dataset_sha256=sha256_file(dataset_path),
            manifest_sha256=sha256_file(manifest_path),
            corpus_sha256=corpus.corpus_sha256,
            document_hashes_sha256=document_hashes_sha256,
        ),
        dataset=dataset_summary(items, manifest),
        corpus=CorpusSummary(
            page_count=len(corpus.pages),
            chunk_count=len(chunked.chunks),
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            chunk_tokenizer_name=CANONICAL_CHUNK_TOKENIZER,
            chunking_strategy=config.chunking_strategy,
            chunking_strategy_version=config.chunking_strategy_version,
            documents=chunked.documents,
        ),
        metrics=metrics,
        embedding_inputs=embedding_inputs,
        timings=timings,
        publishability=publishability,
        run=RunMetadata(started_at=started_at, finished_at=finished_at),
    )


def write_result_json(result: BenchmarkResult, output_path: pathlib.Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(
            result.model_dump(mode="json", exclude_none=False),
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


class FakeSmokeEmbedder:
    dimension = 2

    def tokenize(self, text: str) -> list[int]:
        return list(range(len(text.split())))

    def embed_queries(self, texts: list[str]) -> np.ndarray:
        return self._embed(texts)

    def embed_passages(self, texts: list[str]) -> np.ndarray:
        return self._embed(texts)

    def _embed(self, texts: list[str]) -> np.ndarray:
        vectors = []
        for text in texts:
            lower = text.casefold()
            vectors.append([1.0, 0.0] if "milho" in lower else [0.0, 1.0])
        return normalize_embeddings(np.array(vectors, dtype=np.float32))


def fake_smoke_result(output_path: pathlib.Path | None = None) -> BenchmarkResult:
    """Run a no-PDF/no-model smoke benchmark with a deterministic fake embedder."""
    started_at = datetime.now(timezone.utc).isoformat()
    candidate = EmbeddingCandidate(
        alias="fake-smoke",
        model_name="fake://keyword-smoke",
        dimension=2,
        family="fake",
        max_sequence_tokens=512,
    )
    config = BenchmarkConfig(
        model_alias=candidate.alias,
        model_name=candidate.model_name,
        model_dimension=2,
        dataset_path="synthetic://smoke",
        manifest_path="synthetic://smoke",
        output_path=str(output_path) if output_path else None,
        offline=True,
        max_pages_per_document=1,
        max_items=2,
    )
    embedder = FakeSmokeEmbedder()
    chunks = [
        BenchmarkChunk("doc-smoke.pdf:1:0", "doc-smoke.pdf", 1, 0, "plantio de milho", "a", 3),
        BenchmarkChunk("doc-smoke.pdf:2:0", "doc-smoke.pdf", 2, 0, "manejo de feijão", "b", 3),
    ]
    embeddings = embedder.embed_passages([chunk.text for chunk in chunks])
    index = InMemoryCosineIndex(chunks, embeddings)
    items = [
        GoldenItem(
            id="smoke-001",
            pergunta="Como plantar milho?",
            resposta_referencia="Com solo adequado.",
            documento="doc-smoke.pdf",
            paginas_esperadas=[1],
            evidence_quotes=["plantio de milho"],
            tipo=ItemType.ANSWERABLE,
            dificuldade=Difficulty.FACIL,
            review_status=ReviewStatus.DRAFT,
            notas=None,
        ),
        GoldenItem(
            id="smoke-002",
            pergunta="Qual é o preço futuro da soja?",
            resposta_referencia=None,
            documento="doc-smoke.pdf",
            paginas_esperadas=[],
            evidence_quotes=[],
            tipo=ItemType.UNANSWERABLE,
            dificuldade=Difficulty.FACIL,
            review_status=ReviewStatus.DRAFT,
            notas="fora do corpus sintético",
        ),
    ]
    metrics = evaluate_retrieval(items=items, index=index, embedder=embedder)
    finished_at = datetime.now(timezone.utc).isoformat()
    return BenchmarkResult(
        model=ModelResult(
            alias=candidate.alias,
            model_name=candidate.model_name,
            dimension=2,
            family="fake",
        ),
        config=config,
        hashes=HashSummary(
            config_sha256=canonical_sha256(config.deterministic_payload()),
            dataset_sha256=canonical_sha256([item.model_dump(mode="json") for item in items]),
            manifest_sha256=canonical_sha256({"status": "draft", "version": "smoke"}),
            corpus_sha256=canonical_sha256([chunk.chunk_id for chunk in chunks]),
            document_hashes_sha256=canonical_sha256({"doc-smoke.pdf": "synthetic"}),
        ),
        dataset=DatasetSummary(
            version="smoke",
            status="draft",
            item_count=2,
            composition={"answerable": 1, "unanswerable": 1, "ambiguous_partial": 0},
            review_counts={"draft": 2, "reviewed": 0, "approved": 0},
            evidence_quote_count=1,
        ),
        corpus=CorpusSummary(
            page_count=2,
            chunk_count=2,
            chunk_size=512,
            chunk_overlap=64,
            chunk_tokenizer_name=CANONICAL_CHUNK_TOKENIZER,
            chunking_strategy="structural",
            chunking_strategy_version="structural-v1-t512-o64",
            documents={"doc-smoke.pdf": {"pages": 2, "chunks": 2}},
        ),
        metrics=metrics,
        embedding_inputs=EmbeddingInputSummary(
            max_sequence_tokens=512,
            max_prepared_tokens=3,
            truncated_chunk_count=0,
            valid=True,
        ),
        timings=TimingSummary(total_ms=0.0),
        publishability=PublishabilityStatus(
            publishable=False,
            label="PROVISIONAL",
            blocker_reasons=["Synthetic smoke dataset is draft and not publishable."],
        ),
        run=RunMetadata(started_at=started_at, finished_at=finished_at),
    )
