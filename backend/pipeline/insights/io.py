from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


@dataclass
class DataPaths:
    base_dir: Path

    @property
    def data_dir(self) -> Path:
        return self.base_dir / "data"

    @property
    def cleaned_dir(self) -> Path:
        return self.data_dir / "cleaned_data"

    @property
    def featured_dir(self) -> Path:
        return self.data_dir / "featured_data"

    @property
    def hypothesis_dir(self) -> Path:
        return self.data_dir / "hypothesis_outputs"

    @property
    def insights_dir(self) -> Path:
        return self.data_dir / "insight_outputs"


def load_featured(paths: DataPaths) -> dict[str, pd.DataFrame]:
    data: dict[str, pd.DataFrame] = {}
    if not paths.featured_dir.exists():
        return data
    for p in paths.featured_dir.glob("*.csv"):
        data[p.stem] = pd.read_csv(p)
    return data


def load_cleaned(paths: DataPaths) -> dict[str, pd.DataFrame]:
    data: dict[str, pd.DataFrame] = {}
    if not paths.cleaned_dir.exists():
        return data
    for p in paths.cleaned_dir.glob("*.csv"):
        data[p.stem] = pd.read_csv(p)
    return data


def load_hypothesis_results(paths: DataPaths) -> list[dict[str, Any]]:
    """
    Prefer JSON (richer, consistent). Fall back to CSV if JSON is absent.
    """
    json_path = paths.hypothesis_dir / "hypothesis_results.json"
    csv_path = paths.hypothesis_dir / "hypothesis_results.csv"

    if json_path.exists():
        with open(json_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        return payload.get("results", []) or []

    if csv_path.exists():
        df = pd.read_csv(csv_path)
        return df.to_dict(orient="records")

    return []
