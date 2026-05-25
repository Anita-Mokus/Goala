"""
Database-backed settings with caching.
Provides accessors for configuration that can be overridden in DB.
"""
from typing import Optional

# Cache for database settings to avoid repeated queries
_settings_cache: Optional[dict] = None


def get_settings_from_db() -> Optional[dict]:
    """
    Fetch settings from database.
    Returns None if database is not available or settings don't exist.
    """
    global _settings_cache
    
    # Return cached settings if available
    if _settings_cache is not None:
        return _settings_cache
    
    try:
        from src.models.database import AppSettings, get_db_session
        
        with get_db_session() as session:
            settings = session.query(AppSettings).filter(AppSettings.id == 1).first()
            
            if settings:
                _settings_cache = {
                    'dataset_name': settings.dataset_name,
                    'llm_provider': settings.llm_provider,
                    'llm_model': settings.llm_model,
                    'llm_temperature': settings.llm_temperature,
                    'retriever_k': settings.retriever_k,
                    'pdf_language': settings.pdf_language,
                    'pdf_strategy': settings.pdf_strategy,
                    'chunk_max_characters': settings.chunk_max_characters,
                    'chunk_new_after_n_chars': settings.chunk_new_after_n_chars,
                    'chunk_overlap': settings.chunk_overlap,
                    'rag_prompt_template': settings.rag_prompt_template,
                }
                return _settings_cache
    except Exception as e:
        print(f"Warning: Could not load settings from database: {e}")
        print("Falling back to environment variables.")
    
    return None


def clear_settings_cache():
    """Clear the settings cache to force reload from database."""
    global _settings_cache
    _settings_cache = None


def get_current_dataset_name() -> str:
    """Get current dataset name from DB or env."""
    from src.config.env import DEFAULT_DATASET_KEY
    
    db_settings = get_settings_from_db()
    if db_settings:
        return db_settings['dataset_name']
    return DEFAULT_DATASET_KEY

def get_current_llm_provider() -> str:
    """Get current LLM provider from DB or env."""
    from src.config.env import LLM_PROVIDER
    
    db_settings = get_settings_from_db()
    if db_settings:
        return db_settings['llm_provider']
    return LLM_PROVIDER


def get_current_llm_model() -> str:
    """Get current LLM model from DB or env."""
    from src.config.env import (
        DEEPSEEK_LLM_MODEL,
        GROQ_LLM_MODEL,
        OPENROUTER_LLM_MODEL,
        OLLAMA_LLM_MODEL
    )
    
    db_settings = get_settings_from_db()
    if db_settings:
        return db_settings['llm_model']
    
    # Fallback to env-based model selection
    provider = get_current_llm_provider()
    if provider.lower() == "deepseek":
        return DEEPSEEK_LLM_MODEL
    elif provider.lower() == "groq":
        return GROQ_LLM_MODEL
    elif provider.lower() == "openrouter":
        return OPENROUTER_LLM_MODEL
    elif provider.lower() == "ollama":
        return OLLAMA_LLM_MODEL
    return OPENROUTER_LLM_MODEL


def get_current_llm_temperature() -> float:
    """Get current LLM temperature from DB or env."""
    from src.config.env import LLM_TEMPERATURE
    
    db_settings = get_settings_from_db()
    if db_settings:
        return db_settings['llm_temperature']
    return LLM_TEMPERATURE


def get_current_retriever_k() -> int:
    """Get current retriever K from DB or env."""
    from src.config.env import RETRIEVER_K
    
    db_settings = get_settings_from_db()
    if db_settings:
        return db_settings['retriever_k']
    return RETRIEVER_K


def get_current_pdf_language() -> str:
    """Get current PDF language from DB or env."""
    from src.config.env import PDF_LANGUAGE
    
    db_settings = get_settings_from_db()
    if db_settings:
        return db_settings['pdf_language']
    return PDF_LANGUAGE


def get_current_pdf_strategy() -> str:
    """Get current PDF strategy from DB or env."""
    from src.config.env import PDF_STRATEGY
    
    db_settings = get_settings_from_db()
    if db_settings:
        return db_settings['pdf_strategy']
    return PDF_STRATEGY


def get_current_chunk_max_characters() -> int:
    """Get current chunk max characters from DB or env."""
    from src.config.env import CHUNK_MAX_CHARACTERS
    
    db_settings = get_settings_from_db()
    if db_settings:
        return db_settings['chunk_max_characters']
    return CHUNK_MAX_CHARACTERS


def get_current_chunk_new_after_n_chars() -> int:
    """Get current chunk new after N chars from DB or env."""
    from src.config.env import CHUNK_NEW_AFTER_N_CHARS
    
    db_settings = get_settings_from_db()
    if db_settings:
        return db_settings['chunk_new_after_n_chars']
    return CHUNK_NEW_AFTER_N_CHARS


def get_current_chunk_overlap() -> int:
    """Get current chunk overlap from DB or env."""
    from src.config.env import CHUNK_OVERLAP
    
    db_settings = get_settings_from_db()
    if db_settings:
        return db_settings['chunk_overlap']
    return CHUNK_OVERLAP


def get_current_rag_prompt_template() -> str:
    """Get current RAG prompt template from DB or env."""
    from src.config.env import RAG_PROMPT_TEMPLATE
    
    db_settings = get_settings_from_db()
    if db_settings:
        return db_settings['rag_prompt_template']
    return RAG_PROMPT_TEMPLATE
