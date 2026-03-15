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
            from langchain_openai import ChatOpenAI
            self._llm = ChatOpenAI(
                model=self.model,
                temperature=self.temperature,
                base_url="https://openrouter.ai/api/v1",
            )
        return self._llm
