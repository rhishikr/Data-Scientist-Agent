from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Dict, Any, Optional

import pandas as pd


@dataclass(frozen=True)
class DataPaths:
    root: str
    cleaned_dir: str
    featured_dir: str
    hypothesis_json_path: str
    out_dir: str

    @staticmethod
    def default() -> "DataPaths":
        # backend/pipeline/kpi/io.py -> backend/
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        return DataPaths(
            root=root,
            cleaned_dir=os.path.join(root, "data", "cleaned_data"),
            featured_dir=os.path.join(root, "data", "featured_data"),
            hypothesis_json_path=os.path.join(root, "data", "hypothesis_outputs", "hypothesis_results.json"),
            out_dir=os.path.join(root, "data", "kpi_outputs"),
        )


def _read_csv(path: str) -> pd.DataFrame:
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.read_csv(path, encoding="latin-1")


def read_dataset(paths: DataPaths) -> Dict[str, pd.DataFrame]:
    """
    Reads known datasets if present. Missing files just return empty DFs.
    Keys match your filenames (without .csv).
    """
    files = {
        # cleaned
        "customers": os.path.join(paths.cleaned_dir, "customers.csv"),
        "inventory": os.path.join(paths.cleaned_dir, "inventory.csv"),
        "marketing": os.path.join(paths.cleaned_dir, "marketing.csv"),
        "payments": os.path.join(paths.cleaned_dir, "payments.csv"),
        "products": os.path.join(paths.cleaned_dir, "products.csv"),
        "transactions": os.path.join(paths.cleaned_dir, "transactions.csv"),
        "web_analytics": os.path.join(paths.cleaned_dir, "web_analytics.csv"),
        # featured
        "customers_features": os.path.join(paths.featured_dir, "customers_features.csv"),
        "products_features": os.path.join(paths.featured_dir, "products_features.csv"),
        "transactions_features": os.path.join(paths.featured_dir, "transactions_features.csv"),
    }

    out: Dict[str, pd.DataFrame] = {}
    for k, p in files.items():
        if os.path.isfile(p):
            out[k] = _read_csv(p)
        else:
            out[k] = pd.DataFrame()
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
