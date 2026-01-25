from pipeline.customer_insights import run_customer_insights

def answer_customer_question(payload: dict):
    message = (payload.get("message") or "").strip().lower()
    days = int(payload.get("days") or 30)

    data = run_customer_insights(days=days)

    # Very simple grounded QA (MVP). Later, swap this with GPT using the same "grounding".
    facts = data.get("grounding", {}).get("facts", [])
    insights = data.get("insights", [])
    tests = data.get("tests", [])

    if any(k in message for k in ["active", "customers active"]):
        return {"answer": facts[0] if facts else "I don't have active customer counts available."}

    if "retention" in message:
        for f in facts:
            if f.lower().startswith("retention rate"):
                return {"answer": f}

    if "churn" in message or "at risk" in message:
        churn_fact = next((f for f in facts if "churn-risk" in f.lower()), None)
        top_ins = next((i for i in insights if "at-risk" in i["title"].lower() or "churn" in i["title"].lower()), None)
        parts = [p for p in [churn_fact, (top_ins["evidence"] if top_ins else None), (top_ins["recommendedAction"] if top_ins else None)] if p]
        return {"answer": " ".join(parts) if parts else "I don't have churn insights available for this range."}

    if "test" in message or "significant" in message:
        sig = [t for t in tests if t.get("result") == "significant"]
        if not sig:
            return {"answer": "No statistically significant tests were detected for the current dataset and range."}
        t = sig[0]
        return {"answer": f"{t['name']} was significant (p={t['pValue']:.4f})."}

    # fallback: summarize insights
    if insights:
        bullets = " ".join([f"- {i['title']}: {i['evidence']} Action: {i['recommendedAction']}" for i in insights[:3]])
        return {"answer": f"Here are the top insights for the last {days} days: {bullets}"}

    return {"answer": "I can answer questions about active customers, retention, churn risk, and detected patterns, but I don't have enough computed insights yet."}
