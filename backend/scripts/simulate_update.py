"""
Dataset Update Simulator
=========================
Simulates time passing in a retail store by appending new data to existing
CSVs in data/raw/. Each invocation adds ~1 week of realistic new data.

Usage:
    cd backend
    python scripts/simulate_update.py              # simulate 7 days
    python scripts/simulate_update.py --days 14    # simulate 14 days
"""
from __future__ import annotations

import argparse
import random
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# Reuse reference data from the generator
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from generate_synthetic_data import (
    LOCATIONS, DEVICES, CATEGORIES, BRANDS, COLORS, MATERIALS,
    PAYMENT_METHODS, ORDER_STATUSES, CURRENCIES, SUPPLIERS, WAREHOUSES,
    CHANNELS, CAMPAIGN_TYPES, PAGE_TYPES, ACTIONS, REFERRAL_SOURCES,
    SEARCH_QUERIES, PROMO_CODES, DIRTY_RATE,
    maybe_null, maybe_dirty_str, random_date,
)

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"


def _read_csv(name: str) -> pd.DataFrame:
    path = RAW_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"{path} not found. Run generate_synthetic_data.py first.")
    return pd.read_csv(path)


def _append_csv(name: str, new_rows: pd.DataFrame) -> None:
    path = RAW_DIR / name
    new_rows.to_csv(path, mode="a", header=False, index=False)


def _max_id(series: pd.Series, prefix: str) -> int:
    """Extract the max numeric suffix from an ID series like 'CUST1234'."""
    nums = series.dropna().astype(str).str.extract(r"(\d+)", expand=False)
    nums = pd.to_numeric(nums, errors="coerce").dropna()
    return int(nums.max()) if len(nums) > 0 else 0


def _latest_date(series: pd.Series) -> datetime:
    """Get the latest date from a date column."""
    dates = pd.to_datetime(series, errors="coerce").dropna()
    if len(dates) == 0:
        return datetime(2026, 2, 15)
    return dates.max().to_pydatetime()


def simulate_customers(days: int) -> pd.DataFrame:
    existing = _read_csv("customers.csv")
    next_id = _max_id(existing["customer_id"], "CUST") + 1
    n_new = random.randint(max(1, days // 2), days * 2)
    latest = _latest_date(existing["account_creation_date"])

    rows = []
    for i in range(n_new):
        cid = f"CUST{next_id + i}"
        rows.append({
            "customer_id": maybe_null(maybe_dirty_str(cid, 0.02)),
            "name": maybe_null(maybe_dirty_str(f"Customer {next_id + i}", 0.03)),
            "location": maybe_null(maybe_dirty_str(random.choice(LOCATIONS))),
            "device_type": maybe_null(maybe_dirty_str(random.choice(DEVICES))),
            "account_creation_date": maybe_null(
                random_date(latest, latest + timedelta(days=days)).strftime(
                    "%Y-%m-%d %H:%M:%S.%f"
                )
            ),
            "avg_session_time_min": maybe_null(round(random.uniform(0.5, 30.0), 1)),
            "wishlist_items_count": maybe_null(float(random.randint(0, 10))),
        })
    return pd.DataFrame(rows)


def simulate_transactions(days: int) -> pd.DataFrame:
    customers = _read_csv("customers.csv")
    products = _read_csv("products.csv")
    transactions = _read_csv("transactions.csv")

    valid_cids = customers["customer_id"].dropna().astype(str).tolist()
    valid_skus = products["sku"].dropna().astype(str).tolist()
    sku_prices = dict(zip(
        products["sku"].dropna().astype(str),
        products["retail_price"].dropna()
    ))

    next_id = _max_id(transactions["order_id"], "ORD") + 1
    latest = _latest_date(transactions["order_datetime"])
    n_new = random.randint(days * 5, days * 20)

    rows = []
    for i in range(n_new):
        oid = f"ORD{next_id + i}"
        cid = random.choice(valid_cids)
        sku = random.choice(valid_skus)
        qty = random.randint(1, 5)
        price = sku_prices.get(sku, round(random.uniform(10, 500), 2))
        if isinstance(price, float) and np.isnan(price):
            price = round(random.uniform(10, 500), 2)
        total = round(qty * price, 2)
        order_dt = random_date(latest, latest + timedelta(days=days))

        rows.append({
            "order_id": maybe_null(maybe_dirty_str(oid, 0.02)),
            "customer_id": maybe_null(maybe_dirty_str(str(cid), 0.03)),
            "order_datetime": maybe_null(order_dt.strftime("%Y-%m-%d %H:%M:%S.%f")),
            "sku": maybe_null(maybe_dirty_str(str(sku), 0.03)),
            "quantity": maybe_null(float(qty)),
            "unit_price": maybe_null(price),
            "total_amount": maybe_null(total),
            "payment_method": maybe_null(maybe_dirty_str(random.choice(PAYMENT_METHODS))),
            "order_status": maybe_null(maybe_dirty_str(
                random.choices(ORDER_STATUSES, weights=[60, 15, 10, 10, 5])[0]
            )),
            "coupon_applied": maybe_null(random.choice([True, False, False, False])),
        })
    return pd.DataFrame(rows)


def simulate_payments(new_transactions: pd.DataFrame) -> pd.DataFrame:
    existing = _read_csv("payments.csv")
    next_id = _max_id(existing["payment_id"], "PAY") + 1

    rows = []
    for i, (_, txn) in enumerate(new_transactions.iterrows()):
        pid = f"PAY{next_id + i}"
        refunded = random.random() < 0.08
        total = txn.get("total_amount", 0)
        if isinstance(total, float) and np.isnan(total):
            total = 0

        rows.append({
            "payment_id": maybe_null(maybe_dirty_str(pid, 0.02)),
            "order_id": maybe_null(maybe_dirty_str(str(txn.get("order_id", "")), 0.03)),
            "customer_id": maybe_null(maybe_dirty_str(str(txn.get("customer_id", "")), 0.03)),
            "payment_provider": maybe_null(maybe_dirty_str(
                random.choice(["visa", "mastercard", "paypal", "stripe", "amex"])
            )),
            "payment_type": maybe_null(maybe_dirty_str(
                str(txn.get("payment_method", random.choice(PAYMENT_METHODS)))
            )),
            "transaction_fee": maybe_null(round(random.uniform(1, 30), 2)),
            "currency": maybe_null(maybe_dirty_str(random.choice(CURRENCIES))),
            "exchange_rate_to_usd": maybe_null(round(random.uniform(0.5, 1.5), 4)),
            "refunded": maybe_null(refunded),
            "refund_amount": maybe_null(round(total, 2) if refunded else 0.0),
        })
    return pd.DataFrame(rows)


def simulate_inventory_changes(new_transactions: pd.DataFrame) -> None:
    """Update inventory stock levels based on new transactions (in-place update)."""
    inv_path = RAW_DIR / "inventory.csv"
    inventory = pd.read_csv(inv_path)

    # Decrement stock for sold items
    sold_qty = (
        new_transactions.dropna(subset=["sku", "quantity"])
        .groupby("sku")["quantity"]
        .sum()
    )
    for sku, qty in sold_qty.items():
        mask = inventory["sku"].astype(str).str.strip().str.upper() == str(sku).strip().upper()
        if mask.any():
            idx = inventory.loc[mask].index[0]
            current = inventory.at[idx, "stock_level"]
            if not np.isnan(current):
                inventory.at[idx, "stock_level"] = max(0, current - qty)

    # Random restocks (10% of products)
    restock_mask = np.random.random(len(inventory)) < 0.1
    inventory.loc[restock_mask, "stock_level"] = inventory.loc[
        restock_mask, "stock_level"
    ].apply(lambda x: x + random.randint(50, 200) if not np.isnan(x) else x)

    inventory.to_csv(inv_path, index=False)


def simulate_web_events(days: int) -> pd.DataFrame:
    customers = _read_csv("customers.csv")
    web = _read_csv("web_analytics.csv")

    valid_cids = customers["customer_id"].dropna().astype(str).tolist()
    next_id = _max_id(web["event_id"], "EVT") + 1
    latest = _latest_date(web["event_datetime"])
    session_counter = _max_id(web["session_id"], "SESS") + 1
    n_new = random.randint(days * 15, days * 40)

    rows = []
    for i in range(n_new):
        eid = f"EVT{next_id + i}"
        cid = random.choice(valid_cids)
        session_counter += random.choice([0, 0, 0, 1])
        sid = f"SESS{session_counter}"
        action = random.choice(ACTIONS)
        add_to_cart = action == "add_to_cart"
        abandoned = add_to_cart and random.random() < 0.4

        rows.append({
            "event_id": maybe_null(maybe_dirty_str(eid, 0.02)),
            "customer_id": maybe_dirty_str(str(cid), 0.03),
            "session_id": maybe_null(maybe_dirty_str(sid, 0.02)),
            "event_datetime": maybe_null(
                random_date(latest, latest + timedelta(days=days)).strftime(
                    "%Y-%m-%d %H:%M:%S.%f"
                )
            ),
            "page_type": maybe_null(maybe_dirty_str(random.choice(PAGE_TYPES))),
            "action": maybe_null(maybe_dirty_str(action)),
            "page_views_in_session": maybe_null(float(random.randint(1, 15))),
            "search_query": maybe_null(
                maybe_dirty_str(random.choice(SEARCH_QUERIES))
                if random.random() < 0.3 else np.nan
            ),
            "referral_source": maybe_null(maybe_dirty_str(random.choice(REFERRAL_SOURCES))),
            "add_to_cart": maybe_null(add_to_cart),
            "abandoned_cart": maybe_null(abandoned),
        })
    return pd.DataFrame(rows)


def simulate_marketing(days: int) -> pd.DataFrame:
    existing = _read_csv("marketing.csv")
    next_id = _max_id(existing["campaign_id"], "CAMP") + 1
    latest = _latest_date(existing["start_date"])
    n_new = random.randint(1, max(2, days // 3))

    rows = []
    for i in range(n_new):
        cid = f"CAMP{next_id + i}"
        start = random_date(latest, latest + timedelta(days=days))
        end = start + timedelta(days=random.randint(14, 90))
        impressions = random.randint(5000, 100000)
        clicks = int(impressions * random.uniform(0.01, 0.06))
        conversions = int(clicks * random.uniform(0.02, 0.15))
        spend = round(random.uniform(50, 5000), 2)
        revenue = round(conversions * random.uniform(20, 200), 2)

        rows.append({
            "campaign_id": maybe_null(maybe_dirty_str(cid, 0.02)),
            "channel": maybe_null(maybe_dirty_str(random.choice(CHANNELS))),
            "campaign_type": maybe_null(maybe_dirty_str(random.choice(CAMPAIGN_TYPES))),
            "start_date": maybe_null(start.strftime("%Y-%m-%d")),
            "end_date": maybe_null(end.strftime("%Y-%m-%d")),
            "promo_code": maybe_null(random.choice(PROMO_CODES)),
            "ad_spend": maybe_null(spend),
            "impressions": maybe_null(float(impressions)),
            "clicks": maybe_null(float(clicks)),
            "conversions": maybe_null(float(conversions)),
            "revenue": maybe_null(revenue),
            "ctr": maybe_null(round(clicks / impressions, 4) if impressions else 0),
            "conversion_rate": maybe_null(
                round(conversions / clicks, 4) if clicks else 0
            ),
        })
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser(description="Simulate retail dataset updates")
    parser.add_argument("--days", type=int, default=7, help="Number of days to simulate (default: 7)")
    args = parser.parse_args()
    days = args.days

    print(f"Simulating {days} days of retail activity...\n")

    # 1. New customers
    new_customers = simulate_customers(days)
    _append_csv("customers.csv", new_customers)
    print(f"  + {len(new_customers)} new customers")

    # 2. New transactions
    new_transactions = simulate_transactions(days)
    _append_csv("transactions.csv", new_transactions)
    print(f"  + {len(new_transactions)} new transactions")

    # 3. Payments for new transactions
    new_payments = simulate_payments(new_transactions)
    _append_csv("payments.csv", new_payments)
    print(f"  + {len(new_payments)} new payments")

    # 4. Inventory adjustments
    simulate_inventory_changes(new_transactions)
    print("  ~ Inventory levels updated")

    # 5. Web analytics events
    new_events = simulate_web_events(days)
    _append_csv("web_analytics.csv", new_events)
    print(f"  + {len(new_events)} new web events")

    # 6. Marketing campaigns
    new_campaigns = simulate_marketing(days)
    _append_csv("marketing.csv", new_campaigns)
    print(f"  + {len(new_campaigns)} new campaigns")

    print(f"\nDone! {days}-day update applied to {RAW_DIR}")


if __name__ == "__main__":
    main()
