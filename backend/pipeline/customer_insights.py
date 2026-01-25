import os
import pandas as pd
from datetime import datetime, timedelta

from .load import load_all
from .clean import clean_all
from .features import build_customer_features
from .tests import run_tests
from .model import train_churn_model, score_churn
from .insights import generate_insights
from .assemble import assemble_response

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

# simple in-memory cache to keep it snappy during dev
_CACHE = {}

def run_customer_insights(days: int = 30):
    # 1) Load + clean first (so we can see dataset max date)
    raw = load_all(DATA_DIR)
    clean = clean_all(raw)

    # 2) Anchor end date to the dataset, not "today"
    tx = clean["transactions"]
    data_end = pd.to_datetime(tx["order_datetime"]).max()

    if pd.isna(data_end):
        raise ValueError("No valid order_datetime found in transactions.csv")

    end = data_end.normalize()  # pandas Timestamp at midnight
    start = end - pd.Timedelta(days=days)

    cache_key = f"customer_insights:{days}:{end.date().isoformat()}"
    if cache_key in _CACHE:
        return _CACHE[cache_key]

    # 3) Features
    feats = build_customer_features(
        customers=clean["customers"],
        transactions=clean["transactions"],
        start_date=start,
        end_date=end,
    )

    # 4) Tests
    tests = run_tests(
        customers=clean["customers"],
        transactions=clean["transactions"],
        features=feats
    )

    # 5) Model + scoring
    model_bundle = train_churn_model(features=feats, end_date=end)
    scored = score_churn(features=feats, model_bundle=model_bundle)

    # 6) Insights
    insights = generate_insights(
        scored=scored,
        tests=tests,
        start_date=start.date(),
        end_date=end.date()
    )

    # 7) Assemble response
    response = assemble_response(
        scored=scored,
        tests=tests,
        insights=insights,
        model_bundle=model_bundle,
        days=days,
        end=end.date(),
    )

    _CACHE[cache_key] = response
    return response
