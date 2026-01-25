from datetime import date

def generate_insights(scored, tests, start_date: date, end_date: date):
    insights = []

    # At-risk share
    total = len(scored)
    at_risk = int((scored["segment"] == "At-Risk").sum()) if total else 0
    share = (at_risk / total) if total else 0

    if share >= 0.15:
        insights.append({
            "title": "At-risk segment is sizable",
            "severity": "warning",
            "evidence": f"At-risk customers are {share:.0%} of all customers in the model base.",
            "recommendedAction": "Target customers inactive 45–90 days with a win-back offer or reminder campaign."
        })

    # Test summaries
    for t in tests:
        if t.get("result") == "significant":
            insights.append({
                "title": f"Statistically significant pattern detected",
                "severity": "info",
                "evidence": f"{t['name']} (p={t['pValue']:.4f}).",
                "recommendedAction": "Use this segment dimension when designing offers or UX changes."
            })

    return insights[:6]
