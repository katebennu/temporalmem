from __future__ import annotations

from functools import cached_property

from .config import settings


class Embedder:
    """Local embeddings via sentence-transformers. Model loads lazily on first use."""

    def __init__(self, model_name: str = settings.embedding_model):
        self.model_name = model_name

    @cached_property
    def model(self):
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer(self.model_name)

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors = self.model.encode(texts, normalize_embeddings=True)
        return [vector.tolist() for vector in vectors]

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]
