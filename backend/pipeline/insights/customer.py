from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .hypothesis_support import HypothesisIndex, select_relevant_support
from .math_utils import knee_threshold, two_knees
from .render import build_doc
from .schemas import Insight, utc_now_iso
from .scoring import confidence_score, severity_from_metric


def _num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce")


def derive_customer_thresholds(customers: pd.DataFrame) -> dict[str, float]:
    """
    Purely data-driven thresholds extracted from distributions.
    """
    out: dict[str, float] = {}

    if "avg_session_time_min" in customers.columns:
        t = knee_threshold(_num(customers["avg_session_time_min"]))
        if t is not None and np.isfinite(t):
            out["engaged_session_min"] = float(t)

    if "wishlist_items_count" in customers.columns:
        t = knee_threshold(_num(customers["wishlist_items_count"]))
        if t is not None and np.isfinite(t):
            out["engaged_wishlist_min"] = float(t)

    # Recency thresholds derived only among buyers (makes churn meaningful)
    if "recency_days" in customers.columns:
        spend = _num(customers.get("total_spend", pd.Series(dtype=float))).fillna(0.0)
        orders = _num(customers.get("total_orders", pd.Series(dtype=float))).fillna(0.0)
        buyers = customers[(spend > 0.0) | (orders > 0.0)]
        if not buyers.empty:
            a, b = two_knees(_num(buyers["recency_days"]))
            if a is not None and np.isfinite(a):
                out["at_risk_recency_days"] = float(a)
            if b is not None and np.isfinite(b):
                out["churn_recency_days"] = float(b)

    # Revenue concentration threshold
    if "total_spend" in customers.columns:
        t = knee_threshold(_num(customers["total_spend"]))
        if t is not None and np.isfinite(t):
            out["top_spend_threshold"] = float(t)

    return out


def detect_engaged_no_purchase(
    customers: pd.DataFrame,
    hyp: HypothesisIndex,
    hyp_universe_count: int,
    thresholds: dict[str, float],
) -> list[Insight]:
    if "customer_id" not in customers.columns:
        return []

    df = customers.copy()
    sess = _num(df.get("avg_session_time_min", pd.Series(dtype=float)))
    wish = _num(df.get("wishlist_items_count", pd.Series(dtype=float)))
    orders = _num(df.get("total_orders", pd.Series(dtype=float))).fillna(0.0)
    spend = _num(df.get("total_spend", pd.Series(dtype=float))).fillna(0.0)

    has_purchase = (orders > 0.0) | (spend > 0.0)

    engaged = pd.Series(False, index=df.index)
    rules: dict[str, Any] = {}

    if "engaged_session_min" in thresholds:
        engaged |= sess >= thresholds["engaged_session_min"]
        rules["engaged_session_min"] = thresholds["engaged_session_min"]

    if "engaged_wishlist_min" in thresholds:
        engaged |= wish >= thresholds["engaged_wishlist_min"]
        rules["engaged_wishlist_min"] = thresholds["engaged_wishlist_min"]

    candidates = df[engaged & (~has_purchase)]
    if candidates.empty:
        return []

    variables = ["avg_session_time_min", "wishlist_items_count", "device_type", "location", "total_orders", "total_spend"]
    support = select_relevant_support(hyp, "customers_features", variables)

    conf = confidence_score(
        coverage_count=int(len(candidates)),
        universe_count=int(len(df)),
        support_count=len(support),
        support_universe=hyp_universe_count,
    )

    # severity metric: prevalence among all customers (no business threshold)
    prevalence = len(candidates) / max(len(df), 1)
    sev = severity_from_metric(prevalence, reference_values=[prevalence])

    evidence = {
        "count_customers": int(len(candidates)),
        "total_customers": int(len(df)),
        "derived_rules": rules,
        "examples": candidates[
            [c for c in ["customer_id", "location", "device_type", "avg_session_time_min", "wishlist_items_count"] if c in candidates.columns]
        ].head(12).to_dict(orient="records"),
    }

    ins = Insight(
        insight_id="cust_engaged_no_purchase",
        title="Engaged customers are not converting into purchases",
        description=(
            "A segment of customers shows high engagement signals (time on site and/or wishlist activity) "
            "but no recorded purchases. This often indicates conversion friction (checkout, pricing, shipping trust, or product fit)."
        ),
        evidence=evidence,
        recommendation=(
            "Investigate conversion friction for this segment: audit checkout steps, validate pricing/competitiveness, "
            "improve trust signals, and run targeted retargeting campaigns. Track the conversion rate of this segment after changes."
        ),
        severity="medium" if prevalence > 0 else "low",
        confidence=float(conf),
        datasets_used=["customers_features"],
        hypothesis_support=support,
        created_at=utc_now_iso(),
        doc="",
        tags=["customer", "conversion", "engagement"],
        action_type="campaign",
        impact_estimate=f"{int(len(candidates))} engaged visitors not converting",
        effort="moderate",
        priority=30 if prevalence > 0.1 else 50,
    )
    ins.doc = build_doc(ins)
    return [ins]


def detect_at_risk_and_churn(
    customers: pd.DataFrame,
    hyp: HypothesisIndex,
    hyp_universe_count: int,
    thresholds: dict[str, float],
) -> list[Insight]:
    if "recency_days" not in customers.columns:
        return []

    df = customers.copy()
    rec = _num(df["recency_days"])
    orders = _num(df.get("total_orders", pd.Series(dtype=float))).fillna(0.0)
    spend = _num(df.get("total_spend", pd.Series(dtype=float))).fillna(0.0)

    buyers = df[(orders > 0.0) | (spend > 0.0)].copy()
    if buyers.empty:
        return []

    out: list[Insight] = []

    variables = ["recency_days", "total_orders", "total_spend", "avg_order_value", "device_type", "location"]
    support = select_relevant_support(hyp, "customers_features", variables)

    # severity reference distribution = per-customer spend shares (for impact-based labeling)
    total_rev = float(_num(buyers.get("total_spend", pd.Series(dtype=float))).fillna(0.0).sum())
    spend_shares = []
    if total_rev > 0:
        spend_shares = ( _num(buyers.get("total_spend", pd.Series(dtype=float))).fillna(0.0) / total_rev ).tolist()

    def make_insight(
        segment_name: str, seg_df: pd.DataFrame, thr: float,
        insight_id: str, title: str, descr: str, rec_text: str,
        action_type: str = "outreach", effort: str = "moderate", priority: int = 20,
    ) -> Insight:
        seg_rev = float(_num(seg_df.get("total_spend", pd.Series(dtype=float))).fillna(0.0).sum())
        impact_share = (seg_rev / total_rev) if total_rev > 0 else None

        conf = confidence_score(
            coverage_count=int(len(seg_df)),
            universe_count=int(len(buyers)),
            support_count=len(support),
            support_universe=hyp_universe_count,
        )

        sev = "medium"
        if impact_share is not None and spend_shares:
            sev = severity_from_metric(float(impact_share), reference_values=spend_shares)
        else:
            prevalence = len(seg_df) / max(len(buyers), 1)
            sev = severity_from_metric(prevalence, reference_values=[prevalence])

        impact_str = f"${seg_rev:,.0f} revenue at risk from {int(len(seg_df))} customers" if seg_rev > 0 else f"{int(len(seg_df))} customers at risk"

        evidence = {
            "segment": segment_name,
            "threshold_recency_days": float(thr),
            "count_customers": int(len(seg_df)),
            "total_buyers": int(len(buyers)),
            "revenue_share_of_buyers": float(impact_share) if impact_share is not None else None,
            "examples": seg_df[
                [c for c in ["customer_id", "location", "device_type", "total_orders", "total_spend", "recency_days", "top_product_id"] if c in seg_df.columns]
            ].head(12).to_dict(orient="records"),
        }

        ins = Insight(
            insight_id=insight_id,
            title=title,
            description=descr,
            evidence=evidence,
            recommendation=rec_text,
            severity=sev,  # data-derived
            confidence=float(conf),
            datasets_used=["customers_features"],
            hypothesis_support=support,
            created_at=utc_now_iso(),
            doc="",
            tags=["customer", "retention", segment_name],
            action_type=action_type,
            impact_estimate=impact_str,
            effort=effort,
            priority=priority,
        )
        ins.doc = build_doc(ins)
        return ins

    if "at_risk_recency_days" in thresholds:
        thr = thresholds["at_risk_recency_days"]
        at_risk = buyers[_num(buyers["recency_days"]) >= thr]
        if not at_risk.empty:
            out.append(
                make_insight(
                    segment_name="at_risk",
                    seg_df=at_risk,
                    thr=thr,
                    insight_id="cust_at_risk",
                    title="A segment of buyers is becoming inactive (at-risk)",
                    descr=(
                        "Buyers with purchase history show elevated inactivity based on the natural separation in the recency distribution. "
                        "This is an early warning signal for churn if they are not re-engaged."
                    ),
                    rec_text=(
                        "Trigger re-engagement for this segment: personalized messages based on past purchases, replenishment reminders, "
                        "and targeted offers. Prioritize high historical spenders first and measure win-back conversion rate."
                    ),
                    action_type="outreach",
                    effort="moderate",
                    priority=15,
                )
            )

    if "churn_recency_days" in thresholds:
        thr = thresholds["churn_recency_days"]
        churn = buyers[_num(buyers["recency_days"]) >= thr]
        if not churn.empty:
            out.append(
                make_insight(
                    segment_name="churn_candidates",
                    seg_df=churn,
                    thr=thr,
                    insight_id="cust_churn_candidates",
                    title="Churn candidates detected from prolonged inactivity",
                    descr=(
                        "A subset of buyers has been inactive for a prolonged period based on the natural separation in the recency distribution. "
                        "These customers are likely churned unless reactivated quickly."
                    ),
                    rec_text=(
                        "Launch a win-back campaign: personalized offers, product reminders based on top_product_id, "
                        "and outreach that prioritizes customers with the highest historical spend. Track time-to-reactivation."
                    ),
                    action_type="campaign",
                    effort="moderate",
                    priority=10,
                )
            )

    return out


def detect_revenue_concentration(
    customers: pd.DataFrame,
    hyp: HypothesisIndex,
    hyp_universe_count: int,
    thresholds: dict[str, float],
) -> list[Insight]:
    if "total_spend" not in customers.columns:
        return []

    df = customers.copy()
    spend = _num(df["total_spend"])
    spenders = df[spend.notna() & (spend > 0.0)].copy()
    if spenders.empty:
        return []

    if "top_spend_threshold" not in thresholds:
        return []

    thr = thresholds["top_spend_threshold"]
    top = spenders[_num(spenders["total_spend"]) >= thr].copy()
    if top.empty:
        return []

    total_rev = float(_num(spenders["total_spend"]).sum())
    top_rev = float(_num(top["total_spend"]).sum())
    share = (top_rev / total_rev) if total_rev > 0 else None

    variables = ["total_spend", "monetary_value", "avg_order_value", "recency_days", "device_type", "location"]
    support = select_relevant_support(hyp, "customers_features", variables)

    # reference distribution: per-customer spend shares
    spend_shares = []
    if total_rev > 0:
        spend_shares = (_num(spenders["total_spend"]) / total_rev).tolist()

    conf = confidence_score(
        coverage_count=int(len(top)),
        universe_count=int(len(spenders)),
        support_count=len(support),
        support_universe=hyp_universe_count,
    )

    sev = "medium"
    if share is not None and spend_shares:
        sev = severity_from_metric(float(share), reference_values=spend_shares)

    evidence: dict[str, Any] = {
        "top_spend_threshold": float(thr),
        "top_customer_count": int(len(top)),
        "total_spenders": int(len(spenders)),
        "total_revenue": total_rev,
        "top_group_revenue": top_rev,
        "top_group_revenue_share": float(share) if share is not None else None,
        "examples": top.sort_values("total_spend", ascending=False)[
            [c for c in ["customer_id", "location", "device_type", "total_orders", "total_spend", "recency_days"] if c in top.columns]
        ].head(12).to_dict(orient="records"),
    }

    impact_str = f"${top_rev:,.0f} revenue ({(share * 100):.0f}% of total) depends on {int(len(top))} customers" if share else ""

    ins = Insight(
        insight_id="cust_revenue_concentration",
        title="Revenue is concentrated among a small group of customers",
        description=(
            "Customer spend forms a naturally separated top group. Revenue concentration increases risk: "
            "if a small number of customers churn, total revenue can drop disproportionately."
        ),
        evidence=evidence,
        recommendation=(
            "Create a retention plan for the top group: proactive outreach, loyalty benefits, and early-warning alerts when recency increases. "
            "Also invest in converting engaged non-buyers and growing mid-tier customers to reduce dependency."
        ),
        severity=sev,
        confidence=float(conf),
        datasets_used=["customers_features"],
        hypothesis_support=support,
        created_at=utc_now_iso(),
        doc="",
        tags=["customer", "revenue", "concentration", "risk"],
        action_type="investigate",
        impact_estimate=impact_str,
        effort="strategic",
        priority=25,
    )
    ins.doc = build_doc(ins)
    return [ins]
