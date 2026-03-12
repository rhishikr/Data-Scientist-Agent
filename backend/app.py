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

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.responses import StreamingResponse

from pipeline.hypothesis.runner import run_hypothesis_agent
from pipeline.insights.runner import run_insights
from pipeline.kpi.runner import run_kpi_snapshot
from pipeline.kpi.io import DataPaths, read_json
from pipeline.forecast.runner import run_forecasting
from pipeline.forecast.io import ForecastPaths

from rag.api import router as rag_router
from agents.orchestrator import PipelineOrchestrator

import math

import pandas as pd

from db.store import (
    get_latest_kpi_snapshot as db_get_latest_kpi,
    get_latest_forecast_snapshot as db_get_latest_forecast,
    get_latest_insight_snapshot as db_get_latest_insight,
    get_latest_hypothesis_snapshot as db_get_latest_hypothesis,
    get_run_kpi_snapshot as db_get_run_kpi,
    get_run_forecast_snapshot as db_get_run_forecast,
    get_run_insight_snapshot as db_get_run_insight,
    get_run_hypothesis_snapshot as db_get_run_hypothesis,
    get_latest_ai_analysis as db_get_latest_ai_analysis,
    get_run_ai_analysis as db_get_run_ai_analysis,
    store_ai_analysis as db_store_ai_analysis,
    store_comparison_ai as db_store_comparison_ai,
    get_comparison_ai as db_get_comparison_ai,
    get_latest_action_plan_snapshot as db_get_latest_action_plan,
    get_run_action_plan_snapshot as db_get_run_action_plan,
    upsert_prescription_status as db_upsert_prescription_status,
    get_prescription_statuses as db_get_prescription_statuses,
    delete_pipeline_run,
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
    import tempfile
    import shutil
    from db.raw_store import download_all_raw_to_dir

    print("\n=== STARTING FULL PIPELINE (legacy) ===")

    project_root = Path(__file__).resolve().parent  # backend/

    # All intermediate dirs use system temp
    raw_dir = Path(tempfile.mkdtemp(prefix="dsa_legacy_raw_"))
    cleaned_dir = Path(tempfile.mkdtemp(prefix="dsa_legacy_cleaned_"))
    featured_dir = Path(tempfile.mkdtemp(prefix="dsa_legacy_featured_"))
    reports_dir = Path(tempfile.mkdtemp(prefix="dsa_legacy_reports_"))
    hypothesis_dir = Path(tempfile.mkdtemp(prefix="dsa_legacy_hypothesis_"))
    insight_dir = Path(tempfile.mkdtemp(prefix="dsa_legacy_insight_"))
    kpi_dir = Path(tempfile.mkdtemp(prefix="dsa_legacy_kpi_"))
    forecast_dir = Path(tempfile.mkdtemp(prefix="dsa_legacy_forecast_"))

    temp_dirs = [raw_dir, cleaned_dir, featured_dir, reports_dir,
                 hypothesis_dir, insight_dir, kpi_dir, forecast_dir]

    clean_script = project_root / "pipeline" / "cleaning" / "clean_folder.py"
    feature_script = project_root / "pipeline" / "features" / "feature_folder.py"

    try:
        # Download raw data from Supabase
        print("Downloading raw data from Supabase...")
        download_all_raw_to_dir(str(raw_dir))

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
        run_hypothesis_agent(
            alpha=alpha,
            cleaned_dir=str(cleaned_dir),
            featured_dir=str(featured_dir),
            out_dir=str(hypothesis_dir),
        )

        # 4. INSIGHTS
        print("\n--- INSIGHTS ---")
        from pipeline.insights.io import DataPaths as InsightDataPaths
        insight_paths = InsightDataPaths(
            base_dir=project_root,
            _cleaned_dir=cleaned_dir,
            _featured_dir=featured_dir,
            _hypothesis_dir=hypothesis_dir,
            _insights_dir=insight_dir,
        )
        run_insights(project_root, data_paths=insight_paths)

        # 5. KPI SNAPSHOT
        print("\n--- KPI SNAPSHOT ---")
        from pipeline.kpi.io import DataPaths as KpiDataPaths
        kpi_paths = KpiDataPaths.from_blackboard({
            "project_root": str(project_root),
            "cleaned_dir": str(cleaned_dir),
            "featured_dir": str(featured_dir),
            "hypothesis_dir": str(hypothesis_dir),
            "insight_dir": str(insight_dir),
            "kpi_dir": str(kpi_dir),
            "forecast_dir": str(forecast_dir),
        })
        run_kpi_snapshot(kpi_paths)

        # 6. FORECASTING
        print("\n--- FORECASTING ---")
        forecast_paths = ForecastPaths.from_blackboard({
            "project_root": str(project_root),
            "cleaned_dir": str(cleaned_dir),
            "featured_dir": str(featured_dir),
            "hypothesis_dir": str(hypothesis_dir),
            "insight_dir": str(insight_dir),
            "kpi_dir": str(kpi_dir),
            "forecast_dir": str(forecast_dir),
        })
        run_forecasting(forecast_paths)

        print("\n=== PIPELINE COMPLETE ===")
    finally:
        # Clean up temp dirs
        for d in temp_dirs:
            try:
                shutil.rmtree(d, ignore_errors=True)
            except Exception:
                pass


# -----------------------------------------------------------------------------
# Multi-agent pipeline state
# -----------------------------------------------------------------------------
_pipeline_status: dict = {}
_pipeline_running: bool = False


# -----------------------------------------------------------------------------
# Lifespan: run multi-agent pipeline on server start
# -----------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    When the FastAPI server starts, run the multi-agent pipeline automatically.
    You can control behavior via env vars:

    - RUN_PIPELINE_ON_START=1 (default) to run
    - PIPELINE_RESET=1 (default) to reset outputs each start
    - USE_AGENTS=1 (default) to use multi-agent pipeline
    - USE_AGENTS=0 to fall back to legacy sequential pipeline
    """
    global _pipeline_status, _pipeline_running

    run_on_start = os.getenv("RUN_PIPELINE_ON_START", "0") == "1"
    if not run_on_start:
        print("RUN_PIPELINE_ON_START=0 -> skipping pipeline on startup.")
    else:
        reset = os.getenv("PIPELINE_RESET", "1") == "1"
        alpha_str = os.getenv("HYPOTHESIS_ALPHA", "0.05")
        try:
            alpha = float(alpha_str)
        except ValueError:
            alpha = 0.05

        use_agents = os.getenv("USE_AGENTS", "1") == "1"

        if use_agents:
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

    yield


# -----------------------------------------------------------------------------
# FastAPI app
# -----------------------------------------------------------------------------
app = FastAPI(title="AI Data Scientist Agent API", lifespan=lifespan)

# CORS (origins configured via ALLOWED_ORIGINS in .env)
_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API key protection – reject requests without valid key
_API_SECRET = os.getenv("API_SECRET_KEY", "")
_PUBLIC_PATHS = {"/docs", "/openapi.json", "/redoc"}
_allowed_origins = [o.strip() for o in _origins.split(",") if o.strip()]

@app.middleware("http")
async def api_key_guard(request: Request, call_next):
    if request.method == "OPTIONS":          # CORS preflight
        return await call_next(request)
    if request.url.path in _PUBLIC_PATHS:    # Swagger / docs
        return await call_next(request)
    key = request.headers.get("X-API-Key") or request.query_params.get("api_key")
    if _API_SECRET and key != _API_SECRET:
        # Must include CORS headers so the browser can read the 403 response
        origin = request.headers.get("origin", "")
        headers = {}
        if origin in _allowed_origins:
            headers["Access-Control-Allow-Origin"] = origin
            headers["Access-Control-Allow-Credentials"] = "true"
        return JSONResponse(status_code=403, content={"detail": "Forbidden"}, headers=headers)
    return await call_next(request)

# Mount your RAG endpoints if you have them
app.include_router(rag_router, prefix="/api/rag", tags=["rag"])


# -----------------------------------------------------------------------------
# Raw data management endpoints (Settings page)
# -----------------------------------------------------------------------------
@app.get("/api/data/status")
async def data_status():
    """Get row counts for all raw data tables."""
    try:
        from db.raw_store import get_raw_data_stats
        stats = get_raw_data_stats()
        return {"success": True, "stats": stats}
    except Exception as e:
        return {"success": False, "message": str(e), "stats": {}}


@app.post("/api/data/generate")
async def data_generate():
    """Generate fresh synthetic data and store in Supabase."""
    try:
        import sys as _sys
        _sys.path.insert(0, os.path.join(os.path.dirname(__file__), "scripts"))
        from generate_synthetic_data import generate_all_data
        stats = generate_all_data(local=False)
        return {"success": True, "message": "Data generated successfully", "stats": stats}
    except Exception as e:
        return {"success": False, "message": str(e), "stats": {}}


@app.post("/api/data/update")
async def data_update(days: int = 7, scenario: str = "organic-growth"):
    """Simulate a data update with the given scenario."""
    try:
        import sys as _sys
        _sys.path.insert(0, os.path.join(os.path.dirname(__file__), "scripts"))
        from simulate_update import run_update
        summary = run_update(days=days, scenario=scenario, local=False)
        return {"success": True, "message": f"{days}-day [{scenario}] update applied", "stats": summary}
    except Exception as e:
        return {"success": False, "message": str(e), "stats": {}}


@app.delete("/api/data/delete")
async def data_delete():
    """Delete all raw data from Supabase."""
    try:
        from db.raw_store import delete_all_raw_data
        deleted = delete_all_raw_data()
        total = sum(deleted.values())
        return {"success": True, "message": f"Deleted {total} total rows", "stats": deleted}
    except Exception as e:
        return {"success": False, "message": str(e), "stats": {}}


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


@app.get("/api/runs/compare")
def compare_runs(current: Optional[str] = None, previous: Optional[str] = None):
    """Compare KPI snapshots between two runs. Returns deltas for all KPI cards."""
    # Load current snapshot
    current_snap = _load_kpi_snapshot(current)
    if not current_snap:
        return _safe_json({"error": "No current KPI snapshot found", "deltas": []})

    # Load previous snapshot
    prev_snap = None
    if previous:
        prev_snap = _load_kpi_snapshot(previous)
    else:
        # Try to get the second-most-recent run from Supabase
        try:
            runs = get_pipeline_runs()
            if isinstance(runs, list) and len(runs) >= 2:
                completed = [r for r in runs if r.get("status") == "completed"]
                if len(completed) >= 2:
                    prev_run_id = completed[1].get("id")
                    if prev_run_id:
                        prev_snap = _load_kpi_snapshot(prev_run_id)
        except Exception:
            pass

    if not prev_snap:
        return _safe_json({
            "current_snapshot": {
                "generated_at": current_snap.get("meta", {}).get("generated_at"),
                "cards": current_snap.get("cards", []),
            },
            "previous_snapshot": None,
            "deltas": [],
            "message": "No previous run available for comparison",
        })

    # Compute deltas for every card
    current_cards = {c["id"]: c for c in current_snap.get("cards", []) if isinstance(c, dict)}
    prev_cards = {c["id"]: c for c in prev_snap.get("cards", []) if isinstance(c, dict)}

    deltas = []
    for card_id, card in current_cards.items():
        cur_val = card.get("value")
        prev_card = prev_cards.get(card_id)
        prev_val = prev_card.get("value") if prev_card else None

        # Skip non-numeric values
        if not isinstance(cur_val, (int, float)) or (prev_val is not None and not isinstance(prev_val, (int, float))):
            continue

        if prev_val is None:
            direction = "new"
            abs_change = None
            pct_change = None
        else:
            abs_change = cur_val - prev_val
            pct_change = abs_change / prev_val if prev_val != 0 else None
            if abs_change > 0:
                direction = "up"
            elif abs_change < 0:
                direction = "down"
            else:
                direction = "stable"

        deltas.append({
            "id": card_id,
            "title": card.get("title", ""),
            "group": card.get("group", ""),
            "format": card.get("format", "number"),
            "current_value": cur_val,
            "previous_value": prev_val,
            "absolute_change": abs_change,
            "percent_change": pct_change,
            "direction": direction,
        })

    # ---- Insight comparison ----
    resolved_issues = []
    new_risks = []
    try:
        current_insight_snap = None
        prev_insight_snap = None

        # Load current insights
        if current:
            current_insight_snap = db_get_run_insight(current)
        else:
            current_insight_snap = db_get_latest_insight()

        # Load previous insights
        if previous:
            prev_insight_snap = db_get_run_insight(previous)
        elif prev_snap:
            # We already found the previous run ID above, reuse it
            try:
                runs = get_pipeline_runs()
                completed = [r for r in runs if r.get("status") == "completed"]
                if len(completed) >= 2:
                    prev_run_id = completed[1].get("id")
                    if prev_run_id:
                        prev_insight_snap = db_get_run_insight(prev_run_id)
            except Exception:
                pass

        current_insights = []
        prev_insights = []
        if current_insight_snap:
            current_insights = current_insight_snap.get("insights", [])
            if not isinstance(current_insights, list):
                current_insights = []
        if prev_insight_snap:
            prev_insights = prev_insight_snap.get("insights", [])
            if not isinstance(prev_insights, list):
                prev_insights = []

        # Build title sets for comparison
        current_titles = {i.get("title", "").lower().strip() for i in current_insights if i.get("title")}
        prev_titles = {i.get("title", "").lower().strip() for i in prev_insights if i.get("title")}

        # Resolved: were in previous (high/medium severity) but not in current
        for ins in prev_insights:
            title = (ins.get("title") or "").lower().strip()
            severity = ins.get("severity", "low")
            if severity in ("high", "medium") and title and title not in current_titles:
                resolved_issues.append({
                    "title": ins.get("title", ""),
                    "severity": severity,
                    "description": ins.get("description", ""),
                })

        # New risks: in current (high/medium severity) but not in previous
        for ins in current_insights:
            title = (ins.get("title") or "").lower().strip()
            severity = ins.get("severity", "low")
            if severity in ("high", "medium") and title and title not in prev_titles:
                new_risks.append({
                    "title": ins.get("title", ""),
                    "severity": severity,
                    "description": ins.get("description", ""),
                })
    except Exception:
        pass

    # ---- Prescription impact ----
    completed_prescriptions = []
    try:
        # Get previous run's action plan to find prescriptions
        prev_action_plan = None
        prev_run_id_for_rx = previous
        if not prev_run_id_for_rx:
            try:
                runs = get_pipeline_runs()
                completed_runs = [r for r in runs if r.get("status") == "completed"]
                if len(completed_runs) >= 2:
                    prev_run_id_for_rx = completed_runs[1].get("id")
            except Exception:
                pass

        if prev_run_id_for_rx:
            prev_action_plan = db_get_run_action_plan(prev_run_id_for_rx)
            if prev_action_plan:
                # Get prescription statuses
                statuses = db_get_prescription_statuses(prev_run_id_for_rx)
                status_map = {s["prescription_id"]: s["status"] for s in statuses}

                prescriptions = prev_action_plan.get("prescriptions", [])
                for rx in prescriptions:
                    rx_id = rx.get("id", "")
                    rx_status = status_map.get(rx_id, rx.get("status", "pending"))
                    if rx_status == "done":
                        # Find related KPI deltas for this prescription
                        related_deltas = []
                        rx_category = rx.get("category", "")
                        # Map prescription category to KPI group
                        cat_to_group = {
                            "inventory": "Inventory",
                            "customer": "Customers",
                            "revenue": "Revenue",
                            "marketing": "Marketing",
                            "product": "Product",
                            "funnel": "Funnel",
                            "pricing": "Revenue",
                        }
                        target_group = cat_to_group.get(rx_category, "")
                        for d in deltas:
                            if d.get("group") == target_group:
                                related_deltas.append({
                                    "id": d["id"],
                                    "title": d["title"],
                                    "direction": d["direction"],
                                    "percent_change": d.get("percent_change"),
                                })

                        completed_prescriptions.append({
                            "id": rx_id,
                            "title": rx.get("title", ""),
                            "category": rx_category,
                            "urgency": rx.get("urgency", "medium"),
                            "related_kpi_changes": related_deltas,
                        })
    except Exception:
        pass

    return _safe_json({
        "current_snapshot": {
            "generated_at": current_snap.get("meta", {}).get("generated_at"),
        },
        "previous_snapshot": {
            "generated_at": prev_snap.get("meta", {}).get("generated_at"),
        },
        "deltas": deltas,
        "resolved_issues": resolved_issues,
        "new_risks": new_risks,
        "completed_prescriptions": completed_prescriptions,
    })


@app.get("/api/runs/compare/ai-analysis")
async def get_comparison_ai_analysis(current: Optional[str] = None, previous: Optional[str] = None):
    """AI-powered analysis of changes between two pipeline runs."""
    from datetime import datetime, timezone
    from agents.llm import ask_llm, parse_llm_json

    # ---- 1. Resolve run IDs ------------------------------------------------
    current_run_id = current or get_latest_run_id()
    previous_run_id = previous

    if not previous_run_id:
        try:
            runs = get_pipeline_runs()
            completed = [r for r in runs if r.get("status") == "completed"]
            if len(completed) >= 2:
                previous_run_id = completed[1].get("id")
        except Exception:
            pass

    if not current_run_id or not previous_run_id:
        return _safe_json({
            "error": "Need at least two completed runs for AI comparison analysis",
            "executive_summary": None, "department_grades": [], "root_causes": [],
            "causal_chains": [], "revenue_bridge": None, "profit_loss_drivers": {"positive": [], "negative": []},
            "prescription_report_card": [], "missed_opportunities": [], "next_30_day_targets": [],
            "quick_wins": [], "start_doing": [], "stop_doing": [], "keep_doing": [],
            "anomalies": [], "trend_verdict": None,
        })

    # ---- 2. Check cache ----------------------------------------------------
    try:
        cached = db_get_comparison_ai(current_run_id, previous_run_id)
        if cached and isinstance(cached, dict) and "error" not in cached and cached.get("executive_summary"):
            cached["cached"] = True
            return _safe_json(cached)
    except Exception:
        pass

    # ---- 3. Load snapshots for both runs -----------------------------------
    try:
        cur_snap = _load_kpi_snapshot(current_run_id if current else None)
        prev_snap = _load_kpi_snapshot(previous_run_id)
        cur_insight = db_get_run_insight(current_run_id) if current_run_id else db_get_latest_insight()
        prev_insight = db_get_run_insight(previous_run_id) if previous_run_id else None
        cur_action = db_get_run_action_plan(current_run_id) if current_run_id else db_get_latest_action_plan()
        prev_action = db_get_run_action_plan(previous_run_id) if previous_run_id else None
        cur_forecast = db_get_run_forecast(current_run_id) if current_run_id else db_get_latest_forecast()
    except Exception:
        cur_snap = prev_snap = None
        cur_insight = prev_insight = cur_action = prev_action = cur_forecast = None

    if not cur_snap or not prev_snap:
        return _safe_json({
            "error": "Could not load KPI snapshots for comparison",
            "executive_summary": None, "department_grades": [], "root_causes": [],
            "causal_chains": [], "revenue_bridge": None, "profit_loss_drivers": {"positive": [], "negative": []},
            "prescription_report_card": [], "missed_opportunities": [], "next_30_day_targets": [],
            "quick_wins": [], "start_doing": [], "stop_doing": [], "keep_doing": [],
            "anomalies": [], "trend_verdict": None,
        })

    # ---- 4. Build data digest for LLM -------------------------------------
    digest_parts = []

    # 4a. KPI Deltas (top 20 by |percent_change|)
    current_cards = {c["id"]: c for c in cur_snap.get("cards", []) if isinstance(c, dict)}
    prev_cards = {c["id"]: c for c in prev_snap.get("cards", []) if isinstance(c, dict)}
    deltas = []
    for card_id, card in current_cards.items():
        cur_val = card.get("value")
        prev_card = prev_cards.get(card_id)
        prev_val = prev_card.get("value") if prev_card else None
        if not isinstance(cur_val, (int, float)):
            continue
        if prev_val is not None and isinstance(prev_val, (int, float)):
            abs_chg = cur_val - prev_val
            pct_chg = abs_chg / prev_val if prev_val != 0 else None
            direction = "up" if abs_chg > 0 else ("down" if abs_chg < 0 else "stable")
        else:
            pct_chg = None
            direction = "new"
        deltas.append({
            "id": card_id, "title": card.get("title", ""), "group": card.get("group", ""),
            "format": card.get("format", "number"),
            "current": cur_val, "previous": prev_val, "pct_change": pct_chg, "direction": direction,
        })

    deltas_sorted = sorted(deltas, key=lambda d: abs(d["pct_change"]) if d["pct_change"] is not None else 0, reverse=True)
    top_deltas = deltas_sorted[:20]
    delta_lines = []
    for d in top_deltas:
        pct_str = f"{d['pct_change']*100:+.1f}%" if d["pct_change"] is not None else "NEW"
        delta_lines.append(f"  [{d['group']}] {d['title']}: {d['previous']} → {d['current']} ({pct_str}, {d['direction']})")
    digest_parts.append("## TOP KPI CHANGES (by magnitude)\n" + "\n".join(delta_lines))

    # 4b. Revenue Waterfall (both runs)
    cur_net = cur_snap.get("kpis", {}).get("net_revenue", {})
    prev_net = prev_snap.get("kpis", {}).get("net_revenue", {})
    if cur_net or prev_net:
        waterfall_fields = ["gross_revenue", "total_discounts", "total_returns", "total_refunds", "total_fees", "net_revenue", "discount_rate"]
        wf_lines = []
        for f in waterfall_fields:
            cv = cur_net.get(f, "N/A")
            pv = prev_net.get(f, "N/A")
            wf_lines.append(f"  {f}: {pv} → {cv}")
        digest_parts.append("## REVENUE WATERFALL\n" + "\n".join(wf_lines))

    # 4c. Customer metrics (both runs)
    cur_cust = cur_snap.get("kpis", {}).get("customer_health_value", {})
    prev_cust = prev_snap.get("kpis", {}).get("customer_health_value", {})
    if cur_cust or prev_cust:
        cust_fields = ["active_customers_30d", "new_customers_30d", "returning_customers_30d",
                       "repeat_purchase_rate", "churn_rate_proxy", "avg_clv"]
        cl = [f"  {f}: {prev_cust.get(f, 'N/A')} → {cur_cust.get(f, 'N/A')}" for f in cust_fields]
        digest_parts.append("## CUSTOMER METRICS\n" + "\n".join(cl))

    # 4d. Funnel metrics (both runs)
    cur_funnel = cur_snap.get("kpis", {}).get("conversion_funnel", {})
    prev_funnel = prev_snap.get("kpis", {}).get("conversion_funnel", {})
    if cur_funnel or prev_funnel:
        funnel_fields = ["conversion_rate", "cart_abandonment_rate", "bounce_rate",
                         "avg_session_duration", "revenue_per_session",
                         "mobile_conversion_rate", "desktop_conversion_rate"]
        fl = [f"  {f}: {prev_funnel.get(f, 'N/A')} → {cur_funnel.get(f, 'N/A')}" for f in funnel_fields]
        digest_parts.append("## FUNNEL METRICS\n" + "\n".join(fl))

    # 4e. Brand performance (both runs) — revenue, margins, ratings
    cur_brand = cur_snap.get("kpis", {}).get("brand_performance", {})
    prev_brand = prev_snap.get("kpis", {}).get("brand_performance", {})
    if cur_brand or prev_brand:
        brand_lines = []
        if cur_brand.get("revenue_by_brand") or prev_brand.get("revenue_by_brand"):
            brand_lines.append(f"  Revenue: Previous: {json.dumps(prev_brand.get('revenue_by_brand', {}), default=str)} → Current: {json.dumps(cur_brand.get('revenue_by_brand', {}), default=str)}")
        if cur_brand.get("margin_by_brand") or prev_brand.get("margin_by_brand"):
            brand_lines.append(f"  Margins: Previous: {json.dumps(prev_brand.get('margin_by_brand', {}), default=str)} → Current: {json.dumps(cur_brand.get('margin_by_brand', {}), default=str)}")
        if cur_brand.get("rating_by_brand") or prev_brand.get("rating_by_brand"):
            brand_lines.append(f"  Ratings: Previous: {json.dumps(prev_brand.get('rating_by_brand', {}), default=str)} → Current: {json.dumps(cur_brand.get('rating_by_brand', {}), default=str)}")
        if brand_lines:
            digest_parts.append("## BRAND PERFORMANCE\n" + "\n".join(brand_lines))

    # 4f. Supplier health (both runs) — stockouts + reliability scores
    cur_supp = cur_snap.get("kpis", {}).get("supplier_health", {})
    prev_supp = prev_snap.get("kpis", {}).get("supplier_health", {})
    if cur_supp or prev_supp:
        supp_lines = []
        if cur_supp.get("stockout_by_supplier") or prev_supp.get("stockout_by_supplier"):
            supp_lines.append(f"  Stockouts: Previous: {json.dumps(prev_supp.get('stockout_by_supplier', {}), default=str)} → Current: {json.dumps(cur_supp.get('stockout_by_supplier', {}), default=str)}")
        if cur_supp.get("supplier_reliability_score") or prev_supp.get("supplier_reliability_score"):
            supp_lines.append(f"  Reliability: Previous: {json.dumps(prev_supp.get('supplier_reliability_score', {}), default=str)} → Current: {json.dumps(cur_supp.get('supplier_reliability_score', {}), default=str)}")
        if supp_lines:
            digest_parts.append("## SUPPLIER HEALTH\n" + "\n".join(supp_lines))

    # 4g. Resolved issues & new risks
    cur_insights_list = (cur_insight or {}).get("insights", []) if isinstance(cur_insight, dict) else []
    prev_insights_list = (prev_insight or {}).get("insights", []) if isinstance(prev_insight, dict) else []
    cur_titles = {i.get("title", "").lower().strip() for i in cur_insights_list if i.get("title")}
    prev_titles = {i.get("title", "").lower().strip() for i in prev_insights_list if i.get("title")}

    resolved = [i for i in prev_insights_list
                if i.get("severity") in ("high", "medium") and (i.get("title", "").lower().strip()) not in cur_titles]
    new_risks = [i for i in cur_insights_list
                 if i.get("severity") in ("high", "medium") and (i.get("title", "").lower().strip()) not in prev_titles]

    if resolved:
        rl = []
        for i in resolved[:8]:
            entry = f"  [{i.get('severity')}] {i.get('title')}"
            if i.get("description"):
                entry += f"\n    Description: {i['description'][:200]}"
            if i.get("recommendation"):
                entry += f"\n    Recommendation: {i['recommendation'][:200]}"
            if i.get("impact_estimate"):
                entry += f"\n    Impact: {i['impact_estimate']}"
            ev = i.get("evidence")
            if ev and isinstance(ev, dict):
                entry += f"\n    Evidence: {json.dumps(ev, default=str)[:300]}"
            rl.append(entry)
        digest_parts.append("## RESOLVED ISSUES\n" + "\n".join(rl))
    if new_risks:
        nl = []
        for i in new_risks[:8]:
            entry = f"  [{i.get('severity')}] {i.get('title')}"
            if i.get("description"):
                entry += f"\n    Description: {i['description'][:200]}"
            if i.get("recommendation"):
                entry += f"\n    Recommendation: {i['recommendation'][:200]}"
            if i.get("impact_estimate"):
                entry += f"\n    Impact: {i['impact_estimate']}"
            ev = i.get("evidence")
            if ev and isinstance(ev, dict):
                entry += f"\n    Evidence: {json.dumps(ev, default=str)[:300]}"
            nl.append(entry)
        digest_parts.append("## NEW RISKS\n" + "\n".join(nl))

    # 4h. ALL prescriptions from previous run with statuses
    if prev_action and isinstance(prev_action, dict):
        prev_rxs = prev_action.get("prescriptions", [])
        statuses = {}
        try:
            status_rows = db_get_prescription_statuses(previous_run_id)
            statuses = {s["prescription_id"]: s["status"] for s in status_rows}
        except Exception:
            pass
        if prev_rxs:
            rx_lines = []
            for rx in prev_rxs[:15]:
                rx_id = rx.get("id", "")
                st = statuses.get(rx_id, rx.get("status", "pending"))
                entry = f"  [{st.upper()}] [{rx.get('urgency')}] {rx.get('title')} (category: {rx.get('category')}, impact: {rx.get('impact_estimate', 'N/A')})"
                if rx.get("description"):
                    entry += f"\n    Description: {rx['description'][:250]}"
                ev = rx.get("evidence")
                if ev and isinstance(ev, dict):
                    entry += f"\n    Evidence: {json.dumps(ev, default=str)[:300]}"
                rels = rx.get("related_entities")
                if rels and isinstance(rels, list):
                    entry += f"\n    Related: {', '.join(rels[:5])}"
                rx_lines.append(entry)
            digest_parts.append("## PREVIOUS RUN PRESCRIPTIONS (with status)\n" + "\n".join(rx_lines))

    # 4i. Demand forecast context
    demand_csv = _read_local_csv(_FORECAST_DIR / "demand_forecast_sku.csv")
    if demand_csv is not None and not demand_csv.empty and "status" in demand_csv.columns:
        critical = demand_csv[demand_csv["status"] == "critical"].head(5)
        warning = demand_csv[demand_csv["status"] == "warning"].head(5)
        if not critical.empty:
            cols = [c for c in ["sku", "product_name", "current_stock", "forecast_qty_30d", "days_until_stockout"] if c in critical.columns]
            digest_parts.append(f"## CRITICAL DEMAND SKUS\n{critical[cols].to_string(index=False)}")
        if not warning.empty:
            cols = [c for c in ["sku", "product_name", "current_stock", "forecast_qty_30d", "days_until_stockout"] if c in warning.columns]
            digest_parts.append(f"## WARNING DEMAND SKUS\n{warning[cols].to_string(index=False)}")

    # 4j. Churn risk context
    churn_csv = _read_local_csv(_FORECAST_DIR / "churn_predictions.csv")
    if churn_csv is not None and not churn_csv.empty and "churn_prob_30d" in churn_csv.columns:
        high_churn = churn_csv[churn_csv["churn_prob_30d"] >= 0.7].sort_values("churn_prob_30d", ascending=False).head(5)
        if not high_churn.empty:
            cols = [c for c in ["customer_id", "name", "churn_prob_30d", "total_spend", "recency_days"] if c in high_churn.columns]
            total_at_risk = churn_csv[churn_csv["churn_prob_30d"] >= 0.7]["total_spend"].sum() if "total_spend" in churn_csv.columns else 0
            digest_parts.append(f"## HIGH CHURN RISK CUSTOMERS (top 5 of {len(churn_csv[churn_csv['churn_prob_30d'] >= 0.7])} at risk, ${total_at_risk:,.0f} spend at risk)\n{high_churn[cols].to_string(index=False)}")

    # 4k. Forecast context
    if cur_forecast and isinstance(cur_forecast, dict) and "error" not in cur_forecast:
        forecasts = cur_forecast.get("forecasts", {})
        fc_lines = []
        rev_fc = forecasts.get("forecasted_revenue", {})
        if rev_fc:
            fc_lines.append(f"  Revenue forecast: 7d={rev_fc.get('next_7d', 'N/A')}, 30d={rev_fc.get('next_30d', 'N/A')}, 90d={rev_fc.get('next_90d', 'N/A')}")
        churn_fc = forecasts.get("expected_churn_next_month", {})
        if churn_fc:
            fc_lines.append(f"  Churn forecast: {churn_fc.get('expected_churn_rate_next_30d', 'N/A')}")
        if fc_lines:
            digest_parts.append("## FORECASTS\n" + "\n".join(fc_lines))

    # 4l. Health scores
    cur_health = (cur_action or {}).get("health_score") if isinstance(cur_action, dict) else None
    prev_health = (prev_action or {}).get("health_score") if isinstance(prev_action, dict) else None
    if cur_health is not None or prev_health is not None:
        digest_parts.append(f"## HEALTH SCORE\n  Previous: {prev_health or 'N/A'} → Current: {cur_health or 'N/A'}")

    # 4m. Top products (current run)
    cur_tables = cur_snap.get("tables", {})
    top_prods = cur_tables.get("top_products", [])
    if top_prods:
        prod_lines = []
        for p in top_prods[:10]:
            if isinstance(p, dict):
                prod_lines.append(
                    f"  {p.get('sku', 'N/A')} | {p.get('product_name', 'N/A')} | Revenue: {p.get('revenue', 'N/A')} | "
                    f"Margin: {p.get('margin_pct', 'N/A')} | Units: {p.get('quantity', 'N/A')} | "
                    f"Brand: {p.get('brand', 'N/A')} | Category: {p.get('category', 'N/A')}"
                )
        if prod_lines:
            digest_parts.append("## TOP PRODUCTS BY REVENUE\n" + "\n".join(prod_lines))

    # 4n. Low-performing products
    low_prods = cur_tables.get("low_products", [])
    if low_prods:
        low_lines = []
        for p in low_prods[:5]:
            if isinstance(p, dict):
                low_lines.append(
                    f"  {p.get('sku', 'N/A')} | {p.get('product_name', 'N/A')} | Revenue: {p.get('revenue', 'N/A')} | "
                    f"Margin: {p.get('margin_pct', 'N/A')} | Brand: {p.get('brand', 'N/A')}"
                )
        if low_lines:
            digest_parts.append("## LOW PERFORMING PRODUCTS\n" + "\n".join(low_lines))

    # 4o. Risky products (inventory risk)
    risky_prods = cur_tables.get("risky_products", [])
    if risky_prods:
        risky_lines = []
        for p in risky_prods[:8]:
            if isinstance(p, dict):
                risky_lines.append(
                    f"  {p.get('sku', 'N/A')} | stock: {p.get('stock_level', 'N/A')} | "
                    f"reorder_threshold: {p.get('reorder_threshold', 'N/A')} | "
                    f"avg_daily_sold: {p.get('avg_daily_qty_sold_30d', 'N/A')} | "
                    f"days_remaining: {p.get('days_of_inventory_remaining', 'N/A')} | "
                    f"risk: {p.get('risk_flag', 'N/A')}"
                )
        if risky_lines:
            digest_parts.append("## RISKY PRODUCTS (low stock + high demand)\n" + "\n".join(risky_lines))

    # 4p. Discount watchlist
    disc_watch = cur_tables.get("discount_watchlist", [])
    if disc_watch:
        disc_lines = []
        for p in disc_watch[:5]:
            if isinstance(p, dict):
                disc_lines.append(
                    f"  {p.get('sku', 'N/A')} | {p.get('product_name', 'N/A')} | "
                    f"discount: {p.get('discount_percent', 'N/A')}% | rating: {p.get('average_rating', 'N/A')} | "
                    f"price: {p.get('retail_price', 'N/A')} | cost: {p.get('cost_price', 'N/A')} | "
                    f"brand: {p.get('brand', 'N/A')}{' | LOW_RATING' if p.get('flag_low_rating') else ''}"
                )
        if disc_lines:
            digest_parts.append("## HIGH-DISCOUNT PRODUCTS (discount >= 15%)\n" + "\n".join(disc_lines))

    # 4q. Top customers
    top_custs = cur_tables.get("top_customers", [])
    if top_custs:
        cust_lines = []
        for c in top_custs[:10]:
            if isinstance(c, dict):
                cust_lines.append(
                    f"  {c.get('customer_id', 'N/A')} | {c.get('name', 'N/A')} | "
                    f"orders: {c.get('total_orders', 'N/A')} | spend: ${c.get('total_spend', 0):,.0f} | "
                    f"AOV: ${c.get('avg_order_value', 0):,.0f} | recency: {c.get('recency_days', 'N/A')} days | "
                    f"device: {c.get('device_type', 'N/A')} | location: {c.get('location', 'N/A')}"
                )
        if cust_lines:
            digest_parts.append("## TOP CUSTOMERS\n" + "\n".join(cust_lines))

    # 4r. Demographics (both runs)
    cur_demo = cur_snap.get("kpis", {}).get("demographics", {})
    prev_demo = prev_snap.get("kpis", {}).get("demographics", {})
    if cur_demo or prev_demo:
        demo_lines = []
        for field in ["customers_by_gender", "customers_by_age_group", "customers_by_loyalty_tier", "avg_spend_by_loyalty"]:
            cv = cur_demo.get(field)
            pv = prev_demo.get(field)
            if cv or pv:
                demo_lines.append(f"  {field}: {json.dumps(pv or {}, default=str)} → {json.dumps(cv or {}, default=str)}")
        if demo_lines:
            digest_parts.append("## CUSTOMER DEMOGRAPHICS\n" + "\n".join(demo_lines))

    # 4s. Payment health (both runs)
    cur_pay = cur_snap.get("kpis", {}).get("payment_health", {})
    prev_pay = prev_snap.get("kpis", {}).get("payment_health", {})
    if cur_pay or prev_pay:
        pay_fields = ["payment_failure_rate", "refund_rate", "top_payment_method", "avg_transaction_fee"]
        pay_lines = [f"  {f}: {prev_pay.get(f, 'N/A')} → {cur_pay.get(f, 'N/A')}" for f in pay_fields]
        digest_parts.append("## PAYMENT HEALTH\n" + "\n".join(pay_lines))

    # 4t. Forecast executive insights (risks + opportunities)
    if cur_forecast and isinstance(cur_forecast, dict) and "error" not in cur_forecast:
        exec_ins = cur_forecast.get("executive_insights", {})
        if isinstance(exec_ins, dict):
            risks = exec_ins.get("top_3_risks", [])
            opps = exec_ins.get("top_3_opportunities", [])
            if risks:
                risk_lines = []
                for r in risks[:3]:
                    if isinstance(r, dict):
                        risk_lines.append(f"  - {r.get('title', 'N/A')} — Evidence: {json.dumps(r.get('evidence', {}), default=str)[:200]}")
                    elif isinstance(r, str):
                        risk_lines.append(f"  - {r}")
                if risk_lines:
                    digest_parts.append("## FORECAST RISKS\n" + "\n".join(risk_lines))
            if opps:
                opp_lines = []
                for o in opps[:3]:
                    if isinstance(o, dict):
                        opp_lines.append(f"  - {o.get('title', 'N/A')} — Evidence: {json.dumps(o.get('evidence', {}), default=str)[:200]}")
                    elif isinstance(o, str):
                        opp_lines.append(f"  - {o}")
                if opp_lines:
                    digest_parts.append("## FORECAST OPPORTUNITIES\n" + "\n".join(opp_lines))

    # Build final digest (cap at ~15000 chars)
    digest = "\n\n".join(digest_parts)
    if len(digest) > 15000:
        digest = digest[:15000] + "\n... (truncated)"

    # ---- 5. System prompt --------------------------------------------------
    system_prompt = """You are an expert retail analytics advisor. You are comparing two pipeline analysis runs of a retail store and must explain WHAT changed, WHY it changed (root causes), and WHAT TO DO about it.

Return ONLY valid JSON with this exact structure:
{
  "executive_summary": "2-3 sentences connecting the biggest changes with their root causes, referencing specific numbers from the data.",

  "department_grades": [
    {"department": "Revenue|Customers|Inventory|Marketing|Funnel|Product|Payments", "grade": "A|B|C|D|F", "trend": "improving|stable|declining", "one_liner": "Short assessment"}
  ],

  "root_causes": [
    {"metric": "metric_id", "direction": "up|down", "explanation": "1-2 sentences explaining likely cause", "contributing_factors": ["factor1", "factor2"]}
  ],

  "causal_chains": [
    {"chain": ["Metric A changed X%", "Which caused Metric B to change Y%", "Leading to Z impact"], "narrative": "One sentence connecting the chain"}
  ],

  "revenue_bridge": {
    "total_change": <number>,
    "components": [{"label": "Component name", "impact": <positive or negative number>}]
  },

  "profit_loss_drivers": {
    "positive": ["Specific driver that helped, with numbers"],
    "negative": ["Specific driver that hurt, with numbers"]
  },

  "prescription_report_card": [
    {"prescription_title": "Title of completed prescription", "verdict": "effective|partially_effective|no_impact|too_early", "evidence": "What changed as a result", "related_kpi_impact": "e.g. +20% metric"}
  ],

  "missed_opportunities": [
    {"prescription_title": "Title of undone prescription", "status": "pending|dismissed", "estimated_cost_of_inaction": "$X in lost Y", "urgency_now": "critical|high|medium"}
  ],

  "next_30_day_targets": [
    {"target": "Specific measurable goal", "current_value": "68%", "target_value": "55%", "how": "Specific steps to achieve this", "expected_impact": "Estimated business impact"}
  ],

  "quick_wins": [
    {"action": "Specific immediate action", "effort": "Time estimate", "expected_impact": "Quantified impact", "data_point": "Supporting data"}
  ],

  "start_doing": ["Actionable recommendation to START, with data backing"],
  "stop_doing": ["Thing to STOP or reduce, with data backing"],
  "keep_doing": ["Thing that IS working well, with data backing"],

  "anomalies": [
    {"metric": "metric_id", "change": "+X%", "why_unexpected": "Why this is unusual", "suggested_investigation": "What to check"}
  ],

  "trend_verdict": {
    "direction": "improving|stable|declining",
    "confidence": "high|medium|low",
    "summary": "2-3 sentence overall trajectory assessment"
  }
}

RULES:
1. Focus on the TOP 5 most significant metric changes by percent_change magnitude.
2. Cross-reference metrics: if revenue dropped and churn rose, connect them in causal_chains.
3. For prescription_report_card, ONLY include prescriptions marked DONE. Evaluate their effectiveness by checking if related KPIs improved.
4. For missed_opportunities, include prescriptions still PENDING or DISMISSED that are now more urgent.
5. Revenue bridge components should sum approximately to total_change. Use revenue waterfall data.
6. Generate 5-7 department_grades (one per department that has data).
7. Generate 3-5 root_causes, 1-3 causal_chains, 2-4 items per start/stop/keep.
8. Generate 2-3 next_30_day_targets with realistic target values based on current data.
9. Generate 2-4 quick_wins — things that can be done in < 1 week.
10. Only include anomalies for truly unexpected changes (max 3).
11. Ground ALL claims in actual numbers from the data. Never invent numbers.
12. Return ONLY valid JSON. No markdown fences, no extra text.

CRITICAL — BE SPECIFIC, NOT VAGUE:
13. ALWAYS reference specific product names, SKU IDs, customer names, brand names, supplier names, and dollar amounts from the data provided. Never use generic language like "some products", "certain customers", or "strong growth". Instead say "Nike Air Max (SKU-101) revenue dropped 12% from $25K to $22K" or "Customer John D ($12,500 lifetime spend) is at 85% churn risk".
14. In department_grades one_liner: include the most important metric value and its change. E.g. "Revenue MTD dropped 8% ($45K → $41K) driven by Nike brand decline, but YTD up 15% at $600K".
15. In quick_wins: name the specific SKUs to restock, customers to contact, or campaigns to adjust — with quantities and dollar amounts.
16. In root_causes: cite the specific data evidence (revenue waterfall components, brand breakdowns, product tables, customer data) that supports each cause.
17. Use the TOP PRODUCTS, RISKY PRODUCTS, TOP CUSTOMERS, BRAND PERFORMANCE, and DISCOUNT WATCHLIST data extensively to make recommendations concrete."""

    user_prompt = f"Analyze this comparison between two pipeline runs:\n\n{digest}"

    # ---- 6. Call LLM -------------------------------------------------------
    try:
        raw = await ask_llm(system_prompt, user_prompt)
        result = parse_llm_json(raw, fallback={
            "executive_summary": None, "department_grades": [], "root_causes": [],
            "causal_chains": [], "revenue_bridge": None,
            "profit_loss_drivers": {"positive": [], "negative": []},
            "prescription_report_card": [], "missed_opportunities": [],
            "next_30_day_targets": [], "quick_wins": [],
            "start_doing": [], "stop_doing": [], "keep_doing": [],
            "anomalies": [], "trend_verdict": None,
        })

        result["generated_at"] = datetime.now(timezone.utc).isoformat()
        result["cached"] = False

        # ---- 7. Cache in Supabase ------------------------------------------
        try:
            db_store_comparison_ai(current_run_id, previous_run_id, result)
        except Exception as e:
            print(f"[comparison-ai] Failed to cache in Supabase: {e}")

        return _safe_json(result)

    except Exception as e:
        return _safe_json({
            "error": str(e),
            "executive_summary": None, "department_grades": [], "root_causes": [],
            "causal_chains": [], "revenue_bridge": None,
            "profit_loss_drivers": {"positive": [], "negative": []},
            "prescription_report_card": [], "missed_opportunities": [],
            "next_30_day_targets": [], "quick_wins": [],
            "start_doing": [], "stop_doing": [], "keep_doing": [],
            "anomalies": [], "trend_verdict": None,
            "cached": False,
        })


@app.get("/api/runs/{run_id}")
def get_run_detail(run_id: str):
    """Returns all snapshots for a specific pipeline run."""
    return get_run_snapshots(run_id)


@app.delete("/api/runs/{run_id}")
async def delete_run(run_id: str):
    """Delete a specific pipeline run and all its associated data."""
    try:
        return delete_pipeline_run(run_id)
    except Exception as e:
        return {"success": False, "message": str(e)}


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
# Forecast series & AI analysis endpoints
# -----------------------------------------------------------------------------
_BACKEND_ROOT = Path(__file__).resolve().parent
_FORECAST_DIR = _BACKEND_ROOT / "data" / "forecast_outputs"
_CLEANED_DIR = _BACKEND_ROOT / "data" / "cleaned_data"
_FEATURED_DIR = _BACKEND_ROOT / "data" / "featured_data"
_INSIGHT_DIR = _BACKEND_ROOT / "data" / "insight_outputs"


def _safe_json(obj):
    """Replace NaN/Inf with None for JSON serialization."""
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if isinstance(obj, dict):
        return {k: _safe_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_safe_json(v) for v in obj]
    return obj


def _read_local_csv(path: Path) -> pd.DataFrame | None:
    if path.is_file():
        return pd.read_csv(path)
    return None


def _sanitize(obj):
    """Alias for _safe_json — replace NaN/Inf with None for JSON serialization."""
    return _safe_json(obj)


def _load_kpi_snapshot(run_id: Optional[str] = None) -> dict | None:
    """Load KPI snapshot from local file first, then Supabase fallback.

    Local file is preferred because it reflects the latest pipeline run
    (including newly added KPI groups) without needing a Supabase re-upload.
    """
    # Prefer local file (always up-to-date with latest pipeline output)
    kpi_path = _BACKEND_ROOT / "data" / "kpi_outputs" / "kpi_snapshot.json"
    if kpi_path.is_file() and not run_id:
        try:
            with open(kpi_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    # Fallback: Supabase (needed for historical run_id lookups)
    try:
        if run_id:
            result = db_get_run_kpi(run_id)
        else:
            result = db_get_latest_kpi()
        if result and isinstance(result, dict) and result.get("kpis"):
            return result
    except Exception:
        pass
    return None


@app.get("/api/forecast/series/revenue")
def get_revenue_forecast_series(run_id: Optional[str] = None):
    """Returns daily revenue forecast time-series data."""
    # Try local CSV first (works without Supabase)
    rev_csv = _read_local_csv(_FORECAST_DIR / "revenue_forecast_daily.csv")
    if rev_csv is not None and not rev_csv.empty:
        rev_csv["date"] = pd.to_datetime(rev_csv["date"]).dt.strftime("%Y-%m-%d")
        series = rev_csv.rename(columns={"revenue_forecast": "revenue_forecast"}).to_dict(orient="records")
        return _safe_json({"series": series})

    # Fallback: derive daily revenue from transactions
    txn_csv = _read_local_csv(_CLEANED_DIR / "transactions_cleaned.csv")
    if txn_csv is not None and not txn_csv.empty:
        txn_csv["date"] = pd.to_datetime(txn_csv["order_datetime"], errors="coerce").dt.date
        daily = txn_csv.groupby("date")["total_amount"].sum().reset_index()
        daily.columns = ["date", "revenue_actual"]
        daily["date"] = daily["date"].astype(str)
        daily = daily.sort_values("date")
        return _safe_json({"series": daily.to_dict(orient="records")})

    return {"series": [], "error": "No revenue data available. Run the pipeline first."}


@app.get("/api/forecast/series/demand")
def get_demand_forecast(run_id: Optional[str] = None):
    """Returns per-SKU demand forecast with stock health data."""
    demand_csv = _read_local_csv(_FORECAST_DIR / "demand_forecast_sku.csv")
    if demand_csv is None or demand_csv.empty:
        return {"skus": [], "error": "No demand forecast available. Run the pipeline first."}

    # Join with inventory for stock levels
    inv_csv = _read_local_csv(_CLEANED_DIR / "inventory_cleaned.csv")
    prod_csv = _read_local_csv(_CLEANED_DIR / "products_cleaned.csv")

    demand_csv["sku"] = demand_csv["sku"].astype(str).str.upper()

    if inv_csv is not None and not inv_csv.empty:
        inv_csv["sku"] = inv_csv["sku"].astype(str).str.upper()
        # Normalize column names
        inv_renames = {"stock_quantity": "stock_level", "reorder_level": "reorder_threshold"}
        inv_csv = inv_csv.rename(columns={k: v for k, v in inv_renames.items() if k in inv_csv.columns})
        inv_cols = ["sku", "stock_level", "reorder_threshold"]
        inv_cols = [c for c in inv_cols if c in inv_csv.columns]
        demand_csv = demand_csv.merge(inv_csv[inv_cols], on="sku", how="left")

    if prod_csv is not None and not prod_csv.empty:
        sku_col_prod = "sku" if "sku" in prod_csv.columns else ("product_id" if "product_id" in prod_csv.columns else None)
        if sku_col_prod:
            prod_csv["sku"] = prod_csv[sku_col_prod].astype(str).str.upper()
            # Normalize column names
            if "product_name" in prod_csv.columns and "name" not in prod_csv.columns:
                prod_csv = prod_csv.rename(columns={"product_name": "name"})
            prod_cols = ["sku"]
            for c in ["name", "category", "brand"]:
                if c in prod_csv.columns:
                    prod_cols.append(c)
            demand_csv = demand_csv.merge(prod_csv[prod_cols], on="sku", how="left")

    # Compute days until stockout
    stock_col = "stock_level" if "stock_level" in demand_csv.columns else None
    if stock_col and "avg_daily_forecast" in demand_csv.columns:
        demand_csv["current_stock"] = pd.to_numeric(demand_csv[stock_col], errors="coerce").fillna(0)
        demand_csv["days_until_stockout"] = demand_csv.apply(
            lambda r: round(r["current_stock"] / r["avg_daily_forecast"], 1)
            if r["avg_daily_forecast"] > 0
            else (9999 if r["current_stock"] > 0 else None),
            axis=1,
        )
        demand_csv["reorder_threshold"] = pd.to_numeric(
            demand_csv.get("reorder_threshold", pd.Series(dtype=float)), errors="coerce"
        ).fillna(0)
    else:
        demand_csv["current_stock"] = 0
        demand_csv["days_until_stockout"] = None
        demand_csv["reorder_threshold"] = 0

    # Compute status
    def compute_status(row):
        d = row.get("days_until_stockout")
        if d is None or (isinstance(d, float) and math.isnan(d)):
            return "unknown"
        if d < 7:
            return "critical"
        if d < 14:
            return "warning"
        return "healthy"

    demand_csv["status"] = demand_csv.apply(compute_status, axis=1)

    # Sort by urgency
    demand_csv = demand_csv.sort_values("days_until_stockout", ascending=True, na_position="last")

    out_cols = ["sku", "name", "category", "brand", "forecast_qty_30d", "avg_daily_forecast",
                "current_stock", "reorder_threshold", "days_until_stockout", "status"]
    out_cols = [c for c in out_cols if c in demand_csv.columns]
    result = demand_csv[out_cols].head(100).to_dict(orient="records")
    return _safe_json({"skus": result})


@app.get("/api/forecast/series/churn")
def get_churn_predictions(run_id: Optional[str] = None):
    """Returns churn predictions with customer details."""
    churn_csv = _read_local_csv(_FORECAST_DIR / "churn_predictions.csv")
    if churn_csv is None or churn_csv.empty:
        return {"customers": [], "error": "No churn predictions available. Run the pipeline first."}

    churn_csv["customer_id"] = churn_csv["customer_id"].astype(str)

    # Join with customer features for names and details
    cust_csv = _read_local_csv(_FEATURED_DIR / "customers_features.csv")
    if cust_csv is not None and not cust_csv.empty:
        cust_csv["customer_id"] = cust_csv["customer_id"].astype(str)
        join_cols = ["customer_id"]
        for c in ["name", "total_spend", "total_orders", "recency_days"]:
            if c in cust_csv.columns:
                join_cols.append(c)
        churn_csv = churn_csv.merge(cust_csv[join_cols], on="customer_id", how="left")

    # Add segment based on spend
    if "total_spend" in churn_csv.columns:
        churn_csv["total_spend"] = pd.to_numeric(churn_csv["total_spend"], errors="coerce").fillna(0)
        churn_csv["segment"] = churn_csv["total_spend"].apply(
            lambda s: "Top Buyer" if s >= 3500 else ("Moderate" if s >= 1500 else "At-Risk")
        )
    else:
        churn_csv["segment"] = "Unknown"

    churn_csv = churn_csv.sort_values("churn_prob_30d", ascending=False)

    out_cols = ["customer_id", "name", "churn_prob_30d", "total_spend", "recency_days",
                "total_orders", "segment"]
    out_cols = [c for c in out_cols if c in churn_csv.columns]
    result = churn_csv[out_cols].head(100).to_dict(orient="records")
    return _safe_json({"customers": result})


@app.get("/api/insights/ai-analysis")
def get_ai_analysis(run_id: Optional[str] = None):
    """Returns cached LLM analysis or generates one if not cached."""
    from datetime import datetime, timezone

    # 1. Check Supabase cache
    try:
        if run_id:
            cached = db_get_run_ai_analysis(run_id)
        else:
            cached = db_get_latest_ai_analysis()
        if cached and "error" not in cached:
            cached["cached"] = True
            return cached
    except Exception:
        pass

    # 2. Check local JSON cache
    local_path = _INSIGHT_DIR / "ai_analysis.json"
    if local_path.is_file():
        try:
            with open(local_path, "r", encoding="utf-8") as f:
                local_cached = json.load(f)
            if local_cached and local_cached.get("analysis"):
                local_cached["cached"] = True
                return local_cached
        except Exception:
            pass

    # 3. Generate new analysis via LLM
    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import SystemMessage, HumanMessage

        # Gather context from existing snapshots
        kpi_data = db_get_latest_kpi() if not run_id else db_get_run_kpi(run_id)
        forecast_data = db_get_latest_forecast() if not run_id else db_get_run_forecast(run_id)
        insight_data = db_get_latest_insight() if not run_id else db_get_run_insight(run_id)

        # Build context string from available data
        context_parts = []

        if kpi_data and "error" not in kpi_data:
            cards = kpi_data.get("cards", [])
            card_summary = {c["id"]: c["value"] for c in cards if isinstance(c, dict) and "id" in c and "value" in c}
            context_parts.append(f"KPI Metrics:\n{json.dumps(card_summary, indent=2, default=str)}")

            tables = kpi_data.get("tables", {})
            if tables.get("risky_products"):
                context_parts.append(f"Risky Products (low stock): {json.dumps(tables['risky_products'][:10], default=str)}")
            if tables.get("top_products"):
                context_parts.append(f"Top Products: {json.dumps(tables['top_products'][:5], default=str)}")

        if forecast_data and "error" not in forecast_data:
            forecasts = forecast_data.get("forecasts", {})
            context_parts.append(f"Revenue Forecast: {json.dumps(forecasts.get('forecasted_revenue', {}), default=str)}")
            churn_info = forecasts.get("expected_churn_next_month", {})
            context_parts.append(f"Churn Forecast: {json.dumps(churn_info, default=str)}")
            cashflow = forecasts.get("projected_cashflow", {})
            context_parts.append(f"Cashflow Projection: {json.dumps(cashflow, default=str)}")
            exec_insights = forecast_data.get("executive_insights", {})
            context_parts.append(f"Executive Insights: {json.dumps(exec_insights, default=str)}")

        if insight_data and "error" not in insight_data:
            insights = insight_data.get("insights", []) if isinstance(insight_data, dict) else []
            if insights:
                insight_summaries = [{"title": i.get("title"), "severity": i.get("severity"),
                                      "recommendation": i.get("recommendation")} for i in insights[:10]]
                context_parts.append(f"Generated Insights:\n{json.dumps(insight_summaries, indent=2, default=str)}")

        # Demand forecast context
        demand_csv = _read_local_csv(_FORECAST_DIR / "demand_forecast_sku.csv")
        if demand_csv is not None and not demand_csv.empty:
            top_demand = demand_csv.sort_values("forecast_qty_30d", ascending=False).head(10)
            context_parts.append(f"Top Demand SKUs (30d forecast):\n{top_demand.to_string(index=False)}")

        context = "\n\n".join(context_parts)

        # Cap context to avoid token limits
        if len(context) > 12000:
            context = context[:12000] + "\n... (truncated)"

        system_prompt = """You are a senior retail data analyst. Analyze the following business data and provide a comprehensive analysis.

Your response MUST be valid JSON with this exact structure:
{
  "analysis": "A 2-3 sentence executive summary of the overall business health",
  "key_findings": ["finding 1", "finding 2", "finding 3", "finding 4", "finding 5"],
  "recommendations": ["recommendation 1", "recommendation 2", "recommendation 3", "recommendation 4", "recommendation 5"],
  "risks": ["risk 1", "risk 2", "risk 3"]
}

Guidelines:
- Key findings should be specific, data-backed observations (mention actual numbers)
- Recommendations should be actionable with specific SKUs, customer segments, or channels when possible
- Risks should highlight urgent issues that need attention
- Use plain business language, avoid technical jargon
- Focus on what the retail store owner should DO next"""

        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Analyze this retail business data:\n\n{context}"),
        ])

        # Parse LLM response
        try:
            result = json.loads(response.content)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            result = json.loads(content)

        result["generated_at"] = datetime.now(timezone.utc).isoformat()
        result["cached"] = False

        # 4. Persist to Supabase
        rid = run_id or get_latest_run_id()
        if rid:
            try:
                db_store_ai_analysis(rid, result)
            except Exception as e:
                print(f"[ai-analysis] Failed to store in Supabase: {e}")

        # 5. Persist locally
        os.makedirs(str(_INSIGHT_DIR), exist_ok=True)
        with open(local_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, default=str)

        return result

    except Exception as e:
        return {
            "analysis": None,
            "key_findings": [],
            "recommendations": [],
            "risks": [],
            "error": str(e),
            "cached": False,
        }


# -----------------------------------------------------------------------------
# Action Plan endpoint (Retail Doctor)
# -----------------------------------------------------------------------------
@app.get("/api/action-plan")
def get_action_plan(run_id: Optional[str] = None):
    """Returns a prioritized action plan aggregated from all data sources.

    Primary path: read from Supabase (stored by ActionAgent during pipeline run).
    Fallback: compute rule-based action plan on-the-fly.
    """
    # 1. Try DB-stored action plan (from ActionAgent pipeline run)
    try:
        db_plan = db_get_run_action_plan(run_id) if run_id else db_get_latest_action_plan()
        if db_plan and "error" not in db_plan and db_plan.get("prescriptions"):
            return _safe_json(db_plan)
    except Exception:
        pass

    # 2. Try local cached file
    cache_path = _INSIGHT_DIR / "action_plan.json"
    if cache_path.is_file():
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cached = json.load(f)
            if cached and cached.get("prescriptions"):
                return _safe_json(cached)
        except Exception:
            pass

    # 3. Fallback: compute rule-based action plan on-the-fly
    from datetime import datetime, timezone
    from pipeline.insights.prescriptions import build_action_plan

    insight_data = db_get_run_insight(run_id) if run_id else db_get_latest_insight()
    forecast_data = db_get_run_forecast(run_id) if run_id else db_get_latest_forecast()

    insights = []
    if insight_data and "error" not in insight_data:
        insights = insight_data.get("insights", []) if isinstance(insight_data, dict) else []

    executive_insights = {}
    if forecast_data and "error" not in forecast_data:
        executive_insights = forecast_data.get("executive_insights", {})

    demand_resp = get_demand_forecast(run_id)
    demand_skus = demand_resp.get("skus", [])

    churn_resp = get_churn_predictions(run_id)
    churn_predictions = churn_resp.get("customers", [])

    plan = build_action_plan(
        insights=insights,
        demand_skus=demand_skus,
        churn_predictions=churn_predictions,
        executive_insights=executive_insights,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )

    return _safe_json(plan.to_dict())


# -----------------------------------------------------------------------------
# Location-level stock analysis
# -----------------------------------------------------------------------------
@app.get("/api/forecast/series/demand-by-location")
def get_demand_by_location(run_id: Optional[str] = None):
    """Returns per-SKU stock levels broken down by warehouse location,
    with store transfer recommendations where stock imbalances exist."""
    inv_csv = _read_local_csv(_CLEANED_DIR / "inventory_cleaned.csv")
    if inv_csv is None or inv_csv.empty:
        return {"locations": [], "transfers": [], "error": "No inventory data available."}

    demand_csv = _read_local_csv(_FORECAST_DIR / "demand_forecast_sku.csv")
    prod_csv = _read_local_csv(_CLEANED_DIR / "products_cleaned.csv")

    inv_csv["sku"] = inv_csv["sku"].astype(str).str.upper()

    # Normalize column names
    inv_renames = {"stock_quantity": "stock_level", "reorder_level": "reorder_threshold"}
    inv_csv = inv_csv.rename(columns={k: v for k, v in inv_renames.items() if k in inv_csv.columns})

    # Normalize warehouse_location casing
    loc_col = "warehouse_location" if "warehouse_location" in inv_csv.columns else None
    if not loc_col:
        return {"locations": [], "transfers": [], "error": "No warehouse_location column in inventory data."}

    inv_csv[loc_col] = inv_csv[loc_col].str.upper().str.strip()
    inv_csv = inv_csv[inv_csv[loc_col].notna() & (inv_csv[loc_col] != "")]

    stock_col = "stock_level" if "stock_level" in inv_csv.columns else "quantity_available"
    if stock_col not in inv_csv.columns:
        return {"locations": [], "transfers": [], "error": "No stock level column found."}

    inv_csv["stock"] = pd.to_numeric(inv_csv[stock_col], errors="coerce").fillna(0)

    # Join with product names
    if prod_csv is not None and not prod_csv.empty:
        sku_col_prod = "sku" if "sku" in prod_csv.columns else ("product_id" if "product_id" in prod_csv.columns else None)
        if sku_col_prod:
            prod_csv["sku"] = prod_csv[sku_col_prod].astype(str).str.upper()
            if "product_name" in prod_csv.columns and "name" not in prod_csv.columns:
                prod_csv = prod_csv.rename(columns={"product_name": "name"})
            name_cols = ["sku"]
            for c in ["name", "category"]:
                if c in prod_csv.columns:
                    name_cols.append(c)
            # Deduplicate product info
            prod_info = prod_csv[name_cols].drop_duplicates(subset=["sku"])
            inv_csv = inv_csv.merge(prod_info, on="sku", how="left")

    # Join with demand forecast for avg_daily_forecast
    if demand_csv is not None and not demand_csv.empty:
        demand_csv["sku"] = demand_csv["sku"].astype(str).str.upper()
        demand_cols = ["sku", "avg_daily_forecast", "forecast_qty_30d"]
        demand_cols = [c for c in demand_cols if c in demand_csv.columns]
        inv_csv = inv_csv.merge(demand_csv[demand_cols], on="sku", how="left")
    else:
        inv_csv["avg_daily_forecast"] = 0
        inv_csv["forecast_qty_30d"] = 0

    inv_csv["avg_daily_forecast"] = pd.to_numeric(inv_csv.get("avg_daily_forecast", 0), errors="coerce").fillna(0)

    # Build per-location summary
    location_summary = (
        inv_csv.groupby(loc_col)
        .agg(
            total_skus=("sku", "nunique"),
            total_stock=("stock", "sum"),
            avg_stock=("stock", "mean"),
        )
        .reset_index()
        .rename(columns={loc_col: "location"})
        .sort_values("total_stock", ascending=False)
        .to_dict(orient="records")
    )

    # Identify store transfer opportunities:
    # SKU present in multiple locations where one has excess and another is low
    transfers = []
    sku_groups = inv_csv.groupby("sku")
    for sku_id, group in sku_groups:
        if len(group) < 2:
            continue  # Need at least 2 locations to transfer

        avg_demand = group["avg_daily_forecast"].iloc[0]
        if avg_demand <= 0:
            continue

        group = group.copy()
        group["days_left"] = group["stock"] / avg_demand

        low_stock = group[group["days_left"] < 14]
        high_stock = group[group["days_left"] >= 30]

        if low_stock.empty or high_stock.empty:
            continue

        for _, low_row in low_stock.iterrows():
            best_source = high_stock.loc[high_stock["stock"].idxmax()]
            surplus = int(best_source["stock"] - avg_demand * 30)  # Keep 30 days at source
            if surplus <= 0:
                continue

            deficit = int(avg_demand * 14 - low_row["stock"])  # Bring to 14 days
            transfer_qty = min(surplus, max(deficit, 1))

            transfers.append({
                "sku": str(sku_id),
                "product_name": str(low_row.get("name", sku_id)),
                "category": str(low_row.get("category", "")),
                "from_location": str(best_source[loc_col]),
                "from_stock": int(best_source["stock"]),
                "to_location": str(low_row[loc_col]),
                "to_stock": int(low_row["stock"]),
                "transfer_qty": transfer_qty,
                "to_days_left": round(low_row["days_left"], 1),
                "urgency": "critical" if low_row["days_left"] < 7 else "warning",
            })

    # Sort transfers by urgency
    transfers.sort(key=lambda t: t["to_days_left"])

    # Build per-location per-SKU detail (top 100 rows)
    detail_cols = ["sku", loc_col, "stock"]
    for c in ["name", "category", "avg_daily_forecast"]:
        if c in inv_csv.columns:
            detail_cols.append(c)
    detail = inv_csv[detail_cols].head(200).rename(columns={loc_col: "location"}).to_dict(orient="records")

    return _safe_json({
        "locations": location_summary,
        "transfers": transfers[:50],
        "detail": detail,
    })


# -----------------------------------------------------------------------------
# Prescription status tracking (action checklist)
# -----------------------------------------------------------------------------
@app.patch("/api/action-plan/prescriptions/{prescription_id}/status")
async def update_prescription_status(prescription_id: str, body: dict):
    """Update the status of a prescription (done/dismissed/pending)."""
    from pydantic import BaseModel

    status = body.get("status", "pending")
    if status not in ("pending", "done", "dismissed"):
        return {"error": f"Invalid status: {status}. Must be pending, done, or dismissed."}

    run_id = body.get("run_id") or get_latest_run_id()
    if not run_id:
        return {"error": "No pipeline run found."}

    try:
        db_upsert_prescription_status(run_id, prescription_id, status)
        return {"ok": True, "prescription_id": prescription_id, "status": status}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/action-plan/prescriptions/statuses")
def get_prescription_statuses_endpoint(run_id: Optional[str] = None):
    """Get all prescription statuses for a run."""
    rid = run_id or get_latest_run_id()
    if not rid:
        return {"statuses": [], "run_id": None}
    statuses = db_get_prescription_statuses(rid)
    return {"statuses": statuses, "run_id": rid}


# -----------------------------------------------------------------------------
# Funnel & Sessions Analytics endpoint
# -----------------------------------------------------------------------------
@app.get("/api/funnel/snapshot")
def get_funnel_snapshot(run_id: Optional[str] = None):
    """Returns funnel analytics aggregated from sessions, events, and funnel_summary."""
    kpi = _load_kpi_snapshot(run_id)
    if not kpi:
        return {"error": "No KPI snapshot found"}

    kpis = kpi.get("kpis", {})
    funnel = kpis.get("conversion_funnel", {})

    # Load funnel_summary for daily trends
    daily_trends = []
    funnel_csv = _CLEANED_DIR / "funnel_summary_cleaned.csv"
    if funnel_csv.is_file():
        try:
            df = pd.read_csv(funnel_csv)
            for col in ["sessions", "product_views", "add_to_cart", "checkout_started", "purchases", "conversion_rate", "cart_abandonment_rate"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"], errors="coerce")
                df = df.sort_values("date")
                daily_trends = _sanitize(df.to_dict(orient="records"))
        except Exception:
            pass

    return _sanitize({
        "funnel_kpis": funnel,
        "daily_trends": daily_trends,
    })


@app.get("/api/sessions/analytics")
def get_sessions_analytics(run_id: Optional[str] = None):
    """Returns session analytics: device, source, landing page breakdowns."""
    sessions_csv = _CLEANED_DIR / "sessions_cleaned.csv"
    if not sessions_csv.is_file():
        return {"error": "No sessions data found"}

    try:
        df = pd.read_csv(sessions_csv)
    except Exception as e:
        return {"error": str(e)}

    result = {}

    # Device breakdown
    if "device_type" in df.columns:
        device_counts = df["device_type"].value_counts().to_dict()
        result["by_device"] = {str(k): int(v) for k, v in device_counts.items()}

        if "converted_flag" in df.columns:
            conv = df["converted_flag"].astype(str).str.lower().isin(["true", "1", "yes"])
            device_conv = df.assign(_conv=conv).groupby("device_type")["_conv"].mean()
            result["conversion_by_device"] = {str(k): round(float(v), 4) for k, v in device_conv.items()}

        if "revenue" in df.columns:
            rev = pd.to_numeric(df["revenue"], errors="coerce")
            device_rev = df.assign(_rev=rev).groupby("device_type")["_rev"].mean()
            result["avg_revenue_by_device"] = {str(k): round(float(v), 2) for k, v in device_rev.items()}

    # Traffic source breakdown
    if "traffic_source" in df.columns:
        source_counts = df["traffic_source"].value_counts().to_dict()
        result["by_traffic_source"] = {str(k): int(v) for k, v in source_counts.items()}

        if "converted_flag" in df.columns:
            conv = df["converted_flag"].astype(str).str.lower().isin(["true", "1", "yes"])
            source_conv = df.assign(_conv=conv).groupby("traffic_source")["_conv"].mean()
            result["conversion_by_source"] = {str(k): round(float(v), 4) for k, v in source_conv.items()}

    # Landing page breakdown
    if "landing_page" in df.columns:
        lp_counts = df["landing_page"].value_counts().to_dict()
        result["by_landing_page"] = {str(k): int(v) for k, v in lp_counts.items()}

        if "converted_flag" in df.columns:
            conv = df["converted_flag"].astype(str).str.lower().isin(["true", "1", "yes"])
            lp_conv = df.assign(_conv=conv).groupby("landing_page")["_conv"].mean()
            result["conversion_by_landing"] = {str(k): round(float(v), 4) for k, v in lp_conv.items()}

    # Session duration distribution
    if "session_duration_sec" in df.columns:
        dur = pd.to_numeric(df["session_duration_sec"], errors="coerce").dropna()
        bins = [0, 60, 180, 300, 600, 900, 1800, float("inf")]
        labels = ["<1min", "1-3min", "3-5min", "5-10min", "10-15min", "15-30min", "30min+"]
        groups = pd.cut(dur, bins=bins, labels=labels, right=False)
        dist = groups.value_counts().sort_index()
        result["session_duration_distribution"] = {str(k): int(v) for k, v in dist.items()}

        if "converted_flag" in df.columns:
            conv = df["converted_flag"].astype(str).str.lower().isin(["true", "1", "yes"])
            dur_conv = df.assign(_dur_group=groups, _conv=conv).groupby("_dur_group")["_conv"].mean()
            result["session_duration_conversion"] = {str(k): round(float(v), 4) for k, v in dur_conv.items()}

    return _sanitize(result)


# -----------------------------------------------------------------------------
# Demographics endpoint
# -----------------------------------------------------------------------------
@app.get("/api/demographics/snapshot")
def get_demographics_snapshot(run_id: Optional[str] = None):
    """Returns customer demographic distributions."""
    kpi = _load_kpi_snapshot(run_id)
    if not kpi:
        return {"error": "No KPI snapshot found"}

    demographics = kpi.get("kpis", {}).get("demographics", {})
    return _sanitize(demographics)


# -----------------------------------------------------------------------------
# Campaign Performance endpoint
# -----------------------------------------------------------------------------
@app.get("/api/campaigns/performance")
def get_campaigns_performance(run_id: Optional[str] = None):
    """Returns campaign-level performance table and channel aggregates."""
    result = {"campaigns": [], "by_channel": {}, "by_type": {}}

    # Campaign performance from cleaned data
    cp_csv = _CLEANED_DIR / "campaign_performance_cleaned.csv"
    if cp_csv.is_file():
        try:
            df = pd.read_csv(cp_csv)
            for col in ["impressions", "clicks", "spend", "sessions", "orders", "attributed_revenue"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")

            # Aggregate per campaign
            if "campaign_id" in df.columns:
                agg = df.groupby(["campaign_id"]).agg(
                    channel=("channel", "first"),
                    campaign_name=("campaign_name", "first"),
                    total_impressions=("impressions", "sum"),
                    total_clicks=("clicks", "sum"),
                    total_spend=("spend", "sum"),
                    total_sessions=("sessions", "sum"),
                    total_orders=("orders", "sum"),
                    total_revenue=("attributed_revenue", "sum"),
                ).reset_index()
                agg["roas"] = agg["total_revenue"] / agg["total_spend"].replace(0, float("nan"))
                agg["cpa"] = agg["total_spend"] / agg["total_orders"].replace(0, float("nan"))
                agg["ctr"] = agg["total_clicks"] / agg["total_impressions"].replace(0, float("nan"))
                result["campaigns"] = _sanitize(agg.sort_values("total_revenue", ascending=False).to_dict(orient="records"))

            # By channel
            if "channel" in df.columns:
                ch = df.groupby("channel").agg(
                    total_spend=("spend", "sum"),
                    total_revenue=("attributed_revenue", "sum"),
                    total_orders=("orders", "sum"),
                ).reset_index()
                ch["roas"] = ch["total_revenue"] / ch["total_spend"].replace(0, float("nan"))
                result["by_channel"] = _sanitize(ch.to_dict(orient="records"))
        except Exception:
            pass

    # Campaign type breakdown from marketing table
    mkt_csv = _CLEANED_DIR / "marketing_cleaned.csv"
    if mkt_csv.is_file():
        try:
            mdf = pd.read_csv(mkt_csv)
            if "campaign_type" in mdf.columns:
                for col in ["ad_spend", "impressions", "clicks", "conversions"]:
                    if col in mdf.columns:
                        mdf[col] = pd.to_numeric(mdf[col], errors="coerce")
                type_agg = mdf.groupby("campaign_type").agg(
                    count=("campaign_id", "count"),
                    total_spend=("ad_spend", "sum"),
                    total_conversions=("conversions", "sum"),
                ).reset_index()
                result["by_type"] = _sanitize(type_agg.to_dict(orient="records"))
        except Exception:
            pass

    # KPI-level marketing metrics
    kpi = _load_kpi_snapshot(run_id)
    if kpi:
        mkt_kpis = kpi.get("kpis", {}).get("marketing_effectiveness", {})
        result["marketing_kpis"] = _sanitize(mkt_kpis)

    return result


# -----------------------------------------------------------------------------
# Brand Performance endpoint
# -----------------------------------------------------------------------------
@app.get("/api/brands/performance")
def get_brands_performance(run_id: Optional[str] = None):
    """Returns brand-level performance metrics."""
    kpi = _load_kpi_snapshot(run_id)
    if not kpi:
        return {"error": "No KPI snapshot found"}

    brand_kpis = kpi.get("kpis", {}).get("brand_performance", {})
    return _sanitize(brand_kpis)


# -----------------------------------------------------------------------------
# Supplier Health endpoint
# -----------------------------------------------------------------------------
@app.get("/api/suppliers/health")
def get_suppliers_health(run_id: Optional[str] = None):
    """Returns supplier-level health metrics."""
    kpi = _load_kpi_snapshot(run_id)
    if not kpi:
        return {"error": "No KPI snapshot found"}

    supplier_kpis = kpi.get("kpis", {}).get("supplier_health", {})
    return _sanitize(supplier_kpis)


# -----------------------------------------------------------------------------
# Payment Health endpoint
# -----------------------------------------------------------------------------
@app.get("/api/payments/health")
def get_payments_health(run_id: Optional[str] = None):
    """Returns payment health metrics."""
    kpi = _load_kpi_snapshot(run_id)
    if not kpi:
        return {"error": "No KPI snapshot found"}

    payment_kpis = kpi.get("kpis", {}).get("payment_health", {})
    return _sanitize(payment_kpis)


# -----------------------------------------------------------------------------
# Net Revenue endpoint
# -----------------------------------------------------------------------------
@app.get("/api/revenue/net")
def get_net_revenue(run_id: Optional[str] = None):
    """Returns net revenue waterfall data."""
    kpi = _load_kpi_snapshot(run_id)
    if not kpi:
        return {"error": "No KPI snapshot found"}

    net_rev = kpi.get("kpis", {}).get("net_revenue", {})
    return _sanitize(net_rev)


# -----------------------------------------------------------------------------
# Chart Narratives endpoint
# -----------------------------------------------------------------------------
@app.get("/api/chart-narratives")
def get_chart_narratives(run_id: Optional[str] = None):
    """Returns natural-language annotations for each dashboard chart."""
    from datetime import datetime, timezone

    # Check local cache
    cache_path = _INSIGHT_DIR / "chart_narratives.json"
    if cache_path.is_file():
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cached = json.load(f)
            if cached and cached.get("narratives"):
                cached["cached"] = True
                return cached
        except Exception:
            pass

    # Gather context
    kpi_data = db_get_run_kpi(run_id) if run_id else db_get_latest_kpi()
    forecast_data = db_get_run_forecast(run_id) if run_id else db_get_latest_forecast()
    insight_data = db_get_run_insight(run_id) if run_id else db_get_latest_insight()
    demand_resp = get_demand_forecast(run_id)
    churn_resp = get_churn_predictions(run_id)

    context_parts = []

    if kpi_data and "error" not in kpi_data:
        cards = kpi_data.get("cards", [])
        card_summary = {c["id"]: {"value": c["value"], "title": c["title"]}
                        for c in cards if isinstance(c, dict) and "id" in c}
        context_parts.append(f"KPIs: {json.dumps(card_summary, default=str)}")

    if forecast_data and "error" not in forecast_data:
        forecasts = forecast_data.get("forecasts", {})
        context_parts.append(f"Revenue forecast: {json.dumps(forecasts.get('forecasted_revenue', {}), default=str)}")
        context_parts.append(f"Churn forecast: {json.dumps(forecasts.get('expected_churn_next_month', {}), default=str)}")

    demand_skus = demand_resp.get("skus", [])
    critical_count = sum(1 for s in demand_skus if s.get("status") == "critical")
    warning_count = sum(1 for s in demand_skus if s.get("status") == "warning")
    context_parts.append(f"Demand: {critical_count} critical SKUs, {warning_count} warning SKUs, {len(demand_skus)} total")

    churn_customers = churn_resp.get("customers", [])
    high_churn = [c for c in churn_customers if (c.get("churn_prob_30d") or 0) >= 0.7]
    total_churn_value = sum(c.get("total_spend", 0) for c in high_churn)
    context_parts.append(f"Churn: {len(high_churn)} high-risk customers, ${total_churn_value:,.0f} at risk")

    if insight_data and "error" not in insight_data:
        insights = insight_data.get("insights", []) if isinstance(insight_data, dict) else []
        insight_titles = [i.get("title", "") for i in insights[:5]]
        context_parts.append(f"Top insights: {json.dumps(insight_titles)}")

    context = "\n".join(context_parts)

    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import SystemMessage, HumanMessage

        system_prompt = """You are a retail doctor generating chart annotations. For each chart below, write:
1. A 1-2 sentence narrative explaining what the data shows in plain English
2. An action hint starting with "Action:" that tells the store owner what to do

Return valid JSON with this structure:
{
  "revenue_trend": {"narrative": "...", "action_hint": "..."},
  "revenue_by_channel": {"narrative": "...", "action_hint": "..."},
  "stock_health": {"narrative": "...", "action_hint": "..."},
  "demand_forecast": {"narrative": "...", "action_hint": "..."},
  "customer_segments": {"narrative": "...", "action_hint": "..."},
  "churn_distribution": {"narrative": "...", "action_hint": "..."},
  "top_products": {"narrative": "...", "action_hint": "..."},
  "marketing_channels": {"narrative": "...", "action_hint": "..."}
}

Use specific numbers. Be concise. Every action_hint must start with an action verb."""

        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Business data:\n{context}"),
        ])

        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        narratives = json.loads(content)

        result = {
            "narratives": narratives,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "cached": False,
        }

        # Cache locally
        os.makedirs(str(_INSIGHT_DIR), exist_ok=True)
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, default=str)

        return result

    except Exception as e:
        return {"narratives": {}, "error": str(e), "cached": False}


# -----------------------------------------------------------------------------
# Entry point: run the API server
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    # When you run: python app.py
    # -> it starts FastAPI, and the multi-agent pipeline runs automatically.
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
