from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass
class DataPaths:
    base_dir: Path

    @property
    def data_dir(self) -> Path:
        return self.base_dir / "data"

    @property
    def featured_dir(self) -> Path:
        return self.data_dir / "featured_data"

    @property
    def cleaned_dir(self) -> Path:
        return self.data_dir / "cleaned_data"

    @property
    def kpi_dir(self) -> Path:
        return self.data_dir / "kpi_outputs"


def load_featured(paths: DataPaths) -> dict[str, pd.DataFrame]:
    out: dict[str, pd.DataFrame] = {}
    if not paths.featured_dir.exists():
        return out
    for p in paths.featured_dir.glob("*.csv"):
        out[p.stem] = pd.read_csv(p)
    return out


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def read_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
