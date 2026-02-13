from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pipeline.hypothesis.runner import run_hypothesis_agent
from pipeline.insights.runner import run_insights
from pipeline.kpi.runner import run_kpi_snapshot
from pipeline.kpi.io import DataPaths, read_json
from pipeline.forecast.runner import run_forecasting
from pipeline.forecast.io import ForecastPaths

from rag.api import router as rag_router


# -----------------------------------------------------------------------------
# Helpers
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
# Main pipeline
# -----------------------------------------------------------------------------
def run_pipeline(reset: bool = True, alpha: float = 0.05):
    print("\n=== STARTING FULL PIPELINE ===")

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

# CORS (adjust ports/origins as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount your RAG endpoints if you have them
app.include_router(rag_router, prefix="/api/rag", tags=["rag"])


# -----------------------------------------------------------------------------
# Run pipeline automatically on server start
# -----------------------------------------------------------------------------
@app.on_event("startup")
def startup_run_pipeline():
    """
    When the FastAPI server starts, run the full pipeline automatically.
    You can control behavior via env vars:

    - RUN_PIPELINE_ON_START=1 (default) to run
    - PIPELINE_RESET=1 (default) to reset outputs each start
    """
    run_on_start = os.getenv("RUN_PIPELINE_ON_START", "1") == "1"
    if not run_on_start:
        print("RUN_PIPELINE_ON_START=0 -> skipping pipeline on startup.")
        return

    reset = os.getenv("PIPELINE_RESET", "1") == "1"
    alpha_str = os.getenv("HYPOTHESIS_ALPHA", "0.05")
    try:
        alpha = float(alpha_str)
    except ValueError:
        alpha = 0.05

    try:
        run_pipeline(reset=reset, alpha=alpha)
    except Exception as e:
        # IMPORTANT: don't crash the API server if pipeline fails
        print(f"[startup] Pipeline failed: {e}")


# -----------------------------------------------------------------------------
# Small helper: read JSON safely
# -----------------------------------------------------------------------------
def _read_json_file(path: Path) -> dict:
    payload = read_json(str(path))
    if payload:
        return payload
    return {"error": f"{path.name} not found. Run pipeline or /api/*/run first."}


# -----------------------------------------------------------------------------
# Endpoints (RUN)
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
# Endpoints (SNAPSHOTS / READ OUTPUTS)
# -----------------------------------------------------------------------------
@app.get("/api/kpi/snapshot")
def get_kpi_snapshot():
    """
    Returns the latest KPI snapshot JSON if it exists.
    """
    paths = DataPaths.default()
    snap_path = Path(paths.out_dir) / "kpi_snapshot.json"
    return _read_json_file(snap_path)


@app.get("/api/forecast/snapshot")
def get_forecast_snapshot():
    """
    Returns latest forecast snapshot JSON if it exists.
    """
    paths = ForecastPaths.default()
    snap_path = Path(paths.out_dir) / "forecast_snapshot.json"
    return _read_json_file(snap_path)


@app.get("/api/insights/snapshot")
def get_insights_snapshot():
    """
    Returns latest insights JSON if it exists.
    """
    project_root = Path(__file__).resolve().parent
    snap_path = project_root / "data" / "insight_outputs" / "insights.json"
    return _read_json_file(snap_path)


@app.get("/api/hypothesis/snapshot")
def get_hypothesis_snapshot():
    """
    Returns latest hypothesis results JSON if it exists.
    """
    project_root = Path(__file__).resolve().parent
    snap_path = project_root / "data" / "hypothesis_outputs" / "hypothesis_results.json"
    return _read_json_file(snap_path)


# -----------------------------------------------------------------------------
# Entry point: run the API server
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    # When you run: python app.py
    # -> it starts FastAPI, and the pipeline runs automatically via startup event.
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
