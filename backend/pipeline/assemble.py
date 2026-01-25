import pandas as pd

def _delta(current: float, previous: float):
    if previous == 0:
        return None
    return (current - previous) / previous

def assemble_response(scored: pd.DataFrame, tests: list, insights: list, model_bundle: dict, days: int, end,):
    # KPIs
    active = int(scored["isActiveInWindow"].sum())
    churn_risk_customers = int((scored["churnRisk"] >= 0.7).sum())

    # "Avg customer value" = monetary per customer (simple)
    avg_value = float(scored["monetary"].mean()) if len(scored) else 0.0

    # retention proxy (MVP): share with frequency >= 2
    retention = float((scored["frequency"] >= 2).mean()) if len(scored) else 0.0

    # segments counts
    seg = scored.groupby("segment")["customer_id"].count().reset_index()
    segments = [{"name": r["segment"], "value": int(r["customer_id"])} for _, r in seg.iterrows()]

    # CLV trend (MVP): monthly average monetary for customers who ordered that month
    # Use last 6 months of "last_order" month buckets
    tmp = scored.copy()
    tmp["month"] = pd.to_datetime(tmp["last_order"]).dt.to_period("M").astype(str)
    clv = tmp.groupby("month")["monetary"].mean().reset_index().sort_values("month").tail(6)
    clvTrend = [{"month": r["month"], "value": float(r["monetary"])} for _, r in clv.iterrows()]

    # top customers
    top = scored.sort_values("monetary", ascending=False).head(12)
    topCustomers = []
    for _, r in top.iterrows():
        topCustomers.append({
            "id": str(r["customer_id"]),
            "name": str(r["name"]) if pd.notna(r.get("name")) else str(r["customer_id"]),
            "segment": r["segment"],
            "recencyDays": int(r["recencyDays"]),
            "frequency": int(r["frequency"]),
            "monetary": float(r["monetary"]),
            "churnRisk": float(r["churnRisk"]),
        })

    # model section
    model = {
        "churnModel": {
            "type": model_bundle["type"],
            "labelRule": model_bundle["label_rule"],
            "features": model_bundle["feature_cols"],
            "metrics": model_bundle["metrics"],
        }
    }

    # grounding facts for chat
    facts = [
        f"Active customers: {active}",
        f"Retention rate: {retention:.1%}",
        f"Churn-risk customers: {churn_risk_customers}",
    ]
    if model_bundle["metrics"].get("auc") is not None:
        facts.append(f"Churn model AUC: {model_bundle['metrics']['auc']:.2f}")

    return {
        "range": {"days": days, "end": str(end)},
        "kpis": {
            "activeCustomers": {"value": active, "deltaPct": None, "deltaLabel": "vs previous period"},
            "avgCustomerValue": {"value": avg_value, "deltaPct": None, "deltaLabel": "vs previous period"},
            "churnRiskCustomers": {"value": churn_risk_customers, "deltaPct": None, "deltaLabel": "needs attention"},
            "retentionRate": {"value": retention, "deltaPct": None, "deltaLabel": "vs previous period"},
        },
        "segments": segments,
        "clvTrend": clvTrend,
        "topCustomers": topCustomers,
        "model": model,
        "tests": tests,
        "insights": insights,
        "grounding": {"facts": facts},
    }
