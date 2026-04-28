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
- Supports multi-turn chat sessions.
- Opens the uploaded PDF beside the chat and jumps to cited pages.
- Preserves grounding and citation structure when answering non-English questions.

## Why This Project

PDF Reviewer is built for document-grounded review workflows where the assistant should answer from the uploaded file, cite the source pages, and refuse unsupported questions instead of guessing. It keeps the retrieval layer lightweight by using a local TF-IDF index, making the app simple to run without a hosted vector database.

## Agent Architecture

This is an AI agent workflow, not just a static JavaScript app. The React frontend handles upload, chat, citations, and PDF viewing. The FastAPI backend performs PDF extraction, retrieval, prompt construction, Groq LLM generation, refusal detection, and citation metadata assembly.

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

## Reviewer Test Pack

This repository includes the assignment testability assets:

- `samples/sample-review-policy.pdf`: sample PDF to upload.
- `samples/test-cases.md`: 5 valid queries, 3 invalid/out-of-scope queries, and expected behavior.
- `samples/sample-review-policy-source.md`: readable source text used to generate the PDF.

Recommended reviewer flow:

1. Open the app.
2. Upload `samples/sample-review-policy.pdf`.
3. Run the valid queries in `samples/test-cases.md` and confirm answers include page citations.
4. Run the invalid queries and confirm the assistant refuses instead of guessing.
5. Try the Spanish query to verify same-language grounded behavior.

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
3. PyMuPDF extracts text from each page.
4. The text is chunked into overlapping sections.
5. The chunks are indexed using TF-IDF.
6. A user question is converted into the same search space.
7. The backend retrieves the most relevant chunks.
8. Groq receives only those chunks as context.
9. The model answers with citations, responds in the user's language when possible, or refuses if the answer is not supported.
10. The frontend displays the answer, citations, and PDF viewer.

## Notes

- Uploaded PDFs and generated indexes are local runtime data.
- The app uses a local lightweight retrieval index instead of an external vector database.
- The Groq API key must be configured locally in `backend/.env`.
- The real API key is intentionally not included in this repository.
