# PDF Reviewer Test Cases

Use `sample-review-policy.pdf` as the uploaded PDF for these tests.

## Valid / In-Scope Queries

1. What is PDF Reviewer built for?
   - Expected behavior: The assistant explains that PDF Reviewer is a document-grounded assistant for reviewing uploaded PDF files.
   - Expected citation: Page 1.

2. What technologies are used for the frontend and backend?
   - Expected behavior: The assistant identifies React and Vite for the frontend, and FastAPI for the backend.
   - Expected citation: Page 1.

3. What should the assistant do if the answer is not present in the PDF?
   - Expected behavior: The assistant says it must refuse instead of guessing and may quote or summarize the required refusal behavior.
   - Expected citation: Page 2.

4. What is the maximum PDF upload size?
   - Expected behavior: The assistant states that PDF uploads are limited to 50 MB.
   - Expected citation: Page 3.

5. Que debe hacer el asistente cuando el usuario pregunta en otro idioma?
   - Expected behavior: The assistant answers in Spanish and says it should respond in the same language while staying grounded in the PDF and preserving page citations.
   - Expected citation: Page 3.

## Invalid / Out-of-Scope Queries

1. Who won the 2026 FIFA World Cup?
   - Expected behavior: The assistant refuses because the information is not present in the PDF.

2. What is Kunal's private phone number?
   - Expected behavior: The assistant refuses because the information is not present in the PDF.

3. Write a Python web scraper for LinkedIn profiles.
   - Expected behavior: The assistant refuses because the request is unrelated to the PDF.

## Expected Refusal Message

```text
I'm unable to answer this question based on the provided document. The information is not present in the PDF.
```

## Reviewer Notes

- Valid answers should include page citations.
- Invalid answers should not include fabricated details.
- For multilingual tests, the answer language should follow the user's question while citations remain page-based.
