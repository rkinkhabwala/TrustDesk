"""SQLite storage: chunks + FTS5 keyword index + embeddings, and the review/answer store.

One file (.trustdesk/index.db). Vectors are stored as float32 blobs and searched by brute-force
cosine similarity, which is instant for the few thousand chunks a policy set produces.
"""
from __future__ import annotations

import json
import re
import sqlite3
import time
from pathlib import Path

import numpy as np

from .ingest import Chunk

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS chunks (
    rowid INTEGER PRIMARY KEY,
    id TEXT UNIQUE, doc TEXT, section TEXT, text TEXT, kind TEXT, embedding BLOB
);
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    text, section, doc, content='chunks', content_rowid='rowid', tokenize='porter unicode61'
);
CREATE TABLE IF NOT EXISTS answers (
    questionnaire TEXT, qid TEXT, question TEXT, draft TEXT,
    final_answer TEXT, final_explanation TEXT, status TEXT, updated_at REAL,
    PRIMARY KEY (questionnaire, qid)
);
"""

STOPWORDS = set("""a an and are as at be by can do does for from has have how in is it its of on or
our that the their this to was we what when where which who will with you your yes no""".split())


class Store:
    def __init__(self, path: Path | str):
        path = Path(path)
        if str(path) != ":memory:":
            path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(path), check_same_thread=False)
        self.db.executescript(SCHEMA)
        self._matrix: np.ndarray | None = None
        self._ids: list[str] = []

    # ------------------------------------------------------------ meta
    def get_meta(self, key: str) -> str | None:
        row = self.db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return row[0] if row else None

    def set_meta(self, key: str, value: str) -> None:
        self.db.execute("INSERT OR REPLACE INTO meta VALUES (?, ?)", (key, value))
        self.db.commit()

    # ------------------------------------------------------------ chunks
    def add_chunks(self, chunks: list[Chunk], vectors: np.ndarray) -> int:
        added = 0
        for c, v in zip(chunks, vectors):
            cur = self.db.execute(
                "INSERT OR IGNORE INTO chunks (id, doc, section, text, kind, embedding) VALUES (?,?,?,?,?,?)",
                (c.id, c.doc, c.section, c.text, c.kind, np.asarray(v, dtype=np.float32).tobytes()),
            )
            if cur.rowcount:
                self.db.execute("INSERT INTO chunks_fts(rowid, text, section, doc) VALUES (?,?,?,?)",
                                (cur.lastrowid, c.text, c.section, c.doc))
                added += 1
        self.db.commit()
        self._matrix = None
        return added

    def clear(self) -> None:
        self.db.execute("INSERT INTO chunks_fts(chunks_fts) VALUES ('delete-all')")
        self.db.execute("DELETE FROM chunks")
        self.db.commit()
        self._matrix = None

    def count(self) -> dict[str, int]:
        return dict(self.db.execute("SELECT kind, COUNT(*) FROM chunks GROUP BY kind").fetchall())

    def get(self, ids: list[str]) -> list[Chunk]:
        if not ids:
            return []
        q = f"SELECT id, doc, section, text, kind FROM chunks WHERE id IN ({','.join('?' * len(ids))})"
        by_id = {r[0]: Chunk(*r) for r in self.db.execute(q, ids)}
        return [by_id[i] for i in ids if i in by_id]

    def keyword_search(self, query: str, k: int) -> list[str]:
        words = [w for w in re.findall(r"[A-Za-z0-9]+", query.lower()) if w not in STOPWORDS and len(w) > 1]
        if not words:
            return []
        match = " OR ".join(f'"{w}"' for w in dict.fromkeys(words))
        rows = self.db.execute(
            "SELECT c.id FROM chunks_fts f JOIN chunks c ON c.rowid = f.rowid "
            "WHERE chunks_fts MATCH ? ORDER BY bm25(chunks_fts) LIMIT ?", (match, k)).fetchall()
        return [r[0] for r in rows]

    def vector_search(self, qvec: np.ndarray, k: int) -> list[tuple[str, float]]:
        if self._matrix is None:
            rows = self.db.execute("SELECT id, embedding FROM chunks").fetchall()
            self._ids = [r[0] for r in rows]
            self._matrix = (np.stack([np.frombuffer(r[1], dtype=np.float32) for r in rows])
                            if rows else np.zeros((0, len(qvec)), dtype=np.float32))
        if not self._ids:
            return []
        sims = self._matrix @ qvec.astype(np.float32)
        top = np.argsort(-sims)[:k]
        return [(self._ids[i], float(sims[i])) for i in top]

    # ------------------------------------------------------------ answers
    def save_draft(self, questionnaire: str, qid: str, question: str, draft: dict) -> None:
        self.db.execute(
            "INSERT INTO answers (questionnaire, qid, question, draft, status, updated_at) VALUES (?,?,?,?,?,?) "
            "ON CONFLICT(questionnaire, qid) DO UPDATE SET question=excluded.question, draft=excluded.draft, "
            "status=CASE WHEN answers.status='approved' THEN 'approved' ELSE excluded.status END, "
            "updated_at=excluded.updated_at",
            (questionnaire, qid, question, json.dumps(draft), "draft", time.time()))
        self.db.commit()

    def approve(self, questionnaire: str, qid: str, answer: str, explanation: str) -> None:
        self.db.execute(
            "UPDATE answers SET final_answer=?, final_explanation=?, status='approved', updated_at=? "
            "WHERE questionnaire=? AND qid=?", (answer, explanation, time.time(), questionnaire, qid))
        self.db.commit()

    def answers(self, questionnaire: str) -> list[dict]:
        rows = self.db.execute(
            "SELECT qid, question, draft, final_answer, final_explanation, status FROM answers "
            "WHERE questionnaire=? ORDER BY rowid", (questionnaire,)).fetchall()
        return [{"qid": r[0], "question": r[1], "draft": json.loads(r[2]), "final_answer": r[3],
                 "final_explanation": r[4], "status": r[5]} for r in rows]

    def has_draft(self, questionnaire: str, qid: str) -> bool:
        return self.db.execute("SELECT 1 FROM answers WHERE questionnaire=? AND qid=?",
                               (questionnaire, qid)).fetchone() is not None
