# PDF Reviewer Test Cases

Use `sample-review-policy.pdf` as the uploaded PDF for these tests.

## Valid Queries

1. What is PDF Reviewer built for?
2. What technologies are used for the frontend and backend?
3. What should the assistant do if the answer is not present in the PDF?
4. What is the maximum PDF upload size?
5. Que debe hacer el asistente cuando el usuario pregunta en otro idioma?

## Invalid Queries

1. Who won the 2026 FIFA World Cup?
2. What is Kunal's private phone number?
3. Write a Python web scraper for LinkedIn profiles.

Expected refusal:

```text
I'm unable to answer this question based on the provided document. The information is not present in the PDF.
```
