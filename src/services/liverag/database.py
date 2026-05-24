"""
Database operations for LiveRAG ingestion.

PGVector store setup and document storage.
"""
from typing import List, Optional

from langchain_core.documents import Document
from langchain_postgres import PGVector
from sqlalchemy import create_engine, text


def ensure_extension_exists(connection_string: str) -> None:
    """
    Ensure the pgvector extension is present in the database.
    
    Args:
        connection_string: PostgreSQL connection string.
    """
    try:
        engine = create_engine(connection_string, echo=False)
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            conn.commit()
        engine.dispose()
        print("✓ pgvector extension confirmed")
    except Exception as e:
        print(f"ℹ Extension check: {type(e).__name__}: {e}")


def store_documents_batch(
    documents: List[Document],
    store: Optional[PGVector],
    first_batch: bool,
    embedding_function,
    connection_string: str,
    collection_name: str,
) -> PGVector:
    """
    Embed and store a batch of documents in PGVector.

    On the first call the collection is recreated (pre_delete_collection=True)
    and the PGVector store object is returned so subsequent calls can reuse
    it via ``store.add_documents()`` instead of reconnecting each time.
    
    Args:
        documents: List of Document objects to store.
        store: Existing PGVector store (or None for first batch).
        first_batch: Whether this is the first batch (will recreate collection).
        embedding_function: Embedding function to use.
        connection_string: PostgreSQL connection string.
        collection_name: Name of the collection in PGVector.
        
    Returns:
        PGVector store instance for subsequent batches.
    """
    if first_batch or store is None:
        store = PGVector.from_documents(
            documents=documents,
            embedding=embedding_function,
            connection=connection_string,
            collection_name=collection_name,
            use_jsonb=True,
            pre_delete_collection=True,
        )
    else:
        store.add_documents(documents)
    return store
