from __future__ import annotations

import math
import os
from datetime import datetime
from typing import Any, Dict, Iterable

import numpy as np
import pandas as pd

from .io import DataPaths, read_dataset, read_json, write_json, write_csv
from .metrics import (
    compute_revenue_kpis,
    compute_customer_kpis,
    compute_funnel_kpis,
    compute_marketing_kpis,
    compute_product_kpis,
    compute_inventory_kpis,
    compute_forecast_kpis,
)


# -----------------------------
# Helpers: dates + JSON safety
# -----------------------------
def _to_dt_max(df: pd.DataFrame, col: str) -> pd.Timestamp | None:
    if df is None or df.empty or col not in df.columns:
        return None
    s = pd.to_datetime(df[col], errors="coerce", utc=False)
    if s.notna().any():
        return pd.Timestamp(s.max())
    return None


def _infer_as_of_from_available(
    transactions_features: pd.DataFrame,
    transactions: pd.DataFrame,
    web: pd.DataFrame,
    marketing: pd.DataFrame,
) -> pd.Timestamp | None:
    """
    Choose 'as_of' from the freshest timestamp in your data (NOT wall-clock time).
    Priority:
      1) transactions_features.order_datetime
      2) transactions.order_datetime
      3) web_analytics.event_datetime
      4) marketing.end_date / start_date
    """
    # 1) transactions_features
    as_of = _to_dt_max(transactions_features, "order_datetime")
    if as_of is not None:
        return as_of

    # 2) transactions
    as_of = _to_dt_max(transactions, "order_datetime")
    if as_of is not None:
        return as_of

    # 3) web
    as_of = _to_dt_max(web, "event_datetime")
    if as_of is not None:
        return as_of

    # 4) marketing (date-only)
    if marketing is not None and not marketing.empty:
        for c in ("end_date", "start_date"):
            if c in marketing.columns:
                s = pd.to_datetime(marketing[c], errors="coerce")
                if s.notna().any():
                    return pd.Timestamp(s.max())

    return None


def _is_bad_number(x: Any) -> bool:
    # catches: NaN, inf, -inf (python float + numpy float)
    try:
        if x is None:
            return False
        if isinstance(x, (np.floating, float)):
            return bool(math.isnan(float(x)) or math.isinf(float(x)))
        return False
    except Exception:
        return False


def _sanitize_for_json(obj: Any) -> Any:
    """
    FastAPI/Starlette JSON response fails if ANY NaN/Inf exists.
    Convert NaN/Inf -> None recursively.
    """
    if obj is None:
        return None

    if _is_bad_number(obj):
        return None

    # numpy scalars -> python scalars
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        v = float(obj)
        return None if (math.isnan(v) or math.isinf(v)) else v
    if isinstance(obj, (np.bool_,)):
        return bool(obj)

    if isinstance(obj, (pd.Timestamp, datetime)):
        # keep as ISO string for API friendliness
        return str(obj)

    if isinstance(obj, dict):
        return {str(k): _sanitize_for_json(v) for k, v in obj.items()}

    if isinstance(obj, (list, tuple)):
        return [_sanitize_for_json(v) for v in obj]

    return obj


def _safe_card_value(v: Any) -> Any:
    # Keep ints/strings as-is, but remove NaN/Inf floats.
    return None if _is_bad_number(v) else v


# -----------------------------
# Main KPI Snapshot
# -----------------------------
def run_kpi_snapshot(paths: DataPaths | None = None) -> Dict[str, Any]:
    """
    Produces:
      - data/kpi_outputs/kpi_snapshot.json
      - data/kpi_outputs/kpi_cards.csv
      - data/kpi_outputs/kpi_top_customers.csv
      - data/kpi_outputs/kpi_risky_products.csv
      - data/kpi_outputs/kpi_discount_watchlist.csv
    """
    paths = paths or DataPaths.default()
    os.makedirs(paths.out_dir, exist_ok=True)

    data = read_dataset(paths)

    customers = data.get("customers", pd.DataFrame())
    inventory = data.get("inventory", pd.DataFrame())
    marketing = data.get("marketing", pd.DataFrame())
    payments = data.get("payments", pd.DataFrame())
    products = data.get("products", pd.DataFrame())
    transactions = data.get("transactions", pd.DataFrame())
    web = data.get("web_analytics", pd.DataFrame())

    customers_features = data.get("customers_features", pd.DataFrame())
    products_features = data.get("products_features", pd.DataFrame())
    transactions_features = data.get("transactions_features", pd.DataFrame())

    # IMPORTANT: as_of should come from your data, not from "today"
    as_of = _infer_as_of_from_available(transactions_features, transactions, web, marketing)
    if as_of is None:
        # last-resort fallback: still avoid crashing
        as_of = pd.Timestamp.utcnow().floor("s")

    # --- KPI Groups ---
    revenue_kpis = compute_revenue_kpis(transactions, as_of)
    customer_kpis = compute_customer_kpis(customers, customers_features, transactions, as_of)
    funnel_kpis = compute_funnel_kpis(web, transactions, as_of)
    marketing_kpis = compute_marketing_kpis(marketing)
    product_kpis, top_products_df, low_products_df = compute_product_kpis(products, transactions)
    inventory_kpis, risky_products_df = compute_inventory_kpis(inventory, transactions, as_of)
    # forecast_kpis = compute_forecast_kpis(transactions, as_of)

    # --- Tables ---
    # Top customers table from customers_features (fallback could be added later)
    top_customers_df = pd.DataFrame()
    if customers_features is not None and not customers_features.empty and "total_spend" in customers_features.columns:
        cf = customers_features.copy()

        # numeric cleanup
        for c in ("total_spend", "total_orders", "recency_days", "avg_order_value"):
            if c in cf.columns:
                cf[c] = pd.to_numeric(cf[c], errors="coerce")

        cols = [
            "customer_id",
            "name",
            "location",
            "device_type",
            "total_orders",
            "total_spend",
            "avg_order_value",
            "recency_days",
            "top_product_id",
        ]
        cols = [c for c in cols if c in cf.columns]
        top_customers_df = (
            cf.sort_values("total_spend", ascending=False)
            .head(25)[cols]
            .copy()
        )

    # Discount watchlist: high discount + low rating
    discount_watchlist_df = pd.DataFrame()
    if products is not None and not products.empty and "discount_percent" in products.columns:
        p = products.copy()
        p["discount_percent"] = pd.to_numeric(p["discount_percent"], errors="coerce").fillna(0)
        if "average_rating" in p.columns:
            p["average_rating"] = pd.to_numeric(p["average_rating"], errors="coerce")

        watch = p.loc[p["discount_percent"] >= 15].copy()
        if not watch.empty:
            if "average_rating" in watch.columns:
                watch["flag_low_rating"] = watch["average_rating"].notna() & (watch["average_rating"] <= 3.2)
            else:
                watch["flag_low_rating"] = False

            cols = [
                "sku",
                "name",
                "category",
                "brand",
                "discount_percent",
                "average_rating",
                "retail_price",
                "cost_price",
            ]
            cols = [c for c in cols if c in watch.columns]
            discount_watchlist_df = (
                watch.sort_values(["flag_low_rating", "discount_percent"], ascending=[False, False])
                .head(50)[cols]
                .copy()
            )

    # --- KPI Cards list (for UI + drag/drop later) ---
    cards: list[dict[str, Any]] = []

    def add_card(card_id: str, title: str, value: Any, unit: str = "", fmt: str = "number", group: str = ""):
        cards.append(
            {
                "id": card_id,
                "title": title,
                "value": _safe_card_value(value),
                "unit": unit,
                "format": fmt,   # number | percent | currency | minutes
                "group": group,  # Revenue | Customers | Funnel | Marketing | Product | Inventory | Forecast
            }
        )

    # Revenue & Sales Health
    add_card("rev_mtd", "Total Revenue (MTD)", revenue_kpis.get("total_revenue", {}).get("mtd"), "USD", "currency", "Revenue")
    add_card("rev_qtd", "Total Revenue (QTD)", revenue_kpis.get("total_revenue", {}).get("qtd"), "USD", "currency", "Revenue")
    add_card("rev_ytd", "Total Revenue (YTD)", revenue_kpis.get("total_revenue", {}).get("ytd"), "USD", "currency", "Revenue")
    add_card("rev_growth_30d", "Revenue Growth (30d vs prev)", revenue_kpis.get("revenue_growth_30d"), "", "percent", "Revenue")
    add_card("aov", "Average Order Value (AOV)", revenue_kpis.get("average_order_value"), "USD", "currency", "Revenue")
    add_card("orders_day", "Orders per Day", revenue_kpis.get("orders_per_day"), "", "number", "Revenue")
    add_card("orders_week", "Orders per Week", revenue_kpis.get("orders_per_week"), "", "number", "Revenue")

    # Customer Health
    add_card("active_customers_30d", "Active Customers (30d)", customer_kpis.get("active_customers_30d"), "", "number", "Customers")
    add_card("new_customers_30d", "New Customers (30d)", customer_kpis.get("new_customers_30d"), "", "number", "Customers")
    add_card("returning_customers_30d", "Returning Customers (lifetime)", customer_kpis.get("returning_customers_30d"), "", "number", "Customers")
    add_card("repeat_purchase_rate", "Repeat Purchase Rate", customer_kpis.get("repeat_purchase_rate"), "", "percent", "Customers")
    add_card("retention_rate_proxy", "Retention Rate (proxy)", customer_kpis.get("retention_rate_proxy"), "", "percent", "Customers")
    add_card("churn_rate_proxy", "Churn Rate (proxy)", customer_kpis.get("churn_rate_proxy"), "", "percent", "Customers")
    add_card("avg_clv", "Average CLV", customer_kpis.get("avg_clv"), "USD", "currency", "Customers")
    add_card("median_clv", "Median CLV", customer_kpis.get("median_clv"), "USD", "currency", "Customers")

    # Funnel
    add_card("conversion_rate", "Conversion Rate", funnel_kpis.get("conversion_rate"), "", "percent", "Funnel")
    add_card("cart_abandonment_rate", "Cart Abandonment Rate", funnel_kpis.get("cart_abandonment_rate"), "", "percent", "Funnel")
    add_card("checkout_completion_rate", "Checkout Completion Rate", funnel_kpis.get("checkout_completion_rate"), "", "percent", "Funnel")
    add_card("bounce_rate", "Bounce Rate", funnel_kpis.get("bounce_rate"), "", "percent", "Funnel")
    add_card("time_to_purchase", "Avg Time to Purchase", funnel_kpis.get("avg_time_to_purchase_min"), "min", "minutes", "Funnel")

    # Marketing
    add_card("cac", "Customer Acquisition Cost (proxy)", marketing_kpis.get("cac"), "USD", "currency", "Marketing")
    add_card("roas", "ROAS", marketing_kpis.get("roas"), "x", "number", "Marketing")
    add_card("campaign_cr", "Campaign Conversion Rate", marketing_kpis.get("campaign_conversion_rate"), "", "percent", "Marketing")
    add_card("promo_uplift", "Promotion Uplift (proxy)", marketing_kpis.get("promotion_uplift_proxy"), "", "percent", "Marketing")

    # Product & Merchandising
    add_card("avg_margin_pct", "Average Product Margin", product_kpis.get("avg_product_margin_pct"), "", "percent", "Product")
    add_card("return_rate_proxy", "Return Rate (proxy)", product_kpis.get("return_rate_proxy"), "", "percent", "Product")

    # Inventory & Ops
    add_card("stock_out_risk_pct", "Stock-Out Risk", inventory_kpis.get("stock_out_risk_pct"), "", "percent", "Inventory")
    add_card("inventory_turnover_proxy", "Inventory Turnover (proxy)", inventory_kpis.get("inventory_turnover_proxy"), "", "number", "Inventory")

    # Forecast
    # add_card("forecast_rev_7d", "Forecasted Revenue (7d)", forecast_kpis.get("forecasted_revenue_7d"), "USD", "currency", "Forecast")
    # add_card("forecast_rev_30d", "Forecasted Revenue (30d)", forecast_kpis.get("forecasted_revenue_30d"), "USD", "currency", "Forecast")
    # add_card("forecast_rev_90d", "Forecasted Revenue (90d)", forecast_kpis.get("forecasted_revenue_90d"), "USD", "currency", "Forecast")

    # --- AI Executive Insights (rule-based now; LLM can rewrite later) ---
    exec_insights: list[str] = []

    rg = revenue_kpis.get("revenue_growth_30d")
    if isinstance(rg, (int, float)) and not _is_bad_number(rg):
        if rg > 0.05:
            exec_insights.append(f"Revenue is up ~{rg*100:.1f}% over the last 30 days vs the prior 30 days.")
        elif rg < -0.05:
            exec_insights.append(f"Revenue is down ~{abs(rg)*100:.1f}% over the last 30 days vs the prior 30 days.")

    aov = revenue_kpis.get("average_order_value")
    conv = funnel_kpis.get("conversion_rate")
    if isinstance(aov, (int, float)) and isinstance(conv, (int, float)) and not _is_bad_number(aov) and not _is_bad_number(conv):
        exec_insights.append("Revenue changes are usually driven by a mix of Average Order Value (AOV) and Conversion Rate—track both together.")

    so = inventory_kpis.get("stock_out_risk_pct")
    if isinstance(so, (int, float)) and not _is_bad_number(so) and so >= 0.15:
        exec_insights.append(f"Stock-out risk is elevated: ~{so*100:.0f}% of SKUs are at/under reorder threshold.")

    # Optionally incorporate hypothesis_results.json if available (for “drivers”)
    hyp = read_json(paths.hypothesis_json_path)
    drivers: list[str] = []
    if hyp and isinstance(hyp.get("top_findings"), list):
        drivers = [str(x) for x in hyp["top_findings"][:5]]

    snapshot = {
        "meta": {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            # as_of should be the newest date in your data
            "as_of": as_of.isoformat(sep=" ") if isinstance(as_of, pd.Timestamp) else str(as_of),
            "datasets_used": [k for k, v in data.items() if isinstance(v, pd.DataFrame) and not v.empty],
        },
        "kpis": {
            "revenue_sales_health": revenue_kpis,
            "customer_health_value": customer_kpis,
            "conversion_funnel": funnel_kpis,
            "marketing_effectiveness": marketing_kpis,
            "product_merchandising": product_kpis,
            "inventory_operations": inventory_kpis,
            # "forecasting_outlook": forecast_kpis,
        },
        # This is your “25–30 KPI options” list for a dynamic dashboard
        "cards": cards,
        "tables": {
            "top_customers": top_customers_df.to_dict(orient="records") if not top_customers_df.empty else [],
            "top_products": top_products_df.to_dict(orient="records") if isinstance(top_products_df, pd.DataFrame) and not top_products_df.empty else [],
            "low_products": low_products_df.to_dict(orient="records") if isinstance(low_products_df, pd.DataFrame) and not low_products_df.empty else [],
            "risky_products": risky_products_df.to_dict(orient="records") if isinstance(risky_products_df, pd.DataFrame) and not risky_products_df.empty else [],
            "discount_watchlist": discount_watchlist_df.to_dict(orient="records") if not discount_watchlist_df.empty else [],
        },
        "executive_insights": {
            "summary": exec_insights,
            "top_drivers_from_hypothesis": drivers,
        },
    }

    # IMPORTANT: sanitize before returning to FastAPI (prevents NaN JSON crash)
    snapshot = _sanitize_for_json(snapshot)

    # --- Write outputs ---
    write_json(os.path.join(paths.out_dir, "kpi_snapshot.json"), snapshot)
    write_csv(os.path.join(paths.out_dir, "kpi_cards.csv"), pd.DataFrame(cards))

    if not top_customers_df.empty:
        write_csv(os.path.join(paths.out_dir, "kpi_top_customers.csv"), top_customers_df)

    if isinstance(risky_products_df, pd.DataFrame) and not risky_products_df.empty:
        write_csv(os.path.join(paths.out_dir, "kpi_risky_products.csv"), risky_products_df)

    if not discount_watchlist_df.empty:
        write_csv(os.path.join(paths.out_dir, "kpi_discount_watchlist.csv"), discount_watchlist_df)

    return snapshot
