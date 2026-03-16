"""
RAG prompt templates.
Single responsibility: provide prompt template strings with placeholders.
"""
from src.config.settings import get_current_rag_prompt_template


def get_rag_prompt_template() -> str:
    """
    Get the RAG prompt template from DB or fallback to env default.
    
    Returns:
        Prompt template string with {context} and {question} placeholders
    """
    return get_current_rag_prompt_template()
