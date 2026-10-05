"""The engine: index documents, answer a question, learn from approved answers."""
from __future__ import annotations

import logging
import time
from pathlib import Path

from .config import settings
from .embed import Embedder
from .guardrails import Checked, check
from .ingest import Chunk, _cid, collect
from .llm import LLM
from .prompts import SYSTEM, user_prompt
from .retrieve import Hit, Retriever
from .store import Store

log = logging.getLogger(__name__)


class Engine:
    def __init__(self, store: Store, embedder: Embedder, llm: LLM | None = None, k: int | None = None,
                 mode: str = "hybrid"):
        self.store, self.embedder, self.llm = store, embedder, llm
        self.k = k or settings.top_k
        self.retriever = Retriever(store, embedder, mode=mode)

    # ------------------------------------------------------------ indexing
    def index(self, policy_dir: Path | None, library: list[Path], rebuild: bool = False) -> dict:
        prev = self.store.get_meta("embedder")
        if prev and prev != self.embedder.name and not rebuild:
            raise RuntimeError(f"Index was built with {prev}, not {self.embedder.name}. Re-run with --rebuild.")
        if rebuild:
            self.store.clear()
        chunks = collect(policy_dir, library)
        start = time.perf_counter()
        vectors = self.embedder.embed_documents([f"{c.label}\n{c.text}" for c in chunks])
        added = self.store.add_chunks(chunks, vectors)
        self.store.set_meta("embedder", self.embedder.name)
        log.info("indexed %d new chunks in %.1fs", added, time.perf_counter() - start)
        return {"chunks_seen": len(chunks), "added": added, "totals": self.store.count()}

    def add_to_library(self, question: str, answer: str, explanation: str, source: str) -> None:
        text = f"Q: {question.strip()}\nA: {answer}. {explanation.strip()}".strip()
        chunk = Chunk(_cid(source, question, text), source, "approved answer", text, "library")
        self.store.add_chunks([chunk], self.embedder.embed_documents([f"{chunk.label}\n{text}"]))

    # ------------------------------------------------------------ answering
    def retrieve(self, question: str) -> list[Hit]:
        return self.retriever.search(question, self.k)

    def ask(self, question: str) -> tuple[Checked, list[Hit]]:
        if self.llm is None:
            raise RuntimeError("Engine has no LLM configured")
        hits = self.retrieve(question)
        if not hits:
            return Checked("needs_review", None, "Nothing relevant is indexed.", "needs_review",
                           problems=["no sources retrieved"]), hits
        draft = self.llm.draft(SYSTEM, user_prompt(question, hits))
        return check(draft, hits), hits
