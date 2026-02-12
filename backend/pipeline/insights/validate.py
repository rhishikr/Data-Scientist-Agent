from __future__ import annotations

from .schemas import Insight


def validate_insight(i: Insight) -> list[str]:
    issues: list[str] = []

    if not i.insight_id:
        issues.append("missing_insight_id")
    if not i.title.strip():
        issues.append("missing_title")
    if not i.description.strip():
        issues.append("missing_description")
    if not i.recommendation.strip():
        issues.append("missing_recommendation")
    if i.severity not in ("low", "medium", "high"):
        issues.append("invalid_severity")
    if not (0.0 <= float(i.confidence) <= 1.0):
        issues.append("confidence_out_of_range")
    if not isinstance(i.evidence, dict) or not i.evidence:
        issues.append("missing_evidence")
    if not i.datasets_used:
        issues.append("missing_datasets_used")
    if not i.doc.strip():
        issues.append("missing_doc")
    if not isinstance(i.tags, list):
        issues.append("tags_not_list")

    return issues


def validate_all(insights: list[Insight]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for i in insights:
        issues = validate_insight(i)
        if issues:
            out[i.insight_id] = issues
    return out
