"""DeepSeek API provider implementation."""
import os
from .base import LLMProvider


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
            api_key = os.getenv("OPENAI_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
            self._llm = ChatOpenAI(
                model=self.model,
                temperature=self.temperature,
                base_url="https://api.deepseek.com",
                api_key=api_key,
            )
        return self._llm
