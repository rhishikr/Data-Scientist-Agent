-- ============================================================================
-- RAG Pipeline — pgvector + chat memory tables
-- ============================================================================

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- 1. rag_documents — stores embedded documents for similarity search
CREATE TABLE IF NOT EXISTS rag_documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  content TEXT NOT NULL,
  metadata JSONB DEFAULT '{}',
  embedding VECTOR(1536),        -- text-embedding-3-small output dimension
  source TEXT NOT NULL,           -- 'table_profile', 'rows_sample', 'insight', 'hypothesis', 'kpi'
  source_id TEXT,                 -- dedup key within a source category
  created_at TIMESTAMPTZ DEFAULT now()
);

-- HNSW index for fast approximate nearest-neighbor search
CREATE INDEX IF NOT EXISTS idx_rag_documents_embedding
  ON rag_documents USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS idx_rag_documents_source
  ON rag_documents(source);

-- 2. chat_messages — session-based conversation history
CREATE TABLE IF NOT EXISTS chat_messages (
  id BIGSERIAL PRIMARY KEY,
  session_id TEXT NOT NULL,
  role TEXT NOT NULL,             -- 'human' or 'ai'
  content TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_session
  ON chat_messages(session_id, created_at);
