# Quick Reference Guide

## 🚀 Common Commands

### Starting the Application

```bash
# Start API server (Windows)
start_api.bat

# Start API server (Linux/Mac)
./start_api.sh

# Or manually
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Working with Documents

```bash
# Ingest PDF documents
python -m src.utils.ingest_cli

# Ingest specific PDF
python -m src.utils.ingest_cli path/to/your/file.pdf
```

### Interactive Query

```bash
# Start CLI chat interface
python -m src.utils.query_cli
```

### Testing

```bash
# Test Groq API connection
python -m tests.test_setup
```

## 📂 Important Files

| File | Description |
|------|-------------|
| `src/api/main.py` | FastAPI application with endpoints |
| `src/core/config.py` | All configuration settings |
| `src/services/rag_service.py` | RAG query logic |
| `src/services/ingest_service.py` | PDF ingestion logic |
| `.env` | Environment variables (API keys) |
| `requirements.txt` | Python dependencies |

## 🔧 Configuration

Edit `src/core/config.py` to customize:

- **LLM Model**: Change `LLM_MODEL` variable
- **Temperature**: Adjust `LLM_TEMPERATURE` (0 = deterministic, 1 = creative)
- **Retrieval**: Modify `RETRIEVER_K` (documents to retrieve)
- **CORS**: Update `CORS_ORIGINS` for production

## 🌐 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API status and info |
| `/health` | GET | Health check |
| `/chat` | POST | Send message, get response |
| `/docs` | GET | Interactive API docs |

## 📝 Example API Call

```bash
# Using curl
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "What are your room rates?"}'

# Using Python
import requests
response = requests.post(
    "http://localhost:8000/chat",
    json={"message": "What are your room rates?"}
)
print(response.json()["response"])
```

## 🐛 Troubleshooting

### Import Errors
```bash
# Reinstall dependencies
pip install -r requirements.txt
```

### API Not Starting
```bash
# Check if port 8000 is in use
netstat -ano | findstr :8000  # Windows
lsof -i :8000  # Linux/Mac

# Use different port
uvicorn src.api.main:app --port 8001
```

### Missing API Key
```bash
# Verify .env file exists and contains GROQ_API_KEY
type .env  # Windows
cat .env   # Linux/Mac
```

## 📦 Project Structure Explained

```
src/
├── api/          # HTTP endpoints (FastAPI routes)
├── core/         # Shared config and constants
├── services/     # Business logic (no HTTP dependencies)
└── utils/        # Helper scripts and CLI tools

tests/            # Test files
data/             # Input PDFs
chroma_db/        # Vector database (generated)
```

## 🔄 Development Workflow

1. **Add new PDF**: Place in `data/` folder
2. **Ingest**: Run `python -m src.utils.ingest_cli`
3. **Test**: Use `python -m src.utils.query_cli`
4. **Deploy**: Start API with `start_api.bat` or `start_api.sh`

## 🎯 Key Design Principles

- **Separation of Concerns**: API, services, and config are separate
- **Single Responsibility**: Each module has one clear purpose
- **Dependency Injection**: Services are instantiated via factory functions
- **Configuration**: Centralized in `config.py`
- **Imports**: Absolute imports from `src/` package
