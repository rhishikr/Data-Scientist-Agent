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
        from pipeline.insights.io import DataPaths

        project_root = Path(blackboard.paths["project_root"])
        data_paths = DataPaths.from_blackboard(blackboard.paths)
        bundle = run_insights(project_root, data_paths=data_paths)

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
                "You are a retail doctor diagnosing a store's health. Write a 3-4 sentence "
                "executive briefing that:\n"
                "1. Diagnoses the most critical business issue (like a doctor diagnosing the main condition)\n"
                "2. Prescribes 1-2 specific actions with expected impact\n"
                "3. Uses imperative voice: 'Do X to achieve Y'\n"
                "Include specific numbers (dollar amounts, percentages, customer counts) where available.\n\n"
                f"Insights:\n{json.dumps(insights_summary, indent=2)}\n\n"
                f"Priority areas from analysis: {plan.get('priority_areas', [])}"
            )
            narrative = await ask_llm(
                "You are a retail doctor — you diagnose business problems and prescribe specific actions. "
                "Write for a store owner who needs to decide what to do today.",
                narrative_prompt,
            )

        blackboard.data_state["insights"] = {
            "bundle": bundle_dict,
            "num_insights": num_insights,
            "executive_narrative": narrative,
        }

        # Store insights to Supabase
        run_id = blackboard.config.get("run_id")
        if run_id:
            try:
                from db.store import store_insight_snapshot
                store_insight_snapshot(run_id, bundle_dict)
            except Exception as e:
                print(f"[InsightsAgent] Warning: Supabase storage failed: {e}")

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
