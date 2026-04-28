# PDF Reviewer Sample Policy

This file is the source text used to generate `sample-review-policy.pdf`.
Use the PDF file for manual QA and reviewer testing.

## Page 1 - Overview and Scope

PDF Reviewer is a document-grounded assistant for reviewing uploaded PDF files.
The system accepts PDF input, extracts text page by page, splits the document into
overlapping chunks, and builds a local TF-IDF retrieval index. The user interface
is built with React and Vite, while the backend API is built with FastAPI.

The assistant must answer questions only from the uploaded PDF. Each supported
answer should include page-level citations so the user can verify the source.
The application includes an integrated PDF viewer so citation badges can be used
to open the referenced page.

## Page 2 - Grounding and Refusal Policy

The assistant must not use outside knowledge, assumptions, or unrelated training
data when answering questions. If the answer is not present in the uploaded PDF,
the assistant must refuse the question instead of guessing.

The required refusal message is:
"I'm unable to answer this question based on the provided document. The information is not present in the PDF."

Supported answers must cite the page used for the answer. If a section heading is
available, the assistant may include the section reference with the page number.
The assistant should keep responses concise and factual.

## Page 3 - Operational Details

PDF uploads are limited to 50 MB. The backend validates the file extension and PDF
magic bytes before processing. Text extraction is performed with PyMuPDF.
Retrieval uses scikit-learn TF-IDF and cosine similarity. Answer generation uses
the Groq API with the retrieved PDF excerpts as the only context.

The system supports multi-turn chat sessions by preserving recent conversation
history in memory. Uploaded PDFs and generated indexes are local runtime data.
When the user asks in another language, the assistant should answer in that same
language while staying grounded in the PDF and preserving page citations.
