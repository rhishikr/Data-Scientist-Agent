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
from .llm import ask_llm, parse_llm_json


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

        self.emit_hint("Reading cleaned datasets...")
        cleaned_dir = Path(blackboard.paths["cleaned_dir"])
        cleaning_result = blackboard.data_state.get("cleaning", {})

        table_summaries = []
        for f in sorted(cleaned_dir.glob("*.csv")):
            try:
                df = pd.read_csv(f, nrows=100)
                numeric_cols = df.select_dtypes(include="number").columns.tolist()
                categorical_cols = df.select_dtypes(exclude="number").columns.tolist()
                table_summaries.append(
                    {
                        "file": f.name,
                        "columns": list(df.columns),
                        "num_cols": len(df.columns),
                        "rows_sampled": len(df),
                        "dtypes": {col: str(df[col].dtype) for col in df.columns},
                        "null_pct": {
                            col: round(float(df[col].isna().mean()), 3)
                            for col in df.columns
                        },
                        "numeric_columns": numeric_cols,
                        "categorical_columns": categorical_cols,
                        "unique_counts": {
                            col: int(df[col].nunique()) for col in df.columns
                        },
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
            "for e-commerce/retail data. Given the cleaned table schemas (with data "
            "types, null rates, and cardinality), assess what features would be most "
            "valuable and how tables should be joined.\n\n"
            "Return JSON:\n"
            '{"assessment": "2-3 sentence analysis of the data landscape and feature potential",\n'
            ' "key_join_strategy": "how tables relate (e.g., customer_id links customers<->transactions)",\n'
            ' "high_value_features": ["top 5 specific feature ideas with rationale"],\n'
            ' "data_quality_concerns": ["any issues that could affect feature quality"],\n'
            ' "proceed": true}\n'
            "Return ONLY valid JSON, no markdown formatting."
        )

        tables_str = json.dumps(perception["cleaned_tables"], indent=2, default=str)[
            :5000
        ]
        user_prompt = f"Cleaned tables:\n{tables_str}"

        self.emit_hint("Planning feature engineering strategy...")
        llm_response = await ask_llm(system_prompt, user_prompt)
        plan = parse_llm_json(
            llm_response,
            fallback={"assessment": llm_response[:200], "proceed": True},
        )

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
        self.emit_hint("Running feature engineering subprocess...")
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

        self.emit_hint("Evaluating engineered features...")
        # POST-ACT LLM: Evaluate the features that were actually built
        interpretation = "Feature engineering completed."
        if report:
            feature_summary = {
                "tables_loaded": report.get("loaded_tables", []),
                "output_files": {
                    k: {"rows": report["rows"].get(k, 0), "cols": report["cols"].get(k, 0)}
                    for k in report.get("rows", {})
                },
                "llm_suggested_features": plan.get("high_value_features", []),
                "llm_join_strategy": plan.get("key_join_strategy", ""),
            }

            featured_dir = Path(blackboard.paths["featured_dir"])
            for csv_file in sorted(featured_dir.glob("*.csv")):
                try:
                    import pandas as _pd
                    cols = list(_pd.read_csv(csv_file, nrows=0).columns)
                    feature_summary[f"{csv_file.stem}_columns"] = cols
                except Exception:
                    pass

            eval_prompt = (
                "You are a senior data scientist reviewing feature engineering output. "
                "Analyze what was built and provide a 3-4 sentence evaluation covering:\n"
                "1. Quality assessment of the engineered features\n"
                "2. How well the features cover customer, product, and transaction dimensions\n"
                "3. Any gaps or additional features that would add value\n\n"
                f"Feature engineering results:\n{json.dumps(feature_summary, indent=2, default=str)[:3000]}"
            )

            try:
                interpretation = await ask_llm(
                    "You are a feature engineering specialist evaluating pipeline output.",
                    eval_prompt,
                )
            except Exception as e:
                interpretation = f"Feature evaluation skipped: {e}"

        blackboard.data_state["features"] = {
            "report": report,
            "strategy": plan,
            "interpretation": interpretation,
        }

        self.emit_hint("Storing featured data to database...")
        # Store featured data + report to Supabase
        run_id = blackboard.config.get("run_id")
        if run_id:
            try:
                import pandas as _pd
                from db.store import store_featured_dataset, store_feature_report

                featured_dir = Path(blackboard.paths["featured_dir"])
                for csv_file in sorted(featured_dir.glob("*.csv")):
                    table_name = csv_file.stem  # e.g. customers_features
                    df = _pd.read_csv(csv_file)
                    store_featured_dataset(run_id, table_name, df)

                if report:
                    store_feature_report(run_id, report)
            except Exception as e:
                print(f"[FeatureAgent] Warning: Supabase storage failed: {e}")

        self.log(
            MessageType.DATA_READY,
            {"agent": self.name, "output": "featured_data"},
            recipient="hypothesis",
        )

        return AgentResult(
            agent_id=self.agent_id,
            success=True,
            outputs={
                "feature_report_keys": list(report.keys()),
                "tables_loaded": report.get("loaded_tables", []),
                "output_rows": report.get("rows", {}),
                "output_cols": report.get("cols", {}),
            },
            llm_reasoning=plan.get("assessment", ""),
            llm_decisions=[
                f"Join strategy: {plan.get('key_join_strategy', 'auto-detected')}",
                f"Data concerns: {plan.get('data_quality_concerns', 'none identified')}",
                f"Feature evaluation: {interpretation[:300]}",
            ],
        )
