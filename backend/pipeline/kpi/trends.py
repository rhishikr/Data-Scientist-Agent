from __future__ import annotations

import pandas as pd
import numpy as np


def _to_dt(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, errors="coerce", utc=False)


def _num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce")


def _trend_frame(tx: pd.DataFrame) -> pd.DataFrame:
    df = tx.copy()
    if "order_datetime" not in df.columns:
        return pd.DataFrame()
    df["order_datetime"] = _to_dt(df["order_datetime"])
    df = df[df["order_datetime"].notna()].copy()
    if df.empty:
        return pd.DataFrame()

    # revenue field preference
    if "total_amount" in df.columns:
        df["revenue"] = _num(df["total_amount"]).fillna(0.0)
    elif "line_amount" in df.columns:
        df["revenue"] = _num(df["line_amount"]).fillna(0.0)
    else:
        df["revenue"] = 0.0

    df["orders"] = 1
    if "customer_id" in df.columns:
        df["customer_id"] = df["customer_id"].astype(str)
    return df


def build_trends(transactions: pd.DataFrame) -> dict:
    """
    Weekly + monthly trends for dashboard charts.
    No hardcoded time windows.
    """
    df = _trend_frame(transactions)
    if df.empty:
        return {"weekly": {}, "monthly": {}}

    def agg(period: str) -> dict:
        # period can be "W" or "M"
        g = df.set_index("order_datetime").groupby(pd.Grouper(freq=period))

        revenue = g["revenue"].sum()
        orders = g["orders"].sum()

        if "customer_id" in df.columns:
            uniq_customers = g["customer_id"].nunique()
        else:
            uniq_customers = pd.Series(index=revenue.index, data=np.nan)

        # AOV = revenue / orders
        aov = revenue / (orders.replace(0, np.nan))
        # revenue per customer = revenue / uniq_customers
        rpc = revenue / (uniq_customers.replace(0, np.nan))

        out = []
        for ts in revenue.index:
            out.append(
                {
                    "period_start": ts.isoformat(),
                    "revenue": float(revenue.loc[ts]) if pd.notna(revenue.loc[ts]) else None,
                    "orders": int(orders.loc[ts]) if pd.notna(orders.loc[ts]) else 0,
                    "unique_customers": int(uniq_customers.loc[ts]) if pd.notna(uniq_customers.loc[ts]) else None,
                    "avg_order_value": float(aov.loc[ts]) if pd.notna(aov.loc[ts]) else None,
                    "revenue_per_customer": float(rpc.loc[ts]) if pd.notna(rpc.loc[ts]) else None,
                }
            )

        return {
            "series": out
        }

    return {
        "weekly": agg("W"),
        "monthly": agg("M"),
    }
