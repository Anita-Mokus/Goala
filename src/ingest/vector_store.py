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
    collection_name: str
) -> PGVector:
    """
    Create or update the vector store with documents.
    
    Args:
        documents: List of document chunks to store
        embedding_function: Embedding function instance
        connection_string: PostgreSQL connection string
        collection_name: Name of the collection
        
    Returns:
        PGVector instance
    """
    try:
        vector_store = PGVector.from_documents(
            documents=documents,
            embedding=embedding_function,
            connection=connection_string,
            collection_name=collection_name,
            use_jsonb=True,
            pre_delete_collection=True
        )
        return vector_store
    except Exception as e:
        print(f"Error creating vector store: {e}")
        raise
