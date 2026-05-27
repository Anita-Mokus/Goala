"""
API dependencies.
Provides dependency injection for shared resources (RAG service singleton).
"""
from fastapi import HTTPException

from src.config import DEFAULT_DATASET_KEY, normalize_dataset_key

# Global service instances keyed by dataset
_rag_services = {}


def get_rag_service(dataset_key: str = DEFAULT_DATASET_KEY):
    """
    Get or create a dataset-specific RAG service instance with error handling.
    
    Returns:
        RAGService instance
        
    Raises:
        HTTPException: If service initialization fails
    """
    normalized_dataset_key = normalize_dataset_key(dataset_key)
    if normalized_dataset_key not in _rag_services:
        try:
            from src.chat import RAGService
            _rag_services[normalized_dataset_key] = RAGService(dataset_key=normalized_dataset_key)
        except Exception as e:
            raise HTTPException(
                status_code=503,
                detail=f"Service unavailable for dataset '{normalized_dataset_key}': {str(e)}. Vector database may not be initialized."
            )
    return _rag_services[normalized_dataset_key]
