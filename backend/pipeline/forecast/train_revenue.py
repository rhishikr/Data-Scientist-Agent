from __future__ import annotations

from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from joblib import dump
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error

from .features import build_daily_revenue, add_time_features, add_lag_features, train_test_split_time


def _mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    mask = y_true != 0
    if not mask.any():
        return 0.0
    return float(np.mean(np.abs(y_true[mask] - y_pred[mask]) / np.abs(y_true[mask])))


def train_revenue_model(
    transactions: pd.DataFrame,
    models_dir: str,
    model_id: str = "revenue_hgbr_v1",
) -> Tuple[Any, Dict[str, Any], List[str], pd.DataFrame]:
    daily = build_daily_revenue(transactions)
    if daily.empty or len(daily) < 60:
        raise ValueError("Not enough history to train revenue model (need ~60+ days).")

    df = add_time_features(daily, "date")
    df = add_lag_features(df, "revenue")
    df = df.dropna().reset_index(drop=True)

    feature_cols = [c for c in df.columns if c not in ["date", "revenue"]]
    train, test = train_test_split_time(df, test_days=30)

    model = HistGradientBoostingRegressor(max_depth=6, learning_rate=0.05, max_iter=400)
    model.fit(train[feature_cols], train["revenue"])

    pred = model.predict(test[feature_cols])
    metrics = {
        "mae": float(mean_absolute_error(test["revenue"], pred)),
        "mape": _mape(test["revenue"].values, pred),
        "train_rows": int(len(train)),
        "test_rows": int(len(test)),
    }

    dump(model, f"{models_dir}/{model_id}.joblib")
    return model, metrics, feature_cols, df
