from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Optional, Tuple

import pandas as pd


# ----------------------------
# Helpers
# ----------------------------

def _read_csv_safe(p: Path) -> pd.DataFrame:
    return pd.read_csv(p)


def _pick_first(df: pd.DataFrame, candidates) -> Optional[str]:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def _to_datetime(df: pd.DataFrame, col: Optional[str]) -> None:
    if col and col in df.columns:
        df[col] = pd.to_datetime(df[col], errors="coerce")


def _to_numeric(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce")


def load_cleaned_tables(input_dir: Path) -> Dict[str, pd.DataFrame]:
    """
    Loads all cleaned CSVs into dict.
    Key is inferred from filename.
    Skips any '*sample*' files.
    """
    tables: Dict[str, pd.DataFrame] = {}

    for f in sorted(input_dir.glob("*.csv")):
        stem = f.stem.lower()

        if "sample" in stem:
            continue

        base = stem.replace("_cleaned", "")

        # Map filenames to table keys
        if base.startswith("transactions_with_session"):
            key = "transactions_with_session"
        elif base.startswith("transactions"):
            key = "transactions"
        elif base.startswith("web_analytics") or base.startswith("webanalytics"):
            key = "web_analytics"
        elif base.startswith("campaign_performance"):
            key = "campaign_performance"
        elif base.startswith("funnel_summary"):
            key = "funnel_summary"
        elif base.startswith("inventory"):
            key = "inventory"
        elif base.startswith("customers"):
            key = "customers"
        elif base.startswith("products"):
            key = "products"
        elif base.startswith("sessions"):
            key = "sessions"
        elif base.startswith("events"):
            key = "events"
        elif base.startswith("marketing"):
            key = "marketing"
        elif base.startswith("payments"):
            key = "payments"
        else:
            key = base

        try:
            df = _read_csv_safe(f)
            if key in tables:
                if len(df) > len(tables[key]):
                    tables[key] = df
            else:
                tables[key] = df
        except Exception:
            continue

    return tables


# ----------------------------
# Feature Engineering
# ----------------------------

def build_features_from_all_tables(
    tables: Dict[str, pd.DataFrame]
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:

    customers = tables.get("customers")
    products = tables.get("products")
    transactions = tables.get("transactions")
    web = tables.get("web_analytics")
    inventory = tables.get("inventory")
    sessions = tables.get("sessions")
    events = tables.get("events")

    if customers is None or products is None or transactions is None:
        raise RuntimeError(
            f"Missing required tables. Found keys={sorted(tables.keys())}. "
            f"Need customers + products + transactions."
        )

    # --- identify key columns ---
    cust_id = _pick_first(customers, ["customer_id", "cust_id", "id"])
    prod_id = _pick_first(products, ["sku", "product_id", "prod_id", "id"])

    tx_cust = _pick_first(transactions, ["customer_id", "cust_id"])
    tx_prod = _pick_first(transactions, ["sku", "product_id", "prod_id"])
    tx_order = _pick_first(transactions, ["order_id", "transaction_id", "tx_id", "id"])
    tx_time = _pick_first(transactions, ["order_datetime", "timestamp", "date", "transaction_date", "datetime"])
    qty_col = _pick_first(transactions, ["quantity", "qty", "units"])
    unit_price_col = _pick_first(transactions, ["unit_price", "price_per_unit", "unitprice", "price"])
    total_col = _pick_first(transactions, ["total_amount", "total", "amount"])

    if not cust_id or not prod_id or not tx_cust or not tx_prod:
        raise RuntimeError(
            f"Could not detect join keys. "
            f"cust_id={cust_id}, prod_id={prod_id}, tx_cust={tx_cust}, tx_prod={tx_prod}"
        )

    tx = transactions.copy()
    _to_datetime(tx, tx_time)

    # robust numeric
    if qty_col and qty_col in tx.columns:
        tx[qty_col] = _to_numeric(tx[qty_col]).fillna(0)
    if unit_price_col and unit_price_col in tx.columns:
        tx[unit_price_col] = _to_numeric(tx[unit_price_col]).fillna(0)
    if total_col and total_col in tx.columns:
        tx[total_col] = _to_numeric(tx[total_col])

    # build line amount
    if total_col and total_col in tx.columns and tx[total_col].notna().any():
        tx["line_amount"] = tx[total_col].fillna(0)
    else:
        q = tx[qty_col] if qty_col and qty_col in tx.columns else 0
        p = tx[unit_price_col] if unit_price_col and unit_price_col in tx.columns else 0
        tx["line_amount"] = (q * p).fillna(0)

    # cart_unique_items per order
    if tx_order and tx_order in tx.columns:
        tx["cart_unique_items"] = (
            tx.groupby(tx_order)[tx_prod].transform("nunique")
        )
    else:
        tx["cart_unique_items"] = 1

    # ----------------------------
    # 1) TRANSACTIONS FEATURES (enriched)
    # ----------------------------
    tx_feat = tx.copy()

    # merge customers
    cust_cols = [c for c in customers.columns if c != cust_id]
    tx_feat = tx_feat.merge(
        customers[[cust_id] + cust_cols],
        left_on=tx_cust,
        right_on=cust_id,
        how="left",
        suffixes=("", "_cust"),
    )

    # merge products
    prod_cols = [c for c in products.columns if c != prod_id]
    tx_feat = tx_feat.merge(
        products[[prod_id] + prod_cols],
        left_on=tx_prod,
        right_on=prod_id,
        how="left",
        suffixes=("", "_prod"),
    )

    # ----------------------------
    # 2) CUSTOMERS FEATURES (transactions + sessions + web analytics)
    # ----------------------------
    cust_feat = customers.copy()

    # Drop original total_spend from customers (we'll recompute from transactions)
    if "total_spend" in cust_feat.columns:
        cust_feat = cust_feat.drop(columns=["total_spend"])

    # transaction aggregates per customer
    grp_c = tx.groupby(tx_cust, dropna=True)

    total_orders = grp_c[tx_order].nunique() if tx_order and tx_order in tx.columns else grp_c.size()
    total_qty = grp_c[qty_col].sum() if qty_col and qty_col in tx.columns else grp_c.size()
    total_spend = grp_c["line_amount"].sum()
    avg_order_value = grp_c["line_amount"].mean()

    cust_agg = pd.DataFrame({
        cust_id: total_orders.index,
        "total_orders": total_orders.values,
        "total_quantity": total_qty.values,
        "total_spend": total_spend.values,
        "avg_order_value": avg_order_value.values,
        "monetary_value": total_spend.values,
    })

    # recency + active days
    if tx_time and tx_time in tx.columns and tx[tx_time].notna().any():
        last_ts = grp_c[tx_time].max()
        first_ts = grp_c[tx_time].min()
        global_max = tx[tx_time].max()
        recency_days = (global_max - last_ts).dt.days

        active_days = ((last_ts - first_ts).dt.days + 1).clip(lower=1)
        orders_per_active_day = total_orders / active_days

        cust_agg["recency_days"] = recency_days.values
        cust_agg["orders_per_active_day"] = orders_per_active_day.values

    # top product per customer (by quantity)
    if qty_col and qty_col in tx.columns:
        top_prod = (
            tx.groupby([tx_cust, tx_prod])[qty_col]
            .sum()
            .reset_index()
            .sort_values([tx_cust, qty_col], ascending=[True, False])
            .drop_duplicates(tx_cust)
        )
        top_prod = top_prod.rename(columns={tx_prod: "top_product_id"})
        cust_agg = cust_agg.merge(
            top_prod[[tx_cust, "top_product_id"]],
            on=tx_cust,
            how="left"
        )

    cust_feat = cust_feat.merge(cust_agg, left_on=cust_id, right_on=cust_id, how="left")

    # Session-based features per customer (if sessions table is available)
    if sessions is not None and not sessions.empty:
        sess = sessions.copy()
        sess_cust = _pick_first(sess, ["customer_id", "cust_id"])
        if sess_cust:
            sess_grp = sess.groupby(sess_cust, dropna=True)
            sess_agg = pd.DataFrame({cust_id: sess_grp.size().index})

            sess_agg["sessions_count"] = sess_grp.size().values

            if "session_duration_sec" in sess.columns:
                sess["session_duration_sec"] = _to_numeric(sess["session_duration_sec"])
                sess_agg["avg_session_duration"] = sess_grp["session_duration_sec"].mean().values

            if "converted_flag" in sess.columns:
                # Convert to boolean
                conv_flag = sess["converted_flag"].astype(str).str.lower().isin(["true", "1", "yes"])
                conv_rate = conv_flag.groupby(sess[sess_cust]).mean()
                sess_agg["conversion_rate"] = conv_rate.values

            if "pages_viewed" in sess.columns:
                sess["pages_viewed"] = _to_numeric(sess["pages_viewed"])
                sess_agg["avg_pages_viewed"] = sess_grp["pages_viewed"].mean().values

            cust_feat = cust_feat.merge(sess_agg, on=cust_id, how="left")

    # Web analytics aggregates per customer (fallback if no sessions)
    elif web is not None and not web.empty:
        web_df = web.copy()
        web_cust = _pick_first(web_df, ["customer_id", "cust_id"])

        if web_cust:
            web_grp = web_df.groupby(web_cust, dropna=True)
            web_out = {cust_id: web_grp.size().index}

            dur_col = _pick_first(web_df, ["session_duration_sec", "time_spent", "session_duration", "duration"])
            if dur_col and dur_col in web_df.columns:
                web_df[dur_col] = _to_numeric(web_df[dur_col])
                web_out["avg_session_time_min"] = web_grp[dur_col].mean().values

            web_agg = pd.DataFrame(web_out)
            cust_feat = cust_feat.merge(web_agg, on=cust_id, how="left")

    # Funnel depth per customer (if events table available)
    if events is not None and not events.empty and "event_type" in events.columns:
        ev = events.copy()
        ev_cust = _pick_first(ev, ["customer_id", "cust_id"])
        if ev_cust:
            # Map event types to numeric depth
            depth_map = {
                "page_view": 1,
                "product_view": 2,
                "add_to_cart": 3,
                "begin_checkout": 4,
                "purchase": 5,
            }
            ev["_depth"] = ev["event_type"].astype(str).str.lower().map(depth_map)
            max_depth = ev.groupby(ev_cust)["_depth"].max()
            depth_df = pd.DataFrame({cust_id: max_depth.index, "max_funnel_depth": max_depth.values})
            cust_feat = cust_feat.merge(depth_df, on=cust_id, how="left")

    # Age group buckets
    if "age" in cust_feat.columns:
        age = _to_numeric(cust_feat["age"])
        bins = [0, 18, 25, 35, 45, 55, 65, 200]
        labels = ["<18", "18-24", "25-34", "35-44", "45-54", "55-64", "65+"]
        cust_feat["age_group"] = pd.cut(age, bins=bins, labels=labels, right=False)

    # Loyalty score numeric
    if "loyalty_status" in cust_feat.columns:
        loyalty_map = {"bronze": 1, "silver": 2, "gold": 3, "platinum": 4}
        cust_feat["loyalty_score"] = cust_feat["loyalty_status"].astype(str).str.lower().map(loyalty_map)

    # fill numeric NaNs
    for c in ["total_orders", "total_quantity", "total_spend", "avg_order_value",
              "recency_days", "orders_per_active_day", "monetary_value",
              "sessions_count", "avg_session_duration", "conversion_rate",
              "avg_pages_viewed", "max_funnel_depth", "loyalty_score"]:
        if c in cust_feat.columns:
            cust_feat[c] = _to_numeric(cust_feat[c]).fillna(0)

    # ----------------------------
    # 3) PRODUCTS FEATURES (transactions + inventory)
    # ----------------------------
    prod_feat = products.copy()

    grp_p = tx.groupby(tx_prod, dropna=True)

    times_purchased = grp_p[tx_order].nunique() if tx_order and tx_order in tx.columns else grp_p.size()
    total_qty_sold = grp_p[qty_col].sum() if qty_col and qty_col in tx.columns else grp_p.size()
    total_rev = grp_p["line_amount"].sum()
    avg_order_value_per_order = grp_p["line_amount"].mean()
    unique_customers = grp_p[tx_cust].nunique() if tx_cust in tx.columns else grp_p.size()
    qty_std = grp_p[qty_col].std() if qty_col and qty_col in tx.columns else None

    prod_agg = pd.DataFrame({
        prod_id: times_purchased.index,
        "times_purchased": times_purchased.values,
        "total_quantity_sold": total_qty_sold.values,
        "total_revenue": total_rev.values,
        "avg_order_value_per_order": avg_order_value_per_order.values,
        "unique_customers": unique_customers.values,
    })

    if qty_std is not None:
        prod_agg["quantity_std"] = qty_std.fillna(0).values

    prod_feat = prod_feat.merge(prod_agg, left_on=prod_id, right_on=prod_id, how="left")

    # inventory stock merge
    if inventory is not None:
        inv = inventory.copy()
        inv_prod = _pick_first(inv, ["sku", prod_id, "product_id", "prod_id"])
        stock_col = _pick_first(inv, ["stock_quantity", "stock", "inventory", "inventory_level", "qty_on_hand", "on_hand"])

        if inv_prod and stock_col and inv_prod in inv.columns and stock_col in inv.columns:
            inv[stock_col] = _to_numeric(inv[stock_col]).fillna(0)
            inv_small = inv[[inv_prod, stock_col]].rename(columns={inv_prod: prod_id, stock_col: "stock"})
            inv_small = inv_small.groupby(prod_id, as_index=False)["stock"].sum()
            prod_feat = prod_feat.merge(inv_small, on=prod_id, how="left")

    # fill numeric NaNs
    for c in ["times_purchased", "total_quantity_sold", "total_revenue", "avg_order_value_per_order", "unique_customers", "quantity_std", "stock"]:
        if c in prod_feat.columns:
            prod_feat[c] = _to_numeric(prod_feat[c]).fillna(0)

    return cust_feat, prod_feat, tx_feat


# ----------------------------
# CLI
# ----------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Feature Engineering: read ALL cleaned CSVs, detect relationships, output only 3 entity feature files"
    )
    parser.add_argument("--input_dir", required=True, help="Folder containing cleaned CSV files")
    parser.add_argument("--output_dir", required=True, help="Folder to write feature CSV files")
    parser.add_argument("--reports_dir", required=True, help="Folder to write feature_report.json")
    parser.add_argument("--ontology_path", required=False, default=None, help="Optional ontology YAML path (accepted but not required)")
    args = parser.parse_args()

    input_dir = Path(args.input_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    reports_dir = Path(args.reports_dir).resolve()

    output_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    tables = load_cleaned_tables(input_dir)
    cust_feat, prod_feat, tx_feat = build_features_from_all_tables(tables)

    out_files = {
        "customers_features.csv": cust_feat,
        "products_features.csv": prod_feat,
        "transactions_features.csv": tx_feat,
    }

    written = []
    for name, df in out_files.items():
        out_path = output_dir / name
        df.to_csv(out_path, index=False)
        written.append(str(out_path))

    report = {
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "written": written,
        "loaded_tables": sorted(list(tables.keys())),
        "rows": {k: int(v.shape[0]) for k, v in out_files.items()},
        "cols": {k: int(v.shape[1]) for k, v in out_files.items()},
        "note": "Reads ALL cleaned CSVs, uses joins via transactions<->customers/products, and enriches with sessions + events + web_analytics + inventory when present.",
        "ontology_path": args.ontology_path,
    }

    report_path = reports_dir / "feature_report.json"
    report_path.write_text(json.dumps(report, indent=2))

    print(" Feature engineering done.")
    print(" Loaded tables:", sorted(list(tables.keys())))
    print("Wrote:", written)
    print(" Report:", str(report_path))


if __name__ == "__main__":
    main()
