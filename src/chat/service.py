"""
RAG Service.
Handles document retrieval and response generation.
"""
import time
from langchain_postgres import PGVector

from src.config import (
    DATABASE_URL,
    DEFAULT_DATASET_KEY,
    OLLAMA_BASE_URL,
    get_dataset_collection_name,
    normalize_dataset_key,
)
from src.config.settings import (
    get_current_llm_provider,
    get_current_llm_model,
    get_current_llm_temperature,
    get_current_retriever_k,
    clear_settings_cache,
)
from src.embeddings import get_embeddings
from src.llm import get_llm_provider
from src.prompts import get_rag_prompt_template
from src.chat.chain import create_rag_chain
from src.chat.history_logger import log_chat_to_history


class RAGService:
    """Service for handling RAG operations."""
    
    def __init__(self, dataset_key: str = DEFAULT_DATASET_KEY):
        """Initialize RAG components."""
        self.dataset_key = normalize_dataset_key(dataset_key)
        # Use shared embedding function (singleton)
        self.embedding_function = get_embeddings()
        
        # Load vector database from PostgreSQL
        try:
            self.db = PGVector(
                embeddings=self.embedding_function,
                connection=DATABASE_URL,
                collection_name=get_dataset_collection_name(self.dataset_key),
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
        rag_prompt_template = get_rag_prompt_template()
        
        # Initialize LLM using the configured provider
        provider = get_llm_provider(llm_provider, llm_model, llm_temperature, base_url=OLLAMA_BASE_URL)
        self.llm = provider.get_llm()
        self.current_model = llm_model
        
        # Create retriever
        self.retriever = self.db.as_retriever(search_kwargs={"k": retriever_k})
        
        # Create chain
        self.chain = create_rag_chain(self.retriever, rag_prompt_template, self.llm)
    
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
        log_chat_to_history(question, answer, self.current_model, response_time_ms)
        
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
        log_chat_to_history(question, answer, self.current_model, response_time_ms, source, message_metadata)
        
        return answer
