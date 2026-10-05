"""Review UI:  streamlit run src/trustdesk/app.py"""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from trustdesk.answer import Engine
from trustdesk.config import settings
from trustdesk.embed import make_embedder
from trustdesk.llm import OllamaLLM
from trustdesk.questionnaire import answers_for_export, read_questions, write_completed
from trustdesk.store import Store

st.set_page_config(page_title="TrustDesk", page_icon="🛡️", layout="wide")
UPLOADS = settings.db_path.parent / "uploads"
UPLOADS.mkdir(parents=True, exist_ok=True)


@st.cache_resource
def engine() -> Engine:
    return Engine(Store(settings.db_path), make_embedder("ollama"), OllamaLLM())


eng = engine()
st.title("🛡️ TrustDesk")
st.caption(f"Security questionnaires answered from your own documents · {settings.llm_model} via Ollama · "
           "nothing leaves this machine")

with st.sidebar:
    st.subheader("Knowledge base")
    counts = eng.store.count()
    st.write(f"Policy chunks: **{counts.get('policy', 0)}** · Library answers: **{counts.get('library', 0)}**")
    if st.button("Index sample company (Harborline)"):
        with st.spinner("Embedding documents…"):
            eng.index(Path("sample_data/policies"),
                      [Path("sample_data/past_questionnaires/2025_customer_questionnaire.csv")])
        st.rerun()
    show = st.multiselect("Show", ["high", "medium", "needs_review"], default=["medium", "needs_review"],
                          format_func={"high": "High confidence", "medium": "Medium",
                                       "needs_review": "Needs review"}.get)

upload = st.file_uploader("Questionnaire (.xlsx or .csv)", type=["xlsx", "csv"])
if not upload:
    st.info("Upload a questionnaire to start. Try sample_data/questionnaires/acme_bank_2026.xlsx.")
    st.stop()

path = UPLOADS / upload.name
path.write_bytes(upload.getvalue())
questions = read_questions(path)
existing = {a["qid"]: a for a in eng.store.answers(upload.name)}
pending = [q for q in questions if q.qid not in existing]

c1, c2 = st.columns([3, 1])
c1.write(f"**{len(questions)}** questions · **{len(existing)}** drafted · **{len(pending)}** remaining")
if pending and c2.button(f"Draft {len(pending)} answers", type="primary"):
    bar = st.progress(0.0)
    for i, q in enumerate(pending, 1):
        checked, _ = eng.ask(q.text)
        eng.store.save_draft(upload.name, q.qid, q.text, checked.to_dict())
        bar.progress(i / len(pending), text=f"{i}/{len(pending)}: {q.text[:70]}")
    st.rerun()

rows = eng.store.answers(upload.name)
if not rows:
    st.stop()

approved = sum(r["status"] == "approved" for r in rows)
conf = [r["draft"]["confidence"] for r in rows]
m = st.columns(4)
m[0].metric("High confidence", conf.count("high"))
m[1].metric("Medium", conf.count("medium"))
m[2].metric("Needs review", conf.count("needs_review"))
m[3].metric("Approved", f"{approved}/{len(rows)}")

icon = {"high": "🟢", "medium": "🟡", "needs_review": "🔴"}
for r in rows:
    d = r["draft"]
    if d["confidence"] not in show and r["status"] != "approved":
        continue
    done = " ✅" if r["status"] == "approved" else ""
    with st.expander(f"{icon[d['confidence']]} {r['qid']} · {r['question']}{done}"):
        options = ["Yes", "No", "Partial", "N/A"]
        current = r["final_answer"] or d["answer"]
        ans = st.selectbox("Answer", options, index=options.index(current) if current in options else 0,
                           key=f"a-{r['qid']}")
        exp = st.text_area("Explanation", r["final_explanation"] or d["explanation"], key=f"e-{r['qid']}")
        for c in d["citations"]:
            st.markdown(f"> {c['quote']}  \n— *{c['doc']} › {c['section']}*")
        for p in d["problems"]:
            st.warning(p)
        if st.button("Approve", key=f"ok-{r['qid']}"):
            eng.store.approve(upload.name, r["qid"], ans, exp)
            eng.add_to_library(r["question"], ans, exp, source=f"approved:{upload.name}")
            st.rerun()

if st.button("Export completed questionnaire"):
    answers = answers_for_export(eng.store.answers(upload.name))
    out = write_completed(path, UPLOADS / f"{path.stem}_completed{path.suffix}", answers)
    st.download_button("Download", out.read_bytes(), file_name=out.name)
