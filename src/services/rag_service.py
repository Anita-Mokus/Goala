"""
RAG (Retrieval-Augmented Generation) Service.
Handles document retrieval and response generation using LangChain with pgvector.

Key improvements over vanilla top-k retrieval:
  - Definition-level chunks (ingested with doc_id metadata per regulation doc)
  - Automatic metadata filtering: when the user question references a specific
    document (e.g. "H-68/2024"), retrieval is scoped to that document only,
    preventing cross-document context bleeding.
"""
import re
from typing import Dict, List, Optional

from langchain_postgres import PGVector
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from src.core.config import (
    DATABASE_URL,
    PGVECTOR_COLLECTION_NAME,
    LLM_PROVIDER,
    LLM_MODEL,
    LLM_TEMPERATURE,
    RETRIEVER_K,
    RETRIEVER_K_UNFILTERED,
    ENABLE_METADATA_FILTER,
    RAG_PROMPT_TEMPLATE
)
from src.services.llm_provider import get_llm_provider
from src.services.embeddings import get_embeddings


class RAGService:
    """Service for handling RAG operations."""
    
    def __init__(self):
        """Initialize RAG components."""
        # Use shared embedding function (singleton)
        self.embedding_function = get_embeddings()
        
        # Load vector database from PostgreSQL
        try:
            self.db = PGVector(
                embeddings=self.embedding_function,
                connection=DATABASE_URL,
                collection_name=PGVECTOR_COLLECTION_NAME,
                use_jsonb=True,
            )
        except Exception as e:
            raise RuntimeError(f"Failed to connect to vector database: {str(e)}")
        
        # Initialize LLM using the configured provider
        llm_provider = get_llm_provider(LLM_PROVIDER, LLM_MODEL, LLM_TEMPERATURE)
        self.llm = llm_provider.get_llm()
        
        # Create prompt template
        self.prompt = ChatPromptTemplate.from_template(RAG_PROMPT_TEMPLATE)
        # Note: retrieval is done manually in query() to support optional metadata filtering
    
    @staticmethod
    def _format_docs(docs: List) -> str:
        """Format retrieved documents for the prompt with source attribution."""
        parts = []
        for doc in docs:
            label = doc.metadata.get('doc_id') or doc.metadata.get('source', 'unknown')
            page  = doc.metadata.get('page_number')
            header = f"[{label}{f', p.{page}' if page else ''}]"
            parts.append(f"{header}\n{doc.page_content}")
        return "\n\n---\n\n".join(parts)

    @staticmethod
    def _extract_doc_filter(question: str) -> Optional[Dict]:
        """
        Detect regulation document references in the user question and build
        a PGVector metadata filter dict.

        Recognises all of:
            H-68/2024   H-68-2024   H68/2024   H 68/2024
            H-1339/2025  H-682  H-776

        Returns:
            A filter dict for PGVector, or None (no reference found → search all docs).
        """
        pattern = re.compile(
            r'\bH[-\s]?(\d{1,4})(?:[-/](\d{4}))?\b',
            re.IGNORECASE,
        )
        matches = pattern.findall(question)
        if not matches:
            return None

        exact, prefix = [], []
        for num, year in matches:
            if year:
                exact.append(f"H-{num}/{year}")
            else:
                prefix.append(f"H-{num}")

        # Multiple exact doc IDs — use $in
        if len(exact) > 1:
            return {"doc_id": {"$in": exact}}
        # Single exact match
        if len(exact) == 1 and not prefix:
            return {"doc_id": {"$eq": exact[0]}}
        # Only doc number, no year — use $like to match any year
        if prefix and not exact:
            return {"doc_id": {"$like": f"{prefix[0]}/%"}}
        # Mixed: prefer exact
        return {"doc_id": {"$in": exact}}

    def query(self, question: str) -> str:
        """
        Query the RAG system with automatic metadata filtering.

        When the question references a specific document (e.g. "H-68/2024"),
        retrieval is scoped to that document's chunks (RETRIEVER_K results).
        Otherwise all documents are searched (RETRIEVER_K_UNFILTERED results).

        Args:
            question: The user's question

        Returns:
            The AI-generated response
        """
        # 1. Determine filter and k
        metadata_filter: Optional[Dict] = None
        k = RETRIEVER_K_UNFILTERED

        if ENABLE_METADATA_FILTER:
            metadata_filter = self._extract_doc_filter(question)
            if metadata_filter:
                k = RETRIEVER_K
                doc_ref = list(metadata_filter.values())[0]
                print(f"  [filter] Scoping to {doc_ref}  (k={k})")
            else:
                print(f"  [filter] No doc reference — searching all documents  (k={k})")

        # 2. Retrieve chunks
        docs = self.db.similarity_search(question, k=k, filter=metadata_filter)

        # 3. Build prompt and call LLM
        context  = self._format_docs(docs)
        messages = self.prompt.format_messages(context=context, question=question)
        response = self.llm.invoke(messages)
        return StrOutputParser().invoke(response)


# Singleton instance
_rag_service_instance = None


def get_rag_service() -> RAGService:
    """Get or create the RAG service singleton instance."""
    global _rag_service_instance
    if _rag_service_instance is None:
        _rag_service_instance = RAGService()
    return _rag_service_instance
