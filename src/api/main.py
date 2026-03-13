"""
FastAPI application for AI Chat Flow.
Main API endpoints for the hotel chatbot.
"""
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.core.config import (
    API_TITLE,
    API_DESCRIPTION,
    API_VERSION,
    CORS_ORIGINS,
    CORS_CREDENTIALS,
    CORS_METHODS,
    CORS_HEADERS,
    DATABASE_URL,
    RAG_PROMPT_TEMPLATE,
)
from src.api.routes import settings, history, messenger

# Global service instance (lazy initialization to prevent startup crashes)
_rag_service = None


def ensure_database_schema() -> None:
    """Ensure required database tables/columns/indexes exist for API routes."""
    try:
        from sqlalchemy import create_engine, text

        engine = create_engine(DATABASE_URL)
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS app_settings (
                        id INTEGER PRIMARY KEY DEFAULT 1,
                        llm_provider VARCHAR(50) NOT NULL DEFAULT 'openrouter',
                        llm_model VARCHAR(100) NOT NULL DEFAULT 'openai/gpt-oss-120b:exacto',
                        llm_temperature REAL NOT NULL DEFAULT 0.3,
                        retriever_k INTEGER NOT NULL DEFAULT 8,
                        pdf_language VARCHAR(10) NOT NULL DEFAULT 'hun',
                        pdf_strategy VARCHAR(20) NOT NULL DEFAULT 'auto',
                        chunk_max_characters INTEGER NOT NULL DEFAULT 1000,
                        chunk_new_after_n_chars INTEGER NOT NULL DEFAULT 800,
                        chunk_overlap INTEGER NOT NULL DEFAULT 200,
                        rag_prompt_template TEXT,
                        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE app_settings "
                    "ADD COLUMN IF NOT EXISTS llm_provider VARCHAR(50) NOT NULL DEFAULT 'openrouter'"
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE app_settings "
                    "ADD COLUMN IF NOT EXISTS llm_model VARCHAR(100) NOT NULL DEFAULT 'openai/gpt-oss-120b:exacto'"
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE app_settings "
                    "ADD COLUMN IF NOT EXISTS llm_temperature REAL NOT NULL DEFAULT 0.3"
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE app_settings "
                    "ADD COLUMN IF NOT EXISTS retriever_k INTEGER NOT NULL DEFAULT 8"
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE app_settings "
                    "ADD COLUMN IF NOT EXISTS pdf_language VARCHAR(10) NOT NULL DEFAULT 'hun'"
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE app_settings "
                    "ADD COLUMN IF NOT EXISTS pdf_strategy VARCHAR(20) NOT NULL DEFAULT 'auto'"
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE app_settings "
                    "ADD COLUMN IF NOT EXISTS chunk_max_characters INTEGER NOT NULL DEFAULT 1000"
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE app_settings "
                    "ADD COLUMN IF NOT EXISTS chunk_new_after_n_chars INTEGER NOT NULL DEFAULT 800"
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE app_settings "
                    "ADD COLUMN IF NOT EXISTS chunk_overlap INTEGER NOT NULL DEFAULT 200"
                )
            )
            conn.execute(
                text("ALTER TABLE app_settings ADD COLUMN IF NOT EXISTS rag_prompt_template TEXT")
            )
            conn.execute(
                text(
                    "ALTER TABLE app_settings "
                    "ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP"
                )
            )
            conn.execute(
                text(
                    """
                    INSERT INTO app_settings (
                        id,
                        llm_provider,
                        llm_model,
                        llm_temperature,
                        retriever_k,
                        pdf_language,
                        pdf_strategy,
                        chunk_max_characters,
                        chunk_new_after_n_chars,
                        chunk_overlap,
                        rag_prompt_template
                    )
                    VALUES (
                        1,
                        'openrouter',
                        'openai/gpt-oss-120b:exacto',
                        0.3,
                        8,
                        'hun',
                        'auto',
                        1000,
                        800,
                        200,
                        :rag_prompt_template
                    )
                    ON CONFLICT (id) DO NOTHING
                    """
                ),
                {"rag_prompt_template": RAG_PROMPT_TEMPLATE},
            )
            conn.execute(
                text(
                    "UPDATE app_settings "
                    "SET rag_prompt_template = :rag_prompt_template "
                    "WHERE rag_prompt_template IS NULL"
                ),
                {"rag_prompt_template": RAG_PROMPT_TEMPLATE},
            )
            conn.execute(
                text(
                    "ALTER TABLE app_settings "
                    "ALTER COLUMN rag_prompt_template SET NOT NULL"
                )
            )

            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS chat_history (
                        id SERIAL PRIMARY KEY,
                        question TEXT NOT NULL,
                        answer TEXT NOT NULL,
                        model_used VARCHAR(100),
                        response_time_ms INTEGER,
                        source VARCHAR(50) NOT NULL DEFAULT 'api',
                        message_metadata JSONB,
                        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE chat_history "
                    "ADD COLUMN IF NOT EXISTS source VARCHAR(50) NOT NULL DEFAULT 'api'"
                )
            )
            conn.execute(
                text("ALTER TABLE chat_history ADD COLUMN IF NOT EXISTS message_metadata JSONB")
            )
            conn.execute(
                text("CREATE INDEX IF NOT EXISTS idx_chat_history_source ON chat_history(source)")
            )

        engine.dispose()
        print("Database schema check completed.")
    except Exception as e:
        print(f"Warning: Failed to run schema check: {e}")

def get_rag_service():
    """Get or create RAG service instance with error handling."""
    global _rag_service
    if _rag_service is None:
        try:
            from src.services import RAGService
            _rag_service = RAGService()
        except Exception as e:
            raise HTTPException(
                status_code=503,
                detail=f"Service unavailable: {str(e)}. Vector database may not be initialized."
            )
    return _rag_service


# Initialize FastAPI app
app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION,
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=CORS_CREDENTIALS,
    allow_methods=CORS_METHODS,
    allow_headers=CORS_HEADERS,
)

# Register API routers
app.include_router(settings.router)
app.include_router(history.router)
app.include_router(messenger.router)


# Startup event: Initialize vector database on first run
@app.on_event("startup")
def startup_event():
    """Run ingestion on startup if vector database doesn't have documents."""
    ensure_database_schema()

    # Clear stale Messenger bot status file from previous container runs
    try:
        from src.integrations.messenger.config import MessengerConfig
        if MessengerConfig.STATUS_FILE and os.path.exists(MessengerConfig.STATUS_FILE):
            os.remove(MessengerConfig.STATUS_FILE)
            print("Cleared stale Messenger bot status file")
    except Exception as e:
        print(f"Warning: Could not clear Messenger status file: {e}")
    
    try:
        from src.services.ingest_service import IngestService
        ingest_service = IngestService()
        
        # Check if collection already has documents
        has_documents = ingest_service.check_collection_exists()
        
        if not has_documents:
            print("\n" + "="*50)
            print("Vector database empty. Starting document ingestion...")
            print("="*50 + "\n")
            
            ingest_service.ingest_all_documents()
            
            print("\n" + "="*50)
            print("Document ingestion completed successfully!")
            print("="*50 + "\n")
        else:
            print("Vector database found with documents. Skipping ingestion.")
    except Exception as e:
        print(f"Warning: Failed to initialize vector database: {e}")
        print("The service will start, but /chat endpoint may not work until database is initialized.")


# Request/Response models
class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    message: str


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    response: str


# API Endpoints
@app.get("/")
def read_root():
    """Root endpoint - API status check."""
    return {
        "status": "running",
        "title": API_TITLE,
        "version": API_VERSION
    }


@app.get("/health")
def health_check():
    """Health check endpoint with service validation."""
    try:
        from sqlalchemy import create_engine, text
        
        # Test database connection
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        
        # Try to initialize service
        service = get_rag_service()
        
        return {
            "status": "healthy",
            "database": "connected",
            "service": "initialized"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "database": "not connected"
        }


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """
    Main chat endpoint - send a message, get an AI response.
    
    Args:
        request: ChatRequest containing the user's message
        
    Returns:
        ChatResponse with the AI-generated response
    """
    try:
        rag_service = get_rag_service()
        result = rag_service.query(request.message)
        return ChatResponse(response=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


