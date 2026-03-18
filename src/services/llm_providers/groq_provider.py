"""Groq API provider implementation."""
from .base import LLMProvider


class GroqProvider(LLMProvider):
    """Groq API provider implementation."""
    
    def __init__(self, model: str, temperature: float):
        """
        Initialize Groq provider.
        
        Args:
            model: Model name (e.g., 'openai/gpt-oss-120b')
            temperature: Temperature parameter for generation
        """
        self.model = model
        self.temperature = temperature
        self._llm = None
    
    def get_llm(self):
        """Get or create Groq LLM instance."""
        if self._llm is None:
            from langchain_groq import ChatGroq
            self._llm = ChatGroq(
                model=self.model,
                temperature=self.temperature
            )
        return self._llm
