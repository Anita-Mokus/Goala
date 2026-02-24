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
# Options: 'groq' or 'deepseek' or 'openrouter'
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

# Get the appropriate model based on provider
if LLM_PROVIDER.lower() == "deepseek":
    LLM_MODEL = DEEPSEEK_LLM_MODEL
elif LLM_PROVIDER.lower() == "groq":
    LLM_MODEL = GROQ_LLM_MODEL
elif LLM_PROVIDER.lower() == "openrouter":
    LLM_MODEL = OPENROUTER_LLM_MODEL

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

Your role: Answer ONLY based on the provided context documents. If — and ONLY if — after carefully reading ALL context chunks the information is truly absent, say "Az adott információ nem elérhető a dokumentumok alapján" (in Hungarian).

CRITICAL RULES:
1. Use ONLY information from context - NEVER make up details
2. READ ALL context chunks carefully before concluding the information is missing
3. For dates, amounts and document identifiers: copy them EXACTLY as they appear in context; never guess or infer
4. If multiple promotions with similar names appear, identify the correct one by matching ALL keywords in the question
5. For comparisons, list differences in a structured format, drawing from whichever context chunks contain each side
6. If the answer spans several context chunks, synthesise them into one coherent answer
7. Respond in the same language as the question (Hungarian or English)

CONTEXT FROM DOCUMENTS:
{context}

QUESTION: {question}

ANSWER (be precise and concise):"""