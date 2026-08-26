"""
Tests for the document-loading and paragraph-chunking logic in
src/services/rag_service.py — load_documents() and split_into_chunks().

These two functions are pure (no FAISS, no embeddings), but importing this
module still pays the ~35s SentenceTransformer load cost from line 10 of
rag_service.py, since Python has to run the whole file to get at any name
inside it. That's a Phase 2 concern (see PHASES.md risk #8), not something
fixed here — these tests use tmp_path so they never touch the real docs/
folder.
"""
from src.services.rag_service import load_documents, split_into_chunks


def test_load_documents_reads_txt_files(tmp_path):
    (tmp_path / "a.txt").write_text("Hello from file A.")
    (tmp_path / "b.txt").write_text("Hello from file B.")

    documents = load_documents(str(tmp_path))

    filenames = {doc["filename"] for doc in documents}
    assert filenames == {"a.txt", "b.txt"}


def test_load_documents_skips_non_txt_files(tmp_path):
    (tmp_path / "notes.txt").write_text("This should be loaded.")
    (tmp_path / "image.png").write_bytes(b"\x89PNG fake bytes")
    (tmp_path / "data.csv").write_text("col1,col2\n1,2\n")

    documents = load_documents(str(tmp_path))

    assert len(documents) == 1
    assert documents[0]["filename"] == "notes.txt"


def test_load_documents_returns_empty_list_for_empty_folder(tmp_path):
    assert load_documents(str(tmp_path)) == []


def test_load_documents_preserves_file_content(tmp_path):
    (tmp_path / "routing_rules.txt").write_text("Use python for calculations.")

    documents = load_documents(str(tmp_path))

    assert documents[0]["content"] == "Use python for calculations."


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
