from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import sys
from asyncio import Queue
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse

from pipeline.hypothesis.runner import run_hypothesis_agent
from pipeline.insights.runner import run_insights
from pipeline.kpi.runner import run_kpi_snapshot
from pipeline.kpi.io import DataPaths, read_json
from pipeline.forecast.runner import run_forecasting
from pipeline.forecast.io import ForecastPaths

from rag.api import router as rag_router
from agents.orchestrator import PipelineOrchestrator

from db.store import (
    get_latest_kpi_snapshot as db_get_latest_kpi,
    get_latest_forecast_snapshot as db_get_latest_forecast,
    get_latest_insight_snapshot as db_get_latest_insight,
    get_latest_hypothesis_snapshot as db_get_latest_hypothesis,
    get_run_kpi_snapshot as db_get_run_kpi,
    get_run_forecast_snapshot as db_get_run_forecast,
    get_run_insight_snapshot as db_get_run_insight,
    get_run_hypothesis_snapshot as db_get_run_hypothesis,
    get_pipeline_runs,
    get_latest_run_id,
    get_run_snapshots,
    get_cleaned_datasets,
    get_featured_datasets,
    get_cleaning_report,
    get_feature_report,
    get_signed_url,
)


# -----------------------------------------------------------------------------
# Helpers (kept for backward-compat individual /run endpoints)
# -----------------------------------------------------------------------------
def rm_dir(p: Path):
    if p.exists():
        shutil.rmtree(p)


def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)


def run_cmd(cmd: list[str], cwd: Path):
    print(f"\nRunning: {' '.join(cmd)}")
    p = subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    if p.returncode != 0:
        raise RuntimeError(p.stderr or p.stdout)
    if p.stdout:
        print(p.stdout.strip())


# -----------------------------------------------------------------------------
# Legacy pipeline (kept for backward compat; agents are the primary path now)
# -----------------------------------------------------------------------------
def run_pipeline(reset: bool = True, alpha: float = 0.05):
    print("\n=== STARTING FULL PIPELINE (legacy) ===")

    project_root = Path(__file__).resolve().parent  # backend/
    data_dir = project_root / "data"

    raw_dir = data_dir / "raw"
    cleaned_dir = data_dir / "cleaned_data"
    featured_dir = data_dir / "featured_data"
    reports_dir = data_dir / "reports"

    hypothesis_dir = data_dir / "hypothesis_outputs"
    insight_dir = data_dir / "insight_outputs"
    kpi_dir = data_dir / "kpi_outputs"
    forecast_dir = data_dir / "forecast_outputs"

    clean_script = project_root / "pipeline" / "cleaning" / "clean_folder.py"
    feature_script = project_root / "pipeline" / "features" / "feature_folder.py"

    if not raw_dir.exists():
        raise RuntimeError(f"Missing raw data directory: {raw_dir}")

    # Reset output folders
    if reset:
        print("Resetting output folders...")
        for p in [
            cleaned_dir,
            featured_dir,
            reports_dir,
            hypothesis_dir,
            insight_dir,
            kpi_dir,
            forecast_dir,
        ]:
            rm_dir(p)

    for p in [
        cleaned_dir,
        featured_dir,
        reports_dir,
        hypothesis_dir,
        insight_dir,
        kpi_dir,
        forecast_dir,
    ]:
        ensure_dir(p)

    # 1. CLEANING
    print("\n--- CLEANING ---")
    run_cmd(
        [
            sys.executable,
            str(clean_script),
            "--input_dir",
            str(raw_dir),
            "--output_dir",
            str(cleaned_dir),
            "--reports_dir",
            str(reports_dir),
        ],
        cwd=clean_script.parent,
    )

    # 2. FEATURE ENGINEERING
    print("\n--- FEATURE ENGINEERING ---")
    run_cmd(
        [
            sys.executable,
            str(feature_script),
            "--input_dir",
            str(cleaned_dir),
            "--output_dir",
            str(featured_dir),
            "--reports_dir",
            str(reports_dir),
        ],
        cwd=feature_script.parent,
    )

    # 3. HYPOTHESIS TESTING
    print("\n--- HYPOTHESIS TESTING ---")
    run_hypothesis_agent(alpha=alpha)

    # 4. INSIGHTS
    print("\n--- INSIGHTS ---")
    run_insights(project_root)

    # 5. KPI SNAPSHOT
    print("\n--- KPI SNAPSHOT ---")
    run_kpi_snapshot(DataPaths.default())

    # 6. FORECASTING
    print("\n--- FORECASTING ---")
    run_forecasting(ForecastPaths.default())

    print("\n=== PIPELINE COMPLETE ===")


# -----------------------------------------------------------------------------
# FastAPI app
# -----------------------------------------------------------------------------
app = FastAPI(title="AI Data Scientist Agent API")

# CORS (origins configured via ALLOWED_ORIGINS in .env)
_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount your RAG endpoints if you have them
app.include_router(rag_router, prefix="/api/rag", tags=["rag"])


# -----------------------------------------------------------------------------
# Multi-agent pipeline state
# -----------------------------------------------------------------------------
_pipeline_status: dict = {}
_pipeline_running: bool = False


# -----------------------------------------------------------------------------
# Run multi-agent pipeline on server start
# -----------------------------------------------------------------------------
@app.on_event("startup")
async def startup_run_pipeline():
    """
    When the FastAPI server starts, run the multi-agent pipeline automatically.
    You can control behavior via env vars:

    - RUN_PIPELINE_ON_START=1 (default) to run
    - PIPELINE_RESET=1 (default) to reset outputs each start
    - USE_AGENTS=1 (default) to use multi-agent pipeline
    - USE_AGENTS=0 to fall back to legacy sequential pipeline
    """
    run_on_start = os.getenv("RUN_PIPELINE_ON_START", "0") == "1"
    if not run_on_start:
        print("RUN_PIPELINE_ON_START=0 -> skipping pipeline on startup.")
        return

    reset = os.getenv("PIPELINE_RESET", "1") == "1"
    alpha_str = os.getenv("HYPOTHESIS_ALPHA", "0.05")
    try:
        alpha = float(alpha_str)
    except ValueError:
        alpha = 0.05

    use_agents = os.getenv("USE_AGENTS", "1") == "1"

    if use_agents:
        global _pipeline_status, _pipeline_running
        try:
            print("\n=== STARTING MULTI-AGENT PIPELINE ===")
            orchestrator = PipelineOrchestrator.create_default(
                reset=reset, alpha=alpha
            )
            _pipeline_running = True
            _pipeline_status = await orchestrator.run()
            _pipeline_running = False
            print("\n=== MULTI-AGENT PIPELINE COMPLETE ===")
        except Exception as e:
            _pipeline_running = False
            _pipeline_status = {"error": str(e)}
            print(f"[startup] Multi-agent pipeline failed: {e}")
    else:
        try:
            run_pipeline(reset=reset, alpha=alpha)
        except Exception as e:
            print(f"[startup] Legacy pipeline failed: {e}")


# -----------------------------------------------------------------------------
# Multi-agent pipeline endpoints
# -----------------------------------------------------------------------------
@app.post("/api/pipeline/run")
async def run_pipeline_endpoint(reset: bool = True, alpha: float = 0.05):
    """Trigger the multi-agent pipeline manually."""
    global _pipeline_status, _pipeline_running
    if _pipeline_running:
        return {"error": "Pipeline is already running"}

    orchestrator = PipelineOrchestrator.create_default(reset=reset, alpha=alpha)
    _pipeline_running = True
    try:
        _pipeline_status = await orchestrator.run()
    finally:
        _pipeline_running = False
    return _pipeline_status


@app.get("/api/pipeline/status")
def get_pipeline_status():
    """Get current pipeline execution status and all agent decisions."""
    return {
        "running": _pipeline_running,
        "status": _pipeline_status,
    }


@app.get("/api/pipeline/stream")
async def stream_pipeline(reset: bool = True, alpha: float = 0.05):
    """
    SSE endpoint for real-time pipeline status updates.
    Frontend connects via EventSource for live progress visualization.
    """
    global _pipeline_running
    if _pipeline_running:
        return {"error": "Pipeline is already running"}

    queue: Queue = Queue()

    def on_status(event: dict):
        queue.put_nowait(event)

    orchestrator = PipelineOrchestrator.create_default(reset=reset, alpha=alpha)
    orchestrator.on_status(on_status)

    async def event_generator():
        global _pipeline_status, _pipeline_running
        _pipeline_running = True
        task = asyncio.create_task(orchestrator.run())

        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=1.0)
                    yield f"data: {json.dumps(event, default=str)}\n\n"
                    if event.get("event") == "pipeline_complete":
                        break
                except asyncio.TimeoutError:
                    yield f"data: {json.dumps({'event': 'heartbeat'})}\n\n"

            result = await task
            _pipeline_status = result
        finally:
            _pipeline_running = False

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/pipeline/decisions")
def get_llm_decisions():
    """
    Returns all LLM decisions made during the pipeline.
    Transparency endpoint for academic demonstration.
    """
    return _pipeline_status.get("llm_decisions_log", [])


# -----------------------------------------------------------------------------
# Small helper: read JSON safely
# -----------------------------------------------------------------------------
def _read_json_file(path: Path) -> dict:
    payload = read_json(str(path))
    if payload:
        return payload
    return {"error": f"{path.name} not found. Run pipeline or /api/*/run first."}


# -----------------------------------------------------------------------------
# Endpoints (RUN) — individual stage triggers (kept for backward compat)
# -----------------------------------------------------------------------------
@app.get("/api/hypothesis/run")
def run_hypothesis():
    """
    Run hypothesis tests using:
    - backend/data/cleaned_data/*.csv
    - backend/data/featured_data/*.csv

    Saves to:
    - backend/data/hypothesis_outputs/hypothesis_results.json
    - backend/data/hypothesis_outputs/hypothesis_results.csv
    """
    return run_hypothesis_agent(alpha=0.05)


@app.get("/api/insights/run")
def run_insights_endpoint():
    """
    Run insight generation using:
    - backend/data/featured_data/*.csv
    - backend/data/hypothesis_outputs/hypothesis_results.json (preferred) or .csv

    Saves to:
    - backend/data/insight_outputs/insights.json
    - backend/data/insight_outputs/insights.csv
    """
    project_root = Path(__file__).resolve().parent  # backend/
    bundle = run_insights(project_root)
    return bundle.to_dict() if hasattr(bundle, "to_dict") else {"ok": True}


@app.get("/api/kpi/run")
def run_kpis():
    """
    Computes KPI snapshot and writes outputs to:
      backend/data/kpi_outputs/*
    """
    return run_kpi_snapshot(DataPaths.default())


@app.get("/api/forecast/run")
def run_forecast():
    """
    Trains/loads forecasting models and writes outputs to:
      backend/data/forecast_outputs/*
    Also saves model artifacts to:
      backend/models/*
    """
    return run_forecasting(ForecastPaths.default())


# -----------------------------------------------------------------------------
# Endpoints (SNAPSHOTS / READ OUTPUTS) — now backed by Supabase
# -----------------------------------------------------------------------------
@app.get("/api/kpi/snapshot")
def get_kpi_snapshot(run_id: Optional[str] = None):
    """Returns KPI snapshot from Supabase (latest or for a specific run)."""
    if run_id:
        return db_get_run_kpi(run_id)
    return db_get_latest_kpi()


@app.get("/api/forecast/snapshot")
def get_forecast_snapshot(run_id: Optional[str] = None):
    """Returns forecast snapshot from Supabase."""
    if run_id:
        return db_get_run_forecast(run_id)
    return db_get_latest_forecast()


@app.get("/api/insights/snapshot")
def get_insights_snapshot(run_id: Optional[str] = None):
    """Returns insights snapshot from Supabase."""
    if run_id:
        return db_get_run_insight(run_id)
    return db_get_latest_insight()


@app.get("/api/hypothesis/snapshot")
def get_hypothesis_snapshot(run_id: Optional[str] = None):
    """Returns hypothesis results from Supabase."""
    if run_id:
        return db_get_run_hypothesis(run_id)
    return db_get_latest_hypothesis()


# -----------------------------------------------------------------------------
# New endpoints: Runs, Cleaned/Featured data
# -----------------------------------------------------------------------------
@app.get("/api/runs")
def list_runs():
    """Returns list of all pipeline runs with timestamps and status."""
    return get_pipeline_runs()


@app.get("/api/runs/{run_id}")
def get_run_detail(run_id: str):
    """Returns all snapshots for a specific pipeline run."""
    return get_run_snapshots(run_id)


@app.get("/api/cleaned-data")
def get_cleaned_data(run_id: Optional[str] = None):
    """Returns cleaned dataset previews + column stats + download URLs."""
    rid = run_id or get_latest_run_id()
    if not rid:
        return {"error": "No completed pipeline runs found.", "tables": [], "report": {}}
    tables = get_cleaned_datasets(rid)
    for t in tables:
        t["download_url"] = get_signed_url(t["storage_path"])
    return {"run_id": rid, "tables": tables, "report": get_cleaning_report(rid)}


@app.get("/api/featured-data")
def get_featured_data(run_id: Optional[str] = None):
    """Returns featured dataset previews + column stats + download URLs."""
    rid = run_id or get_latest_run_id()
    if not rid:
        return {"error": "No completed pipeline runs found.", "tables": [], "report": {}}
    tables = get_featured_datasets(rid)
    for t in tables:
        t["download_url"] = get_signed_url(t["storage_path"])
    return {"run_id": rid, "tables": tables, "report": get_feature_report(rid)}


# -----------------------------------------------------------------------------
# Entry point: run the API server
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    # When you run: python app.py
    # -> it starts FastAPI, and the multi-agent pipeline runs automatically.
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
