from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Literal


Severity = Literal["low", "medium", "high"]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass
class Insight:
    insight_id: str
    title: str
    description: str
    evidence: dict[str, Any]
    recommendation: str
    severity: Severity
    confidence: float
    datasets_used: list[str]
    hypothesis_support: list[dict[str, Any]]
    created_at: str

    # RAG/LLM-friendly
    doc: str
    tags: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class InsightRunMeta:
    generated_at: str
    datasets_used: list[str]
    num_insights: int
    version: str = "insights_v1"


@dataclass
class InsightBundle:
    meta: InsightRunMeta
    insights: list[Insight]
    validation: dict[str, list[str]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "meta": asdict(self.meta),
            "insights": [i.to_dict() for i in self.insights],
            "validation": self.validation,
        }
