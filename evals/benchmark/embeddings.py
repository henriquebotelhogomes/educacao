"""Embedding adapters for ADR-018 benchmark candidates."""

from __future__ import annotations

import os
from typing import Any, Protocol

import numpy as np

from evals.benchmark.registry import EmbeddingCandidate


class Embedder(Protocol):
    dimension: int

    def embed_queries(self, texts: list[str]) -> np.ndarray: ...

    def embed_passages(self, texts: list[str]) -> np.ndarray: ...

    def tokenize(self, text: str) -> list[int]: ...


def normalize_embeddings(vectors: np.ndarray) -> np.ndarray:
    """Return row-wise L2-normalized float32 embeddings."""
    array = np.asarray(vectors, dtype=np.float32)
    if array.ndim == 1:
        array = array.reshape(1, -1)
    norms = np.linalg.norm(array, axis=1, keepdims=True)
    norms[norms == 0.0] = 1.0
    return array / norms


class SentenceTransformerAdapter:
    """Lazy sentence-transformers adapter with candidate-specific prefixes."""

    def __init__(
        self,
        candidate: EmbeddingCandidate,
        *,
        device: str | None,
        offline: bool,
        model_factory: Any | None = None,
    ) -> None:
        self.candidate = candidate
        self.dimension = candidate.dimension
        self.device = device
        self.offline = offline
        self._model_factory = model_factory
        self._model: Any | None = None

    def prepare_queries(self, texts: list[str]) -> list[str]:
        if not self.candidate.requires_e5_prefix:
            return list(texts)
        return [text if text.startswith("query: ") else f"query: {text}" for text in texts]

    def prepare_passages(self, texts: list[str]) -> list[str]:
        if not self.candidate.requires_e5_prefix:
            return list(texts)
        return [text if text.startswith("passage: ") else f"passage: {text}" for text in texts]

    def _load_model(self) -> Any:
        if self._model is not None:
            return self._model
        if self.offline:
            os.environ["HF_HUB_OFFLINE"] = "1"
            os.environ["TRANSFORMERS_OFFLINE"] = "1"
        if self._model_factory is not None:
            self._model = self._model_factory(self.candidate, self.device, self.offline)
            return self._model

        from sentence_transformers import SentenceTransformer

        kwargs: dict[str, Any] = {}
        if self.device:
            kwargs["device"] = self.device
        if self.offline:
            kwargs["local_files_only"] = True
        self._model = SentenceTransformer(self.candidate.model_name, **kwargs)
        return self._model

    def _encode(self, texts: list[str], *, kind: str) -> np.ndarray:
        prepared = self.prepare_queries(texts) if kind == "query" else self.prepare_passages(texts)
        model = self._load_model()
        embeddings = model.encode(
            prepared,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return normalize_embeddings(np.asarray(embeddings, dtype=np.float32))

    def embed_queries(self, texts: list[str]) -> np.ndarray:
        return self._encode(texts, kind="query")

    def embed_passages(self, texts: list[str]) -> np.ndarray:
        return self._encode(texts, kind="passage")

    def tokenize(self, text: str) -> list[int]:
        model = self._load_model()
        tokenizer = getattr(model, "tokenizer", None)
        if tokenizer is not None and hasattr(tokenizer, "encode"):
            return list(tokenizer.encode(text, verbose=False))
        tokenized = model.tokenize([text])
        input_ids = tokenized.get("input_ids")
        if input_ids is None:
            return list(range(len(text.split())))
        first = input_ids[0]
        if hasattr(first, "tolist"):
            return list(first.tolist())
        return list(first)
