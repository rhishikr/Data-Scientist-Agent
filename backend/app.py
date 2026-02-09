from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pipeline.hypothesis.runner import run_hypothesis_agent
from pipeline.insights.runner import run_insights 
from pipeline.kpi.runner import run_kpi_snapshot
from pipeline.kpi.io import DataPaths, read_json

app = FastAPI(title="Hypothesis + Insights Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    return bundle.to_dict()

@app.get("/api/kpis/run")
def run_kpis_endpoint():
    root = Path(__file__).resolve().parent
    snap = run_kpi_snapshot(root)
    return snap.to_dict()

@app.get("/api/kpis/current")
def get_current_kpis():
    root = Path(__file__).resolve().parent
    paths = DataPaths(base_dir=root)
    return read_json(paths.kpi_dir / "kpi_snapshot.json")