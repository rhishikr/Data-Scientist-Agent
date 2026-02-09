from __future__ import annotations

from pathlib import Path

from .io import DataPaths, load_featured, write_json
from .schemas import KpiSnapshot, KpiMeta, utc_now_iso
from .customer_kpis import compute_customer_cards_and_segments, build_customer_tables
from .product_kpis import build_product_tables
from .trends import build_trends
from .csv_writer import write_csv, write_single_row_csv


def run_kpi_snapshot(project_root: str | Path) -> KpiSnapshot:
    """
    Generates a dashboard-ready KPI snapshot.

    Outputs:
      - JSON: data/kpi_outputs/kpi_snapshot.json

      - CSVs:
          data/kpi_outputs/kpi_cards.csv
          data/kpi_outputs/kpi_segments.csv
          data/kpi_outputs/kpi_trends_weekly.csv
          data/kpi_outputs/kpi_trends_monthly.csv
          data/kpi_outputs/kpi_top_customers.csv
          data/kpi_outputs/kpi_at_risk_customers.csv
          data/kpi_outputs/kpi_risky_products.csv
          data/kpi_outputs/kpi_discount_watchlist.csv
    """
    root = Path(project_root)
    paths = DataPaths(base_dir=root)

    featured = load_featured(paths)
    customers = featured.get("customers_features")
    products = featured.get("products_features")
    transactions = featured.get("transactions_features")

    # ---- Customers ----
    if customers is not None and not customers.empty:
        cards, segments, defs_cust = compute_customer_cards_and_segments(customers)
        cust_tables = build_customer_tables(customers)
    else:
        cards, segments, defs_cust = {}, [], {}
        cust_tables = {"top_customers": [], "at_risk_customers": []}

    # ---- Products ----
    if products is not None and not products.empty:
        prod_tables, defs_prod = build_product_tables(products)
    else:
        prod_tables, defs_prod = {"risky_products": [], "discount_watchlist": []}, {}

    # ---- Trends ----
    if transactions is not None and not transactions.empty:
        trends = build_trends(transactions)
    else:
        trends = {"weekly": {}, "monthly": {}}

    # ---- Merge definitions + tables ----
    definitions: dict = {**defs_cust, **defs_prod}
    tables: dict = {**cust_tables, **prod_tables}

    snapshot = KpiSnapshot(
        meta=KpiMeta(generated_at=utc_now_iso()),
        definitions=definitions,
        cards=cards,
        segments=segments,
        trends=trends,
        tables=tables,
    )

    # ---- Write JSON ----
    out_json = paths.kpi_dir / "kpi_snapshot.json"
    write_json(out_json, snapshot.to_dict())

    # ---- Write CSVs (dashboard-friendly) ----
    csv_dir = paths.kpi_dir

    # Cards (single row)
    write_single_row_csv(csv_dir / "kpi_cards.csv", snapshot.cards)

    # Segments (pie/donut)
    write_csv(csv_dir / "kpi_segments.csv", snapshot.segments)

    # Trends (line charts)
    weekly_series = snapshot.trends.get("weekly", {}).get("series", []) or []
    monthly_series = snapshot.trends.get("monthly", {}).get("series", []) or []
    write_csv(csv_dir / "kpi_trends_weekly.csv", weekly_series)
    write_csv(csv_dir / "kpi_trends_monthly.csv", monthly_series)

    # Tables
    write_csv(csv_dir / "kpi_top_customers.csv", tables.get("top_customers", []) or [])
    write_csv(csv_dir / "kpi_at_risk_customers.csv", tables.get("at_risk_customers", []) or [])
    write_csv(csv_dir / "kpi_risky_products.csv", tables.get("risky_products", []) or [])
    write_csv(csv_dir / "kpi_discount_watchlist.csv", tables.get("discount_watchlist", []) or [])

    return snapshot
