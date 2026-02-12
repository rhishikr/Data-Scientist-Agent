from __future__ import annotations

from typing import Any, Dict, List, Tuple

import pandas as pd
from joblib import dump
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error

from .features import _to_dt, add_time_features, make_code_map, map_with_default


def build_daily_sku_demand(transactions_features: pd.DataFrame) -> pd.DataFrame:
    """
    Uses transactions_features because it has rich product attributes (category, brand, discount_percent, rating, stock).
    Required cols: order_datetime, (sku or product_id), quantity
    """
    if transactions_features.empty or "order_datetime" not in transactions_features.columns:
        return pd.DataFrame()

    tx = transactions_features.copy()
    tx["order_datetime"] = _to_dt(tx["order_datetime"])

    sku_col = "sku" if "sku" in tx.columns else ("product_id" if "product_id" in tx.columns else None)
    if sku_col is None:
        return pd.DataFrame()

    tx["sku"] = tx[sku_col].astype(str)
    tx["qty"] = pd.to_numeric(tx.get("quantity"), errors="coerce").fillna(1.0)
    tx["date"] = tx["order_datetime"].dt.date
    tx["date"] = pd.to_datetime(tx["date"])

    # Static-ish product attributes (take last observed per sku)
    attr_cols = []
    for c in ["category", "brand", "discount_percent", "average_rating", "stock", "cost_price", "retail_price"]:
        if c in tx.columns:
            attr_cols.append(c)

    # daily qty per sku
    daily = tx.groupby(["sku", "date"])["qty"].sum(min_count=1).reset_index()

    # last known attrs per sku (from latest timestamp)
    if attr_cols:
        last = (
            tx.sort_values("order_datetime")
            .groupby("sku", as_index=False)[attr_cols]
            .last()
        )
        daily = daily.merge(last, on="sku", how="left")

    daily = daily.sort_values(["sku", "date"])
    return daily


def add_group_lags(df: pd.DataFrame, y_col: str = "qty") -> pd.DataFrame:
    """
    Lag/rolling per SKU.
    """
    out = df.copy()
    out = out.sort_values(["sku", "date"])

    out[f"{y_col}_lag_1"] = out.groupby("sku")[y_col].shift(1)
    out[f"{y_col}_lag_7"] = out.groupby("sku")[y_col].shift(7)
    out[f"{y_col}_lag_14"] = out.groupby("sku")[y_col].shift(14)
    out[f"{y_col}_roll_mean_7"] = (
        out.groupby("sku")[y_col].shift(1).rolling(7).mean().reset_index(level=0, drop=True)
    )
    out[f"{y_col}_roll_std_7"] = (
        out.groupby("sku")[y_col].shift(1).rolling(7).std().reset_index(level=0, drop=True)
    )
    return out


def train_demand_model(
    transactions_features: pd.DataFrame,
    models_dir: str,
    top_n_skus: int = 75,
    model_id: str = "demand_hgbr_v1",
) -> Tuple[Any, Dict[str, Any], List[str], pd.DataFrame, Dict[str, Dict[str, int]]]:
    df = build_daily_sku_demand(transactions_features)
    if df.empty or len(df) < 500:
        raise ValueError("Not enough SKU demand rows to train demand model.")

    # Focus on top-N SKUs for stability
    sku_totals = df.groupby("sku")["qty"].sum().sort_values(ascending=False)
    keep = set(sku_totals.head(top_n_skus).index.astype(str))
    df = df[df["sku"].astype(str).isin(keep)].copy()

    df = add_time_features(df, "date")

    # Categorical encodings with stable maps
    cat_maps: Dict[str, Dict[str, int]] = {}
    df["sku_code"] = df["sku"].astype("category").cat.codes  # stable within training df
    cat_maps["sku"] = {v: int(i) for i, v in enumerate(df["sku"].astype(str).astype("category").cat.categories)}

    if "category" in df.columns:
        cat_maps["category"] = make_code_map(df["category"])
        df["category_code"] = df["category"].astype(str).map(lambda v: map_with_default(v, cat_maps["category"])).astype(int)
    else:
        df["category_code"] = 0

    if "brand" in df.columns:
        cat_maps["brand"] = make_code_map(df["brand"])
        df["brand_code"] = df["brand"].astype(str).map(lambda v: map_with_default(v, cat_maps["brand"])).astype(int)
    else:
        df["brand_code"] = 0

    # Numeric attrs
    for c in ["discount_percent", "average_rating", "stock", "cost_price", "retail_price"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    df = add_group_lags(df, "qty")
    df = df.dropna().reset_index(drop=True)

    # Features
    drop = {"date", "sku", "qty", "category", "brand"}
    feature_cols = [c for c in df.columns if c not in drop]

    # Time split: last 21 days
    cut = df["date"].max() - pd.Timedelta(days=21)
    train = df[df["date"] <= cut]
    test = df[df["date"] > cut]

    model = HistGradientBoostingRegressor(max_depth=8, learning_rate=0.06, max_iter=450)
    model.fit(train[feature_cols], train["qty"])

    pred = model.predict(test[feature_cols])
    metrics = {
        "mae": float(mean_absolute_error(test["qty"], pred)),
        "train_rows": int(len(train)),
        "test_rows": int(len(test)),
        "skus_modeled": int(df["sku"].nunique()),
        "top_n_skus": int(top_n_skus),
    }

    dump({"model": model, "feature_cols": feature_cols, "cat_maps": cat_maps}, f"{models_dir}/{model_id}.joblib")
    return model, metrics, feature_cols, df, cat_maps
