-- ============================================================================
-- Migration Script: Add Messenger Persistent Per-User Conversation History
-- Creates thread/message tables used by Selenium Messenger bot context memory
-- ============================================================================

CREATE TABLE IF NOT EXISTS messenger_threads (
    id BIGSERIAL PRIMARY KEY,
    conversation_url TEXT NOT NULL UNIQUE,
    conversation_id VARCHAR(64) NOT NULL UNIQUE,
    thread_key VARCHAR(128) NOT NULL UNIQUE,
    display_name TEXT,
    platform VARCHAR(32) NOT NULL DEFAULT 'messenger',
    first_seen_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    bootstrapped_from_dom BOOLEAN NOT NULL DEFAULT FALSE,
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_messenger_threads_last_seen_at
ON messenger_threads(last_seen_at DESC);

CREATE TABLE IF NOT EXISTS messenger_messages (
    id BIGSERIAL PRIMARY KEY,
    thread_id BIGINT NOT NULL REFERENCES messenger_threads(id) ON DELETE CASCADE,
    role VARCHAR(16) NOT NULL,
    direction VARCHAR(16) NOT NULL,
    content TEXT NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    source VARCHAR(32) NOT NULL,
    is_edited BOOLEAN NOT NULL DEFAULT FALSE,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    observed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB,
    CONSTRAINT chk_messenger_messages_role CHECK (role IN ('user', 'assistant', 'system')),
    CONSTRAINT chk_messenger_messages_direction CHECK (direction IN ('inbound', 'outbound', 'internal'))
);

CREATE INDEX IF NOT EXISTS idx_messenger_messages_thread_created
ON messenger_messages(thread_id, created_at DESC);

DO $$
BEGIN
    RAISE NOTICE 'Migration 003 completed successfully!';
    RAISE NOTICE 'Created tables: messenger_threads, messenger_messages';
END $$;
