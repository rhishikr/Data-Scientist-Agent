"""
Synthetic Retail Data Generator
================================
Generates 7 interrelated CSV files for the Data Scientist Agent pipeline.
Includes ~5% dirty data (nulls, mixed casing, whitespace) to keep the
cleaning agent meaningful.

Usage:
    cd backend
    python scripts/generate_synthetic_data.py
"""
from __future__ import annotations

import random
import string
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
SEED = 42
random.seed(SEED)
np.random.seed(SEED)

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

N_CUSTOMERS = 500
N_PRODUCTS = 200
N_TRANSACTIONS = 5000
N_WEB_EVENTS = 10000
N_CAMPAIGNS = 100
DIRTY_RATE = 0.05  # 5% of values get dirtied

# Time range: last 12 months
END_DATE = datetime(2026, 2, 15)
START_DATE = END_DATE - timedelta(days=365)

# Reference data
LOCATIONS = [
    "New York, USA", "Los Angeles, USA", "Chicago, USA", "Houston, USA",
    "Mumbai, India", "Delhi, India", "Bangalore, India",
    "London, UK", "Berlin, Germany", "Paris, France",
    "Tokyo, Japan", "Sydney, Australia", "Toronto, Canada",
    "São Paulo, Brazil", "Dubai, UAE",
]
DEVICES = ["mobile", "desktop", "tablet"]
CATEGORIES = ["Electronics", "Clothing", "Beauty", "Sports", "Books", "Home", "Toys", "Food"]
BRANDS = ["Terra", "Helios", "Zenith", "Orion", "Nova", "Apex", "Vibe", "Pulse"]
COLORS = ["Red", "Blue", "Green", "Black", "White", "Grey", "Pink", "Yellow"]
MATERIALS = ["Cotton", "Plastic", "Metal", "Leather", "Polyester", "Wood", "Glass"]
PAYMENT_METHODS = ["credit_card", "paypal", "wallet", "bank_transfer"]
ORDER_STATUSES = ["delivered", "shipped", "processing", "cancelled", "returned"]
CURRENCIES = ["USD", "EUR", "GBP", "CAD", "INR", "AUD", "BRL", "JPY"]
SUPPLIERS = ["GlobalSupplyCo", "PrimeWholesale", "UrbanTraders", "MegaDistro", "FastShip"]
WAREHOUSES = ["WH-NY", "WH-LA", "WH-LON", "WH-TOR", "WH-MUM", "WH-SYD"]
CHANNELS = ["email", "google_ads", "facebook", "instagram", "in_app", "social"]
CAMPAIGN_TYPES = ["seasonal_sale", "new_arrival", "clearance", "loyalty", "flash_sale"]
PAGE_TYPES = ["home", "product", "category", "cart", "checkout", "search_results"]
ACTIONS = ["view_page", "add_to_cart", "remove_from_cart", "purchase", "search"]
REFERRAL_SOURCES = ["direct", "organic_search", "email", "social", "paid_ads"]
SEARCH_QUERIES = [
    "headphones", "running shoes", "winter jacket", "laptop", "skincare",
    "yoga mat", "novel", "coffee maker", "backpack", "sunglasses",
    "phone case", "water bottle", "desk lamp", "protein powder", None,
]
PROMO_CODES = ["SUMMER15", "WINTER20", "FLASH10", "LOYALTY25", "NEWUSER30", None]


# ---------------------------------------------------------------------------
# Dirty-data injection helpers
# ---------------------------------------------------------------------------

def dirty_string(val: str) -> str:
    """Randomly mess up a string value."""
    r = random.random()
    if r < 0.25:
        return f" {val.lower()} "
    elif r < 0.5:
        return val.upper()
    elif r < 0.75:
        return f" {val} "
    else:
        return val.lower()


def maybe_null(val, rate: float = DIRTY_RATE):
    """Replace a value with NaN at the given rate."""
    if random.random() < rate:
        return np.nan
    return val


def maybe_dirty_str(val: str, rate: float = DIRTY_RATE):
    """Possibly dirty a string value."""
    if val is None:
        return val
    if random.random() < rate:
        return dirty_string(val)
    return val


def random_date(start: datetime, end: datetime) -> datetime:
    delta = end - start
    random_seconds = random.randint(0, int(delta.total_seconds()))
    return start + timedelta(seconds=random_seconds)


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------

def generate_customers() -> pd.DataFrame:
    rows = []
    for i in range(N_CUSTOMERS):
        cid = f"CUST{1000 + i}"
        rows.append({
            "customer_id": maybe_null(maybe_dirty_str(cid, 0.02)),
            "name": maybe_null(maybe_dirty_str(f"Customer {i}", 0.03)),
            "location": maybe_null(maybe_dirty_str(random.choice(LOCATIONS))),
            "device_type": maybe_null(maybe_dirty_str(random.choice(DEVICES))),
            "account_creation_date": maybe_null(
                random_date(START_DATE - timedelta(days=365), END_DATE).strftime(
                    "%Y-%m-%d %H:%M:%S.%f"
                )
            ),
            "avg_session_time_min": maybe_null(round(random.uniform(0.5, 30.0), 1)),
            "wishlist_items_count": maybe_null(float(random.randint(0, 10))),
        })
    return pd.DataFrame(rows)


def generate_products() -> pd.DataFrame:
    rows = []
    for i in range(N_PRODUCTS):
        sku = f"SKU{10000 + i}"
        cost = round(random.uniform(5, 200), 2)
        retail = round(cost * random.uniform(1.3, 3.0), 2)
        discount = random.choice([0, 0, 0, 5, 10, 15, 20, 25, 30])
        rows.append({
            "sku": maybe_null(maybe_dirty_str(sku, 0.02)),
            "name": maybe_null(maybe_dirty_str(f"Product {i}", 0.03)),
            "category": maybe_null(maybe_dirty_str(random.choice(CATEGORIES))),
            "brand": maybe_null(maybe_dirty_str(random.choice(BRANDS))),
            "color": maybe_null(maybe_dirty_str(random.choice(COLORS))),
            "material": maybe_null(maybe_dirty_str(random.choice(MATERIALS))),
            "cost_price": maybe_null(cost),
            "retail_price": maybe_null(retail),
            "discount_percent": maybe_null(float(discount)),
            "average_rating": maybe_null(round(random.uniform(1.0, 5.0), 2)),
            "stock_available": maybe_null(float(random.randint(10, 500))),
        })
    return pd.DataFrame(rows)


def generate_transactions(customers: pd.DataFrame, products: pd.DataFrame) -> pd.DataFrame:
    valid_cids = customers["customer_id"].dropna().tolist()
    valid_skus = products["sku"].dropna().tolist()
    sku_prices = dict(zip(products["sku"].dropna(), products["retail_price"].dropna()))

    rows = []
    for i in range(N_TRANSACTIONS):
        oid = f"ORD{5000 + i}"
        cid = random.choice(valid_cids)
        sku = random.choice(valid_skus)
        qty = random.randint(1, 5)
        price = sku_prices.get(sku, round(random.uniform(10, 500), 2))
        if isinstance(price, float) and np.isnan(price):
            price = round(random.uniform(10, 500), 2)
        total = round(qty * price, 2)

        # Weekend boost: slightly more orders on weekends
        order_dt = random_date(START_DATE, END_DATE)
        if order_dt.weekday() >= 5:  # weekend
            if random.random() < 0.3:
                order_dt = random_date(START_DATE, END_DATE)

        rows.append({
            "order_id": maybe_null(maybe_dirty_str(oid, 0.02)),
            "customer_id": maybe_null(maybe_dirty_str(str(cid), 0.03)),
            "order_datetime": maybe_null(
                order_dt.strftime("%Y-%m-%d %H:%M:%S.%f")
            ),
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


def generate_inventory(products: pd.DataFrame) -> pd.DataFrame:
    valid_skus = products["sku"].dropna().tolist()
    rows = []
    for sku in valid_skus:
        rows.append({
            "sku": maybe_dirty_str(str(sku), 0.02),
            "warehouse_location": maybe_null(maybe_dirty_str(random.choice(WAREHOUSES))),
            "stock_level": maybe_null(float(random.randint(10, 500))),
            "reorder_threshold": maybe_null(float(random.randint(20, 80))),
            "supplier": maybe_null(maybe_dirty_str(random.choice(SUPPLIERS))),
            "avg_shipping_time_days": maybe_null(round(random.uniform(1, 14), 1)),
            "return_rate_percent": maybe_null(round(random.uniform(1, 20), 2)),
        })
    return pd.DataFrame(rows)


def generate_payments(transactions: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for i, (_, txn) in enumerate(transactions.iterrows()):
        pid = f"PAY{6000 + i}"
        refunded = random.random() < 0.08  # 8% refund rate
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


def generate_marketing() -> pd.DataFrame:
    rows = []
    for i in range(N_CAMPAIGNS):
        cid = f"CAMP{3000 + i}"
        start = random_date(START_DATE, END_DATE - timedelta(days=30))
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


def generate_web_analytics(customers: pd.DataFrame) -> pd.DataFrame:
    valid_cids = customers["customer_id"].dropna().tolist()
    rows = []
    session_counter = 100000

    for i in range(N_WEB_EVENTS):
        eid = f"EVT{200000 + i}"
        cid = random.choice(valid_cids)
        session_counter += random.choice([0, 0, 0, 1])  # some events share sessions
        sid = f"SESS{session_counter}"
        action = random.choice(ACTIONS)
        add_to_cart = action == "add_to_cart"
        abandoned = add_to_cart and random.random() < 0.4  # 40% cart abandonment

        rows.append({
            "event_id": maybe_null(maybe_dirty_str(eid, 0.02)),
            "customer_id": maybe_dirty_str(str(cid), 0.03),
            "session_id": maybe_null(maybe_dirty_str(sid, 0.02)),
            "event_datetime": maybe_null(
                random_date(START_DATE, END_DATE).strftime("%Y-%m-%d %H:%M:%S.%f")
            ),
            "page_type": maybe_null(maybe_dirty_str(random.choice(PAGE_TYPES))),
            "action": maybe_null(maybe_dirty_str(action)),
            "page_views_in_session": maybe_null(float(random.randint(1, 15))),
            "search_query": maybe_null(
                maybe_dirty_str(random.choice(SEARCH_QUERIES)) if random.random() < 0.3 else np.nan
            ),
            "referral_source": maybe_null(maybe_dirty_str(random.choice(REFERRAL_SOURCES))),
            "add_to_cart": maybe_null(add_to_cart),
            "abandoned_cart": maybe_null(abandoned),
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    # Remove old dirty files if they exist
    for f in RAW_DIR.glob("*_dirty.csv"):
        f.unlink()
        print(f"  Removed old file: {f.name}")

    print("Generating synthetic retail data...")

    print(f"  Customers ({N_CUSTOMERS} rows)...")
    customers = generate_customers()

    print(f"  Products ({N_PRODUCTS} rows)...")
    products = generate_products()

    print(f"  Transactions ({N_TRANSACTIONS} rows)...")
    transactions = generate_transactions(customers, products)

    print(f"  Inventory ({len(products)} rows)...")
    inventory = generate_inventory(products)

    print(f"  Payments ({N_TRANSACTIONS} rows)...")
    payments = generate_payments(transactions)

    print(f"  Marketing ({N_CAMPAIGNS} campaigns)...")
    marketing = generate_marketing()

    print(f"  Web Analytics ({N_WEB_EVENTS} events)...")
    web_analytics = generate_web_analytics(customers)

    # Save
    datasets = {
        "customers.csv": customers,
        "products.csv": products,
        "transactions.csv": transactions,
        "inventory.csv": inventory,
        "payments.csv": payments,
        "marketing.csv": marketing,
        "web_analytics.csv": web_analytics,
    }

    for name, df in datasets.items():
        path = RAW_DIR / name
        df.to_csv(path, index=False)
        print(f"  Saved {name} ({len(df)} rows, {len(df.columns)} cols)")

    print(f"\nDone! Files saved to {RAW_DIR}")


if __name__ == "__main__":
    main()
