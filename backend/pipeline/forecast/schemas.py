from __future__ import annotations

from typing import Any, Dict, List
from pydantic import BaseModel, Field


class ModelCard(BaseModel):
    model_id: str
    task: str
    target: str
    training_window: Dict[str, Any]
    features_used: List[str]
    metrics: Dict[str, Any] = Field(default_factory=dict)
    caveats: List[str] = Field(default_factory=list)


class ForecastSnapshot(BaseModel):
    meta: Dict[str, Any]
    forecasts: Dict[str, Any]
    executive_insights: Dict[str, Any]
