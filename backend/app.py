from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from pipeline.hypothesis.runner import run_hypothesis_agent
from pipeline.insights.runner import run_insights
from pipeline.kpi.runner import run_kpi_snapshot
from pipeline.kpi.io import DataPaths
from pipeline.forecast.runner import run_forecasting
from pipeline.forecast.io import ForecastPaths
from rag.api import router as rag_router

# from pipeline.insights import run_customer_insights
# from chat.customer_chat import answer_customer_question


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

    # -------------------------------------------------------------------------
    # Reset
    # -------------------------------------------------------------------------
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

    # -------------------------------------------------------------------------
    # 1. CLEANING
    # -------------------------------------------------------------------------
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

    # -------------------------------------------------------------------------
    # 2. FEATURE ENGINEERING
    # -------------------------------------------------------------------------
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

    # -------------------------------------------------------------------------
    # 3. HYPOTHESIS TESTING
    # -------------------------------------------------------------------------
    print("\n--- HYPOTHESIS TESTING ---")
    run_hypothesis_agent(alpha=alpha)

    # -------------------------------------------------------------------------
    # 4. INSIGHTS
    # -------------------------------------------------------------------------
    print("\n--- INSIGHTS ---")
    run_insights(project_root)

    # -------------------------------------------------------------------------
    # 5. KPI SNAPSHOT
    # -------------------------------------------------------------------------
    print("\n--- KPI SNAPSHOT ---")
    run_kpi_snapshot(DataPaths.default())

    # -------------------------------------------------------------------------
    # 6. FORECASTING
    # -------------------------------------------------------------------------
    print("\n--- FORECASTING ---")
    run_forecasting(ForecastPaths.default())

    print("\n=== PIPELINE COMPLETE ===")


# -----------------------------------------------------------------------------
# Entry point
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    run_pipeline(reset=True)
