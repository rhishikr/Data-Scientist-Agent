from __future__ import annotations

from typing import Any, Optional

import numpy as np
import pandas as pd

from .math_utils import jenks_breaks, two_knees, knee_threshold, percentile_rank


def _num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce")


def derive_recency_thresholds(customers: pd.DataFrame) -> dict[str, Optional[float]]:
    """
    Data-driven thresholds from recency distribution among buyers:
    - active_threshold: separates 'recent' group from rest (left-side)
    - at_risk_threshold: right-tail knee
    - churn_threshold: deeper right-tail knee
    """
    if "recency_days" not in customers.columns:
        return {"active": None, "at_risk": None, "churn": None}

    df = customers.copy()
    spend = _num(df.get("total_spend", pd.Series(dtype=float))).fillna(0.0)
    orders = _num(df.get("total_orders", pd.Series(dtype=float))).fillna(0.0)
    buyers = df[(spend > 0.0) | (orders > 0.0)].copy()
    if buyers.empty:
        return {"active": None, "at_risk": None, "churn": None}

    rec = _num(buyers["recency_days"]).dropna()
    if rec.empty:
        return {"active": None, "at_risk": None, "churn": None}

    # ACTIVE: natural breaks for low-recency class boundary
    # Use Jenks k=3: break[1] becomes boundary of "most recent" group.
    br = jenks_breaks(rec.values, k=3)
    active_thr = float(br[1]) if br and len(br) >= 2 else None

    # AT-RISK/CHURN: right-tail knees
    at_risk, churn = two_knees(rec.values)

    return {"active": active_thr, "at_risk": at_risk, "churn": churn}


def derive_top_buyer_threshold(customers: pd.DataFrame) -> Optional[float]:
    if "total_spend" not in customers.columns:
        return None
    spend = _num(customers["total_spend"]).dropna()
    spend = spend[spend > 0]
    if spend.empty:
        return None
    return knee_threshold(spend.values)


def compute_customer_cards_and_segments(customers: pd.DataFrame) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    """
    Returns:
      - cards dict
      - segments list
      - definitions dict (thresholds used)
    """
    cards: dict[str, Any] = {}
    defs: dict[str, Any] = {}

    if customers is None or customers.empty:
        return cards, [], defs

    df = customers.copy()

    # derived thresholds
    rec_th = derive_recency_thresholds(df)
    top_thr = derive_top_buyer_threshold(df)

    defs["active_customer_rule"] = "recency_days <= active_threshold_recency_days (derived from distribution among buyers)"
    defs["active_threshold_recency_days"] = rec_th["active"]
    defs["at_risk_threshold_recency_days"] = rec_th["at_risk"]
    defs["churn_threshold_recency_days"] = rec_th["churn"]
    defs["top_buyer_threshold_total_spend"] = top_thr

    spend = _num(df.get("total_spend", pd.Series(dtype=float))).fillna(0.0)
    orders = _num(df.get("total_orders", pd.Series(dtype=float))).fillna(0.0)
    buyers_mask = (spend > 0.0) | (orders > 0.0)
    buyers = df[buyers_mask].copy()

    # Cards: Active customers
    active_count = None
    if rec_th["active"] is not None and "recency_days" in buyers.columns:
        rec = _num(buyers["recency_days"]).fillna(np.inf)
        active_count = int((rec <= float(rec_th["active"])).sum())
    else:
        active_count = int(len(buyers))  # best-effort fallback

    cards["active_customers"] = active_count

    # Cards: churn risk customers = at_risk union churn candidates (if thresholds exist)
    churn_risk = 0
    if rec_th["at_risk"] is not None and "recency_days" in buyers.columns:
        rec = _num(buyers["recency_days"]).fillna(-np.inf)
        churn_risk = int((rec >= float(rec_th["at_risk"])).sum())
    cards["churn_risk_customers"] = churn_risk

    # Customer value cards
    if not buyers.empty:
        cards["avg_customer_lifetime_value"] = float(_num(buyers.get("total_spend", pd.Series(dtype=float))).fillna(0.0).mean())
        cards["avg_order_value"] = float(_num(buyers.get("avg_order_value", pd.Series(dtype=float))).dropna().mean()) if "avg_order_value" in buyers.columns else None
    else:
        cards["avg_customer_lifetime_value"] = None
        cards["avg_order_value"] = None

    # Retention rate (data-derived definition):
    # repeat buyers / buyers (repeat = total_orders > 1)
    if not buyers.empty and "total_orders" in buyers.columns:
        repeat = int((_num(buyers["total_orders"]).fillna(0.0) > 1.0).sum())
        cards["retention_rate"] = float(repeat / max(len(buyers), 1))
        defs["retention_rate_rule"] = "repeat_buyers / buyers, where repeat_buyers = total_orders > 1"
    else:
        cards["retention_rate"] = None

    # Segments
    segments: list[dict[str, Any]] = []

    total_rev = float(spend.sum())
    if total_rev <= 0:
        total_rev = 0.0

    non_buyers = df[~buyers_mask]
    if not non_buyers.empty:
        segments.append({"name": "Non-Buyers", "count": int(len(non_buyers)), "revenue_share": 0.0})

    if buyers.empty:
        return cards, segments, defs

    # Classify buyers into top/moderate/at-risk/churn_candidates (all thresholds derived)
    rec = _num(buyers.get("recency_days", pd.Series(dtype=float))).fillna(np.inf)
    b_spend = _num(buyers.get("total_spend", pd.Series(dtype=float))).fillna(0.0)

    is_top = pd.Series(False, index=buyers.index)
    if top_thr is not None:
        is_top = b_spend >= float(top_thr)

    is_at_risk = pd.Series(False, index=buyers.index)
    is_churn = pd.Series(False, index=buyers.index)

    if rec_th["at_risk"] is not None:
        is_at_risk = rec >= float(rec_th["at_risk"])
    if rec_th["churn"] is not None:
        is_churn = rec >= float(rec_th["churn"])

    # Define segments (churn is subset of at-risk; report both)
    top_df = buyers[is_top & (~is_at_risk)]
    churn_df = buyers[is_churn]
    at_risk_df = buyers[is_at_risk & (~is_churn)]
    moderate_df = buyers[(~is_top) & (~is_at_risk)]

    def rev_share(seg: pd.DataFrame) -> float:
        if total_rev <= 0 or seg.empty:
            return 0.0
        seg_rev = float(_num(seg.get("total_spend", pd.Series(dtype=float))).fillna(0.0).sum())
        return float(seg_rev / (total_rev + 1e-12))

    segments.extend(
        [
            {"name": "Top Buyers", "count": int(len(top_df)), "revenue_share": rev_share(top_df)},
            {"name": "Moderate", "count": int(len(moderate_df)), "revenue_share": rev_share(moderate_df)},
            {"name": "At-Risk", "count": int(len(at_risk_df)), "revenue_share": rev_share(at_risk_df)},
            {"name": "Churn Candidates", "count": int(len(churn_df)), "revenue_share": rev_share(churn_df)},
        ]
    )

    return cards, segments, defs


def build_customer_tables(customers: pd.DataFrame) -> dict[str, Any]:
    """
    Tables for dashboard drill-down.
    """
    if customers is None or customers.empty:
        return {"top_customers": [], "at_risk_customers": []}

    df = customers.copy()
    spend = _num(df.get("total_spend", pd.Series(dtype=float))).fillna(0.0)
    orders = _num(df.get("total_orders", pd.Series(dtype=float))).fillna(0.0)
    buyers = df[(spend > 0.0) | (orders > 0.0)].copy()
    if buyers.empty:
        return {"top_customers": [], "at_risk_customers": []}

    rec_th = derive_recency_thresholds(buyers)
    rec = _num(buyers.get("recency_days", pd.Series(dtype=float))).fillna(np.inf)

    # churn_risk_score as percentile rank of recency among buyers (higher recency => higher risk)
    rec_vals = rec.to_numpy(dtype=float)
    # invert for rank? No: higher recency => higher risk => rank on recency directly
    ranks = percentile_rank(rec_vals)

    buyers = buyers.assign(churn_risk_score=ranks)

    cols = [c for c in ["customer_id", "name", "location", "device_type", "recency_days", "total_orders", "total_spend", "avg_order_value", "churn_risk_score"] if c in buyers.columns]

    top_customers = (
        buyers.sort_values("total_spend", ascending=False)[cols]
        .head(25)
        .to_dict(orient="records")
    )

    at_risk_customers = []
    if rec_th["at_risk"] is not None:
        ar = buyers[rec >= float(rec_th["at_risk"])].copy()
        at_risk_customers = (
            ar.sort_values(["total_spend", "recency_days"], ascending=[False, False])[cols]
            .head(50)
            .to_dict(orient="records")
        )

    return {"top_customers": top_customers, "at_risk_customers": at_risk_customers}
