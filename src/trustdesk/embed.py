"""Embedders: Ollama for real use, a deterministic hashing embedder for tests and offline runs."""
from __future__ import annotations

import hashlib
import re
from typing import Protocol

import numpy as np

from .config import settings


class Embedder(Protocol):
    name: str

    def embed_documents(self, texts: list[str]) -> np.ndarray: ...

    def embed_query(self, text: str) -> np.ndarray: ...


def _normalize(m: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(m, axis=-1, keepdims=True)
    return m / np.where(norms == 0, 1, norms)


class OllamaEmbedder:
    """nomic-embed-text expects task prefixes; other models just ignore them harmlessly."""

    def __init__(self, model: str | None = None, host: str | None = None, batch: int = 32):
        from ollama import Client

        self.model = model or settings.embed_model
        self.client = Client(host=host or settings.ollama_host)
        self.batch = batch
        self.name = f"ollama:{self.model}"
        self._prefix = "nomic" in self.model

    def _embed(self, texts: list[str]) -> np.ndarray:
        out = []
        for i in range(0, len(texts), self.batch):
            out += self.client.embed(model=self.model, input=texts[i:i + self.batch]).embeddings
        return _normalize(np.asarray(out, dtype=np.float32))

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        return self._embed([f"search_document: {t}" if self._prefix else t for t in texts])

    def embed_query(self, text: str) -> np.ndarray:
        return self._embed([f"search_query: {text}" if self._prefix else text])[0]


class HashEmbedder:
    """Bag of word unigrams + bigrams, hashed into a fixed vector. No model, fully deterministic."""

    name = "hash"

    def __init__(self, dim: int = 1024):
        self.dim = dim

    def _vec(self, text: str) -> np.ndarray:
        words = re.findall(r"[a-z0-9]+", text.lower())
        v = np.zeros(self.dim, dtype=np.float32)
        for tok in words + [f"{a}_{b}" for a, b in zip(words, words[1:])]:
            h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
            v[h % self.dim] += 1.0 if (h >> 64) % 2 else -1.0
        return v

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        return _normalize(np.stack([self._vec(t) for t in texts])) if texts else np.zeros((0, self.dim))

    def embed_query(self, text: str) -> np.ndarray:
        return _normalize(self._vec(text)[None])[0]


def make_embedder(kind: str = "ollama") -> Embedder:
    return HashEmbedder() if kind == "hash" else OllamaEmbedder()
