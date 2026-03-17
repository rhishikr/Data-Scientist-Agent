# RAG System

This document explains the Retrieval-Augmented Generation (RAG) system that powers the chat assistant. The RAG system lets users ask natural language questions about their retail data and get answers backed by pipeline results and database queries.

## Architecture Overview

```
User Question
      │
      ▼
┌─────────────────┐
│  Query Router    │  Classifies: snapshot | sql | insight | hybrid
│  (router.py)    │
└────────┬────────┘
         │
    ┌────┼────────────┬──────────────┐
    ▼    ▼            ▼              ▼
Snapshot  SQL Agent   pgvector     Hybrid
Matcher   (LangChain  Similarity   (SQL +
          ReAct)      Search       Insight)
    │    │            │              │
    └────┴────────────┴──────────────┘
         │
         ▼
┌─────────────────┐
│  LLM Synthesis  │  Contextualizes retrieved data into an answer
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Chat Memory    │  Saves Q&A to session history
│  (memory.py)    │
└────────┬────────┘
         │
         ▼
   SSE Stream to Frontend
```

## Query Router (`backend/rag/router.py`)

The router classifies each question into one of four types using a two-tier approach:

### Tier 1: Pattern Matching (instant, free)

Keyword-based scoring against three pattern lists:

- **SQL patterns:** `revenue`, `total`, `sum`, `average`, `count`, `top`, `how many`, `trend`, `growth rate`, etc.
- **Insight patterns:** `why`, `how to`, `recommend`, `suggest`, `opportunity`, `risk`, `improve`, `optimize`, etc.
- **Hybrid patterns:** `why did`, `what drove`, `what caused`, `analyze and recommend`, etc.

Hybrid patterns are checked first (most specific). If SQL and insight scores tie, the query is ambiguous.

### Tier 2: LLM Fallback (when patterns are ambiguous)

If pattern matching can't decide, the LLM classifies the query into `sql`, `insight`, or `hybrid`.

### Query Types

| Type | When Used | Retrieval Method |
|---|---|---|
| `snapshot` | Direct metric lookups ("what is the revenue?") | Snapshot matcher — looks up KPI/forecast snapshots |
| `sql` | Data queries ("top 10 products by sales") | LangChain SQL agent queries the database |
| `insight` | Strategic questions ("why are sales declining?") | pgvector similarity search over indexed documents |
| `hybrid` | Both data + strategy ("what caused the spike and what should we do?") | SQL agent + pgvector, results combined |

## Snapshot Matcher (`backend/rag/snapshot_matcher.py`)

For direct metric lookups, the snapshot matcher checks if the question maps to a stored KPI or forecast value. This is the fastest path — no LLM call needed for retrieval.

Examples:
- "What is our revenue?" → looks up `revenue` in `kpi_snapshots`
- "What is the churn rate?" → looks up `churn_rate` in `kpi_snapshots`

If a match is found, it formats the response directly. If not, the query falls through to other retrieval methods.

## SQL Agent (`backend/rag/sql_agent.py`)

A LangChain ReAct agent that can write and execute SQL queries against the Supabase database.

**How it works:**
1. Receives the user's question
2. Inspects the database schema (dynamically loaded from Supabase)
3. Writes SQL to answer the question
4. Executes the query and reads results
5. Iterates if needed (ReAct loop)

**Key behavior:**
- Prefers querying `kpi_snapshots` (JSONB) for standard metrics
- Falls back to `raw_*` tables for custom or detailed queries
- Schema is loaded dynamically at runtime

## Vector Store (`backend/rag/store_pgvector.py`)

Uses PostgreSQL's `pgvector` extension (via SQLAlchemy + LangChain) for similarity search.

**Configuration:**
- Embedding model: `text-embedding-3-small` (configurable via `RAG_EMBED_MODEL`)
- Top-K results: `5` (configurable via `RAG_TOP_K`)
- Storage: `rag_documents` table in Supabase with `embedding` column

**Operations:**
- `upsert(docs)` — Insert or update documents with their embeddings
- `similarity_search(query, k)` — Find the K most similar documents

## Ingestion Pipeline (`backend/rag/ingest.py` + `etl.py`)

After each pipeline run, the orchestrator automatically rebuilds the RAG index.

### ETL (`backend/rag/etl.py`)

Builds documents from pipeline outputs for indexing:

| Builder Function | Source | Document Content |
|---|---|---|
| `build_table_profile_documents()` | Cleaned datasets or raw tables | Table schemas, column stats, sample data |
| `build_insight_documents()` | `insight_snapshots` | Business insights with metadata |
| `build_hypothesis_documents()` | `hypothesis_snapshots` | Significant statistical findings |
| `build_kpi_documents()` | `kpi_snapshots` | KPI values with context |

Each document is a `{"text": str, "metadata": {"source": str, "source_id": str}}` dict.

### Ingestion (`backend/rag/ingest.py`)

`rebuild_index(base_dir, run_id)`:
1. Loads config
2. Calls all ETL builder functions
3. Upserts documents into the pgvector store
4. Returns ingestion stats

## Chat Memory (`backend/rag/memory.py`)

Session-based conversation history stored in the `chat_messages` PostgreSQL table.

**Functions:**
- `get_history(session_id, db_url, max_messages=20)` — Retrieve recent messages
- `save_turn(session_id, question, answer, db_url)` — Save a Q&A pair
- `list_sessions(db_url)` — All sessions with preview and message count
- `delete_session(session_id, db_url)` — Delete all messages in a session
- `to_langchain_messages(history)` — Convert to LangChain message objects for context

The last 3 conversation turns are included in the LLM prompt for multi-turn context.

## Service Layer (`backend/rag/service.py`)

The `answer_question()` and `answer_question_stream()` functions orchestrate the full RAG flow:

1. Load config and create LLM instance
2. Try snapshot matcher first (fastest path)
3. If no snapshot match, classify the query via the router
4. Route to the appropriate handler:
   - **sql** → `run_sql_agent()`
   - **insight** → pgvector similarity search + LLM synthesis
   - **hybrid** → both SQL and pgvector, combined by LLM
5. Save the Q&A turn to chat memory
6. Return the answer (or stream chunks via SSE)

### Streaming

`answer_question_stream()` returns an SSE generator:
```
data: {"event": "start", "query_type": "sql"}
data: {"event": "chunk", "content": "..."}
data: {"event": "sources", "sources": [...]}
```

## Configuration (`backend/rag/config.py`)

The `RagConfig` dataclass holds all RAG settings:

| Field | Env Variable | Default |
|---|---|---|
| `db_url` | `SUPABASE_DB_URL` | (required) |
| `llm_model` | `RAG_LLM_MODEL` | `gpt-4.1-mini` |
| `embed_model` | `RAG_EMBED_MODEL` | `text-embedding-3-small` |
| `top_k` | `RAG_TOP_K` | `5` |

## API Endpoints

See [backend-api.md](backend-api.md#rag-chat-endpoints) for the full list of RAG REST endpoints.

Key endpoints:
- `POST /api/rag/chat` — Synchronous chat
- `POST /api/rag/chat/stream` — Streaming chat (SSE)
- `POST /api/rag/ingest` — Rebuild vector index
- `GET /api/rag/history` — Session history
- `GET /api/rag/sessions` — List sessions
