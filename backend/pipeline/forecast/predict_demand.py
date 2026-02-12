from __future__ import annotations

from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd


def _calendar_feats(date: pd.Timestamp) -> Dict[str, int]:
    return {
        "dow": int(date.dayofweek),
        "month": int(date.month),
        "weekofyear": int(date.isocalendar().week),
        "is_weekend": int(date.dayofweek >= 5),
    }


def predict_demand_sku(
    model: Any,
    history: pd.DataFrame,
    feature_cols: List[str],
    sku_to_code: Dict[str, int],
    horizon_days: int = 30,
    min_history_days: int = 30,
) -> pd.DataFrame:
    """
    Proper per-SKU walk-forward forecast.
    Inputs:
      history: DataFrame with columns [date, sku, qty] (daily, filled with zeros recommended)
    Output:
      columns: sku, date, qty_forecast
    """
    if history.empty:
        return pd.DataFrame(columns=["sku", "date", "qty_forecast"])

    history = history.copy()
    history["date"] = pd.to_datetime(history["date"], errors="coerce")
    history["sku"] = history["sku"].astype(str)
    history["qty"] = pd.to_numeric(history["qty"], errors="coerce").fillna(0.0)

    out_rows = []

    for sku, g in history.groupby("sku"):
        g = g.sort_values("date").copy()
        if len(g) < min_history_days:
            continue

        sku_code = sku_to_code.get(str(sku))
        if sku_code is None:
            continue

        # Build a dict date->qty for fast lag/roll lookups, updated with predictions.
        y = dict(zip(g["date"], g["qty"]))
        last_date = g["date"].max()

        for step in range(1, horizon_days + 1):
            d = last_date + pd.Timedelta(days=step)

            # Lags (missing dates treated as 0)
            def lag(k: int) -> float:
                return float(y.get(d - pd.Timedelta(days=k), 0.0))

            # Rolling windows from prior days
            def roll_mean(w: int) -> float:
                vals = [float(y.get(d - pd.Timedelta(days=i), 0.0)) for i in range(1, w + 1)]
                return float(np.mean(vals)) if vals else 0.0

            def roll_std(w: int) -> float:
                vals = [float(y.get(d - pd.Timedelta(days=i), 0.0)) for i in range(1, w + 1)]
                return float(np.std(vals)) if len(vals) > 1 else 0.0

            row = {
                "date": d,
                "sku_code": int(sku_code),
                "qty_lag_1": lag(1),
                "qty_lag_7": lag(7),
                "qty_lag_14": lag(14),
                "qty_roll_mean_7": roll_mean(7),
                "qty_roll_mean_14": roll_mean(14),
                "qty_roll_std_14": roll_std(14),
            }
            row.update(_calendar_feats(d))

            X = pd.DataFrame([row])[feature_cols].fillna(0.0)
            yhat = float(model.predict(X)[0])
            yhat = max(0.0, yhat)

            y[d] = yhat
            out_rows.append({"sku": str(sku), "date": d, "qty_forecast": yhat})

    return pd.DataFrame(out_rows)
