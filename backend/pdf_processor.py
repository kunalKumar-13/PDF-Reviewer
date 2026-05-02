"""PDF text extraction and chunking with page-level metadata.

Uses PyMuPDF (fitz) to extract text from each page, then splits
into overlapping chunks while preserving the source page number
for citation accuracy.
"""

import fitz  # PyMuPDF
import hashlib
import json
import os
import re
import uuid
from dataclasses import dataclass

import config


CACHE_FILE = os.path.join(config.UPLOAD_DIR, "_pdf_cache.json")
CACHE_VERSION = 2


@dataclass
class TextChunk:
    """A chunk of text with its source metadata."""
    chunk_id: str
    text: str
    page_number: int
    section: str | None
    document_id: str


def _rebuild_spaced_word_line(words: list[tuple]) -> str:
    """Rebuild lines exported as one-letter 'words' into readable words."""
    if len(words) < 4:
        return " ".join(word[4] for word in words)

    single_letter_words = [
        word for word in words if len(word[4]) == 1 and word[4].isalpha()
    ]
    if len(single_letter_words) / len(words) < 0.5:
        return " ".join(word[4] for word in words)

    gaps = [
        max(0.0, words[i + 1][0] - words[i][2])
        for i in range(len(words) - 1)
        if len(words[i][4]) == 1 and len(words[i + 1][4]) == 1
    ]
    positive_gaps = sorted(gap for gap in gaps if gap > 0)
    median_gap = positive_gaps[len(positive_gaps) // 2] if positive_gaps else 0.0
    word_gap = max(median_gap * 1.8, 4.0)

    rebuilt: list[str] = []
    current = ""

    for index, word in enumerate(words):
        text = word[4].strip()
        if not text:
            continue

        if len(text) == 1 and text.isalpha():
            current += text
        else:
            if current:
                rebuilt.append(current)
                current = ""
            rebuilt.append(text)

        is_last = index == len(words) - 1
        if not is_last and current:
            next_word = words[index + 1]
            next_text = next_word[4].strip()
            gap = max(0.0, next_word[0] - word[2])
            if not (len(next_text) == 1 and next_text.isalpha()) or gap > word_gap:
                rebuilt.append(current)
                current = ""

    if current:
        rebuilt.append(current)

    return " ".join(rebuilt)


def _extract_page_text(page) -> str:
    """Extract readable page text, repairing spaced resume headings."""
    raw_words = page.get_text("words", sort=True)
    if not raw_words:
        return page.get_text("text").strip()

    lines: dict[tuple[int, int], list[tuple]] = {}
    for word in raw_words:
        block_no = int(word[5])
        line_no = int(word[6])
        lines.setdefault((block_no, line_no), []).append(word)

    page_lines = []
    for key in sorted(lines):
        line_words = sorted(lines[key], key=lambda word: word[0])
        line_text = _rebuild_spaced_word_line(line_words)
        if line_text:
            page_lines.append(line_text)

    return "\n".join(page_lines).strip()


def extract_pages(pdf_path: str) -> list[dict]:
    """Extract text from each page of a PDF.

    Args:
        pdf_path: Path to the PDF file on disk.

    Returns:
        List of dicts with 'page_number' (1-indexed) and 'text'.
    """
    doc = fitz.open(pdf_path)
    pages = []

    try:
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = _extract_page_text(page)

            if text.strip():
                pages.append({
                    "page_number": page_num + 1,  # 1-indexed for citations
                    "text": text.strip(),
                })
    finally:
        doc.close()

    return pages


def _detect_section(text: str) -> str | None:
    """Try to detect a section heading from the beginning of a chunk.

    Looks for common heading patterns: lines in ALL CAPS, lines starting
    with numbers like '1.2', or short bold-looking lines.
    """
    lines = text.strip().split("\n")
    if not lines:
        return None

    first_line = lines[0].strip()

    # Skip very long lines — unlikely to be headings
    if len(first_line) > 80:
        return None

    # Pattern: numbered heading (e.g., "1.2 Introduction")
    if re.match(r"^\d+(\.\d+)*\s+\w", first_line):
        return first_line

    # Pattern: ALL CAPS heading
    if first_line.isupper() and len(first_line) > 3:
        return first_line

    # Pattern: Title Case short line (likely heading)
    if first_line.istitle() and len(first_line) < 60 and len(lines) > 1:
        return first_line

    return None


def chunk_pages(
    pages: list[dict],
    document_id: str,
    chunk_size: int = config.CHUNK_SIZE,
    chunk_overlap: int = config.CHUNK_OVERLAP,
) -> list[TextChunk]:
    """Split page texts into overlapping chunks with page metadata.

    Each chunk retains a reference to its source page number for citation
    purposes. When a chunk spans a page boundary, it is attributed to the
    page where it starts.

    Args:
        pages: Output from extract_pages().
        document_id: Unique identifier for this document.
        chunk_size: Maximum characters per chunk.
        chunk_overlap: Overlap between consecutive chunks.

    Returns:
        List of TextChunk objects ready for embedding.
    """
    chunks: list[TextChunk] = []

    for page_data in pages:
        page_num = page_data["page_number"]
        text = page_data["text"]

        # Split the page text into chunks
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk_text = text[start:end]

            # Try to break at sentence boundary
            if end < len(text):
                last_period = chunk_text.rfind(". ")
                last_newline = chunk_text.rfind("\n")
                break_point = max(last_period, last_newline)

                if break_point > chunk_size * 0.3:
                    chunk_text = chunk_text[: break_point + 1]
                    end = start + break_point + 1

            if chunk_text.strip():
                section = _detect_section(chunk_text)
                chunks.append(
                    TextChunk(
                        chunk_id=str(uuid.uuid4()),
                        text=chunk_text.strip(),
                        page_number=page_num,
                        section=section,
                        document_id=document_id,
                    )
                )

            start = end - chunk_overlap
            if start < 0:
                start = 0
            # Prevent infinite loop on very small texts
            if end >= len(text):
                break

    return chunks


def _safe_filename(filename: str) -> str:
    """Return a filesystem-safe version of the uploaded filename."""
    return re.sub(r"[^A-Za-z0-9._-]", "_", filename)


def get_content_hash(file_content: bytes) -> str:
    """Stable hash used to identify already-processed PDFs."""
    return hashlib.sha256(file_content).hexdigest()


def _load_cache() -> dict:
    """Load the upload cache registry from disk."""
    if not os.path.exists(CACHE_FILE):
        return {}

    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_cache(cache: dict) -> None:
    """Persist the upload cache registry."""
    os.makedirs(config.UPLOAD_DIR, exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)


def get_cached_document(file_content: bytes) -> dict | None:
    """Return cache metadata for a previously processed PDF, if available."""
    content_hash = get_content_hash(file_content)
    cached = _load_cache().get(content_hash)

    if not cached or cached.get("cache_version") != CACHE_VERSION:
        return None

    file_path = cached.get("file_path")
    if not file_path or not os.path.exists(file_path):
        return None

    return cached


def save_uploaded_pdf(
    file_content: bytes,
    filename: str,
    document_id: str | None = None,
) -> tuple[str, str]:
    """Save an uploaded PDF to disk and return (document_id, file_path).

    Args:
        file_content: Raw bytes of the uploaded PDF.
        filename: Original filename.

    Returns:
        Tuple of (document_id, saved_file_path).
    """
    os.makedirs(config.UPLOAD_DIR, exist_ok=True)
    document_id = document_id or str(uuid.uuid4())
    safe_name = f"{document_id}_{_safe_filename(filename)}"
    file_path = os.path.join(config.UPLOAD_DIR, safe_name)

    with open(file_path, "wb") as f:
        f.write(file_content)

    return document_id, file_path


def process_pdf(
    file_content: bytes,
    filename: str,
    document_id: str | None = None,
) -> tuple[str, list[TextChunk], int]:
    """Full pipeline: save PDF → extract pages → chunk text.

    Args:
        file_content: Raw bytes of the uploaded PDF.
        filename: Original filename.

    Returns:
        Tuple of (document_id, chunks, total_pages).
    """
    content_hash = get_content_hash(file_content)
    document_id, file_path = save_uploaded_pdf(file_content, filename, document_id)

    try:
        pages = extract_pages(file_path)
        total_pages = len(pages)
        chunks = chunk_pages(pages, document_id)
        cache = _load_cache()
        cache[content_hash] = {
            "cache_version": CACHE_VERSION,
            "document_id": document_id,
            "file_path": file_path,
            "filename": filename,
            "total_pages": total_pages,
            "total_chunks": len(chunks),
        }
        _save_cache(cache)
        return document_id, chunks, total_pages
    except Exception as e:
        # Clean up file on failure
        if os.path.exists(file_path):
            os.remove(file_path)
        raise e


def get_pdf_path(document_id: str) -> str | None:
    """Find the saved PDF file path for a given document_id.

    Args:
        document_id: The document ID returned from process_pdf().

    Returns:
        Absolute path to the PDF file, or None if not found.
    """
    if not os.path.exists(config.UPLOAD_DIR):
        return None

    for filename in os.listdir(config.UPLOAD_DIR):
        if filename.startswith(document_id):
            return os.path.join(config.UPLOAD_DIR, filename)

    return None


def delete_document_files(document_id: str) -> None:
    """Remove saved PDFs and cache entries for a document."""
    if os.path.exists(config.UPLOAD_DIR):
        for filename in os.listdir(config.UPLOAD_DIR):
            if filename.startswith(document_id):
                os.remove(os.path.join(config.UPLOAD_DIR, filename))

    cache = _load_cache()
    filtered = {
        content_hash: metadata
        for content_hash, metadata in cache.items()
        if metadata.get("document_id") != document_id
    }
    if filtered != cache:
        _save_cache(filtered)

