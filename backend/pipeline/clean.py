import pandas as pd

def clean_all(raw: dict):
    customers = raw["customers"].copy()
    tx = raw["transactions"].copy()

    # dates
    customers["account_creation_date"] = pd.to_datetime(customers["account_creation_date"], errors="coerce")
    tx["order_datetime"] = pd.to_datetime(tx["order_datetime"], errors="coerce")

    # numeric
    for c in ["avg_session_time_min", "wishlist_items_count"]:
        if c in customers.columns:
            customers[c] = pd.to_numeric(customers[c], errors="coerce")

    for c in ["quantity", "unit_price", "total_amount"]:
        if c in tx.columns:
            tx[c] = pd.to_numeric(tx[c], errors="coerce")

    # basic cleaning
    customers = customers.dropna(subset=["customer_id"])
    tx = tx.dropna(subset=["order_id", "customer_id", "order_datetime", "total_amount"])

    # fix bool-ish
    if "coupon_applied" in tx.columns:
        tx["coupon_applied"] = tx["coupon_applied"].astype(str).str.upper().map({"TRUE": True, "FALSE": False}).fillna(False)

    return {**raw, "customers": customers, "transactions": tx}
