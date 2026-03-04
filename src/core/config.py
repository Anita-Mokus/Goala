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

# Unstructured partitioning configuration
# Strategy options: "auto", "fast", "hi_res", "ocr_only"
# - "auto": Smart selection (fast for text-heavy, hi_res for tables)
# - "fast": Quick extraction for text-based PDFs
# - "hi_res": Best accuracy for complex layouts and tables (slower)
# - "ocr_only": Force OCR for scanned documents

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

HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN", "")

# Judge LLM — used only during evaluation, kept separate from the RAG LLM
# so the model scoring answers is independent of the model producing them.
JUDGE_LLM_PROVIDER = os.getenv("JUDGE_LLM_PROVIDER", "ollama")
JUDGE_LLM_MODEL = os.getenv("JUDGE_LLM_MODEL", "llama3.1:8b")

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


# Prompt template for the LiveRAG/Benchmark evaluation dataset.
# The dataset contains English general-knowledge questions backed by FineWeb
# web passages.  The expected answers are short and factual (1-3 sentences),
# so the template prioritises precision and conciseness over completeness.
LIVERAG_RAG_PROMPT_TEMPLATE = """You are a precise question-answering assistant. Your only job is to extract and state the correct answer from the provided passages.

RULES:
1. Base your answer EXCLUSIVELY on the passages below — never use outside knowledge.
2. Copy numbers, dates, names and units EXACTLY as they appear in the text.
3. If the answer requires combining information from multiple passages, do so clearly.
4. Keep the answer short and direct (1-3 sentences). Do not add disclaimers or filler.
5. If none of the passages contain the answer, reply exactly: "The answer is not present in the provided context."

PASSAGES:
{context}

QUESTION: {question}

ANSWER: (be precise and concise):"""