"""
LLM Provider abstraction layer.
Allows easy switching between different LLM providers (Groq, DeepSeek, etc.)
"""
from abc import ABC, abstractmethod
from typing import Optional


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    def get_llm(self):
        """Get the LLM instance configured for this provider."""
        pass


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


class DeepSeekProvider(LLMProvider):
    """DeepSeek API provider implementation."""
    
    def __init__(self, model: str = "deepseek-chat", temperature: float = 0.3):
        """
        Initialize DeepSeek provider.
        
        Args:
            model: Model name (default: 'deepseek-chat')
            temperature: Temperature parameter for generation
        """
        self.model = model
        self.temperature = temperature
        self._llm = None
    
    def get_llm(self):
        """Get or create DeepSeek LLM instance."""
        if self._llm is None:
            from langchain_openai import ChatOpenAI
            self._llm = ChatOpenAI(
                model=self.model,
                temperature=self.temperature,
                base_url="https://api.deepseek.com",
            )
        return self._llm
    
class OpenRouterProvider(LLMProvider):
    """OpenRouter API provider implementation."""
    
    def __init__(self, model: str = "openai/gpt-oss-120b:exacto", temperature: float = 0.3):
        """
        Initialize OpenRouter provider.
        
        Args:
            model: Model name (default: 'openai/gpt-oss-120b:exacto')
            temperature: Temperature parameter for generation
        """
        self.model = model
        self.temperature = temperature
        self._llm = None
    
    def get_llm(self):
        """Get or create OpenRouter LLM instance."""
        if self._llm is None:
            from langchain_openai import ChatOpenAI
            self._llm = ChatOpenAI(
                model=self.model,
                temperature=self.temperature,
                base_url="https://openrouter.ai/api/v1",
            )
        return self._llm


def get_llm_provider(provider_name: str, model: str, temperature: float) -> LLMProvider:
    """
    Factory function to get the appropriate LLM provider.
    
    Args:
        provider_name: Name of the provider ('groq' or 'deepseek' or 'openrouter')
        model: Model name for the provider
        temperature: Temperature parameter for generation
        
    Returns:
        An instance of the requested LLM provider
        
    Raises:
        ValueError: If provider_name is not recognized
    """
    providers = {
        'groq': GroqProvider,
        'deepseek': DeepSeekProvider,
        'openrouter': OpenRouterProvider,
    }
    
    if provider_name.lower() not in providers:
        raise ValueError(
            f"Unknown LLM provider: {provider_name}. "
            f"Available providers: {', '.join(providers.keys())}"
        )
    
    provider_class = providers[provider_name.lower()]
    return provider_class(model=model, temperature=temperature)
