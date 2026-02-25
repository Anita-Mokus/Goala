"""
RAG (Retrieval-Augmented Generation) Service.
Handles document retrieval and response generation using LangChain with pgvector.
"""
from langchain_postgres import PGVector
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

from src.core.config import (
    DATABASE_URL,
    PGVECTOR_COLLECTION_NAME,
    LLM_PROVIDER,
    LLM_MODEL,
    LLM_TEMPERATURE,
    RETRIEVER_K,
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
        
        # Create retriever
        self.retriever = self.db.as_retriever(search_kwargs={"k": RETRIEVER_K})
        
        # Create chain
        self.chain = (
            {"context": self.retriever | self._format_docs, "question": RunnablePassthrough()}
            | self.prompt
            | self.llm
            | StrOutputParser()
        )
    
    @staticmethod
    def _format_docs(docs):
        """Format retrieved documents for the prompt."""
        return "\n\n".join(doc.page_content for doc in docs)
    
    def query(self, question: str) -> str:
        """
        Query the RAG system with a question.
        
        Args:
            question: The user's question
            
        Returns:
            The AI-generated response
        """
        return self.chain.invoke(question)


# Singleton instance
_rag_service_instance = None


def get_rag_service() -> RAGService:
    """Get or create the RAG service singleton instance."""
    global _rag_service_instance
    if _rag_service_instance is None:
        _rag_service_instance = RAGService()
    return _rag_service_instance
