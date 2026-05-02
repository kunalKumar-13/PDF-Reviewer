"""Grounded chat engine — the core intelligence of PDFChat.

Orchestrates:
1. Retrieving relevant chunks from the vector store
2. Building a grounded system prompt with strict rules
3. Calling Groq API for generation
4. Enforcing citation format and refusal behavior
5. Maintaining per-session conversation memory
"""

import logging
import re
import uuid
from groq import Groq

import config
import vector_store

# --- Session Memory ---
# In-memory conversation history keyed by session_id
_sessions: dict[str, list[dict]] = {}
REFUSAL_MESSAGE = (
    "I'm unable to answer this question based on the provided document. "
    "The information is not present in the PDF."
)

logger = logging.getLogger(__name__)

# --- Groq Client ---
_groq_client: Groq | None = None


def _get_groq() -> Groq:
    """Lazy-initialize the Groq client."""
    global _groq_client
    if _groq_client is None:
        key = config.GROQ_API_KEY
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
1. Every non-refusal answer MUST include citations.
2. Use this exact response shape for non-refusal answers:
   Answer text

   Sources:

   * Page X: short snippet
   * Page Y: short snippet
3. If multiple sources are used, cite ALL relevant pages.

## REFUSAL BEHAVIOR
If the query is out of scope, ambiguous, or not answerable from the context:
Respond EXACTLY with this message and nothing else:
"I'm unable to answer this question based on the provided document. The information is not present in the PDF."

## ANSWER STYLE
- Be precise and factual.
- Do not add fluff or unnecessary elaboration.
- Prefer bullet points for structured answers.
- If the user asks for explanation, keep it grounded strictly in the document context.
- If the user asks in a language other than English, answer in that same language while preserving the citation format.

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


REWRITE_SYSTEM_PROMPT = """You rewrite follow-up questions into standalone retrieval queries.

Rules:
- Use only the conversation history and current question.
- Do not answer the question.
- Do not add outside knowledge.
- Preserve the user's intent and language where possible.
- If the question is already standalone, return it unchanged.
- Return only the rewritten query text."""


def _is_lookup_query(question: str) -> bool:
    """Detect short keyword/name lookups that users expect us to summarize."""
    normalized = question.strip()
    if not normalized or normalized.endswith("?"):
        return False

    words = re.findall(r"[A-Za-z0-9]+", normalized)
    if not 1 <= len(words) <= 5:
        return False

    question_words = {
        "what",
        "when",
        "where",
        "who",
        "why",
        "how",
        "which",
        "does",
        "do",
        "did",
        "is",
        "are",
        "can",
        "should",
    }
    return words[0].lower() not in question_words


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


def _format_history(history: list[dict], max_turns: int = config.MEMORY_TURNS) -> str:
    """Render recent user/assistant turns for query rewriting."""
    if not history:
        return "(No previous conversation.)"

    recent = history[-max_turns * 2:]
    lines = []
    for message in recent:
        role = "User" if message["role"] == "user" else "Assistant"
        lines.append(f"{role}: {message['content']}")

    return "\n".join(lines)


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
    # Normalize whitespace for comparison
    normalized = " ".join(answer.strip().split())
    return REFUSAL_MESSAGE.lower() in normalized.lower()


def _short_snippet(text: str, limit: int = 180) -> str:
    """Create a compact source snippet for citations and debug display."""
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3].rsplit(" ", 1)[0] + "..."


def _extract_citations(chunks: list[dict], answer: str) -> list[dict]:
    """Build citation objects from the retrieved chunks.

    Returns citation metadata for the frontend to display.
    """
    cited_pages = {int(page) for page in re.findall(r"\bPage\s+(\d+)\b", answer)}
    citations = []
    seen_pages = set()

    for chunk in chunks:
        page = chunk["page_number"]
        if cited_pages and page not in cited_pages:
            continue

        section = chunk.get("section")
        snippet = _short_snippet(chunk["text"])

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


def _format_sources(citations: list[dict]) -> str:
    """Build the required deterministic Sources block."""
    source_lines = ["Sources:"]
    for citation in citations:
        source_lines.append(
            f"* Page {citation['page']}: {citation['text_snippet']}"
        )

    return "\n\n".join([source_lines[0], "\n".join(source_lines[1:])])


def _strip_sources_block(answer: str) -> str:
    """Remove any model-generated Sources block before appending our own."""
    return re.split(r"\n\s*Sources\s*:\s*", answer.strip(), flags=re.IGNORECASE)[0].strip()


def _rewrite_query(question: str, history: list[dict]) -> str:
    """Rewrite the user question into a standalone retrieval query."""
    if _is_lookup_query(question):
        return f"What information does the document provide about {question.strip()}?"

    if not history:
        return question

    client = _get_groq()
    completion = client.chat.completions.create(
        model=config.GENERATION_MODEL,
        messages=[
            {"role": "system", "content": REWRITE_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "Conversation history:\n"
                    f"{_format_history(history)}\n\n"
                    f"Current question: {question}\n\n"
                    "Standalone retrieval query:"
                ),
            },
        ],
        temperature=0.0,
        max_tokens=256,
    )

    rewritten = completion.choices[0].message.content.strip().strip('"')
    return rewritten or question


def _build_debug_info(rewritten_query: str, chunks: list[dict]) -> dict:
    """Expose observability details for the frontend debug panel."""
    return {
        "rewritten_query": rewritten_query,
        "retrieved_chunks": [
            {
                "page": chunk["page_number"],
                "section": chunk.get("section"),
                "similarity": round(chunk.get("similarity", 0.0), 4),
                "keyword_overlap": round(chunk.get("keyword_overlap", 0.0), 4),
                "combined_score": round(chunk.get("combined_score", 0.0), 4),
                "text_snippet": _short_snippet(chunk["text"], limit=140),
            }
            for chunk in chunks
        ],
    }


def _append_turn(history: list[dict], question: str, answer: str) -> None:
    """Append one turn and retain only the configured session memory window."""
    history.append({"role": "user", "content": question})
    history.append({"role": "assistant", "content": answer})

    max_messages = config.MEMORY_TURNS * 2
    if len(history) > max_messages:
        del history[:-max_messages]


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

    # 2. Get/create session and rewrite the query before retrieval
    session_id, history = _get_session(session_id)
    rewritten_query = _rewrite_query(question, history)

    # 3. Retrieve relevant chunks
    chunks = vector_store.query_chunks(document_id, rewritten_query)
    debug_info = _build_debug_info(rewritten_query, chunks)
    logger.info("rewritten_query=%s", rewritten_query)
    logger.info("retrieved_chunks=%s", debug_info["retrieved_chunks"])

    if not chunks:
        _append_turn(history, question, REFUSAL_MESSAGE)
        return {
            "answer": REFUSAL_MESSAGE,
            "citations": [],
            "session_id": session_id,
            "is_refusal": True,
            "debug": debug_info,
        }

    # 4. Build system prompt with context
    context = _build_context(chunks)
    system_prompt = SYSTEM_PROMPT.replace("{context}", context)

    messages = [{"role": "system", "content": system_prompt}]

    # Add recent conversation history for multi-turn continuity.
    recent_history = history[-config.MEMORY_TURNS * 2:]
    messages.extend(recent_history)

    # Add current question. When a terse lookup was expanded for retrieval,
    # ask the model to answer the expanded intent while preserving grounding.
    if rewritten_query != question:
        messages.append({
            "role": "user",
            "content": (
                f"Original user input: {question}\n"
                f"Standalone question to answer: {rewritten_query}"
            ),
        })
    else:
        messages.append({"role": "user", "content": question})

    # 5. Call Groq API
    client = _get_groq()
    completion = client.chat.completions.create(
        model=config.GENERATION_MODEL,
        messages=messages,
        temperature=0.0,  # Deterministic generation for factual grounding
        max_tokens=2048,
    )

    answer = completion.choices[0].message.content.strip()

    # 6. Normalize refusal/citation format and update session history
    is_refusal = _is_refusal(answer)
    if is_refusal:
        answer = REFUSAL_MESSAGE
        citations = []
    else:
        citations = _extract_citations(chunks, answer)
        if not citations:
            citations = _extract_citations(chunks, " ".join(
                f"Page {chunk['page_number']}" for chunk in chunks
            ))
        answer_text = _strip_sources_block(answer)
        answer = f"{answer_text}\n\n{_format_sources(citations)}"

    _append_turn(history, question, answer)

    return {
        "answer": answer,
        "citations": citations,
        "session_id": session_id,
        "is_refusal": is_refusal,
        "debug": debug_info,
    }


def clear_session(session_id: str) -> bool:
    """Clear conversation history for a session."""
    if session_id in _sessions:
        del _sessions[session_id]
        return True
    return False
