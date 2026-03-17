# System Architecture

This document provides a big-picture view of how the Data Scientist Agent system is designed and how data flows through it.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Browser                                    │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                  React SPA (Vite + TypeScript)                │  │
│  │                                                               │  │
│  │  LoginPage ──► Sidebar Nav ──► Screen Components              │  │
│  │                                  │                            │  │
│  │              ┌───────────────────┼──────────────────┐         │  │
│  │              │                   │                  │         │  │
│  │         PipelineScreen    InsightsScreen    ChatAssistant     │  │
│  │          (SSE stream)     (REST polling)    (SSE stream)      │  │
│  └──────────────┬──────────────────┬──────────────────┬─────────┘  │
└─────────────────┼──────────────────┼──────────────────┼─────────────┘
                  │ SSE              │ REST             │ SSE
                  ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     FastAPI Backend (app.py)                         │
│                                                                     │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │ Pipeline Engine   │  │ Snapshot API     │  │ RAG System       │  │
│  │                   │  │                  │  │                  │  │
│  │ Orchestrator      │  │ KPI endpoints    │  │ Router           │  │
│  │ 7 Agents          │  │ Forecast series  │  │ pgvector store   │  │
│  │ Blackboard        │  │ Insights         │  │ SQL Agent        │  │
│  │ LLM reasoning     │  │ Run management   │  │ Chat memory      │  │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘  │
│           │                     │                      │            │
│           └─────────────────────┼──────────────────────┘            │
│                                 │                                   │
│                    ┌────────────▼────────────┐                      │
│                    │   Database Layer (db/)   │                      │
│                    │   store.py + raw_store   │                      │
│                    │   + supabase_client      │                      │
│                    └────────────┬────────────┘                      │
└─────────────────────────────────┼───────────────────────────────────┘
                                  │
                       ┌──────────▼──────────┐
                       │      Supabase       │
                       │                     │
                       │  PostgreSQL tables   │
                       │  pgvector extension  │
                       │  Storage bucket      │
                       │  (pipeline-artifacts)│
                       └─────────────────────┘
```

## Monorepo Layout

The project is a simple two-folder monorepo with no shared packages:

```
Data-Scientist-Agent/
├── backend/     # Python (FastAPI) — all server-side code
├── frontend/    # TypeScript (React/Vite) — all client-side code
├── start.sh     # Starts both servers
└── docs/        # This documentation
```

There is no mono-repo tooling (like Turborepo or Nx). The backend and frontend are started independently (or together via `start.sh`).

## Backend Subsystems

The backend has four major subsystems:

### 1. Agent Pipeline (`backend/agents/` + `backend/pipeline/`)

A sequential 7-agent system that processes raw retail data through cleaning, feature engineering, hypothesis testing, insight generation, KPI computation, forecasting, and action planning.

Each agent follows the **Perceive → Reason → Act** cycle, using an LLM for the reasoning step.

See [agents-and-pipeline.md](agents-and-pipeline.md) for details.

### 2. RAG System (`backend/rag/`)

A Retrieval-Augmented Generation system that lets users ask natural language questions about their data. Queries are routed to one of four paths: snapshot lookup, SQL query, vector similarity search, or hybrid.

See [rag-system.md](rag-system.md) for details.

### 3. Database Layer (`backend/db/`)

All persistence goes through Supabase (PostgreSQL). The `store.py` module handles pipeline results (snapshots, artifacts, runs), while `raw_store.py` manages raw data uploads/downloads.

See [database.md](database.md) for details.

### 4. API Layer (`backend/app.py` + `backend/rag/api.py`)

40+ REST endpoints organized by domain: pipeline execution, data management, snapshot retrieval, run management, analytics, and RAG chat. Uses SSE (Server-Sent Events) for real-time pipeline progress and chat streaming.

See [backend-api.md](backend-api.md) for details.

## Frontend Architecture

The frontend is a React SPA with **no client-side router** (no React Router). Navigation works through a simple state variable:

1. `App.tsx` holds an `activeSection` state variable
2. Sidebar buttons call `setActiveSection("section-id")`
3. A `switch` statement in `renderContent()` returns the matching screen component
4. Default view: `CustomerInsightsScreen`

Authentication is handled by `AuthContext`, which checks a password from the `VITE_APP_PASSWORD` environment variable and stores auth state in `sessionStorage`.

The frontend uses **shadcn/ui** (built on Radix UI primitives) for UI components, **Tailwind CSS** for styling, and **Recharts** for data visualization.

See [frontend.md](frontend.md) for details.

## End-to-End Data Flow

### Pipeline Flow

```
1. Raw data generated     →  12 CSV files (customers, products, transactions, etc.)
       │
2. Uploaded to Supabase   →  raw_* tables + pipeline-artifacts bucket
       │
3. Pipeline triggered     →  POST /api/pipeline/run
       │
4. Orchestrator starts    →  Downloads raw data from Supabase to temp dirs
       │
5. Agents execute         →  Cleaning → Features → Hypothesis → Insights
   sequentially              → KPI → Forecast → Action
       │
6. Results stored         →  Snapshot tables in Supabase (kpi_snapshots,
                              forecast_snapshots, insight_snapshots, etc.)
       │
7. RAG index rebuilt      →  Pipeline outputs ingested into pgvector
       │
8. Frontend fetches       →  REST calls to snapshot endpoints
       │
9. Dashboard renders      →  Charts, KPI cards, insights, prescriptions
```

### RAG Chat Flow

```
1. User asks a question        →  "What is our revenue trend?"
       │
2. Router classifies query     →  snapshot | sql | insight | hybrid
       │
3a. Snapshot path              →  Direct KPI/forecast lookup (fast)
3b. SQL path                   →  LangChain SQL agent queries database
3c. Insight path               →  pgvector similarity search
3d. Hybrid path                →  Combines SQL + vector results
       │
4. LLM synthesizes answer     →  Contextualizes retrieved data
       │
5. Streamed to frontend       →  SSE chunks rendered in ChatAssistant
```

## Key Design Patterns

### Blackboard Pattern

The `SharedBlackboard` (`backend/agents/blackboard.py`) is a central data store that all agents read from and write to. It holds:
- **config** — pipeline settings (reset flag, alpha for hypothesis testing, run_id)
- **paths** — temp directory locations for each pipeline stage
- **data_state** — output metadata from each agent (passed to downstream agents)
- **llm_decisions** — log of all LLM reasoning (for transparency)
- **agent_results** — execution results keyed by agent ID
- **messages** — inter-agent message bus

### Perceive → Reason → Act

Every agent follows a three-phase cycle defined by `BaseAgent`:
1. **Perceive** — examine the blackboard, gather inputs, profile the data
2. **Reason** — call the LLM to decide strategy/parameters
3. **Act** — execute the actual data processing, write results to blackboard

### Server-Sent Events (SSE)

Two SSE streams keep the frontend updated in real time:
- **Pipeline progress** (`/api/pipeline/stream`) — broadcasts `agent_started`, `agent_completed`, `pipeline_complete` events as agents execute
- **RAG chat** (`/api/rag/chat/stream`) — streams LLM response chunks as they're generated

### Temp Directory Isolation

Each pipeline run creates isolated temp directories (`tempfile.mkdtemp()`). Raw data is downloaded from Supabase into these dirs, agents process data there, and results are uploaded back to Supabase. The temp dirs are cleaned up after the run completes. This ensures pipeline runs don't interfere with each other or pollute the project directory.
