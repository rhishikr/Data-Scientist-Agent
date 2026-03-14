# backend/rag/etl.py
"""
ETL: Build embeddable documents from Supabase data sources.

All data is read from Supabase (cleaned datasets + pipeline snapshot tables).
Falls back to raw tables if no cleaned data is available.
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
# 1. Table profiles + sampled rows  (from cleaned data, fallback to raw)
# ---------------------------------------------------------------------------

def build_table_profile_documents(
    run_id: Optional[str] = None,
    max_sample_rows: int = 100,
    max_cols_per_row: int = 20,
) -> List[Dict[str, Any]]:
    """
    Build profile + sample documents from cleaned datasets of a pipeline run.
    Falls back to raw Supabase tables if no cleaned data is available.
    """
    docs = _build_from_cleaned(run_id, max_sample_rows, max_cols_per_row)
    if docs:
        return docs

    # Fallback: use raw tables if no cleaned data available
    logger.info("No cleaned datasets found, falling back to raw tables")
    return _build_from_raw(max_sample_rows, max_cols_per_row)


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


def _build_from_raw(
    max_sample_rows: int,
    max_cols_per_row: int,
) -> List[Dict[str, Any]]:
    """Fallback: build documents from raw Supabase tables."""
    from db.raw_store import read_raw_table, TABLE_MAP

    docs: List[Dict[str, Any]] = []
    for csv_name, table_name in TABLE_MAP.items():
        try:
            df = read_raw_table(csv_name)
        except Exception as e:
            logger.warning("Skipping %s: %s", table_name, e)
            continue

        table_docs = _build_docs_from_df(df, table_name, max_sample_rows, max_cols_per_row)
        docs.extend(table_docs)

    logger.info("Built %d documents from %d Supabase raw tables", len(docs), len(TABLE_MAP))
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
