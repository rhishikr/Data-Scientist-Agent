"""
PipelineOrchestrator: Manages the sequential execution of all agents.

Provides real-time status, agent logs, and LLM decision transparency.
"""
from __future__ import annotations

import asyncio
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


def _run_agent_in_thread(agent, blackboard):
    """Run an async agent in a dedicated event loop on a background thread.

    Agents contain blocking calls (subprocess.run, pd.read_csv, sync HTTP).
    Running them in a thread prevents starving the main asyncio event loop,
    keeping all other API endpoints responsive during pipeline execution.
    """
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(agent.run(blackboard))
    finally:
        loop.close()


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

        # Create a new pipeline run in Supabase (sync call → run in thread)
        try:
            run_id = await asyncio.to_thread(create_pipeline_run)
            self.blackboard.config["run_id"] = run_id
        except Exception as e:
            print(f"[orchestrator] Warning: Could not create pipeline run in Supabase: {e}")
            self.blackboard.config["run_id"] = None

        from datetime import datetime, timezone
        started_at = datetime.now(timezone.utc).isoformat()
        self._emit(
            {"event": "pipeline_started", "total_agents": total_agents, "run_id": run_id, "started_at": started_at}
        )

        # Download raw data from Supabase into the temp raw_dir (sync I/O → thread)
        self._emit({"event": "pipeline_preparing", "message": "Downloading raw data from database..."})
        try:
            from db.raw_store import download_all_raw_to_dir
            await asyncio.to_thread(download_all_raw_to_dir, self.blackboard.paths["raw_dir"])
            print(f"[orchestrator] Raw data downloaded from Supabase to temp dir")
            self._emit({"event": "pipeline_preparing", "message": "Raw data ready — starting agents..."})
        except Exception as e:
            print(f"[orchestrator] Warning: Could not download raw data from Supabase: {e}")
            self._emit({"event": "pipeline_preparing", "message": "Data download issue — proceeding with available data..."})

        results = {}
        try:
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

                # Inject phase & hint callbacks so the agent can emit
                # granular SSE events from within its background thread.
                agent._phase_callback = lambda aid, phase: self._emit(
                    {"event": "agent_phase_changed", "agent_id": aid, "phase": phase}
                )
                agent._hint_callback = lambda aid, msg: self._emit(
                    {"event": "agent_activity_hint", "agent_id": aid, "message": msg}
                )

                result = await asyncio.to_thread(_run_agent_in_thread, agent, self.blackboard)
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

        except asyncio.CancelledError:
            print("[orchestrator] Pipeline cancelled — cleaning up temp directories")
            self._cleanup_temp_dirs()
            raise

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
                await asyncio.to_thread(
                    complete_pipeline_run,
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

        # Auto-rebuild RAG vector index with latest pipeline outputs (may do heavy I/O)
        try:
            from rag.ingest import rebuild_index
            await asyncio.to_thread(rebuild_index, Path(__file__).resolve().parents[1], run_id=run_id)
            print("[orchestrator] RAG vector index rebuilt successfully")
        except Exception as e:
            print(f"[orchestrator] Warning: RAG index rebuild failed: {e}")

        self._cleanup_temp_dirs()

        return summary

    def _cleanup_temp_dirs(self) -> None:
        """Remove all temporary directories created for this pipeline run."""
        temp_base = tempfile.gettempdir()
        for key in [
            "data_dir", "raw_dir", "cleaned_dir", "featured_dir",
            "reports_dir", "hypothesis_dir", "insight_dir",
            "kpi_dir", "forecast_dir",
        ]:
            p = self.blackboard.paths.get(key, "")
            if p and Path(p).exists() and p.startswith(temp_base):
                shutil.rmtree(p, ignore_errors=True)
