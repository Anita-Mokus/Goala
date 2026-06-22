-- ============================================================================
-- Migration 005: Fix invalid chunk_overlap / chunk_max_characters values
-- The app_settings row may have chunk_overlap >= chunk_max_characters, which
-- causes unstructured's chunk_by_title to raise a ValueError at ingestion time.
-- This migration resets both fields to safe defaults.
-- ============================================================================

UPDATE app_settings
SET
    chunk_max_characters    = 500,
    chunk_new_after_n_chars = 400,
    chunk_overlap           = 0,
    updated_at              = CURRENT_TIMESTAMP
WHERE id = 1
  AND chunk_overlap >= chunk_max_characters;

DO $$
BEGIN
    RAISE NOTICE 'Migration 005 applied: chunk settings corrected if overlap >= max_characters.';
END $$;
