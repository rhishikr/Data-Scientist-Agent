"""
PipelineOrchestrator: Manages the sequential execution of all agents.

Provides real-time status, agent logs, and LLM decision transparency.
"""
from __future__ import annotations

import shutil
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List

from .base import BaseAgent, MessageType
from .blackboard import SharedBlackboard
from .cleaning_agent import CleaningAgent
from .feature_agent import FeatureAgent
from .hypothesis_agent import HypothesisAgent
from .insights_agent import InsightsAgent
from .kpi_agent import KPIAgent
from .forecast_agent import ForecastAgent
from .action_agent import ActionAgent

from db.store import create_pipeline_run, complete_pipeline_run


@dataclass
class PipelineOrchestrator:
    """
    Orchestrates the multi-agent pipeline.

    Responsibilities:
    1. Initialize agents in execution order
    2. Create and manage the shared blackboard
    3. Execute agents sequentially
    4. Handle errors and decide whether to continue or abort
    5. Provide status updates for frontend consumption
    """

    agents: List[BaseAgent] = field(default_factory=list)
    blackboard: SharedBlackboard = field(default_factory=SharedBlackboard)
    _status_callbacks: List[Callable[[Dict[str, Any]], None]] = field(
        default_factory=list, repr=False
    )

    @classmethod
    def create_default(
        cls, reset: bool = True, alpha: float = 0.05
    ) -> "PipelineOrchestrator":
        """Factory method that creates the standard 7-agent pipeline."""
        project_root = Path(__file__).resolve().parent.parent  # backend/

        # Use system temp dirs for all pipeline data — nothing in the project folder
        blackboard = SharedBlackboard(
            config={"reset": reset, "alpha": alpha},
            paths={
                "project_root": str(project_root),
                "data_dir": tempfile.mkdtemp(prefix="dsa_data_"),
                "raw_dir": tempfile.mkdtemp(prefix="dsa_raw_"),
                "cleaned_dir": tempfile.mkdtemp(prefix="dsa_cleaned_"),
                "featured_dir": tempfile.mkdtemp(prefix="dsa_featured_"),
                "reports_dir": tempfile.mkdtemp(prefix="dsa_reports_"),
                "hypothesis_dir": tempfile.mkdtemp(prefix="dsa_hypothesis_"),
                "insight_dir": tempfile.mkdtemp(prefix="dsa_insights_"),
                "kpi_dir": tempfile.mkdtemp(prefix="dsa_kpi_"),
                "forecast_dir": tempfile.mkdtemp(prefix="dsa_forecast_"),
            },
        )

        agents: List[BaseAgent] = [
            CleaningAgent(),
            FeatureAgent(),
            HypothesisAgent(),
            InsightsAgent(),
            KPIAgent(),
            ForecastAgent(),
            ActionAgent(),
        ]

        return cls(agents=agents, blackboard=blackboard)

    def on_status(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Register a callback for real-time status updates (for SSE)."""
        self._status_callbacks.append(callback)

    def _emit(self, event: Dict[str, Any]) -> None:
        for cb in self._status_callbacks:
            try:
                cb(event)
            except Exception:
                pass

    async def run(self) -> Dict[str, Any]:
        """Execute the full multi-agent pipeline."""
        start = time.time()
        total_agents = len(self.agents)

        # Create a new pipeline run in Supabase
        try:
            run_id = create_pipeline_run()
            self.blackboard.config["run_id"] = run_id
        except Exception as e:
            print(f"[orchestrator] Warning: Could not create pipeline run in Supabase: {e}")
            self.blackboard.config["run_id"] = None

        self._emit(
            {"event": "pipeline_started", "total_agents": total_agents}
        )

        # Download raw data from Supabase into the temp raw_dir
        try:
            from db.raw_store import download_all_raw_to_dir
            download_all_raw_to_dir(self.blackboard.paths["raw_dir"])
            print(f"[orchestrator] Raw data downloaded from Supabase to temp dir")
        except Exception as e:
            print(f"[orchestrator] Warning: Could not download raw data from Supabase: {e}")

        results = {}
        for i, agent in enumerate(self.agents):
            self._emit(
                {
                    "event": "agent_started",
                    "agent_id": agent.agent_id,
                    "agent_name": agent.name,
                    "step": i + 1,
                    "total_steps": total_agents,
                    "progress_pct": int((i / total_agents) * 100),
                }
            )

            result = await agent.run(self.blackboard)
            self.blackboard.set_agent_result(agent.agent_id, result)
            results[agent.agent_id] = result

            # Record LLM decisions globally
            for decision in result.llm_decisions:
                self.blackboard.llm_decisions.append(
                    {"agent": agent.name, "decision": decision}
                )

            self._emit(
                {
                    "event": "agent_completed",
                    "agent_id": agent.agent_id,
                    "agent_name": agent.name,
                    "success": result.success,
                    "duration": result.duration_seconds,
                    "llm_reasoning": result.llm_reasoning,
                    "step": i + 1,
                    "total_steps": total_agents,
                    "progress_pct": int(((i + 1) / total_agents) * 100),
                }
            )

            if not result.success:
                self._emit(
                    {
                        "event": "agent_error",
                        "agent_id": agent.agent_id,
                        "error": result.error,
                    }
                )
                # Log and continue — resilient pipeline

        total_time = time.time() - start

        summary: Dict[str, Any] = {
            "event": "pipeline_complete",
            "total_duration_seconds": round(total_time, 2),
            "agents": {
                aid: {
                    "success": r.success,
                    "duration_seconds": round(r.duration_seconds, 2),
                    "llm_reasoning": r.llm_reasoning,
                    "llm_decisions": r.llm_decisions,
                    "error": r.error,
                }
                for aid, r in results.items()
            },
            "llm_decisions_log": self.blackboard.llm_decisions,
        }

        # Complete the pipeline run in Supabase
        run_id = self.blackboard.config.get("run_id")
        if run_id:
            any_failed = any(not r.success for r in results.values())
            try:
                complete_pipeline_run(
                    run_id=run_id,
                    status="failed" if any_failed else "completed",
                    duration_seconds=total_time,
                    agent_summary=summary.get("agents"),
                    llm_decisions_log=self.blackboard.llm_decisions,
                )
            except Exception as e:
                print(f"[orchestrator] Warning: Could not complete pipeline run in Supabase: {e}")

        summary["run_id"] = run_id
        self._emit(summary)

        # Auto-rebuild RAG vector index with latest pipeline outputs
        try:
            from rag.ingest import rebuild_index
            rebuild_index(Path(__file__).resolve().parents[1])
            print("[orchestrator] RAG vector index rebuilt successfully")
        except Exception as e:
            print(f"[orchestrator] Warning: RAG index rebuild failed: {e}")

        # Clean up all temp directories
        temp_base = tempfile.gettempdir()
        for key in [
            "data_dir", "raw_dir", "cleaned_dir", "featured_dir",
            "reports_dir", "hypothesis_dir", "insight_dir",
            "kpi_dir", "forecast_dir",
        ]:
            p = self.blackboard.paths.get(key, "")
            if p and Path(p).exists() and p.startswith(temp_base):
                shutil.rmtree(p, ignore_errors=True)

        return summary
