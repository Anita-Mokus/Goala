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
        
        # Create retriever using MMR (Maximum Marginal Relevance) for better
        # diversity: fetch_k=20 candidates, then select the k most diverse ones.
        # This prevents multiple similar chunks from the same promotion crowding
        # out chunks from other relevant documents.
        self.retriever = self.db.as_retriever(
            search_type="mmr",
            search_kwargs={"k": RETRIEVER_K, "fetch_k": RETRIEVER_K * 3},
        )
        
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

    def query_with_sources(self, question: str) -> tuple[str, list]:
        """
        Query the RAG system and also return the retrieved source documents.

        This is used by the evaluation pipeline to compute retrieval metrics
        (e.g. MRR) without a redundant second retriever call.

        Args:
            question: The user's question

        Returns:
            Tuple of (answer_string, list_of_retrieved_Documents).
            Each Document has a ``metadata["doc_id"]`` field when the
            LiveRAG/Benchmark collection was ingested.
        """
        retrieved_docs = self.retriever.invoke(question)
        context = self._format_docs(retrieved_docs)
        prompt_value = self.prompt.invoke({"context": context, "question": question})
        answer = self.llm.invoke(prompt_value)
        answer_text = answer.content if hasattr(answer, "content") else str(answer)
        return answer_text, retrieved_docs


# Singleton instance
_rag_service_instance = None


def get_rag_service() -> RAGService:
    """Get or create the RAG service singleton instance."""
    global _rag_service_instance
    if _rag_service_instance is None:
        _rag_service_instance = RAGService()
    return _rag_service_instance
