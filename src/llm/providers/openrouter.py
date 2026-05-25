"""OpenRouter API provider implementation."""
from src.llm.base import LLMProvider


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
            import os
            from langchain_openai import ChatOpenAI
            api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError(
                    "No API key found for OpenRouter. "
                    "Set OPENROUTER_API_KEY in your environment."
                )
            self._llm = ChatOpenAI(
                model=self.model,
                temperature=self.temperature,
                base_url="https://openrouter.ai/api/v1",
                api_key=api_key,
            )
        return self._llm
