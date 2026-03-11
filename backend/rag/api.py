# backend/rag/api.py
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel
from starlette.responses import StreamingResponse

from .config import load_config
from .ingest import rebuild_index
from .memory import get_history, list_sessions, delete_session
from .service import answer_question, answer_question_stream, schema_help

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parents[1]  # backend/


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/ingest")
def ingest():
    return rebuild_index(BASE_DIR)


class ChatReq(BaseModel):
    message: Optional[str] = None       # existing contract (backward compat)
    question: Optional[str] = None      # preferred field name
    session_id: str = "default"
    include_sources: bool = True


@router.post("/chat")
def chat(req: ChatReq):
    q = req.question or req.message
    if not q:
        return {"answer": "No question provided.", "query_type": "error", "success": False}

    result = answer_question(BASE_DIR, q, req.session_id)

    return {
        "answer": result.get("answer", ""),
        "query_type": result.get("query_type", result.get("mode", "unknown")),
        "success": result.get("success", True),
        "timestamp": datetime.now().isoformat(),
        "sources": result.get("sources", result.get("citations")) if req.include_sources else None,
        "data_summary": result.get("data_summary"),
    }


@router.post("/chat/stream")
def chat_stream(req: ChatReq):
    q = req.question or req.message
    if not q:
        return {"error": "No question provided."}

    return StreamingResponse(
        answer_question_stream(BASE_DIR, q, req.session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/history")
def history(session_id: str = "default"):
    cfg = load_config(BASE_DIR)
    messages = get_history(session_id, cfg.db_url, max_messages=50)
    return {"session_id": session_id, "messages": messages}


@router.get("/sessions")
def sessions():
    cfg = load_config(BASE_DIR)
    return {"sessions": list_sessions(cfg.db_url)}


@router.delete("/sessions/{session_id}")
def delete_session_endpoint(session_id: str):
    cfg = load_config(BASE_DIR)
    delete_session(session_id, cfg.db_url)
    return {"status": "deleted", "session_id": session_id}


class SchemaReq(BaseModel):
    message: Optional[str] = None
    question: Optional[str] = None


@router.post("/schema")
def schema(req: SchemaReq):
    q = req.question or req.message
    if not q:
        return {"answer": "No question provided.", "mode": "error"}
    return schema_help(BASE_DIR, q)
