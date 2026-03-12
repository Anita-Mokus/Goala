"""
Configuration module for AI Chat Flow application.
Centralizes all configuration settings and environment variables.
Reads from database with fallback to environment variables.
"""
import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Cache for database settings to avoid repeated queries
_settings_cache: Optional[dict] = None

# Project paths
DATA_FOLDER = "data"

# PostgreSQL / pgvector configuration (using psycopg3 driver)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/goala"
)
PGVECTOR_COLLECTION_NAME = "document_embeddings"

# Model configurations
EMBEDDING_MODEL = "BAAI/bge-m3"
PDF_LANGUAGE = os.getenv("PDF_LANGUAGE", "hun")  # Language for PDF processing (hun = Hungarian)

# Unstructured partitioning configuration
# Strategy options: "auto", "fast", "hi_res", "ocr_only"
# - "auto": Smart selection (fast for text-heavy, hi_res for tables)
# - "fast": Quick extraction for text-based PDFs
# - "hi_res": Best accuracy for complex layouts and tables (slower)
# - "ocr_only": Force OCR for scanned documents
PDF_STRATEGY = os.getenv("PDF_STRATEGY", "auto")

# Unstructured chunking configuration (using chunk_by_title strategy)
CHUNK_MAX_CHARACTERS = int(os.getenv("CHUNK_MAX_CHARACTERS", "1000"))  # Hard maximum chunk size
CHUNK_NEW_AFTER_N_CHARS = int(os.getenv("CHUNK_NEW_AFTER_N_CHARS", "800"))  # Soft maximum (preferred size)
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))  # Overlap between chunks (applied on text-splitting)
CHUNK_MULTIPAGE_SECTIONS = os.getenv("CHUNK_MULTIPAGE_SECTIONS", "true").lower() == "true"  # Allow sections to span pages

# LLM Provider Selection
# Options: 'groq', 'deepseek', 'openrouter', or 'ollama'
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openrouter")

# Groq Model Options (when using Groq provider)
# "llama-3.3-70b-versatile"  # Faster with good accuracy
# "qwen/qwen3-32b"            # Pretty slow, but accurate
# "openai/gpt-oss-120b"       # Result after evaluation: 90%
GROQ_LLM_MODEL = os.getenv("GROQ_LLM_MODEL", "openai/gpt-oss-120b")

# DeepSeek Model Options (when using DeepSeek provider)
# "deepseek-chat"             # Non-thinking mode (faster, default)
# "deepseek-reasoner"         # Thinking mode (more accurate)
DEEPSEEK_LLM_MODEL = os.getenv("DEEPSEEK_LLM_MODEL", "deepseek-chat")

OPENROUTER_LLM_MODEL = os.getenv("OPENROUTER_LLM_MODEL", "openai/gpt-oss-120b:exacto")

# Ollama Model Options (when using Ollama provider)
# "qwen2.5"                   # Qwen 2.5 model
# "llama2"                    # Llama 2 model
# "mistral"                   # Mistral model
OLLAMA_LLM_MODEL = os.getenv("OLLAMA_LLM_MODEL", "qwen2.5")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Get the appropriate model based on provider
if LLM_PROVIDER.lower() == "deepseek":
    LLM_MODEL = DEEPSEEK_LLM_MODEL
elif LLM_PROVIDER.lower() == "groq":
    LLM_MODEL = GROQ_LLM_MODEL
elif LLM_PROVIDER.lower() == "openrouter":
    LLM_MODEL = OPENROUTER_LLM_MODEL
elif LLM_PROVIDER.lower() == "ollama":
    LLM_MODEL = OLLAMA_LLM_MODEL

LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.3"))  # Slightly higher for friendlier responses

# Retriever settings
RETRIEVER_K = 8  # Number of documents to retrieve

# API settings
API_TITLE = "AI Chat Flow API"
API_DESCRIPTION = "Hotel Chatbot API with RAG capabilities"
API_VERSION = "1.0.0"

# CORS settings
# Origins must exactly match the browser's Origin header (no trailing slashes)
CORS_ORIGINS = [
	"http://localhost:3000",
	"http://127.0.0.1:3000",
]
CORS_CREDENTIALS = True
CORS_METHODS = ["*"]
CORS_HEADERS = ["*"]

# Prompt template with security and personality
RAG_PROMPT_TEMPLATE = """You are an expert assistant for MBH Bank (Magyar Bankholding Bank Nyrt.) customer support.

Your role: Answer customer questions helpfully and naturally. Use the provided context when available, but you can also respond with general banking knowledge and natural conversation.

GUIDELINES:
1. For specific bank information (rates, products, policies): Use ONLY information from context
2. For general questions or conversational interactions: Respond naturally and helpfully
3. Quote specific dates, amounts, document names when available in context
4. If context is insufficient for specific bank info, say "Az adott információ nem elérhető a dokumentumok alapján" (in Hungarian)
5. For greetings, general banking questions, or polite conversation: Respond naturally using your knowledge
6. If multiple promotions are mentioned in context, clearly distinguish them
7. For comparisons using context, list differences in a structured format
8. Always respond in the same language as the question (Hungarian, Romanian, or English)

CONTEXT FROM DOCUMENTS:
{context}

QUESTION: {question}

ANSWER (be helpful, natural, and precise):"""


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


def get_current_llm_provider() -> str:
    """Get current LLM provider from DB or env."""
    db_settings = get_settings_from_db()
    if db_settings:
        return db_settings['llm_provider']
    return LLM_PROVIDER


def get_current_llm_model() -> str:
    """Get current LLM model from DB or env."""
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
    db_settings = get_settings_from_db()
    if db_settings:
        return db_settings['llm_temperature']
    return LLM_TEMPERATURE


def get_current_retriever_k() -> int:
    """Get current retriever K from DB or env."""
    db_settings = get_settings_from_db()
    if db_settings:
        return db_settings['retriever_k']
    return RETRIEVER_K


def get_current_pdf_language() -> str:
    """Get current PDF language from DB or env."""
    db_settings = get_settings_from_db()
    if db_settings:
        return db_settings['pdf_language']
    return PDF_LANGUAGE


def get_current_pdf_strategy() -> str:
    """Get current PDF strategy from DB or env."""
    db_settings = get_settings_from_db()
    if db_settings:
        return db_settings['pdf_strategy']
    return PDF_STRATEGY


def get_current_chunk_max_characters() -> int:
    """Get current chunk max characters from DB or env."""
    db_settings = get_settings_from_db()
    if db_settings:
        return db_settings['chunk_max_characters']
    return CHUNK_MAX_CHARACTERS


def get_current_chunk_new_after_n_chars() -> int:
    """Get current chunk new after N chars from DB or env."""
    db_settings = get_settings_from_db()
    if db_settings:
        return db_settings['chunk_new_after_n_chars']
    return CHUNK_NEW_AFTER_N_CHARS


def get_current_chunk_overlap() -> int:
    """Get current chunk overlap from DB or env."""
    db_settings = get_settings_from_db()
    if db_settings:
        return db_settings['chunk_overlap']
    return CHUNK_OVERLAP


def get_current_rag_prompt_template() -> str:
    """Get current RAG prompt template from DB or env."""
    db_settings = get_settings_from_db()
    if db_settings:
        return db_settings['rag_prompt_template']
    return RAG_PROMPT_TEMPLATE