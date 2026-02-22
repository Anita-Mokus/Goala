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

# Chunking strategy:
#   "semantic"   — embedding-based: split where cosine similarity drops (one chunk = one idea)
#   "definition" — one chunk per regulation clause / glossary entry
#   "title"      — original unstructured chunk_by_title, character-count-based (fallback)
CHUNKING_STRATEGY = os.getenv("CHUNKING_STRATEGY", "semantic")

# Semantic chunking options (used when CHUNKING_STRATEGY="semantic")
# breakpoint_threshold_type: "percentile" | "standard_deviation" | "interquartile" | "gradient"
# For "percentile"+95: split only on the sharpest 5% of similarity drops → larger, coherent chunks
SEMANTIC_CHUNK_BREAKPOINT_TYPE   = os.getenv("SEMANTIC_CHUNK_BREAKPOINT_TYPE", "percentile")
SEMANTIC_CHUNK_BREAKPOINT_AMOUNT = float(os.getenv("SEMANTIC_CHUNK_BREAKPOINT_AMOUNT", "95"))

# Definition-level chunking size guards (used when CHUNKING_STRATEGY="definition")
DEFINITION_CHUNK_MIN_CHARS = int(os.getenv("DEFINITION_CHUNK_MIN_CHARS", "50"))    # merge tiny fragments below this
DEFINITION_CHUNK_MAX_CHARS = int(os.getenv("DEFINITION_CHUNK_MAX_CHARS", "2000"))  # hard-split entries above this

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
RETRIEVER_K = int(os.getenv("RETRIEVER_K", "4"))          # Number of documents to retrieve when a doc filter matches
RETRIEVER_K_UNFILTERED = int(os.getenv("RETRIEVER_K_UNFILTERED", "6"))  # k when no filter matches (all docs)

# Metadata filtering: auto-detect doc references (e.g. "H-68/2024") in the user question
# and scope retrieval to only those chunks — prevents cross-document bleeding
ENABLE_METADATA_FILTER = os.getenv("ENABLE_METADATA_FILTER", "true").lower() == "true"

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