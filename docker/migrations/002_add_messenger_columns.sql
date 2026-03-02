-- ============================================================================
-- Migration Script: Add Messenger Bot Support Columns
-- Adds source and message_metadata columns to chat_history table
-- ============================================================================

-- Add source column to track message origin (api, messenger, etc.)
ALTER TABLE chat_history 
ADD COLUMN IF NOT EXISTS source VARCHAR(50) NOT NULL DEFAULT 'api';

-- Add message_metadata column to store additional context (sender info, etc.)
-- Note: Using message_metadata instead of metadata to avoid SQLAlchemy reserved name
ALTER TABLE chat_history 
ADD COLUMN IF NOT EXISTS message_metadata JSONB;

-- Create index for efficient filtering by source
CREATE INDEX IF NOT EXISTS idx_chat_history_source 
ON chat_history(source);

-- Verify migration completed successfully
DO $$
BEGIN
    RAISE NOTICE 'Migration 002 completed successfully!';
    RAISE NOTICE 'Added columns: source (VARCHAR), message_metadata (JSONB)';
    RAISE NOTICE 'Added index: idx_chat_history_source';
END $$;
