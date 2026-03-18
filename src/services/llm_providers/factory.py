"""Factory function for creating LLM providers."""
from .base import LLMProvider
from .groq_provider import GroqProvider
from .deepseek_provider import DeepSeekProvider
from .openrouter_provider import OpenRouterProvider
from .ollama_provider import OllamaProvider


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
        'ollama': OllamaProvider,
    }
    
    if provider_name.lower() not in providers:
        raise ValueError(
            f"Unknown LLM provider: {provider_name}. "
            f"Available providers: {', '.join(providers.keys())}"
        )
    
    provider_class = providers[provider_name.lower()]
    return provider_class(model=model, temperature=temperature)
