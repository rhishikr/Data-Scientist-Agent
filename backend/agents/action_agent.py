"""
ActionAgent: Produces a fully LLM-generated action plan from all upstream data.

LLM injection points:
  - PRE:  LLM decides prioritization strategy and cross-domain connections
  - POST: LLM generates the complete action plan from structured data digest

Fallback: rule-based prescriptions.py if LLM fails.
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from .base import BaseAgent, AgentResult, MessageType
from .blackboard import SharedBlackboard
from .llm import ask_llm, parse_llm_json


VALID_CATEGORIES = {"inventory", "customer", "revenue", "marketing", "product", "funnel", "pricing"}
VALID_URGENCIES = {"critical", "high", "medium", "low"}
VALID_EFFORTS = {"quick-win", "moderate", "strategic"}


class ActionAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_id="actions",
            name="Action Plan Agent",
            description="Aggregates all upstream data into a prioritized, LLM-generated action plan",
        )
        self._perception: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Perceive (unchanged)
    # ------------------------------------------------------------------

    async def perceive(self, blackboard: SharedBlackboard) -> Dict[str, Any]:
        insights_state = blackboard.data_state.get("insights", {})
        kpi_state = blackboard.data_state.get("kpi", {})
        forecast_state = blackboard.data_state.get("forecast", {})

        # Extract structured data from upstream agents
        insight_bundle = insights_state.get("bundle", {})
        insights_list = insight_bundle.get("insights", []) if isinstance(insight_bundle, dict) else []
        executive_narrative = insights_state.get("executive_narrative", "")

        kpi_snapshot = kpi_state.get("snapshot", {})
        kpi_commentary = kpi_state.get("commentary", "")

        forecast_snapshot = forecast_state.get("snapshot", {})
        strategic_assessment = forecast_state.get("strategic_assessment", "")
        executive_insights = forecast_snapshot.get("executive_insights", {})

        # Read demand SKUs from CSV
        demand_skus: List[dict] = []
        forecast_dir = Path(blackboard.paths.get("forecast_dir", ""))
        demand_path = forecast_dir / "demand_forecast_sku.csv"
        if demand_path.is_file():
            try:
                df = pd.read_csv(demand_path)
                demand_skus = df.to_dict(orient="records")
            except Exception:
                pass

        # Read churn predictions from CSV
        churn_predictions: List[dict] = []
        churn_path = forecast_dir / "churn_predictions.csv"
        if churn_path.is_file():
            try:
                df = pd.read_csv(churn_path)
                churn_predictions = df.to_dict(orient="records")
            except Exception:
                pass

        perception = {
            "insights_list": insights_list,
            "executive_narrative": executive_narrative,
            "kpi_snapshot": kpi_snapshot,
            "kpi_commentary": kpi_commentary,
            "forecast_snapshot": forecast_snapshot,
            "strategic_assessment": strategic_assessment,
            "executive_insights": executive_insights,
            "demand_skus": demand_skus,
            "churn_predictions": churn_predictions,
        }

        self._perception = perception
        return perception

    # ------------------------------------------------------------------
    # Reason (PRE-act LLM call — unchanged)
    # ------------------------------------------------------------------

    async def reason(self, perception: Dict[str, Any]) -> Dict[str, Any]:
        num_insights = len(perception["insights_list"])
        demand_skus = perception["demand_skus"]
        churn_preds = perception["churn_predictions"]

        critical_skus = sum(1 for s in demand_skus if s.get("status") == "critical")
        warning_skus = sum(1 for s in demand_skus if s.get("status") == "warning")
        high_churn = sum(1 for c in churn_preds if (c.get("churn_prob_30d") or 0) >= 0.7)
        churn_value = sum(c.get("total_spend", 0) for c in churn_preds if (c.get("churn_prob_30d") or 0) >= 0.7)

        system_prompt = (
            "You are a retail business strategist. Given analysis from multiple agents "
            "- insights, KPIs, forecasts, demand, churn - decide how to prioritize and "
            "group prescriptions into a coherent action plan.\n\n"
            "Return JSON:\n"
            '{"assessment": "1-2 sentence overall business state",\n'
            ' "prioritization_strategy": "criteria for ordering actions",\n'
            ' "cross_domain_connections": ["connections across data sources"],\n'
            ' "deduplication_targets": ["areas where prescriptions overlap"],\n'
            ' "proceed": true}\n'
            "Return ONLY valid JSON."
        )

        user_prompt = (
            f"Business Insights ({num_insights} total): "
            f"{perception['executive_narrative'][:500]}\n\n"
            f"KPI Summary: {perception['kpi_commentary'][:500]}\n\n"
            f"Forecast Assessment: {perception['strategic_assessment'][:500]}\n\n"
            f"Demand Alerts: {critical_skus} critical, {warning_skus} warning "
            f"out of {len(demand_skus)} SKUs\n\n"
            f"Churn Risk: {high_churn} customers with >70% churn probability, "
            f"${churn_value:,.0f} at risk"
        )

        llm_response = await ask_llm(system_prompt, user_prompt)
        plan = parse_llm_json(llm_response)

        self.log(
            MessageType.LLM_DECISION,
            {
                "agent": self.name,
                "decision_type": "action_prioritization",
                "decision": plan,
            },
        )
        return plan

    # ------------------------------------------------------------------
    # Data Digest Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _fmt_card_value(card: dict) -> str:
        """Format a single KPI card value for the digest."""
        val = card.get("value")
        if val is None:
            return "N/A"
        fmt = card.get("format", "number")
        try:
            val = float(val)
            if math.isnan(val) or math.isinf(val):
                return "N/A"
        except (TypeError, ValueError):
            return str(val)

        if fmt == "currency":
            return f"${val:,.0f}" if val >= 1000 else f"${val:,.2f}"
        if fmt == "percent":
            return f"{val:.1f}%"
        if fmt == "minutes":
            return f"{val:.1f}min"
        return f"{val:,.1f}" if val != int(val) else f"{int(val)}"

    def _build_data_digest(self, p: Dict[str, Any]) -> str:
        """Format all upstream data into a structured text block for the LLM."""
        sections: List[str] = []

        # A. KPI Summary — grouped by card group
        kpi_snapshot = p.get("kpi_snapshot", {})
        cards = kpi_snapshot.get("cards", [])
        if cards:
            groups: Dict[str, List[str]] = {}
            for card in cards:
                group = card.get("group", "Other")
                label = card.get("title", card.get("id", ""))
                value = self._fmt_card_value(card)
                groups.setdefault(group, []).append(f"{label}: {value}")
            kpi_lines = []
            for group, items in groups.items():
                kpi_lines.append(f"  {group}: {' | '.join(items)}")
            sections.append("=== KPI DASHBOARD ===\n" + "\n".join(kpi_lines))

        # B. Funnel & Conversion Summary
        kpi_groups = kpi_snapshot.get("kpis", {})
        funnel_data = kpi_groups.get("conversion_funnel", {})
        if funnel_data:
            funnel_lines = []
            for key in ["conversion_rate", "cart_abandonment_rate", "checkout_completion_rate",
                         "product_view_rate", "avg_session_duration", "revenue_per_session",
                         "mobile_conversion_rate", "desktop_conversion_rate", "bounce_rate"]:
                val = funnel_data.get(key)
                if val is not None:
                    if "rate" in key or key == "bounce_rate":
                        funnel_lines.append(f"  {key}: {val:.1%}")
                    elif key == "avg_session_duration":
                        funnel_lines.append(f"  {key}: {val:.0f}s")
                    elif key == "revenue_per_session":
                        funnel_lines.append(f"  {key}: ${val:.2f}")
                    else:
                        funnel_lines.append(f"  {key}: {val}")
            if funnel_lines:
                sections.append("=== FUNNEL & CONVERSION ===\n" + "\n".join(funnel_lines))

        # C. Demographics Summary
        demo_data = kpi_groups.get("demographics", {})
        if demo_data:
            demo_lines = []
            by_gender = demo_data.get("customers_by_gender", {})
            if by_gender:
                demo_lines.append(f"  Gender: {', '.join(f'{k}={v}' for k, v in by_gender.items())}")
            by_age = demo_data.get("customers_by_age_group", {})
            if by_age:
                demo_lines.append(f"  Age groups: {', '.join(f'{k}={v}' for k, v in by_age.items())}")
            by_loyalty = demo_data.get("customers_by_loyalty_tier", {})
            if by_loyalty:
                demo_lines.append(f"  Loyalty tiers: {', '.join(f'{k}={v}' for k, v in by_loyalty.items())}")
            avg_spend = demo_data.get("avg_spend_by_loyalty", {})
            if avg_spend:
                demo_lines.append(f"  Avg spend by tier: {', '.join(f'{k}=${v:,.0f}' for k, v in avg_spend.items())}")
            if demo_lines:
                sections.append("=== CUSTOMER DEMOGRAPHICS ===\n" + "\n".join(demo_lines))

        # D. Net Revenue Breakdown
        net_rev = kpi_groups.get("net_revenue", {})
        if net_rev and net_rev.get("gross_revenue"):
            nr_lines = [
                f"  Gross Revenue: ${net_rev.get('gross_revenue', 0):,.0f}",
                f"  Discounts: ${net_rev.get('total_discounts', 0):,.0f}",
                f"  Returns: ${net_rev.get('total_returns', 0):,.0f}",
                f"  Refunds: ${net_rev.get('total_refunds', 0):,.0f}",
                f"  Fees: ${net_rev.get('total_fees', 0):,.0f}",
                f"  Net Revenue: ${net_rev.get('net_revenue', 0):,.0f}",
                f"  Discount Rate: {net_rev.get('discount_rate', 0):.1%}",
            ]
            sections.append("=== NET REVENUE WATERFALL ===\n" + "\n".join(nr_lines))

        # E. Payment Health
        pay_data = kpi_groups.get("payment_health", {})
        if pay_data and pay_data.get("payment_failure_rate") is not None:
            pay_lines = [
                f"  Failure Rate: {pay_data.get('payment_failure_rate', 0):.1%}",
                f"  Refund Rate: {pay_data.get('refund_rate', 0):.1%}",
                f"  Top Method: {pay_data.get('top_payment_method', 'N/A')}",
                f"  Avg Fee: ${pay_data.get('avg_transaction_fee', 0):.2f}",
            ]
            sections.append("=== PAYMENT HEALTH ===\n" + "\n".join(pay_lines))

        # F. Brand Performance (top 5)
        brand_data = kpi_groups.get("brand_performance", {})
        rev_by_brand = brand_data.get("revenue_by_brand", {})
        if rev_by_brand:
            top_brands = sorted(rev_by_brand.items(), key=lambda x: -x[1])[:5]
            brand_lines = [f"  {b}: ${v:,.0f}" for b, v in top_brands]
            sections.append("=== TOP BRANDS BY REVENUE ===\n" + "\n".join(brand_lines))

        # G. Supplier Health
        supplier_data = kpi_groups.get("supplier_health", {})
        stockout_by_supplier = supplier_data.get("stockout_by_supplier", {})
        if stockout_by_supplier:
            problem_suppliers = {k: v for k, v in stockout_by_supplier.items() if v > 0}
            if problem_suppliers:
                supplier_lines = [f"  {s}: {n} SKUs at risk" for s, n in sorted(problem_suppliers.items(), key=lambda x: -x[1])]
                sections.append("=== SUPPLIER STOCKOUT RISKS ===\n" + "\n".join(supplier_lines))

        # H. Demand SKU Summary
        demand_skus = p.get("demand_skus", [])
        critical = [s for s in demand_skus if s.get("status") == "critical"]
        warning = [s for s in demand_skus if s.get("status") == "warning"]
        healthy = [s for s in demand_skus if s.get("status") == "healthy"]
        demand_lines = [
            f"Total SKUs: {len(demand_skus)} ({len(critical)} critical, "
            f"{len(warning)} warning, {len(healthy)} healthy)"
        ]
        for label, skus in [("Critical", critical[:5]), ("Warning", warning[:5])]:
            for s in skus:
                sku_id = s.get("sku", s.get("product_id", "?"))
                name = s.get("product_name", sku_id)
                stock = s.get("current_stock", "?")
                forecast = s.get("forecast_qty_30d", "?")
                days = s.get("days_until_stockout", "?")
                demand_lines.append(
                    f"  [{label}] {sku_id} \"{name}\": "
                    f"stock={stock}, forecast_30d={forecast}, days_to_stockout={days}"
                )
        sections.append("=== DEMAND FORECAST ===\n" + "\n".join(demand_lines))

        # C. Churn Risk Summary
        churn_preds = p.get("churn_predictions", [])
        high_risk = sorted(
            [c for c in churn_preds if (c.get("churn_prob_30d") or 0) >= 0.7],
            key=lambda c: c.get("churn_prob_30d", 0),
            reverse=True,
        )
        total_at_risk = sum(c.get("total_spend", 0) for c in high_risk)
        churn_lines = [
            f"High-risk customers (>70% churn prob): {len(high_risk)} "
            f"out of {len(churn_preds)} total, ${total_at_risk:,.0f} spend at risk"
        ]
        for c in high_risk[:5]:
            cid = c.get("customer_id", "?")
            name = c.get("name", cid)
            prob = c.get("churn_prob_30d", 0)
            spend = c.get("total_spend", 0)
            recency = c.get("recency_days", "?")
            churn_lines.append(
                f"  customer:{cid} \"{name}\": "
                f"churn_prob={prob:.0%}, spend=${spend:,.0f}, recency={recency}d"
            )
        sections.append("=== CHURN RISK ===\n" + "\n".join(churn_lines))

        # D. Forecast Highlights
        forecasts = p.get("forecast_snapshot", {}).get("forecasts", {})
        rev = forecasts.get("forecasted_revenue", {})
        churn_fc = forecasts.get("expected_churn_next_month", {})
        cashflow = forecasts.get("projected_cashflow", {})
        forecast_lines = [
            f"Revenue forecast: 7d=${rev.get('next_7d', 'N/A')}, "
            f"30d=${rev.get('next_30d', 'N/A')}, 90d=${rev.get('next_90d', 'N/A')}",
            f"Expected churn rate (30d): {churn_fc.get('expected_churn_rate_next_30d', 'N/A')}",
            f"Cashflow proxy (30d): ${cashflow.get('next_30d', 'N/A')}",
        ]
        sections.append("=== REVENUE & CASHFLOW FORECAST ===\n" + "\n".join(forecast_lines))

        # E. Insight Summaries — grouped by severity
        insights = p.get("insights_list", [])
        if insights:
            by_severity: Dict[str, List[str]] = {}
            for ins in insights:
                sev = ins.get("severity", "low")
                title = ins.get("title", "Untitled")
                by_severity.setdefault(sev, []).append(f'"{title}"')
            insight_lines = [f"Total insights: {len(insights)}"]
            for sev in ["high", "medium", "low"]:
                titles = by_severity.get(sev, [])
                if titles:
                    insight_lines.append(f"  {sev.capitalize()} ({len(titles)}): {', '.join(titles)}")
            sections.append("=== INSIGHTS ===\n" + "\n".join(insight_lines))

        # F. Executive Context — truncated narratives
        exec_lines = []
        if p.get("executive_narrative"):
            exec_lines.append(f"Diagnosis: {p['executive_narrative'][:400]}")
        if p.get("kpi_commentary"):
            exec_lines.append(f"KPI Commentary: {p['kpi_commentary'][:400]}")
        if p.get("strategic_assessment"):
            exec_lines.append(f"Strategic Assessment: {p['strategic_assessment'][:400]}")
        risks = p.get("executive_insights", {}).get("top_3_risks", [])
        if risks:
            risk_strs = []
            for r in risks:
                if isinstance(r, dict):
                    risk_strs.append(r.get("title", str(r)))
                else:
                    risk_strs.append(str(r))
            exec_lines.append(f"Top Risks: {', '.join(risk_strs)}")
        if exec_lines:
            sections.append("=== EXECUTIVE CONTEXT ===\n" + "\n".join(exec_lines))

        # G. Follow-Up Context (comparison with previous run)
        comparison = p.get("comparison_data")
        if comparison and isinstance(comparison, dict):
            comp_lines = []

            # KPI changes summary
            deltas = comparison.get("deltas", [])
            if deltas:
                improving = [d for d in deltas if d.get("direction") == "up"]
                declining = [d for d in deltas if d.get("direction") == "down"]
                comp_lines.append(f"KPI Changes: {len(improving)} improving, {len(declining)} declining out of {len(deltas)} total")

                # Show top improving
                for d in sorted(improving, key=lambda x: abs(x.get("percent_change") or 0), reverse=True)[:5]:
                    pct = d.get("percent_change")
                    pct_str = f" ({pct:+.1%})" if pct is not None else ""
                    comp_lines.append(f"  ↑ {d.get('title', d.get('id', ''))}{pct_str}")

                # Show top declining
                for d in sorted(declining, key=lambda x: abs(x.get("percent_change") or 0), reverse=True)[:5]:
                    pct = d.get("percent_change")
                    pct_str = f" ({pct:+.1%})" if pct is not None else ""
                    comp_lines.append(f"  ↓ {d.get('title', d.get('id', ''))}{pct_str}")

            # Resolved issues
            resolved = comparison.get("resolved_issues", [])
            if resolved:
                comp_lines.append(f"Resolved Issues ({len(resolved)}):")
                for r in resolved[:5]:
                    comp_lines.append(f"  ✓ [{r.get('severity', '')}] {r.get('title', '')}")

            # New risks
            new_risks = comparison.get("new_risks", [])
            if new_risks:
                comp_lines.append(f"New Risks ({len(new_risks)}):")
                for r in new_risks[:5]:
                    comp_lines.append(f"  ⚠ [{r.get('severity', '')}] {r.get('title', '')}")

            # Completed prescriptions impact
            completed_rx = comparison.get("completed_prescriptions", [])
            if completed_rx:
                comp_lines.append(f"Completed Prescriptions ({len(completed_rx)}):")
                for rx in completed_rx:
                    impact_summary = ""
                    related = rx.get("related_kpi_changes", [])
                    if related:
                        impacts = [f"{d['title']} {d['direction']}" for d in related[:3]]
                        impact_summary = f" → {', '.join(impacts)}"
                    comp_lines.append(f"  Done: {rx.get('title', '')}{impact_summary}")

            if comp_lines:
                sections.append("=== FOLLOW-UP COMPARISON (vs previous run) ===\n" + "\n".join(comp_lines))

        return "\n\n".join(sections)

    @staticmethod
    def _build_evidence_registry(p: Dict[str, Any]) -> Dict[str, Any]:
        """Index real data by entity reference for post-processing."""
        registry: Dict[str, Any] = {}
        for sku in p.get("demand_skus", []):
            sku_id = str(sku.get("sku", sku.get("product_id", "")))
            if sku_id:
                registry[f"sku:{sku_id}"] = sku
        for cust in p.get("churn_predictions", []):
            cid = str(cust.get("customer_id", ""))
            if cid:
                registry[f"customer:{cid}"] = cust
        for ins in p.get("insights_list", []):
            iid = ins.get("insight_id", "")
            if iid:
                registry[f"insight:{iid}"] = ins.get("evidence", {})
        return registry

    @staticmethod
    def _attach_evidence(
        prescriptions: List[dict], registry: Dict[str, Any]
    ) -> List[dict]:
        """Populate evidence fields from the registry using related_entities."""
        for rx in prescriptions:
            evidence: Dict[str, Any] = {}
            for ref in rx.get("related_entities", []):
                if ref in registry:
                    evidence[ref] = registry[ref]
            rx["evidence"] = evidence
        return prescriptions

    @staticmethod
    def _validate_and_fix(prescriptions: List[dict]) -> List[dict]:
        """Guard against invalid LLM output."""
        if not prescriptions:
            raise ValueError("LLM returned zero prescriptions")

        seen_ids: set = set()
        for rx in prescriptions:
            if rx.get("category") not in VALID_CATEGORIES:
                rx["category"] = "product"
            if rx.get("urgency") not in VALID_URGENCIES:
                rx["urgency"] = "medium"
            if rx.get("effort") not in VALID_EFFORTS:
                rx["effort"] = "moderate"
            try:
                rx["priority"] = int(rx.get("priority", 50))
            except (TypeError, ValueError):
                rx["priority"] = 50

            # Ensure unique IDs
            rid = rx.get("id") or hashlib.md5(
                rx.get("title", "rx").encode()
            ).hexdigest()[:8]
            while rid in seen_ids:
                rid = rid + "x"
            seen_ids.add(rid)
            rx["id"] = rid

            # Ensure required fields
            rx.setdefault("title", "Review action")
            rx.setdefault("description", "")
            rx.setdefault("impact_estimate", "")
            rx.setdefault("source", "action_agent")
            rx.setdefault("action_type", "investigate")
            rx.setdefault("related_entities", [])

        return prescriptions

    # ------------------------------------------------------------------
    # Act (LLM-first with rule-based fallback)
    # ------------------------------------------------------------------

    async def act(
        self, plan: Dict[str, Any], blackboard: SharedBlackboard
    ) -> AgentResult:
        p = self._perception

        # Inject comparison data if a previous run exists
        try:
            from db.store import get_pipeline_runs, get_latest_run_id
            runs = get_pipeline_runs()
            completed_runs = [r for r in runs if r.get("status") == "completed"]
            if len(completed_runs) >= 2:
                import httpx
                # Use the internal compare endpoint data
                current_run = blackboard.config.get("run_id")
                prev_run = completed_runs[1].get("id") if not current_run else None
                # Build comparison inline instead of HTTP call
                from db.store import (
                    get_run_insight_snapshot, get_latest_insight_snapshot,
                    get_run_action_plan_snapshot, get_prescription_statuses,
                    get_run_kpi_snapshot, get_latest_kpi_snapshot,
                )

                cur_kpi = get_run_kpi_snapshot(current_run) if current_run else get_latest_kpi_snapshot()
                prev_kpi = get_run_kpi_snapshot(completed_runs[1]["id"]) if len(completed_runs) >= 2 else None

                if cur_kpi and prev_kpi:
                    cur_cards = {c["id"]: c for c in cur_kpi.get("cards", []) if isinstance(c, dict)}
                    prev_cards = {c["id"]: c for c in prev_kpi.get("cards", []) if isinstance(c, dict)}

                    deltas = []
                    for card_id, card in cur_cards.items():
                        cur_val = card.get("value")
                        prev_card = prev_cards.get(card_id)
                        prev_val = prev_card.get("value") if prev_card else None
                        if not isinstance(cur_val, (int, float)):
                            continue
                        if prev_val is not None and not isinstance(prev_val, (int, float)):
                            continue
                        if prev_val is None:
                            continue
                        abs_change = cur_val - prev_val
                        pct_change = abs_change / prev_val if prev_val != 0 else None
                        direction = "up" if abs_change > 0 else ("down" if abs_change < 0 else "stable")
                        deltas.append({
                            "id": card_id,
                            "title": card.get("title", ""),
                            "group": card.get("group", ""),
                            "direction": direction,
                            "percent_change": pct_change,
                        })

                    # Insight comparison
                    cur_insights = []
                    prev_insights = []
                    try:
                        ci = get_run_insight_snapshot(current_run) if current_run else get_latest_insight_snapshot()
                        if ci:
                            cur_insights = ci.get("insights", [])
                    except Exception:
                        pass
                    try:
                        pi = get_run_insight_snapshot(completed_runs[1]["id"])
                        if pi:
                            prev_insights = pi.get("insights", [])
                    except Exception:
                        pass

                    cur_titles = {i.get("title", "").lower().strip() for i in cur_insights if i.get("title")}
                    prev_titles = {i.get("title", "").lower().strip() for i in prev_insights if i.get("title")}

                    resolved = [{"title": i.get("title",""), "severity": i.get("severity","low")}
                                for i in prev_insights
                                if i.get("severity") in ("high","medium")
                                and (i.get("title","").lower().strip()) not in cur_titles]
                    new_risks = [{"title": i.get("title",""), "severity": i.get("severity","low")}
                                 for i in cur_insights
                                 if i.get("severity") in ("high","medium")
                                 and (i.get("title","").lower().strip()) not in prev_titles]

                    p["comparison_data"] = {
                        "deltas": deltas,
                        "resolved_issues": resolved,
                        "new_risks": new_risks,
                    }
        except Exception as e:
            print(f"[ActionAgent] Could not load comparison data: {e}")

        # Build structured data for LLM and evidence registry for post-processing
        data_digest = self._build_data_digest(p)
        evidence_registry = self._build_evidence_registry(p)

        generation_method = "llm"
        final_dict: Dict[str, Any]

        try:
            system_prompt = (
                "You are a retail business doctor. You diagnose a store's health and "
                "prescribe a complete action plan based on structured data from multiple "
                "analysis systems.\n\n"
                "Generate a complete action plan as JSON:\n"
                "{\n"
                '  "health_score": <integer 0-100>,\n'
                '  "health_score_reasoning": "1 sentence justifying the score with specific numbers",\n'
                '  "health_diagnosis": "4-6 sentence paragraph diagnosing the store\'s overall health. '
                "Connect dots across inventory, customers, revenue, marketing, and products. "
                'Use specific numbers from the data.",\n'
                '  "prescriptions": [\n'
                "    {\n"
                '      "id": "<unique 8-char alphanumeric>",\n'
                '      "priority": <integer, 1=most urgent>,\n'
                '      "category": "<inventory|customer|revenue|marketing|product|funnel|pricing>",\n'
                '      "urgency": "<critical|high|medium|low>",\n'
                '      "title": "<imperative voice, max 80 chars, start with action verb>",\n'
                '      "description": "<2-3 sentences cross-referencing data sources with specific numbers>",\n'
                '      "impact_estimate": "<quantified using actual data numbers>",\n'
                '      "effort": "<quick-win|moderate|strategic>",\n'
                '      "action_type": "<restock|outreach|optimize|investigate|campaign|monitor>",\n'
                '      "source": "action_agent",\n'
                '      "related_entities": ["sku:<sku_id>", "customer:<customer_id>", "insight:<insight_id>"]\n'
                "    }\n"
                "  ]\n"
                "}\n\n"
                "RULES:\n"
                "1. Generate 10-15 prescriptions total.\n"
                "2. MANDATORY: Include at least 1 prescription per category "
                "(inventory, customer, revenue, marketing, product, funnel, pricing).\n"
                "3. Use IMPERATIVE VOICE for titles — start with action verbs: "
                "Restock, Launch, Investigate, Optimize, Monitor, Redesign, Test, "
                "Expand, Reduce, Consolidate, etc.\n"
                "4. Ground ALL impact_estimate values in actual numbers from the data. "
                "Never invent numbers.\n"
                "5. In related_entities, reference actual entity IDs from the data "
                'using format "sku:<id>" or "customer:<id>" or "insight:<id>".\n'
                "6. Cross-reference data sources in descriptions — connect inventory "
                "issues with customer churn, revenue trends with marketing spend, etc.\n"
                "7. Health score: 80-100=healthy, 60-79=needs attention, "
                "40-59=concerning, 0-39=critical.\n"
                "8. Return ONLY valid JSON. No markdown fences.\n"
                "9. If FOLLOW-UP COMPARISON data is provided, reference it in your prescriptions. "
                "Acknowledge resolved issues, flag new risks, and adjust recommendations based on "
                "what improved and what declined since the last analysis.\n"
            )

            user_prompt = (
                f"{data_digest}\n\n"
                f"=== PRIORITIZATION GUIDANCE (from strategic analysis) ===\n"
                f"Assessment: {plan.get('assessment', '')}\n"
                f"Strategy: {plan.get('prioritization_strategy', '')}\n"
                f"Cross-domain connections: {plan.get('cross_domain_connections', [])}"
            )

            llm_response = await ask_llm(system_prompt, user_prompt)
            llm_result = parse_llm_json(llm_response, fallback=None)

            if not llm_result or "prescriptions" not in llm_result:
                raise ValueError("LLM response missing prescriptions key")

            # Post-process: validate fields, attach real evidence
            prescriptions = self._validate_and_fix(llm_result["prescriptions"])
            prescriptions = self._attach_evidence(prescriptions, evidence_registry)

            final_dict = {
                "health_score": max(0, min(100, int(llm_result.get("health_score", 50)))),
                "health_summary": llm_result.get("health_diagnosis", ""),
                "health_score_justification": llm_result.get("health_score_reasoning", ""),
                "prescriptions": prescriptions,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "generation_method": "llm",
            }

        except Exception as e:
            print(f"[ActionAgent] LLM generation failed, using rule-based fallback: {e}")
            from pipeline.insights.prescriptions import build_action_plan

            baseline = build_action_plan(
                insights=p["insights_list"],
                demand_skus=p["demand_skus"],
                churn_predictions=p["churn_predictions"],
                executive_insights=p["executive_insights"],
                generated_at=datetime.now(timezone.utc).isoformat(),
            )
            final_dict = baseline.to_dict()
            final_dict["generation_method"] = "rule_based_fallback"
            generation_method = "rule_based_fallback"

        # Save to blackboard
        blackboard.data_state["actions"] = final_dict

        # Save locally
        insight_dir = Path(blackboard.paths.get("insight_dir", ""))
        insight_dir.mkdir(parents=True, exist_ok=True)
        output_path = insight_dir / "action_plan.json"
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(final_dict, f, indent=2, default=str)
        except Exception as e:
            print(f"[ActionAgent] Warning: Could not save local file: {e}")

        # Save to Supabase
        run_id = blackboard.config.get("run_id")
        if run_id:
            try:
                from db.store import store_action_plan_snapshot
                store_action_plan_snapshot(run_id, final_dict)
            except Exception as e:
                print(f"[ActionAgent] Warning: Supabase storage failed: {e}")

        return AgentResult(
            agent_id=self.agent_id,
            success=True,
            outputs={
                "num_prescriptions": len(final_dict.get("prescriptions", [])),
                "health_score": final_dict.get("health_score", 0),
                "generation_method": generation_method,
            },
            llm_reasoning=plan.get("assessment", ""),
            llm_decisions=[
                f"Prioritization: {plan.get('prioritization_strategy', '')}",
                f"Health score: {final_dict.get('health_score', 0)}/100",
                f"Generation method: {generation_method}",
            ],
        )
