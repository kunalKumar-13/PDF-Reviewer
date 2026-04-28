"""Lightweight vector store using scikit-learn TF-IDF + cosine similarity.

No C++ compilation required — works out of the box on Windows.
Each document gets its own index stored as a pickle file on disk.

How it works:
1. Text chunks are vectorized using TF-IDF (term frequency–inverse document frequency)
2. Queries are vectorized with the same fitted vectorizer
3. Cosine similarity finds the most relevant chunks
4. Results include page number and section metadata for citations
"""

import os
import pickle
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

import config
from pdf_processor import TextChunk


# In-memory cache of loaded document indexes
_indexes: dict[str, dict] = {}


def _get_store_path(document_id: str) -> str:
    """Get the file path for a document's index."""
    os.makedirs(config.STORE_DIR, exist_ok=True)
    return os.path.join(config.STORE_DIR, f"{document_id}.pkl")


def _load_index(document_id: str) -> dict | None:
    """Load a document index from disk into memory."""
    if document_id in _indexes:
        return _indexes[document_id]

    store_path = _get_store_path(document_id)
    if os.path.exists(store_path):
        with open(store_path, "rb") as f:
            index = pickle.load(f)
        _indexes[document_id] = index
        return index

    return None


def _save_index(document_id: str, index: dict) -> None:
    """Save a document index to disk and cache in memory."""
    store_path = _get_store_path(document_id)
    with open(store_path, "wb") as f:
        pickle.dump(index, f)
    _indexes[document_id] = index


def store_chunks(chunks: list[TextChunk]) -> int:
    """Store text chunks by building a TF-IDF index.

    Args:
        chunks: List of TextChunk objects from pdf_processor.

    Returns:
        Number of chunks stored.
    """
    if not chunks:
        return 0

    document_id = chunks[0].document_id

    # Extract texts and metadata
    texts = [c.text for c in chunks]
    metadata = [
        {
            "chunk_id": c.chunk_id,
            "page_number": c.page_number,
            "section": c.section,
            "document_id": c.document_id,
            "text": c.text,
        }
        for c in chunks
    ]

    # Fit TF-IDF vectorizer on the document chunks
    vectorizer = TfidfVectorizer(
        stop_words="english",
        max_features=10000,
        ngram_range=(1, 2),  # unigrams + bigrams for better matching
    )
    tfidf_matrix = vectorizer.fit_transform(texts)

    # Build and save the index
    index = {
        "vectorizer": vectorizer,
        "tfidf_matrix": tfidf_matrix,
        "metadata": metadata,
        "document_id": document_id,
    }
    _save_index(document_id, index)

    return len(chunks)


def query_chunks(
    document_id: str,
    query_text: str,
    top_k: int = config.TOP_K_RESULTS,
) -> list[dict]:
    """Retrieve the most relevant chunks for a query.

    Args:
        document_id: Which document to search within.
        query_text: The user's question.
        top_k: Number of results to return.

    Returns:
        List of dicts with 'text', 'page_number', 'section', 'distance'.
    """
    index = _load_index(document_id)
    if index is None:
        return []

    vectorizer = index["vectorizer"]
    tfidf_matrix = index["tfidf_matrix"]
    metadata = index["metadata"]

    # Vectorize the query using the same fitted vectorizer
    query_vec = vectorizer.transform([query_text])

    # Compute cosine similarity between query and all chunks
    similarities = cosine_similarity(query_vec, tfidf_matrix).flatten()

    # Get top-k indices sorted by similarity (highest first)
    top_indices = np.argsort(similarities)[::-1][:top_k]

    results = []
    for idx in top_indices:
        score = float(similarities[idx])
        if score > 0.0:  # Only include chunks with some relevance
            meta = metadata[idx]
            results.append({
                "text": meta["text"],
                "page_number": meta["page_number"],
                "section": meta["section"],
                "distance": 1.0 - score,  # Convert similarity to distance
            })

    return results


def delete_document(document_id: str) -> bool:
    """Delete a document's index from disk and memory.

    Args:
        document_id: The document to remove.

    Returns:
        True if deletion succeeded.
    """
    try:
        # Remove from memory
        if document_id in _indexes:
            del _indexes[document_id]

        # Remove from disk
        store_path = _get_store_path(document_id)
        if os.path.exists(store_path):
            os.remove(store_path)

        return True
    except Exception:
        return False


def document_exists(document_id: str) -> bool:
    """Check if a document has been indexed."""
    if document_id in _indexes:
        return True

    store_path = _get_store_path(document_id)
    return os.path.exists(store_path)
