# backend/rag/service.py
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import re

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from .config import load_config
from .store_faiss import FaissStore
from .tools import DataTool


SYSTEM_PROMPT = """You are an AI Data Scientist assistant.
Answer the user's question using ONLY the provided CONTEXT retrieved from the dataset index.
If the context is insufficient, say what is missing (which table/column/time window) and how to get it.
Be concise and business-actionable.
"""


# -------------------------
# Lookup routing (POC)
# -------------------------

def _extract_customer_id(question: str) -> Optional[str]:
    # Match CUST1007, cust1007, etc.
    m = re.search(r"\bCUST\d+\b", question.upper())
    return m.group(0) if m else None

def _extract_product_id(question: str) -> Optional[str]:
    """
    Match product ids like AA-10, AB-123, etc.
    This is intentionally simple for POC.
    """
    m = re.search(r"\b[A-Z]{2,5}-\d+\b", question.upper())
    return m.group(0) if m else None


def try_customer_location_lookup(tool: DataTool, customer_id: str) -> Optional[str]:
    # Try common key/target column combinations
    key_cols = ["customer_id", "cust_id", "id"]
    target_cols = ["location", "city", "province", "region"]

    for key in key_cols:
        for target in target_cols:
            val = tool.lookup_value("customers.csv", key, customer_id, target)
            if val is not None:
                return str(val)
    return None


def try_product_name_lookup(tool: DataTool, product_id: str) -> Optional[str]:
    """
    Try to map product_id -> product name using common schemas.
    """
    key_cols = ["product_id", "sku", "productID", "id"]
    target_cols = ["name", "product_name", "title", "product"]

    for key in key_cols:
        for target in target_cols:
            val = tool.lookup_value("products.csv", key, product_id, target)
            if val is not None:
                return str(val)
    return None


def answer_question(base_dir: Path, question: str) -> Dict[str, Any]:
    cfg = load_config(base_dir)

    # ---------- Step 1: Deterministic lookup ----------
    tool = DataTool.from_csv_dir(cfg.data_dir)

    cust_id = _extract_customer_id(question)
    if cust_id and ("location" in question.lower() or "where" in question.lower()):
        loc = try_customer_location_lookup(tool, cust_id)
        if loc is not None:
            return {
                "answer": f"The location of customer {cust_id} is {loc}.",
                "mode": "lookup",
                "source": "customers.csv",
            }

    prod_id = _extract_product_id(question)
    if prod_id and ("name" in question.lower() or "product" in question.lower() or "title" in question.lower()):
        name = try_product_name_lookup(tool, prod_id)
        if name is not None:
            return {
                "answer": f"The name of product {prod_id} is {name}.",
                "mode": "lookup",
                "source": "products.csv",
            }

    # ---------- Step 2: RAG fallback ----------
    store = FaissStore(cfg)

    if not store.index_exists():
        return {"error": "Vector index not found. Call POST /rag/ingest first."}

    vs = store.load()
    retrieved = vs.similarity_search(question, k=cfg.top_k)

    context_parts: List[str] = []
    citations: List[Dict[str, Any]] = []
    for d in retrieved:
        context_parts.append(d.page_content)
        citations.append(d.metadata or {})

    context = "\n\n---\n\n".join(context_parts)

    llm = ChatOpenAI(model=cfg.llm_model, temperature=0.2)
    prompt = f"QUESTION:\n{question}\n\nCONTEXT:\n{context}"

    answer = llm.invoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ]).content

    return {
        "answer": answer,
        "citations": citations,
        "top_k": cfg.top_k,
        "mode": "rag",
    }
