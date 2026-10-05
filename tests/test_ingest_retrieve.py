from trustdesk.ingest import _split_long, chunk_markdown, load_library
from trustdesk.retrieve import Retriever, rrf

MD = """# Encryption Policy

Intro paragraph.

## Data at rest

All data is encrypted with AES-256.

## Customer-managed keys

We do not support BYOK.
"""


def test_chunks_carry_heading_path():
    chunks = chunk_markdown("enc.md", MD)
    assert [c.section for c in chunks] == ["Encryption Policy", "Encryption Policy > Data at rest",
                                           "Encryption Policy > Customer-managed keys"]
    assert chunks[2].label == "enc.md › Encryption Policy > Customer-managed keys"


def test_long_sections_are_split_without_losing_text():
    text = "\n\n".join(f"Paragraph {i} " + "word " * 60 for i in range(10))
    parts = _split_long(text, 900)
    assert all(len(p) <= 900 for p in parts)
    assert "".join(parts).replace("\n", "").replace(" ", "") == text.replace("\n", "").replace(" ", "")


def test_library_rows(sample):
    lib = load_library(sample / "past_questionnaires" / "2025_customer_questionnaire.csv")
    assert len(lib) == 12 and lib[0].kind == "library" and lib[0].text.startswith("Q: ")


def test_rrf_rewards_agreement():
    scores = rrf([["a", "b", "c"], ["b", "a", "d"]])
    assert max(scores, key=scores.get) in {"a", "b"}
    assert scores["a"] == scores["b"] > scores["c"] > 0


def test_index_is_idempotent(engine, sample):
    before = engine.store.count()
    stats = engine.index(sample / "policies", [sample / "past_questionnaires" / "2025_customer_questionnaire.csv"])
    assert stats["added"] == 0 and engine.store.count() == before


def test_keyword_search_finds_exact_terms(engine):
    ids = engine.store.keyword_search("Do you support BYOK customer-managed keys?", 3)
    docs = [c.doc for c in engine.store.get(ids)]
    assert docs[0] == "03-encryption-policy.md"


def test_hybrid_finds_expected_doc(engine):
    hits = Retriever(engine.store, engine.embedder).search("Is access removed when an employee leaves?", 5)
    assert "02-access-control-policy.md" in [h.chunk.doc for h in hits]
