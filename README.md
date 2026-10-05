# 🛡️ TrustDesk

**A private assistant for security questionnaires.** Drop in a customer's security questionnaire.
TrustDesk drafts every answer from *your own* policies and past answers, cites the exact sentence it
relied on, and flags anything your documents don't support for a human to review. It runs entirely
on your laptop with open models in Ollama, so confidential security documents never leave your
machine.

```
Q: Do you support customer-managed encryption keys (BYOK)?
A: No   [High confidence]
   We do not currently support customer-managed keys; all keys are managed by us in AWS KMS.
   ↳ 03-encryption-policy.md › Customer-managed keys:
     "Harborline does not currently support customer-managed encryption keys (BYOK)."

Q: Is your platform FedRAMP authorized?
A: —    [Needs review]  Not covered by the indexed documents.
```

## Why

Before an enterprise customer signs, their security team sends a questionnaire of 100–400
questions. Answering one takes a security or sales engineer days of digging through policies, and
the same questions come back every time in new wording. AI can help, but the source material is
exactly the kind of document companies won't upload to a cloud model.

## How it works

```
policies (.md .pdf .docx) + past questionnaires
        │  section-aware chunking
        ▼
SQLite: keyword index (BM25) + embeddings (nomic-embed-text)
        │  for each question: hybrid search → top sources S1..S6
        ▼
local LLM (qwen3:8b) → JSON: {status, answer, explanation, citations[{source, quote}]}
        │
        ▼  guardrails (plain code, not the model)
  • every quote must appear word-for-word in the cited source
  • no verified citation → "Needs review", never "Yes"
  • confidence computed by code; answers backed only by old questionnaires capped at Medium
        ▼
review UI (approve / edit) → completed .xlsx → approved answers join the library
```

**The model drafts, code verifies, a human approves.** A confident wrong "Yes, we do that" to a
customer's security team is a real business and legal risk, so TrustDesk would rather say "I
don't know".

## Quick start (Apple Silicon, 16GB)

```bash
ollama pull qwen3:8b && ollama pull nomic-embed-text
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[ui,dev]"
trustdesk doctor
make test

make index                     # index the sample company "Harborline Software"
trustdesk ask "Do you support BYOK?"
make run                       # answer all 40 questions → acme_bank_2026_completed.xlsx
make ui                        # review, edit, approve, export
make eval                      # accuracy, citation accuracy, bluff rate
```

Use your own documents:
`trustdesk index path/to/policies --library past.xlsx --rebuild`, then
`trustdesk run their_questionnaire.xlsx`.

## Sample data

`sample_data/` contains a **fictional** company, Harborline Software:
- 10 policy documents
- one previously answered questionnaire, including a deliberately stale answer (backup retention
  of 30 days vs 35 in the current policy) to show why policies outrank past answers
- a 40-question customer questionnaire with ground truth: 30 answerable (Yes/No/Partial) and
  **10 the policies don't cover** (bug bounty, FedRAMP, WAF, cyber insurance…), which must come
  back as "Needs review"

For real-world practice, try the Cloud Security Alliance's free
[CAIQ v4](https://cloudsecurityalliance.org/artifacts/star-level-1-security-questionnaire-caiq-v4)
against open-source policy templates such as [StrongDM Comply](https://github.com/strongdm/comply).

## Evaluation

| Metric | What it means |
|---|---|
| Retrieval recall@k | the right policy is among the top-k sources |
| Answer accuracy | answerable questions answered correctly |
| Citation accuracy | answers that cite the right document with a verified quote |
| **Bluff rate** | unanswerable questions that got an answer anyway (want ≈ 0) |
| Over-caution | answerable questions sent to review |

Measured so far (offline, without an embedding model):

| Search mode | recall@1 | recall@3 | recall@5 |
|---|---|---|---|
| Keyword (BM25) | 97% | 100% | 100% |
| Hybrid (BM25 + stand-in embedder) | 93% | 100% | 100% |

With a perfect stand-in model, the full pipeline scores 100% accuracy and a 0% bluff rate, which
proves the guardrails and scoring work. Next, record the real models:

| Model | Answer accuracy | Citation accuracy | Bluff rate | s/question |
|---|---|---|---|---|
| qwen3:8b | | | | |
| gemma4 | | | | |

**Honest caveat:** the sample questions share vocabulary with the sample policies. Real
questionnaires word things differently ("joiner-mover-leaver process" vs "termination"), which is
where hybrid search and the embedding model earn their keep. Add paraphrased questions to
`sample_data/eval/questions.jsonl` to stress-test that.

## Roadmap

See [`spec.md`](spec.md): near-duplicate question grouping, a reranker experiment, and a
"policy gap report" that turns every Needs-review question into a to-do for your security team.
