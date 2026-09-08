import numpy as np
import os
import logging

from src.config import get_settings

logger = logging.getLogger(__name__)


def load_documents(doc_folder: str) -> list:
    documents = []
    for filename in os.listdir(doc_folder):
        if filename.endswith('.txt'):
            file_path = os.path.join(doc_folder, filename)
            with open(file_path, 'r') as f:
                content = f.read()
                documents.append({"filename": filename, "content": content})
            logger.info(f"Loaded document: {filename}")
    return documents

def split_into_chunks(documents: list) -> list:
    all_chunks = []
    for doc in documents:
        paragraphs = doc["content"].split('\n\n')
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            # if len(paragraph) > 50:  # This threshold can be adjusted based on your needs
            if len(paragraph.split()) >= 5:
                all_chunks.append({"filename": doc["filename"], "content": paragraph})
    return all_chunks


class RagIndex:
    """Owns the embedding model, FAISS index, and chunk store as instance
    state instead of module globals. The SentenceTransformer is constructed
    lazily in _get_model() on first actual use (build or retrieve), not at
    import time — importing this module (or anything that imports it, e.g.
    every agent) no longer pays the ~35s model-load cost just to run."""

    def __init__(self, settings=None):
        self._settings = settings if settings is not None else get_settings()
        self._model = None
        self.index = None
        self.chunks = []

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading embedding model: {self._settings.embedding_model}")
            self._model = SentenceTransformer(self._settings.embedding_model)
        return self._model

    def build_index(self, doc_folder: str) -> None:
        import faiss

        logger.info("Building FAISS index")

        documents = load_documents(doc_folder)
        self.chunks = split_into_chunks(documents)

        logger.info(f"Total chunks created: {len(self.chunks)}")

        if not self.chunks:
            # No documents to index (e.g. docs/ is empty between Phase 4's
            # RAG cleanup and Phase 4b's real corpus). encode([]) returns a
            # shape with no second axis, so `.shape[1]` below would crash —
            # this used to be unreachable when docs/ always had content,
            # but isn't anymore. self.index stays None, and
            # retrieve_context()'s existing "index not built yet" guard
            # already returns "" safely for that case.
            logger.warning(f"No documents found in {doc_folder} — RAG index left empty")
            self.index = None
            return

        embeddings = self._get_model().encode([chunk["content"] for chunk in self.chunks])
        embeddings = np.array(embeddings).astype('float32')
        logger.info(f"Embeddings generated with shape: {embeddings.shape}")

        dimension = embeddings.shape[1]
        index = faiss.IndexFlatL2(dimension)  # Euclidean distance index best for small datasets, can switch to IndexIVFFlat for larger datasets
        index.add(embeddings)
        self.index = index

        logger.info(f"FAISS index built with {self.index.ntotal} vectors")

    def retrieve_context(self, question: str, top_k: int = None) -> str:
        if top_k is None:
            top_k = self._settings.rag_top_k

        if self.index is None:
            logger.warning("FAISS index not built yet")
            return ""

        question_embedding = self._get_model().encode([question])
        question_embedding = np.array(question_embedding).astype('float32')

        distances, indices = self.index.search(question_embedding, top_k)

        relevant_chunks = []
        for i, distance in zip(indices[0], distances[0]):
            if 0 <= i < len(self.chunks) and distance < self._settings.rag_distance_threshold:
                relevant_chunks.append(self.chunks[i]["content"])

        return "\n\n".join(relevant_chunks)


_rag_index = None


def _get_rag_index() -> RagIndex:
    global _rag_index
    if _rag_index is None:
        _rag_index = RagIndex()
    return _rag_index


def build_index(doc_folder: str) -> None:
    _get_rag_index().build_index(doc_folder)


def retrieve_context(question: str, top_k: int = None) -> str:
    return _get_rag_index().retrieve_context(question, top_k)