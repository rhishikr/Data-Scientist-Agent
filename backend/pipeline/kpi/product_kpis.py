from __future__ import annotations

from typing import Any, Optional

import numpy as np
import pandas as pd

from .math_utils import knee_threshold


def _num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce")


def derive_product_thresholds(products: pd.DataFrame) -> dict[str, Optional[float]]:
    out: dict[str, Optional[float]] = {}

    if products is None or products.empty:
        return out

    if "times_purchased" in products.columns:
        t = knee_threshold(_num(products["times_purchased"]).dropna().values)
        out["high_demand_times_purchased"] = t

    if "stock" in products.columns:
        st = _num(products["stock"]).dropna()
        if not st.empty:
            inv = (st.max() - st)
            t = knee_threshold(inv.values)
            out["low_stock"] = float(st.max() - t) if t is not None else None

    if "discount_percent" in products.columns:
        t = knee_threshold(_num(products["discount_percent"]).dropna().values)
        out["high_discount_percent"] = t

    if "average_rating" in products.columns:
        r = _num(products["average_rating"]).dropna()
        if not r.empty:
            inv = (r.max() - r)
            t = knee_threshold(inv.values)
            out["low_rating"] = float(r.max() - t) if t is not None else None

    return out


def build_product_tables(products: pd.DataFrame) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Tables:
      - risky_products: combines (high demand + low stock) and (low rating)
      - discount_watchlist: high discount + weak revenue-per-purchase (if available)
    Returns: (tables, definitions)
    """
    if products is None or products.empty:
        return {"risky_products": [], "discount_watchlist": []}, {}

    df = products.copy()
    th = derive_product_thresholds(df)

    defs: dict[str, Any] = {
        "high_demand_threshold_times_purchased": th.get("high_demand_times_purchased"),
        "low_stock_threshold": th.get("low_stock"),
        "high_discount_threshold_percent": th.get("high_discount_percent"),
        "low_rating_threshold": th.get("low_rating"),
    }

    # Risky: high demand & low stock
    risky_parts = []

    if th.get("high_demand_times_purchased") is not None and th.get("low_stock") is not None:
        demand = _num(df.get("times_purchased", pd.Series(dtype=float))).fillna(0.0)
        stock = _num(df.get("stock", pd.Series(dtype=float))).fillna(np.inf)

        cand = df[(demand >= float(th["high_demand_times_purchased"])) & (stock <= float(th["low_stock"]))].copy()
        if not cand.empty:
            cand = cand.assign(risk_reason="High demand + low stock")
            risky_parts.append(cand)

    # Risky: low rating
    if th.get("low_rating") is not None and "average_rating" in df.columns:
        rating = _num(df["average_rating"]).fillna(np.inf)
        low = df[rating <= float(th["low_rating"])].copy()
        if not low.empty:
            low = low.assign(risk_reason="Low rating")
            risky_parts.append(low)

    risky = pd.concat(risky_parts, ignore_index=True) if risky_parts else pd.DataFrame()

    cols_risky = [c for c in ["product_id", "name", "category", "brand", "average_rating", "stock", "times_purchased", "total_revenue", "discount_percent", "risk_reason"] if c in (risky.columns if not risky.empty else df.columns)]

    risky_products = []
    if not risky.empty:
        risky_products = (
            risky.sort_values(["total_revenue", "times_purchased"], ascending=[False, False], na_position="last")[cols_risky]
            .head(50)
            .to_dict(orient="records")
        )

    # Discount watchlist
    discount_watchlist = []
    if th.get("high_discount_percent") is not None and "discount_percent" in df.columns:
        disc = _num(df["discount_percent"]).fillna(-np.inf)
        high_disc = df[disc >= float(th["high_discount_percent"])].copy()
        if not high_disc.empty:
            # Revenue-per-purchase if available
            if "total_revenue" in high_disc.columns and "times_purchased" in high_disc.columns:
                rev = _num(high_disc["total_revenue"]).fillna(0.0)
                tp = _num(high_disc["times_purchased"]).replace(0, np.nan)
                rpp = (rev / tp).replace([np.inf, -np.inf], np.nan)

                # Underperformance threshold derived from distribution of rpp within high discount set
                inv = (rpp.max() - rpp)
                t = knee_threshold(inv.dropna().values) if not inv.dropna().empty else None
                under_thr = float(rpp.max() - t) if t is not None else None
                if under_thr is not None:
                    high_disc = high_disc.assign(revenue_per_purchase=rpp)
                    high_disc = high_disc[high_disc["revenue_per_purchase"] <= under_thr].copy()
                    defs["discount_underperformance_threshold_revenue_per_purchase"] = under_thr

            cols_disc = [c for c in ["product_id", "name", "category", "brand", "discount_percent", "total_revenue", "times_purchased", "revenue_per_purchase"] if c in high_disc.columns]
            discount_watchlist = (
                high_disc.sort_values(["discount_percent", "total_revenue"], ascending=[False, False], na_position="last")[cols_disc]
                .head(50)
                .to_dict(orient="records")
            )

    return {"risky_products": risky_products, "discount_watchlist": discount_watchlist}, defs
