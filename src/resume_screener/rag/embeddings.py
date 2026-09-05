"""Embedding helpers. OpenAI when a key is present; otherwise a local token-hash fallback."""

from __future__ import annotations

import hashlib
import math
import os
from typing import Sequence

from resume_screener.config import Settings

LOCAL_EMBEDDING_DIM = 64


def _l2_normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


def token_hash_embed(text: str, dim: int = LOCAL_EMBEDDING_DIM) -> list[float]:
    """Bag-of-tokens hashed into a fixed vector. Shared tokens land in the same bins."""
    vec = [0.0] * dim
    for raw in text.lower().replace("#", " ").replace("/", " ").split():
        token = "".join(ch for ch in raw if ch.isalnum() or ch in "-+")
        if not token:
            continue
        digest = hashlib.md5(token.encode("utf-8")).digest()
        idx = int.from_bytes(digest[:2], "little") % dim
        vec[idx] += 1.0
    return _l2_normalize(vec)


class LocalHashEmbeddingFunction:
    """Deterministic embeddings so ingest/query work without an API key."""

    def __init__(self, dim: int = LOCAL_EMBEDDING_DIM) -> None:
        self.dim = dim

    def name(self) -> str:
        return f"local-token-hash-{self.dim}"

    def __call__(self, input: Sequence[str]) -> list[list[float]]:
        return [token_hash_embed(text, dim=self.dim) for text in input]


class OpenAIEmbeddingFunction:
    def __init__(self, api_key: str, model: str) -> None:
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key)
        self._model = model

    def name(self) -> str:
        return f"openai:{self._model}"

    def __call__(self, input: Sequence[str]) -> list[list[float]]:
        texts = list(input)
        if not texts:
            return []
        response = self._client.embeddings.create(model=self._model, input=texts)
        by_index = {item.index: item.embedding for item in response.data}
        return [by_index[i] for i in range(len(texts))]


def embedding_function_for(settings: Settings):
    """Use OpenAI embeddings when configured; otherwise the local hash fallback."""
    use_local = os.getenv("RESUME_SCREENER_EMBEDDINGS", "").lower() == "local"
    if settings.openai_api_key and not use_local:
        return OpenAIEmbeddingFunction(
            api_key=settings.openai_api_key, model=settings.embedding_model
        )
    return LocalHashEmbeddingFunction()
