from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .hypothesis_support import HypothesisIndex, select_relevant_support
from .math_utils import knee_threshold
from .render import build_doc
from .schemas import Insight, utc_now_iso
from .scoring import confidence_score, severity_from_metric


def _num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce")


def derive_product_thresholds(products: pd.DataFrame) -> dict[str, float]:
    out: dict[str, float] = {}

    if "average_rating" in products.columns:
        # For low tail, we can still use knee on inverted scale
        r = _num(products["average_rating"])
        inv = (r.max() - r)
        t = knee_threshold(inv)
        if t is not None and np.isfinite(t):
            out["low_rating_threshold"] = float(r.max() - t)

    if "discount_percent" in products.columns:
        t = knee_threshold(_num(products["discount_percent"]))
        if t is not None and np.isfinite(t):
            out["high_discount_threshold"] = float(t)

    if "times_purchased" in products.columns:
        t = knee_threshold(_num(products["times_purchased"]))
        if t is not None and np.isfinite(t):
            out["high_demand_threshold"] = float(t)

    if "stock" in products.columns:
        # low stock: knee on inverted stock
        st = _num(products["stock"])
        inv = (st.max() - st)
        t = knee_threshold(inv)
        if t is not None and np.isfinite(t):
            out["low_stock_threshold"] = float(st.max() - t)

    return out


def detect_low_rating_risk(
    products: pd.DataFrame,
    hyp: HypothesisIndex,
    hyp_universe_count: int,
    thresholds: dict[str, float],
) -> list[Insight]:
    if "average_rating" not in products.columns:
        return []
    if "low_rating_threshold" not in thresholds:
        return []

    df = products.copy()
    thr = thresholds["low_rating_threshold"]
    rating = _num(df["average_rating"])

    low = df[rating <= thr].copy()
    if low.empty:
        return []

    total_rev = float(_num(df.get("total_revenue", pd.Series(dtype=float))).fillna(0.0).sum())
    low_rev = float(_num(low.get("total_revenue", pd.Series(dtype=float))).fillna(0.0).sum())
    share = (low_rev / total_rev) if total_rev > 0 else None

    variables = ["average_rating", "total_revenue", "times_purchased", "unique_customers", "discount_percent", "stock"]
    support = select_relevant_support(hyp, "products_features", variables)

    # reference distribution: per-product revenue shares
    rev_shares = []
    if total_rev > 0 and "total_revenue" in df.columns:
        rev_shares = (_num(df["total_revenue"]).fillna(0.0) / total_rev).tolist()

    conf = confidence_score(
        coverage_count=int(len(low)),
        universe_count=int(len(df)),
        support_count=len(support),
        support_universe=hyp_universe_count,
    )

    sev = "medium"
    if share is not None and rev_shares:
        sev = severity_from_metric(float(share), reference_values=rev_shares)
    else:
        prevalence = len(low) / max(len(df), 1)
        sev = severity_from_metric(prevalence, reference_values=[prevalence])

    evidence: dict[str, Any] = {
        "low_rating_threshold": float(thr),
        "count_products": int(len(low)),
        "total_products": int(len(df)),
        "low_rating_revenue_share": float(share) if share is not None else None,
        "examples": low.sort_values("total_revenue", ascending=False)[
            [c for c in ["product_id", "category", "brand", "average_rating", "stock", "total_revenue", "times_purchased"] if c in low.columns]
        ].head(12).to_dict(orient="records"),
    }

    impact_str = f"${low_rev:,.0f} revenue from {int(len(low))} low-rated products" if low_rev > 0 else f"{int(len(low))} low-rated products"

    ins = Insight(
        insight_id="prod_low_rating_risk",
        title="Low-rated products may be creating quality and satisfaction risk",
        description=(
            "A naturally separated low-rating group exists in the catalog. Low ratings typically reduce conversion "
            "and can increase returns or refund pressure."
        ),
        evidence=evidence,
        recommendation=(
            f"Pull the {min(int(len(low)), 3)} worst-rated SKUs from promotion and investigate quality. "
            f"${low_rev:,.0f} in revenue is tied to products rated below {thr:.1f} stars."
        ),
        severity=sev,
        confidence=float(conf),
        datasets_used=["products_features"],
        hypothesis_support=support,
        created_at=utc_now_iso(),
        doc="",
        tags=["product", "quality", "rating", "risk"],
        action_type="investigate",
        impact_estimate=impact_str,
        effort="moderate",
        priority=35,
    )
    ins.doc = build_doc(ins)
    return [ins]


def detect_high_discount_underperformance(
    products: pd.DataFrame,
    hyp: HypothesisIndex,
    hyp_universe_count: int,
    thresholds: dict[str, float],
) -> list[Insight]:
    if "discount_percent" not in products.columns:
        return []
    if "high_discount_threshold" not in thresholds:
        return []

    df = products.copy()
    thr = thresholds["high_discount_threshold"]
    disc = _num(df["discount_percent"])

    high_disc = df[disc >= thr].copy()
    if high_disc.empty:
        return []

    # If we have revenue & purchases, check whether within high-discount group
    # there is a naturally-separated low performance sub-group.
    metric = None
    if "total_revenue" in high_disc.columns and "times_purchased" in high_disc.columns:
        rev = _num(high_disc["total_revenue"]).fillna(0.0)
        tp = _num(high_disc["times_purchased"]).replace(0, np.nan)
        metric = (rev / tp).replace([np.inf, -np.inf], np.nan)

    flagged = high_disc
    metric_thr = None
    if metric is not None:
        inv = (metric.max() - metric)
        t = knee_threshold(inv.dropna())
        if t is not None and np.isfinite(t):
            metric_thr = float(metric.max() - t)
            flagged = high_disc[metric <= metric_thr].copy() if not metric.isna().all() else high_disc

    if flagged.empty:
        return []

    total_rev = float(_num(df.get("total_revenue", pd.Series(dtype=float))).fillna(0.0).sum())
    flagged_rev = float(_num(flagged.get("total_revenue", pd.Series(dtype=float))).fillna(0.0).sum())
    share = (flagged_rev / total_rev) if total_rev > 0 else None

    variables = ["discount_percent", "total_revenue", "times_purchased", "unique_customers", "avg_order_value_per_order"]
    support = select_relevant_support(hyp, "products_features", variables)

    # reference distribution: revenue shares
    rev_shares = []
    if total_rev > 0 and "total_revenue" in df.columns:
        rev_shares = (_num(df["total_revenue"]).fillna(0.0) / total_rev).tolist()

    conf = confidence_score(
        coverage_count=int(len(flagged)),
        universe_count=int(len(df)),
        support_count=len(support),
        support_universe=hyp_universe_count,
    )

    sev = "medium"
    if share is not None and rev_shares:
        sev = severity_from_metric(float(share), reference_values=rev_shares)
    else:
        prevalence = len(flagged) / max(len(df), 1)
        sev = severity_from_metric(prevalence, reference_values=[prevalence])

    evidence: dict[str, Any] = {
        "high_discount_threshold": float(thr),
        "within_group_low_performance_threshold": metric_thr,
        "count_products_flagged": int(len(flagged)),
        "total_products": int(len(df)),
        "flagged_revenue_share": float(share) if share is not None else None,
        "examples": flagged.sort_values("discount_percent", ascending=False)[
            [c for c in ["product_id", "category", "brand", "discount_percent", "total_revenue", "times_purchased"] if c in flagged.columns]
        ].head(12).to_dict(orient="records"),
    }

    impact_str = f"${flagged_rev:,.0f} revenue from {int(len(flagged))} underperforming discounted products" if flagged_rev > 0 else f"{int(len(flagged))} underperforming discounted products"

    ins = Insight(
        insight_id="prod_high_discount_underperformance",
        title="Some high-discount products may be underperforming relative to their discount level",
        description=(
            "A naturally separated high-discount group exists. Within it, a subset shows weaker performance patterns "
            "(when measured by revenue-per-purchase where available). This suggests discounts may not be efficiently driving demand."
        ),
        evidence=evidence,
        recommendation=(
            f"Cut discounts on {int(len(flagged))} underperforming SKUs (currently >{thr:.0f}% off). "
            f"They generate only ${flagged_rev:,.0f} despite heavy markdowns."
        ),
        severity=sev,
        confidence=float(conf),
        datasets_used=["products_features"],
        hypothesis_support=support,
        created_at=utc_now_iso(),
        doc="",
        tags=["product", "pricing", "discount", "margin"],
        action_type="pricing",
        impact_estimate=impact_str,
        effort="moderate",
        priority=30,
    )
    ins.doc = build_doc(ins)
    return [ins]


def detect_high_demand_low_stock(
    products: pd.DataFrame,
    hyp: HypothesisIndex,
    hyp_universe_count: int,
    thresholds: dict[str, float],
) -> list[Insight]:
    if "times_purchased" not in products.columns or "stock" not in products.columns:
        return []
    if "high_demand_threshold" not in thresholds or "low_stock_threshold" not in thresholds:
        return []

    df = products.copy()
    d_thr = thresholds["high_demand_threshold"]
    s_thr = thresholds["low_stock_threshold"]

    demand = _num(df["times_purchased"]).fillna(0.0)
    stock = _num(df["stock"]).fillna(0.0)

    cand = df[(demand >= d_thr) & (stock <= s_thr)].copy()
    if cand.empty:
        return []

    total_rev = float(_num(df.get("total_revenue", pd.Series(dtype=float))).fillna(0.0).sum())
    cand_rev = float(_num(cand.get("total_revenue", pd.Series(dtype=float))).fillna(0.0).sum())
    share = (cand_rev / total_rev) if total_rev > 0 else None

    variables = ["times_purchased", "stock", "total_revenue", "unique_customers", "quantity_std"]
    support = select_relevant_support(hyp, "products_features", variables)

    rev_shares = []
    if total_rev > 0 and "total_revenue" in df.columns:
        rev_shares = (_num(df["total_revenue"]).fillna(0.0) / total_rev).tolist()

    conf = confidence_score(
        coverage_count=int(len(cand)),
        universe_count=int(len(df)),
        support_count=len(support),
        support_universe=hyp_universe_count,
    )

    sev = "medium"
    if share is not None and rev_shares:
        sev = severity_from_metric(float(share), reference_values=rev_shares)
    else:
        prevalence = len(cand) / max(len(df), 1)
        sev = severity_from_metric(prevalence, reference_values=[prevalence])

    evidence: dict[str, Any] = {
        "high_demand_threshold_times_purchased": float(d_thr),
        "low_stock_threshold": float(s_thr),
        "count_products": int(len(cand)),
        "total_products": int(len(df)),
        "revenue_share": float(share) if share is not None else None,
        "examples": cand.sort_values(["times_purchased", "stock"], ascending=[False, True])[
            [c for c in ["product_id", "category", "brand", "times_purchased", "stock", "total_revenue"] if c in cand.columns]
        ].head(12).to_dict(orient="records"),
    }

    impact_str = f"${cand_rev:,.0f} revenue at risk from {int(len(cand))} SKUs near stockout" if cand_rev > 0 else f"{int(len(cand))} SKUs near stockout"

    ins = Insight(
        insight_id="prod_high_demand_low_stock",
        title="Stockout risk detected for high-demand products",
        description=(
            "A naturally separated group of products shows high demand signals while also having unusually low stock. "
            "This combination increases near-term stockout risk and potential lost revenue."
        ),
        evidence=evidence,
        recommendation=(
            f"Restock {int(len(cand))} high-demand SKUs immediately — "
            f"${cand_rev:,.0f} in revenue at risk from stockouts."
        ),
        severity=sev,
        confidence=float(conf),
        datasets_used=["products_features"],
        hypothesis_support=support,
        created_at=utc_now_iso(),
        doc="",
        tags=["product", "inventory", "stockout", "risk"],
        action_type="restock",
        impact_estimate=impact_str,
        effort="quick-win",
        priority=5,
    )
    ins.doc = build_doc(ins)
    return [ins]
