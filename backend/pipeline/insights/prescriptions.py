"""
Prescription builder: aggregates insights, forecast risks, demand alerts,
and churn data into a prioritized ActionPlan.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, asdict
from typing import Any, Literal


Urgency = Literal["critical", "high", "medium", "low"]
Category = Literal["inventory", "customer", "revenue", "marketing", "product", "funnel", "pricing"]


@dataclass
class Prescription:
    id: str
    priority: int  # 1 = most urgent
    category: Category
    urgency: Urgency
    title: str  # imperative voice: "Restock SKU-1234"
    description: str
    impact_estimate: str
    effort: str  # quick-win | moderate | strategic
    evidence: dict[str, Any]
    source: str  # which agent/analysis produced this
    action_type: str
    related_entities: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ActionPlan:
    health_score: int  # 0-100
    health_summary: str
    prescriptions: list[Prescription]
    generated_at: str
    segment_recommendations: dict[str, list[str]] | None = None

    def to_dict(self) -> dict[str, Any]:
        d = {
            "health_score": self.health_score,
            "health_summary": self.health_summary,
            "prescriptions": [p.to_dict() for p in self.prescriptions],
            "generated_at": self.generated_at,
        }
        if self.segment_recommendations:
            d["segment_recommendations"] = self.segment_recommendations
        return d


def _make_id(*parts: str) -> str:
    return hashlib.md5(":".join(parts).encode()).hexdigest()[:12]


def _severity_to_urgency(severity: str) -> Urgency:
    return {"high": "high", "medium": "medium", "low": "low"}.get(severity, "medium")


def _insight_to_category(tags: list[str]) -> Category:
    tag_set = set(t.lower() for t in tags)
    if tag_set & {"inventory", "stockout", "restock"}:
        return "inventory"
    if tag_set & {"customer", "retention", "churn", "conversion"}:
        return "customer"
    if tag_set & {"revenue", "concentration"}:
        return "revenue"
    if tag_set & {"marketing", "campaign"}:
        return "marketing"
    if tag_set & {"product", "pricing", "quality", "rating", "discount"}:
        return "product"
    return "product"


def prescriptions_from_insights(insights: list[dict[str, Any]]) -> list[Prescription]:
    """Convert insight objects into prescriptions."""
    out: list[Prescription] = []
    for ins in insights:
        rec = ins.get("recommendation", "")
        if not rec:
            continue
        out.append(Prescription(
            id=_make_id("insight", ins.get("insight_id", "")),
            priority=ins.get("priority", 50),
            category=_insight_to_category(ins.get("tags", [])),
            urgency=_severity_to_urgency(ins.get("severity", "medium")),
            title=ins.get("title", "Review insight"),
            description=rec,
            impact_estimate=ins.get("impact_estimate", ""),
            effort=ins.get("effort", "moderate"),
            evidence=ins.get("evidence", {}),
            source="insights_agent",
            action_type=ins.get("action_type", "investigate"),
            related_entities=[],
        ))
    return out


def prescriptions_from_demand(demand_skus: list[dict[str, Any]]) -> list[Prescription]:
    """Convert critical/warning demand SKUs into restock prescriptions."""
    out: list[Prescription] = []
    for sku in demand_skus:
        status = sku.get("status", "healthy")
        if status == "healthy":
            continue
        sku_id = sku.get("sku", sku.get("product_id", "unknown"))
        name = sku.get("product_name", sku_id)
        forecast_qty = sku.get("forecast_qty_30d", 0)
        current_stock = sku.get("current_stock", 0)
        days_left = sku.get("days_until_stockout")

        is_critical = status == "critical"
        urgency: Urgency = "critical" if is_critical else "high"

        days_str = f" ({days_left} days until stockout)" if days_left is not None else ""
        title = f"Restock {name} immediately" if is_critical else f"Restock {name} this week"

        unmet = max(int(forecast_qty) - int(current_stock), 0) if isinstance(forecast_qty, (int, float)) and isinstance(current_stock, (int, float)) else 0
        out.append(Prescription(
            id=_make_id("demand", sku_id),
            priority=1 if is_critical else 8,
            category="inventory",
            urgency=urgency,
            title=title,
            description=(
                f"Order {unmet} units of {name}. Current stock: {current_stock}, 30-day demand: {forecast_qty}{days_str}."
            ),
            impact_estimate=f"{unmet} units of unmet demand on {name}" if unmet > 0 else f"Stockout risk on {name}",
            effort="quick-win",
            evidence=sku,
            source="forecast_agent",
            action_type="restock",
            related_entities=[sku_id],
        ))
    return out


def prescriptions_from_churn(
    churn_predictions: list[dict[str, Any]],
    threshold: float = 0.7,
) -> list[Prescription]:
    """Convert high-churn-risk customers into outreach prescriptions."""
    high_risk = [c for c in churn_predictions if (c.get("churn_prob_30d") or 0) >= threshold]
    if not high_risk:
        return []

    total_value = sum(c.get("total_spend", 0) for c in high_risk)
    customer_ids = [str(c.get("customer_id", "")) for c in high_risk[:10]]

    return [Prescription(
        id=_make_id("churn", str(len(high_risk))),
        priority=12,
        category="customer",
        urgency="high",
        title=f"Email {len(high_risk)} high-risk customers a retention offer this week",
        description=(
            f"{len(high_risk)} customers have >70% churn probability next 30 days. "
            f"Email the top {min(len(high_risk), 20)} highest-value at-risk customers a retention offer. "
            f"${total_value:,.0f} lifetime spend at risk."
        ),
        impact_estimate=f"${total_value:,.0f} customer lifetime value at risk",
        effort="moderate",
        evidence={"high_risk_count": len(high_risk), "total_value_at_risk": total_value},
        source="forecast_agent",
        action_type="outreach",
        related_entities=customer_ids,
    )]


def prescriptions_from_executive_insights(
    executive_insights: dict[str, Any],
) -> list[Prescription]:
    """Convert rule-based recommended actions from forecast snapshot."""
    out: list[Prescription] = []

    # Rule-based actions
    actions = executive_insights.get("recommended_actions_rule_based", [])
    for i, action in enumerate(actions):
        if not action:
            continue
        out.append(Prescription(
            id=_make_id("exec_rule", str(i)),
            priority=20 + i,
            category="revenue",
            urgency="medium",
            title=action if len(action) < 80 else action[:77] + "...",
            description=action,
            impact_estimate="",
            effort="moderate",
            evidence={},
            source="forecast_agent",
            action_type="optimize",
            related_entities=[],
        ))

    # Risks as prescriptions
    risks = executive_insights.get("top_3_risks", [])
    for i, risk in enumerate(risks):
        title = risk.get("title", "") if isinstance(risk, dict) else str(risk)
        if not title:
            continue
        out.append(Prescription(
            id=_make_id("risk", str(i)),
            priority=15 + i,
            category="revenue",
            urgency="high",
            title=f"Mitigate risk: {title}" if len(title) < 60 else title[:77] + "...",
            description=f"Risk identified: {title}",
            impact_estimate="",
            effort="strategic",
            evidence=risk if isinstance(risk, dict) else {"description": str(risk)},
            source="forecast_agent",
            action_type="monitor",
            related_entities=[],
        ))

    return out


def build_segment_recommendations(
    churn_predictions: list[dict[str, Any]],
) -> dict[str, list[str]]:
    """Generate actionable recommendations for each customer segment."""
    # Segment stats
    segments: dict[str, dict[str, Any]] = {}
    for c in churn_predictions:
        seg = c.get("segment", "Unknown")
        if seg not in segments:
            segments[seg] = {"count": 0, "total_spend": 0, "high_churn": 0}
        segments[seg]["count"] += 1
        segments[seg]["total_spend"] += c.get("total_spend", 0)
        if (c.get("churn_prob_30d") or 0) >= 0.6:
            segments[seg]["high_churn"] += 1

    recs: dict[str, list[str]] = {}

    if "Top Buyer" in segments:
        s = segments["Top Buyer"]
        recs["Top Buyer"] = [
            f"Protect your {s['count']} top buyers who drive ${s['total_spend']:,.0f} in revenue",
            "Offer exclusive loyalty rewards, early access to new products, or VIP experiences",
            "Assign dedicated account management for your highest-value customers",
        ]
        if s["high_churn"] > 0:
            recs["Top Buyer"].append(
                f"URGENT: {s['high_churn']} top buyers show high churn risk -- prioritize personal outreach"
            )

    if "Moderate" in segments:
        s = segments["Moderate"]
        recs["Moderate"] = [
            f"Nurture {s['count']} moderate spenders to upgrade their spending",
            "Use targeted cross-sell campaigns based on purchase history",
            "Implement tiered rewards to incentivize higher order values",
        ]

    if "At-Risk" in segments:
        s = segments["At-Risk"]
        recs["At-Risk"] = [
            f"Re-engage {s['count']} at-risk customers before they churn",
            "Send win-back campaigns with personalized discounts",
            "Survey churning customers to understand dissatisfaction drivers",
        ]
        if s["high_churn"] > 0:
            recs["At-Risk"].append(
                f"{s['high_churn']} at-risk customers have >60% churn probability -- act within 7 days"
            )

    return recs


def compute_health_score(
    insights: list[dict[str, Any]],
    demand_skus: list[dict[str, Any]],
    churn_predictions: list[dict[str, Any]],
) -> int:
    """Compute a 0-100 health score. 100 = perfectly healthy.

    Uses proportional deductions capped per category so that large
    datasets don't automatically floor the score to 0.
    """
    # --- Insights penalty (max 30 points) ---
    insight_penalty = 0
    for ins in insights:
        sev = ins.get("severity", "low")
        if sev == "high":
            insight_penalty += 10
        elif sev == "medium":
            insight_penalty += 5
        elif sev == "low":
            insight_penalty += 2
    insight_penalty = min(insight_penalty, 30)

    # --- Inventory penalty (max 30 points) ---
    total_skus = max(len(demand_skus), 1)
    critical_skus = sum(1 for s in demand_skus if s.get("status") == "critical")
    warning_skus = sum(1 for s in demand_skus if s.get("status") == "warning")
    # Proportion-based: what fraction of SKUs are unhealthy
    inv_ratio = (critical_skus * 2 + warning_skus) / total_skus
    inventory_penalty = min(round(inv_ratio * 30), 30)

    # --- Churn penalty (max 20 points) ---
    total_customers = max(len(churn_predictions), 1)
    high_churn = sum(1 for c in churn_predictions if (c.get("churn_prob_30d") or 0) >= 0.7)
    churn_ratio = high_churn / total_customers
    churn_penalty = min(round(churn_ratio * 20), 20)

    # --- Base penalty for having zero data (max 20 points) ---
    no_data_penalty = 0
    if not insights:
        no_data_penalty += 7
    if not demand_skus:
        no_data_penalty += 7
    if not churn_predictions:
        no_data_penalty += 6

    score = 100 - insight_penalty - inventory_penalty - churn_penalty - no_data_penalty
    return max(0, min(100, score))


def build_health_summary(
    health_score: int,
    prescriptions: list[Prescription],
    demand_skus: list[dict[str, Any]],
    churn_predictions: list[dict[str, Any]],
) -> str:
    """Generate a styled HTML health summary (fallback when LLM is unavailable)."""
    critical_count = sum(1 for p in prescriptions if p.urgency == "critical")
    high_count = sum(1 for p in prescriptions if p.urgency == "high")
    stockout_count = sum(1 for s in demand_skus if s.get("status") == "critical")
    churn_count = sum(1 for c in churn_predictions if (c.get("churn_prob_30d") or 0) >= 0.7)

    green = "color:#16a34a;font-weight:600"
    red = "color:#dc2626;font-weight:600"
    bold = "font-weight:600"

    if health_score >= 80:
        status = f"Your store is in <span style='{green}'>good health</span>"
    elif health_score >= 60:
        status = f"Your store <span style='{bold}'>needs attention</span>"
    elif health_score >= 40:
        status = f"Your store has <span style='{red}'>several issues</span> that need action"
    else:
        status = f"Your store requires <span style='{red}'>urgent attention</span>"

    parts = [status + "."]

    alerts = []
    if stockout_count:
        alerts.append(
            f"<span style='{red}'>{stockout_count} SKU{'s' if stockout_count > 1 else ''}</span> near stockout"
        )
    if churn_count:
        alerts.append(
            f"<span style='{red}'>{churn_count} customer{'s' if churn_count > 1 else ''}</span> at high churn risk"
        )
    if alerts:
        parts.append(" and ".join(alerts).capitalize() + ".")

    if critical_count + high_count > 0:
        total = critical_count + high_count
        parts.append(
            f"<span style='{bold}'>{total} action{'s' if total > 1 else ''}</span>"
            f" need{'s' if total == 1 else ''} your attention this week."
        )

    return " ".join(parts)


def build_action_plan(
    insights: list[dict[str, Any]],
    demand_skus: list[dict[str, Any]],
    churn_predictions: list[dict[str, Any]],
    executive_insights: dict[str, Any],
    generated_at: str,
) -> ActionPlan:
    """Build a complete ActionPlan from all data sources."""
    prescriptions: list[Prescription] = []
    prescriptions.extend(prescriptions_from_insights(insights))
    prescriptions.extend(prescriptions_from_demand(demand_skus))
    prescriptions.extend(prescriptions_from_churn(churn_predictions))
    prescriptions.extend(prescriptions_from_executive_insights(executive_insights))

    # Sort by priority (lower = more urgent)
    prescriptions.sort(key=lambda p: p.priority)

    health_score = compute_health_score(insights, demand_skus, churn_predictions)
    health_summary = build_health_summary(
        health_score, prescriptions, demand_skus, churn_predictions,
    )

    segment_recs = build_segment_recommendations(churn_predictions)

    return ActionPlan(
        health_score=health_score,
        health_summary=health_summary,
        prescriptions=prescriptions,
        generated_at=generated_at,
        segment_recommendations=segment_recs if segment_recs else None,
    )
