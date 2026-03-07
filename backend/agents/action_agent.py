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


VALID_CATEGORIES = {"inventory", "customer", "revenue", "marketing", "product"}
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

        # B. Demand SKU Summary
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
                '      "category": "<inventory|customer|revenue|marketing|product>",\n'
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
                "1. Generate 8-12 prescriptions total.\n"
                "2. MANDATORY: Include at least 1 prescription per category "
                "(inventory, customer, revenue, marketing, product).\n"
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
                "8. Return ONLY valid JSON. No markdown fences."
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
