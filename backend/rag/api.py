# backend/rag/api.py
from pathlib import Path
from fastapi import APIRouter
from pydantic import BaseModel

from .ingest import rebuild_index
from .service import answer_question, schema_help

router = APIRouter(prefix="/rag", tags=["rag"])

BASE_DIR = Path(__file__).resolve().parents[1]  # backend/


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/ingest")
def ingest():
    # Rebuild FAISS index from backend/data/*.csv
    return rebuild_index(BASE_DIR)


class ChatReq(BaseModel):
    message: str


@router.post("/chat")
def chat(req: ChatReq):
    return answer_question(BASE_DIR, req.message)

@router.post("/schema")
def schema(req: ChatReq):
    return schema_help(BASE_DIR, req.message)

