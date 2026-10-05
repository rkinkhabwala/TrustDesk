# TrustDesk — Private Security Questionnaire Assistant

## 1. Problem

B2B companies must answer security questionnaires (CAIQ, SIG, custom spreadsheets of 100–400
questions) before customers will sign. Answers live in confidential internal documents: security
policies, audit summaries, architecture notes, past questionnaires. Today a security engineer or
sales engineer spends days per questionnaire, and many companies won't paste those documents into a
cloud AI.

TrustDesk drafts every answer **from the company's own documents, with citations**, flags anything
it can't support, and lets a human review and export. It runs entirely on a laptop with Ollama.

## 2. Goals / Non-goals

**Goals**
- 100% local: Ollama for generation and embeddings; SQLite for storage. No other network calls.
- Every drafted answer cites verbatim quotes from indexed sources; code verifies each quote.
- Unsupported questions become **Needs review**, never a confident "Yes".
- Human approval loop; approved answers feed a reusable answer library.
- Measured quality: retrieval recall, answer accuracy, citation accuracy and **bluff rate**.

**Non-goals (v1)**
- Portal integrations (OneTrust, Whistic, etc.); input/output is xlsx/csv.
- Multi-user auth. It's a single-user desktop tool.
- Legal attestation. Humans own what gets sent.

## 3. Hardware budget (M1 Pro, 16GB)

| Role | Model | Notes |
|---|---|---|
| Answering | `qwen3:8b` (default) or `gemma4` | ~5–7 GB, thinking disabled, JSON-schema output |
| Embeddings | `nomic-embed-text` | <0.5 GB, uses `search_query:` / `search_document:` prefixes |

A 250-question questionnaire takes roughly as long as 250 short generations, so it runs as a batch
with progress output, and results are saved as they complete so a run can resume.

## 4. Architecture

```
policies/*.md|pdf|docx ─┐                       ┌─► SQLite FTS5 (BM25 keyword search)
past questionnaires ────┴─► ingest: section-aware chunks ─┤
                                                         └─► embeddings (nomic-embed-text)
questionnaire.xlsx ─► for each question:
     hybrid search (BM25 + vector, reciprocal rank fusion) → top-k sources S1..Sk
     → LLM (JSON schema): {status, answer, explanation, citations[{source, quote}]}
     → guardrails (code): verify quotes, drop bad citations, compute confidence, downgrade
     → review store (SQLite) → Streamlit review → approve/edit → export xlsx
     → approved answers → answer library (indexed for next time)
```

Design principle: **the model drafts, code verifies, a human approves.**

## 5. Guardrails (all in code, `guardrails.py`)

1. A citation must reference a source ID that was actually provided (S1..Sk).
2. Its quote must appear in that source's text (case/whitespace/quote-mark normalized) and be at
   least 20 characters long.
3. Any answer other than `insufficient_evidence` needs ≥1 verified citation, or it's downgraded to
   **Needs review**.
4. Confidence is computed by code, not claimed by the model:
   - **high**: Yes/No answer with a verified quote from a *policy* document
   - **medium**: Partial answer, support only from past answers, or some citations failed
   - **needs_review**: everything else
5. Questionnaire text is treated as data: the system prompt instructs the model to ignore any
   instructions inside a question (prompt-injection hygiene for customer-supplied files).

Past answers can go stale, so policy documents are the source of truth. An answer supported only by
the library is capped at medium.

## 6. Data

`sample_data/` ships a fictional company, **Harborline Software**:
- `policies/`: 10 short policy documents (security program, access, encryption, IR, BC/DR,
  vendors, SDLC, privacy/retention, HR security, compliance).
- `past_questionnaires/2025_customer_questionnaire.csv`: 12 previously answered questions.
- `questionnaires/acme_bank_2026.xlsx`: 40 new questions.
- `eval/questions.jsonl`: ground truth for those 40, with the expected answer (Yes/No/Partial) and
  expected source document, including **10 unanswerable** questions the policies don't cover.

Real-world swap-ins: CSA CAIQ v4 (free from cloudsecurityalliance.org), plus open-source policy
templates (StrongDM Comply, SOC 2 template libraries) or your company's own documents.

## 7. Evaluation (`trustdesk eval`)

| Metric | Definition |
|---|---|
| Retrieval recall@k | expected document appears in the top-k sources (no LLM needed) |
| Answer accuracy | answerable questions answered with the expected value |
| Citation accuracy | answered questions with ≥1 verified quote from the expected document |
| **Bluff rate** | unanswerable questions given an answer instead of "Needs review" |
| Over-caution rate | answerable questions sent to "Needs review" |
| Seconds per question | wall clock |

Targets: recall@5 ≥ 0.9, answer accuracy ≥ 0.85, citation accuracy ≥ 0.85, bluff rate ≤ 0.10.

## 8. Phases

1. **Ingest + retrieval** with BM25/vector/hybrid comparison. (scaffolded)
2. **Answering + guardrails**, CLI questionnaire run, xlsx export. (scaffolded)
3. **Review UI + answer library** in Streamlit. (scaffolded)
4. **Eval**: compare `qwen3:8b` vs `gemma4`, and hybrid vs BM25-only vs vector-only.
5. **Polish**: question deduplication (answer near-duplicate questions once), reranker
   experiment, a "policy gap report" listing questions the documents can't answer.

## 9. Repo layout

```
src/trustdesk/  config.py ingest.py store.py embed.py llm.py retrieve.py prompts.py guardrails.py
                answer.py questionnaire.py evaluate.py cli.py app.py
sample_data/    policies/ past_questionnaires/ questionnaires/ eval/
tests/
```

## 10. Conventions (for Claude Code)

- Python 3.11+, type hints, Pydantic v2. Network calls only to the Ollama host.
- `guardrails.py` and `retrieve.py` fusion logic are pure and unit-tested.
- Tests use `HashEmbedder` and `FakeLLM`, so they never need Ollama.
- Prompts live in `prompts.py` only.
