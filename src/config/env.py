"""
Environment variables and static configuration constants.
Single source of truth for all env-based settings.
"""
import os
import hashlib
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project paths and dataset scoping
DEFAULT_DATASET_KEY = os.getenv("DEFAULT_DATASET_KEY", "sapientia")
DATASETS_ROOT = Path(os.getenv("DATASETS_ROOT", "shared"))


def normalize_dataset_key(dataset_key: str | None) -> str:
    """Normalize a dataset key into a safe, lowercase identifier."""
    key = (dataset_key or DEFAULT_DATASET_KEY).strip().lower()
    safe_key = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in key)
    return safe_key.strip("_") or DEFAULT_DATASET_KEY


def get_dataset_folder(dataset_key: str | None = None) -> Path:
    """Return the filesystem folder that stores files for a dataset."""
    return DATASETS_ROOT / normalize_dataset_key(dataset_key)


def get_dataset_collection_name(dataset_key: str | None = None) -> str:
    """Return the pgvector collection name for a dataset."""
    dataset_suffix = normalize_dataset_key(dataset_key)
    return f"{PGVECTOR_COLLECTION_PREFIX}_{dataset_suffix}"


def normalize_database_url(database_url: str | None = None) -> str:
    """Ensure SQLAlchemy uses the psycopg3 driver for Postgres connections."""
    url = (database_url or DATABASE_URL).strip()
    if url.startswith("postgresql+psycopg2://"):
        return url.replace("postgresql+psycopg2://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


DEFAULT_DATASET_FOLDER = str(get_dataset_folder())

# PostgreSQL / pgvector configuration (using psycopg3 driver)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/goala"
)
PGVECTOR_COLLECTION_PREFIX = os.getenv("PGVECTOR_COLLECTION_PREFIX", "document_embeddings")
PGVECTOR_COLLECTION_NAME = get_dataset_collection_name()

# Model configurations
EMBEDDING_MODEL = "BAAI/bge-m3"
PDF_LANGUAGE = os.getenv("PDF_LANGUAGE", "hun")

# Unstructured partitioning configuration
PDF_STRATEGY = os.getenv("PDF_STRATEGY", "auto")

# Unstructured chunking configuration (using chunk_by_title strategy)
CHUNK_MAX_CHARACTERS = int(os.getenv("CHUNK_MAX_CHARACTERS", "1000"))
CHUNK_NEW_AFTER_N_CHARS = int(os.getenv("CHUNK_NEW_AFTER_N_CHARS", "800"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))
CHUNK_MULTIPAGE_SECTIONS = os.getenv("CHUNK_MULTIPAGE_SECTIONS", "true").lower() == "true"

# LLM Provider Selection
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openrouter")

# Groq Model Options
GROQ_LLM_MODEL = os.getenv("GROQ_LLM_MODEL", "openai/gpt-oss-120b")

# DeepSeek Model Options
DEEPSEEK_LLM_MODEL = os.getenv("DEEPSEEK_LLM_MODEL", "deepseek-chat")

# OpenRouter Model Options
OPENROUTER_LLM_MODEL = os.getenv("OPENROUTER_LLM_MODEL", "openai/gpt-oss-120b:exacto")

# Ollama Model Options
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

LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.3"))

# Retriever settings
RETRIEVER_K = 8

# API settings
API_TITLE = "AI Chat Flow API"
API_DESCRIPTION = "Hotel Chatbot API with RAG capabilities"
API_VERSION = "1.0.0"

# CORS settings
DEFAULT_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", ",".join(DEFAULT_CORS_ORIGINS)).split(",")
    if origin.strip()
]
CORS_CREDENTIALS = True
CORS_METHODS = ["*"]
CORS_HEADERS = ["*"]

# Access gate settings
ACCESS_GATE_COOKIE_NAME = os.getenv("ACCESS_GATE_COOKIE_NAME", "goala_access")
ACCESS_GATE_SESSION_SECRET = os.getenv("ACCESS_GATE_SESSION_SECRET", "")
ACCESS_GATE_SESSION_TTL_SECONDS = int(os.getenv("ACCESS_GATE_SESSION_TTL_SECONDS", "604800"))
ACCESS_GATE_TOKEN_HASHES = [
    token_hash.strip().lower()
    for token_hash in os.getenv("ACCESS_GATE_TOKEN_HASHES", "").split(",")
    if token_hash.strip()
]


def hash_access_token(token: str) -> str:
    """Return the SHA-256 hash for an access token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

# Default RAG Prompt Template
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
