"""
Shared Embeddings Singleton.
Provides a single instance of HuggingFaceEmbeddings to avoid duplicate model loading
in memory when both IngestService and RAGService are active.
"""
import torch
from langchain_huggingface import HuggingFaceEmbeddings
from src.core.config import EMBEDDING_MODEL


_embeddings_instance = None


def _best_device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def get_embeddings() -> HuggingFaceEmbeddings:
    """
    Get the shared embeddings instance (singleton pattern).
    
    Returns:
        HuggingFaceEmbeddings instance configured with the model from config
    """
    global _embeddings_instance
    
    if _embeddings_instance is None:
        device = _best_device()
        # Batch sizes tuned for BGE-M3 (2.2 GB weights).
        # FineWeb passages are long (~400 tokens avg), so VRAM per doc is high.
        #   cuda → 8  conservative to avoid OOM on cards < 8 GB
        #   mps  → 8  (unified memory, conservative)
        #   cpu  → 32
        batch_size = 8 if device == "cuda" else (8 if device == "mps" else 32)
        print(f"Initializing embeddings model: {EMBEDDING_MODEL} (device={device}, batch_size={batch_size})")
        _embeddings_instance = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL,
            model_kwargs={'device': device},
            encode_kwargs={
                'normalize_embeddings': True,
                'batch_size': batch_size,
            }
        )
        print("✓ Embeddings model loaded")
    
    return _embeddings_instance
