from __future__ import annotations

from typing import Any, Dict, List, Tuple

import pandas as pd
from joblib import dump
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, average_precision_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .features import _to_dt, ChurnConfig, infer_as_of


def build_churn_training_table(
    transactions: pd.DataFrame,
    customers_features: pd.DataFrame,
    cfg: ChurnConfig,
) -> pd.DataFrame:
    if transactions.empty or not {"customer_id", "order_datetime"}.issubset(transactions.columns):
        return pd.DataFrame()

    tx = transactions.copy()
    tx["order_datetime"] = _to_dt(tx["order_datetime"])
    tx["customer_id"] = tx["customer_id"].astype(str)

    as_of = infer_as_of(tx, pd.DataFrame())
    start = as_of - pd.Timedelta(days=cfg.lookback_days)
    tx = tx[(tx["order_datetime"] >= start) & (tx["order_datetime"] <= as_of)].copy()
    if tx.empty:
        return pd.DataFrame()

    # revenue
    rev_col = "total_amount" if "total_amount" in tx.columns else None
    if rev_col is None:
        tx["revenue"] = pd.to_numeric(tx.get("quantity"), errors="coerce") * pd.to_numeric(tx.get("unit_price"), errors="coerce")
        rev_col = "revenue"
    tx[rev_col] = pd.to_numeric(tx[rev_col], errors="coerce").fillna(0.0)

    snapshot_dates = pd.date_range(tx["order_datetime"].min().floor("D"), as_of.floor("D"), freq=f"{cfg.snapshot_every_days}D")
    customers = tx["customer_id"].dropna().unique().astype(str)

    rows = []
    tx_sorted = tx.sort_values("order_datetime")

    for snap in snapshot_dates:
        snap_end = pd.Timestamp(snap)
        label_end = snap_end + pd.Timedelta(days=cfg.churn_horizon_days)

        w30 = (snap_end - pd.Timedelta(days=30), snap_end)
        w90 = (snap_end - pd.Timedelta(days=90), snap_end)

        tx_30 = tx_sorted[(tx_sorted["order_datetime"] > w30[0]) & (tx_sorted["order_datetime"] <= w30[1])]
        tx_90 = tx_sorted[(tx_sorted["order_datetime"] > w90[0]) & (tx_sorted["order_datetime"] <= w90[1])]
        tx_future = tx_sorted[(tx_sorted["order_datetime"] > snap_end) & (tx_sorted["order_datetime"] <= label_end)]

        f_orders_30 = tx_30.groupby("customer_id").size()
        f_rev_30 = tx_30.groupby("customer_id")[rev_col].sum()
        f_orders_90 = tx_90.groupby("customer_id").size()
        f_rev_90 = tx_90.groupby("customer_id")[rev_col].sum()

        last_purchase = tx_sorted[tx_sorted["order_datetime"] <= snap_end].groupby("customer_id")["order_datetime"].max()
        recency_days = (snap_end - last_purchase).dt.days

        bought_future = tx_future.groupby("customer_id").size()
        churn = pd.Series(1, index=pd.Index(customers, name="customer_id"), dtype=int)
        churn.loc[bought_future.index] = 0

        base = pd.DataFrame(index=pd.Index(customers, name="customer_id"))
        base["snapshot_date"] = snap_end
        base["orders_30d"] = f_orders_30.reindex(base.index).fillna(0).astype(float)
        base["revenue_30d"] = f_rev_30.reindex(base.index).fillna(0).astype(float)
        base["orders_90d"] = f_orders_90.reindex(base.index).fillna(0).astype(float)
        base["revenue_90d"] = f_rev_90.reindex(base.index).fillna(0).astype(float)
        base["recency_days"] = recency_days.reindex(base.index).fillna(999).astype(float)
        base["churn_30d"] = churn.reindex(base.index).fillna(1).astype(int)

        rows.append(base.reset_index())

    ds = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    if ds.empty:
        return ds

    # join numeric engineered features if available
    if customers_features is not None and not customers_features.empty and "customer_id" in customers_features.columns:
        cf = customers_features.copy()
        cf["customer_id"] = cf["customer_id"].astype(str)
        num_cols = [c for c in cf.columns if c != "customer_id" and pd.api.types.is_numeric_dtype(cf[c])]
        ds = ds.merge(cf[["customer_id"] + num_cols], on="customer_id", how="left")

    return ds


def train_churn_model(
    transactions: pd.DataFrame,
    customers_features: pd.DataFrame,
    models_dir: str,
    cfg: ChurnConfig | None = None,
    model_id: str = "churn_logreg_cal_v1",
) -> Tuple[Any, Dict[str, Any], List[str], pd.DataFrame]:
    cfg = cfg or ChurnConfig()
    ds = build_churn_training_table(transactions, customers_features, cfg)
    if ds.empty or ds["churn_30d"].nunique() < 2:
        raise ValueError("Not enough churn label variation to train churn model.")

    ds["snapshot_date"] = pd.to_datetime(ds["snapshot_date"])
    snaps = sorted(ds["snapshot_date"].unique())
    test_snaps = set(snaps[-4:]) if len(snaps) >= 6 else set(snaps[-2:])

    train = ds[~ds["snapshot_date"].isin(test_snaps)]
    test = ds[ds["snapshot_date"].isin(test_snaps)]

    drop_cols = {"customer_id", "snapshot_date", "churn_30d"}
    feature_cols = [c for c in ds.columns if c not in drop_cols]

    X_train, y_train = train[feature_cols].fillna(0.0), train["churn_30d"]
    X_test, y_test = test[feature_cols].fillna(0.0), test["churn_30d"]

    base = make_pipeline(StandardScaler(), LogisticRegression(max_iter=5000))
    cal = CalibratedClassifierCV(base, method="isotonic", cv=3)
    cal.fit(X_train, y_train)

    p = cal.predict_proba(X_test)[:, 1]
    metrics = {
        "roc_auc": float(roc_auc_score(y_test, p)) if y_test.nunique() > 1 else None,
        "avg_precision": float(average_precision_score(y_test, p)) if y_test.nunique() > 1 else None,
        "train_rows": int(len(train)),
        "test_rows": int(len(test)),
        "positive_rate_train": float(y_train.mean()),
        "positive_rate_test": float(y_test.mean()),
    }

    dump({"model": cal, "feature_cols": feature_cols}, f"{models_dir}/{model_id}.joblib")
    return cal, metrics, feature_cols, ds
