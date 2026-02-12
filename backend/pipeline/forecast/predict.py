from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd

from .features import add_time_features, add_lag_features


def forecast_next_days_recursive(
    model: Any,
    history: pd.DataFrame,
    date_col: str,
    y_col: str,
    feature_cols: List[str],
    horizon_days: int,
) -> pd.DataFrame:
    """
    Generic recursive forecaster for single-series y_col using lag/rolling features.
    history must contain [date_col, y_col] with daily frequency.
    """
    hist = history[[date_col, y_col]].copy().sort_values(date_col)
    hist[date_col] = pd.to_datetime(hist[date_col])
    last_date = hist[date_col].max()

    # working y series keyed by date
    y_series = hist.set_index(date_col)[y_col].astype(float).sort_index()

    out = []
    for i in range(1, horizon_days + 1):
        d = last_date + pd.Timedelta(days=i)

        row = pd.DataFrame({ "date": [d] })
        row = add_time_features(row, "date")

        # lags
        for l in (1, 7, 14, 28):
            dl = d - pd.Timedelta(days=l)
            row[f"{y_col}_lag_{l}"] = float(y_series.get(dl, np.nan))

        # rolls
        for w in (7, 14, 28):
            window = y_series[(y_series.index < d) & (y_series.index >= d - pd.Timedelta(days=w))]
            row[f"{y_col}_roll_mean_{w}"] = float(window.mean()) if len(window) > 0 else np.nan
            row[f"{y_col}_roll_std_{w}"] = float(window.std()) if len(window) > 1 else np.nan

        X = row[feature_cols].fillna(0.0)
        yhat = float(model.predict(X)[0])
        yhat = max(0.0, yhat)

        out.append({"date": d, "yhat": yhat})
        y_series.loc[d] = yhat

    return pd.DataFrame(out)


def predict_demand_sku(
    bundle: Dict[str, Any],
    sku_history: pd.DataFrame,
    sku_static: Dict[str, Any],
    horizon_days: int = 30,
) -> pd.DataFrame:
    """
    Correct per-SKU demand forecasting.
    - Keeps sku_code/category_code/brand_code consistent with training mappings
    - Computes SKU-grouped lags/rolling from that SKU's own history + predicted values
    """
    model = bundle["model"]
    feature_cols = bundle["feature_cols"]

    # History: columns [date, qty] daily
    hist = sku_history.copy().sort_values("date")
    hist["date"] = pd.to_datetime(hist["date"])
    last_date = hist["date"].max()

    # y series keyed by date
    y_series = hist.set_index("date")["qty"].astype(float).sort_index()

    out = []
    for i in range(1, horizon_days + 1):
        d = last_date + pd.Timedelta(days=i)
        row = pd.DataFrame({"date": [d]})
        row = add_time_features(row, "date")

        # static codes/attrs (carried forward)
        for k, v in sku_static.items():
            row[k] = v

        # SKU lags from y_series
        for l in (1, 7, 14):
            dl = d - pd.Timedelta(days=l)
            row[f"qty_lag_{l}"] = float(y_series.get(dl, np.nan))

        # rolling (7)
        window = y_series[(y_series.index < d) & (y_series.index >= d - pd.Timedelta(days=7))]
        row["qty_roll_mean_7"] = float(window.mean()) if len(window) > 0 else np.nan
        row["qty_roll_std_7"] = float(window.std()) if len(window) > 1 else np.nan

        X = row[feature_cols].fillna(0.0)
        yhat = float(model.predict(X)[0])
        yhat = max(0.0, yhat)

        out.append({"date": d, "qty_forecast": yhat})
        y_series.loc[d] = yhat

    return pd.DataFrame(out)
