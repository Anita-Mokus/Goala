"""
RAG (Retrieval-Augmented Generation) Service.
Handles document retrieval and response generation using LangChain with pgvector.
"""
import time
from langchain_postgres import PGVector
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

from src.core.config import (
    DATABASE_URL,
    PGVECTOR_COLLECTION_NAME,
    OLLAMA_BASE_URL,
    get_current_llm_provider,
    get_current_llm_model,
    get_current_llm_temperature,
    get_current_retriever_k,
    get_current_rag_prompt_template,
    clear_settings_cache
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
        
        # Initialize components with current settings
        self._initialize_chain()
    
    def _initialize_chain(self):
        """Initialize or reinitialize the RAG chain with current settings."""
        # Get current settings from DB or env
        llm_provider = get_current_llm_provider()
        llm_model = get_current_llm_model()
        llm_temperature = get_current_llm_temperature()
        retriever_k = get_current_retriever_k()
        rag_prompt_template = get_current_rag_prompt_template()
        
        # Initialize LLM using the configured provider
        provider = get_llm_provider(llm_provider, llm_model, llm_temperature, base_url=OLLAMA_BASE_URL)
        self.llm = provider.get_llm()
        self.current_model = llm_model
        
        # Create prompt template
        self.prompt = ChatPromptTemplate.from_template(rag_prompt_template)
        
        # Create retriever
        self.retriever = self.db.as_retriever(search_kwargs={"k": retriever_k})
        
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
    
    def _log_to_history(self, question: str, answer: str, response_time_ms: int, 
                        source: str = "api", message_metadata: dict = None):
        """
        Log Q&A to chat history table.
        
        Args:
            question: The user's question
            answer: The AI-generated answer
            response_time_ms: Response time in milliseconds
            source: The source of the message (api, messenger, etc.)
            message_metadata: Additional metadata (e.g., sender info)
        """
        try:
            from src.models.database import ChatHistory, get_db_session
            
            with get_db_session() as session:
                history_entry = ChatHistory(
                    question=question,
                    answer=answer,
                    model_used=self.current_model,
                    response_time_ms=response_time_ms,
                    source=source,
                    message_metadata=message_metadata
                )
                session.add(history_entry)
                session.commit()
        except Exception as e:
            print(f"Warning: Failed to log chat history: {e}")
    
    def query(self, question: str) -> str:
        """
        Query the RAG system with a question.
        
        Args:
            question: The user's question
            
        Returns:
            The AI-generated response
        """
        # Clear settings cache to ensure fresh read on each query
        clear_settings_cache()
        
        # Reinitialize chain with potentially updated settings
        self._initialize_chain()
        
        # Measure response time
        start_time = time.time()
        answer = self.chain.invoke(question)
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # Log to history
        self._log_to_history(question, answer, response_time_ms)
        
        return answer
    
    def query_with_metadata(self, question: str, source: str = "api", 
                           message_metadata: dict = None) -> str:
        """
        Query the RAG system with a question and log with custom metadata.
        
        Args:
            question: The user's question
            source: The source of the message (api, messenger, etc.)
            message_metadata: Additional metadata (e.g., sender info)
            
        Returns:
            The AI-generated response
        """
        # Clear settings cache to ensure fresh read on each query
        clear_settings_cache()
        
        # Reinitialize chain with potentially updated settings
        self._initialize_chain()
        
        # Measure response time
        start_time = time.time()
        answer = self.chain.invoke(question)
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # Log to history with metadata
        self._log_to_history(question, answer, response_time_ms, source, message_metadata)
        
        return answer


# Singleton instance
_rag_service_instance = None


def get_rag_service() -> RAGService:
    """Get or create the RAG service singleton instance."""
    global _rag_service_instance
    if _rag_service_instance is None:
        _rag_service_instance = RAGService()
    return _rag_service_instance
