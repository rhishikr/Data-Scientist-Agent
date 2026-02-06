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

You are in SCHEMA-HELP mode.
Use ONLY the provided CONTEXT to:
- explain what tables/columns mean if asked
- describe which table likely answers a question if asked
- explain how to compute something (without making up numeric results)if asked


IMPORTANT:
- Do NOT invent numbers or claim computed results.
- If the user asks for "most", "top", "highest", totals, averages, or rankings, explain which table/columns to use and what computation is needed.
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

def _is_aggregation_question(q: str) -> bool:
    q = q.lower()
    keywords = [
        "most", "highest", "top", "best", "spent", "spend", "popular", "expensive",
        "max", "minimum", "min", "sum", "total", "average", "avg", "count", "rank"
    ]
    return any(k in q for k in keywords)


def _try_deterministic_analytics(tool: DataTool, question: str) -> Optional[Dict[str, Any]]:
    q = question.lower()

    # ---- (1) Most popular product (units sold) ----
    if "popular" in q and "product" in q:
        # transactions: group by sku, sum(quantity)
        top = tool.top_k(
            table="transactions.csv",
            group_by=["sku"],
            metric_col="quantity",
            metric_agg="sum",
            k=1,
            metric_name="units_sold",
        )
        if top:
            sku = top[0].get("sku")
            units = top[0].get("units_sold")

            # optional: map sku -> product name
            name = tool.lookup_value("products.csv", "sku", sku, "name")
            product_label = f"{name} (SKU {sku})" if name else f"SKU {sku}"

            return {
                "answer": f"The most popular product (by units sold) is {product_label}, with {units} units sold.",
                "mode": "analytics",
                "metric": "units_sold",
                "table_used": "transactions.csv",
                "evidence": top,
            }

    # ---- (2) Best spender (highest total_amount by customer_id) ----
    if ("spent the most" in q) or ("best spender" in q) or ("spent most" in q) or ("highest spender" in q):
        top = tool.top_k(
            table="transactions.csv",
            group_by=["customer_id"],
            metric_col="total_amount",
            metric_agg="sum",
            k=1,
            metric_name="total_spend",
        )
        if top:
            cust = top[0].get("customer_id")
            spend = top[0].get("total_spend")

            # optional: map customer_id -> name
            name = tool.lookup_value("customers.csv", "customer_id", cust, "name")
            customer_label = f"{name} ({cust})" if name else str(cust)

            return {
                "answer": f"The customer who spent the most is {customer_label}, with a total spend of {spend}.",
                "mode": "analytics",
                "metric": "total_spend",
                "table_used": "transactions.csv",
                "evidence": top,
            }

    # ---- (3) Most expensive product (max retail_price) ----
    if ("most expensive" in q) and ("product" in q):
        max_price = tool.max_value("products.csv", "retail_price")
        # If you want the actual product (not just the price), use group/sort:
        # Here’s a safe way without adding new DataTool methods:
        rows = tool.filter_rows(
            "products.csv",
            conditions=[{"col": "retail_price", "op": "==", "value": max_price}],
            limit=1,
        )
        if rows:
            sku = rows[0].get("sku")
            name = rows[0].get("name")
            label = f"{name} (SKU {sku})" if name and sku else (name or sku or "the top-priced product")
            return {
                "answer": f"The most expensive product is {label}, priced at {max_price}.",
                "mode": "analytics",
                "metric": "max_retail_price",
                "table_used": "products.csv",
                "evidence": rows,
            }
        return {
            "answer": f"The highest retail_price in products.csv is {max_price}.",
            "mode": "analytics",
            "metric": "max_retail_price",
            "table_used": "products.csv",
            "evidence": [{"max_retail_price": max_price}],
        }

    return None

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
        # ---------- Step 2: Deterministic analytics (SQL-ish questions) ----------
    analytics = _try_deterministic_analytics(tool, question)
    if analytics is not None:
        return analytics

    # ---------- Step 2: RAG fallback ----------
    store = FaissStore(cfg)

    if not store.index_exists():
        return {"error": "Vector index not found. Call POST /rag/ingest first."}
    
        # If it's an aggregation question but we couldn't handle it deterministically,
    # do NOT fall back to RAG guessing. Tell the user what's missing.
    if _is_aggregation_question(question):
        return {
            "answer": "I can answer that, but I need a supported deterministic operation or a clearer metric/table mapping. "
                      "Try specifying the table and metric (e.g., 'in transactions.csv, who has the highest sum of total_amount?').",
            "mode": "needs_clarification",
        }

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

def schema_help(base_dir: Path, question: str) -> Dict[str, Any]:
    cfg = load_config(base_dir)
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

    llm = ChatOpenAI(model=cfg.llm_model, temperature=0.0)
    prompt = f"QUESTION:\n{question}\n\nCONTEXT:\n{context}"

    answer = llm.invoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ]).content

    return {
        "answer": answer,
        "citations": citations,
        "top_k": cfg.top_k,
        "mode": "schema",
    }
