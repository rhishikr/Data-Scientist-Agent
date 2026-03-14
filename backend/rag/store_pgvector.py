# backend/rag/store_pgvector.py
"""
pgvector-backed document store for RAG.
Replaces the previous FAISS store — all embeddings live in Supabase PostgreSQL.
"""
from typing import List, Dict, Any, Optional
import logging

from sqlalchemy import create_engine, text
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document

from .config import RagConfig

logger = logging.getLogger(__name__)

# Module-level engine singleton (lazy)
_engine = None


def _get_engine(db_url: str):
    global _engine
    if _engine is None:
        _engine = create_engine(db_url, pool_pre_ping=True, pool_size=5)
    return _engine


class PgVectorStore:
    """
    Thin wrapper around Supabase pgvector for document storage and retrieval.
    """

    def __init__(self, cfg: RagConfig):
        self.cfg = cfg
        self.engine = _get_engine(cfg.db_url)
        self.embeddings = OpenAIEmbeddings(model=cfg.embed_model)

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def upsert_documents(self, docs: List[Dict[str, Any]]) -> int:
        """
        Embed and insert documents into rag_documents.
        Deletes existing docs per source category before inserting (full replace).

        Each doc: {"text": str, "metadata": dict}
        metadata must include "source" (e.g. "table_profile", "insight").
        """
        if not docs:
            return 0

        # Group by source for batch delete
        sources = set(d.get("metadata", {}).get("source", "unknown") for d in docs)

        # Embed all texts
        texts = [d["text"] for d in docs]
        vectors = self.embeddings.embed_documents(texts)

        with self.engine.begin() as conn:
            # Delete old docs for each source category
            for src in sources:
                conn.execute(
                    text("DELETE FROM rag_documents WHERE source = :src"),
                    {"src": src},
                )

            # Batch insert
            for doc, vec in zip(docs, vectors):
                meta = doc.get("metadata", {})
                conn.execute(
                    text("""
                        INSERT INTO rag_documents (content, metadata, embedding, source, source_id)
                        VALUES (:content, :metadata, :embedding, :source, :source_id)
                    """),
                    {
                        "content": doc["text"],
                        "metadata": _json_dumps(meta),
                        "embedding": _vec_literal(vec),
                        "source": meta.get("source", "unknown"),
                        "source_id": meta.get("source_id"),
                    },
                )

        logger.info("Upserted %d documents (sources: %s)", len(docs), sources)
        return len(docs)

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def similarity_search(self, query: str, k: Optional[int] = None) -> List[Document]:
        """
        Embed the query and return the k most similar documents.
        """
        k = k or self.cfg.top_k
        query_vec = self.embeddings.embed_query(query)

        with self.engine.connect() as conn:
            rows = conn.execute(
                text("""
                    SELECT content, metadata, 1 - (embedding <=> :qvec) AS similarity
                    FROM rag_documents
                    ORDER BY embedding <=> :qvec
                    LIMIT :k
                """),
                {"qvec": _vec_literal(query_vec), "k": k},
            ).fetchall()

        results = []
        for row in rows:
            meta = row.metadata if isinstance(row.metadata, dict) else {}
            meta["similarity"] = round(row.similarity, 4)
            results.append(Document(page_content=row.content, metadata=meta))
        return results

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def delete_by_source(self, source: str) -> int:
        with self.engine.begin() as conn:
            result = conn.execute(
                text("DELETE FROM rag_documents WHERE source = :src"),
                {"src": source},
            )
            return result.rowcount

    def doc_count(self) -> int:
        with self.engine.connect() as conn:
            row = conn.execute(text("SELECT count(*) FROM rag_documents")).fetchone()
            return row[0] if row else 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _vec_literal(vec: List[float]) -> str:
    """Format a vector as a pgvector literal string '[0.1,0.2,...]'."""
    return "[" + ",".join(f"{v:.8f}" for v in vec) + "]"


def _json_dumps(obj: Any) -> str:
    import json
    return json.dumps(obj, default=str)
