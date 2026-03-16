-- =============================================================================
-- PostgreSQL Initialization Script for Goala
-- This script runs automatically when the PostgreSQL container is first created
-- =============================================================================

-- Enable the pgvector extension for vector similarity search
CREATE EXTENSION IF NOT EXISTS vector;

-- Grant permissions to the default user
GRANT ALL PRIVILEGES ON DATABASE goala TO postgres;

-- =============================================================================
-- Application Settings Table
-- Stores configurable RAG parameters (singleton pattern - only one row)
-- =============================================================================
CREATE TABLE IF NOT EXISTS app_settings (
    id INTEGER PRIMARY KEY DEFAULT 1,
    llm_provider VARCHAR(50) NOT NULL DEFAULT 'openrouter',
    llm_model VARCHAR(100) NOT NULL DEFAULT 'openai/gpt-oss-120b:exacto',
    llm_temperature REAL NOT NULL DEFAULT 0.3 CHECK (llm_temperature >= 0 AND llm_temperature <= 1),
    retriever_k INTEGER NOT NULL DEFAULT 8 CHECK (retriever_k >= 1 AND retriever_k <= 20),
    pdf_language VARCHAR(10) NOT NULL DEFAULT 'hun',
    pdf_strategy VARCHAR(20) NOT NULL DEFAULT 'auto',
    chunk_max_characters INTEGER NOT NULL DEFAULT 1000,
    chunk_new_after_n_chars INTEGER NOT NULL DEFAULT 800,
    chunk_overlap INTEGER NOT NULL DEFAULT 200,
    rag_prompt_template TEXT DEFAULT NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT single_row_constraint CHECK (id = 1)
);

-- Insert default settings row
INSERT INTO app_settings (id) VALUES (1) ON CONFLICT (id) DO NOTHING;

-- =============================================================================
-- Chat History Table
-- Logs all question-answer interactions
-- =============================================================================
CREATE TABLE IF NOT EXISTS chat_history (
    id SERIAL PRIMARY KEY,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    model_used VARCHAR(100),
    response_time_ms INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create index on created_at for efficient pagination
CREATE INDEX IF NOT EXISTS idx_chat_history_created_at ON chat_history(created_at DESC);

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE 'Goala database initialized successfully with pgvector extension, app_settings, and chat_history tables';
END $$;
