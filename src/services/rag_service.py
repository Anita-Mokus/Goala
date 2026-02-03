"""
RAG (Retrieval-Augmented Generation) Service.
Handles document retrieval and response generation using LangChain.
"""
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

from src.core.config import (
    CHROMA_PATH,
    EMBEDDING_MODEL,
    LLM_MODEL,
    LLM_TEMPERATURE,
    RETRIEVER_K,
    RAG_PROMPT_TEMPLATE
)


class RAGService:
    """Service for handling RAG operations."""
    
    def __init__(self):
        """Initialize RAG components."""
        import os
        
        # Check if vector database exists
        if not os.path.exists(CHROMA_PATH):
            raise RuntimeError(
                f"Vector database directory '{CHROMA_PATH}' not found. "
                "Please run document ingestion first."
            )
        
        if not os.listdir(CHROMA_PATH):
            raise RuntimeError(
                f"Vector database directory '{CHROMA_PATH}' is empty. "
                "Please run document ingestion first."
            )
        
        # Initialize embedding function
        self.embedding_function = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
        
        # Load vector database
        try:
            self.db = Chroma(
                persist_directory=CHROMA_PATH,
                embedding_function=self.embedding_function
            )
        except Exception as e:
            raise RuntimeError(f"Failed to load vector database: {str(e)}")
        
        # Initialize LLM
        self.llm = ChatGroq(
            model=LLM_MODEL,
            temperature=LLM_TEMPERATURE
        )
        
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
