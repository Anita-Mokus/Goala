"""Abstract base class for LLM providers."""
from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    def get_llm(self):
        """Get the LLM instance configured for this provider."""
        pass
