"""
HuggingFace embedding singleton.
Ensures only one embedding model instance is created (CPU-only).
"""
from langchain_huggingface import HuggingFaceEmbeddings
from src.config import EMBEDDING_MODEL

# Singleton instance
_embeddings_instance = None


def get_embeddings() -> HuggingFaceEmbeddings:
    """
    Get or create the singleton HuggingFace embeddings instance.
    
    Returns:
        HuggingFaceEmbeddings instance configured with BAAI/bge-m3 model
    """
    global _embeddings_instance
    if _embeddings_instance is None:
        _embeddings_instance = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True}
        )
    return _embeddings_instance
