from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Dict, Any, Optional

import pandas as pd


@dataclass(frozen=True)
class ForecastPaths:
    root: str
    cleaned_dir: str
    featured_dir: str
    hypothesis_json_path: str
    insights_json_path: str
    out_dir: str
    models_dir: str

    @staticmethod
    def default() -> "ForecastPaths":
        # backend/pipeline/forecast/io.py -> backend/
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        return ForecastPaths(
            root=root,
            cleaned_dir=os.path.join(root, "data", "cleaned_data"),
            featured_dir=os.path.join(root, "data", "featured_data"),
            hypothesis_json_path=os.path.join(root, "data", "hypothesis_outputs", "hypothesis_results.json"),
            insights_json_path=os.path.join(root, "data", "insight_outputs", "insights.json"),
            out_dir=os.path.join(root, "data", "forecast_outputs"),
            models_dir=os.path.join(root, "models"),
        )

    @staticmethod
    def from_blackboard(paths: dict) -> "ForecastPaths":
        """Construct ForecastPaths from orchestrator blackboard paths dict."""
        return ForecastPaths(
            root=paths.get("project_root", ""),
            cleaned_dir=paths.get("cleaned_dir", ""),
            featured_dir=paths.get("featured_dir", ""),
            hypothesis_json_path=os.path.join(
                paths.get("hypothesis_dir", ""), "hypothesis_results.json"
            ),
            insights_json_path=os.path.join(
                paths.get("insight_dir", ""), "insights.json"
            ),
            out_dir=paths.get("forecast_dir", ""),
            models_dir=os.path.join(paths.get("project_root", ""), "models"),
        )


def _read_csv(path: str) -> pd.DataFrame:
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.read_csv(path, encoding="latin-1")


def read_datasets(paths: ForecastPaths) -> Dict[str, pd.DataFrame]:
    files = {
        # cleaned
        "customers": os.path.join(paths.cleaned_dir, "customers_cleaned.csv"),
        "inventory": os.path.join(paths.cleaned_dir, "inventory_cleaned.csv"),
        "marketing": os.path.join(paths.cleaned_dir, "marketing_cleaned.csv"),
        "payments": os.path.join(paths.cleaned_dir, "payments_cleaned.csv"),
        "products": os.path.join(paths.cleaned_dir, "products_cleaned.csv"),
        "transactions": os.path.join(paths.cleaned_dir, "transactions_cleaned.csv"),
        "web_analytics": os.path.join(paths.cleaned_dir, "web_analytics_cleaned.csv"),
        # featured
        "customers_features": os.path.join(paths.featured_dir, "customers_features.csv"),
        "products_features": os.path.join(paths.featured_dir, "products_features.csv"),
        "transactions_features": os.path.join(paths.featured_dir, "transactions_features.csv"),
    }

    out: Dict[str, pd.DataFrame] = {}
    for k, p in files.items():
        out[k] = _read_csv(p) if os.path.isfile(p) else pd.DataFrame()
    return out


def read_json(path: str) -> Optional[Dict[str, Any]]:
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: str, payload: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def write_csv(path: str, df: pd.DataFrame) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, index=False)
