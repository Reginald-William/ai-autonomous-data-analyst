"""
Tests for the per-session RAG mechanism added in Phase 4b —
build_session_index(), retrieve_session_context(), and drop_session() in
src/services/rag_service.py. These replaced the Phase 1-4 global,
docs/-folder-based RagIndex singleton (see PHASES.md Phase 4b): RAG is now
built on demand from one user-uploaded business-context document, scoped to
that document's session_id only.

RagIndex._get_model() is monkeypatched to a small deterministic fake encoder
instead of loading the real ~35s SentenceTransformer — these tests care about
session isolation and empty/no-index behavior, not real embedding quality.
The fake encoder is a tiny bag-of-words vector over a fixed vocabulary, which
is enough to make "the chunk mentioning X" reliably the nearest neighbor for
"a question mentioning X" under FAISS's real L2 search.
"""
import numpy as np
import pytest

from src.services.rag_service import (
    RagIndex,
    build_session_index,
    retrieve_session_context,
    drop_session,
    _session_indexes,
)

VOCAB = ["won", "fiscal", "revenue", "closed", "april", "unrelated"]


def _fake_encode(texts):
    vectors = []
    for text in texts:
        lowered = text.lower()
        vectors.append([lowered.count(word) for word in VOCAB])
    return np.array(vectors, dtype="float32")


class _FakeModel:
    def encode(self, texts):
        return _fake_encode(texts)


@pytest.fixture(autouse=True)
def fake_embedding_model(monkeypatch):
    monkeypatch.setattr(RagIndex, "_get_model", lambda self: _FakeModel())
    yield
    _session_indexes.clear()


def test_retrieve_session_context_returns_empty_string_when_no_index_exists():
    assert retrieve_session_context("no-such-session", "What does won mean?") == ""


def test_build_session_index_then_retrieve_returns_relevant_chunk():
    build_session_index(
        "session-a",
        "In our pipeline, won means a closed-deal, not just a signed contract.\n\n"
        "This paragraph is unrelated filler text about something else entirely.",
    )

    result = retrieve_session_context("session-a", "What does won mean in our data?")

    assert "closed-deal" in result


def test_retrieve_session_context_isolates_sessions():
    build_session_index(
        "session-a",
        "In our pipeline, won means a closed-deal for session A only.",
    )
    build_session_index(
        "session-b",
        "Our fiscal year starts in April, not January, for session B only.",
    )

    result_a = retrieve_session_context("session-a", "What does won mean?")
    result_b = retrieve_session_context("session-b", "When does the fiscal year start?")

    assert "session A" in result_a
    assert "session B" not in result_a
    assert "session B" in result_b
    assert "session A" not in result_b


def test_session_with_no_context_document_gets_empty_string_even_after_others_build():
    build_session_index("session-a", "In our pipeline, won means a closed-deal.")

    # session-c never uploaded a context document — must never see session-a's data
    assert retrieve_session_context("session-c", "What does won mean?") == ""


def test_build_session_index_with_no_usable_chunks_leaves_retrieval_empty():
    # Every paragraph is under the 5-word chunking threshold
    build_session_index("session-a", "Too short.\n\nAlso short.")

    assert retrieve_session_context("session-a", "anything") == ""


def test_drop_session_removes_the_index():
    build_session_index("session-a", "In our pipeline, won means a closed-deal for real.")
    assert retrieve_session_context("session-a", "What does won mean?") != ""

    drop_session("session-a")

    assert retrieve_session_context("session-a", "What does won mean?") == ""


def test_drop_session_is_a_no_op_for_a_session_with_no_index():
    drop_session("never-built-anything")  # must not raise
