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
    dt = pd.to_datetime(dt, errors="coerce")
    as_of = pd.to_datetime(as_of)

    m_start = as_of.replace(day=1)
    q = (as_of.month - 1) // 3 + 1
    q_start_month = 3 * (q - 1) + 1
    q_start = as_of.replace(month=q_start_month, day=1)
    y_start = as_of.replace(month=1, day=1)

    return {
        "mtd": (dt >= m_start) & (dt <= as_of),
        "qtd": (dt >= q_start) & (dt <= as_of),
        "ytd": (dt >= y_start) & (dt <= as_of),
        "all": dt.notna(),
    }


# =====================================================================
# 1. Revenue KPIs (from transactions)
# =====================================================================

def compute_revenue_kpis(transactions: pd.DataFrame, as_of: pd.Timestamp) -> Dict[str, Any]:
    if transactions.empty:
        return {
            "total_revenue": {"mtd": None, "qtd": None, "ytd": None},
            "revenue_growth_mom": None,
            "aov": None,
            "orders_per_week": None,
            "orders_per_day": None,
            "order_status_breakdown": {},
        }

    tx = transactions.copy()

    if "order_datetime" not in tx.columns:
        return {}

    tx["order_datetime"] = _to_dt(tx["order_datetime"])
    if "total_amount" in tx.columns:
        tx["revenue"] = pd.to_numeric(tx["total_amount"], errors="coerce")
    else:
        tx["revenue"] = pd.to_numeric(tx.get("quantity"), errors="coerce") * pd.to_numeric(tx.get("unit_price"), errors="coerce")

    # Order status breakdown (before filtering)
    order_status_breakdown: Dict[str, int] = {}
    if "order_status" in tx.columns:
        counts = tx["order_status"].astype(str).str.lower().str.strip().value_counts()
        order_status_breakdown = {str(k): int(v) for k, v in counts.items()}

    # filter out cancelled/returned for revenue
    if "order_status" in tx.columns:
        bad = {"canceled", "cancelled", "returned"}
        tx = tx[~tx["order_status"].astype(str).str.lower().isin(bad)]

    masks = _period_masks(tx["order_datetime"], as_of)

    totals = {}
    for k, mask in masks.items():
        if k == "all":
            continue
        totals[k] = float(tx.loc[mask, "revenue"].sum(skipna=True))

    order_count = tx["order_id"].nunique() if "order_id" in tx.columns else len(tx)
    aov = _safe_div(float(tx["revenue"].sum(skipna=True)), float(order_count))

    min_dt = tx["order_datetime"].min()
    max_dt = tx["order_datetime"].max()
    span_days = max(1, int((max_dt - min_dt).days) if pd.notna(min_dt) and pd.notna(max_dt) else 1)

    orders_per_day = _safe_div(float(order_count), float(span_days))
    orders_per_week = _safe_div(float(order_count), float(span_days) / 7.0)

    last_30_start = as_of - pd.Timedelta(days=30)
    prev_30_start = as_of - pd.Timedelta(days=60)

    rev_last_30 = float(tx.loc[(tx["order_datetime"] > last_30_start) & (tx["order_datetime"] <= as_of), "revenue"].sum(skipna=True))
    rev_prev_30 = float(tx.loc[(tx["order_datetime"] > prev_30_start) & (tx["order_datetime"] <= last_30_start), "revenue"].sum(skipna=True))
    growth = _pct_change(rev_last_30, rev_prev_30)

    return {
        "total_revenue": totals,
        "revenue_growth_30d": growth,
        "average_order_value": aov,
        "orders_per_day": orders_per_day,
        "orders_per_week": orders_per_week,
        "order_status_breakdown": order_status_breakdown,
    }


# =====================================================================
# 2. Customer KPIs
# =====================================================================

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

    # New vs returning
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

    # Repeat purchase rate
    if not transactions.empty and "customer_id" in transactions.columns:
        counts = transactions.groupby("customer_id").size()
        total_buyers = int((counts >= 1).sum())
        repeat_buyers = int((counts >= 2).sum())
        out["repeat_purchase_rate"] = _safe_div(repeat_buyers, total_buyers)
    else:
        out["repeat_purchase_rate"] = None

    # CLV
    if not customers_features.empty and "total_spend" in customers_features.columns:
        clv = pd.to_numeric(customers_features["total_spend"], errors="coerce").dropna()
        out["avg_clv"] = float(clv.mean()) if not clv.empty else None
        out["median_clv"] = float(clv.median()) if not clv.empty else None
    else:
        out["avg_clv"] = None
        out["median_clv"] = None

    # Retention proxy
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


# =====================================================================
# 3. Funnel KPIs (from sessions + events + funnel_summary)
# =====================================================================

def compute_funnel_kpis(
    sessions: pd.DataFrame,
    events: pd.DataFrame,
    funnel_summary: pd.DataFrame,
    web: pd.DataFrame,
    transactions: pd.DataFrame,
    as_of: pd.Timestamp,
) -> Dict[str, Any]:
    """
    Compute funnel KPIs from the new session/event data.
    Falls back to web_analytics if sessions/events are unavailable.
    """
    result: Dict[str, Any] = {
        "conversion_rate": None,
        "cart_abandonment_rate": None,
        "checkout_completion_rate": None,
        "product_view_rate": None,
        "avg_session_duration": None,
        "revenue_per_session": None,
        "mobile_conversion_rate": None,
        "desktop_conversion_rate": None,
        "bounce_rate": None,
        "avg_time_to_purchase_min": None,
        "total_sessions": 0,
        "total_product_views": 0,
        "total_add_to_cart": 0,
        "total_begin_checkout": 0,
        "total_purchases": 0,
    }

    # --- From sessions.csv (primary source) ---
    if not sessions.empty and "session_id" in sessions.columns:
        s = sessions.copy()
        total_sessions = len(s)

        # Conversion rate from converted_flag
        if "converted_flag" in s.columns:
            s["converted_flag"] = s["converted_flag"].astype(str).str.lower().isin(["true", "1", "yes"])
            converted = s["converted_flag"].sum()
            result["conversion_rate"] = _safe_div(float(converted), float(total_sessions))

            # By device
            if "device_type" in s.columns:
                for device in ("mobile", "desktop"):
                    mask = s["device_type"].astype(str).str.lower() == device
                    d_total = mask.sum()
                    d_conv = (s.loc[mask, "converted_flag"]).sum()
                    result[f"{device}_conversion_rate"] = _safe_div(float(d_conv), float(d_total))

        # Avg session duration
        if "session_duration_sec" in s.columns:
            dur = pd.to_numeric(s["session_duration_sec"], errors="coerce")
            result["avg_session_duration"] = float(dur.mean()) if dur.notna().any() else None

        # Revenue per session
        if "revenue" in s.columns:
            rev = pd.to_numeric(s["revenue"], errors="coerce")
            result["revenue_per_session"] = _safe_div(float(rev.sum(skipna=True)), float(total_sessions))

        # Bounce rate (sessions with pages_viewed == 1)
        if "pages_viewed" in s.columns:
            pv = pd.to_numeric(s["pages_viewed"], errors="coerce")
            bounce = (pv == 1).sum()
            result["bounce_rate"] = _safe_div(float(bounce), float(total_sessions))

    # --- From funnel_summary.csv ---
    if not funnel_summary.empty:
        fs = funnel_summary.copy()
        if "conversion_rate" in fs.columns:
            cr = pd.to_numeric(fs["conversion_rate"], errors="coerce").dropna()
            if not cr.empty:
                # Use overall mean if sessions-based wasn't computed
                if result["conversion_rate"] is None:
                    result["conversion_rate"] = float(cr.mean())

        if "cart_abandonment_rate" in fs.columns:
            car = pd.to_numeric(fs["cart_abandonment_rate"], errors="coerce").dropna()
            if not car.empty:
                result["cart_abandonment_rate"] = float(car.mean())

        # Funnel stage totals
        stage_cols = {
            "total_sessions": "sessions",
            "total_product_views": "product_views",
            "total_add_to_cart": "add_to_cart",
            "total_begin_checkout": "checkout_started",
            "total_purchases": "purchases",
        }
        for key, col in stage_cols.items():
            if col in fs.columns:
                result[key] = int(pd.to_numeric(fs[col], errors="coerce").sum(skipna=True))

        # Product view rate from funnel summary
        if {"product_views", "sessions"}.issubset(fs.columns):
            pv_total = pd.to_numeric(fs["product_views"], errors="coerce").sum(skipna=True)
            sess_total = pd.to_numeric(fs["sessions"], errors="coerce").sum(skipna=True)
            result["product_view_rate"] = _safe_div(float(pv_total), float(sess_total))

        # Checkout completion rate from funnel summary
        if {"purchases", "checkout_started"}.issubset(fs.columns):
            purchases = pd.to_numeric(fs["purchases"], errors="coerce").sum(skipna=True)
            checkouts = pd.to_numeric(fs["checkout_started"], errors="coerce").sum(skipna=True)
            result["checkout_completion_rate"] = _safe_div(float(purchases), float(checkouts))

    # --- From events.csv (time to purchase) ---
    if not events.empty and "event_datetime" in events.columns and "session_id" in events.columns:
        ev = events.copy()
        ev["event_datetime"] = _to_dt(ev["event_datetime"])
        if "event_type" in ev.columns:
            first_event = ev.groupby("session_id")["event_datetime"].min()
            purchase_events = ev.loc[ev["event_type"].astype(str).str.lower() == "purchase"]
            if not purchase_events.empty:
                first_purchase = purchase_events.groupby("session_id")["event_datetime"].min()
                joined = pd.concat([first_event, first_purchase], axis=1)
                joined.columns = ["t0", "tp"]
                joined = joined.dropna()
                if not joined.empty:
                    delta_min = (joined["tp"] - joined["t0"]).dt.total_seconds() / 60.0
                    result["avg_time_to_purchase_min"] = float(delta_min.mean())

    # --- Fallback: legacy web_analytics ---
    if result["conversion_rate"] is None and not web.empty and "session_id" in web.columns:
        w = web.copy()
        if "action" in w.columns:
            w["is_purchase"] = w["action"].astype(str).str.lower().eq("purchase")
            total_sessions = w["session_id"].nunique()
            purchase_sessions = w.loc[w["is_purchase"], "session_id"].nunique()
            result["conversion_rate"] = _safe_div(purchase_sessions, total_sessions)

        if result["cart_abandonment_rate"] is None and "add_to_cart" in w.columns:
            atc = w.groupby("session_id")["add_to_cart"].max()
            atc_sessions = int((atc == True).sum())  # noqa
            if "action" in w.columns:
                purchase_sessions = w.loc[w["action"].astype(str).str.lower() == "purchase", "session_id"].nunique()
                non_purchase_atc = atc_sessions - purchase_sessions
                result["cart_abandonment_rate"] = _safe_div(float(max(0, non_purchase_atc)), float(atc_sessions)) if atc_sessions > 0 else None

    return result


# =====================================================================
# 4. Marketing KPIs (from marketing + campaign_performance)
# =====================================================================

def compute_marketing_kpis(marketing: pd.DataFrame, campaign_performance: pd.DataFrame = None) -> Dict[str, Any]:
    if marketing.empty:
        return {
            "cac": None,
            "roas": None,
            "revenue_by_channel": {},
            "campaign_conversion_rate": None,
            "best_performing_campaign": None,
            "worst_performing_campaign": None,
        }

    m = marketing.copy()

    # ROAS from campaign_performance (more accurate) or marketing table
    if campaign_performance is not None and not campaign_performance.empty:
        cp = campaign_performance.copy()
        total_spend = pd.to_numeric(cp.get("spend"), errors="coerce").sum(skipna=True)
        total_rev = pd.to_numeric(cp.get("attributed_revenue"), errors="coerce").sum(skipna=True)
        roas = _safe_div(float(total_rev), float(total_spend))

        # Revenue by channel
        by_channel = {}
        if "channel" in cp.columns and "attributed_revenue" in cp.columns:
            by = cp.groupby("channel")["attributed_revenue"].sum()
            by_channel = {str(k): float(v) for k, v in by.items()}

        # Best/worst campaign by ROAS
        if {"campaign_id", "spend", "attributed_revenue"}.issubset(cp.columns):
            camp_agg = cp.groupby("campaign_id").agg(
                total_spend=("spend", "sum"),
                total_rev=("attributed_revenue", "sum"),
            )
            camp_agg["roas"] = camp_agg["total_rev"] / camp_agg["total_spend"].replace(0, np.nan)
            camp_agg = camp_agg.dropna(subset=["roas"])
            if not camp_agg.empty:
                # Resolve campaign names
                name_map = {}
                if "campaign_name" in cp.columns:
                    name_map = cp.drop_duplicates("campaign_id").set_index("campaign_id")["campaign_name"].to_dict()
                best_id = str(camp_agg["roas"].idxmax())
                worst_id = str(camp_agg["roas"].idxmin())
                best_roas = camp_agg.loc[camp_agg["roas"].idxmax(), "roas"]
                worst_roas = camp_agg.loc[camp_agg["roas"].idxmin(), "roas"]
                best_name = name_map.get(best_id, best_id)
                worst_name = name_map.get(worst_id, worst_id)
                best = f"{best_name} (ROAS: {best_roas:.1f}x)"
                worst = f"{worst_name} (ROAS: {worst_roas:.1f}x)"
            else:
                best = worst = None
        else:
            best = worst = None
    else:
        # Fallback to marketing table
        spend = pd.to_numeric(m.get("ad_spend"), errors="coerce")
        rev = pd.to_numeric(m.get("revenue"), errors="coerce") if "revenue" in m.columns else pd.Series([0])
        total_spend = float(spend.sum(skipna=True))
        roas = _safe_div(float(rev.sum(skipna=True)), total_spend)
        by_channel = {}
        best = worst = None

    # CAC = ad_spend / conversions
    conv = pd.to_numeric(m.get("conversions"), errors="coerce")
    ad_spend = pd.to_numeric(m.get("ad_spend"), errors="coerce")
    cac = _safe_div(float(ad_spend.sum(skipna=True)), float(conv.sum(skipna=True)))

    # Campaign conversion rate: conversions / clicks
    clicks = pd.to_numeric(m.get("clicks"), errors="coerce")
    campaign_cr = _safe_div(float(conv.sum(skipna=True)), float(clicks.sum(skipna=True))) if clicks is not None else None

    return {
        "cac": cac,
        "roas": roas,
        "revenue_by_channel": by_channel,
        "campaign_conversion_rate": campaign_cr,
        "best_performing_campaign": best,
        "worst_performing_campaign": worst,
    }


# =====================================================================
# 5. Product KPIs
# =====================================================================

def compute_product_kpis(products: pd.DataFrame, transactions: pd.DataFrame) -> Tuple[Dict[str, Any], pd.DataFrame, pd.DataFrame]:
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

    tx["sku"] = tx[sku_col].astype(str).str.upper()
    qty = pd.to_numeric(tx.get("quantity"), errors="coerce")
    rev = pd.to_numeric(tx.get("total_amount"), errors="coerce")
    if rev.isna().all():
        rev = pd.to_numeric(tx.get("unit_price"), errors="coerce") * qty

    agg = pd.DataFrame({"sku": tx["sku"], "quantity": qty, "revenue": rev})
    agg = agg.groupby("sku").sum(numeric_only=True).reset_index()

    # join products for names/categories
    if not products.empty:
        p = products.copy()
        p_id = "sku" if "sku" in p.columns else ("product_id" if "product_id" in p.columns else None)
        if p_id:
            p["sku"] = p[p_id].astype(str).str.upper()
            merge_cols = ["sku"]
            for c in ["product_name", "name", "category", "brand", "cost_price", "retail_price", "profit_margin", "discount_percent", "average_rating"]:
                if c in p.columns:
                    merge_cols.append(c)
            agg = agg.merge(p[merge_cols], on="sku", how="left")

            # margin %
            cp = pd.to_numeric(agg.get("cost_price"), errors="coerce")
            rp = pd.to_numeric(agg.get("retail_price"), errors="coerce")
            if cp is not None and rp is not None:
                agg["margin_pct"] = (rp - cp) / rp

    top = agg.sort_values("revenue", ascending=False).head(10).copy()
    low = agg.sort_values("revenue", ascending=True).head(10).copy()

    avg_margin = None
    if "margin_pct" in agg.columns:
        m = agg["margin_pct"].dropna()
        avg_margin = float(m.mean()) if not m.empty else None

    # return rate proxy
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


# =====================================================================
# 6. Inventory KPIs
# =====================================================================

def compute_inventory_kpis(inventory: pd.DataFrame, transactions: pd.DataFrame, as_of: pd.Timestamp) -> Tuple[Dict[str, Any], pd.DataFrame]:
    if inventory.empty:
        return (
            {
                "stock_out_risk_pct": None,
                "inventory_turnover_proxy": None,
            },
            pd.DataFrame(),
        )

    inv = inventory.copy()
    inv["sku"] = inv["sku"].astype(str).str.upper()

    # Use new column names, with fallback
    stock_col = "stock_quantity" if "stock_quantity" in inv.columns else ("stock_level" if "stock_level" in inv.columns else None)
    reorder_col = "reorder_level" if "reorder_level" in inv.columns else ("reorder_threshold" if "reorder_threshold" in inv.columns else None)

    if stock_col:
        inv["stock_level"] = pd.to_numeric(inv[stock_col], errors="coerce")
    else:
        inv["stock_level"] = np.nan

    if reorder_col:
        inv["reorder_threshold"] = pd.to_numeric(inv[reorder_col], errors="coerce")
    else:
        inv["reorder_threshold"] = np.nan

    at_risk = inv.loc[inv["stock_level"].notna() & inv["reorder_threshold"].notna() & (inv["stock_level"] <= inv["reorder_threshold"])].copy()
    stock_out_risk_pct = _safe_div(float(len(at_risk)), float(len(inv))) if len(inv) > 0 else None

    # demand from transactions
    if not transactions.empty and ("order_datetime" in transactions.columns) and ("sku" in transactions.columns or "product_id" in transactions.columns):
        tx = transactions.copy()
        tx["order_datetime"] = _to_dt(tx["order_datetime"])
        tx_sku = "sku" if "sku" in tx.columns else "product_id"
        tx["sku"] = tx[tx_sku].astype(str).str.upper()
        tx["quantity"] = pd.to_numeric(tx.get("quantity"), errors="coerce")

        last_30 = as_of - pd.Timedelta(days=30)
        tx30 = tx.loc[(tx["order_datetime"] > last_30) & (tx["order_datetime"] <= as_of)].copy()

        if not tx30.empty:
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

    # inventory turnover proxy
    turnover = None
    if not transactions.empty and ("quantity" in transactions.columns) and ("sku" in transactions.columns or "product_id" in transactions.columns):
        tx = transactions.copy()
        tx_sku = "sku" if "sku" in tx.columns else "product_id"
        tx["sku"] = tx[tx_sku].astype(str).str.upper()
        tx["quantity"] = pd.to_numeric(tx.get("quantity"), errors="coerce")
        sold_by_sku = tx.groupby("sku")["quantity"].sum(min_count=1)
        inv2 = inv.set_index("sku")
        common = inv2.index.intersection(sold_by_sku.index)
        if len(common) > 0:
            total_sold = float(sold_by_sku.loc[common].sum(skipna=True))
            avg_stock = float(inv2.loc[common, "stock_level"].mean(skipna=True))
            turnover = _safe_div(total_sold, avg_stock)

    # risky products table
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


# =====================================================================
# 7. Forecast KPIs (simple)
# =====================================================================

def compute_forecast_kpis(transactions: pd.DataFrame, as_of: pd.Timestamp) -> Dict[str, Any]:
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


# =====================================================================
# 8. Net Revenue KPIs (from transactions + payments)
# =====================================================================

def compute_net_revenue_kpis(transactions: pd.DataFrame, payments: pd.DataFrame) -> Dict[str, Any]:
    result = {
        "gross_revenue": None,
        "total_discounts": None,
        "total_returns": None,
        "total_refunds": None,
        "total_fees": None,
        "net_revenue": None,
        "discount_rate": None,
    }

    if transactions.empty:
        return result

    tx = transactions.copy()
    rev = pd.to_numeric(tx.get("total_amount"), errors="coerce")
    gross = float(rev.sum(skipna=True))
    result["gross_revenue"] = gross

    # Total discounts
    if "discount_amount" in tx.columns:
        disc = pd.to_numeric(tx["discount_amount"], errors="coerce")
        total_disc = float(disc.sum(skipna=True))
        result["total_discounts"] = total_disc
        result["discount_rate"] = _safe_div(total_disc, gross)
    else:
        total_disc = 0.0

    # Returns (order_status == 'returned')
    if "order_status" in tx.columns:
        returned_mask = tx["order_status"].astype(str).str.lower() == "returned"
        total_returns = float(rev[returned_mask].sum(skipna=True))
        result["total_returns"] = total_returns
    else:
        total_returns = 0.0

    # Refunds + fees from payments
    total_refunds = 0.0
    total_fees = 0.0
    if not payments.empty:
        pay = payments.copy()
        if "payment_status" in pay.columns and "order_id" in pay.columns:
            # Join payment info to transactions to get refund amounts
            refund_orders = pay.loc[pay["payment_status"].astype(str).str.lower() == "refunded", "order_id"]
            if not refund_orders.empty and "order_id" in tx.columns:
                refund_mask = tx["order_id"].isin(refund_orders)
                total_refunds = float(rev[refund_mask].sum(skipna=True))
            result["total_refunds"] = total_refunds

        if "transaction_fee" in pay.columns:
            total_fees = float(pd.to_numeric(pay["transaction_fee"], errors="coerce").sum(skipna=True))
            result["total_fees"] = total_fees

    result["net_revenue"] = gross - total_disc - total_returns - total_refunds - total_fees

    return result


# =====================================================================
# 9. Demographic KPIs (from customers)
# =====================================================================

def compute_demographic_kpis(customers: pd.DataFrame) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "customers_by_gender": {},
        "customers_by_age_group": {},
        "customers_by_loyalty_tier": {},
        "avg_spend_by_loyalty": {},
    }

    if customers.empty:
        return result

    c = customers.copy()

    # Gender distribution
    if "gender" in c.columns:
        dist = c["gender"].value_counts()
        result["customers_by_gender"] = {str(k): int(v) for k, v in dist.items()}

    # Age group distribution
    if "age" in c.columns:
        age = pd.to_numeric(c["age"], errors="coerce").dropna()
        if not age.empty:
            bins = [0, 18, 25, 35, 45, 55, 65, 100]
            labels = ["<18", "18-24", "25-34", "35-44", "45-54", "55-64", "65+"]
            groups = pd.cut(age, bins=bins, labels=labels, right=False)
            dist = groups.value_counts().sort_index()
            result["customers_by_age_group"] = {str(k): int(v) for k, v in dist.items()}

    # Loyalty tier distribution + avg CLV per tier
    if "loyalty_status" in c.columns:
        dist = c["loyalty_status"].value_counts()
        result["customers_by_loyalty_tier"] = {str(k): int(v) for k, v in dist.items()}

        if "total_spend" in c.columns:
            spend = pd.to_numeric(c["total_spend"], errors="coerce")
            avg_by_tier = c.assign(spend=spend).groupby("loyalty_status")["spend"].mean()
            result["avg_spend_by_loyalty"] = {str(k): float(v) for k, v in avg_by_tier.items() if pd.notna(v)}

    return result


# =====================================================================
# 10. Payment KPIs (from payments)
# =====================================================================

def compute_payment_kpis(payments: pd.DataFrame) -> Dict[str, Any]:
    result = {
        "payment_failure_rate": None,
        "refund_rate": None,
        "top_payment_method": None,
        "avg_transaction_fee": None,
        "revenue_by_currency": {},
    }

    if payments.empty:
        return result

    pay = payments.copy()
    total = len(pay)

    if "payment_status" in pay.columns:
        status = pay["payment_status"].astype(str).str.lower()
        failed = (status == "failed").sum()
        refunded = (status == "refunded").sum()
        result["payment_failure_rate"] = _safe_div(float(failed), float(total))
        result["refund_rate"] = _safe_div(float(refunded), float(total))

    if "payment_method" in pay.columns:
        top = pay["payment_method"].value_counts()
        result["top_payment_method"] = str(top.index[0]) if not top.empty else None

    if "transaction_fee" in pay.columns:
        fees = pd.to_numeric(pay["transaction_fee"], errors="coerce")
        result["avg_transaction_fee"] = float(fees.mean()) if fees.notna().any() else None

    if "currency" in pay.columns:
        dist = pay["currency"].value_counts()
        result["revenue_by_currency"] = {str(k): int(v) for k, v in dist.items()}

    return result


# =====================================================================
# 11. Supplier KPIs (from inventory)
# =====================================================================

def compute_supplier_kpis(inventory: pd.DataFrame) -> Dict[str, Any]:
    result = {
        "stockout_by_supplier": {},
        "supplier_reliability_score": {},
    }

    if inventory.empty or "supplier" not in inventory.columns:
        return result

    inv = inventory.copy()
    stock_col = "stock_quantity" if "stock_quantity" in inv.columns else ("stock_level" if "stock_level" in inv.columns else None)
    reorder_col = "reorder_level" if "reorder_level" in inv.columns else ("reorder_threshold" if "reorder_threshold" in inv.columns else None)

    if not stock_col or not reorder_col:
        return result

    inv["_stock"] = pd.to_numeric(inv[stock_col], errors="coerce")
    inv["_reorder"] = pd.to_numeric(inv[reorder_col], errors="coerce")
    inv["_at_risk"] = inv["_stock"] <= inv["_reorder"]

    by_supplier = inv.groupby("supplier").agg(
        total_skus=("sku", "count"),
        at_risk_count=("_at_risk", "sum"),
    )
    by_supplier["reliability_score"] = 1 - (by_supplier["at_risk_count"] / by_supplier["total_skus"])

    result["stockout_by_supplier"] = {str(k): int(v) for k, v in by_supplier["at_risk_count"].items()}
    result["supplier_reliability_score"] = {str(k): round(float(v), 3) for k, v in by_supplier["reliability_score"].items()}

    return result


# =====================================================================
# 12. Brand KPIs (from products + transactions)
# =====================================================================

def compute_brand_kpis(products: pd.DataFrame, transactions: pd.DataFrame) -> Dict[str, Any]:
    result = {
        "revenue_by_brand": {},
        "margin_by_brand": {},
        "rating_by_brand": {},
    }

    if products.empty or "brand" not in products.columns:
        return result

    p = products.copy()

    # Rating by brand
    if "average_rating" in p.columns:
        rating = p.groupby("brand")["average_rating"].mean()
        result["rating_by_brand"] = {str(k): round(float(v), 2) for k, v in rating.items() if pd.notna(v)}

    # Margin by brand
    if "profit_margin" in p.columns:
        margin = p.groupby("brand")["profit_margin"].mean()
        result["margin_by_brand"] = {str(k): round(float(v), 3) for k, v in margin.items() if pd.notna(v)}

    # Revenue by brand (need transactions)
    if not transactions.empty:
        tx = transactions.copy()
        sku_col = "sku" if "sku" in tx.columns else ("product_id" if "product_id" in tx.columns else None)
        if sku_col:
            tx["sku"] = tx[sku_col].astype(str)
            p_sku = "sku" if "sku" in p.columns else ("product_id" if "product_id" in p.columns else None)
            if p_sku:
                p["sku"] = p[p_sku].astype(str)
                merged = tx.merge(p[["sku", "brand"]], on="sku", how="left")
                if "total_amount" in merged.columns:
                    rev = pd.to_numeric(merged["total_amount"], errors="coerce")
                    by_brand = merged.assign(rev=rev).groupby("brand")["rev"].sum()
                    result["revenue_by_brand"] = {str(k): round(float(v), 2) for k, v in by_brand.items() if pd.notna(v)}

    return result
