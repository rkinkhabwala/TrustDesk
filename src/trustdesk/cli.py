"""TrustDesk command line.

  trustdesk doctor
  trustdesk index sample_data/policies --library sample_data/past_questionnaires/2025_customer_questionnaire.csv
  trustdesk ask "Do you support BYOK?"
  trustdesk run sample_data/questionnaires/acme_bank_2026.xlsx      # draft every answer, export xlsx
  trustdesk eval sample_data/eval/questions.jsonl [--retrieval-only] [--mode keyword|vector|hybrid]
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import typer

from .answer import Engine
from .config import settings
from .embed import make_embedder
from .evaluate import load_gold, retrieval_recall
from .evaluate import run as run_eval
from .questionnaire import answers_for_export, read_questions, write_completed
from .store import Store

app = typer.Typer(add_completion=False, help="Private security questionnaire assistant (local Ollama).")


def _engine(with_llm: bool = True, embedder: str = "ollama", model: str | None = None,
            mode: str = "hybrid", db: Path | None = None) -> Engine:
    llm = None
    if with_llm:
        from .llm import OllamaLLM

        llm = OllamaLLM(model)
    return Engine(Store(db or settings.db_path), make_embedder(embedder), llm, mode=mode)


@app.callback()
def _main(verbose: bool = typer.Option(False, "-v", "--verbose")):
    logging.basicConfig(level=logging.INFO if verbose else logging.WARNING, format="%(message)s")


@app.command()
def doctor():
    """Check Ollama and the configured models."""
    from ollama import Client

    try:
        have = {m.model for m in Client(host=settings.ollama_host).list().models}
    except Exception as e:  # noqa: BLE001
        typer.secho(f"✗ Ollama not reachable at {settings.ollama_host}: {e}", fg="red")
        raise typer.Exit(1)
    typer.secho(f"✓ Ollama at {settings.ollama_host}", fg="green")
    ok = True
    for m in (settings.llm_model, settings.embed_model):
        present = m in have or f"{m}:latest" in have
        ok &= present
        typer.secho(f"{'✓' if present else '✗'} {m}" + ("" if present else f"  → ollama pull {m}"),
                    fg="green" if present else "red")
    raise typer.Exit(0 if ok else 1)


@app.command()
def index(
    policies: Path = typer.Argument(None, help="Folder of policy documents (.md .txt .pdf .docx)"),
    library: list[Path] = typer.Option([], help="Past answered questionnaires (.csv/.xlsx); repeatable"),
    rebuild: bool = typer.Option(False, help="Drop the existing index first"),
    embedder: str = typer.Option("ollama", help="ollama | hash (offline, lower quality)"),
):
    """Index policies and past answers."""
    stats = _engine(False, embedder).index(policies, library, rebuild)
    typer.echo(json.dumps(stats, indent=2))


@app.command()
def ask(question: str, embedder: str = "ollama", model: str = typer.Option(None)):
    """Answer one question and show the evidence."""
    eng = _engine(True, embedder, model)
    checked, hits = eng.ask(question)
    color = {"high": "green", "medium": "yellow", "needs_review": "red"}[checked.confidence]
    typer.secho(f"{checked.answer or '—'}  [{checked.confidence}]", fg=color, bold=True)
    typer.echo(checked.explanation)
    for c in checked.citations:
        typer.echo(f"  ↳ {c.doc} › {c.section}: \"{c.quote}\"")
    for p in checked.problems:
        typer.secho(f"  ! {p}", fg="yellow")
    typer.echo("\nRetrieved: " + ", ".join(f"S{i} {h.chunk.label}" for i, h in enumerate(hits, 1)))


@app.command()
def run(
    questionnaire: Path,
    out: Path = typer.Option(None, help="Output path (default: <name>_completed.xlsx)"),
    embedder: str = "ollama",
    model: str = typer.Option(None),
    resume: bool = typer.Option(True, help="Skip questions already drafted for this questionnaire"),
):
    """Draft answers for a whole questionnaire and export a completed copy."""
    eng = _engine(True, embedder, model)
    qs = read_questions(questionnaire)
    name = questionnaire.name
    todo = [q for q in qs if not (resume and eng.store.has_draft(name, q.qid))]
    typer.echo(f"{len(qs)} questions, {len(todo)} to draft with {eng.llm.name}")
    with typer.progressbar(todo, label="Drafting") as bar:
        for q in bar:
            checked, _ = eng.ask(q.text)
            eng.store.save_draft(name, q.qid, q.text, checked.to_dict())
    out_path = export(questionnaire, out, db=None)
    _print_counts(eng.store.answers(name))
    typer.echo(f"Wrote {out_path}. Review with:  streamlit run src/trustdesk/app.py")


@app.command()
def export(questionnaire: Path, out: Path = typer.Option(None), db: Path = typer.Option(None)) -> Path:
    """Export the current drafts/approvals for a questionnaire."""
    store = Store(db or settings.db_path)
    answers = answers_for_export(store.answers(questionnaire.name))
    out = out or questionnaire.with_name(questionnaire.stem + "_completed" + questionnaire.suffix)
    path = write_completed(questionnaire, out, answers)
    typer.echo(f"Exported {path}")
    return path


def _print_counts(rows: list[dict]) -> None:
    from collections import Counter

    c = Counter(r["draft"]["confidence"] for r in rows)
    typer.echo(f"High: {c['high']}   Medium: {c['medium']}   Needs review: {c['needs_review']}")


@app.command("eval")
def evaluate(
    gold: Path,
    retrieval_only: bool = typer.Option(False, help="Only measure retrieval (no LLM)"),
    mode: str = typer.Option("hybrid", help="hybrid | keyword | vector"),
    embedder: str = "ollama",
    model: str = typer.Option(None),
    limit: int = typer.Option(None),
    tag: str = typer.Option(None),
):
    """Score retrieval and answers against ground truth."""
    g = load_gold(gold)
    eng = _engine(not retrieval_only, embedder, model, mode)
    report: dict = {"mode": mode, "embedder": eng.embedder.name, "retrieval": retrieval_recall(eng, g)}
    typer.echo("Retrieval: " + "  ".join(f"{k}={v:.0%}" for k, v in report["retrieval"].items()))
    if not retrieval_only:
        res = run_eval(eng, g, limit)
        report["llm"] = eng.llm.name
        report["answers"] = res.summary()
        s = report["answers"]
        typer.echo(f"Answer accuracy {s['answer_accuracy']:.0%}   Citation accuracy {s['citation_accuracy']:.0%}   "
                   f"Bluff rate {s['bluff_rate']:.0%}   Over-caution {s['over_caution_rate']:.0%}   "
                   f"High-confidence wrong {s['high_confidence_wrong']}   {s['sec_per_question']:.1f}s/question")
        for r in res.rows:
            ok = (r["status"] == "needs_review") if r["expected"] == "UNANSWERABLE" else (r["answer"] == r["expected"])
            if not ok:
                typer.secho(f"  ✗ {r['id']} expected {r['expected']}, got {r['answer'] or 'needs review'}: "
                            f"{r['question']}", fg="yellow")
        report["rows"] = res.rows
    Path("results").mkdir(exist_ok=True)
    tag = tag or f"{mode}_{eng.embedder.name}_{(eng.llm.name if eng.llm else 'retrieval')}".replace(":", "-")
    Path(f"results/{tag}.json").write_text(json.dumps(report, indent=2))
    typer.echo(f"Saved results/{tag}.json")


if __name__ == "__main__":
    app()
