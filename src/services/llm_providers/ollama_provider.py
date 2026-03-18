"""Ollama local provider implementation."""
import os
from .base import LLMProvider


class OllamaProvider(LLMProvider):
    """Ollama local provider implementation."""

    def __init__(self, model: str = "llama3.1:8b", temperature: float = 0.0):
        """
        Initialize Ollama provider.

        Args:
            model: Model name as it appears in `ollama list` (e.g. 'llama3.1:8b')
            temperature: Temperature parameter for generation
        """
        self.model = model
        self.temperature = temperature
        self._llm = None

    def get_llm(self):
        """Get or create Ollama LLM instance."""
        if self._llm is None:
            from langchain_ollama import ChatOllama
            base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            self._llm = ChatOllama(
                model=self.model,
                temperature=self.temperature,
                base_url=base_url,
            )
        return self._llm
