# Backend API Reference

This document lists all REST endpoints exposed by the FastAPI backend. The server runs on `http://localhost:8000` by default.

Interactive Swagger documentation is available at [http://localhost:8000/docs](http://localhost:8000/docs).

## Authentication

All endpoints (except Swagger docs and CORS preflight) require an API key. Pass it via:

- **Header:** `X-API-Key: <your-key>`
- **Query param:** `?api_key=<your-key>`

The key is validated against the `API_SECRET_KEY` environment variable in `backend/.env`.

Exempt routes: `OPTIONS` (CORS preflight), `/docs`, `/openapi.json`, `/redoc`.

**Implementation:** `api_key_guard` middleware in `backend/app.py`.

---

## Data Management

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/data/status` | Row counts for all raw data tables in Supabase |
| `POST` | `/api/data/generate` | Generate fresh synthetic data (12 CSV files) and upload to Supabase |
| `POST` | `/api/data/update` | Simulate data update. Body: `{"days": 7, "scenario": "organic-growth"}` |
| `DELETE` | `/api/data/delete` | Delete all raw data from Supabase |

### Available scenarios for `/api/data/update`:
`organic-growth`, `profit`, `loss`, `seasonal-spike`, `stockout-crisis`, `marketing-blitz`, `churn-wave`, `new-product-launch`

---

## Pipeline Execution

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/pipeline/run` | Trigger the 7-agent pipeline. Returns immediately with `run_id` |
| `GET` | `/api/pipeline/status` | Current pipeline status (survives tab refresh) |
| `GET` | `/api/pipeline/stream` | SSE stream for real-time pipeline progress |
| `GET` | `/api/pipeline/stream/subscribe` | Reconnect to a running pipeline (replays completed agents) |
| `GET` | `/api/pipeline/decisions` | All LLM decisions made during the current/last pipeline run |

### SSE Event Format (`/api/pipeline/stream`)

Events are sent as `data: {JSON}\n\n` with these event types:

```
pipeline_started    → {"event": "pipeline_started", "total_agents": 7, "run_id": "..."}
agent_started       → {"event": "agent_started", "agent_name": "...", "step": 1, "progress_pct": 0}
agent_completed     → {"event": "agent_completed", "agent_name": "...", "success": true, "duration": 12.5, "step": 1, "progress_pct": 14}
agent_error         → {"event": "agent_error", "agent_id": "...", "error": "..."}
pipeline_complete   → {"event": "pipeline_complete", "total_duration_seconds": 120, "agents": {...}, "run_id": "..."}
```

---

## Snapshot Endpoints

All snapshot endpoints accept an optional `?run_id=` query parameter. Without it, they return the latest run's data.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/kpi/snapshot` | KPI cards (revenue, AOV, churn rate, conversion, etc.) |
| `GET` | `/api/forecast/snapshot` | Forecast results (revenue, demand, churn predictions) |
| `GET` | `/api/insights/snapshot` | Business insights bundle |
| `GET` | `/api/hypothesis/snapshot` | Hypothesis test results (significant findings) |

---

## Forecast Series

Detailed timeseries and per-entity forecast data. All accept optional `?run_id=`.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/forecast/series/revenue` | Revenue forecast timeseries (30d, 60d, 90d) |
| `GET` | `/api/forecast/series/demand` | Demand forecast by SKU |
| `GET` | `/api/forecast/series/churn` | Churn predictions with customer details |
| `GET` | `/api/forecast/series/demand-by-location` | Demand forecast grouped by geographic location |

---

## Run Management

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/runs` | List all pipeline runs with timestamps and status |
| `GET` | `/api/runs/{run_id}` | Get specific run details |
| `DELETE` | `/api/runs/{run_id}` | Delete a pipeline run and its snapshots |
| `GET` | `/api/runs/compare` | Compare KPI snapshots between two runs. Query: `?run_a=...&run_b=...` |
| `GET` | `/api/runs/compare/ai-analysis` | LLM-generated comparison analysis between two runs |

---

## Insights & Actions

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/insights/ai-analysis` | Cached or freshly generated LLM analysis of insights. Optional `?run_id=` |
| `GET` | `/api/action-plan` | Prioritized action items (prescriptions) from ActionAgent |
| `PATCH` | `/api/action-plan/prescriptions/{id}/status` | Update prescription status. Body: `{"status": "done"}` |
| `GET` | `/api/action-plan/prescriptions/statuses` | Get all prescription statuses |
| `GET` | `/api/chart-narratives` | AI-generated narrative descriptions for dashboard charts |

---

## Data Explorer

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/cleaned-data` | Cleaned dataset previews (columns, stats, sample rows). Optional `?run_id=` |
| `GET` | `/api/featured-data` | Feature-engineered dataset previews. Optional `?run_id=` |

---

## Analytics

Additional analytics endpoints derived from pipeline data. All accept optional `?run_id=`.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/funnel/snapshot` | Conversion funnel metrics (visitors → leads → customers) |
| `GET` | `/api/sessions/analytics` | Session-level analytics (duration, bounce rate, pages per session) |
| `GET` | `/api/demographics/snapshot` | Customer demographics breakdown |
| `GET` | `/api/campaigns/performance` | Marketing campaign ROI, CPA, CTR metrics |
| `GET` | `/api/brands/performance` | Brand performance metrics |
| `GET` | `/api/suppliers/health` | Supplier health scores |
| `GET` | `/api/payments/health` | Payment processing health metrics |
| `GET` | `/api/revenue/net` | Net revenue metrics |

---

## RAG Chat Endpoints

Mounted at `/api/rag/`. See also [rag-system.md](rag-system.md) for architecture details.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/rag/health` | RAG system health check |
| `POST` | `/api/rag/ingest` | Rebuild the pgvector index from latest pipeline outputs |
| `POST` | `/api/rag/chat` | Answer a question (synchronous). Body: `{"question": "...", "session_id": "default"}` |
| `POST` | `/api/rag/chat/stream` | Answer with SSE streaming. Same body as `/chat` |
| `GET` | `/api/rag/history?session_id=default` | Get chat history for a session (last 50 messages) |
| `GET` | `/api/rag/sessions` | List all chat sessions with previews |
| `DELETE` | `/api/rag/sessions/{session_id}` | Delete a chat session |
| `POST` | `/api/rag/schema` | Get database schema help. Body: `{"question": "..."}` |

### Chat Response Format

```json
{
  "answer": "Revenue increased by 15% last month...",
  "query_type": "sql",
  "success": true,
  "timestamp": "2025-01-15T10:30:00",
  "sources": [{"source": "kpi_snapshots", "source_id": "run_abc123"}]
}
```

### Chat Stream Format (SSE)

```
data: {"event": "start", "query_type": "sql"}
data: {"event": "chunk", "content": "Revenue "}
data: {"event": "chunk", "content": "increased by "}
data: {"event": "chunk", "content": "15%..."}
data: {"event": "sources", "sources": [...]}
```

---

## Legacy Pipeline Endpoints

These run individual pipeline stages directly (without the agent system). Kept for backward compatibility but not used by the frontend.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/hypothesis/run` | Run hypothesis testing directly |
| `GET` | `/api/insights/run` | Run insights generation directly |
| `GET` | `/api/kpi/run` | Run KPI computation directly |
| `GET` | `/api/forecast/run` | Run forecasting directly |
