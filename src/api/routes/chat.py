"""
Chat API routes.
Endpoints: POST /chat, GET /, GET /health.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, text

from src.config import DATABASE_URL, DEFAULT_DATASET_KEY
from src.api.dependencies import get_rag_service

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    message: str
    dataset_key: str = DEFAULT_DATASET_KEY


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    response: str


@router.get("/")
def read_root():
    """Root endpoint - API status check."""
    from src.config import API_TITLE, API_VERSION
    return {
        "status": "running",
        "title": API_TITLE,
        "version": API_VERSION
    }


@router.get("/health")
def health_check():
    """Health check endpoint with service validation."""
    try:
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


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """
    Main chat endpoint - send a message, get an AI response.
    
    Args:
        request: ChatRequest containing the user's message
        
    Returns:
        ChatResponse with the AI-generated response
    """
    try:
        rag_service = get_rag_service(request.dataset_key)
        result = rag_service.query(request.message)
        return ChatResponse(response=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
