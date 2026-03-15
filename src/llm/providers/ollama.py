"""Ollama local model provider implementation."""
from src.llm.base import LLMProvider


class OllamaProvider(LLMProvider):
    """Ollama local model provider implementation."""
    
    def __init__(self, model: str = "qwen2.5", temperature: float = 0.3, base_url: str = "http://localhost:11434"):
        """
        Initialize Ollama provider.
        
        Args:
            model: Model name (default: 'qwen2.5')
            temperature: Temperature parameter for generation
            base_url: Ollama server base URL (default: 'http://localhost:11434')
        """
        self.model = model
        self.temperature = temperature
        self.base_url = base_url
        self._llm = None
    
    def get_llm(self):
        """Get or create Ollama LLM instance."""
        if self._llm is None:
            from langchain_ollama import ChatOllama
            self._llm = ChatOllama(
                model=self.model,
                temperature=self.temperature,
                base_url=self.base_url,
            )
        return self._llm
