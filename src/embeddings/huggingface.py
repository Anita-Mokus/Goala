"""
HuggingFace embedding singleton.
Ensures only one embedding model instance is created.
"""
import torch
from langchain_huggingface import HuggingFaceEmbeddings
from src.config import EMBEDDING_MODEL, ENABLE_GPU

# Singleton instance
_embeddings_instance = None


def _get_embedding_device() -> str:
    """Pick CUDA when ENABLE_GPU=true and CUDA is available, otherwise CPU."""
    if ENABLE_GPU.lower() == "true":
        if torch.cuda.is_available():
            return "cuda"
        print("WARNING: ENABLE_GPU=true but CUDA is not available — falling back to CPU.")
    return "cpu"


def get_embeddings() -> HuggingFaceEmbeddings:
    """
    Get or create the singleton HuggingFace embeddings instance.
    
    Returns:
        HuggingFaceEmbeddings instance configured with BAAI/bge-m3 model
    """
    global _embeddings_instance
    if _embeddings_instance is None:
        device = _get_embedding_device()
        print(f"Using embedding device: {device}")
        _embeddings_instance = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL,
            model_kwargs={"device": device},
            encode_kwargs={"normalize_embeddings": True}
        )
    return _embeddings_instance
