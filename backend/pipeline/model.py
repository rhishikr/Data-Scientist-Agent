import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, accuracy_score

def _make_label(features: pd.DataFrame, end_date: pd.Timestamp, churn_days: int = 60):
    # churned if no purchase in last churn_days
    return (features["recencyDays"] >= churn_days).astype(int)

def train_churn_model(features: pd.DataFrame, end_date: pd.Timestamp):
    df = features.copy()
    df["label_churn"] = _make_label(df, end_date)

    feature_cols = [c for c in ["recencyDays", "frequency90d", "monetary90d", "avg_session_time_min", "wishlist_items_count"] if c in df.columns]
    X = df[feature_cols].fillna(0)
    y = df["label_churn"]

    # If dataset is tiny, guard
    if y.nunique() < 2 or len(df) < 50:
        return {
            "model": None,
            "feature_cols": feature_cols,
            "metrics": {"auc": None, "accuracy": None},
            "label_rule": f"churned if recencyDays >= 60",
            "type": "rule_only"
        }

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)

    model = LogisticRegression(max_iter=1000)
    model.fit(X_train, y_train)

    p = model.predict_proba(X_test)[:, 1]
    pred = (p >= 0.5).astype(int)

    return {
        "model": model,
        "feature_cols": feature_cols,
        "metrics": {
            "auc": float(roc_auc_score(y_test, p)),
            "accuracy": float(accuracy_score(y_test, pred)),
        },
        "label_rule": "churned if no purchase in last 60 days",
        "type": "logistic_regression"
    }

def score_churn(features: pd.DataFrame, model_bundle: dict):
    df = features.copy()
    model = model_bundle["model"]
    cols = model_bundle["feature_cols"]

    if model is None:
        # fallback: normalize recencyDays into 0..1 risk
        r = df["recencyDays"].clip(lower=0)
        df["churnRisk"] = (r / (r.max() if r.max() > 0 else 1)).clip(0, 1)
        return df

    X = df[cols].fillna(0)
    df["churnRisk"] = model.predict_proba(X)[:, 1].clip(0, 1)
    return df
