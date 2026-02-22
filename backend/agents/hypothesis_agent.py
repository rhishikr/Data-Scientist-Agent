"""
HypothesisAgent: Wraps pipeline/hypothesis/runner.py

LLM injection points:
  - PRE:  LLM reviews available data and suggests what relationship types to expect
  - POST: LLM interprets significant findings in business language
"""
from __future__ import annotations

import json
from typing import Any, Dict

from .base import BaseAgent, AgentResult, MessageType
from .blackboard import SharedBlackboard
from .llm import ask_llm


class HypothesisAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_id="hypothesis",
            name="Hypothesis Testing Agent",
            description="Runs statistical tests and interprets significant findings",
        )

    async def perceive(self, blackboard: SharedBlackboard) -> Dict[str, Any]:
        feature_state = blackboard.data_state.get("features", {})
        report = feature_state.get("report", {})
        return {
            "featured_tables": report.get("loaded_tables", []),
            "feature_columns": report.get("cols", {}),
            "alpha": blackboard.config.get("alpha", 0.05),
        }

    async def reason(self, perception: Dict[str, Any]) -> Dict[str, Any]:
        system_prompt = (
            "You are a statistician reviewing retail data for hypothesis testing. "
            "Given the available feature tables, briefly assess what kinds of "
            "relationships might exist and what tests would be appropriate. Return JSON:\n"
            '{"assessment": "brief analysis",\n'
            ' "expected_relationship_types": ["numeric-numeric correlations", '
            '"category-numeric comparisons"],\n'
            ' "alpha": 0.05,\n'
            ' "proceed": true}\n'
            "Return ONLY valid JSON."
        )

        user_prompt = (
            f"Available featured tables: {perception['featured_tables']}\n"
            f"Feature column counts: {perception['feature_columns']}\n"
            f"Alpha level: {perception['alpha']}"
        )

        llm_response = await ask_llm(system_prompt, user_prompt)

        try:
            plan = json.loads(llm_response)
        except json.JSONDecodeError:
            plan = {
                "assessment": llm_response[:200],
                "alpha": perception["alpha"],
                "proceed": True,
            }

        self.log(
            MessageType.LLM_DECISION,
            {
                "agent": self.name,
                "decision_type": "hypothesis_strategy",
                "decision": plan,
            },
        )
        return plan

    async def act(
        self, plan: Dict[str, Any], blackboard: SharedBlackboard
    ) -> AgentResult:
        from pipeline.hypothesis.runner import run_hypothesis_agent

        alpha = plan.get("alpha", blackboard.config.get("alpha", 0.05))
        payload = run_hypothesis_agent(alpha=alpha)

        num_sig = payload.get("meta", {}).get("num_significant", 0)
        top_findings = payload.get("top_findings", [])

        # POST-ACT LLM: Interpret the top findings in natural language
        interpretation = "No statistically significant findings after FDR correction."
        if top_findings:
            interpret_prompt = (
                "You are a data scientist. These are the top statistically significant "
                "findings from hypothesis testing on retail data. Write a 2-3 sentence "
                "executive summary of what these findings mean for the business. "
                "Be specific but concise.\n\n"
                f"Findings:\n{json.dumps(top_findings[:10], indent=2)}"
            )
            interpretation = await ask_llm(
                "You are a data analyst providing business insights.",
                interpret_prompt,
            )

        blackboard.data_state["hypothesis"] = {
            "payload": payload,
            "num_significant": num_sig,
            "interpretation": interpretation,
        }

        # Store hypothesis results to Supabase
        run_id = blackboard.config.get("run_id")
        if run_id:
            try:
                from db.store import store_hypothesis_snapshot
                store_hypothesis_snapshot(run_id, payload)
            except Exception as e:
                print(f"[HypothesisAgent] Warning: Supabase storage failed: {e}")

        return AgentResult(
            agent_id=self.agent_id,
            success=True,
            outputs={
                "num_tests": payload.get("meta", {}).get("num_tests", 0),
                "num_significant": num_sig,
            },
            llm_reasoning=plan.get("assessment", ""),
            llm_decisions=[
                f"Alpha: {alpha}",
                f"Interpretation: {interpretation}",
            ],
        )
