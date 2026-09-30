"""Tests for the Ragas-based RAG Triad evaluation contract."""

from __future__ import annotations

import pytest

from evals.rag_triad import (
    RAG_TRIAD_METRICS,
    RagTriadCase,
    evaluate_rag_triad,
    require_eval_credentials,
)


def test_rag_triad_uses_the_four_declared_ragas_metrics() -> None:
    case = RagTriadCase(
        item_id="v1-doc-001",
        user_input="Qual é a resposta?",
        retrieved_contexts=["Trecho comprovado."],
        response="A resposta está no trecho.",
        reference="Resposta de referência.",
    )
    observed: dict[str, object] = {}

    def fake_evaluate(*, dataset, metrics, llm, embeddings, **kwargs):
        observed["dataset"] = dataset
        observed["metric_names"] = [metric.name for metric in metrics]
        observed["llm"] = llm
        observed["embeddings"] = embeddings
        return {
            "faithfulness": 0.9,
            "answer_relevancy": 0.8,
            "context_precision": 0.7,
            "context_recall": 0.6,
        }

    summary = evaluate_rag_triad(
        [case],
        llm=object(),
        embeddings=object(),
        evaluate_fn=fake_evaluate,
    )

    assert observed["metric_names"] == list(RAG_TRIAD_METRICS)
    assert summary.item_count == 1
    assert summary.metrics["faithfulness"] == pytest.approx(0.9)
    assert summary.provisional is True


def test_rag_triad_forwards_configured_batch_size_to_ragas() -> None:
    case = RagTriadCase(
        item_id="v1-doc-001",
        user_input="Qual é a resposta?",
        retrieved_contexts=["Trecho comprovado."],
        response="A resposta está no trecho.",
        reference="Resposta de referência.",
    )
    observed: dict[str, object] = {}

    def fake_evaluate(*, batch_size, **kwargs):
        observed["batch_size"] = batch_size
        return {
            "faithfulness": 0.9,
            "answer_relevancy": 0.8,
            "context_precision": 0.7,
            "context_recall": 0.6,
        }

    evaluate_rag_triad(
        [case],
        llm=object(),
        embeddings=object(),
        batch_size=2,
        evaluate_fn=fake_evaluate,
    )

    assert observed["batch_size"] == 2


@pytest.mark.parametrize("batch_size", [0, -1])
def test_rag_triad_rejects_non_positive_batch_size(batch_size: int) -> None:
    case = RagTriadCase(
        item_id="v1-doc-001",
        user_input="Qual é a resposta?",
        retrieved_contexts=["Trecho comprovado."],
        response="A resposta está no trecho.",
        reference="Resposta de referência.",
    )

    with pytest.raises(ValueError, match="batch_size"):
        evaluate_rag_triad(
            [case],
            llm=object(),
            embeddings=object(),
            batch_size=batch_size,
            evaluate_fn=lambda **kwargs: {},
        )


def test_rag_triad_case_rejects_missing_grounding_context() -> None:
    with pytest.raises(ValueError, match="retrieved_contexts"):
        RagTriadCase(
            item_id="v1-doc-001",
            user_input="Pergunta",
            retrieved_contexts=[],
            response="Resposta",
            reference="Referência",
        )


def test_eval_credentials_require_groq_and_complete_langfuse_pair() -> None:
    with pytest.raises(ValueError, match="GROQ_API_KEY"):
        require_eval_credentials(
            groq_api_key=None,
            langfuse_public_key=None,
            langfuse_secret_key=None,
        )

    with pytest.raises(ValueError, match="Langfuse"):
        require_eval_credentials(
            groq_api_key="groq",
            langfuse_public_key="public",
            langfuse_secret_key=None,
        )

    credentials = require_eval_credentials(
        groq_api_key="groq",
        langfuse_public_key="public",
        langfuse_secret_key="secret",
    )
    assert credentials.langfuse_enabled is True
