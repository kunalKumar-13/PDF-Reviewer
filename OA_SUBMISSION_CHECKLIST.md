# OA Submission Checklist

This project is built for Task 3: PDF-Constrained Conversational Agent.

## Requirement Mapping

- Accept any PDF as input: implemented through drag-and-drop/click upload with PDF extension, magic-byte, and 50 MB size validation.
- Enable conversational querying: implemented with multi-turn chat sessions and recent conversation memory.
- Answer only from the PDF: implemented with retrieval over extracted PDF chunks and a strict Groq system prompt that forbids outside knowledge.
- Explicitly refuse out-of-scope queries: implemented with a fixed refusal instruction and refusal flag in API responses.
- Include citations: implemented with page/section citations in answers and clickable citation metadata in the UI.
- Provide a sample PDF: included at `samples/sample-review-policy.pdf`.
- Include 5 valid queries and 3 invalid queries: included at `samples/test-cases.md`.
- Show expected behavior: included in `samples/test-cases.md` with expected citations/refusals.
- Multilingual bonus: supported for answerable questions by instructing the agent to answer in the user's language while keeping citations and PDF-only grounding.

## Important Multilingual Clarification

Multilingual support does not mean the assistant can answer general questions in many languages. It means:

1. The user may ask an answerable PDF-based question in another language.
2. The agent should answer in that language.
3. The evidence still must come only from the uploaded PDF.
4. Citations must still be page/section based.
5. Out-of-scope questions must still be refused instead of guessed.

## Recommended Reviewer Flow

1. Open the deployed app.
2. Download or use `samples/sample-review-policy.pdf`.
3. Upload the sample PDF.
4. Ask all 5 valid questions from `samples/test-cases.md`.
5. Confirm each supported answer cites a page.
6. Ask all 3 invalid questions.
7. Confirm each invalid question is refused without fabricated details.
8. Ask the Spanish valid query to verify grounded multilingual behavior.

## Architecture Summary

The frontend is React/Vite for user interaction. The AI agent behavior is in the FastAPI backend:

- PyMuPDF extracts text from PDFs.
- The backend chunks text with page metadata.
- scikit-learn TF-IDF retrieves relevant chunks.
- Groq generates answers from only those retrieved chunks.
- The system prompt enforces grounding, citations, refusals, and same-language responses for supported multilingual queries.
