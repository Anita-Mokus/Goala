"""
Configuration module for AI Chat Flow application.
Centralizes all configuration settings and environment variables.
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

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

Your role: Answer ONLY based on the provided context. If context is insufficient, say "Az adott információ nem elérhető a dokumentumok alapján" (in Hungarian).

CRITICAL RULES:
1. Use ONLY information from context - NEVER make up details
2. Quote specific dates, amounts, document names from context
3. If multiple promotions are mentioned, clearly distinguish them
4. For comparisons, list differences in a structured format
5. Respond in the same language as the question (Hungarian or English)

CONTEXT FROM DOCUMENTS:
{context}

QUESTION: {question}

ANSWER (be precise and concise):"""