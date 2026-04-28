"""PDF text extraction and chunking with page-level metadata.

Uses PyMuPDF (fitz) to extract text from each page, then splits
into overlapping chunks while preserving the source page number
for citation accuracy.
"""

import fitz  # PyMuPDF
import os
import uuid
import re
from dataclasses import dataclass

import config


@dataclass
class TextChunk:
    """A chunk of text with its source metadata."""
    chunk_id: str
    text: str
    page_number: int
    section: str | None
    document_id: str


def extract_pages(pdf_path: str) -> list[dict]:
    """Extract text from each page of a PDF.

    Args:
        pdf_path: Path to the PDF file on disk.

    Returns:
        List of dicts with 'page_number' (1-indexed) and 'text'.
    """
    doc = fitz.open(pdf_path)
    pages = []

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text = page.get_text("text")

        if text.strip():
            pages.append({
                "page_number": page_num + 1,  # 1-indexed for citations
                "text": text.strip(),
            })

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


def save_uploaded_pdf(file_content: bytes, filename: str) -> tuple[str, str]:
    """Save an uploaded PDF to disk and return (document_id, file_path).

    Args:
        file_content: Raw bytes of the uploaded PDF.
        filename: Original filename.

    Returns:
        Tuple of (document_id, saved_file_path).
    """
    os.makedirs(config.UPLOAD_DIR, exist_ok=True)
    document_id = str(uuid.uuid4())
    safe_name = f"{document_id}_{filename}"
    file_path = os.path.join(config.UPLOAD_DIR, safe_name)

    with open(file_path, "wb") as f:
        f.write(file_content)

    return document_id, file_path


def process_pdf(file_content: bytes, filename: str) -> tuple[str, list[TextChunk], int]:
    """Full pipeline: save PDF → extract pages → chunk text.

    Args:
        file_content: Raw bytes of the uploaded PDF.
        filename: Original filename.

    Returns:
        Tuple of (document_id, chunks, total_pages).
    """
    document_id, file_path = save_uploaded_pdf(file_content, filename)

    try:
        pages = extract_pages(file_path)
        total_pages = len(pages)
        chunks = chunk_pages(pages, document_id)
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

