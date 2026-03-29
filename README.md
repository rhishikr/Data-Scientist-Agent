# Data Scientist Agent

An AI-driven retail analytics platform that uses a **7-agent pipeline** to automatically clean, analyze, and generate insights from retail data. It combines multi-agent orchestration, machine learning forecasting, and a RAG-powered chat assistant — all presented through an interactive React dashboard.

## Architecture at a Glance

```
┌──────────────────┐         ┌──────────────────────────────────────┐
│   React / Vite   │  REST   │           FastAPI Backend            │
│   Frontend SPA   │◄───────►│                                      │
│                  │   SSE   │  ┌─────────────────────────────────┐ │
│  - Dashboard     │         │  │     7-Agent Pipeline            │ │
│  - Pipeline View │         │  │  Cleaning → Features →          │ │
│  - Chat (RAG)    │         │  │  Hypothesis → Insights →        │ │
│  - Data Explorer │         │  │  KPI → Forecast → Action        │ │
│                  │         │  └─────────────────────────────────┘ │
│                  │         │  ┌─────────────────────────────────┐ │
│                  │         │  │     RAG Chat System             │ │
│                  │         │  │  pgvector + SQL Agent + LLM     │ │
│                  │         │  └─────────────────────────────────┘ │
└──────────────────┘         └──────────────┬───────────────────────┘
                                            │
                                  ┌─────────▼─────────┐
                                  │     Supabase       │
                                  │  PostgreSQL +      │
                                  │  pgvector +        │
                                  │  Object Storage    │
                                  └───────────────────┘
```

## Quick Start

1. **Clone** the repository
2. **Configure** environment variables in `backend/.env` and `frontend/.env` (see [Getting Started](docs/getting-started.md))
3. **Install dependencies**: `pip install -r backend/requirements.txt` and `cd frontend && npm install`
4. **Run database migrations**: `cd backend && python -m db.setup`
5. **Start both servers**: `bash start.sh`

For a complete walkthrough, see [docs/getting-started.md](docs/getting-started.md).

## Repository Structure

```
Data-Scientist-Agent/
├── backend/                    # FastAPI backend (Python)
│   ├── app.py                  # Main API server (40+ endpoints)
│   ├── agents/                 # 7 AI agents + orchestrator + blackboard
│   ├── pipeline/               # Data processing logic (cleaning, features, etc.)
│   ├── rag/                    # RAG chat system (pgvector, SQL agent, memory)
│   ├── db/                     # Supabase database layer + migrations
│   ├── models/                 # Pre-trained ML models (.joblib)
│   ├── scripts/                # Data generation & migration scripts
│   └── requirements.txt        # Python dependencies
├── frontend/                   # React SPA (TypeScript / Vite)
│   ├── src/
│   │   ├── App.tsx             # Root component + sidebar navigation
│   │   ├── components/         # All UI components (screens, charts, chat)
│   │   ├── contexts/           # AuthContext (password-based auth)
│   │   └── lib/                # API client utilities
│   └── package.json            # Node.js dependencies
├── docs/                       # Developer documentation
├── start.sh                    # Start both backend + frontend
├── generate_data.sh            # Generate synthetic retail data
└── update_data.sh              # Simulate data updates with scenarios
```

## Documentation

| Document | Description |
|---|---|
| [Getting Started](docs/getting-started.md) | Prerequisites, installation, environment setup, first run |
| [Architecture](docs/architecture.md) | System design, data flows, design patterns |
| [Agents & Pipeline](docs/agents-and-pipeline.md) | 7-agent system, orchestrator, blackboard pattern |
| [Backend API](docs/backend-api.md) | All REST endpoints grouped by domain |
| [RAG System](docs/rag-system.md) | Chat system: vector search, SQL agent, routing |
| [Database](docs/database.md) | Supabase schema, migrations, storage layer |
| [Frontend](docs/frontend.md) | React app structure, screens, data fetching |
| [Data & Scripts](docs/data-and-scripts.md) | Synthetic data, shell scripts, pipeline modules |
| [Contributing](docs/contributing.md) | Development workflow, conventions, useful commands |

## Tech Stack

| Backend | Frontend |
|---|---|
| Python 3.11+ | React 18 + TypeScript |
| FastAPI + Uvicorn | Vite (build tool) |
| LangChain + OpenAI | Tailwind CSS + shadcn/ui (Radix) |
| Scikit-learn, SciPy, Pandas | Recharts (data visualization) |
| Supabase (PostgreSQL + pgvector) | Lucide React (icons) |
| Featuretools, Great Expectations | Sonner (toast notifications) |
| LangGraph (agent framework) | React Markdown |
