from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass
class KpiMeta:
    generated_at: str
    version: str = "kpi_v1"


@dataclass
class KpiSnapshot:
    meta: KpiMeta
    definitions: dict[str, Any]
    cards: dict[str, Any]
    segments: list[dict[str, Any]]
    trends: dict[str, Any]
    tables: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
