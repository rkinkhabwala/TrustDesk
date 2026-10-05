"""Evaluation against a ground-truth question set (jsonl: id, question, expected, expected_doc).

expected is "Yes" | "No" | "Partial" | "UNANSWERABLE". UNANSWERABLE questions should end up in
Needs review; answering them is a bluff.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from .answer import Engine


def load_gold(path: Path) -> list[dict]:
    return [json.loads(line) for line in Path(path).open() if line.strip()]


def retrieval_recall(engine: Engine, gold: list[dict], ks: tuple[int, ...] = (1, 3, 5)) -> dict[str, float]:
    answerable = [g for g in gold if g["expected_doc"]]
    out = {}
    hits_by_q = {g["id"]: [h.chunk.doc for h in engine.retriever.search(g["question"], max(ks))] for g in answerable}
    for k in ks:
        found = sum(g["expected_doc"] in hits_by_q[g["id"]][:k] for g in answerable)
        out[f"recall@{k}"] = found / len(answerable) if answerable else 0.0
    return out


@dataclass
class EvalResult:
    rows: list[dict] = field(default_factory=list)
    seconds: float = 0.0

    def summary(self) -> dict:
        answerable = [r for r in self.rows if r["expected"] != "UNANSWERABLE"]
        unanswerable = [r for r in self.rows if r["expected"] == "UNANSWERABLE"]
        answered = [r for r in answerable if r["status"] == "answered"]

        def rate(xs, pred):
            return sum(1 for x in xs if pred(x)) / len(xs) if xs else 0.0

        return {
            "questions": len(self.rows),
            "answer_accuracy": rate(answerable, lambda r: r["status"] == "answered" and r["answer"] == r["expected"]),
            "citation_accuracy": rate(answered, lambda r: r["expected_doc"] in r["cited_docs"]),
            "bluff_rate": rate(unanswerable, lambda r: r["status"] == "answered"),
            "over_caution_rate": rate(answerable, lambda r: r["status"] == "needs_review"),
            "high_confidence_wrong": sum(1 for r in self.rows if r["confidence"] == "high"
                                         and (r["expected"] == "UNANSWERABLE" or r["answer"] != r["expected"])),
            "sec_per_question": self.seconds / len(self.rows) if self.rows else 0.0,
        }


def run(engine: Engine, gold: list[dict], limit: int | None = None) -> EvalResult:
    res = EvalResult()
    for g in gold[:limit]:
        start = time.perf_counter()
        checked, _ = engine.ask(g["question"])
        res.seconds += time.perf_counter() - start
        res.rows.append({
            "id": g["id"], "question": g["question"], "expected": g["expected"], "expected_doc": g["expected_doc"],
            "status": checked.status, "answer": checked.answer, "confidence": checked.confidence,
            "cited_docs": sorted({c.doc for c in checked.citations}), "problems": checked.problems,
            "explanation": checked.explanation,
        })
    return res
