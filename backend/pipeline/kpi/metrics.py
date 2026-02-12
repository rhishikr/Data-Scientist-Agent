from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Tuple, Optional

import numpy as np
import pandas as pd


def _to_dt(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, errors="coerce", utc=False)


def _safe_div(a: float, b: float) -> Optional[float]:
    try:
        if b == 0:
            return None
        return float(a) / float(b)
    except Exception:
        return None


def _pct_change(curr: float, prev: float) -> Optional[float]:
    if prev == 0:
        return None
    return (curr - prev) / prev


def _infer_as_of_date(transactions: pd.DataFrame, web: pd.DataFrame, marketing: pd.DataFrame) -> pd.Timestamp:
    """
    Use the max timestamp in your data as "today" so MTD/QTD/YTD works.
    """
    candidates = []

    if not transactions.empty and "order_datetime" in transactions.columns:
        candidates.append(pd.to_datetime(transactions["order_datetime"], errors="coerce").max())
    if not web.empty and "event_datetime" in web.columns:
        candidates.append(pd.to_datetime(web["event_datetime"], errors="coerce").max())
    if not marketing.empty and "end_date" in marketing.columns:
        candidates.append(pd.to_datetime(marketing["end_date"], errors="coerce").max())

    candidates = [c for c in candidates if pd.notna(c)]
    if not candidates:
        return pd.Timestamp.utcnow()
    return max(candidates)


def _period_masks(dt: pd.Series, as_of: pd.Timestamp) -> Dict[str, pd.Series]:
    """
    Returns masks for MTD/QTD/YTD.
    """
    dt = pd.to_datetime(dt, errors="coerce")
    as_of = pd.to_datetime(as_of)

    # month start
    m_start = as_of.replace(day=1)
    # quarter start
    q = (as_of.month - 1) // 3 + 1
    q_start_month = 3 * (q - 1) + 1
    q_start = as_of.replace(month=q_start_month, day=1)
    # year start
    y_start = as_of.replace(month=1, day=1)

    return {
        "mtd": (dt >= m_start) & (dt <= as_of),
        "qtd": (dt >= q_start) & (dt <= as_of),
        "ytd": (dt >= y_start) & (dt <= as_of),
        "all": dt.notna(),
    }


def compute_revenue_kpis(transactions: pd.DataFrame, as_of: pd.Timestamp) -> Dict[str, Any]:
    if transactions.empty:
        return {
            "total_revenue": {"mtd": None, "qtd": None, "ytd": None},
            "revenue_growth_mom": None,
            "aov": None,
            "orders_per_week": None,
            "orders_per_day": None,
        }

    tx = transactions.copy()

    # expected columns: order_id, order_datetime, total_amount
    if "order_datetime" not in tx.columns:
        return {}

    tx["order_datetime"] = _to_dt(tx["order_datetime"])
    if "total_amount" in tx.columns:
        tx["revenue"] = pd.to_numeric(tx["total_amount"], errors="coerce")
    else:
        # fallback: quantity * unit_price
        tx["revenue"] = pd.to_numeric(tx.get("quantity"), errors="coerce") * pd.to_numeric(tx.get("unit_price"), errors="coerce")

    # optional: ignore canceled if you have such statuses
    if "order_status" in tx.columns:
        bad = {"canceled", "cancelled"}
        tx = tx[~tx["order_status"].astype(str).str.lower().isin(bad)]

    masks = _period_masks(tx["order_datetime"], as_of)

    totals = {}
    for k, mask in masks.items():
        if k == "all":
            continue
        totals[k] = float(tx.loc[mask, "revenue"].sum(skipna=True))

    # AOV
    order_count = tx["order_id"].nunique() if "order_id" in tx.columns else len(tx)
    aov = _safe_div(float(tx["revenue"].sum(skipna=True)), float(order_count))

    # Orders per day/week (using whole span)
    min_dt = tx["order_datetime"].min()
    max_dt = tx["order_datetime"].max()
    span_days = max(1, int((max_dt - min_dt).days) if pd.notna(min_dt) and pd.notna(max_dt) else 1)

    orders_per_day = _safe_div(float(order_count), float(span_days))
    orders_per_week = _safe_div(float(order_count), float(span_days) / 7.0)

    # MoM growth: last 30 days vs previous 30 days (robust for small demo datasets)
    last_30_start = as_of - pd.Timedelta(days=30)
    prev_30_start = as_of - pd.Timedelta(days=60)

    rev_last_30 = float(tx.loc[(tx["order_datetime"] > last_30_start) & (tx["order_datetime"] <= as_of), "revenue"].sum(skipna=True))
    rev_prev_30 = float(tx.loc[(tx["order_datetime"] > prev_30_start) & (tx["order_datetime"] <= last_30_start), "revenue"].sum(skipna=True))
    growth = _pct_change(rev_last_30, rev_prev_30)

    return {
        "total_revenue": totals,                 # mtd/qtd/ytd
        "revenue_growth_30d": growth,            # % change vs previous 30d
        "average_order_value": aov,
        "orders_per_day": orders_per_day,
        "orders_per_week": orders_per_week,
    }


def compute_customer_kpis(customers: pd.DataFrame, customers_features: pd.DataFrame, transactions: pd.DataFrame, as_of: pd.Timestamp) -> Dict[str, Any]:
    out: Dict[str, Any] = {}

    # Active customers: customers who ordered in last 30 days
    if not transactions.empty and "order_datetime" in transactions.columns and "customer_id" in transactions.columns:
        tx = transactions.copy()
        tx["order_datetime"] = _to_dt(tx["order_datetime"])
        last_30 = as_of - pd.Timedelta(days=30)
        active = tx.loc[(tx["order_datetime"] > last_30) & (tx["order_datetime"] <= as_of), "customer_id"].nunique()
        out["active_customers_30d"] = int(active)
    else:
        out["active_customers_30d"] = None

    # New vs returning (based on first purchase date in transactions)
    if not transactions.empty and {"customer_id", "order_datetime"}.issubset(transactions.columns):
        tx = transactions.copy()
        tx["order_datetime"] = _to_dt(tx["order_datetime"])
        first_purchase = tx.groupby("customer_id")["order_datetime"].min()
        last_30 = as_of - pd.Timedelta(days=30)
        new_customers = int((first_purchase > last_30).sum())
        returning_customers = int((first_purchase <= last_30).sum())
        total = new_customers + returning_customers
        out["new_customers_30d"] = new_customers
        out["returning_customers_30d"] = returning_customers
        out["new_vs_returning_pct_30d"] = {
            "new": _safe_div(new_customers, total),
            "returning": _safe_div(returning_customers, total),
        }
    else:
        out["new_customers_30d"] = None
        out["returning_customers_30d"] = None
        out["new_vs_returning_pct_30d"] = {"new": None, "returning": None}

    # Repeat purchase rate (customers with >=2 orders / customers with >=1 order)
    if not transactions.empty and "customer_id" in transactions.columns:
        counts = transactions.groupby("customer_id").size()
        total_buyers = int((counts >= 1).sum())
        repeat_buyers = int((counts >= 2).sum())
        out["repeat_purchase_rate"] = _safe_div(repeat_buyers, total_buyers)
    else:
        out["repeat_purchase_rate"] = None

    # CLV (demo): use customers_features.total_spend if present, else average spend per customer
    if not customers_features.empty and "total_spend" in customers_features.columns:
        clv = pd.to_numeric(customers_features["total_spend"], errors="coerce").dropna()
        out["avg_clv"] = float(clv.mean()) if not clv.empty else None
        out["median_clv"] = float(clv.median()) if not clv.empty else None
    else:
        out["avg_clv"] = None
        out["median_clv"] = None

    # Retention proxy: share of customers who purchased in last 60 days AND also in prior 60 days
    if not transactions.empty and {"customer_id", "order_datetime"}.issubset(transactions.columns):
        tx = transactions.copy()
        tx["order_datetime"] = _to_dt(tx["order_datetime"])
        last_60 = as_of - pd.Timedelta(days=60)
        prev_60 = as_of - pd.Timedelta(days=120)

        set_last = set(tx.loc[(tx["order_datetime"] > last_60) & (tx["order_datetime"] <= as_of), "customer_id"].dropna().astype(str))
        set_prev = set(tx.loc[(tx["order_datetime"] > prev_60) & (tx["order_datetime"] <= last_60), "customer_id"].dropna().astype(str))

        retained = len(set_last.intersection(set_prev))
        out["retention_rate_proxy"] = _safe_div(retained, len(set_prev)) if len(set_prev) > 0 else None
        out["churn_rate_proxy"] = (1 - out["retention_rate_proxy"]) if out["retention_rate_proxy"] is not None else None
    else:
        out["retention_rate_proxy"] = None
        out["churn_rate_proxy"] = None

    return out


def compute_funnel_kpis(web: pd.DataFrame, transactions: pd.DataFrame, as_of: pd.Timestamp) -> Dict[str, Any]:
    """
    Uses web_analytics events.
    - conversion_rate: purchase_sessions / total_sessions
    - cart_abandonment_rate: sessions with abandoned_cart=True / sessions with add_to_cart=True (or all)
    - bounce_rate: sessions with page_views_in_session == 1 / all sessions
    - time_to_purchase: avg minutes between first event and purchase event within a session (only sessions with purchase event)
    """
    if web.empty or "session_id" not in web.columns:
        return {
            "conversion_rate": None,
            "cart_abandonment_rate": None,
            "bounce_rate": None,
            "avg_time_to_purchase_min": None,
            "checkout_completion_rate": None,
        }

    w = web.copy()
    w["event_datetime"] = _to_dt(w.get("event_datetime"))
    if "action" in w.columns:
        w["is_purchase"] = w["action"].astype(str).str.lower().eq("purchase")
    else:
        w["is_purchase"] = False

    total_sessions = w["session_id"].nunique()
    purchase_sessions = w.loc[w["is_purchase"], "session_id"].nunique()
    conversion_rate = _safe_div(purchase_sessions, total_sessions)

    # abandonment
    if "abandoned_cart" in w.columns:
        ab = w.groupby("session_id")["abandoned_cart"].max()
        if "add_to_cart" in w.columns:
            atc = w.groupby("session_id")["add_to_cart"].max()
            denom = int((atc == True).sum())  # noqa
            numer = int((ab == True).sum())   # noqa
            cart_abandonment_rate = _safe_div(numer, denom) if denom > 0 else None
        else:
            cart_abandonment_rate = _safe_div(int((ab == True).sum()), len(ab)) if len(ab) > 0 else None  # noqa
    else:
        cart_abandonment_rate = None

    # bounce
    if "page_views_in_session" in w.columns:
        pv = pd.to_numeric(w.groupby("session_id")["page_views_in_session"].max(), errors="coerce")
        bounce_rate = _safe_div(int((pv == 1).sum()), int(pv.notna().sum())) if pv.notna().sum() > 0 else None
    else:
        bounce_rate = None

    # time to purchase
    if w["event_datetime"].notna().any():
        # per session: first event time, first purchase time
        first_event = w.groupby("session_id")["event_datetime"].min()
        first_purchase = w.loc[w["is_purchase"]].groupby("session_id")["event_datetime"].min()
        joined = pd.concat([first_event, first_purchase], axis=1)
        joined.columns = ["t0", "tp"]
        joined = joined.dropna()
        if not joined.empty:
            delta_min = (joined["tp"] - joined["t0"]).dt.total_seconds() / 60.0
            avg_time_to_purchase_min = float(delta_min.mean())
        else:
            avg_time_to_purchase_min = None
    else:
        avg_time_to_purchase_min = None

    # checkout completion proxy: purchase sessions / checkout page sessions
    if "page_type" in w.columns:
        checkout_sessions = w.loc[w["page_type"].astype(str).str.lower().eq("checkout"), "session_id"].nunique()
        checkout_completion_rate = _safe_div(purchase_sessions, checkout_sessions) if checkout_sessions > 0 else None
    else:
        checkout_completion_rate = None

    return {
        "conversion_rate": conversion_rate,
        "cart_abandonment_rate": cart_abandonment_rate,
        "bounce_rate": bounce_rate,
        "avg_time_to_purchase_min": avg_time_to_purchase_min,
        "checkout_completion_rate": checkout_completion_rate,
    }


def compute_marketing_kpis(marketing: pd.DataFrame) -> Dict[str, Any]:
    if marketing.empty:
        return {
            "cac": None,
            "roas": None,
            "revenue_by_channel": {},
            "campaign_conversion_rate": None,
            "promo_uplift_proxy": None,
        }

    m = marketing.copy()

    # ROAS = revenue / ad_spend
    rev = pd.to_numeric(m.get("revenue"), errors="coerce")
    spend = pd.to_numeric(m.get("ad_spend"), errors="coerce")
    roas = _safe_div(float(rev.sum(skipna=True)), float(spend.sum(skipna=True)))

    # CAC proxy = ad_spend / conversions
    conv = pd.to_numeric(m.get("conversions"), errors="coerce")
    cac = _safe_div(float(spend.sum(skipna=True)), float(conv.sum(skipna=True)))

    # revenue by channel
    by_channel = {}
    if "channel" in m.columns and "revenue" in m.columns:
        by = m.groupby("channel")["revenue"].sum(numeric_only=True)
        by_channel = {str(k): float(v) for k, v in by.items()}

    # campaign conversion rate (from marketing table fields if present)
    if "conversion_rate" in m.columns:
        cr = pd.to_numeric(m["conversion_rate"], errors="coerce").dropna()
        campaign_cr = float(cr.mean()) if not cr.empty else None
    else:
        # fallback conversions / clicks
        clicks = pd.to_numeric(m.get("clicks"), errors="coerce")
        campaign_cr = _safe_div(float(conv.sum(skipna=True)), float(clicks.sum(skipna=True))) if clicks is not None else None

    # promo uplift proxy: compare avg revenue for promo_code != null vs null
    promo_uplift = None
    if "promo_code" in m.columns and "revenue" in m.columns:
        has_promo = m["promo_code"].notna() & (m["promo_code"].astype(str).str.len() > 0)
        r1 = pd.to_numeric(m.loc[has_promo, "revenue"], errors="coerce").dropna()
        r0 = pd.to_numeric(m.loc[~has_promo, "revenue"], errors="coerce").dropna()
        if not r0.empty and not r1.empty:
            promo_uplift = _pct_change(float(r1.mean()), float(r0.mean()))

    return {
        "cac": cac,
        "roas": roas,
        "revenue_by_channel": by_channel,
        "campaign_conversion_rate": campaign_cr,
        "promotion_uplift_proxy": promo_uplift,
    }


def compute_product_kpis(products: pd.DataFrame, transactions: pd.DataFrame) -> Tuple[Dict[str, Any], pd.DataFrame, pd.DataFrame]:
    """
    Returns:
    - dict KPIs
    - top_selling_products df
    - low_performing_products df
    """
    if transactions.empty:
        return (
            {
                "top_selling_products": [],
                "low_performing_products": [],
                "avg_product_margin": None,
                "return_rate_proxy": None,
            },
            pd.DataFrame(),
            pd.DataFrame(),
        )

    tx = transactions.copy()
    sku_col = "sku" if "sku" in tx.columns else ("product_id" if "product_id" in tx.columns else None)
    if sku_col is None:
        return ({}, pd.DataFrame(), pd.DataFrame())

    tx["sku"] = tx[sku_col].astype(str)
    qty = pd.to_numeric(tx.get("quantity"), errors="coerce")
    rev = pd.to_numeric(tx.get("total_amount"), errors="coerce")
    if rev.isna().all():
        rev = pd.to_numeric(tx.get("unit_price"), errors="coerce") * qty

    agg = pd.DataFrame({"sku": tx["sku"], "quantity": qty, "revenue": rev})
    agg = agg.groupby("sku").sum(numeric_only=True).reset_index()

    # join products for names/categories if available
    if not products.empty and "sku" in products.columns:
        p = products.copy()
        p["sku"] = p["sku"].astype(str)
        agg = agg.merge(p[["sku", "name", "category", "cost_price", "retail_price", "discount_percent", "average_rating"]], on="sku", how="left")

        # margin % (retail - cost)/retail
        cp = pd.to_numeric(agg.get("cost_price"), errors="coerce")
        rp = pd.to_numeric(agg.get("retail_price"), errors="coerce")
        agg["margin_pct"] = (rp - cp) / rp

    top = agg.sort_values("revenue", ascending=False).head(10).copy()
    low = agg.sort_values("revenue", ascending=True).head(10).copy()

    avg_margin = None
    if "margin_pct" in agg.columns:
        m = agg["margin_pct"].dropna()
        avg_margin = float(m.mean()) if not m.empty else None

    # return rate proxy: % of orders with status "returned"
    return_rate_proxy = None
    if "order_status" in tx.columns:
        returned = tx["order_status"].astype(str).str.lower().eq("returned").sum()
        total = len(tx)
        return_rate_proxy = _safe_div(float(returned), float(total))

    return (
        {
            "avg_product_margin_pct": avg_margin,
            "return_rate_proxy": return_rate_proxy,
        },
        top,
        low,
    )


def compute_inventory_kpis(inventory: pd.DataFrame, transactions: pd.DataFrame, as_of: pd.Timestamp) -> Tuple[Dict[str, Any], pd.DataFrame]:
    """
    - stock_out_risk: items where stock_level <= reorder_threshold
    - days_of_inventory_remaining: stock_level / avg_daily_qty_sold (from transactions)
    - overstock_risk proxy: high stock with low demand
    """
    if inventory.empty:
        return (
            {
                "stock_out_risk_pct": None,
                "inventory_turnover_proxy": None,
            },
            pd.DataFrame(),
        )

    inv = inventory.copy()
    inv["sku"] = inv["sku"].astype(str)
    inv["stock_level"] = pd.to_numeric(inv.get("stock_level"), errors="coerce")
    inv["reorder_threshold"] = pd.to_numeric(inv.get("reorder_threshold"), errors="coerce")

    at_risk = inv.loc[inv["stock_level"].notna() & inv["reorder_threshold"].notna() & (inv["stock_level"] <= inv["reorder_threshold"])].copy()
    stock_out_risk_pct = _safe_div(float(len(at_risk)), float(len(inv))) if len(inv) > 0 else None

    # demand from transactions: avg daily qty per sku over last 30d
    days_remaining = None
    if not transactions.empty and ("order_datetime" in transactions.columns) and ("sku" in transactions.columns or "product_id" in transactions.columns):
        tx = transactions.copy()
        tx["order_datetime"] = _to_dt(tx["order_datetime"])
        tx_sku = "sku" if "sku" in tx.columns else "product_id"
        tx["sku"] = tx[tx_sku].astype(str)
        tx["quantity"] = pd.to_numeric(tx.get("quantity"), errors="coerce")

        last_30 = as_of - pd.Timedelta(days=30)
        tx30 = tx.loc[(tx["order_datetime"] > last_30) & (tx["order_datetime"] <= as_of)].copy()

        if not tx30.empty:
            # avg daily quantity per sku
            tx30["day"] = tx30["order_datetime"].dt.date
            daily = tx30.groupby(["sku", "day"])["quantity"].sum(min_count=1).reset_index()
            avg_daily = daily.groupby("sku")["quantity"].mean()

            inv = inv.join(avg_daily, on="sku", rsuffix="_avg_daily")
            inv = inv.rename(columns={"quantity": "avg_daily_qty_sold_30d"})
            inv["days_of_inventory_remaining"] = inv["stock_level"] / inv["avg_daily_qty_sold_30d"]
        else:
            inv["avg_daily_qty_sold_30d"] = np.nan
            inv["days_of_inventory_remaining"] = np.nan
    else:
        inv["avg_daily_qty_sold_30d"] = np.nan
        inv["days_of_inventory_remaining"] = np.nan

    # inventory turnover proxy: total qty sold (all time) / avg stock
    turnover = None
    if not transactions.empty and ("quantity" in transactions.columns) and ("sku" in transactions.columns or "product_id" in transactions.columns):
        tx = transactions.copy()
        tx_sku = "sku" if "sku" in tx.columns else "product_id"
        tx["sku"] = tx[tx_sku].astype(str)
        tx["quantity"] = pd.to_numeric(tx.get("quantity"), errors="coerce")
        sold_by_sku = tx.groupby("sku")["quantity"].sum(min_count=1)
        inv2 = inv.set_index("sku")
        common = inv2.index.intersection(sold_by_sku.index)
        if len(common) > 0:
            total_sold = float(sold_by_sku.loc[common].sum(skipna=True))
            avg_stock = float(inv2.loc[common, "stock_level"].mean(skipna=True))
            turnover = _safe_div(total_sold, avg_stock)

    # risky products table: at-risk + soon to stock out within 10 days
    risky = inv.copy()
    risky["risk_flag"] = False
    risky.loc[risky["stock_level"] <= risky["reorder_threshold"], "risk_flag"] = True
    risky.loc[risky["days_of_inventory_remaining"].notna() & (risky["days_of_inventory_remaining"] <= 10), "risk_flag"] = True

    risky_products = risky.loc[risky["risk_flag"] == True].copy()  # noqa
    risky_products = risky_products.sort_values(["risk_flag", "days_of_inventory_remaining"], ascending=[False, True])

    return (
        {
            "stock_out_risk_pct": stock_out_risk_pct,
            "inventory_turnover_proxy": turnover,
        },
        risky_products,
    )


def compute_forecast_kpis(transactions: pd.DataFrame, as_of: pd.Timestamp) -> Dict[str, Any]:
    """
    Lightweight forecast proxies (no ML yet):
    - forecast revenue next 7/30/90: use last 30-day avg daily revenue * horizon
    """
    if transactions.empty or "order_datetime" not in transactions.columns:
        return {
            "forecasted_revenue_7d": None,
            "forecasted_revenue_30d": None,
            "forecasted_revenue_90d": None,
        }

    tx = transactions.copy()
    tx["order_datetime"] = _to_dt(tx["order_datetime"])
    tx["revenue"] = pd.to_numeric(tx.get("total_amount"), errors="coerce")
    if tx["revenue"].isna().all():
        tx["revenue"] = pd.to_numeric(tx.get("unit_price"), errors="coerce") * pd.to_numeric(tx.get("quantity"), errors="coerce")

    last_30 = as_of - pd.Timedelta(days=30)
    tx30 = tx.loc[(tx["order_datetime"] > last_30) & (tx["order_datetime"] <= as_of)].copy()
    if tx30.empty:
        return {"forecasted_revenue_7d": None, "forecasted_revenue_30d": None, "forecasted_revenue_90d": None}

    tx30["day"] = tx30["order_datetime"].dt.date
    daily_rev = tx30.groupby("day")["revenue"].sum(min_count=1)
    avg_daily = float(daily_rev.mean())

    return {
        "forecasted_revenue_7d": avg_daily * 7,
        "forecasted_revenue_30d": avg_daily * 30,
        "forecasted_revenue_90d": avg_daily * 90,
    }
