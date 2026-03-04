"""
Shared Embeddings Singleton.
Provides a single instance of HuggingFaceEmbeddings to avoid duplicate model loading
in memory when both IngestService and RAGService are active.
"""
from langchain_huggingface import HuggingFaceEmbeddings
from src.core.config import EMBEDDING_MODEL


_embeddings_instance = None


def get_embeddings() -> HuggingFaceEmbeddings:
    """
    Get the shared embeddings instance (singleton pattern).
    
    Returns:
        HuggingFaceEmbeddings instance configured with the model from config
    """
    global _embeddings_instance
    
    if _embeddings_instance is None:
        print(f"Initializing embeddings model: {EMBEDDING_MODEL}")
        _embeddings_instance = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL,
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True, 'batch_size': 256}
        )
        print("✓ Embeddings model loaded")
    
    return _embeddings_instance
