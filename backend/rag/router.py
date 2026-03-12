# backend/rag/router.py
"""
Query classification — routes questions to sql, insight, or hybrid handlers.
Two-tier: fast pattern matching first, LLM fallback when ambiguous.
"""
from typing import Literal

QueryType = Literal["snapshot", "sql", "insight", "hybrid"]

# ---------------------------------------------------------------------------
# Tier 1: Pattern-based (free, instant)
# ---------------------------------------------------------------------------

SQL_PATTERNS = [
    "revenue", "total", "sum", "average", "count", "top", "bottom",
    "last month", "this month", "last quarter", "year over year",
    "how many", "what was", "compare", "trend", "growth rate",
    "highest", "lowest", "most", "least", "sales", "orders",
    "customers", "products", "inventory", "stock", "payment",
    "spent", "spend", "price", "cost", "profit", "margin",
    "conversion rate", "churn rate", "retention",
]

INSIGHT_PATTERNS = [
    "why", "how to", "what should", "recommend", "suggest",
    "opportunity", "risk", "improve", "optimize", "strategy",
    "best practice", "what drives", "what causes", "explain",
    "action", "advice", "insight", "diagnosis",
]

HYBRID_PATTERNS = [
    "why did", "what drove", "what caused the", "explain the",
    "what opportunities", "which products should we", "who should we target",
    "analyze and recommend", "what happened and what should",
]


def _pattern_score(query_lower: str) -> QueryType:
    """Score query against pattern lists and return best match."""
    # Check hybrid first (most specific)
    for p in HYBRID_PATTERNS:
        if p in query_lower:
            return "hybrid"

    sql_score = sum(1 for p in SQL_PATTERNS if p in query_lower)
    insight_score = sum(1 for p in INSIGHT_PATTERNS if p in query_lower)

    if sql_score > insight_score:
        return "sql"
    elif insight_score > sql_score:
        return "insight"
    else:
        return None  # ambiguous — fall through to LLM


# ---------------------------------------------------------------------------
# Tier 2: LLM fallback
# ---------------------------------------------------------------------------

CLASSIFICATION_PROMPT = """Classify this business query into ONE category:

Categories:
- "sql": Requires data calculations, aggregations, filtering, trends, or comparisons
  Examples: "What was revenue last month?", "Top 10 products by sales", "Customer churn rate"

- "insight": Asks for strategic insights, recommendations, patterns, or business intelligence
  Examples: "Why are sales declining?", "What opportunities exist?", "How to improve conversion?"

- "hybrid": Needs both data analysis AND strategic insights
  Examples: "What drove the revenue spike and what should we do?", "Which products are declining and why?"

Query: {query}

Classification (respond with ONLY 'sql', 'insight', or 'hybrid'):"""


def _llm_classify(query: str, llm) -> QueryType:
    """Use LLM to classify the query."""
    response = llm.invoke(
        CLASSIFICATION_PROMPT.format(query=query)
    ).content.strip().lower()

    if "hybrid" in response:
        return "hybrid"
    elif "insight" in response:
        return "insight"
    return "sql"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def classify_query(query: str, llm=None) -> QueryType:
    """
    Classify a query into sql/insight/hybrid.
    Uses pattern matching first (free), falls back to LLM if ambiguous.
    """
    query_lower = query.lower()
    result = _pattern_score(query_lower)

    if result is not None:
        return result

    # Ambiguous — use LLM if available, otherwise default to sql
    if llm is not None:
        return _llm_classify(query, llm)

    return "sql"
