"""
LiveRAG Dataset Ingestion Service.

The LiveRAG/Benchmark dataset is already pre-chunked into passages,
so no partitioning or chunking step is needed — only embed and store.
"""
import os
from typing import List, Optional

from datasets import load_dataset
from langchain_core.documents import Document
from langchain_postgres import PGVector
from sqlalchemy import create_engine, text

from src.core.config import (
    HUGGINGFACE_TOKEN,
    DATABASE_URL,
    PGVECTOR_COLLECTION_NAME,
)
from src.services.embeddings import get_embeddings


class LiveragIngestor:
    """Ingest pre-chunked passages from the LiveRAG/Benchmark HuggingFace dataset."""

    def __init__(self):
        self.embedding_function = get_embeddings()
        self.connection_string = DATABASE_URL
        self.collection_name = PGVECTOR_COLLECTION_NAME

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_extension_exists(self) -> None:
        """Ensure the pgvector extension is present in the database."""
        try:
            engine = create_engine(self.connection_string, echo=False)
            with engine.connect() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                conn.commit()
            engine.dispose()
            print("✓ pgvector extension confirmed")
        except Exception as e:
            print(f"ℹ Extension check: {type(e).__name__}: {e}")

    def _dataset_to_documents(self, dataset) -> List[Document]:
        """
        Convert HuggingFace dataset rows to LangChain Document objects.

        The LiveRAG/Benchmark dataset rows contain at least:
          - 'id'       : passage identifier
          - 'contents' : the passage text  (main content field)
        Optional fields (used as metadata when present):
          - 'title', 'url', 'source'
        """
        documents = []
        for row in dataset:
            content = row.get("contents") or row.get("text") or row.get("passage") or ""
            if not content.strip():
                continue

            metadata = {"passage_id": row.get("id", "")}
            for field in ("title", "url", "source", "docid"):
                if row.get(field):
                    metadata[field] = row[field]

            documents.append(Document(page_content=content, metadata=metadata))

        return documents

    def _store_documents(self, documents: List[Document]) -> None:
        """Embed and store documents in PGVector, replacing any existing collection."""
        PGVector.from_documents(
            documents=documents,
            embedding=self.embedding_function,
            connection=self.connection_string,
            collection_name=self.collection_name,
            use_jsonb=True,
            pre_delete_collection=True,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def ingest(self, split: str = "train", batch_size: int = 500) -> None:
        """
        Load the LiveRAG/Benchmark dataset and store all passages in PGVector.

        Args:
            split:      Dataset split to load (default: 'train').
            batch_size: Number of rows to convert at a time (memory safety).
        """
        print(f"Loading LiveRAG/Benchmark (split='{split}') from HuggingFace...")
        ds = load_dataset(
            "LiveRAG/Benchmark",
            split=split,
            token=HUGGINGFACE_TOKEN or None,
        )
        total = len(ds)
        print(f"  → {total} passages loaded")

        self._ensure_extension_exists()

        print("Converting passages to Documents and storing in PGVector...")
        all_docs: List[Document] = []

        for start in range(0, total, batch_size):
            batch = ds.select(range(start, min(start + batch_size, total)))
            docs = self._dataset_to_documents(batch)
            all_docs.extend(docs)
            print(f"  Converted {min(start + batch_size, total)}/{total} passages...", end="\r")

        print(f"\n  → {len(all_docs)} non-empty documents ready")

        if not all_docs:
            raise RuntimeError("No documents produced — check the dataset field names.")

        print("Saving embeddings to PostgreSQL...")
        self._store_documents(all_docs)
        print(f"✓ Done! {len(all_docs)} passages stored in collection '{self.collection_name}'.")
