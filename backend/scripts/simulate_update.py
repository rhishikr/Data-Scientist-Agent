"""
Dataset Update Simulator
=========================
Simulates time passing in a retail store by appending new data to existing
CSVs in data/raw/. Each invocation adds ~1 week of realistic new data.

Supports 8 dynamic business scenarios that adjust simulation parameters:
  organic-growth, profit, loss, seasonal-spike, stockout-crisis,
  marketing-blitz, churn-wave, new-product-launch

Usage:
    cd backend
    python scripts/simulate_update.py                              # 7 days, organic-growth
    python scripts/simulate_update.py --days 14 --scenario loss
    python scripts/simulate_update.py --days 30 --scenario seasonal-spike
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
    LOCATIONS, DEVICES, CATEGORIES, PAYMENT_METHODS, ORDER_STATUSES,
    CURRENCIES, SUPPLIERS, WAREHOUSES, CHANNELS, CAMPAIGN_TYPES,
    PAGE_TYPES, ACTIONS, REFERRAL_SOURCES, TRAFFIC_SOURCES,
    GENDERS, LOYALTY_STATUSES, PAYMENT_STATUSES, EVENT_TYPES,
    LANDING_PAGES, CAMPAIGN_NAME_TEMPLATES,
    FIRST_NAMES, LAST_NAMES, EMAIL_DOMAINS,
    DIRTY_RATE, _make_email,
    maybe_null, maybe_dirty_str, random_date,
)

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

# ---------------------------------------------------------------------------
# Scenario Definitions
# ---------------------------------------------------------------------------

SCENARIOS = {
    "organic-growth": {
        "description": "Steady healthy growth across all metrics",
        "conversion_rate": 0.20,
        "volume_mult": 1.0,
        "discount_mult": 1.0,
        "return_rate": 0.10,
        "cart_abandon_rate": 0.55,
        "new_customers_mult": 1.0,
        "marketing_spend_mult": 1.0,
        "aov_mult": 1.0,
        "session_duration_mult": 1.0,
        "refund_rate": 0.08,
        "cancel_rate": 0.10,
        "paid_traffic_weight": 0.3,
    },
    "profit": {
        "description": "Business thriving: high conversions, low returns, strong margins",
        "conversion_rate": 0.30,
        "volume_mult": 1.3,
        "discount_mult": 0.5,
        "return_rate": 0.05,
        "cart_abandon_rate": 0.35,
        "new_customers_mult": 1.2,
        "marketing_spend_mult": 0.8,
        "aov_mult": 1.4,
        "session_duration_mult": 1.3,
        "refund_rate": 0.03,
        "cancel_rate": 0.05,
        "paid_traffic_weight": 0.3,
    },
    "loss": {
        "description": "Business struggling: low conversions, high returns and cancellations",
        "conversion_rate": 0.05,
        "volume_mult": 0.4,
        "discount_mult": 2.0,
        "return_rate": 0.30,
        "cart_abandon_rate": 0.80,
        "new_customers_mult": 0.5,
        "marketing_spend_mult": 1.5,
        "aov_mult": 0.6,
        "session_duration_mult": 0.6,
        "refund_rate": 0.25,
        "cancel_rate": 0.30,
        "paid_traffic_weight": 0.4,
    },
    "seasonal-spike": {
        "description": "Holiday/flash sale: 4x volume, heavy discounts, inventory drain",
        "conversion_rate": 0.25,
        "volume_mult": 4.0,
        "discount_mult": 2.5,
        "return_rate": 0.12,
        "cart_abandon_rate": 0.45,
        "new_customers_mult": 3.0,
        "marketing_spend_mult": 3.0,
        "aov_mult": 1.2,
        "session_duration_mult": 1.1,
        "refund_rate": 0.10,
        "cancel_rate": 0.08,
        "paid_traffic_weight": 0.5,
    },
    "stockout-crisis": {
        "description": "Supply chain problems: inventory drains, many cancelled orders",
        "conversion_rate": 0.10,
        "volume_mult": 0.6,
        "discount_mult": 0.5,
        "return_rate": 0.08,
        "cart_abandon_rate": 0.70,
        "new_customers_mult": 0.7,
        "marketing_spend_mult": 0.5,
        "aov_mult": 0.9,
        "session_duration_mult": 0.8,
        "refund_rate": 0.05,
        "cancel_rate": 0.40,
        "paid_traffic_weight": 0.2,
    },
    "marketing-blitz": {
        "description": "Aggressive ad campaign: 5x spend, flood of paid traffic",
        "conversion_rate": 0.18,
        "volume_mult": 2.0,
        "discount_mult": 1.5,
        "return_rate": 0.10,
        "cart_abandon_rate": 0.50,
        "new_customers_mult": 2.5,
        "marketing_spend_mult": 5.0,
        "aov_mult": 1.0,
        "session_duration_mult": 0.9,
        "refund_rate": 0.08,
        "cancel_rate": 0.10,
        "paid_traffic_weight": 0.80,
    },
    "churn-wave": {
        "description": "Customer exodus: fewer returning customers, low engagement",
        "conversion_rate": 0.08,
        "volume_mult": 0.5,
        "discount_mult": 1.0,
        "return_rate": 0.15,
        "cart_abandon_rate": 0.75,
        "new_customers_mult": 0.3,
        "marketing_spend_mult": 1.0,
        "aov_mult": 0.7,
        "session_duration_mult": 0.4,
        "refund_rate": 0.12,
        "cancel_rate": 0.15,
        "paid_traffic_weight": 0.1,
    },
    "new-product-launch": {
        "description": "New products: concentrated demand on newest SKUs",
        "conversion_rate": 0.22,
        "volume_mult": 1.5,
        "discount_mult": 1.2,
        "return_rate": 0.12,
        "cart_abandon_rate": 0.50,
        "new_customers_mult": 1.5,
        "marketing_spend_mult": 2.0,
        "aov_mult": 1.3,
        "session_duration_mult": 1.2,
        "refund_rate": 0.08,
        "cancel_rate": 0.10,
        "paid_traffic_weight": 0.5,
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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


def _evt_offset(lo, hi, duration):
    """Safe random offset clamped to session duration."""
    lo = min(lo, duration)
    hi = min(hi, duration)
    if lo >= hi:
        return lo
    return random.randint(lo, hi)


# ---------------------------------------------------------------------------
# Simulators
# ---------------------------------------------------------------------------

def simulate_customers(days: int, sc: dict) -> pd.DataFrame:
    existing = _read_csv("customers.csv")
    next_id = _max_id(existing["customer_id"], "CUST") + 1
    base_count = random.randint(max(1, days // 2), days * 2)
    n_new = max(1, int(base_count * sc["new_customers_mult"]))
    latest = _latest_date(existing["acquisition_date"])

    rows = []
    for i in range(n_new):
        cid = f"CUST{next_id + i}"
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        name = f"{first} {last}"
        rows.append({
            "customer_id": maybe_null(maybe_dirty_str(cid, 0.02)),
            "name": maybe_null(maybe_dirty_str(name, 0.03)),
            "email": maybe_null(_make_email(name)),
            "age": maybe_null(random.randint(18, 70)),
            "gender": maybe_null(maybe_dirty_str(
                random.choices(GENDERS, weights=[40, 40, 10, 10])[0]
            )),
            "location": maybe_null(maybe_dirty_str(random.choice(LOCATIONS))),
            "device_type": maybe_null(maybe_dirty_str(random.choice(DEVICES))),
            "loyalty_status": maybe_null(maybe_dirty_str(
                random.choices(LOYALTY_STATUSES, weights=[40, 30, 20, 10])[0]
            )),
            "total_spend": 0.0,
            "acquisition_date": maybe_null(
                random_date(latest, latest + timedelta(days=days)).strftime(
                    "%Y-%m-%d %H:%M:%S.%f"
                )
            ),
        })
    return pd.DataFrame(rows)


def simulate_marketing(days: int, sc: dict) -> pd.DataFrame:
    existing = _read_csv("marketing.csv")
    next_id = _max_id(existing["campaign_id"], "CAMP") + 1
    latest = _latest_date(existing["start_date"])
    n_new = max(1, int(random.randint(1, max(2, days // 3)) * sc["marketing_spend_mult"]))

    year = (latest + timedelta(days=days)).year
    campaign_names = [t.format(year=year) for t in CAMPAIGN_NAME_TEMPLATES]

    # For seasonal-spike, prefer flash_sale campaigns
    if sc is SCENARIOS.get("seasonal-spike"):
        camp_type_weights = [10, 10, 10, 10, 60]  # heavy flash_sale
    else:
        camp_type_weights = [20, 20, 20, 20, 20]

    rows = []
    for i in range(n_new):
        cid = f"CAMP{next_id + i}"
        start = random_date(latest, latest + timedelta(days=days))
        end = start + timedelta(days=random.randint(14, 90))
        base_spend = round(random.uniform(50, 5000), 2)
        spend = round(base_spend * sc["marketing_spend_mult"], 2)
        impressions = int(random.randint(5000, 100000) * sc["marketing_spend_mult"])
        clicks = int(impressions * random.uniform(0.01, 0.06))
        conversions = int(clicks * random.uniform(0.02, 0.15))
        c_name = random.choice(campaign_names)

        rows.append({
            "campaign_id": maybe_null(maybe_dirty_str(cid, 0.02)),
            "channel": maybe_null(maybe_dirty_str(random.choice(CHANNELS))),
            "campaign_type": maybe_null(maybe_dirty_str(
                random.choices(CAMPAIGN_TYPES, weights=camp_type_weights)[0]
            )),
            "campaign_name": maybe_null(maybe_dirty_str(c_name, 0.03)),
            "start_date": maybe_null(start.strftime("%Y-%m-%d")),
            "end_date": maybe_null(end.strftime("%Y-%m-%d")),
            "ad_spend": maybe_null(spend),
            "impressions": maybe_null(float(impressions)),
            "clicks": maybe_null(float(clicks)),
            "conversions": maybe_null(float(conversions)),
        })
    return pd.DataFrame(rows)


def simulate_sessions(days: int, sc: dict) -> pd.DataFrame:
    customers = _read_csv("customers.csv")
    marketing = _read_csv("marketing.csv")
    existing_sessions = _read_csv("sessions.csv")

    valid_cids = customers["customer_id"].dropna().astype(str).tolist()
    next_id = _max_id(existing_sessions["session_id"], "SESS") + 1
    latest = _latest_date(existing_sessions["session_start"])

    # Build active campaign lookup
    active_campaigns = []
    for _, row in marketing.iterrows():
        try:
            c_name = row.get("campaign_name")
            channel = row.get("channel")
            sd = row.get("start_date")
            ed = row.get("end_date")
            if pd.notna(c_name) and pd.notna(sd) and pd.notna(ed):
                active_campaigns.append((
                    str(channel), str(c_name),
                    datetime.strptime(str(sd), "%Y-%m-%d"),
                    datetime.strptime(str(ed), "%Y-%m-%d"),
                ))
        except (ValueError, TypeError):
            continue

    base_sessions = random.randint(days * 10, days * 30)
    n_new = max(5, int(base_sessions * sc["volume_mult"]))

    # Traffic source weights based on scenario
    paid_w = sc["paid_traffic_weight"]
    organic_w = (1 - paid_w) / 3
    source_weights = {
        "organic_search": organic_w,
        "paid_search": paid_w * 0.4,
        "email": paid_w * 0.25,
        "social": paid_w * 0.25,
        "direct": organic_w,
        "referral": organic_w * 0.5 + paid_w * 0.1,
    }
    sources = list(source_weights.keys())
    weights = [source_weights[s] for s in sources]

    rows = []
    for i in range(n_new):
        sid = f"SESS{next_id + i}"
        cid = random.choice(valid_cids)
        sess_start = random_date(latest, latest + timedelta(days=days))
        base_duration = random.randint(30, 1800)
        duration_sec = max(10, int(base_duration * sc["session_duration_mult"]))
        sess_end = sess_start + timedelta(seconds=duration_sec)
        pages = max(1, int(random.randint(1, 20) * sc["session_duration_mult"]))
        device = random.choice(DEVICES)
        landing = random.choice(LANDING_PAGES)
        source = random.choices(sources, weights=weights)[0]

        # Campaign attribution
        camp_name = None
        if source in ("paid_search", "email", "social"):
            matching = [
                c for c in active_campaigns
                if c[2] <= sess_start <= c[3]
            ]
            if matching:
                chosen = random.choice(matching)
                camp_name = chosen[1]

        converted = random.random() < sc["conversion_rate"]
        revenue = round(random.uniform(15, 500) * sc["aov_mult"], 2) if converted else 0.0

        rows.append({
            "session_id": maybe_null(maybe_dirty_str(sid, 0.02)),
            "customer_id": maybe_null(maybe_dirty_str(str(cid), 0.03)),
            "session_start": maybe_null(sess_start.strftime("%Y-%m-%d %H:%M:%S.%f")),
            "session_end": maybe_null(sess_end.strftime("%Y-%m-%d %H:%M:%S.%f")),
            "session_duration_sec": maybe_null(float(duration_sec)),
            "pages_viewed": maybe_null(float(pages)),
            "device_type": maybe_null(maybe_dirty_str(device)),
            "landing_page": maybe_null(maybe_dirty_str(landing)),
            "traffic_source": maybe_null(maybe_dirty_str(source)),
            "campaign_name": maybe_null(maybe_dirty_str(camp_name, 0.03)) if camp_name else np.nan,
            "converted_flag": maybe_null(converted),
            "revenue": maybe_null(revenue),
        })
    return pd.DataFrame(rows)


def simulate_events(new_sessions: pd.DataFrame, sc: dict) -> pd.DataFrame:
    products = _read_csv("products.csv")
    existing_events = _read_csv("events.csv")

    valid_skus = products["sku"].dropna().astype(str).tolist()
    sku_prices = dict(zip(
        products["sku"].dropna().astype(str),
        products["retail_price"].dropna()
    ))

    # For new-product-launch: bias toward last 10 SKUs
    is_launch = sc is SCENARIOS.get("new-product-launch")
    launch_skus = valid_skus[-10:] if is_launch and len(valid_skus) >= 10 else []

    event_counter = _max_id(existing_events["event_id"], "EVT") + 1

    rows = []
    for _, sess in new_sessions.iterrows():
        sid = sess.get("session_id")
        cid = sess.get("customer_id")
        converted = sess.get("converted_flag")
        sess_start_str = sess.get("session_start")

        if pd.isna(sid) or pd.isna(sess_start_str):
            continue

        try:
            sess_start = datetime.strptime(str(sess_start_str).strip(), "%Y-%m-%d %H:%M:%S.%f")
        except (ValueError, TypeError):
            continue

        duration = sess.get("session_duration_sec")
        if pd.isna(duration):
            duration = 300
        duration = int(float(duration))

        def _pick_sku():
            if is_launch and launch_skus and random.random() < 0.60:
                return random.choice(launch_skus)
            return random.choice(valid_skus)

        # page_view (every session)
        eid = f"EVT{event_counter}"
        event_counter += 1
        evt_time = sess_start + timedelta(seconds=_evt_offset(0, 10, duration))
        rows.append({
            "event_id": maybe_null(maybe_dirty_str(eid, 0.02)),
            "session_id": maybe_null(maybe_dirty_str(str(sid), 0.03)),
            "customer_id": maybe_null(maybe_dirty_str(str(cid), 0.03)) if pd.notna(cid) else np.nan,
            "event_type": maybe_null(maybe_dirty_str("page_view")),
            "event_datetime": maybe_null(evt_time.strftime("%Y-%m-%d %H:%M:%S.%f")),
            "sku": np.nan,
            "quantity": np.nan,
            "unit_price": np.nan,
        })

        # product_view (~70%)
        if random.random() < 0.70:
            eid = f"EVT{event_counter}"
            event_counter += 1
            sku = _pick_sku()
            price = sku_prices.get(sku, round(random.uniform(10, 300), 2))
            if isinstance(price, float) and np.isnan(price):
                price = round(random.uniform(10, 300), 2)
            evt_time = sess_start + timedelta(seconds=_evt_offset(10, 60, duration))
            rows.append({
                "event_id": maybe_null(maybe_dirty_str(eid, 0.02)),
                "session_id": maybe_null(maybe_dirty_str(str(sid), 0.03)),
                "customer_id": maybe_null(maybe_dirty_str(str(cid), 0.03)) if pd.notna(cid) else np.nan,
                "event_type": maybe_null(maybe_dirty_str("product_view")),
                "event_datetime": maybe_null(evt_time.strftime("%Y-%m-%d %H:%M:%S.%f")),
                "sku": maybe_null(maybe_dirty_str(str(sku), 0.03)),
                "quantity": np.nan,
                "unit_price": maybe_null(price),
            })

            # add_to_cart (~30%)
            atc_rate = 1 - sc["cart_abandon_rate"]  # lower abandon = more add-to-cart
            if random.random() < 0.43:
                eid = f"EVT{event_counter}"
                event_counter += 1
                qty = random.randint(1, 4)
                evt_time = sess_start + timedelta(seconds=_evt_offset(60, 180, duration))
                rows.append({
                    "event_id": maybe_null(maybe_dirty_str(eid, 0.02)),
                    "session_id": maybe_null(maybe_dirty_str(str(sid), 0.03)),
                    "customer_id": maybe_null(maybe_dirty_str(str(cid), 0.03)) if pd.notna(cid) else np.nan,
                    "event_type": maybe_null(maybe_dirty_str("add_to_cart")),
                    "event_datetime": maybe_null(evt_time.strftime("%Y-%m-%d %H:%M:%S.%f")),
                    "sku": maybe_null(maybe_dirty_str(str(sku), 0.03)),
                    "quantity": maybe_null(float(qty)),
                    "unit_price": maybe_null(price),
                })

                # begin_checkout (~15%)
                if random.random() < 0.50:
                    eid = f"EVT{event_counter}"
                    event_counter += 1
                    evt_time = sess_start + timedelta(seconds=_evt_offset(180, 300, duration))
                    rows.append({
                        "event_id": maybe_null(maybe_dirty_str(eid, 0.02)),
                        "session_id": maybe_null(maybe_dirty_str(str(sid), 0.03)),
                        "customer_id": maybe_null(maybe_dirty_str(str(cid), 0.03)) if pd.notna(cid) else np.nan,
                        "event_type": maybe_null(maybe_dirty_str("begin_checkout")),
                        "event_datetime": maybe_null(evt_time.strftime("%Y-%m-%d %H:%M:%S.%f")),
                        "sku": maybe_null(maybe_dirty_str(str(sku), 0.03)),
                        "quantity": maybe_null(float(qty)),
                        "unit_price": maybe_null(price),
                    })

                    # purchase (only converted)
                    if converted is True or (isinstance(converted, (bool, np.bool_)) and converted):
                        eid = f"EVT{event_counter}"
                        event_counter += 1
                        evt_time = sess_start + timedelta(seconds=_evt_offset(300, 600, duration))
                        rows.append({
                            "event_id": maybe_null(maybe_dirty_str(eid, 0.02)),
                            "session_id": maybe_null(maybe_dirty_str(str(sid), 0.03)),
                            "customer_id": maybe_null(maybe_dirty_str(str(cid), 0.03)) if pd.notna(cid) else np.nan,
                            "event_type": maybe_null(maybe_dirty_str("purchase")),
                            "event_datetime": maybe_null(evt_time.strftime("%Y-%m-%d %H:%M:%S.%f")),
                            "sku": maybe_null(maybe_dirty_str(str(sku), 0.03)),
                            "quantity": maybe_null(float(qty)),
                            "unit_price": maybe_null(price),
                        })

    return pd.DataFrame(rows)


def simulate_web_analytics(days: int, sc: dict) -> pd.DataFrame:
    sessions = _read_csv("sessions.csv")
    customers = _read_csv("customers.csv")
    existing = _read_csv("web_analytics.csv")

    valid_sids = sessions["session_id"].dropna().astype(str).tolist()
    valid_cids = customers["customer_id"].dropna().astype(str).tolist()
    next_id = _max_id(existing["event_id"], "WEB") + 1
    latest = _latest_date(existing["event_datetime"])
    n_new = max(5, int(random.randint(days * 15, days * 40) * sc["volume_mult"]))

    rows = []
    for i in range(n_new):
        eid = f"WEB{next_id + i}"
        sid = random.choice(valid_sids)
        cid = random.choice(valid_cids)
        action = random.choice(ACTIONS)
        add_to_cart = action == "add_to_cart"

        rows.append({
            "event_id": maybe_null(maybe_dirty_str(eid, 0.02)),
            "session_id": maybe_null(maybe_dirty_str(str(sid), 0.03)),
            "customer_id": maybe_dirty_str(str(cid), 0.03),
            "event_datetime": maybe_null(
                random_date(latest, latest + timedelta(days=days)).strftime(
                    "%Y-%m-%d %H:%M:%S.%f"
                )
            ),
            "page_type": maybe_null(maybe_dirty_str(random.choice(PAGE_TYPES))),
            "action": maybe_null(maybe_dirty_str(action)),
            "add_to_cart": maybe_null(add_to_cart),
            "referral_source": maybe_null(maybe_dirty_str(random.choice(REFERRAL_SOURCES))),
        })
    return pd.DataFrame(rows)


def simulate_transactions(new_sessions: pd.DataFrame, sc: dict):
    """Generate transactions from converted sessions. Returns (df, txn_session_map)."""
    products = _read_csv("products.csv")
    existing = _read_csv("transactions.csv")

    valid_skus = products["sku"].dropna().astype(str).tolist()
    sku_prices = dict(zip(
        products["sku"].dropna().astype(str),
        products["retail_price"].dropna()
    ))

    next_id = _max_id(existing["order_id"], "ORD") + 1
    order_counter = next_id

    converted_sessions = new_sessions[new_sessions["converted_flag"] == True]  # noqa: E712
    txn_session_map = []

    rows = []
    for _, sess in converted_sessions.iterrows():
        sid = sess.get("session_id")
        cid = sess.get("customer_id")
        sess_start_str = sess.get("session_start")

        if pd.isna(sid) or pd.isna(cid):
            continue

        try:
            if pd.notna(sess_start_str):
                order_dt = datetime.strptime(str(sess_start_str).strip(), "%Y-%m-%d %H:%M:%S.%f")
            else:
                order_dt = datetime.now()
        except (ValueError, TypeError):
            order_dt = datetime.now()

        n_items = random.randint(1, 5)
        for _ in range(n_items):
            oid = f"ORD{order_counter}"
            order_counter += 1
            sku = random.choice(valid_skus)
            qty = random.randint(1, 5)
            price = sku_prices.get(sku, round(random.uniform(10, 500), 2))
            if isinstance(price, float) and np.isnan(price):
                price = round(random.uniform(10, 500), 2)
            price = round(price * sc["aov_mult"], 2)
            total = round(qty * price, 2)

            # Discount influenced by scenario
            base_discount_rates = [0, 0, 0, 0.05, 0.10, 0.15, 0.20]
            discount_rate = random.choice(base_discount_rates) * sc["discount_mult"]
            discount_amt = round(total * min(discount_rate, 0.50), 2)

            # Order status influenced by scenario
            if random.random() < sc["cancel_rate"]:
                status = "cancelled"
            elif random.random() < sc["return_rate"]:
                status = "returned"
            else:
                status = random.choices(
                    ["delivered", "shipped", "processing"],
                    weights=[65, 20, 15]
                )[0]

            rows.append({
                "order_id": maybe_null(maybe_dirty_str(oid, 0.02)),
                "customer_id": maybe_null(maybe_dirty_str(str(cid), 0.03)),
                "sku": maybe_null(maybe_dirty_str(str(sku), 0.03)),
                "quantity": maybe_null(float(qty)),
                "unit_price": maybe_null(price),
                "total_amount": maybe_null(total),
                "discount_amount": maybe_null(discount_amt),
                "order_status": maybe_null(maybe_dirty_str(status)),
                "order_datetime": maybe_null(order_dt.strftime("%Y-%m-%d %H:%M:%S.%f")),
            })
            txn_session_map.append({"order_id": oid, "session_id": str(sid)})

    return pd.DataFrame(rows), txn_session_map


def simulate_payments(new_transactions: pd.DataFrame, sc: dict) -> pd.DataFrame:
    rows = []
    for _, txn in new_transactions.iterrows():
        oid = txn.get("order_id", "")

        # Payment status influenced by scenario
        if random.random() < sc["refund_rate"]:
            p_status = "refunded"
        elif random.random() < 0.05:
            p_status = "failed"
        elif random.random() < 0.08:
            p_status = "pending"
        else:
            p_status = "completed"

        rows.append({
            "order_id": maybe_null(maybe_dirty_str(str(oid), 0.03)) if pd.notna(oid) else np.nan,
            "payment_method": maybe_null(maybe_dirty_str(random.choice(PAYMENT_METHODS))),
            "payment_status": maybe_null(maybe_dirty_str(p_status)),
            "transaction_fee": maybe_null(round(random.uniform(0.5, 25), 2)),
            "currency": maybe_null(maybe_dirty_str(random.choice(CURRENCIES))),
        })
    return pd.DataFrame(rows)


def simulate_inventory_changes(new_transactions: pd.DataFrame, sc: dict) -> None:
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
            current = inventory.at[idx, "stock_quantity"]
            if not np.isnan(current):
                inventory.at[idx, "stock_quantity"] = max(0, current - qty)

    # Stockout-crisis: drain 30% of SKUs to near-zero
    if sc is SCENARIOS.get("stockout-crisis"):
        drain_mask = np.random.random(len(inventory)) < 0.30
        inventory.loc[drain_mask, "stock_quantity"] = inventory.loc[
            drain_mask, "stock_quantity"
        ].apply(lambda x: max(0, random.randint(0, 3)) if not np.isnan(x) else x)
    else:
        # Normal restocks (10% of products)
        restock_mask = np.random.random(len(inventory)) < 0.1
        inventory.loc[restock_mask, "stock_quantity"] = inventory.loc[
            restock_mask, "stock_quantity"
        ].apply(lambda x: x + random.randint(50, 200) if not np.isnan(x) else x)

    inventory.to_csv(inv_path, index=False)


def simulate_campaign_performance(new_marketing: pd.DataFrame, days: int, sc: dict) -> pd.DataFrame:
    rows = []
    for _, camp in new_marketing.iterrows():
        camp_id = camp.get("campaign_id")
        channel = camp.get("channel")
        c_name = camp.get("campaign_name")
        sd_str = camp.get("start_date")
        ed_str = camp.get("end_date")
        total_impressions = camp.get("impressions", 0)
        total_clicks = camp.get("clicks", 0)
        total_spend = camp.get("ad_spend", 0)

        if pd.isna(sd_str) or pd.isna(ed_str) or pd.isna(camp_id):
            continue

        try:
            sd = datetime.strptime(str(sd_str), "%Y-%m-%d")
            ed = datetime.strptime(str(ed_str), "%Y-%m-%d")
        except (ValueError, TypeError):
            continue

        # Only generate rows for the simulated days window
        n_days = min((ed - sd).days, days)
        n_days = max(n_days, 1)

        for day_offset in range(n_days):
            date = sd + timedelta(days=day_offset)
            noise = random.uniform(0.5, 1.5)
            daily_imp = int((float(total_impressions) / max((ed - sd).days, 1)) * noise) if pd.notna(total_impressions) else 0
            daily_clicks = int((float(total_clicks) / max((ed - sd).days, 1)) * noise) if pd.notna(total_clicks) else 0
            daily_spend = round((float(total_spend) / max((ed - sd).days, 1)) * noise, 2) if pd.notna(total_spend) else 0

            daily_sessions = random.randint(0, int(15 * sc["volume_mult"]))
            daily_orders = random.randint(0, max(1, int(daily_sessions * sc["conversion_rate"])))
            daily_revenue = round(daily_orders * random.uniform(20, 200) * sc["aov_mult"], 2)

            rows.append({
                "date": maybe_null(date.strftime("%Y-%m-%d")),
                "campaign_id": maybe_null(maybe_dirty_str(str(camp_id), 0.02)),
                "channel": maybe_null(maybe_dirty_str(str(channel))) if pd.notna(channel) else np.nan,
                "campaign_name": maybe_null(maybe_dirty_str(str(c_name), 0.03)) if pd.notna(c_name) else np.nan,
                "impressions": maybe_null(float(daily_imp)),
                "clicks": maybe_null(float(daily_clicks)),
                "spend": maybe_null(daily_spend),
                "sessions": maybe_null(float(daily_sessions)),
                "orders": maybe_null(float(daily_orders)),
                "attributed_revenue": maybe_null(daily_revenue),
            })

    return pd.DataFrame(rows)


def simulate_funnel_summary(days: int, sc: dict) -> pd.DataFrame:
    existing = _read_csv("funnel_summary.csv")
    latest = _latest_date(existing["date"])

    rows = []
    for day_offset in range(1, days + 1):
        date = latest + timedelta(days=day_offset)
        date_str = date.strftime("%Y-%m-%d")

        daily_sessions = max(1, int(random.randint(20, 80) * sc["volume_mult"]))
        product_views = int(daily_sessions * random.uniform(0.5, 0.8))
        add_to_cart = int(product_views * random.uniform(0.2, 0.4) * (1 - sc["cart_abandon_rate"] + 0.45))
        checkout_started = int(add_to_cart * random.uniform(0.3, 0.6))
        purchases = int(checkout_started * sc["conversion_rate"] / 0.20 * random.uniform(0.4, 0.7))

        conv_rate = round(purchases / daily_sessions, 4) if daily_sessions > 0 else 0
        cart_abandon = round(1 - (purchases / add_to_cart), 4) if add_to_cart > 0 else 0

        rows.append({
            "date": maybe_null(date_str),
            "sessions": maybe_null(float(daily_sessions)),
            "product_views": maybe_null(float(product_views)),
            "add_to_cart": maybe_null(float(add_to_cart)),
            "checkout_started": maybe_null(float(checkout_started)),
            "purchases": maybe_null(float(purchases)),
            "conversion_rate": maybe_null(conv_rate),
            "cart_abandonment_rate": maybe_null(cart_abandon),
        })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Simulate retail dataset updates with dynamic scenarios")
    parser.add_argument("--days", type=int, default=7, help="Number of days to simulate (default: 7)")
    parser.add_argument(
        "--scenario", type=str, default="organic-growth",
        choices=list(SCENARIOS.keys()),
        help="Business scenario to simulate (default: organic-growth)"
    )
    args = parser.parse_args()
    days = args.days
    sc = SCENARIOS[args.scenario]

    print(f"Simulating {days} days | Scenario: {args.scenario}")
    print(f"  {sc['description']}")
    print(f"  Conversion: {sc['conversion_rate']:.0%} | Volume: {sc['volume_mult']}x | AOV: {sc['aov_mult']}x | Marketing: {sc['marketing_spend_mult']}x")
    print()

    # 1. New customers
    new_customers = simulate_customers(days, sc)
    _append_csv("customers.csv", new_customers)
    print(f"  + {len(new_customers)} new customers")

    # 2. New marketing campaigns
    new_marketing = simulate_marketing(days, sc)
    _append_csv("marketing.csv", new_marketing)
    print(f"  + {len(new_marketing)} new campaigns")

    # 3. New sessions
    new_sessions = simulate_sessions(days, sc)
    _append_csv("sessions.csv", new_sessions)
    converted_count = new_sessions["converted_flag"].sum() if "converted_flag" in new_sessions else 0
    print(f"  + {len(new_sessions)} new sessions ({int(converted_count)} converted)")

    # 4. New events (from sessions)
    new_events = simulate_events(new_sessions, sc)
    _append_csv("events.csv", new_events)
    print(f"  + {len(new_events)} new events")

    # 5. Web analytics
    new_web = simulate_web_analytics(days, sc)
    _append_csv("web_analytics.csv", new_web)
    print(f"  + {len(new_web)} new web analytics events")

    # 6. Transactions (from converted sessions)
    new_transactions, txn_session_map = simulate_transactions(new_sessions, sc)
    _append_csv("transactions.csv", new_transactions)
    print(f"  + {len(new_transactions)} new transactions")

    # 7. Transactions with session
    if not new_transactions.empty:
        txn_with_sess = new_transactions.copy()
        txn_session_df = pd.DataFrame(txn_session_map)
        if not txn_session_df.empty:
            oid_to_sid = dict(zip(txn_session_df["order_id"], txn_session_df["session_id"]))
            txn_with_sess["session_id"] = txn_with_sess["order_id"].map(
                lambda x: maybe_null(maybe_dirty_str(oid_to_sid.get(str(x).strip(), ""), 0.03))
                if pd.notna(x) else np.nan
            )
        else:
            txn_with_sess["session_id"] = np.nan
        _append_csv("transactions_with_session.csv", txn_with_sess)
        print(f"  + {len(txn_with_sess)} new transactions_with_session rows")

    # 8. Payments
    new_payments = simulate_payments(new_transactions, sc)
    _append_csv("payments.csv", new_payments)
    print(f"  + {len(new_payments)} new payments")

    # 9. Inventory adjustments
    if not new_transactions.empty:
        simulate_inventory_changes(new_transactions, sc)
    scenario_note = " (STOCKOUT DRAIN APPLIED)" if args.scenario == "stockout-crisis" else ""
    print(f"  ~ Inventory levels updated{scenario_note}")

    # 10. Campaign performance
    new_camp_perf = simulate_campaign_performance(new_marketing, days, sc)
    _append_csv("campaign_performance.csv", new_camp_perf)
    print(f"  + {len(new_camp_perf)} new campaign_performance rows")

    # 11. Funnel summary
    new_funnel = simulate_funnel_summary(days, sc)
    _append_csv("funnel_summary.csv", new_funnel)
    print(f"  + {len(new_funnel)} new funnel_summary rows")

    print(f"\nDone! {days}-day [{args.scenario}] update applied to {RAW_DIR}")


if __name__ == "__main__":
    main()
