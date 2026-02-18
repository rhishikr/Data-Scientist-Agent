"""
InsightsAgent: Wraps pipeline/insights/runner.py

LLM injection points:
  - PRE:  LLM prioritizes insight categories based on hypothesis results
  - POST: LLM generates executive narrative from structured insights
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from .base import BaseAgent, AgentResult, MessageType
from .blackboard import SharedBlackboard
from .llm import ask_llm


class InsightsAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_id="insights",
            name="Insights Generation Agent",
            description="Generates business insights from features and hypothesis results",
        )

    async def perceive(self, blackboard: SharedBlackboard) -> Dict[str, Any]:
        hyp_state = blackboard.data_state.get("hypothesis", {})
        return {
            "hypothesis_significant": hyp_state.get("num_significant", 0),
            "hypothesis_interpretation": hyp_state.get("interpretation", ""),
            "featured_tables": (
                blackboard.data_state.get("features", {})
                .get("report", {})
                .get("loaded_tables", [])
            ),
        }

    async def reason(self, perception: Dict[str, Any]) -> Dict[str, Any]:
        system_prompt = (
            "You are a business intelligence analyst. Based on the hypothesis "
            "testing results, decide what types of insights to prioritize. Return JSON:\n"
            '{"assessment": "what insights to focus on",\n'
            ' "priority_areas": ["customer churn risk", "product performance", '
            '"revenue concentration"],\n'
            ' "narrative_style": "executive-friendly, action-oriented",\n'
            ' "proceed": true}\n'
            "Return ONLY valid JSON."
        )

        user_prompt = (
            f"Hypothesis results: {perception['hypothesis_significant']} significant findings.\n"
            f"Interpretation: {perception['hypothesis_interpretation']}\n"
            f"Available tables: {perception['featured_tables']}"
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
                "decision_type": "insight_priorities",
                "decision": plan,
            },
        )
        return plan

    async def act(
        self, plan: Dict[str, Any], blackboard: SharedBlackboard
    ) -> AgentResult:
        from pipeline.insights.runner import run_insights

        project_root = Path(blackboard.paths["project_root"])
        bundle = run_insights(project_root)

        bundle_dict = bundle.to_dict() if hasattr(bundle, "to_dict") else {"ok": True}
        num_insights = bundle_dict.get("meta", {}).get("num_insights", 0)

        # POST-ACT LLM: Generate executive narrative
        narrative = "No actionable insights generated from current data."
        insights_list = bundle_dict.get("insights", [])
        if insights_list:
            insights_summary = [
                {
                    "title": ins.get("title", ""),
                    "severity": ins.get("severity", ""),
                    "description": ins.get("description", "")[:100],
                }
                for ins in insights_list[:5]
            ]

            narrative_prompt = (
                "Write a 3-4 sentence executive summary that synthesizes these "
                "business insights into actionable intelligence. Focus on the most "
                "critical findings and what actions they suggest.\n\n"
                f"Insights:\n{json.dumps(insights_summary, indent=2)}\n\n"
                f"Priority areas from analysis: {plan.get('priority_areas', [])}"
            )
            narrative = await ask_llm(
                "You are a chief analytics officer writing for the CEO.",
                narrative_prompt,
            )

        blackboard.data_state["insights"] = {
            "bundle": bundle_dict,
            "num_insights": num_insights,
            "executive_narrative": narrative,
        }

        return AgentResult(
            agent_id=self.agent_id,
            success=True,
            outputs={"num_insights": num_insights},
            llm_reasoning=plan.get("assessment", ""),
            llm_decisions=[
                f"Priority areas: {plan.get('priority_areas', [])}",
                f"Narrative: {narrative[:200]}",
            ],
        )
