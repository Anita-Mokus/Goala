"""
FastAPI application for the Goala LiveRAG question-answering service.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, text

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


_rag_service = None


def get_rag_service():
    """Return the cached RAG service, initializing it on first call."""
    global _rag_service
    if _rag_service is None:
        try:
            from src.services import RAGService
            _rag_service = RAGService()
        except Exception as e:
            raise HTTPException(
                status_code=503,
                detail=f"Service unavailable: {str(e)}. "
                       "Make sure the vector database is initialized via the ingest CLI.",
            )
    return _rag_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting up Goala API...")
    try:
        get_rag_service()
        print("RAG service initialized successfully.")
    except HTTPException as e:
        print(f"Warning: RAG service not ready at startup — {e.detail}")
        print("The /chat endpoint will return 503 until the database is populated.")
    yield
    print("Shutting down Goala API.")


app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=CORS_CREDENTIALS,
    allow_methods=CORS_METHODS,
    allow_headers=CORS_HEADERS,
)



class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str


@app.get("/")
def read_root():
    """Root endpoint — API status check."""
    return {
        "status": "running",
        "title": API_TITLE,
        "version": API_VERSION,
    }


@app.get("/health")
def health_check():
    """Health check: verifies DB connectivity and RAG service readiness."""
    db_status = "disconnected"
    service_status = "unavailable"

    try:
        engine = create_engine(DATABASE_URL, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        db_status = "connected"
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": db_status,
            "service": service_status,
            "error": str(e),
        }

    try:
        get_rag_service()
        service_status = "initialized"
    except HTTPException as e:
        return {
            "status": "degraded",
            "database": db_status,
            "service": service_status,
            "error": e.detail,
        }

    return {
        "status": "healthy",
        "database": db_status,
        "service": service_status,
    }


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """Answer a question using the RAG pipeline."""
    try:
        rag_service = get_rag_service()
        result = rag_service.query(request.message)
        return ChatResponse(response=result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


