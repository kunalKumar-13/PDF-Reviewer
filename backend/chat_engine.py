"""Grounded chat engine — the core intelligence of PDFChat.

Orchestrates:
1. Retrieving relevant chunks from the vector store
2. Building a grounded system prompt with strict rules
3. Calling Groq API for generation
4. Enforcing citation format and refusal behavior
5. Maintaining per-session conversation memory
"""

import uuid
from groq import Groq

import config
import vector_store

# --- Session Memory ---
# In-memory conversation history keyed by session_id
_sessions: dict[str, list[dict]] = {}

# --- Groq Client ---
_groq_client: Groq | None = None


def _get_groq() -> Groq:
    """Lazy-initialize the Groq client."""
    global _groq_client
    if _groq_client is None:
        key = config.GROQ_API_KEY
        print(f"[DEBUG WORKER] Initializing Groq with key: {repr(key[:8])}...{repr(key[-4:])} (len={len(key)})")
        if not key:
            raise ValueError(
                "GROQ_API_KEY not set. Copy backend/.env.example to backend/.env "
                "and add your key from https://console.groq.com/keys"
            )
        _groq_client = Groq(api_key=key)
    return _groq_client


# --- System Prompt ---

SYSTEM_PROMPT = """You are a PDF-Constrained Conversational Agent.

Your ONLY source of truth is the provided PDF context below. You must strictly follow these rules:

## GROUNDING RULES
1. You MUST answer ONLY using the provided PDF context.
2. If the answer is not explicitly present or cannot be reasonably inferred from the context:
   - Respond with the EXACT refusal message (see below).
   - DO NOT hallucinate or use any outside knowledge.
3. Do NOT use prior knowledge, world knowledge, or assumptions.

## CITATION RULES
1. Every answer MUST include citations.
2. Citation format:
   - (Page X)
   - (Page X, Section: <section name>) — use this when a section name is available
3. If multiple sources are used, cite ALL relevant pages.
4. Place citations inline, immediately after the relevant statement.

## REFUSAL BEHAVIOR
If the query is out of scope, ambiguous, or not answerable from the context:
Respond EXACTLY with this message and nothing else:
"I'm unable to answer this question based on the provided document. The information is not present in the PDF."

## ANSWER STYLE
- Be precise and factual.
- Do not add fluff or unnecessary elaboration.
- Prefer bullet points for structured answers.
- If the user asks for explanation, keep it grounded strictly in the document context.

## EDGE CASE HANDLING
- If the question is partially answerable:
  → Answer ONLY the relevant part
  → Explicitly mention what information is missing from the document
- If multiple interpretations exist:
  → Choose the most directly supported one
  → Mention the ambiguity briefly

## PDF CONTEXT
The following are relevant excerpts from the user's uploaded PDF document:

{context}

---
Answer the user's question using ONLY the context above. Include citations."""


def _build_context(chunks: list[dict]) -> str:
    """Format retrieved chunks into a context block for the system prompt.

    Each chunk is labeled with its page number and section (if available)
    so the LLM can produce accurate citations.
    """
    if not chunks:
        return "(No relevant content found in the PDF for this query.)"

    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        page = chunk["page_number"]
        section = chunk.get("section")
        text = chunk["text"]

        header = f"[Excerpt {i} — Page {page}"
        if section:
            header += f", Section: {section}"
        header += "]"

        context_parts.append(f"{header}\n{text}")

    return "\n\n---\n\n".join(context_parts)


def _get_session(session_id: str | None) -> tuple[str, list[dict]]:
    """Get or create a conversation session.

    Args:
        session_id: Existing session ID, or None to create a new one.

    Returns:
        Tuple of (session_id, conversation_history).
    """
    if session_id and session_id in _sessions:
        return session_id, _sessions[session_id]

    new_id = session_id or str(uuid.uuid4())
    _sessions[new_id] = []
    return new_id, _sessions[new_id]


def _is_refusal(answer: str) -> bool:
    """Check if the LLM response is a refusal."""
    refusal_text = (
        "I'm unable to answer this question based on the provided document. "
        "The information is not present in the PDF."
    )
    # Normalize whitespace for comparison
    normalized = " ".join(answer.strip().split())
    return refusal_text.lower() in normalized.lower()


def _extract_citations(chunks: list[dict]) -> list[dict]:
    """Build citation objects from the retrieved chunks.

    Returns citation metadata for the frontend to display.
    """
    citations = []
    seen_pages = set()

    for chunk in chunks:
        page = chunk["page_number"]
        section = chunk.get("section")
        snippet = chunk["text"][:150] + "..." if len(chunk["text"]) > 150 else chunk["text"]

        # Deduplicate by page+section
        key = (page, section)
        if key not in seen_pages:
            seen_pages.add(key)
            citations.append({
                "page": page,
                "section": section,
                "text_snippet": snippet,
            })

    return citations


def chat(
    question: str,
    document_id: str,
    session_id: str | None = None,
) -> dict:
    """Process a user question and return a grounded answer.

    This is the main entry point for the chat pipeline:
    1. Retrieve relevant chunks from the vector store
    2. Build context-enriched system prompt
    3. Include conversation history for multi-turn context
    4. Call Groq API for generation
    5. Parse response for citations and refusals

    Args:
        question: The user's question.
        document_id: Which document to query against.
        session_id: Optional session ID for conversation continuity.

    Returns:
        Dict with 'answer', 'citations', 'session_id', 'is_refusal'.
    """
    # 1. Verify document exists
    if not vector_store.document_exists(document_id):
        return {
            "answer": "No document found. Please upload a PDF first.",
            "citations": [],
            "session_id": session_id or str(uuid.uuid4()),
            "is_refusal": True,
        }

    # 2. Retrieve relevant chunks
    chunks = vector_store.query_chunks(document_id, question)

    # 3. Build system prompt with context
    context = _build_context(chunks)
    system_prompt = SYSTEM_PROMPT.replace("{context}", context)

    # 4. Get/create session and build message history
    session_id, history = _get_session(session_id)

    messages = [{"role": "system", "content": system_prompt}]

    # Add conversation history (keep last 10 exchanges to manage context window)
    recent_history = history[-20:]  # 20 messages = 10 user-assistant pairs
    messages.extend(recent_history)

    # Add current question
    messages.append({"role": "user", "content": question})

    # 5. Call Groq API
    client = _get_groq()
    completion = client.chat.completions.create(
        model=config.GENERATION_MODEL,
        messages=messages,
        temperature=0.1,  # Low temperature for factual grounding
        max_tokens=2048,
    )

    answer = completion.choices[0].message.content.strip()

    # 6. Update session history
    history.append({"role": "user", "content": question})
    history.append({"role": "assistant", "content": answer})

    # 7. Build response
    is_refusal = _is_refusal(answer)
    citations = [] if is_refusal else _extract_citations(chunks)

    return {
        "answer": answer,
        "citations": citations,
        "session_id": session_id,
        "is_refusal": is_refusal,
    }


def clear_session(session_id: str) -> bool:
    """Clear conversation history for a session."""
    if session_id in _sessions:
        del _sessions[session_id]
        return True
    return False
