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

# Mount your RAG endpoints if you have them
app.include_router(rag_router, prefix="/api/rag", tags=["rag"])


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

    demand_csv["sku"] = demand_csv["sku"].astype(str)

    if inv_csv is not None and not inv_csv.empty:
        inv_csv["sku"] = inv_csv["sku"].astype(str)
        inv_cols = ["sku", "stock_level", "reorder_threshold"]
        inv_cols = [c for c in inv_cols if c in inv_csv.columns]
        demand_csv = demand_csv.merge(inv_csv[inv_cols], on="sku", how="left")

    if prod_csv is not None and not prod_csv.empty:
        sku_col_prod = "sku" if "sku" in prod_csv.columns else ("product_id" if "product_id" in prod_csv.columns else None)
        if sku_col_prod:
            prod_csv["sku"] = prod_csv[sku_col_prod].astype(str)
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
            if r["avg_daily_forecast"] > 0 else None,
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
# Entry point: run the API server
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    # When you run: python app.py
    # -> it starts FastAPI, and the multi-agent pipeline runs automatically.
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
