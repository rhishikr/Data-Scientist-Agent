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
    compute_net_revenue_kpis,
    compute_demographic_kpis,
    compute_payment_kpis,
    compute_supplier_kpis,
    compute_brand_kpis,
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
    sessions: pd.DataFrame,
    web: pd.DataFrame,
    marketing: pd.DataFrame,
) -> pd.Timestamp | None:
    """
    Choose 'as_of' from the freshest timestamp in your data (NOT wall-clock time).
    """
    # 1) transactions_features
    as_of = _to_dt_max(transactions_features, "order_datetime")
    if as_of is not None:
        return as_of

    # 2) transactions
    as_of = _to_dt_max(transactions, "order_datetime")
    if as_of is not None:
        return as_of

    # 3) sessions
    as_of = _to_dt_max(sessions, "session_start")
    if as_of is not None:
        return as_of

    # 4) web
    as_of = _to_dt_max(web, "event_datetime")
    if as_of is not None:
        return as_of

    # 5) marketing (date-only)
    if marketing is not None and not marketing.empty:
        for c in ("end_date", "start_date"):
            if c in marketing.columns:
                s = pd.to_datetime(marketing[c], errors="coerce")
                if s.notna().any():
                    return pd.Timestamp(s.max())

    return None


def _is_bad_number(x: Any) -> bool:
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

    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        v = float(obj)
        return None if (math.isnan(v) or math.isinf(v)) else v
    if isinstance(obj, (np.bool_,)):
        return bool(obj)

    if isinstance(obj, (pd.Timestamp, datetime)):
        return str(obj)

    if isinstance(obj, dict):
        return {str(k): _sanitize_for_json(v) for k, v in obj.items()}

    if isinstance(obj, (list, tuple)):
        return [_sanitize_for_json(v) for v in obj]

    return obj


def _safe_card_value(v: Any) -> Any:
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
    sessions = data.get("sessions", pd.DataFrame())
    events = data.get("events", pd.DataFrame())
    campaign_performance = data.get("campaign_performance", pd.DataFrame())
    funnel_summary = data.get("funnel_summary", pd.DataFrame())

    customers_features = data.get("customers_features", pd.DataFrame())
    products_features = data.get("products_features", pd.DataFrame())
    transactions_features = data.get("transactions_features", pd.DataFrame())

    # IMPORTANT: as_of should come from your data, not from "today"
    as_of = _infer_as_of_from_available(transactions_features, transactions, sessions, web, marketing)
    if as_of is None:
        as_of = pd.Timestamp.utcnow().floor("s")

    # --- KPI Groups ---
    revenue_kpis = compute_revenue_kpis(transactions, as_of)
    customer_kpis = compute_customer_kpis(customers, customers_features, transactions, as_of)
    funnel_kpis = compute_funnel_kpis(sessions, events, funnel_summary, web, transactions, as_of)
    marketing_kpis = compute_marketing_kpis(marketing, campaign_performance)
    product_kpis, top_products_df, low_products_df = compute_product_kpis(products, transactions)
    inventory_kpis, risky_products_df = compute_inventory_kpis(inventory, transactions, as_of)
    net_revenue_kpis = compute_net_revenue_kpis(transactions, payments)
    demographic_kpis = compute_demographic_kpis(customers)
    payment_kpis = compute_payment_kpis(payments)
    supplier_kpis = compute_supplier_kpis(inventory)
    brand_kpis = compute_brand_kpis(products, transactions)
    # forecast_kpis = compute_forecast_kpis(transactions, as_of)

    # --- Tables ---
    top_customers_df = pd.DataFrame()
    if customers_features is not None and not customers_features.empty and "total_spend" in customers_features.columns:
        cf = customers_features.copy()

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

    # Discount watchlist
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
                "product_name",
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
                "format": fmt,
                "group": group,
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

    # Net Revenue
    add_card("gross_revenue", "Gross Revenue", net_revenue_kpis.get("gross_revenue"), "USD", "currency", "Revenue")
    add_card("net_revenue", "Net Revenue", net_revenue_kpis.get("net_revenue"), "USD", "currency", "Revenue")
    add_card("total_discounts", "Total Discounts", net_revenue_kpis.get("total_discounts"), "USD", "currency", "Revenue")
    add_card("total_returns", "Total Returns Value", net_revenue_kpis.get("total_returns"), "USD", "currency", "Revenue")
    add_card("total_refunds", "Total Refunds", net_revenue_kpis.get("total_refunds"), "USD", "currency", "Revenue")
    add_card("total_fees", "Total Transaction Fees", net_revenue_kpis.get("total_fees"), "USD", "currency", "Revenue")
    add_card("discount_rate", "Discount Rate", net_revenue_kpis.get("discount_rate"), "", "percent", "Revenue")

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
    add_card("product_view_rate", "Product View Rate", funnel_kpis.get("product_view_rate"), "", "percent", "Funnel")
    add_card("bounce_rate", "Bounce Rate", funnel_kpis.get("bounce_rate"), "", "percent", "Funnel")
    add_card("time_to_purchase", "Avg Time to Purchase", funnel_kpis.get("avg_time_to_purchase_min"), "min", "minutes", "Funnel")
    add_card("avg_session_duration", "Avg Session Duration", funnel_kpis.get("avg_session_duration"), "sec", "number", "Funnel")
    add_card("revenue_per_session", "Revenue per Session", funnel_kpis.get("revenue_per_session"), "USD", "currency", "Funnel")
    add_card("mobile_conversion_rate", "Mobile Conversion Rate", funnel_kpis.get("mobile_conversion_rate"), "", "percent", "Funnel")
    add_card("desktop_conversion_rate", "Desktop Conversion Rate", funnel_kpis.get("desktop_conversion_rate"), "", "percent", "Funnel")

    # Marketing
    add_card("cac", "Customer Acquisition Cost (proxy)", marketing_kpis.get("cac"), "USD", "currency", "Marketing")
    add_card("roas", "ROAS", marketing_kpis.get("roas"), "x", "number", "Marketing")
    add_card("campaign_cr", "Campaign Conversion Rate", marketing_kpis.get("campaign_conversion_rate"), "", "percent", "Marketing")
    add_card("best_campaign", "Best Performing Campaign", marketing_kpis.get("best_performing_campaign"), "", "text", "Marketing")
    add_card("worst_campaign", "Worst Performing Campaign", marketing_kpis.get("worst_performing_campaign"), "", "text", "Marketing")

    # Promo uplift: compare avg order value of discounted vs non-discounted orders
    promo_uplift = None
    if not transactions.empty and "discount_amount" in transactions.columns and "total_amount" in transactions.columns:
        tx_promo = transactions.copy()
        tx_promo["discount_amount"] = pd.to_numeric(tx_promo["discount_amount"], errors="coerce").fillna(0)
        tx_promo["total_amount"] = pd.to_numeric(tx_promo["total_amount"], errors="coerce")
        discounted = tx_promo[tx_promo["discount_amount"] > 0]["total_amount"]
        non_discounted = tx_promo[tx_promo["discount_amount"] <= 0]["total_amount"]
        if len(non_discounted) > 0 and non_discounted.mean() > 0 and len(discounted) > 0:
            promo_uplift = (discounted.mean() - non_discounted.mean()) / non_discounted.mean()
    add_card("promo_uplift", "Promo Uplift", promo_uplift, "", "percent", "Marketing")

    # Payments
    add_card("payment_failure_rate", "Payment Failure Rate", payment_kpis.get("payment_failure_rate"), "", "percent", "Payments")
    add_card("payment_refund_rate", "Payment Refund Rate", payment_kpis.get("refund_rate"), "", "percent", "Payments")
    add_card("top_payment_method", "Top Payment Method", payment_kpis.get("top_payment_method"), "", "text", "Payments")
    add_card("avg_transaction_fee", "Avg Transaction Fee", payment_kpis.get("avg_transaction_fee"), "USD", "currency", "Payments")

    # Product & Merchandising
    add_card("avg_margin_pct", "Average Product Margin", product_kpis.get("avg_product_margin_pct"), "", "percent", "Product")
    add_card("return_rate_proxy", "Return Rate (proxy)", product_kpis.get("return_rate_proxy"), "", "percent", "Product")

    # Inventory & Ops
    add_card("stock_out_risk_pct", "Stock-Out Risk", inventory_kpis.get("stock_out_risk_pct"), "", "percent", "Inventory")
    add_card("inventory_turnover_proxy", "Inventory Turnover (proxy)", inventory_kpis.get("inventory_turnover_proxy"), "", "number", "Inventory")

    # Demographics
    add_card("customers_by_gender", "Customers by Gender", demographic_kpis.get("customers_by_gender"), "", "json", "Demographics")
    add_card("customers_by_age_group", "Customers by Age Group", demographic_kpis.get("customers_by_age_group"), "", "json", "Demographics")
    add_card("customers_by_loyalty", "Customers by Loyalty Tier", demographic_kpis.get("customers_by_loyalty_tier"), "", "json", "Demographics")
    add_card("avg_spend_by_loyalty", "Avg Spend by Loyalty Tier", demographic_kpis.get("avg_spend_by_loyalty"), "", "json", "Demographics")

    # Brand
    top_brands = {}
    rev_by_brand = brand_kpis.get("revenue_by_brand", {})
    if isinstance(rev_by_brand, dict):
        top_brands = dict(sorted(rev_by_brand.items(), key=lambda x: x[1], reverse=True)[:10])
    add_card("top_brands_revenue", "Top 10 Brands by Revenue", top_brands, "", "json", "Brand")
    add_card("brand_count", "Total Brands", len(rev_by_brand) if isinstance(rev_by_brand, dict) else 0, "", "number", "Brand")

    # Supplier
    add_card("supplier_stockouts", "Stockouts by Supplier", supplier_kpis.get("stockout_by_supplier"), "", "json", "Supplier")
    add_card("supplier_reliability", "Supplier Reliability Scores", supplier_kpis.get("supplier_reliability_score"), "", "json", "Supplier")

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

    # Net revenue insights
    nr = net_revenue_kpis.get("net_revenue")
    gr = net_revenue_kpis.get("gross_revenue")
    if isinstance(nr, (int, float)) and isinstance(gr, (int, float)) and not _is_bad_number(nr) and not _is_bad_number(gr) and gr > 0:
        leakage = (gr - nr) / gr
        if leakage > 0.15:
            exec_insights.append(f"Revenue leakage (discounts + returns + refunds + fees) is {leakage*100:.1f}% of gross revenue.")

    # Payment health
    pf = payment_kpis.get("payment_failure_rate")
    if isinstance(pf, (int, float)) and not _is_bad_number(pf) and pf > 0.05:
        exec_insights.append(f"Payment failure rate is {pf*100:.1f}% — investigate payment gateway issues.")

    # Cart abandonment
    ca = funnel_kpis.get("cart_abandonment_rate")
    if isinstance(ca, (int, float)) and not _is_bad_number(ca) and ca > 0.6:
        exec_insights.append(f"Cart abandonment is high at {ca*100:.0f}%. Consider checkout UX improvements or retargeting campaigns.")

    # Optionally incorporate hypothesis_results.json
    hyp = read_json(paths.hypothesis_json_path)
    drivers: list[str] = []
    if hyp and isinstance(hyp.get("top_findings"), list):
        drivers = [str(x) for x in hyp["top_findings"][:5]]

    snapshot = {
        "meta": {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "as_of": as_of.isoformat(sep=" ") if isinstance(as_of, pd.Timestamp) else str(as_of),
            "datasets_used": [k for k, v in data.items() if isinstance(v, pd.DataFrame) and not v.empty],
        },
        "kpis": {
            "revenue_sales_health": revenue_kpis,
            "net_revenue": net_revenue_kpis,
            "customer_health_value": customer_kpis,
            "demographics": demographic_kpis,
            "conversion_funnel": funnel_kpis,
            "marketing_effectiveness": marketing_kpis,
            "product_merchandising": product_kpis,
            "brand_performance": brand_kpis,
            "inventory_operations": inventory_kpis,
            "supplier_health": supplier_kpis,
            "payment_health": payment_kpis,
        },
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

    # IMPORTANT: sanitize before returning to FastAPI
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
