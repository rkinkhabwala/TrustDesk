"""Read questionnaires (xlsx/csv) and write completed copies.

Column detection is heuristic: the header row is the first row with a cell starting with
"question"; the ID column is the first header containing "ref", "id" or "#". The original workbook
is preserved; TrustDesk appends its own columns so nothing the customer wrote is overwritten.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

OUT_COLUMNS = ["TrustDesk Answer", "Explanation", "Sources", "Confidence", "Review Status"]


@dataclass
class Question:
    qid: str
    text: str
    row: int  # 1-based worksheet row (xlsx) or data row index (csv)


def _find_header(rows: list[list]) -> tuple[int, int, int | None]:
    for i, r in enumerate(rows):
        cells = [str(c or "").strip().lower() for c in r]
        q_col = next((j for j, c in enumerate(cells) if c.startswith("question")), None)
        if q_col is not None:
            id_col = next((j for j, c in enumerate(cells)
                           if j != q_col and (c in {"#", "id", "no", "no."} or "ref" in c or c.endswith(" id"))), None)
            return i, q_col, id_col
    raise ValueError("Couldn't find a header row with a 'Question' column")


def read_questions(path: Path) -> list[Question]:
    if path.suffix.lower() == ".csv":
        with path.open(newline="", encoding="utf-8-sig") as f:
            rows = list(csv.reader(f))
        offset = 0
    else:
        from openpyxl import load_workbook

        ws = load_workbook(path, data_only=True).active
        rows = [list(r) for r in ws.iter_rows(values_only=True)]
        offset = 1
    h, q_col, id_col = _find_header(rows)
    out = []
    for i, r in enumerate(rows[h + 1:], start=h + 1):
        text = str(r[q_col] or "").strip() if q_col < len(r) else ""
        if not text:
            continue
        qid = str(r[id_col]).strip() if id_col is not None and id_col < len(r) and r[id_col] else f"row{i + offset}"
        out.append(Question(qid, text, i + offset))
    return out


def format_sources(citations: list[dict]) -> str:
    return "\n".join(f"{c['doc']} › {c['section']}: \"{c['quote']}\"" for c in citations)


def write_completed(src: Path, dst: Path, answers: dict[str, dict]) -> Path:
    """answers: qid -> {"answer","explanation","citations","confidence","review_status"}"""
    questions = read_questions(src)
    if src.suffix.lower() == ".csv":
        with src.open(newline="", encoding="utf-8-sig") as f:
            rows = list(csv.reader(f))
        h, _, _ = _find_header(rows)
        rows[h] = rows[h] + OUT_COLUMNS
        for q in questions:
            a = answers.get(q.qid, {})
            rows[q.row] = rows[q.row] + _values(a)
        dst = dst.with_suffix(".csv")
        with dst.open("w", newline="") as f:
            csv.writer(f).writerows(rows)
        return dst

    from openpyxl import load_workbook
    from openpyxl.styles import Alignment, Font, PatternFill

    wb = load_workbook(src)
    ws = wb.active
    rows = [list(r) for r in ws.iter_rows(values_only=True)]
    h, _, _ = _find_header(rows)
    first = ws.max_column + 1
    fills = {"high": "D9EAD3", "medium": "FFF2CC", "needs_review": "F4CCCC"}
    for j, name in enumerate(OUT_COLUMNS):
        cell = ws.cell(row=h + 1, column=first + j, value=name)
        cell.font = Font(bold=True)
        ws.column_dimensions[cell.column_letter].width = [14, 60, 60, 14, 16][j]
    for q in questions:
        a = answers.get(q.qid, {})
        for j, v in enumerate(_values(a)):
            cell = ws.cell(row=q.row, column=first + j, value=v)
            cell.alignment = Alignment(wrap_text=True, vertical="top")
        conf = a.get("confidence")
        if conf in fills:
            ws.cell(row=q.row, column=first + 3).fill = PatternFill("solid", fgColor=fills[conf])
    dst = dst.with_suffix(".xlsx")
    wb.save(dst)
    return dst


def _values(a: dict) -> list[str]:
    return [
        a.get("answer") or "",
        a.get("explanation") or "",
        format_sources(a.get("citations", [])),
        {"high": "High", "medium": "Medium", "needs_review": "Needs review"}.get(a.get("confidence", ""), ""),
        a.get("review_status", ""),
    ]


def answers_for_export(rows: list[dict]) -> dict[str, dict]:
    """Store rows → export payload. Approved edits win over the model's draft."""
    out = {}
    for r in rows:
        d, ok = r["draft"], r["status"] == "approved"
        out[r["qid"]] = {
            "answer": r["final_answer"] if ok else d["answer"],
            "explanation": r["final_explanation"] if ok else d["explanation"],
            "citations": d["citations"],
            "confidence": d["confidence"],
            "review_status": "Approved" if ok else ("Needs review" if d["status"] == "needs_review" else "Draft"),
        }
    return out
