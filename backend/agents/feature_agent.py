"""
FeatureAgent: Wraps pipeline/features/feature_folder.py

LLM injection point: The LLM reviews column names from cleaned data and
suggests which feature engineering strategies are most relevant.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

from .base import BaseAgent, AgentResult, MessageType
from .blackboard import SharedBlackboard
from .llm import ask_llm


class FeatureAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_id="features",
            name="Feature Engineering Agent",
            description="Analyzes cleaned data structure and engineers features",
        )

    async def perceive(self, blackboard: SharedBlackboard) -> Dict[str, Any]:
        """Read cleaning results from blackboard to understand what we have."""
        import pandas as pd

        cleaned_dir = Path(blackboard.paths["cleaned_dir"])
        cleaning_result = blackboard.data_state.get("cleaning", {})

        table_summaries = []
        for f in sorted(cleaned_dir.glob("*.csv")):
            try:
                df = pd.read_csv(f, nrows=5)
                table_summaries.append(
                    {
                        "file": f.name,
                        "columns": list(df.columns),
                        "num_cols": len(df.columns),
                        "sample_row": df.iloc[0].to_dict() if len(df) > 0 else {},
                    }
                )
            except Exception:
                pass

        return {
            "cleaned_tables": table_summaries,
            "cleaning_strategy": cleaning_result.get("strategy", {}),
        }

    async def reason(self, perception: Dict[str, Any]) -> Dict[str, Any]:
        """Ask the LLM to suggest feature engineering strategies."""
        system_prompt = (
            "You are an expert data scientist specializing in feature engineering "
            "for e-commerce/retail data. Given the cleaned table schemas, assess "
            "what features would be most valuable. Return JSON:\n"
            '{"assessment": "brief analysis of available data",\n'
            ' "key_join_strategy": "how tables relate (e.g., customer_id, sku)",\n'
            ' "high_value_features": ["top 3-5 feature ideas"],\n'
            ' "proceed": true}\n'
            "Return ONLY valid JSON."
        )

        tables_str = json.dumps(perception["cleaned_tables"], indent=2, default=str)[
            :3000
        ]
        user_prompt = f"Cleaned tables:\n{tables_str}"

        llm_response = await ask_llm(system_prompt, user_prompt)

        try:
            plan = json.loads(llm_response)
        except json.JSONDecodeError:
            plan = {"assessment": llm_response[:200], "proceed": True}

        self.log(
            MessageType.LLM_DECISION,
            {
                "agent": self.name,
                "decision_type": "feature_strategy",
                "decision": plan,
            },
        )
        return plan

    async def act(
        self, plan: Dict[str, Any], blackboard: SharedBlackboard
    ) -> AgentResult:
        """Execute the existing feature_folder.py subprocess."""
        project_root = Path(blackboard.paths["project_root"])
        feature_script = project_root / "pipeline" / "features" / "feature_folder.py"

        cmd = [
            sys.executable,
            str(feature_script),
            "--input_dir", blackboard.paths["cleaned_dir"],
            "--output_dir", blackboard.paths["featured_dir"],
            "--reports_dir", blackboard.paths["reports_dir"],
        ]

        p = subprocess.run(
            cmd,
            cwd=str(feature_script.parent),
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )

        if p.returncode != 0:
            return AgentResult(
                agent_id=self.agent_id,
                success=False,
                error=p.stderr or p.stdout,
                llm_reasoning=plan.get("assessment", ""),
            )

        report_path = Path(blackboard.paths["reports_dir"]) / "feature_report.json"
        report: dict = {}
        if report_path.exists():
            report = json.loads(report_path.read_text(encoding="utf-8"))

        blackboard.data_state["features"] = {
            "report": report,
            "strategy": plan,
        }

        self.log(
            MessageType.DATA_READY,
            {"agent": self.name, "output": "featured_data"},
            recipient="hypothesis",
        )

        return AgentResult(
            agent_id=self.agent_id,
            success=True,
            outputs={"feature_report_keys": list(report.keys())},
            llm_reasoning=plan.get("assessment", ""),
            llm_decisions=plan.get("high_value_features", []),
        )
