from __future__ import annotations

import json
from typing import Any

from .hypothesis_support import summarize_support_for_doc
from .schemas import Insight


def build_doc(insight: Insight) -> str:
    """
    Single self-contained document meant for RAG retrieval.
    Plain English + structured evidence + compact statistical support.
    """
    ev_json = json.dumps(insight.evidence, ensure_ascii=False, indent=2)

    parts = [
        f"Title: {insight.title}",
        f"Severity: {insight.severity}",
        f"Confidence: {insight.confidence:.4f}",
        "",
        "What is happening:",
        insight.description.strip(),
        "",
        "Evidence (structured):",
        ev_json,
        "",
        "Recommended action:",
        insight.recommendation.strip(),
        "",
    ]

    if insight.hypothesis_support:
        parts.append("Statistical support (significant & meaningful relationships):")
        parts.extend(summarize_support_for_doc(insight.hypothesis_support))
        parts.append("")

    parts.append(f"Datasets used: {', '.join(insight.datasets_used)}")
    parts.append(f"Tags: {', '.join(insight.tags)}")
    parts.append(f"Generated at: {insight.created_at}")

    return "\n".join(parts)
