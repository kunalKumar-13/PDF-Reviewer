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
import re
import numpy as np
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

import config
from pdf_processor import TextChunk


# In-memory cache of loaded document indexes
_indexes: dict[str, dict] = {}


def _keyword_terms(text: str) -> set[str]:
    """Extract normalized content terms used for deterministic reranking."""
    terms = {
        term
        for term in re.findall(r"[A-Za-z0-9]{3,}", text.lower())
        if term not in ENGLISH_STOP_WORDS
    }
    return terms


def _with_compact_aliases(text: str) -> str:
    """Add no-space aliases so 'Ojas Sinha' can match 'OJASSINHA'."""
    aliases = []
    for line in text.splitlines():
        tokens = re.findall(r"[A-Za-z0-9]+", line)
        if 2 <= len(tokens) <= 8:
            compact = "".join(tokens)
            if len(compact) >= 6:
                aliases.append(compact)

    return " ".join([text, *aliases])


def _keyword_overlap(query_terms: set[str], text: str) -> float:
    """Score how many query keywords appear in a chunk."""
    if not query_terms:
        return 0.0

    chunk_terms = _keyword_terms(text)
    if not chunk_terms:
        return 0.0

    return len(query_terms & chunk_terms) / len(query_terms)


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
    texts = [_with_compact_aliases(c.text) for c in chunks]
    metadata = [
        {
            "chunk_id": c.chunk_id,
            "chunk_index": idx,
            "page_number": c.page_number,
            "section": c.section,
            "document_id": c.document_id,
            "text": c.text,
        }
        for idx, c in enumerate(chunks)
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


def _merge_adjacent_chunks(chunks: list[dict]) -> list[dict]:
    """Merge selected adjacent chunks from the same page into one context block."""
    if not chunks:
        return []

    ordered = sorted(chunks, key=lambda item: item["chunk_index"])
    merged: list[dict] = []

    for chunk in ordered:
        if (
            merged
            and chunk["page_number"] == merged[-1]["page_number"]
            and chunk["chunk_index"] == merged[-1]["end_chunk_index"] + 1
        ):
            merged[-1]["text"] = f"{merged[-1]['text']}\n{chunk['text']}"
            merged[-1]["end_chunk_index"] = chunk["chunk_index"]
            merged[-1]["similarity"] = max(merged[-1]["similarity"], chunk["similarity"])
            merged[-1]["distance"] = 1.0 - merged[-1]["similarity"]
            merged[-1]["keyword_overlap"] = max(
                merged[-1]["keyword_overlap"],
                chunk["keyword_overlap"],
            )
            merged[-1]["combined_score"] = max(
                merged[-1]["combined_score"],
                chunk["combined_score"],
            )
            if not merged[-1].get("section") and chunk.get("section"):
                merged[-1]["section"] = chunk["section"]
            continue

        merged.append({
            **chunk,
            "end_chunk_index": chunk["chunk_index"],
        })

    return sorted(merged, key=lambda item: item["combined_score"], reverse=True)


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
    search_query = _with_compact_aliases(query_text)
    query_vec = vectorizer.transform([search_query])

    # Compute cosine similarity between query and all chunks
    similarities = cosine_similarity(query_vec, tfidf_matrix).flatten()

    # Pull a wider candidate set, then rerank deterministically by similarity
    # plus direct keyword overlap with the standalone query.
    candidate_count = min(
        len(metadata),
        max(top_k, top_k * config.RETRIEVAL_CANDIDATE_MULTIPLIER),
    )
    top_indices = np.argsort(similarities)[::-1][:candidate_count]
    query_terms = _keyword_terms(search_query)

    candidates = []
    for idx in top_indices:
        score = float(similarities[idx])
        meta = metadata[idx]
        overlap = _keyword_overlap(query_terms, _with_compact_aliases(meta["text"]))

        if score < config.MIN_SIMILARITY_SCORE and overlap == 0.0:
            continue

        combined_score = score + (overlap * config.KEYWORD_OVERLAP_WEIGHT)
        candidates.append({
            "text": meta["text"],
            "page_number": meta["page_number"],
            "section": meta["section"],
            "chunk_id": meta["chunk_id"],
            "chunk_index": meta.get("chunk_index", int(idx)),
            "similarity": score,
            "distance": 1.0 - score,  # Convert similarity to distance
            "keyword_overlap": overlap,
            "combined_score": combined_score,
        })

    candidates.sort(key=lambda item: item["combined_score"], reverse=True)
    selected = candidates[:top_k]

    return _merge_adjacent_chunks(selected)[:top_k]


def get_document_stats(document_id: str) -> dict | None:
    """Return lightweight index stats for cached upload responses."""
    index = _load_index(document_id)
    if index is None:
        return None

    return {
        "document_id": document_id,
        "total_chunks": len(index["metadata"]),
    }


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
