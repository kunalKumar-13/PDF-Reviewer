# PDF Reviewer

PDF Reviewer is a full-stack PDF question-answering app. Upload a PDF, ask questions about it, and get grounded answers with page-level citations. The backend extracts and indexes the document locally, while the frontend gives users a clean chat interface with an integrated PDF viewer.

## What It Does

- Uploads and validates PDF files.
- Extracts text page by page with PyMuPDF.
- Splits document text into overlapping chunks with page and section metadata.
- Builds a local TF-IDF search index with scikit-learn.
- Retrieves the most relevant chunks for each question.
- Uses Groq to generate answers strictly from the retrieved PDF context.
- Returns citations for the pages used in each answer.
- Refuses to answer when the information is not present in the uploaded PDF.
- Supports short multi-turn chat sessions with backend memory.
- Rewrites follow-up questions into standalone retrieval queries.
- Reranks retrieved chunks by similarity and keyword overlap.
- Opens the uploaded PDF beside the chat and jumps to cited pages.
- Preserves grounding and citation structure when answering supported non-English questions from the PDF.

## Why This Project

PDF Reviewer is built for document-grounded review workflows where the assistant should answer from the uploaded file, cite the source pages, and refuse unsupported questions instead of guessing. It keeps the retrieval layer lightweight by using a local TF-IDF index, making the app simple to run without a hosted vector database.

## Agent Architecture

This is an AI agent workflow, not just a static JavaScript app. The React frontend handles upload, chat, citations, and PDF viewing. The FastAPI backend performs PDF extraction, retrieval, query rewriting, prompt construction, Groq LLM generation, refusal detection, and citation metadata assembly.

## RAG Query Pipeline

The chat flow is intentionally strict and document-grounded:

1. The frontend sends the user question with the current `document_id` and `session_id`.
2. The backend loads the recent session memory for follow-up context.
3. Short lookups and follow-up questions are rewritten into standalone retrieval queries.
4. The local TF-IDF index retrieves candidate chunks from the active PDF.
5. Retrieval reranks candidates by cosine similarity plus keyword overlap and filters weak matches.
6. If no reliable chunks are found, the backend returns the fixed refusal message without using outside knowledge.
7. Groq receives only the retrieved PDF excerpts, recent conversation turns, and strict grounding rules.
8. The backend normalizes the response, attaches page citations, and exposes retrieval debug metadata.
9. The frontend renders the grounded answer, clickable page sources, recent questions, and retrieval debug panel.

## Tech Stack

Frontend:

- React
- Vite
- Tailwind CSS
- Axios
- React PDF
- Lucide React

Backend:

- FastAPI
- Uvicorn
- PyMuPDF
- scikit-learn
- NumPy
- Groq Python SDK
- python-dotenv

## Project Structure

```text
PDF-Reviewer/
  backend/
    main.py             # FastAPI app and API routes
    config.py           # Environment and app configuration
    pdf_processor.py    # PDF saving, text extraction, and chunking
    vector_store.py     # Local TF-IDF index and similarity search
    chat_engine.py      # Groq-powered grounded chat pipeline
    models.py           # Pydantic request/response models
    requirements.txt    # Backend dependencies
    .env.example        # Example environment file

  frontend/
    src/
      App.jsx           # Main UI and app state
      api.js            # API client helpers
      components/       # Upload, chat, PDF viewer, and UI components
    package.json        # Frontend scripts and dependencies
    vite.config.js      # Vite config and API proxy

  samples/
    sample-review-policy.pdf         # Reviewer-ready sample PDF
    test-cases.md                    # 5 valid and 3 invalid test cases
    sample-review-policy-source.md   # Source text for the sample PDF
```

## Prerequisites

Install these before running the app:

- Python 3.12 recommended
- Node.js 18 or newer
- npm
- A Groq API key from [Groq Console](https://console.groq.com/keys)

Python 3.14 may try to build some scientific packages from source on Windows. Python 3.12 is recommended because the pinned dependencies have prebuilt wheels available.

## Environment Setup

Create a backend environment file:

```powershell
cd backend
copy .env.example .env
```

Open `backend/.env` and set:

```env
GROQ_API_KEY=your_groq_api_key_here
```

Do not commit the real `.env` file. It is already ignored by Git.

## Run Locally

From the project root, install and run the backend:

```powershell
cd backend
py -3.12 -m venv .venv312
.\.venv312\Scripts\python.exe -m pip install --upgrade pip
.\.venv312\Scripts\python.exe -m pip install -r requirements.txt
.\.venv312\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

In another terminal, install and run the frontend:

```powershell
cd frontend
npm install
npm run dev -- --host 0.0.0.0
```

Open the app:

```text
http://localhost:5173/
```

The backend runs at:

```text
http://localhost:8000/
```

## How To Use

1. Start the backend server.
2. Start the frontend dev server.
3. Open `http://localhost:5173/`.
4. Upload a PDF.
5. Wait for the upload and indexing process to finish.
6. Ask questions about the uploaded PDF.
7. Click citation badges to open the PDF viewer on the referenced page.
8. Use the reset button to upload a different PDF.

## API Endpoints

### `GET /api/health`

Checks whether the backend is running.

Response:

```json
{
  "status": "ok",
  "message": "PDFChat API is running"
}
```

### `POST /api/upload`

Uploads and processes a PDF.

Request:

- Form field: `file`
- Accepted format: `.pdf`
- Maximum size: 50 MB

Response includes:

- `document_id`
- `total_pages`
- `total_chunks`
- status message

### `POST /api/chat`

Asks a question about an uploaded PDF.

Request body:

```json
{
  "question": "What is this document about?",
  "document_id": "document-id-from-upload",
  "session_id": null
}
```

Response includes:

- grounded answer
- citations
- session ID
- refusal flag

### `GET /api/document/{document_id}/pdf`

Returns the uploaded PDF for inline viewing in the frontend.

### `DELETE /api/document/{document_id}`

Deletes a processed document index.

## How The Answering Pipeline Works

1. The user uploads a PDF.
2. The backend stores the PDF under `backend/uploads`.
3. PyMuPDF extracts readable page text, including cleanup for letter-spaced resume headings.
4. The text is chunked into overlapping sections with page metadata.
5. The chunks are indexed using TF-IDF with compact aliases for better name matching.
6. A user question is rewritten when needed and converted into the same search space.
7. The backend retrieves, filters, reranks, and merges the most relevant chunks.
8. If retrieval fails, the assistant returns the fixed refusal message.
9. Groq receives only the retrieved PDF context and recent session memory.
10. The frontend displays the answer, citations, recent questions, retrieval debug data, and PDF viewer.

## Notes

- Uploaded PDFs and generated indexes are local runtime data.
- The app uses a local lightweight retrieval index instead of an external vector database.
- The Groq API key must be configured locally in `backend/.env`.
- The real API key is intentionally not included in this repository.
