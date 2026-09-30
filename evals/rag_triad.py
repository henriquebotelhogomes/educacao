"""Ragas-backed RAG Triad evaluation contract for Marco 3.5."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

RAG_TRIAD_METRICS = (
    "faithfulness",
    "answer_relevancy",
    "context_precision",
    "context_recall",
)


@dataclass(frozen=True)
class RagTriadCase:
    item_id: str
    user_input: str
    retrieved_contexts: list[str]
    response: str
    reference: str

    def __post_init__(self) -> None:
        if not self.item_id.strip():
            raise ValueError("item_id must not be empty")
        if not self.user_input.strip():
            raise ValueError("user_input must not be empty")
        if not self.retrieved_contexts or any(
            not context.strip() for context in self.retrieved_contexts
        ):
            raise ValueError("retrieved_contexts must contain non-empty evidence")
        if not self.response.strip():
            raise ValueError("response must not be empty")
        if not self.reference.strip():
            raise ValueError("reference must not be empty")

    def as_ragas_row(self) -> dict[str, object]:
        return {
            "user_input": self.user_input,
            "retrieved_contexts": self.retrieved_contexts,
            "response": self.response,
            "reference": self.reference,
        }


@dataclass(frozen=True)
class RagTriadSummary:
    item_count: int
    metrics: dict[str, float]
    provisional: bool = True


@dataclass(frozen=True)
class EvalCredentials:
    groq_api_key: str | None = field(default=None, repr=False)
    openrouter_api_key: str | None = field(default=None, repr=False)
    langfuse_public_key: str | None = field(default=None, repr=False)
    langfuse_secret_key: str | None = field(default=None, repr=False)

    @property
    def langfuse_enabled(self) -> bool:
        return bool(self.langfuse_public_key and self.langfuse_secret_key)


def require_eval_credentials(
    *,
    groq_api_key: str | None = None,
    openrouter_api_key: str | None = None,
    langfuse_public_key: str | None,
    langfuse_secret_key: str | None,
) -> EvalCredentials:
    if not groq_api_key and not openrouter_api_key:
        raise ValueError(
            "GROQ_API_KEY or OPENROUTER_API_KEY is required for generation and Ragas judging"
        )
    if bool(langfuse_public_key) != bool(langfuse_secret_key):
        raise ValueError("Langfuse public and secret keys must be configured together")
    return EvalCredentials(
        groq_api_key=groq_api_key,
        openrouter_api_key=openrouter_api_key,
        langfuse_public_key=langfuse_public_key,
        langfuse_secret_key=langfuse_secret_key,
    )


def _ragas_components() -> tuple[Any, list[Any]]:
    from ragas import EvaluationDataset
    from ragas.metrics import (
        Faithfulness,
        LLMContextPrecisionWithReference,
        LLMContextRecall,
        ResponseRelevancy,
    )

    metrics = [
        Faithfulness(),
        ResponseRelevancy(),
        LLMContextPrecisionWithReference(name="context_precision"),
        LLMContextRecall(name="context_recall"),
    ]
    return EvaluationDataset, metrics


def _extract_metric_means(raw_result: Any) -> dict[str, float]:
    if isinstance(raw_result, Mapping):
        return {name: float(raw_result[name]) for name in RAG_TRIAD_METRICS}
    if not hasattr(raw_result, "to_pandas"):
        raise TypeError("Ragas result must be a mapping or expose to_pandas()")
    frame = raw_result.to_pandas()
    return {name: float(frame[name].dropna().mean()) for name in RAG_TRIAD_METRICS}


def evaluate_rag_triad(
    cases: list[RagTriadCase],
    *,
    llm: object,
    embeddings: object,
    batch_size: int = 1,
    evaluate_fn: Callable[..., Any] | None = None,
) -> RagTriadSummary:
    if not cases:
        raise ValueError("at least one RAG Triad case is required")
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1")
    EvaluationDataset, metrics = _ragas_components()
    dataset = EvaluationDataset.from_list([case.as_ragas_row() for case in cases])
    if evaluate_fn is None:
        from ragas import evaluate

        evaluate_fn = evaluate
    raw_result = evaluate_fn(
        dataset=dataset,
        metrics=metrics,
        llm=llm,
        embeddings=embeddings,
        raise_exceptions=True,
        show_progress=True,
        batch_size=batch_size,
    )
    return RagTriadSummary(
        item_count=len(cases),
        metrics=_extract_metric_means(raw_result),
    )
