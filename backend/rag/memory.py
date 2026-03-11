# backend/rag/memory.py
"""
Session-based chat memory backed by Supabase PostgreSQL.
Stores conversation history in the chat_messages table.
"""
from typing import List, Dict, Any
import logging

from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)

# Module-level engine singleton
_engine = None


def _get_engine(db_url: str):
    global _engine
    if _engine is None:
        _engine = create_engine(db_url, pool_pre_ping=True, pool_size=5)
    return _engine


def get_history(session_id: str, db_url: str, max_messages: int = 20) -> List[Dict[str, str]]:
    """
    Retrieve recent chat messages for a session.
    Returns list of {"role": "human"|"ai", "content": "..."}.
    """
    engine = _get_engine(db_url)
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT role, content FROM chat_messages
                WHERE session_id = :sid
                ORDER BY created_at DESC
                LIMIT :limit
            """),
            {"sid": session_id, "limit": max_messages},
        ).fetchall()

    # Reverse so oldest first
    return [{"role": r.role, "content": r.content} for r in reversed(rows)]


def add_message(session_id: str, role: str, content: str, db_url: str):
    """
    Persist a single message to the chat history.
    role: 'human' or 'ai'
    """
    engine = _get_engine(db_url)
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO chat_messages (session_id, role, content)
                VALUES (:sid, :role, :content)
            """),
            {"sid": session_id, "role": role, "content": content},
        )


def save_turn(session_id: str, question: str, answer: str, db_url: str):
    """Save a full Q&A turn (convenience wrapper)."""
    add_message(session_id, "human", question, db_url)
    add_message(session_id, "ai", answer, db_url)


def list_sessions(db_url: str) -> List[Dict[str, Any]]:
    """Return all sessions with their first message preview and message count."""
    engine = _get_engine(db_url)
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT session_id,
                   COUNT(*) AS message_count,
                   MAX(created_at) AS last_active,
                   (SELECT content FROM chat_messages c2
                    WHERE c2.session_id = c1.session_id AND c2.role = 'human'
                    ORDER BY c2.created_at ASC LIMIT 1
                   ) AS first_message
            FROM chat_messages c1
            GROUP BY session_id
            ORDER BY last_active DESC
        """)).fetchall()
    return [
        {
            "session_id": r.session_id,
            "message_count": r.message_count,
            "last_active": r.last_active.isoformat() if r.last_active else None,
            "preview": (r.first_message or "")[:80],
        }
        for r in rows
    ]


def delete_session(session_id: str, db_url: str):
    """Delete all messages for a session."""
    engine = _get_engine(db_url)
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM chat_messages WHERE session_id = :sid"),
            {"sid": session_id},
        )


def to_langchain_messages(history: List[Dict[str, str]]):
    """Convert stored history dicts to LangChain message objects."""
    from langchain_core.messages import HumanMessage, AIMessage
    msgs = []
    for h in history:
        if h["role"] == "human":
            msgs.append(HumanMessage(content=h["content"]))
        else:
            msgs.append(AIMessage(content=h["content"]))
    return msgs
