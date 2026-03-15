"""
API dependencies.
Provides dependency injection for shared resources (RAG service singleton).
"""
from fastapi import HTTPException

# Global service instance (lazy initialization)
_rag_service = None


def get_rag_service():
    """
    Get or create RAG service instance with error handling.
    
    Returns:
        RAGService instance
        
    Raises:
        HTTPException: If service initialization fails
    """
    global _rag_service
    if _rag_service is None:
        try:
            from src.chat import RAGService
            _rag_service = RAGService()
        except Exception as e:
            raise HTTPException(
                status_code=503,
                detail=f"Service unavailable: {str(e)}. Vector database may not be initialized."
            )
    return _rag_service
