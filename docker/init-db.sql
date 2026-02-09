-- =============================================================================
-- PostgreSQL Initialization Script for Goala
-- This script runs automatically when the PostgreSQL container is first created
-- =============================================================================

-- Enable the pgvector extension for vector similarity search
CREATE EXTENSION IF NOT EXISTS vector;

-- Grant permissions to the default user
GRANT ALL PRIVILEGES ON DATABASE goala TO postgres;

-- Create a schema for application data (optional, for future use)
-- CREATE SCHEMA IF NOT EXISTS app;

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE 'Goala database initialized successfully with pgvector extension';
END $$;
