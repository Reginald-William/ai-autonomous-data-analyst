"""
Tests for the paragraph-chunking logic in src/services/rag_service.py —
split_into_chunks(). load_documents() (folder-of-.txt-files loading) was
removed in Phase 4b along with the global docs/-based RAG index — RAG is now
built per-session from one uploaded document's text, via
build_session_index(), not a folder scan. See PHASES.md Phase 4b.

split_into_chunks() itself is unchanged and still pure (no FAISS, no
embeddings) — it just operates on an in-memory list of
{filename, content} dicts now, whether that list came from a folder scan
(old) or a single uploaded document wrapped in a list (new).
"""
from src.services.rag_service import split_into_chunks


def test_split_into_chunks_keeps_paragraphs_with_five_or_more_words():
    documents = [{
        "filename": "doc.txt",
        "content": "This paragraph clearly has more than five words in it.",
    }]

    chunks = split_into_chunks(documents)

    assert len(chunks) == 1
    assert chunks[0]["filename"] == "doc.txt"


def test_split_into_chunks_drops_paragraphs_with_fewer_than_five_words():
    documents = [{"filename": "doc.txt", "content": "Too short."}]

    assert split_into_chunks(documents) == []


def test_split_into_chunks_keeps_exactly_five_words():
    documents = [{"filename": "doc.txt", "content": "One two three four five"}]

    chunks = split_into_chunks(documents)

    assert len(chunks) == 1


def test_split_into_chunks_splits_on_blank_lines_into_separate_chunks():
    content = (
        "This is the first paragraph with plenty of words.\n\n"
        "This is the second paragraph also with plenty of words."
    )
    documents = [{"filename": "doc.txt", "content": content}]

    chunks = split_into_chunks(documents)

    assert len(chunks) == 2
    assert all(chunk["filename"] == "doc.txt" for chunk in chunks)


def test_split_into_chunks_handles_multiple_documents():
    documents = [
        {"filename": "a.txt", "content": "This paragraph has enough words to survive."},
        {"filename": "b.txt", "content": "This one also has enough words to survive."},
    ]

    chunks = split_into_chunks(documents)

    filenames = {chunk["filename"] for chunk in chunks}
    assert filenames == {"a.txt", "b.txt"}


def test_split_into_chunks_returns_empty_list_when_all_paragraphs_too_short():
    documents = [{"filename": "doc.txt", "content": "Short.\n\nAlso short.\n\nStill short."}]

    assert split_into_chunks(documents) == []
