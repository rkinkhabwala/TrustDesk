"""Hybrid retrieval: BM25 keyword search + vector search, merged with reciprocal rank fusion.

Keyword search catches exact terms ("SOC 2", "BYOK", "TLS 1.2"); vector search catches paraphrases
("revoked when someone leaves" ↔ "access is revoked within 24 hours of their last working day").
"""
from __future__ import annotations

from dataclasses import dataclass

from .embed import Embedder
from .ingest import Chunk
from .store import Store


@dataclass
class Hit:
    chunk: Chunk
    score: float
    similarity: float | None = None  # cosine similarity from vector search, if found there


def rrf(rankings: list[list[str]], k: int = 60) -> dict[str, float]:
    """Reciprocal rank fusion: score = Σ 1 / (k + rank). Robust to incomparable score scales."""
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, cid in enumerate(ranking, 1):
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
    return scores


class Retriever:
    def __init__(self, store: Store, embedder: Embedder, mode: str = "hybrid", candidates: int = 20):
        assert mode in {"hybrid", "keyword", "vector"}
        self.store, self.embedder, self.mode, self.candidates = store, embedder, mode, candidates

    def search(self, query: str, k: int = 6) -> list[Hit]:
        rankings: list[list[str]] = []
        sims: dict[str, float] = {}
        if self.mode in {"hybrid", "vector"}:
            vec = self.store.vector_search(self.embedder.embed_query(query), self.candidates)
            sims = dict(vec)
            rankings.append([cid for cid, _ in vec])
        if self.mode in {"hybrid", "keyword"}:
            rankings.append(self.store.keyword_search(query, self.candidates))
        fused = sorted(rrf(rankings).items(), key=lambda x: -x[1])[:k]
        chunks = {c.id: c for c in self.store.get([cid for cid, _ in fused])}
        return [Hit(chunks[cid], score, sims.get(cid)) for cid, score in fused if cid in chunks]
