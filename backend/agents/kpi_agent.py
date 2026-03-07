"""
KPIAgent: Wraps pipeline/kpi/runner.py

LLM injection points:
  - PRE:  LLM determines which KPI groups to emphasize
  - POST: LLM contextualizes KPI values with business commentary
"""
from __future__ import annotations

import json
from typing import Any, Dict

from .base import BaseAgent, AgentResult, MessageType
from .blackboard import SharedBlackboard
from .llm import ask_llm


class KPIAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_id="kpi",
            name="KPI Snapshot Agent",
            description="Computes and contextualizes key performance indicators",
        )

    async def perceive(self, blackboard: SharedBlackboard) -> Dict[str, Any]:
        insights_state = blackboard.data_state.get("insights", {})
        return {
            "num_insights": insights_state.get("num_insights", 0),
            "executive_narrative": insights_state.get("executive_narrative", ""),
        }

    async def reason(self, perception: Dict[str, Any]) -> Dict[str, Any]:
        system_prompt = (
            "You are a KPI analytics specialist. Based on the insight analysis "
            "context, determine which KPI groups to emphasize. Return JSON:\n"
            '{"assessment": "brief KPI focus areas",\n'
            ' "emphasis_groups": ["revenue", "customer_health", "inventory"],\n'
            ' "benchmark_context": "e-commerce industry standard",\n'
            ' "proceed": true}\n'
            "Return ONLY valid JSON."
        )

        user_prompt = (
            f"Context from insights agent:\n"
            f"{perception['num_insights']} insights generated.\n"
            f"Executive narrative: {perception['executive_narrative'][:500]}"
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
                "decision_type": "kpi_focus",
                "decision": plan,
            },
        )
        return plan

    async def act(
        self, plan: Dict[str, Any], blackboard: SharedBlackboard
    ) -> AgentResult:
        from pipeline.kpi.runner import run_kpi_snapshot
        from pipeline.kpi.io import DataPaths

        snapshot = run_kpi_snapshot(DataPaths.default())

        # POST-ACT LLM: Contextualize KPI values
        cards = snapshot.get("cards", [])[:10]
        commentary = "KPI snapshot computed but no notable values to highlight."

        if cards:
            cards_summary = [
                {"title": c.get("title"), "value": c.get("value"), "group": c.get("group")}
                for c in cards
                if c.get("value") is not None
            ]

            if cards_summary:
                context_prompt = (
                    "You are a retail doctor reviewing a store's vital signs. For each notable KPI, provide:\n"
                    "1. What it means in plain English (no jargon)\n"
                    "2. Whether it requires action (and what specific action)\n"
                    "3. The 'so what?' — business impact of this number\n\n"
                    "Write 2-3 sentences as if advising a store owner who needs to decide what to do today. "
                    "Start with the most important finding. Use imperative voice for any recommended actions.\n\n"
                    f"KPIs:\n{json.dumps(cards_summary, indent=2, default=str)}"
                )
                commentary = await ask_llm(
                    "You are a retail doctor — you diagnose business health and prescribe actions from KPI data.",
                    context_prompt,
                )

        blackboard.data_state["kpi"] = {
            "snapshot": snapshot,
            "commentary": commentary,
        }

        # Store KPI snapshot to Supabase
        run_id = blackboard.config.get("run_id")
        if run_id:
            try:
                from db.store import store_kpi_snapshot
                store_kpi_snapshot(run_id, snapshot)
            except Exception as e:
                print(f"[KPIAgent] Warning: Supabase storage failed: {e}")

        return AgentResult(
            agent_id=self.agent_id,
            success=True,
            outputs={"num_cards": len(snapshot.get("cards", []))},
            llm_reasoning=plan.get("assessment", ""),
            llm_decisions=[f"KPI Commentary: {commentary[:200]}"],
        )
