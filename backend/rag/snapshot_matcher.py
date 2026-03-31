# backend/rag/snapshot_matcher.py
"""
Snapshot-first metric lookup — matches user questions to pre-computed
KPI cards, forecast metrics, and action plan health score.

Two-tier matching:
  Tier 1: Fast keyword/alias substring matching (free, instant)
  Tier 2: Lightweight LLM fallback for creative phrasings (gpt-4o-mini, ~300ms)

Skips analytical questions (containing "why", "trend", "compare", etc.)
so they still route to the retrieval handler.
"""
from __future__ import annotations

import re
import json
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Match result
# ---------------------------------------------------------------------------

@dataclass
class MatchResult:
    card_id: str
    source: str = "kpi"  # "kpi" or "forecast"


# ---------------------------------------------------------------------------
# KPI alias dictionary
# ---------------------------------------------------------------------------

KPI_ALIASES: Dict[str, List[str]] = {
    # Revenue & Sales Health
    "aov": ["aov", "average order value", "avg order value"],
    "rev_mtd": ["revenue mtd", "revenue month to date", "revenue this month", "mtd revenue", "monthly revenue"],
    "rev_qtd": ["revenue qtd", "revenue quarter to date", "qtd revenue", "revenue this quarter", "quarterly revenue"],
    "rev_ytd": ["revenue ytd", "revenue year to date", "ytd revenue", "total revenue", "yearly revenue", "annual revenue"],
    "rev_growth_30d": ["revenue growth", "revenue change", "revenue growth rate"],
    "orders_day": ["orders per day", "daily orders"],
    "orders_week": ["orders per week", "weekly orders"],
    # Net Revenue
    "gross_revenue": ["gross revenue"],
    "net_revenue": ["net revenue"],
    "total_discounts": ["total discounts", "discount amount", "total discount"],
    "total_returns": ["total returns", "returns value"],
    "total_refunds": ["total refunds", "refund amount"],
    "total_fees": ["total fees", "transaction fees", "total transaction fees"],
    "discount_rate": ["discount rate"],
    # Customer Health
    "active_customers_30d": ["active customers", "active users", "how many active customers"],
    "new_customers_30d": ["new customers", "how many new customers"],
    "returning_customers_30d": ["returning customers", "repeat customers"],
    "repeat_purchase_rate": ["repeat purchase rate", "repurchase rate"],
    "retention_rate_proxy": ["retention rate", "customer retention"],
    "churn_rate_proxy": ["churn rate", "churn", "customer churn"],
    "avg_clv": ["average clv", "avg clv", "customer lifetime value", "clv", "ltv", "lifetime value"],
    "median_clv": ["median clv", "median lifetime value"],
    # Funnel
    "conversion_rate": ["conversion rate", "cvr", "overall conversion"],
    "cart_abandonment_rate": ["cart abandonment", "abandonment rate", "cart abandonment rate"],
    "checkout_completion_rate": ["checkout completion", "checkout rate", "checkout completion rate"],
    "product_view_rate": ["product view rate"],
    "bounce_rate": ["bounce rate"],
    "time_to_purchase": ["time to purchase", "purchase time"],
    "avg_session_duration": ["session duration", "average session duration", "avg session duration"],
    "revenue_per_session": ["revenue per session"],
    "mobile_conversion_rate": ["mobile conversion", "mobile conversion rate"],
    "desktop_conversion_rate": ["desktop conversion", "desktop conversion rate"],
    # Marketing
    "cac": ["cac", "customer acquisition cost", "acquisition cost"],
    "roas": ["roas", "return on ad spend"],
    "campaign_cr": ["campaign conversion rate", "campaign conversion"],
    "best_campaign": ["best campaign", "best performing campaign", "top campaign"],
    "worst_campaign": ["worst campaign", "worst performing campaign"],
    "promo_uplift": ["promo uplift", "promotion uplift", "promotional uplift"],
    # Payments
    "payment_failure_rate": ["payment failure rate", "payment failures", "failed payments"],
    "payment_refund_rate": ["payment refund rate", "refund rate"],
    "top_payment_method": ["top payment method", "most used payment method", "popular payment method"],
    "avg_transaction_fee": ["average transaction fee", "avg transaction fee", "transaction fee"],
    # Product & Merchandising
    "avg_margin_pct": ["average margin", "product margin", "avg margin", "average product margin"],
    "return_rate_proxy": ["return rate", "product return rate"],
    # Inventory & Ops
    "stock_out_risk_pct": ["stock out risk", "stockout risk", "out of stock risk", "stockout"],
    "inventory_turnover_proxy": ["inventory turnover"],
    # Demographics
    "customers_by_gender": ["customers by gender", "gender distribution", "gender breakdown"],
    "customers_by_age_group": ["customers by age", "age distribution", "age breakdown", "age group"],
    "customers_by_loyalty": ["customers by loyalty", "loyalty tier", "loyalty distribution"],
    "avg_spend_by_loyalty": ["spend by loyalty", "average spend by loyalty"],
    # Brand
    "top_brands_revenue": ["top brands", "brands by revenue", "best brands"],
    "brand_count": ["total brands", "number of brands", "how many brands", "brand count"],
    # Supplier
    "supplier_stockouts": ["stockouts by supplier", "supplier stockouts"],
    "supplier_reliability": ["supplier reliability", "supplier reliability scores"],
}

# ---------------------------------------------------------------------------
# Forecast & action plan alias dictionaries
# ---------------------------------------------------------------------------

FORECAST_ALIASES: Dict[str, List[str]] = {
    "revenue_forecast_7d": [
        "revenue forecast 7 day", "forecasted revenue 7d", "revenue next 7 days",
        "revenue next week", "next week revenue",
    ],
    "revenue_forecast_30d": [
        "revenue forecast 30 day", "forecasted revenue 30d", "revenue next 30 days",
        "revenue next month forecast", "revenue forecast next month",
        "revenue forecast", "forecasted revenue",
    ],
    "revenue_forecast_90d": [
        "revenue forecast 90 day", "forecasted revenue 90d", "revenue next 90 days",
        "revenue next quarter forecast", "revenue forecast next quarter",
    ],
    "churn_forecast": [
        "churn forecast", "expected churn", "predicted churn",
        "churn prediction", "forecasted churn rate", "churn next month",
    ],
    "cashflow_forecast": [
        "cashflow forecast", "cash flow forecast", "projected cashflow",
        "cashflow next month", "projected cash flow",
    ],
    "health_score": [
        "health score", "business health", "store health",
        "overall health", "business health score",
    ],
}

# All valid card IDs for LLM fallback validation
VALID_CARD_IDS = set(KPI_ALIASES.keys()) | set(FORECAST_ALIASES.keys())


# ---------------------------------------------------------------------------
# Analytical guard — skip snapshot for analytical questions
# ---------------------------------------------------------------------------

ANALYTICAL_SIGNALS = [
    "why", "how to", "explain", "what caused", "what drove",
    "what should", "recommend", "suggest", "improve", "optimize",
    "compare", "trend", "over time", "vs", "versus",
    "increasing", "decreasing", "declining", "growing",
    "analyze", "analysis", "strategy", "opportunity",
    "which products", "who should", "what happened",
]


def _is_analytical(query_lower: str) -> bool:
    """Return True if the query asks for analysis, not just a metric value."""
    return any(signal in query_lower for signal in ANALYTICAL_SIGNALS)


# ---------------------------------------------------------------------------
# Tier 1: Keyword alias matching
# ---------------------------------------------------------------------------

def _normalize(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _tier1_match(query_norm: str) -> Optional[MatchResult]:
    """
    Substring-match against alias lists (KPI + forecast + action plan).
    Returns the match with the longest alias (most specific).
    """
    best_id: Optional[str] = None
    best_source: str = "kpi"
    best_len: int = 0

    for card_id, aliases in KPI_ALIASES.items():
        for alias in aliases:
            if alias in query_norm and len(alias) > best_len:
                best_id = card_id
                best_source = "kpi"
                best_len = len(alias)

    for card_id, aliases in FORECAST_ALIASES.items():
        source = "action_plan" if card_id == "health_score" else "forecast"
        for alias in aliases:
            if alias in query_norm and len(alias) > best_len:
                best_id = card_id
                best_source = source
                best_len = len(alias)

    if best_id is not None:
        return MatchResult(card_id=best_id, source=best_source)
    return None


# ---------------------------------------------------------------------------
# Tier 2: LLM fallback
# ---------------------------------------------------------------------------

_LLM_MATCH_PROMPT = """You are a metric classifier. Given a user question, determine if it is asking for a specific KPI metric value.

Available KPI metrics (id: title):
{card_list}

Instructions:
- If the question is asking for the value of one of these metrics, return ONLY the metric id (e.g., "aov").
- If the question does NOT ask for a specific metric value, return "none".
- Return ONLY the id or "none", nothing else.

User question: {question}

Answer:"""


def _tier2_match(question: str, llm) -> Optional[MatchResult]:
    """
    Use a lightweight LLM call to match the question to a KPI card.
    """
    # Build compact card list for the prompt
    card_titles = {
        "aov": "Average Order Value (AOV)",
        "rev_mtd": "Total Revenue (MTD)",
        "rev_qtd": "Total Revenue (QTD)",
        "rev_ytd": "Total Revenue (YTD)",
        "rev_growth_30d": "Revenue Growth (30d)",
        "orders_day": "Orders per Day",
        "orders_week": "Orders per Week",
        "gross_revenue": "Gross Revenue",
        "net_revenue": "Net Revenue",
        "total_discounts": "Total Discounts",
        "total_returns": "Total Returns Value",
        "total_refunds": "Total Refunds",
        "total_fees": "Total Transaction Fees",
        "discount_rate": "Discount Rate",
        "active_customers_30d": "Active Customers (30d)",
        "new_customers_30d": "New Customers (30d)",
        "returning_customers_30d": "Returning Customers",
        "repeat_purchase_rate": "Repeat Purchase Rate",
        "retention_rate_proxy": "Retention Rate",
        "churn_rate_proxy": "Churn Rate",
        "avg_clv": "Average Customer Lifetime Value",
        "median_clv": "Median Customer Lifetime Value",
        "conversion_rate": "Conversion Rate",
        "cart_abandonment_rate": "Cart Abandonment Rate",
        "checkout_completion_rate": "Checkout Completion Rate",
        "product_view_rate": "Product View Rate",
        "bounce_rate": "Bounce Rate",
        "time_to_purchase": "Avg Time to Purchase",
        "avg_session_duration": "Avg Session Duration",
        "revenue_per_session": "Revenue per Session",
        "mobile_conversion_rate": "Mobile Conversion Rate",
        "desktop_conversion_rate": "Desktop Conversion Rate",
        "cac": "Customer Acquisition Cost",
        "roas": "Return on Ad Spend (ROAS)",
        "campaign_cr": "Campaign Conversion Rate",
        "best_campaign": "Best Performing Campaign",
        "worst_campaign": "Worst Performing Campaign",
        "promo_uplift": "Promo Uplift",
        "payment_failure_rate": "Payment Failure Rate",
        "payment_refund_rate": "Payment Refund Rate",
        "top_payment_method": "Top Payment Method",
        "avg_transaction_fee": "Avg Transaction Fee",
        "avg_margin_pct": "Average Product Margin",
        "return_rate_proxy": "Return Rate",
        "stock_out_risk_pct": "Stock-Out Risk",
        "inventory_turnover_proxy": "Inventory Turnover",
        "customers_by_gender": "Customers by Gender",
        "customers_by_age_group": "Customers by Age Group",
        "customers_by_loyalty": "Customers by Loyalty Tier",
        "avg_spend_by_loyalty": "Avg Spend by Loyalty Tier",
        "top_brands_revenue": "Top Brands by Revenue",
        "brand_count": "Total Brands",
        "supplier_stockouts": "Stockouts by Supplier",
        "supplier_reliability": "Supplier Reliability Scores",
        # Forecast metrics
        "revenue_forecast_7d": "Revenue Forecast (next 7 days)",
        "revenue_forecast_30d": "Revenue Forecast (next 30 days)",
        "revenue_forecast_90d": "Revenue Forecast (next 90 days)",
        "churn_forecast": "Churn Forecast (next 30 days)",
        "cashflow_forecast": "Cashflow Forecast (next 30 days)",
        # Action plan
        "health_score": "Overall Business Health Score",
    }

    card_list = "\n".join(f"- {cid}: {title}" for cid, title in card_titles.items())
    prompt = _LLM_MATCH_PROMPT.format(card_list=card_list, question=question)

    try:
        response = llm.invoke(prompt).content.strip().lower()
        # Extract just the card ID (strip quotes, whitespace)
        response = re.sub(r"[^a-z0-9_]", "", response)

        if response in VALID_CARD_IDS:
            logger.info("Tier 2 LLM matched '%s' → %s", question[:60], response)
            if response in FORECAST_ALIASES:
                source = "action_plan" if response == "health_score" else "forecast"
            else:
                source = "kpi"
            return MatchResult(card_id=response, source=source)
    except Exception as e:
        logger.warning("Tier 2 LLM match failed: %s", e)

    return None


# ---------------------------------------------------------------------------
# Public API: match_snapshot_metric
# ---------------------------------------------------------------------------

def match_snapshot_metric(
    query: str,
    llm=None,
) -> Optional[MatchResult]:
    """
    Try to match a user question to a pre-computed KPI metric.

    Tier 1: Fast keyword alias matching (no LLM).
    Tier 2: LLM fallback if llm is provided and Tier 1 found nothing.

    Returns None if no match or if the query is analytical.
    """
    query_norm = _normalize(query)

    # Guard: skip analytical questions
    if _is_analytical(query_norm):
        return None

    # Tier 1: keyword alias match
    result = _tier1_match(query_norm)
    if result is not None:
        logger.info("Tier 1 alias matched '%s' → %s", query[:60], result.card_id)
        return result

    # Tier 2: LLM fallback
    if llm is not None:
        return _tier2_match(query, llm)

    return None


# ---------------------------------------------------------------------------
# Response formatting
# ---------------------------------------------------------------------------

def format_snapshot_response(
    card: Dict[str, Any],
    all_cards: List[Dict[str, Any]],
) -> str:
    """
    Format a KPI card into a natural-language answer.
    Includes 1-2 related metrics from the same group.
    """
    title = card.get("title", card.get("id", "Unknown"))
    value = card.get("value")
    unit = card.get("unit", "")
    fmt = card.get("format", "")
    group = card.get("group", "")
    card_id = card.get("id", "")

    # Format the main value
    display = _format_value(value, fmt, unit)

    parts = [f"The **{title}** is **{display}**."]

    # Add 1-2 related metrics from the same group
    related = [
        c for c in all_cards
        if c.get("group") == group
        and c.get("id") != card_id
        and c.get("value") is not None
    ]
    if related:
        rel_lines = []
        for r in related[:2]:
            r_display = _format_value(r.get("value"), r.get("format", ""), r.get("unit", ""))
            rel_lines.append(f"- {r.get('title', r.get('id', ''))}: {r_display}")
        parts.append("\n**Related metrics:**")
        parts.extend(rel_lines)

    parts.append("\n_Source: Dashboard KPI snapshot (computed from cleaned data)_")

    return "\n".join(parts)


def format_forecast_response(card_id: str, snapshot: Dict[str, Any]) -> Optional[str]:
    """Format a forecast metric into a natural-language answer."""
    forecasts = snapshot.get("forecasts", {})

    if card_id == "revenue_forecast_7d":
        rev = forecasts.get("forecasted_revenue", {})
        val = rev.get("next_7d")
        if val is None:
            return None
        display = f"${val:,.2f}" if isinstance(val, (int, float)) else str(val)
        parts = [f"The **forecasted revenue for the next 7 days** is **{display}**."]
        for key, label in [("next_30d", "Next 30 days"), ("next_90d", "Next 90 days")]:
            v = rev.get(key)
            if v is not None and isinstance(v, (int, float)):
                parts.append(f"- {label}: ${v:,.2f}")
        parts.append("\n_Source: Forecast snapshot (computed from cleaned data)_")
        return "\n".join(parts)

    if card_id == "revenue_forecast_30d":
        rev = forecasts.get("forecasted_revenue", {})
        val = rev.get("next_30d")
        if val is None:
            return None
        display = f"${val:,.2f}" if isinstance(val, (int, float)) else str(val)
        parts = [f"The **forecasted revenue for the next 30 days** is **{display}**."]
        for key, label in [("next_7d", "Next 7 days"), ("next_90d", "Next 90 days")]:
            v = rev.get(key)
            if v is not None and isinstance(v, (int, float)):
                parts.append(f"- {label}: ${v:,.2f}")
        parts.append("\n_Source: Forecast snapshot (computed from cleaned data)_")
        return "\n".join(parts)

    if card_id == "revenue_forecast_90d":
        rev = forecasts.get("forecasted_revenue", {})
        val = rev.get("next_90d")
        if val is None:
            return None
        display = f"${val:,.2f}" if isinstance(val, (int, float)) else str(val)
        parts = [f"The **forecasted revenue for the next 90 days** is **{display}**."]
        for key, label in [("next_7d", "Next 7 days"), ("next_30d", "Next 30 days")]:
            v = rev.get(key)
            if v is not None and isinstance(v, (int, float)):
                parts.append(f"- {label}: ${v:,.2f}")
        parts.append("\n_Source: Forecast snapshot (computed from cleaned data)_")
        return "\n".join(parts)

    if card_id == "churn_forecast":
        churn = forecasts.get("expected_churn_next_month", {})
        rate = churn.get("expected_churn_rate_next_30d")
        if rate is None:
            return None
        if isinstance(rate, (int, float)) and abs(rate) < 1:
            display = f"{rate * 100:.1f}%"
        elif isinstance(rate, (int, float)):
            display = f"{rate:.1f}%"
        else:
            display = str(rate)
        parts = [
            f"The **expected churn rate for the next 30 days** is **{display}**.",
            f"Definition: {churn.get('definition', 'no purchase in next 30 days')}",
        ]
        parts.append("\n_Source: Forecast snapshot (computed from cleaned data)_")
        return "\n".join(parts)

    if card_id == "cashflow_forecast":
        cf = forecasts.get("projected_cashflow", {})
        val = cf.get("next_30d_cash_proxy")
        if val is None:
            return None
        display = f"${val:,.2f}" if isinstance(val, (int, float)) else str(val)
        parts = [
            f"The **projected cashflow for the next 30 days** is **{display}**.",
            f"Note: {cf.get('note', 'Proxy cashflow = revenue - refunds')}",
        ]
        parts.append("\n_Source: Forecast snapshot (computed from cleaned data)_")
        return "\n".join(parts)

    return None


def format_action_plan_response(card_id: str, snapshot: Dict[str, Any]) -> Optional[str]:
    """Format an action plan metric into a natural-language answer."""
    if card_id == "health_score":
        score = snapshot.get("health_score")
        if score is None:
            return None
        parts = [f"The **overall business health score** is **{score}/100**."]
        summary = snapshot.get("health_summary", "")
        if summary:
            parts.append(f"\n{summary}")
        prescriptions = snapshot.get("prescriptions", [])
        if prescriptions:
            critical = sum(1 for p in prescriptions if p.get("urgency") == "critical")
            high = sum(1 for p in prescriptions if p.get("urgency") == "high")
            parts.append(f"\nActive prescriptions: {len(prescriptions)} (critical: {critical}, high: {high})")
        parts.append("\n_Source: Action plan snapshot (computed from cleaned data)_")
        return "\n".join(parts)

    return None


def _format_value(value: Any, fmt: str, unit: str) -> str:
    """Format a single metric value for display."""
    if value is None:
        return "N/A"

    if fmt == "currency" and isinstance(value, (int, float)):
        return f"${value:,.2f}"
    elif fmt == "percent" and isinstance(value, (int, float)):
        if abs(value) < 1:
            # Already a fraction (e.g., 0.15 = 15%)
            return f"{value * 100:.1f}%"
        else:
            # Already a percentage (e.g., 15.0)
            return f"{value:.1f}%"
    elif fmt == "number" and isinstance(value, (int, float)):
        if isinstance(value, int) or value == int(value):
            return f"{int(value):,}"
        return f"{value:,.2f}"
    elif fmt == "text":
        return str(value)
    elif fmt == "json" and isinstance(value, dict):
        items = list(value.items())[:5]
        return ", ".join(f"{k}: {v}" for k, v in items)
    elif fmt == "minutes" and isinstance(value, (int, float)):
        return f"{value:.1f} min"
    else:
        display = str(value)
        if unit:
            display += f" {unit}"
        return display
