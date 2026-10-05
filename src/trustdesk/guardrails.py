"""Code-enforced checks on every draft. Pure functions, no I/O.

The model proposes an answer and quotes; this module decides what survives and how confident we are.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from .config import settings
from .llm import DraftAnswer
from .retrieve import Hit

_QUOTES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-"})


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).translate(_QUOTES).lower()
    text = re.sub(r"[*_`#>]", "", text)  # markdown emphasis shouldn't break a quote match
    return re.sub(r"\s+", " ", text).strip().strip(".").strip()


@dataclass
class VerifiedCitation:
    source: str
    doc: str
    section: str
    kind: str
    quote: str


@dataclass
class Checked:
    status: str  # "answered" | "needs_review"
    answer: str | None
    explanation: str
    confidence: str  # "high" | "medium" | "needs_review"
    citations: list[VerifiedCitation] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "status": self.status, "answer": self.answer, "explanation": self.explanation,
            "confidence": self.confidence, "problems": self.problems,
            "citations": [c.__dict__ for c in self.citations],
        }


def verify_citations(draft: DraftAnswer, hits: list[Hit],
                     min_chars: int | None = None) -> tuple[list[VerifiedCitation], list[str]]:
    min_chars = min_chars or settings.min_quote_chars
    by_id = {f"S{i}": h for i, h in enumerate(hits, 1)}
    good, problems = [], []
    for c in draft.citations:
        sid = c.source.strip().strip("[]").upper()
        hit = by_id.get(sid)
        if hit is None:
            problems.append(f"cited unknown source {c.source!r}")
            continue
        q = normalize(c.quote)
        if len(q) < min_chars:
            problems.append(f"quote from {sid} too short to verify")
            continue
        if q not in normalize(hit.chunk.text):
            problems.append(f"quote not found in {sid}")
            continue
        good.append(VerifiedCitation(sid, hit.chunk.doc, hit.chunk.section, hit.chunk.kind, c.quote.strip()))
    return good, problems


def check(draft: DraftAnswer, hits: list[Hit]) -> Checked:
    cites, problems = verify_citations(draft, hits)

    if draft.status == "insufficient_evidence" or draft.answer is None:
        return Checked("needs_review", None, draft.explanation or "Not covered by the indexed documents.",
                       "needs_review", cites, problems + ["model reported insufficient evidence"])
    if not cites:
        return Checked("needs_review", draft.answer, draft.explanation, "needs_review", [],
                       problems + ["no verifiable citation supports this answer"])

    from_policy = any(c.kind == "policy" for c in cites)
    if draft.answer in {"Yes", "No"} and from_policy and not problems:
        confidence = "high"
    else:
        confidence = "medium"
        if not from_policy:
            problems.append("supported only by past answers (may be stale); confirm against policy")
    return Checked("answered", draft.answer, draft.explanation, confidence, cites, problems)
