import pandas as pd

def build_customer_features(customers: pd.DataFrame, transactions: pd.DataFrame, start_date: pd.Timestamp, end_date: pd.Timestamp):
    # Filter tx to selected window for KPIs (but keep full tx for long-term features if you want)
    tx_window = transactions[(transactions["order_datetime"] >= start_date) & (transactions["order_datetime"] <= end_date)].copy()

    # RFM on full history up to end_date
    tx_hist = transactions[transactions["order_datetime"] <= end_date].copy()

    g = tx_hist.groupby("customer_id").agg(
        last_order=("order_datetime", "max"),
        frequency=("order_id", "nunique"),
        monetary=("total_amount", "sum"),
    ).reset_index()

    g["recencyDays"] = (end_date - g["last_order"]).dt.days.astype(int)

    # last 90d features (better for churn)
    since_90 = end_date - pd.Timedelta(days=90)
    tx_90 = tx_hist[tx_hist["order_datetime"] >= since_90]
    g90 = tx_90.groupby("customer_id").agg(
        frequency90d=("order_id", "nunique"),
        monetary90d=("total_amount", "sum"),
    ).reset_index()

    feats = g.merge(g90, on="customer_id", how="left").fillna({"frequency90d": 0, "monetary90d": 0})

    # join customer attributes
    keep_cols = ["customer_id", "name", "device_type", "avg_session_time_min", "wishlist_items_count", "location"]
    keep_cols = [c for c in keep_cols if c in customers.columns]
    feats = feats.merge(customers[keep_cols], on="customer_id", how="left")

    # segmenting: simple quantiles by monetary & frequency & recency
    # (MVP: rule-based)
    feats["segment"] = "Moderate"
    top_mask = (feats["monetary"] >= feats["monetary"].quantile(0.75)) & (feats["frequency"] >= feats["frequency"].quantile(0.75)) & (feats["recencyDays"] <= feats["recencyDays"].quantile(0.50))
    risk_mask = feats["recencyDays"] >= feats["recencyDays"].quantile(0.75)

    feats.loc[top_mask, "segment"] = "Top Buyer"
    feats.loc[risk_mask, "segment"] = "At-Risk"

    # KPI helpers: active customers in window
    active_ids = tx_window["customer_id"].unique().tolist()
    feats["isActiveInWindow"] = feats["customer_id"].isin(active_ids)

    return feats
