"""
FastAPI application for AI Chat Flow.
Main API endpoints for the hotel chatbot.
"""
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
)

# Global service instance (lazy initialization to prevent startup crashes)
_rag_service = None

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


# Startup event: Initialize vector database on first run
@app.on_event("startup")
def startup_event():
    """Run ingestion on startup if vector database doesn't have documents."""
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


