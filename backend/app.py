from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from pipeline.hypothesis.runner import run_hypothesis_agent
from pipeline.insights.runner import run_insights 
from pipeline.kpi.runner import run_kpi_snapshot
from pipeline.kpi.io import DataPaths, read_json
from pipeline.forecast.runner import run_forecasting
from pipeline.forecast.io import ForecastPaths
from rag.api import router as rag_router

from pipeline.insights import run_customer_insights
from chat.customer_chat import answer_customer_question

app = FastAPI(title="AI Data Scientist Backend (MVP)")
app.include_router(rag_router) # router def

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

@app.get("/api/customer-insights")
def customer_insights(days: int = Query(30, ge=7, le=365)):
    return run_customer_insights(days=days)

@app.post("/api/customer-insights/chat")
def customer_chat(payload: dict):
    """
    payload = { "message": "...", "days": 30 }
    """
    return answer_customer_question(payload)

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

@app.get("/api/kpi/run")
def run_kpis():
    """
    Computes KPI snapshot and writes outputs to:
      backend/data/kpi_outputs/*
    """
    return run_kpi_snapshot(DataPaths.default())


@app.get("/api/kpi/snapshot")
def get_kpi_snapshot():
    """
    Returns the latest KPI snapshot JSON if it exists.
    """
    from pipeline.kpi.io import read_json
    paths = DataPaths.default()
    snap_path = Path(paths.out_dir) / "kpi_snapshot.json"
    payload = read_json(str(snap_path))
    return payload or {"error": "kpi_snapshot.json not found. Run /api/kpi/run first."}


@app.get("/api/forecast/run")
def run_forecast():
    """
    Trains/loads forecasting models and writes outputs to:
      backend/data/forecast_outputs/*
    Also saves model artifacts to:
      backend/models/*
    """
    return run_forecasting(ForecastPaths.default())


@app.get("/api/forecast/snapshot")
def get_forecast_snapshot():
    """
    Returns latest forecast snapshot JSON if it exists.
    """
    paths = ForecastPaths.default()
    snap_path = Path(paths.out_dir) / "forecast_snapshot.json"
    payload = read_json(str(snap_path))
    return payload or {"error": "forecast_snapshot.json not found. Run /api/forecast/run first."}