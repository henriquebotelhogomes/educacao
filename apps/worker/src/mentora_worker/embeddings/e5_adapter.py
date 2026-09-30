"""E5 multilingual-small embeddings adapter (ADR-021)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# ADR-021 prefixes
_PASSAGE_PREFIX = "passage: "
_QUERY_PREFIX = "query: "


class E5Embedder:
    """Wraps ``intfloat/multilingual-e5-small`` for passage and query encoding.

    The SentenceTransformer model is lazy-loaded on first use so that importing
    this module does not block the worker startup with a model download.
    """

    def __init__(
        self,
        model_name: str = "intfloat/multilingual-e5-small",
        batch_size: int = 32,
    ) -> None:
        self._model_name = model_name
        self._batch_size = batch_size
        self._model_instance: SentenceTransformer | None = None

    @property
    def _model(self) -> "SentenceTransformer":
        """Lazy-load and cache the SentenceTransformer model."""
        if self._model_instance is None:
            from sentence_transformers import SentenceTransformer

            logger.info("Loading embedding model '%s'…", self._model_name)
            self._model_instance = SentenceTransformer(self._model_name)
        return self._model_instance

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        """Encode *texts* as passage embeddings (prefix: ``passage: ``).

        Processes in batches of ``batch_size`` to control memory usage.
        """
        prefixed = [f"{_PASSAGE_PREFIX}{t}" for t in texts]
        embeddings: list[list[float]] = []
        for i in range(0, len(prefixed), self._batch_size):
            batch = prefixed[i : i + self._batch_size]
            vecs = self._model.encode(batch, convert_to_numpy=True)
            embeddings.extend(v.tolist() for v in vecs)
        return embeddings

    def embed_query(self, text: str) -> list[float]:
        """Encode a single query string (prefix: ``query: ``)."""
        prefixed = f"{_QUERY_PREFIX}{text}"
        vec = self._model.encode([prefixed], convert_to_numpy=True)
        return cast(list[float], vec[0].tolist())
