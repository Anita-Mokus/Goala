"""
LLM provider factory.
Routes to the appropriate provider based on provider name.
"""
from typing import Optional
from src.llm.base import LLMProvider
from src.llm.providers.groq import GroqProvider
from src.llm.providers.deepseek import DeepSeekProvider
from src.llm.providers.openrouter import OpenRouterProvider
from src.llm.providers.ollama import OllamaProvider


def get_llm_provider(provider_name: str, model: str, temperature: float, base_url: Optional[str] = None) -> LLMProvider:
    """
    Factory function to get the appropriate LLM provider.
    
    Args:
        provider_name: Name of the provider ('groq', 'deepseek', 'openrouter', or 'ollama')
        model: Model name for the provider
        temperature: Temperature parameter for generation
        base_url: Optional base URL for Ollama provider
        
    Returns:
        An instance of the requested LLM provider
        
    Raises:
        ValueError: If provider_name is not recognized
    """
    providers = {
        'groq': GroqProvider,
        'deepseek': DeepSeekProvider,
        'openrouter': OpenRouterProvider,
        'ollama': OllamaProvider,
    }
    
    if provider_name.lower() not in providers:
        raise ValueError(
            f"Unknown LLM provider: {provider_name}. "
            f"Available providers: {', '.join(providers.keys())}"
        )
    
    provider_class = providers[provider_name.lower()]
    
    # Pass base_url to OllamaProvider if provided
    if provider_name.lower() == 'ollama' and base_url:
        return provider_class(model=model, temperature=temperature, base_url=base_url)
    
    return provider_class(model=model, temperature=temperature)
