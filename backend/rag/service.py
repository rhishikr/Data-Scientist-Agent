# backend/rag/service.py
"""
Main RAG service — routes queries through SQL agent, pgvector search, or hybrid.
"""
from pathlib import Path
from typing import Dict, Any, Generator, List
import json
import logging

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from openai import BadRequestError

from .config import load_config
from .store_pgvector import PgVectorStore
from .sql_agent import create_sql_agent_instance, run_sql_agent
from .memory import get_history, save_turn, to_langchain_messages
from .router import classify_query

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Insight retrieval (pgvector search + LLM synthesis)
# ---------------------------------------------------------------------------

INSIGHT_SYSTEM_PROMPT = """You are an AI business analyst providing insights from an ecommerce company's data.
Use ONLY the provided context to answer the question.
If you don't have enough information, say so.
Be clear, specific, and actionable."""


def _handle_insight(
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
            "query_type": "insight",
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
            SystemMessage(content=INSIGHT_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]).content
    except BadRequestError as e:
        return {
            "success": False,
            "query_type": "insight",
            "answer": "The retrieved context is too large for the model. Try narrowing your question.",
            "error": str(e),
        }

    return {
        "success": True,
        "query_type": "insight",
        "answer": answer,
        "sources": sources,
    }


# ---------------------------------------------------------------------------
# SQL agent
# ---------------------------------------------------------------------------

def _handle_sql(
    question: str,
    session_id: str,
    cfg,
    llm: ChatOpenAI,
) -> Dict[str, Any]:
    """Route to the LangGraph ReAct SQL agent."""
    agent = create_sql_agent_instance(cfg.db_url, llm)
    history = get_history(session_id, cfg.db_url, max_messages=10)
    lc_history = to_langchain_messages(history)

    result = run_sql_agent(agent, question, history=lc_history)
    return result


# ---------------------------------------------------------------------------
# Hybrid (SQL + Insight combined)
# ---------------------------------------------------------------------------

SYNTHESIS_PROMPT = """You are a business analyst. Combine the following data analysis and strategic insights
to answer the user's question comprehensively.

User Question: {question}

Data Analysis:
{sql_answer}

Strategic Insights:
{insight_answer}

Provide a comprehensive answer that:
1. Presents the key data findings
2. Explains the strategic context from insights
3. Offers actionable recommendations

Answer:"""


def _handle_hybrid(
    question: str,
    session_id: str,
    cfg,
    llm: ChatOpenAI,
) -> Dict[str, Any]:
    """Run both SQL and insight paths, then synthesize."""
    sql_result = _handle_sql(question, session_id, cfg, llm)
    insight_result = _handle_insight(question, session_id, cfg, llm)

    sql_answer = sql_result.get("answer", "No data available")
    insight_answer = insight_result.get("answer", "No insights available")

    try:
        synthesized = llm.invoke(
            SYNTHESIS_PROMPT.format(
                question=question,
                sql_answer=sql_answer,
                insight_answer=insight_answer,
            )
        ).content
    except Exception as e:
        # Fall back to concatenation
        synthesized = f"**Data Analysis:**\n{sql_answer}\n\n**Insights:**\n{insight_answer}"
        logger.warning("Synthesis failed, using concatenation: %s", e)

    return {
        "success": True,
        "query_type": "hybrid",
        "answer": synthesized,
        "data_summary": sql_answer,
        "sources": insight_result.get("sources", []),
    }


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
      1. Classify query → sql / insight / hybrid
      2. Route to appropriate handler
      3. Save Q&A turn to chat memory
    """
    cfg = load_config(base_dir)
    llm = ChatOpenAI(model=cfg.llm_model, temperature=0)

    # Classify
    query_type = classify_query(question, llm)
    logger.info("Query classified as '%s': %s", query_type, question[:80])

    # Route
    if query_type == "sql":
        result = _handle_sql(question, session_id, cfg, llm)
    elif query_type == "insight":
        result = _handle_insight(question, session_id, cfg, llm)
    else:
        result = _handle_hybrid(question, session_id, cfg, llm)

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
    llm = ChatOpenAI(model=cfg.llm_model, temperature=0, streaming=True)

    query_type = classify_query(question, llm)
    logger.info("Stream query classified as '%s': %s", query_type, question[:80])

    yield f"data: {json.dumps({'event': 'start', 'query_type': query_type})}\n\n"

    answer = ""

    try:
        if query_type == "sql":
            # SQL agent does multi-step tool calling — send result as one chunk
            result = _handle_sql(question, session_id, cfg, llm)
            answer = result.get("answer", "")
            yield f"data: {json.dumps({'event': 'chunk', 'content': answer})}\n\n"

        elif query_type == "insight":
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
                    SystemMessage(content=INSIGHT_SYSTEM_PROMPT),
                    HumanMessage(content=prompt),
                ]):
                    token = chunk.content
                    if token:
                        answer_chunks.append(token)
                        yield f"data: {json.dumps({'event': 'chunk', 'content': token})}\n\n"

                answer = "".join(answer_chunks)
                yield f"data: {json.dumps({'event': 'sources', 'sources': sources}, default=str)}\n\n"

        else:  # hybrid
            # SQL part (non-streaming)
            sql_result = _handle_sql(question, session_id, cfg, llm)
            sql_answer = sql_result.get("answer", "No data available")

            # Insight context
            store = PgVectorStore(cfg)
            retrieved = store.similarity_search(question, k=cfg.top_k)
            insight_answer = "No insights available"
            sources = []
            if retrieved:
                context = "\n\n---\n\n".join(d.page_content for d in retrieved)
                sources = [d.metadata for d in retrieved]
                try:
                    insight_answer = llm.invoke([
                        SystemMessage(content=INSIGHT_SYSTEM_PROMPT),
                        HumanMessage(content=f"QUESTION:\n{question}\n\nCONTEXT:\n{context}"),
                    ]).content
                except Exception:
                    pass

            # Stream the synthesis
            answer_chunks = []
            for chunk in llm.stream(
                SYNTHESIS_PROMPT.format(
                    question=question,
                    sql_answer=sql_answer,
                    insight_answer=insight_answer,
                )
            ):
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
