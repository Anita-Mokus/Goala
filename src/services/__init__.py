"""
Services module.

Business logic has been reorganised into focused sub-packages:
  src/chat/     — RAGService (retrieval + generation)
  src/ingest/   — IngestService (file-based) + LiveRAGIngestService (HF dataset)
  src/llm/      — LLM provider factory
  src/embeddings/ — embedding model singleton
"""
