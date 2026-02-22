"""
ForecastAgent: Wraps pipeline/forecast/runner.py

LLM injection points:
  - PRE:  LLM identifies key risks to monitor in forecasts
  - POST: LLM generates strategic risk assessment from forecast results
"""
from __future__ import annotations

import json
from typing import Any, Dict

from .base import BaseAgent, AgentResult, MessageType
from .blackboard import SharedBlackboard
from .llm import ask_llm


class ForecastAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_id="forecast",
            name="Forecasting Agent",
            description="Trains ML models and generates business forecasts with strategic analysis",
        )

    async def perceive(self, blackboard: SharedBlackboard) -> Dict[str, Any]:
        kpi_state = blackboard.data_state.get("kpi", {})
        hyp_state = blackboard.data_state.get("hypothesis", {})
        return {
            "kpi_commentary": kpi_state.get("commentary", ""),
            "hypothesis_interpretation": hyp_state.get("interpretation", ""),
            "num_significant_hypotheses": hyp_state.get("num_significant", 0),
        }

    async def reason(self, perception: Dict[str, Any]) -> Dict[str, Any]:
        system_prompt = (
            "You are a forecasting specialist. Based on current KPI trends and "
            "hypothesis findings, assess what the forecast models should focus on. "
            "Return JSON:\n"
            '{"assessment": "brief forecasting focus",\n'
            ' "key_risks_to_monitor": ["churn acceleration", "demand shifts"],\n'
            ' "forecast_horizon_recommendation": "90 days",\n'
            ' "proceed": true}\n'
            "Return ONLY valid JSON."
        )

        user_prompt = (
            f"KPI context: {perception['kpi_commentary'][:500]}\n"
            f"Hypothesis findings: {perception['hypothesis_interpretation'][:500]}\n"
            f"Significant hypotheses: {perception['num_significant_hypotheses']}"
        )

        llm_response = await ask_llm(system_prompt, user_prompt)

        try:
            plan = json.loads(llm_response)
        except json.JSONDecodeError:
            plan = {"assessment": llm_response[:200], "proceed": True}

        self.log(
            MessageType.LLM_DECISION,
            {
                "agent": self.name,
                "decision_type": "forecast_strategy",
                "decision": plan,
            },
        )
        return plan

    async def act(
        self, plan: Dict[str, Any], blackboard: SharedBlackboard
    ) -> AgentResult:
        from pipeline.forecast.runner import run_forecasting
        from pipeline.forecast.io import ForecastPaths

        snapshot = run_forecasting(ForecastPaths.default())
        forecasts = snapshot.get("forecasts", {})

        # POST-ACT LLM: Strategic risk assessment
        rev_30 = forecasts.get("forecasted_revenue", {}).get("next_30d", "N/A")
        rev_90 = forecasts.get("forecasted_revenue", {}).get("next_90d", "N/A")
        churn = forecasts.get("expected_churn_next_month", {}).get(
            "expected_churn_rate_next_30d", "N/A"
        )

        strategic_prompt = (
            "You are a strategic business advisor. Based on these forecast outputs, "
            "write a 3-4 sentence strategic assessment covering:\n"
            "1. Revenue outlook\n2. Churn risk level\n"
            "3. One specific recommended action\n\n"
            f"Forecast data:\n"
            f"- Revenue next 30d: {rev_30}\n"
            f"- Revenue next 90d: {rev_90}\n"
            f"- Expected churn rate: {churn}\n"
            f"- Key risks identified: {plan.get('key_risks_to_monitor', [])}"
        )

        strategic_assessment = await ask_llm(
            "You are a chief strategy officer providing a business forecast briefing.",
            strategic_prompt,
        )

        blackboard.data_state["forecast"] = {
            "snapshot": snapshot,
            "strategic_assessment": strategic_assessment,
        }

        # Store forecast snapshot to Supabase
        run_id = blackboard.config.get("run_id")
        if run_id:
            try:
                from db.store import store_forecast_snapshot
                store_forecast_snapshot(run_id, snapshot)
            except Exception as e:
                print(f"[ForecastAgent] Warning: Supabase storage failed: {e}")

        return AgentResult(
            agent_id=self.agent_id,
            success=True,
            outputs={
                "revenue_30d": rev_30,
                "churn_rate": churn,
            },
            llm_reasoning=plan.get("assessment", ""),
            llm_decisions=[
                f"Strategic assessment: {strategic_assessment[:200]}",
                f"Risks: {plan.get('key_risks_to_monitor', [])}",
            ],
        )
