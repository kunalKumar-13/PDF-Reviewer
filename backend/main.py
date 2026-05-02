"""FastAPI application — PDFChat backend.

Endpoints:
  POST /api/upload     — Upload and process a PDF
  POST /api/chat       — Ask a question about the uploaded PDF
  GET  /api/health     — Health check
  DELETE /api/document — Delete a processed document
"""

import asyncio

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

import config
from models import (
    UploadResponse,
    ChatRequest,
    ChatResponse,
    Citation,
    HealthResponse,
)
import pdf_processor
import vector_store
import chat_engine

# --- App Setup ---

app = FastAPI(
    title="PDFChat API",
    description="PDF-Constrained Conversational Agent — ask questions grounded in your PDF.",
    version="1.0.0",
)

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        *config.FRONTEND_ORIGINS,
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ],
    allow_origin_regex=config.CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Endpoints ---

@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="ok",
        message="PDFChat API is running",
    )


@app.post("/api/upload", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    """Upload a PDF file for processing.

    The PDF is:
    1. Saved to disk
    2. Text extracted page-by-page with PyMuPDF
    3. Chunked into overlapping segments with page metadata
    4. Embedded and stored in ChromaDB

    Returns the document_id needed for subsequent chat requests.
    """
    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are accepted.",
        )

    # Read file content
    content = await file.read()

    # Validate file size
    size_mb = len(content) / (1024 * 1024)
    if size_mb > config.MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {config.MAX_FILE_SIZE_MB}MB.",
        )

    # Validate it's actually a PDF (check magic bytes)
    if not content[:5] == b"%PDF-":
        raise HTTPException(
            status_code=400,
            detail="Invalid PDF file.",
        )

    try:
        cached = pdf_processor.get_cached_document(content)
        if cached and vector_store.document_exists(cached["document_id"]):
            stats = vector_store.get_document_stats(cached["document_id"]) or {}
            total_chunks = stats.get("total_chunks", cached.get("total_chunks", 0))
            return UploadResponse(
                status="success",
                message=(
                    f"PDF loaded from cache. {cached['total_pages']} pages, "
                    f"{total_chunks} chunks indexed."
                ),
                document_id=cached["document_id"],
                total_pages=cached["total_pages"],
                total_chunks=total_chunks,
            )

        # Process the PDF: extract → chunk → embed
        document_id, chunks, total_pages = await asyncio.to_thread(
            pdf_processor.process_pdf,
            content,
            file.filename,
            cached["document_id"] if cached else None,
        )

        # Store chunks in vector database
        total_chunks = await asyncio.to_thread(vector_store.store_chunks, chunks)

        return UploadResponse(
            status="success",
            message=f"PDF processed successfully. {total_pages} pages, {total_chunks} chunks indexed.",
            document_id=document_id,
            total_pages=total_pages,
            total_chunks=total_chunks,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process PDF: {str(e)}",
        )


@app.post("/api/chat", response_model=ChatResponse)
async def chat_with_pdf(request: ChatRequest):
    """Ask a question about an uploaded PDF.

    The question is:
    1. Used to retrieve relevant chunks from ChromaDB
    2. Passed to Groq with a grounded system prompt
    3. Answered with citations or a clean refusal

    Requires a valid document_id from a prior upload.
    """
    if not request.question.strip():
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty.",
        )

    if not vector_store.document_exists(request.document_id):
        raise HTTPException(
            status_code=404,
            detail="Document not found. Please upload a PDF first.",
        )

    try:
        result = await asyncio.to_thread(
            chat_engine.chat,
            question=request.question,
            document_id=request.document_id,
            session_id=request.session_id,
        )

        return ChatResponse(
            answer=result["answer"],
            citations=[
                Citation(
                    page=c["page"],
                    section=c.get("section"),
                    text_snippet=c["text_snippet"],
                )
                for c in result["citations"]
            ],
            session_id=result["session_id"],
            is_refusal=result["is_refusal"],
            debug=result.get("debug"),
        )

    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Chat error: {str(e)}",
        )


@app.delete("/api/document/{document_id}")
async def delete_document(document_id: str):
    """Delete a processed document and its chunks from the vector store."""
    deleted = vector_store.delete_document(document_id)
    if deleted:
        pdf_processor.delete_document_files(document_id)
        return {"status": "ok", "message": "Document deleted."}
    else:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )


@app.get("/api/document/{document_id}/pdf")
async def serve_pdf(document_id: str):
    """Serve the uploaded PDF file for the frontend viewer."""
    file_path = pdf_processor.get_pdf_path(document_id)
    if not file_path:
        raise HTTPException(
            status_code=404,
            detail="PDF file not found.",
        )
    return FileResponse(
        file_path,
        media_type="application/pdf",
        headers={"Content-Disposition": "inline"},
    )


# --- Main ---

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=config.HOST,
        port=config.PORT,
        reload=True,
    )
