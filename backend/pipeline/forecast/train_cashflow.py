from __future__ import annotations

from typing import Any, Dict, List, Tuple

import pandas as pd
from joblib import dump
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error

from .features import _to_dt, add_time_features, add_lag_features, train_test_split_time


def build_daily_cash_proxy(transactions: pd.DataFrame, payments: pd.DataFrame) -> pd.DataFrame:
    """
    Your payments.csv has refund flags/amount but no payment_date.
    So we build a daily CASHFLOW PROXY:
      cash_proxy = daily_revenue - daily_refund_amount

    This is explicitly not settlement-timing cashflow.
    """
    if transactions.empty or "order_datetime" not in transactions.columns:
        return pd.DataFrame(columns=["date", "cash_proxy"])

    tx = transactions.copy()
    tx["order_datetime"] = _to_dt(tx["order_datetime"])
    tx["date"] = tx["order_datetime"].dt.date
    tx["date"] = pd.to_datetime(tx["date"])

    tx["revenue"] = pd.to_numeric(tx.get("total_amount"), errors="coerce")
    if tx["revenue"].isna().all():
        tx["revenue"] = pd.to_numeric(tx.get("quantity"), errors="coerce") * pd.to_numeric(tx.get("unit_price"), errors="coerce")
    tx["revenue"] = tx["revenue"].fillna(0.0)

    daily_rev = tx.groupby("date")["revenue"].sum(min_count=1).reset_index()

    # refunds by day: we can only align to order_date via order_id join (approx)
    refund_daily = None
    if payments is not None and not payments.empty and "order_id" in payments.columns:
        pay = payments.copy()
        pay["order_id"] = pay["order_id"].astype(str)
        tx_ids = tx[["order_id", "date"]].copy()
        tx_ids["order_id"] = tx_ids["order_id"].astype(str)

        if "refund_amount" in pay.columns:
            pay["refund_amount"] = pd.to_numeric(pay["refund_amount"], errors="coerce").fillna(0.0)
            joined = pay.merge(tx_ids, on="order_id", how="left")
            refund_daily = joined.groupby("date")["refund_amount"].sum(min_count=1).reset_index()
        else:
            refund_daily = None

    if refund_daily is not None and not refund_daily.empty:
        daily = daily_rev.merge(refund_daily, on="date", how="left").fillna({"refund_amount": 0.0})
    else:
        daily = daily_rev.copy()
        daily["refund_amount"] = 0.0

    daily["cash_proxy"] = daily["revenue"] - daily["refund_amount"]
    return daily[["date", "cash_proxy"]].sort_values("date")


def train_cashflow_model(
    transactions: pd.DataFrame,
    payments: pd.DataFrame,
    models_dir: str,
    model_id: str = "cashflow_proxy_hgbr_v1",
) -> Tuple[Any, Dict[str, Any], List[str], pd.DataFrame]:
    daily = build_daily_cash_proxy(transactions, payments)
    if daily.empty or len(daily) < 60:
        raise ValueError("Not enough history to train cashflow proxy model (need ~60+ days).")

    df = add_time_features(daily, "date")
    df = add_lag_features(df, y_col="cash_proxy")
    df = df.dropna().reset_index(drop=True)

    feature_cols = [c for c in df.columns if c not in ["date", "cash_proxy"]]
    train, test = train_test_split_time(df, test_days=30)

    model = HistGradientBoostingRegressor(max_depth=6, learning_rate=0.05, max_iter=400)
    model.fit(train[feature_cols], train["cash_proxy"])

    pred = model.predict(test[feature_cols])
    metrics = {
        "mae": float(mean_absolute_error(test["cash_proxy"], pred)),
        "train_rows": int(len(train)),
        "test_rows": int(len(test)),
        "note": "cashflow is a proxy (revenue - refunds aligned to order_date), not settlement-timing cash",
    }

    dump({"model": model, "feature_cols": feature_cols}, f"{models_dir}/{model_id}.joblib")
    return model, metrics, feature_cols, df
