import faiss
import numpy as np
import os
import logging
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# Load embedding model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Global FAISS index and chunk storage
index = None
chunks = []

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

def build_index(doc_folder: str):
    global index, chunks
    
    logger.info("Building FAISS index")
    
    documents = load_documents(doc_folder)
    chunks = split_into_chunks(documents)
    
    logger.info(f"Total chunks created: {len(chunks)}")
    
    embeddings = model.encode([chunk["content"] for chunk in chunks])  # Batch encoding for efficiency instead of loop encoding
    embeddings = np.array(embeddings).astype('float32')
    logger.info(f"Embeddings generated with shape: {embeddings.shape}")
    
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)  # Euclidean distance index best for small datasets, can switch to IndexIVFFlat for larger datasets
    index.add(embeddings)
    
    logger.info(f"FAISS index built with {index.ntotal} vectors")

def retrieve_context(question: str, top_k: int = 3) -> str:  #  we retrieve the 3 most relevant chunks (refer notes)
    global index, chunks
    
    if index is None:
        logger.warning("FAISS index not built yet")
        return ""
    
    question_embedding = model.encode([question])
    question_embedding = np.array(question_embedding).astype('float32')
    
    distances, indices = index.search(question_embedding, top_k)
    
    relevant_chunks = []
    for i, distance in zip(indices[0], distances[0]):
        if 0 <= i < len(chunks) and distance < 1.5:  # Distance threshold can be tuned based on your dataset and needs (refer notes)
            relevant_chunks.append(chunks[i]["content"])
    
    context = "\n\n".join(relevant_chunks)    
    return context