# backend/rag/etl.py
"""
ETL: Build embeddable documents from Supabase data sources.

All data is read from Supabase (cleaned datasets + pipeline snapshot tables).
Cleaned data is required; an error is logged if none is available.
No local file dependencies.

Each builder returns a list of dicts:
    {"text": str, "metadata": {"source": str, "source_id": str, ...}}
"""
from typing import List, Dict, Any, Optional
from collections import defaultdict
import logging

import pandas as pd

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper: build profile + sample docs from a DataFrame
# ---------------------------------------------------------------------------

def _build_docs_from_df(
    df: pd.DataFrame,
    table_name: str,
    max_sample_rows: int = 100,
    max_cols_per_row: int = 20,
) -> List[Dict[str, Any]]:
    """Build profile + sample documents from a single DataFrame."""
    docs: List[Dict[str, Any]] = []

    if df.empty:
        return docs

    # Profile doc
    missing = df.isna().mean().sort_values(ascending=False).head(15)
    profile_lines = [
        f"TABLE: {table_name}",
        f"ROWS: {len(df)}",
        f"COLS: {df.shape[1]}",
        "",
        "COLUMNS (name : dtype):",
        *[f"- {c}: {df[c].dtype}" for c in df.columns],
        "",
        "TOP MISSINGNESS (fraction):",
        *[f"- {k}: {v:.3f}" for k, v in missing.items()],
        "",
        "HEAD (5 rows):",
        df.head(5).to_string(index=False),
    ]
    docs.append({
        "text": "\n".join(profile_lines),
        "metadata": {"source": "table_profile", "source_id": table_name, "doc_type": "profile"},
    })

    # Sampled rows doc
    if len(df) > 0 and max_sample_rows > 0:
        sample = df.sample(min(len(df), max_sample_rows), random_state=42)
        cols = list(df.columns)[:max_cols_per_row]

        rows_text = []
        for _, row in sample.iterrows():
            pairs = [f"{c}={row[c]}" for c in cols]
            rows_text.append(f"{table_name} | " + " | ".join(pairs))

        docs.append({
            "text": "\n".join(rows_text),
            "metadata": {"source": "rows_sample", "source_id": table_name, "doc_type": "rows_sample"},
        })

    return docs


# ---------------------------------------------------------------------------
# 1. Table profiles + sampled rows  (from cleaned data only)
# ---------------------------------------------------------------------------

def build_table_profile_documents(
    run_id: Optional[str] = None,
    max_sample_rows: int = 100,
    max_cols_per_row: int = 20,
) -> List[Dict[str, Any]]:
    """
    Build profile + sample documents from cleaned datasets of a pipeline run.
    Logs an error and returns empty if no cleaned data is available.
    """
    docs = _build_from_cleaned(run_id, max_sample_rows, max_cols_per_row)
    if not docs:
        logger.error("No cleaned datasets found. Skipping table profile ingestion. "
                      "Run the pipeline to generate cleaned data before rebuilding the RAG index.")
    return docs


def _build_from_cleaned(
    run_id: Optional[str],
    max_sample_rows: int,
    max_cols_per_row: int,
) -> List[Dict[str, Any]]:
    """Build documents from cleaned datasets of a specific (or latest) pipeline run."""
    from db.store import get_latest_run_id, get_cleaned_datasets, download_cleaned_csv

    if run_id is None:
        run_id = get_latest_run_id()
    if run_id is None:
        logger.info("No completed pipeline run found")
        return []

    cleaned_tables = get_cleaned_datasets(run_id)
    if not cleaned_tables:
        logger.info("No cleaned datasets for run %s", run_id)
        return []

    docs: List[Dict[str, Any]] = []
    for table_info in cleaned_tables:
        table_name = table_info["table_name"]
        storage_path = table_info.get("storage_path", "")
        try:
            df = download_cleaned_csv(storage_path)
        except Exception as e:
            logger.warning("Skipping cleaned table %s: %s", table_name, e)
            continue

        table_docs = _build_docs_from_df(df, table_name, max_sample_rows, max_cols_per_row)
        docs.extend(table_docs)

    logger.info("Built %d documents from %d cleaned tables (run %s)", len(docs), len(cleaned_tables), run_id)
    return docs



# ---------------------------------------------------------------------------
# 2. Pipeline output: Insights  (from Supabase insight_snapshots)
# ---------------------------------------------------------------------------

def build_insight_documents() -> List[Dict[str, Any]]:
    """
    Build documents from the latest pipeline insight snapshot in Supabase.
    """
    from db.store import get_latest_insight_snapshot

    snapshot = get_latest_insight_snapshot()

    if "error" in snapshot:
        logger.info("No insight snapshot available: %s", snapshot.get("error"))
        return []

    insights = snapshot.get("insights", [])
    if not insights:
        logger.info("Insight snapshot has no insights list")
        return []

    docs = []
    for ins in insights:
        parts = [
            f"INSIGHT: {ins.get('title', 'Untitled')}",
            f"Severity: {ins.get('severity', 'unknown')}",
            f"Confidence: {ins.get('confidence', 'N/A')}",
            "",
            f"Description: {ins.get('description', '')}",
            "",
            f"Recommendation: {ins.get('recommendation', '')}",
        ]

        # Include evidence summary (truncated — full JSON can be huge)
        evidence = str(ins.get("evidence", ""))
        if len(evidence) > 500:
            evidence = evidence[:500] + "..."
        if evidence:
            parts.append(f"\nEvidence: {evidence}")

        docs.append({
            "text": "\n".join(parts),
            "metadata": {
                "source": "insight",
                "source_id": str(ins.get("insight_id", "")),
                "severity": str(ins.get("severity", "")),
                "confidence": ins.get("confidence", 0) or 0,
                "tags": str(ins.get("tags", "")),
            },
        })

    logger.info("Built %d insight documents from Supabase", len(docs))
    return docs


# ---------------------------------------------------------------------------
# 3. Pipeline output: Hypothesis results  (from Supabase hypothesis_snapshots)
# ---------------------------------------------------------------------------

def build_hypothesis_documents() -> List[Dict[str, Any]]:
    """
    Build documents from the latest hypothesis snapshot in Supabase.
    Only embeds significant results.
    Snapshot shape: {"meta": {...}, "results": [list of test dicts], "top_findings": [...]}
    """
    from db.store import get_latest_hypothesis_snapshot

    snapshot = get_latest_hypothesis_snapshot()

    if "error" in snapshot:
        logger.info("No hypothesis snapshot available: %s", snapshot.get("error"))
        return []

    results = snapshot.get("results", [])
    if not results:
        logger.info("Hypothesis snapshot has no results")
        return []

    # Group significant results by (dataset, x, y)
    groups = defaultdict(list)
    for r in results:
        if not r.get("significant"):
            continue
        key = (r.get("dataset", ""), r.get("x", ""), r.get("y", ""))
        groups[key].append(r)

    docs = []
    for (dataset, x, y), tests in groups.items():
        parts = [
            f"HYPOTHESIS TEST: {x} vs {y}",
            f"Dataset: {dataset}",
            "",
        ]
        for t in tests:
            stat_val = t.get("stat", 0)
            p_val = t.get("p_value", 1)
            eff = t.get("effect_size", 0)
            try:
                parts.append(
                    f"- {t.get('test', 'unknown')} test: stat={float(stat_val):.4f}, "
                    f"p={float(p_val):.2e}, effect_size={float(eff):.4f}"
                )
            except (ValueError, TypeError):
                parts.append(f"- {t.get('test', 'unknown')} test: stat={stat_val}, p={p_val}")

        docs.append({
            "text": "\n".join(parts),
            "metadata": {
                "source": "hypothesis",
                "source_id": f"{dataset}_{x}_{y}",
                "dataset": dataset,
            },
        })

    logger.info("Built %d hypothesis documents from Supabase", len(docs))
    return docs


# ---------------------------------------------------------------------------
# 4. Pipeline output: KPI cards  (from Supabase kpi_snapshots)
# ---------------------------------------------------------------------------

def build_kpi_documents() -> List[Dict[str, Any]]:
    """
    Build documents from the latest KPI snapshot in Supabase.
    Snapshot shape: {"cards": [list of KPI card dicts], ...}
    """
    from db.store import get_latest_kpi_snapshot

    snapshot = get_latest_kpi_snapshot()

    if "error" in snapshot:
        logger.info("No KPI snapshot available: %s", snapshot.get("error"))
        return []

    cards = snapshot.get("cards", [])
    if not cards:
        logger.info("KPI snapshot has no cards")
        return []

    # Group by KPI group
    groups = defaultdict(list)
    for card in cards:
        group_name = card.get("group", "Other")
        groups[group_name].append(card)

    docs = []
    for group_name, group_cards in groups.items():
        parts = [f"KPI GROUP: {group_name}", ""]
        for card in group_cards:
            value = card.get("value", "N/A")
            unit = card.get("unit", "")
            fmt = card.get("format", "")
            title = card.get("title", card.get("id", ""))

            if fmt == "currency" and isinstance(value, (int, float)):
                display = f"${value:,.2f} {unit}".strip()
            elif fmt == "percent" and isinstance(value, (int, float)) and abs(value) < 10:
                display = f"{value:.2%}"
            else:
                display = f"{value} {unit}".strip()

            parts.append(f"- {title}: {display}")

        docs.append({
            "text": "\n".join(parts),
            "metadata": {"source": "kpi", "source_id": f"kpi_group_{group_name}"},
        })

    logger.info("Built %d KPI documents from Supabase", len(docs))
    return docs


# ---------------------------------------------------------------------------
# 5. KPI tables: top/bottom customers, products, etc.
# ---------------------------------------------------------------------------

def build_kpi_table_documents() -> List[Dict[str, Any]]:
    """
    Build documents from the tables embedded in the KPI snapshot
    (top_customers, top_products, low_products, risky_products, discount_watchlist).
    """
    from db.store import get_latest_kpi_snapshot

    snapshot = get_latest_kpi_snapshot()

    if "error" in snapshot:
        logger.info("No KPI snapshot available for tables: %s", snapshot.get("error"))
        return []

    tables = snapshot.get("tables", {})
    if not tables:
        logger.info("KPI snapshot has no tables")
        return []

    TABLE_LABELS = {
        "top_customers": "TOP CUSTOMERS BY TOTAL SPEND",
        "top_products": "TOP PRODUCTS BY REVENUE",
        "low_products": "LOWEST PERFORMING PRODUCTS",
        "risky_products": "PRODUCTS AT STOCK RISK",
        "discount_watchlist": "DISCOUNT WATCHLIST (HIGH DISCOUNT ITEMS)",
    }

    docs = []
    for table_key, label in TABLE_LABELS.items():
        rows = tables.get(table_key, [])
        if not rows:
            continue

        parts = [f"{label}:", ""]
        for i, row in enumerate(rows, 1):
            # Build a readable line from whatever columns the row has
            cols = [f"{k}={v}" for k, v in row.items() if v is not None]
            parts.append(f"{i}. " + " | ".join(cols))

        docs.append({
            "text": "\n".join(parts),
            "metadata": {"source": "kpi_table", "source_id": f"kpi_table_{table_key}"},
        })

    logger.info("Built %d KPI table documents from Supabase", len(docs))
    return docs


# ---------------------------------------------------------------------------
# 6. KPI executive insights
# ---------------------------------------------------------------------------

def build_kpi_executive_documents() -> List[Dict[str, Any]]:
    """
    Build documents from the executive_insights section of the KPI snapshot
    (summary sentences + top drivers from hypothesis).
    """
    from db.store import get_latest_kpi_snapshot

    snapshot = get_latest_kpi_snapshot()

    if "error" in snapshot:
        logger.info("No KPI snapshot for executive insights: %s", snapshot.get("error"))
        return []

    exec_insights = snapshot.get("executive_insights", {})
    if not exec_insights:
        logger.info("KPI snapshot has no executive_insights")
        return []

    parts = ["KPI EXECUTIVE SUMMARY:", ""]

    summary = exec_insights.get("summary", [])
    if summary:
        parts.append("Key Findings:")
        for s in summary:
            parts.append(f"- {s}")
        parts.append("")

    drivers = exec_insights.get("top_drivers_from_hypothesis", [])
    if drivers:
        parts.append("Top Drivers (from hypothesis testing):")
        for d in drivers:
            parts.append(f"- {d}")

    if len(parts) <= 2:
        return []

    docs = [{
        "text": "\n".join(parts),
        "metadata": {"source": "kpi_executive", "source_id": "kpi_executive_summary"},
    }]

    logger.info("Built %d KPI executive documents from Supabase", len(docs))
    return docs


# ---------------------------------------------------------------------------
# 7. Forecast data (revenue, churn, demand, cashflow)
# ---------------------------------------------------------------------------

def build_forecast_documents() -> List[Dict[str, Any]]:
    """
    Build documents from the forecasts section of the forecast snapshot.
    One document per forecast type (revenue, churn, demand, cashflow).
    """
    from db.store import get_latest_forecast_snapshot

    snapshot = get_latest_forecast_snapshot()

    if "error" in snapshot:
        logger.info("No forecast snapshot available: %s", snapshot.get("error"))
        return []

    forecasts = snapshot.get("forecasts", {})
    if not forecasts:
        logger.info("Forecast snapshot has no forecasts")
        return []

    docs = []

    # Revenue forecast
    rev = forecasts.get("forecasted_revenue", {})
    if rev:
        parts = [
            "FORECAST: Revenue",
            f"As of: {rev.get('as_of', 'N/A')}",
            f"Next 7 days: ${rev.get('next_7d', 'N/A'):,.2f}" if isinstance(rev.get('next_7d'), (int, float)) else f"Next 7 days: {rev.get('next_7d', 'N/A')}",
            f"Next 30 days: ${rev.get('next_30d', 'N/A'):,.2f}" if isinstance(rev.get('next_30d'), (int, float)) else f"Next 30 days: {rev.get('next_30d', 'N/A')}",
            f"Next 90 days: ${rev.get('next_90d', 'N/A'):,.2f}" if isinstance(rev.get('next_90d'), (int, float)) else f"Next 90 days: {rev.get('next_90d', 'N/A')}",
        ]
        metrics = rev.get("metrics", {})
        if metrics:
            parts.append(f"Model accuracy — RMSE: {metrics.get('rmse', 'N/A')}, MAE: {metrics.get('mae', 'N/A')}, MAPE: {metrics.get('mape', 'N/A')}")
        docs.append({
            "text": "\n".join(parts),
            "metadata": {"source": "forecast", "source_id": "forecast_revenue"},
        })

    # Churn forecast
    churn = forecasts.get("expected_churn_next_month", {})
    if churn:
        rate = churn.get("expected_churn_rate_next_30d")
        rate_display = f"{rate:.2%}" if isinstance(rate, (int, float)) and abs(rate) < 10 else str(rate)
        parts = [
            "FORECAST: Customer Churn",
            f"Snapshot date: {churn.get('snapshot_date', churn.get('as_of', 'N/A'))}",
            f"Expected churn rate (next 30 days): {rate_display}",
            f"Definition: {churn.get('definition', 'no purchase in next 30 days')}",
        ]
        metrics = churn.get("metrics", {})
        if metrics:
            parts.append(f"Model accuracy — AUC: {metrics.get('auc', metrics.get('roc_auc', 'N/A'))}")
        docs.append({
            "text": "\n".join(parts),
            "metadata": {"source": "forecast", "source_id": "forecast_churn"},
        })

    # Demand per SKU forecast
    demand = forecasts.get("forecasted_demand_per_sku", {})
    if demand:
        parts = [
            "FORECAST: Demand per SKU",
            f"As of: {demand.get('as_of', 'N/A')}",
        ]
        top_skus = demand.get("top_skus", [])
        if top_skus:
            parts.append("")
            parts.append("Top SKUs by forecasted demand:")
            for sku in top_skus[:20]:
                parts.append(
                    f"- {sku.get('sku', '?')}: "
                    f"7d={sku.get('next_7d_qty', 'N/A')}, "
                    f"30d={sku.get('next_30d_qty', 'N/A')}, "
                    f"90d={sku.get('next_90d_qty', 'N/A')}"
                )
        docs.append({
            "text": "\n".join(parts),
            "metadata": {"source": "forecast", "source_id": "forecast_demand"},
        })

    # Cashflow forecast
    cashflow = forecasts.get("projected_cashflow", {})
    if cashflow:
        proxy = cashflow.get("next_30d_cash_proxy")
        proxy_display = f"${proxy:,.2f}" if isinstance(proxy, (int, float)) else str(proxy)
        parts = [
            "FORECAST: Projected Cashflow",
            f"As of: {cashflow.get('as_of', 'N/A')}",
            f"Next 30 days proxy: {proxy_display}",
            f"Note: {cashflow.get('note', 'Proxy cashflow = revenue - refunds')}",
        ]
        docs.append({
            "text": "\n".join(parts),
            "metadata": {"source": "forecast", "source_id": "forecast_cashflow"},
        })

    logger.info("Built %d forecast documents from Supabase", len(docs))
    return docs


# ---------------------------------------------------------------------------
# 8. Forecast executive insights (risks, opportunities, drivers, actions)
# ---------------------------------------------------------------------------

def build_forecast_executive_documents() -> List[Dict[str, Any]]:
    """
    Build documents from the executive_insights section of the forecast snapshot.
    """
    from db.store import get_latest_forecast_snapshot

    snapshot = get_latest_forecast_snapshot()

    if "error" in snapshot:
        logger.info("No forecast snapshot for executive insights: %s", snapshot.get("error"))
        return []

    exec_insights = snapshot.get("executive_insights", {})
    if not exec_insights:
        logger.info("Forecast snapshot has no executive_insights")
        return []

    docs = []

    # Key drivers
    drivers = exec_insights.get("key_drivers_of_growth_decline", [])
    if drivers:
        parts = ["FORECAST EXECUTIVE: Key Drivers of Growth/Decline", ""]
        for d in drivers:
            parts.append(f"- {d}")
        docs.append({
            "text": "\n".join(parts),
            "metadata": {"source": "forecast_executive", "source_id": "forecast_exec_drivers"},
        })

    # Top risks
    risks = exec_insights.get("top_3_risks", [])
    if risks:
        parts = ["FORECAST EXECUTIVE: Top Risks", ""]
        for r in risks:
            if isinstance(r, dict):
                parts.append(f"- {r.get('title', 'Unknown risk')}")
                evidence = r.get("evidence", {})
                if evidence:
                    for k, v in evidence.items():
                        parts.append(f"  Evidence: {k} = {v}")
            else:
                parts.append(f"- {r}")
        docs.append({
            "text": "\n".join(parts),
            "metadata": {"source": "forecast_executive", "source_id": "forecast_exec_risks"},
        })

    # Top opportunities
    opps = exec_insights.get("top_3_opportunities", [])
    if opps:
        parts = ["FORECAST EXECUTIVE: Top Opportunities", ""]
        for o in opps:
            if isinstance(o, dict):
                parts.append(f"- {o.get('title', 'Unknown opportunity')}")
                evidence = o.get("evidence", {})
                if evidence:
                    for k, v in evidence.items():
                        parts.append(f"  Evidence: {k} = {v}")
            else:
                parts.append(f"- {o}")
        docs.append({
            "text": "\n".join(parts),
            "metadata": {"source": "forecast_executive", "source_id": "forecast_exec_opportunities"},
        })

    # Recommended actions
    actions = exec_insights.get("recommended_actions_rule_based", [])
    if actions:
        parts = ["FORECAST EXECUTIVE: Recommended Actions", ""]
        for a in actions:
            parts.append(f"- {a}")
        docs.append({
            "text": "\n".join(parts),
            "metadata": {"source": "forecast_executive", "source_id": "forecast_exec_actions"},
        })

    # Summary
    summary = exec_insights.get("summary", [])
    if summary:
        parts = ["FORECAST EXECUTIVE: Summary", ""]
        for s in summary:
            parts.append(f"- {s}")
        docs.append({
            "text": "\n".join(parts),
            "metadata": {"source": "forecast_executive", "source_id": "forecast_exec_summary"},
        })

    logger.info("Built %d forecast executive documents from Supabase", len(docs))
    return docs


# ---------------------------------------------------------------------------
# 9. Action plan prescriptions (from action_plan_snapshots)
# ---------------------------------------------------------------------------

def build_action_plan_documents() -> List[Dict[str, Any]]:
    """
    Build documents from the latest action plan snapshot.
    One doc per prescription + one summary doc with health score.
    """
    from db.store import get_latest_action_plan_snapshot

    snapshot = get_latest_action_plan_snapshot()

    if "error" in snapshot:
        logger.info("No action plan snapshot available: %s", snapshot.get("error"))
        return []

    docs = []

    # Health score summary
    health_score = snapshot.get("health_score")
    health_summary = snapshot.get("health_summary", "")
    prescriptions = snapshot.get("prescriptions", [])

    if health_score is not None or prescriptions:
        parts = ["ACTION PLAN SUMMARY", ""]
        if health_score is not None:
            parts.append(f"Overall Business Health Score: {health_score}/100")
        if health_summary:
            parts.append(f"Health Summary: {health_summary}")
        if prescriptions:
            parts.append(f"Total Prescriptions: {len(prescriptions)}")
            critical = sum(1 for p in prescriptions if p.get("urgency") == "critical")
            high = sum(1 for p in prescriptions if p.get("urgency") == "high")
            if critical:
                parts.append(f"Critical urgency: {critical}")
            if high:
                parts.append(f"High urgency: {high}")
        docs.append({
            "text": "\n".join(parts),
            "metadata": {"source": "action_plan", "source_id": "action_plan_summary"},
        })

    # Individual prescriptions
    for p in prescriptions:
        pid = p.get("prescription_id", p.get("id", ""))
        parts = [
            f"ACTION PLAN PRESCRIPTION: {p.get('title', 'Untitled')}",
            f"Priority: {p.get('priority', 'N/A')} | Urgency: {p.get('urgency', 'N/A')} | Category: {p.get('category', 'N/A')}",
            f"Effort: {p.get('effort', 'N/A')} | Action Type: {p.get('action_type', 'N/A')}",
        ]
        if p.get("description"):
            parts.append(f"Description: {p['description']}")
        if p.get("rationale"):
            parts.append(f"Rationale: {p['rationale']}")
        if p.get("action"):
            parts.append(f"Action: {p['action']}")
        if p.get("impact_estimate"):
            parts.append(f"Impact Estimate: {p['impact_estimate']}")
        if p.get("estimated_impact_dollars"):
            parts.append(f"Estimated Impact: ${p['estimated_impact_dollars']:,.2f}")
        if p.get("success_metrics"):
            parts.append("Success Metrics: " + "; ".join(p["success_metrics"]))

        docs.append({
            "text": "\n".join(parts),
            "metadata": {
                "source": "action_plan",
                "source_id": f"prescription_{pid}",
                "urgency": str(p.get("urgency", "")),
                "category": str(p.get("category", "")),
            },
        })

    logger.info("Built %d action plan documents from Supabase", len(docs))
    return docs
