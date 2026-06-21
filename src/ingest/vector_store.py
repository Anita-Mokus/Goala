"""
Vector store management.
Handles pgvector extension and vector store creation.
"""
from typing import List
from langchain_core.documents import Document
from langchain_postgres import PGVector
from sqlalchemy import create_engine, text

from src.config import normalize_database_url


def ensure_extension_exists(connection_string: str) -> None:
    """Ensure pgvector extension exists in the database."""
    try:
        engine = create_engine(normalize_database_url(connection_string), echo=False)
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            conn.commit()
        engine.dispose()
        print("✓ pgvector extension confirmed")
    except Exception as e:
        print(f"ℹ Extension check: {type(e).__name__}")


def create_vector_store(
    documents: List[Document],
    embedding_function,
    connection_string: str,
    collection_name: str,
    batch_size: int = 500,
) -> PGVector:
    """
    Create or update the vector store with documents, flushing in batches
    to avoid OOM with large document sets.

    Args:
        documents: List of document chunks to store
        embedding_function: Embedding function instance
        connection_string: PostgreSQL connection string
        collection_name: Name of the collection
        batch_size: Number of documents to embed and insert per flush

    Returns:
        PGVector instance
    """
    try:
        normalized = normalize_database_url(connection_string)
        vector_store = None

        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(documents) + batch_size - 1) // batch_size
            print(f"Batch {batch_num}/{total_batches} ({len(batch)} docs)...")

            if vector_store is None:
                vector_store = PGVector.from_documents(
                    documents=batch,
                    embedding=embedding_function,
                    connection=normalized,
                    collection_name=collection_name,
                    use_jsonb=True,
                    pre_delete_collection=True,
                )
            else:
                vector_store.add_documents(batch)

        return vector_store
    except Exception as e:
        print(f"Error creating vector store: {e}")
        raise
