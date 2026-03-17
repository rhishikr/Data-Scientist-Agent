# Getting Started

This guide walks you through setting up and running the Data Scientist Agent locally.

## Prerequisites

- **Python 3.11+** (with `pip`)
- **Node.js 18+** (with `npm`)
- **A Supabase project** — free tier works. Create one at [supabase.com](https://supabase.com)
- **An OpenAI API key** — from [platform.openai.com](https://platform.openai.com)
- **Git Bash or WSL** (on Windows) — the shell scripts use Bash

## 1. Clone & Install

```bash
git clone <repository-url>
cd Data-Scientist-Agent
```

### Backend

```bash
cd backend
python -m venv venv

# Windows (Git Bash)
source venv/Scripts/activate

# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

### Frontend

```bash
cd frontend
npm install
```

## 2. Environment Configuration

### Backend (`backend/.env`)

Create `backend/.env` using `backend/.env.example` as a template:

```bash
cp backend/.env.example backend/.env
```

| Variable | Description | Where to get it |
|---|---|---|
| `OPENAI_API_KEY` | OpenAI API key for LLM calls | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |
| `SUPABASE_URL` | Your Supabase project URL | Supabase Dashboard → Settings → API |
| `SUPABASE_SERVICE_KEY` | Service role key (full access) | Supabase Dashboard → Settings → API → `service_role` key |
| `SUPABASE_DB_URL` | Direct PostgreSQL connection string | Supabase Dashboard → Settings → Database → Connection string (URI) |
| `ALLOWED_ORIGINS` | CORS origins (comma-separated) | Default: `http://localhost:3000,http://localhost:3001,http://localhost:5173` |
| `RAG_LLM_MODEL` | LLM model for agent reasoning and RAG | Default: `gpt-4.1-mini` |
| `RAG_EMBED_MODEL` | Embedding model for vector search | Default: `text-embedding-3-small` |
| `API_SECRET_KEY` | API key for authenticating frontend requests | Choose any string; must match `VITE_API_KEY` in frontend |

### Frontend (`frontend/.env`)

Create `frontend/.env`:

```env
VITE_API_URL=http://127.0.0.1:8000
VITE_API_KEY=<same value as API_SECRET_KEY in backend>
VITE_APP_PASSWORD=<choose a login password>
```

| Variable | Description |
|---|---|
| `VITE_API_URL` | Backend base URL (default: `http://127.0.0.1:8000`) |
| `VITE_API_KEY` | Must match `API_SECRET_KEY` in backend `.env` |
| `VITE_APP_PASSWORD` | Password for the frontend login screen |

## 3. Database Setup

The project uses Supabase (managed PostgreSQL). You need to run the migration SQL files to create the required tables.

### Option A: Automated (recommended)

```bash
cd backend
python -m db.setup
```

This runs all migration files in `db/migrations/` using the Supabase `exec_sql` RPC function.

### Option B: Manual

If the automated approach fails, run each SQL file manually in the **Supabase SQL Editor** (Dashboard → SQL Editor):

1. `db/migrations/001_init.sql` — Core tables (pipeline_runs, snapshots)
2. `db/migrations/002_disable_rls.sql` — Disable row-level security
3. `db/migrations/003_storage_policies.sql` — Storage bucket policies
4. `db/migrations/004_ai_analysis.sql` — AI analysis results table
5. `db/migrations/005_raw_datasets.sql` — Raw dataset metadata
6. `db/migrations/006_rag_pgvector.sql` — pgvector extension + embedding tables
7. `db/migrations/007_pipeline_current_agent.sql` — Pipeline progress tracking

> **Important:** Migration `006` enables the `pgvector` extension. Make sure it's available in your Supabase project (it's enabled by default on most plans).

## 4. Generate Seed Data

Generate synthetic retail data and upload it to Supabase:

```bash
# From the project root
bash generate_data.sh
```

This creates 12 CSV files (customers, products, transactions, etc.) in `backend/data/raw/`.

Then upload the generated data to Supabase:

```bash
cd backend
python scripts/migrate_raw_to_supabase.py
```

## 5. Running the Application

### Using the start script (recommended)

```bash
# From the project root
bash start.sh
```

This starts the backend first, waits for it to be ready, then starts the frontend.

### Manual start

**Terminal 1 — Backend:**
```bash
cd backend
source venv/Scripts/activate  # or venv/bin/activate on macOS/Linux
python app.py
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm run dev
```

### Access the application

- **Backend API docs (Swagger):** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Frontend app:** [http://localhost:5173](http://localhost:5173)
- Log in with the password you set in `VITE_APP_PASSWORD`

## 6. Verify Everything Works

1. Open [http://localhost:8000/docs](http://localhost:8000/docs) — you should see the FastAPI Swagger UI
2. Open [http://localhost:5173](http://localhost:5173) — you should see a login page
3. Log in with your `VITE_APP_PASSWORD`
4. Navigate to **Settings** and click "Generate Data" to verify the Supabase connection
5. Navigate to **Agent Pipeline** and run a pipeline to see the full system in action

## Common Issues

| Problem | Solution |
|---|---|
| `SUPABASE_URL and SUPABASE_SERVICE_KEY must be set` | Check that `backend/.env` exists and has both variables |
| Port 8000 already in use | Kill the existing process or change the port in `app.py` |
| Port 5173 already in use | Run `npx vite --port 3000` instead |
| `pgvector` extension not found | Enable it in Supabase: Dashboard → Database → Extensions → search "vector" → Enable |
| `ReadError` or `10035` connection errors | These are transient Supabase errors — the app retries automatically. Check your internet connection |
| Frontend shows blank page | Check browser console for errors; verify `VITE_API_URL` points to the running backend |
| Login doesn't work | Ensure `VITE_APP_PASSWORD` is set in `frontend/.env` and restart the Vite dev server |
| `ModuleNotFoundError` in backend | Make sure the virtual environment is activated and all dependencies are installed |
