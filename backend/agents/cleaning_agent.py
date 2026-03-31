"""
CleaningAgent: Wraps pipeline/cleaning/clean_folder.py

LLM injection point: The LLM examines the raw data profile and decides
cleaning strategy parameters (e.g., outlier method, missing value strategy).
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


class CleaningAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_id="cleaning",
            name="Data Cleaning Agent",
            description="Analyzes raw data quality and applies cleaning strategies",
        )

    async def perceive(self, blackboard: SharedBlackboard) -> Dict[str, Any]:
        """Scan raw CSVs for basic quality signals."""
        import pandas as pd

        self.emit_hint("Scanning raw CSV files...")
        raw_dir = Path(blackboard.paths["raw_dir"])
        csv_files = sorted(raw_dir.glob("*.csv"))

        file_profiles = []
        for f in csv_files:
            try:
                df = pd.read_csv(f, nrows=100)
                profile = {
                    "file": f.name,
                    "rows_sampled": len(df),
                    "columns": list(df.columns),
                    "null_pct": {
                        col: round(float(df[col].isna().mean()), 3)
                        for col in df.columns
                    },
                    "dtypes": {col: str(df[col].dtype) for col in df.columns},
                }
                file_profiles.append(profile)
            except Exception as e:
                file_profiles.append({"file": f.name, "error": str(e)})

        return {
            "raw_dir": str(raw_dir),
            "num_files": len(csv_files),
            "file_profiles": file_profiles,
        }

    async def reason(self, perception: Dict[str, Any]) -> Dict[str, Any]:
        """Ask the LLM to assess data quality and recommend cleaning strategy."""
        system_prompt = (
            "You are an expert data engineer. Given a profile of raw CSV files "
            "(column names, null percentages, data types), provide a brief cleaning "
            "strategy assessment. Return a JSON object with:\n"
            '{"assessment": "1-2 sentence summary of data quality",\n'
            ' "high_null_columns": ["columns with >30% nulls that need attention"],\n'
            ' "recommended_outlier_method": "iqr" or "zscore",\n'
            ' "concerns": ["any data quality concerns"],\n'
            ' "proceed": true}\n'
            "Return ONLY valid JSON, no markdown."
        )

        profiles_str = json.dumps(perception["file_profiles"], indent=2)[:3000]
        user_prompt = (
            f"Raw data profile ({perception['num_files']} files):\n{profiles_str}"
        )

        self.emit_hint("Asking LLM for cleaning strategy...")
        llm_response = await ask_llm(system_prompt, user_prompt)

        try:
            plan = json.loads(llm_response)
        except json.JSONDecodeError:
            plan = {
                "assessment": llm_response[:200],
                "recommended_outlier_method": "iqr",
                "proceed": True,
            }

        self.log(
            MessageType.LLM_DECISION,
            {
                "agent": self.name,
                "decision_type": "cleaning_strategy",
                "decision": plan,
            },
        )
        return plan

    async def act(
        self, plan: Dict[str, Any], blackboard: SharedBlackboard
    ) -> AgentResult:
        """Execute the existing clean_folder.py subprocess."""
        self.emit_hint("Running data cleaner subprocess...")
        project_root = Path(blackboard.paths["project_root"])
        raw_dir = blackboard.paths["raw_dir"]
        cleaned_dir = blackboard.paths["cleaned_dir"]
        reports_dir = blackboard.paths["reports_dir"]
        clean_script = project_root / "pipeline" / "cleaning" / "clean_folder.py"

        cmd = [
            sys.executable,
            str(clean_script),
            "--input_dir", raw_dir,
            "--output_dir", cleaned_dir,
            "--reports_dir", reports_dir,
        ]

        p = subprocess.run(
            cmd,
            cwd=str(clean_script.parent),
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
                llm_decisions=[
                    f"Strategy: {plan.get('recommended_outlier_method', 'iqr')}"
                ],
            )

        # Read the cleaning report to store in blackboard
        report_path = Path(reports_dir) / "cleaning_report.json"
        report: dict = {}
        if report_path.exists():
            report = json.loads(report_path.read_text(encoding="utf-8"))

        blackboard.data_state["cleaning"] = {
            "report": report,
            "strategy": plan,
            "files_cleaned": list(Path(cleaned_dir).glob("*.csv")),
        }

        self.emit_hint("Uploading cleaned data to database...")
        # Store cleaned data + report to Supabase
        run_id = blackboard.config.get("run_id")
        if run_id:
            try:
                import pandas as _pd
                from db.store import store_cleaned_dataset, store_cleaning_report

                for csv_file in sorted(Path(cleaned_dir).glob("*.csv")):
                    table_name = csv_file.stem.replace("_cleaned", "").replace("_dirty", "")
                    df = _pd.read_csv(csv_file)
                    store_cleaned_dataset(run_id, table_name, df)

                if report:
                    store_cleaning_report(run_id, report)
            except Exception as e:
                print(f"[CleaningAgent] Warning: Supabase storage failed: {e}")

        self.log(
            MessageType.DATA_READY,
            {"agent": self.name, "output": "cleaned_data"},
            recipient="features",
        )

        return AgentResult(
            agent_id=self.agent_id,
            success=True,
            outputs={"cleaning_report_keys": list(report.keys())},
            llm_reasoning=plan.get("assessment", ""),
            llm_decisions=[
                f"Outlier method: {plan.get('recommended_outlier_method', 'iqr')}",
                f"Concerns: {plan.get('concerns', 'none')}",
            ],
        )
