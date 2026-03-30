# backend/rag/service.py
"""
Main RAG service — routes queries through snapshot lookup or pgvector retrieval.

Two-path architecture (no raw table access):
  1. Snapshot: instant KPI / forecast / health-score lookup (no LLM)
  2. Retrieval: pgvector semantic search + LLM synthesis (all cleaned data)
"""
from pathlib import Path
from typing import Dict, Any, Generator, Optional
import json
import logging

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from openai import BadRequestError

from .config import load_config
from .store_pgvector import PgVectorStore
from .memory import get_history, save_turn
from .snapshot_matcher import (
    match_snapshot_metric,
    format_snapshot_response,
    format_forecast_response,
    format_action_plan_response,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# System prompt for retrieval-based synthesis
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are an AI business analyst for an ecommerce company.
You answer questions using ONLY the provided context, which comes from the
company's cleaned data pipeline — the same source powering the executive dashboard.

Your context may include:
- KPI metrics (revenue, AOV, churn, conversion, etc.)
- Forecast data (revenue/churn/demand projections)
- Business insights with severity and confidence scores
- Action plan prescriptions with urgency and impact estimates
- Top/bottom customer and product rankings
- Statistical hypothesis test results
- Executive summaries and health scores

RULES:
1. Use ONLY numbers and facts from the provided context. Never estimate or calculate.
2. When citing a metric, state its exact value as given in context.
3. If the context doesn't contain enough information, say so explicitly.
4. Be specific and actionable. Reference concrete data points.
5. When multiple context documents are relevant, synthesize them coherently.
6. Indicate the source type (KPI, forecast, insight, action plan, etc.)."""


# ---------------------------------------------------------------------------
# Retrieval handler (pgvector search + LLM synthesis)
# ---------------------------------------------------------------------------

def _handle_retrieval(
    question: str,
    session_id: str,
    cfg,
    llm: ChatOpenAI,
) -> Dict[str, Any]:
    """Retrieve relevant documents via pgvector and synthesize an answer."""
    store = PgVectorStore(cfg)
    retrieved = store.similarity_search(question, k=cfg.top_k)

    if not retrieved:
        return {
            "success": True,
            "query_type": "retrieval",
            "answer": "No relevant documents found in the index. Try running POST /api/rag/ingest first.",
            "sources": [],
        }

    context_parts = []
    sources = []
    for doc in retrieved:
        context_parts.append(doc.page_content)
        sources.append(doc.metadata)

    context = "\n\n---\n\n".join(context_parts)

    # Safety cap
    MAX_CONTEXT_CHARS = 120_000
    if len(context) > MAX_CONTEXT_CHARS:
        context = context[:MAX_CONTEXT_CHARS] + "\n\n[TRUNCATED]"

    # Include chat history for multi-turn context
    history = get_history(session_id, cfg.db_url, max_messages=10)
    history_text = ""
    if history:
        history_text = "\n".join(
            f"{'User' if h['role'] == 'human' else 'Assistant'}: {h['content']}"
            for h in history[-6:]  # last 3 turns
        )
        history_text = f"\nConversation history:\n{history_text}\n"

    prompt = f"{history_text}QUESTION:\n{question}\n\nCONTEXT:\n{context}"

    try:
        answer = llm.invoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]).content
    except BadRequestError as e:
        return {
            "success": False,
            "query_type": "retrieval",
            "answer": "The retrieved context is too large for the model. Try narrowing your question.",
            "error": str(e),
        }

    return {
        "success": True,
        "query_type": "retrieval",
        "answer": answer,
        "sources": sources,
    }


# ---------------------------------------------------------------------------
# Snapshot lookup (pre-computed metrics — no LLM needed)
# ---------------------------------------------------------------------------

def _handle_snapshot(
    question: str,
    llm=None,
) -> Optional[Dict[str, Any]]:
    """
    Try to match the question to a pre-computed metric from the dashboard.
    Supports KPI cards, forecast metrics, and health score.
    Returns None if no match (caller falls through to retrieval).
    """
    match = match_snapshot_metric(question, llm=llm)
    if match is None:
        return None

    if match.source == "kpi":
        from db.store import get_latest_kpi_snapshot

        snapshot = get_latest_kpi_snapshot()
        if "error" in snapshot:
            logger.info("No KPI snapshot available, falling through: %s", snapshot.get("error"))
            return None

        cards = snapshot.get("cards", [])
        card = next((c for c in cards if c.get("id") == match.card_id), None)
        if card is None or card.get("value") is None:
            logger.info("KPI card '%s' not found or has no value, falling through", match.card_id)
            return None

        answer = format_snapshot_response(card, cards)

        return {
            "success": True,
            "query_type": "snapshot",
            "answer": answer,
            "sources": [{"type": "dashboard_snapshot", "note": "Pre-computed from cleaned data"}],
        }

    if match.source == "forecast":
        from db.store import get_latest_forecast_snapshot

        snapshot = get_latest_forecast_snapshot()
        if "error" in snapshot:
            logger.info("No forecast snapshot available, falling through: %s", snapshot.get("error"))
            return None

        answer = format_forecast_response(match.card_id, snapshot)
        if answer is None:
            logger.info("Forecast metric '%s' not found, falling through", match.card_id)
            return None

        return {
            "success": True,
            "query_type": "snapshot",
            "answer": answer,
            "sources": [{"type": "forecast_snapshot", "note": "Pre-computed from cleaned data"}],
        }

    if match.source == "action_plan":
        from db.store import get_latest_action_plan_snapshot

        snapshot = get_latest_action_plan_snapshot()
        if "error" in snapshot:
            logger.info("No action plan snapshot available, falling through: %s", snapshot.get("error"))
            return None

        answer = format_action_plan_response(match.card_id, snapshot)
        if answer is None:
            logger.info("Action plan metric '%s' not found, falling through", match.card_id)
            return None

        return {
            "success": True,
            "query_type": "snapshot",
            "answer": answer,
            "sources": [{"type": "action_plan_snapshot", "note": "Pre-computed from cleaned data"}],
        }

    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def answer_question(
    base_dir: Path,
    question: str,
    session_id: str = "default",
) -> Dict[str, Any]:
    """
    Main entry point for answering a user question.

    Flow:
      1. Try snapshot route (Tier 1 keyword → Tier 2 LLM)
      2. Fall through to pgvector retrieval + LLM synthesis
      3. Save Q&A turn to chat memory
    """
    cfg = load_config(base_dir)

    # --- Snapshot-first route (Tier 1: no LLM) ---
    snapshot_result = _handle_snapshot(question)
    if snapshot_result is not None:
        logger.info("Query answered from snapshot (Tier 1): %s", question[:80])
        if snapshot_result.get("answer"):
            try:
                save_turn(session_id, question, snapshot_result["answer"], cfg.db_url)
            except Exception as e:
                logger.warning("Failed to save chat history: %s", e)
        return snapshot_result

    llm = ChatOpenAI(model=cfg.llm_model, temperature=0)

    # --- Snapshot-first route (Tier 2: lightweight LLM fallback) ---
    fallback_llm = ChatOpenAI(model=cfg.llm_model, temperature=0)
    snapshot_result = _handle_snapshot(question, llm=fallback_llm)
    if snapshot_result is not None:
        logger.info("Query answered from snapshot (Tier 2 LLM): %s", question[:80])
        if snapshot_result.get("answer"):
            try:
                save_turn(session_id, question, snapshot_result["answer"], cfg.db_url)
            except Exception as e:
                logger.warning("Failed to save chat history: %s", e)
        return snapshot_result

    # --- Retrieval path (pgvector + LLM synthesis) ---
    logger.info("Query routed to retrieval: %s", question[:80])
    result = _handle_retrieval(question, session_id, cfg, llm)

    # Persist conversation
    answer = result.get("answer", "")
    if answer:
        try:
            save_turn(session_id, question, answer, cfg.db_url)
        except Exception as e:
            logger.warning("Failed to save chat history: %s", e)

    return result


def answer_question_stream(
    base_dir: Path,
    question: str,
    session_id: str = "default",
) -> Generator[str, None, None]:
    """
    Streaming version of answer_question().
    Yields SSE-formatted event strings for token-by-token delivery.
    """
    cfg = load_config(base_dir)

    # --- Snapshot-first route (Tier 1: no LLM, then Tier 2: lightweight LLM) ---
    snapshot_result = _handle_snapshot(question)
    if snapshot_result is None:
        fallback_llm = ChatOpenAI(model=cfg.llm_model, temperature=0)
        snapshot_result = _handle_snapshot(question, llm=fallback_llm)

    if snapshot_result is not None:
        answer = snapshot_result.get("answer", "")
        logger.info("Stream query answered from snapshot: %s", question[:80])
        yield f"data: {json.dumps({'event': 'start', 'query_type': 'snapshot'})}\n\n"
        yield f"data: {json.dumps({'event': 'chunk', 'content': answer})}\n\n"
        if answer:
            try:
                save_turn(session_id, question, answer, cfg.db_url)
            except Exception as e:
                logger.warning("Failed to save chat history: %s", e)
        yield f"data: {json.dumps({'event': 'done'})}\n\n"
        return

    # --- Retrieval path (pgvector search + streamed LLM synthesis) ---
    llm = ChatOpenAI(model=cfg.llm_model, temperature=0, streaming=True)

    logger.info("Stream query routed to retrieval: %s", question[:80])
    yield f"data: {json.dumps({'event': 'start', 'query_type': 'retrieval'})}\n\n"

    answer = ""

    try:
        store = PgVectorStore(cfg)
        retrieved = store.similarity_search(question, k=cfg.top_k)

        if not retrieved:
            answer = "No relevant documents found in the index. Try running POST /api/rag/ingest first."
            yield f"data: {json.dumps({'event': 'chunk', 'content': answer})}\n\n"
        else:
            context = "\n\n---\n\n".join(d.page_content for d in retrieved)
            sources = [d.metadata for d in retrieved]

            MAX_CONTEXT_CHARS = 120_000
            if len(context) > MAX_CONTEXT_CHARS:
                context = context[:MAX_CONTEXT_CHARS] + "\n\n[TRUNCATED]"

            history = get_history(session_id, cfg.db_url, max_messages=10)
            history_text = ""
            if history:
                history_text = "\n".join(
                    f"{'User' if h['role'] == 'human' else 'Assistant'}: {h['content']}"
                    for h in history[-6:]
                )
                history_text = f"\nConversation history:\n{history_text}\n"

            prompt = f"{history_text}QUESTION:\n{question}\n\nCONTEXT:\n{context}"

            answer_chunks = []
            for chunk in llm.stream([
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ]):
                token = chunk.content
                if token:
                    answer_chunks.append(token)
                    yield f"data: {json.dumps({'event': 'chunk', 'content': token})}\n\n"

            answer = "".join(answer_chunks)
            yield f"data: {json.dumps({'event': 'sources', 'sources': sources}, default=str)}\n\n"

    except Exception as e:
        logger.error("Stream error: %s", e)
        yield f"data: {json.dumps({'event': 'error', 'message': str(e)})}\n\n"

    # Persist conversation
    if answer:
        try:
            save_turn(session_id, question, answer, cfg.db_url)
        except Exception as e:
            logger.warning("Failed to save chat history: %s", e)

    yield f"data: {json.dumps({'event': 'done'})}\n\n"


def schema_help(base_dir: Path, question: str) -> Dict[str, Any]:
    """
    Answer schema-related questions using pgvector context.
    """
    cfg = load_config(base_dir)
    store = PgVectorStore(cfg)

    retrieved = store.similarity_search(question, k=cfg.top_k)
    if not retrieved:
        return {"error": "Vector index not found. Call POST /api/rag/ingest first."}

    context_parts = []
    citations = []
    for d in retrieved:
        context_parts.append(d.page_content)
        citations.append(d.metadata or {})

    context = "\n\n---\n\n".join(context_parts)
    MAX_CONTEXT_CHARS = 120_000
    if len(context) > MAX_CONTEXT_CHARS:
        context = context[:MAX_CONTEXT_CHARS] + "\n\n[TRUNCATED]"

    schema_prompt = (
        "You are an AI Data Scientist assistant.\n"
        "Use ONLY the provided CONTEXT to explain what tables/columns mean, "
        "describe which table answers a question, or explain how to compute something.\n"
        "Do NOT invent numbers or claim computed results."
    )

    llm = ChatOpenAI(model=cfg.llm_model, temperature=0.0)
    prompt = f"QUESTION:\n{question}\n\nCONTEXT:\n{context}"

    try:
        answer = llm.invoke([
            SystemMessage(content=schema_prompt),
            HumanMessage(content=prompt),
        ]).content
    except BadRequestError as e:
        return {
            "answer": "The schema context is too large for the model. Narrow your question.",
            "mode": "error_context_too_large",
            "error": str(e),
        }

    return {
        "answer": answer,
        "citations": citations,
        "top_k": cfg.top_k,
        "mode": "schema",
    }
