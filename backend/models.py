"""Pydantic models for API request/response schemas."""

from pydantic import BaseModel
from typing import Optional


# --- PDF Upload ---

class UploadResponse(BaseModel):
    """Response after a PDF is uploaded and processed."""
    status: str
    message: str
    document_id: str
    total_pages: int
    total_chunks: int


# --- Chat ---

class ChatRequest(BaseModel):
    """Incoming chat question from the user."""
    question: str
    document_id: str
    session_id: Optional[str] = None


class Citation(BaseModel):
    """A single citation pointing to a source location in the PDF."""
    page: int
    section: Optional[str] = None
    text_snippet: str


class DebugChunk(BaseModel):
    """Retrieved chunk metadata shown in the frontend debug panel."""
    page: int
    section: Optional[str] = None
    similarity: float
    keyword_overlap: float
    combined_score: float
    text_snippet: str


class ChatDebug(BaseModel):
    """Observability payload for one chat turn."""
    rewritten_query: str
    retrieved_chunks: list[DebugChunk]


class ChatResponse(BaseModel):
    """Agent response with grounded answer and citations."""
    answer: str
    citations: list[Citation]
    session_id: str
    is_refusal: bool = False
    debug: Optional[ChatDebug] = None


# --- Status ---

class HealthResponse(BaseModel):
    status: str
    message: str
