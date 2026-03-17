# Contributing

This document covers the development workflow, code conventions, and practical patterns for developers working on this project.

## Branch Strategy

The project uses a PR-based workflow with three key branches:

- `dev` — stable development branch, all feature PRs target this
- `prod` — production branch, updated from `dev` after features are confirmed
- Feature branches — create a branch for each feature or fix, open a PR to `dev`

```bash
git checkout dev
git checkout -b feature/my-feature
# ... make changes ...
git push -u origin feature/my-feature
# Open PR targeting dev on GitHub
```

Once features are tested and confirmed on `dev`, they are promoted to `prod` for production deployment.

## Code Organization

### Backend (`backend/`)

| Directory | Purpose | When to add here |
|---|---|---|
| `agents/` | AI agent classes (one file per agent) | Adding a new pipeline agent |
| `pipeline/` | Data processing logic (cleaning, features, etc.) | Adding data processing capabilities |
| `rag/` | RAG chat system (router, memory, vector store, etc.) | Modifying the chat/Q&A system |
| `db/` | Database access layer + migrations | Adding tables or changing data access |
| `scripts/` | Data generation and utility scripts | Adding CLI tools or data utilities |
| `models/` | Pre-trained ML model files (.joblib) | Adding or updating ML models |

The main API file is `app.py` — all non-RAG endpoints are defined here. RAG endpoints are in `rag/api.py` and mounted as a sub-router.

### Frontend (`frontend/src/`)

| Directory | Purpose | When to add here |
|---|---|---|
| `components/ui/` | shadcn/ui primitives (don't modify directly) | Never — add via shadcn CLI |
| `components/mockScreens/` | Top-level screen components | Adding a new full-page screen |
| `components/insightsScreen/` | Dashboard, charts, tab sections | Adding dashboard widgets or tabs |
| `components/chatAssistant/` | Chat interface components | Modifying the chat UI |
| `contexts/` | React Context providers | Adding new global state |
| `lib/` | Utility functions and API client | Adding shared utilities |

## Adding a Backend Endpoint

1. Open `backend/app.py`
2. Add a new route following existing patterns:

```python
@app.get("/api/my-endpoint")
async def my_endpoint(run_id: Optional[str] = None):
    """Description of what this endpoint does."""
    if run_id:
        data = db_get_run_my_data(run_id)
    else:
        data = db_get_latest_my_data()
    return data or {}
```

**Conventions:**
- Prefix all routes with `/api/`
- Accept optional `run_id` query parameter for run-specific data
- Return JSON responses (FastAPI handles serialization)
- Use the `db_` prefix for imported database functions
- For heavy operations, use `asyncio.to_thread()` to avoid blocking

## Adding a Frontend Screen

See [frontend.md](frontend.md#how-to-add-a-new-screen) for the step-by-step guide.

## Adding a Pipeline Agent

See [agents-and-pipeline.md](agents-and-pipeline.md#how-to-add-a-new-agent) for the step-by-step guide.

## Environment Variables

When adding a new environment variable:

1. Add it to `backend/.env.example` (or `frontend/.env` if frontend)
2. Document it in [getting-started.md](getting-started.md#2-environment-configuration)
3. Use `os.getenv("VAR_NAME", "default")` in Python
4. Use `import.meta.env.VITE_VAR_NAME` in the frontend (must be prefixed with `VITE_`)

## Useful Commands

| Command | What it does |
|---|---|
| `bash start.sh` | Start both backend and frontend |
| `bash generate_data.sh` | Generate fresh synthetic data |
| `bash update_data.sh --scenario profit` | Simulate a business scenario |
| `cd backend && python app.py` | Start backend only |
| `cd frontend && npm run dev` | Start frontend only |
| `cd frontend && npm run build` | Production build |
| `cd backend && python -m db.setup` | Run database migrations |
| `cd backend && python scripts/migrate_raw_to_supabase.py` | Upload CSVs to Supabase |
| `cd backend && python scripts/generate_synthetic_data.py` | Generate data (without shell script) |

## Debugging Tips

- **Backend logs:** Uvicorn prints agent progress and errors to the terminal
- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs) for testing endpoints interactively
- **Pipeline decisions:** `GET /api/pipeline/decisions` shows all LLM reasoning from the last run
- **Database inspection:** Use the Supabase Dashboard → Table Editor to inspect stored data
- **Frontend console:** Check browser DevTools for API errors and React state
- **RAG debugging:** `POST /api/rag/chat` with `include_sources: true` shows retrieval sources

## Testing

The project currently does not have an automated test suite. Testing is done manually:

1. **Backend endpoints:** Test via Swagger UI at `/docs`
2. **Pipeline:** Run a full pipeline via the frontend Pipeline screen and verify results in Insights
3. **RAG:** Test questions in the LLM Assistant screen
4. **Data generation:** Use Settings screen to generate/update data and verify in Data Explorer
