# backend/rag/store_faiss.py
from typing import List, Dict, Any
from pathlib import Path

from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

from .config import RagConfig


class FaissStore:
    """
    Thin wrapper around LangChain FAISS:
    - build from docs
    - save to disk
    - load from disk
    """

    def __init__(self, cfg: RagConfig):
        self.cfg = cfg
        self.embeddings = OpenAIEmbeddings(model=cfg.embed_model)

    def index_exists(self) -> bool:
        return (self.cfg.vector_dir / "index.faiss").exists()

    def build_from_docs(self, docs: List[Dict[str, Any]]) -> FAISS:
        lc_docs = [
            Document(page_content=d["text"], metadata=d.get("metadata", {}))
            for d in docs
        ]
        return FAISS.from_documents(lc_docs, self.embeddings)

    def save(self, vs: FAISS) -> None:
        self.cfg.vector_dir.mkdir(parents=True, exist_ok=True)
        vs.save_local(str(self.cfg.vector_dir))

    def load(self) -> FAISS:
        return FAISS.load_local(
            str(self.cfg.vector_dir),
            self.embeddings,
            allow_dangerous_deserialization=True,
        )
