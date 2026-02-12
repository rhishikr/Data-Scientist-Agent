from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Tuple

import numpy as np
import pandas as pd


def _to_dt(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, errors="coerce", utc=False)


def infer_as_of(transactions: pd.DataFrame, transactions_features: pd.DataFrame) -> pd.Timestamp:
    for df, col in [(transactions_features, "order_datetime"), (transactions, "order_datetime")]:
        if df is not None and not df.empty and col in df.columns:
            m = _to_dt(df[col]).max()
            if pd.notna(m):
                return pd.Timestamp(m)
    return pd.Timestamp.utcnow().floor("s")


def infer_revenue_col(df: pd.DataFrame) -> Optional[str]:
    for c in ["revenue", "total_amount", "order_total", "total"]:
        if c in df.columns:
            return c
    return None


def build_daily_revenue(transactions: pd.DataFrame) -> pd.DataFrame:
    if transactions.empty or "order_datetime" not in transactions.columns:
        return pd.DataFrame(columns=["date", "revenue"])

    tx = transactions.copy()
    tx["order_datetime"] = _to_dt(tx["order_datetime"])

    rev_col = infer_revenue_col(tx)
    if rev_col is None:
        tx["revenue"] = pd.to_numeric(tx.get("quantity"), errors="coerce") * pd.to_numeric(tx.get("unit_price"), errors="coerce")
        rev_col = "revenue"

    tx[rev_col] = pd.to_numeric(tx[rev_col], errors="coerce").fillna(0.0)

    if "order_status" in tx.columns:
        bad = {"canceled", "cancelled"}
        tx = tx[~tx["order_status"].astype(str).str.lower().isin(bad)]

    tx["date"] = tx["order_datetime"].dt.date
    daily = tx.groupby("date")[rev_col].sum(min_count=1).reset_index().rename(columns={rev_col: "revenue"})
    daily["date"] = pd.to_datetime(daily["date"])
    daily = daily.sort_values("date")

    # Fill missing calendar days with zero revenue (important)
    if not daily.empty:
        full = pd.date_range(daily["date"].min(), daily["date"].max(), freq="D")
        daily = daily.set_index("date").reindex(full).fillna(0.0).rename_axis("date").reset_index()

    return daily


def add_time_features(df: pd.DataFrame, date_col: str = "date") -> pd.DataFrame:
    out = df.copy()
    d = pd.to_datetime(out[date_col], errors="coerce")
    out["dow"] = d.dt.dayofweek
    out["dom"] = d.dt.day
    out["month"] = d.dt.month
    out["weekofyear"] = d.dt.isocalendar().week.astype(int)
    out["is_weekend"] = (out["dow"] >= 5).astype(int)
    return out


def add_lag_features(df: pd.DataFrame, y_col: str, lags=(1, 7, 14, 28), rolls=(7, 14, 28)) -> pd.DataFrame:
    out = df.copy()
    for l in lags:
        out[f"{y_col}_lag_{l}"] = out[y_col].shift(l)
    for w in rolls:
        out[f"{y_col}_roll_mean_{w}"] = out[y_col].shift(1).rolling(w).mean()
        out[f"{y_col}_roll_std_{w}"] = out[y_col].shift(1).rolling(w).std()
    return out


def train_test_split_time(df: pd.DataFrame, test_days: int = 30) -> Tuple[pd.DataFrame, pd.DataFrame]:
    if df.empty:
        return df, df
    cut = df["date"].max() - pd.Timedelta(days=test_days)
    return df[df["date"] <= cut].copy(), df[df["date"] > cut].copy()


def make_code_map(values: pd.Series) -> Dict[str, int]:
    vals = values.dropna().astype(str).unique().tolist()
    return {v: i for i, v in enumerate(sorted(vals))}


def map_with_default(v: str, mapping: Dict[str, int], default: int = -1) -> int:
    return mapping.get(str(v), default)


@dataclass
class ChurnConfig:
    snapshot_every_days: int = 7
    churn_horizon_days: int = 30
    lookback_days: int = 180
