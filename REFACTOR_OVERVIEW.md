# Backend Source Code Structure Overview

This document provides a comprehensive overview of the refactored backend `src/` folder structure.

---

## Directory Tree

```
src/
├── config/              # Configuration: env vars + DB-backed settings
├── api/                 # HTTP application layer
│   └── routes/          # API route handlers
├── chat/                # RAG feature (retrieval-augmented generation)
├── prompts/             # AI prompt templates
├── llm/                 # LLM provider abstraction
│   └── providers/       # Individual provider implementations
├── embeddings/          # Embedding model singleton
├── ingest/              # Document ingestion pipeline
├── integrations/        # External integrations
│   └── messenger/       # Facebook Messenger bot
├── models/              # SQLAlchemy database models
├── evaluation/          # RAG evaluation with LLM-as-judge
└── utils/               # CLI tools
```

---

## Module Purpose and Contents

### 1. `config/` — Configuration Management

**Purpose**: Single source of truth for all configuration (environment variables and database-backed settings).

**Files**:
- **`env.py`** (99 lines): Environment variables and static constants
  - Database URL, API settings, CORS config
  - LLM provider defaults (Groq, DeepSeek, OpenRouter, Ollama)
  - Embedding model name, PDF processing config
  - Chunking parameters, retriever settings
  - Default RAG prompt template

- **`settings.py`** (172 lines): Database-backed settings with caching
  - `get_settings_from_db()` — fetch settings from DB (cached)
  - `clear_settings_cache()` — invalidate cache
  - `get_current_*()` functions — accessor pattern for all settings (DB → env fallback)

- **`__init__.py`** (92 lines): Package exports for convenient imports

**Dependencies**: `config/settings.py` → `models/database.py` (for DB access)

---

### 2. `api/` — HTTP Application Layer

**Purpose**: FastAPI application, routers, and dependency injection. No business logic.

**Files**:
- **`app.py`** (80 lines): FastAPI app initialization
  - App instance creation with title/description/version
  - CORS middleware configuration
  - Router registration (chat, settings, history, messenger)
  - Startup event: auto-ingest documents if DB empty, clear stale Messenger status

- **`dependencies.py`** (28 lines): Dependency injection
  - `get_rag_service()` — singleton RAG service with lazy initialization

- **`routes/chat.py`** (78 lines): Core chat endpoints
  - `GET /` — API status
  - `GET /health` — health check (DB + service)
  - `POST /chat` — main chat endpoint (accepts `ChatRequest`, returns `ChatResponse`)

- **`routes/history.py`** (109 lines): Chat history management
  - `GET /api/history` — paginated history with optional search
  - `GET /api/history/{id}` — single history entry

- **`routes/settings.py`** (143 lines): Settings CRUD
  - `GET /api/settings` — get current settings from DB
  - `PUT /api/settings` — update settings and clear cache

- **`routes/messenger.py`** (379 lines): Messenger bot control
  - `GET /api/messenger/status` — bot status (checks in-process or status file)
  - `POST /api/messenger/start` — start bot in background thread
  - `POST /api/messenger/stop` — stop bot
  - `POST /api/messenger/pause`, `/resume` — pause/resume
  - `GET /api/messenger/debug` — debug conversation detection
  - `GET /api/messenger/diagnostics` — Chrome/ChromeDriver diagnostics

**Dependencies**:  
`api/app.py` → `api/routes/*`, `ingest/`, `integrations/messenger/`  
`api/routes/chat.py` → `api/dependencies`, `config`  
`api/routes/messenger.py` → `integrations/messenger/registry`, `integrations/messenger/status_file`, `integrations/messenger/bot`

---

### 3. `chat/` — RAG Service

**Purpose**: Retrieval-augmented generation logic. Coordinates retriever, prompt, LLM, and history logging.

**Files**:
- **`chain.py`** (34 lines): RAG chain builder
  - `format_docs()` — format retrieved documents
  - `create_rag_chain(retriever, prompt_template, llm)` — build LangChain runnable

- **`history_logger.py`** (35 lines): Chat history logging
  - `log_chat_to_history(question, answer, model_used, response_time_ms, source, message_metadata)` — insert into DB

- **`service.py`** (127 lines): RAG service orchestrator
  - `RAGService.__init__()` — init embeddings, PGVector, chain
  - `_initialize_chain()` — build chain with current settings (LLM provider, prompt, retriever K)
  - `query(question)` — main query method (clears cache, reinits chain, measures time, logs)
  - `query_with_metadata(question, source, message_metadata)` — query with custom metadata

**Dependencies**:  
`chat/service.py` → `chat/chain`, `chat/history_logger`, `config`, `embeddings`, `llm`, `prompts`, `models`  
`chat/chain.py` → langchain packages only

**Flow**:
1. User sends question → `RAGService.query()`
2. Clear settings cache, reinitialize chain (reads DB for latest settings)
3. Chain: retriever → format → prompt → LLM → parse
4. Measure response time
5. Log to `ChatHistory` table via `log_chat_to_history()`
6. Return answer

---

### 4. `prompts/` — Prompt Templates

**Purpose**: Isolated prompt template strings. No LLM calls, no chain logic.

**Files**:
- **`rag_templates.py`** (12 lines): RAG prompt template accessor
  - `get_rag_prompt_template()` — returns template from DB or env default

**Dependencies**: `prompts` → `config/settings`

**Template format**: String with `{context}` and `{question}` placeholders.

---

### 5. `llm/` — LLM Provider Abstraction

**Purpose**: Unified interface for multiple LLM providers (Groq, DeepSeek, OpenRouter, Ollama).

**Files**:
- **`base.py`** (14 lines): Abstract base class
  - `LLMProvider(ABC)` with abstract `get_llm()` method

- **`providers/groq.py`** (29 lines): Groq provider
  - `GroqProvider(model, temperature)` → `ChatGroq` instance

- **`providers/deepseek.py`** (30 lines): DeepSeek provider
  - `DeepSeekProvider(model, temperature)` → `ChatOpenAI` with `base_url="https://api.deepseek.com"`

- **`providers/openrouter.py`** (30 lines): OpenRouter provider
  - `OpenRouterProvider(model, temperature)` → `ChatOpenAI` with `base_url="https://openrouter.ai/api/v1"`

- **`providers/ollama.py`** (33 lines): Ollama (local) provider
  - `OllamaProvider(model, temperature, base_url)` → `ChatOllama`

- **`factory.py`** (49 lines): Factory function
  - `get_llm_provider(provider_name, model, temperature, base_url=None)` → returns provider instance
  - Validates provider name and routes to correct class

**Dependencies**: `llm` → config (for defaults if needed; factory receives all params from caller)

**Extension**: To add a new provider, create `providers/new_provider.py`, register in `factory.py`.

---

### 6. `embeddings/` — Embedding Singleton

**Purpose**: Singleton for HuggingFace embedding model (CPU-only). Ensures only one instance is created.

**Files**:
- **`huggingface.py`** (26 lines): Singleton getter
  - `get_embeddings()` → `HuggingFaceEmbeddings(model_name="BAAI/bge-m3", device="cpu", normalize=True)`

**Dependencies**: `embeddings` → `config` (for `EMBEDDING_MODEL`)

**Critical**: Always use `get_embeddings()`, never instantiate `HuggingFaceEmbeddings` directly elsewhere (per project rules).

---

### 7. `ingest/` — Document Ingestion Pipeline

**Purpose**: Load documents, partition, chunk semantically, embed, and store in pgvector.

**Files**:
- **`partition.py`** (53 lines): Document partitioning
  - `partition_file(file_path, pdf_strategy, languages)` — routes to `unstructured` partitioners (PDF, TXT, auto)

- **`chunking.py`** (91 lines): Semantic chunking
  - `chunk_elements(elements, chunk_max_chars, chunk_new_after, chunk_overlap, multipage_sections)` — uses `unstructured.chunking.title.chunk_by_title`
  - `elements_to_documents(chunks, source_file)` — convert to LangChain `Document` objects with metadata

- **`vector_store.py`** (50 lines): Vector store management
  - `ensure_extension_exists(connection_string)` — creates pgvector extension
  - `create_vector_store(documents, embedding_function, connection_string, collection_name)` — `PGVector.from_documents()`

- **`service.py`** (218 lines): Ingestion orchestrator
  - `IngestService.__init__()` — init embeddings, read chunking/partitioning config
  - `check_collection_exists()` — test if vector DB has documents
  - `ingest_document(doc_path)` — single file ingestion
  - `ingest_all_documents()` — batch ingestion with per-file error isolation

**Dependencies**: `ingest/service.py` → `ingest/partition`, `ingest/chunking`, `ingest/vector_store`, `config`, `embeddings`

**Flow**:
1. List supported files in `data/` folder
2. For each file: partition → chunk → convert to Documents
3. Collect all Documents
4. Create vector store (clears existing collection, embeds, stores in PostgreSQL)

---

### 8. `integrations/messenger/` — Messenger Bot

**Purpose**: Facebook Messenger automation bot. Monitors conversations, detects unread messages, gets RAG responses, sends replies.

**Files**:
- **`bot.py`** (216 lines): Bot core
  - `MessengerBot.__init__()` — init state, config, driver (none yet)
  - `start()` — create stealth driver, navigate to Messenger, wait for login, start main loop
  - `_wait_for_login(timeout)` — poll for login detection
  - `pause()`, `resume()`, `stop()` — lifecycle control
  - `request_process_unread_now()` — trigger immediate poll (wakes sleep event)
  - `get_status()` — return status dict
  - `_write_status_file()` — persist status to JSON file for API

- **`bot_loop.py`** (63 lines): Main monitoring loop
  - `run_main_loop(bot)` — infinite loop: check pause, poll unread, process messages, sleep (interruptible)

- **`bot_messages.py`** (181 lines): Message detection and extraction
  - `get_unread_messages(bot)` — scan sidebar for bold (unread) conversations, open each, extract message
  - `extract_latest_message(bot)` — parse latest message in open conversation
  - `extract_sender_name(bot)` — get sender name from conversation header/title

- **`bot_actions.py`** (177 lines): Message processing and sending
  - `process_message(bot, message)` — get RAG response, delay, send, mark processed
  - `get_rag_response(bot, message, sender, max_retries)` — call RAG API with retry logic
  - `send_message(bot, text)` — find input box, type, click send (or press Enter)

- **`registry.py`** (39 lines): Bot instance registry
  - `set_bot(bot, thread)`, `get_bot()`, `clear_bot()` — global state management for API routes

- **`status_file.py`** (36 lines): Status file reader
  - `read_status_file()` — read bot status from JSON file (for standalone processes), check if PID alive

- **`config.py`** (73 lines): Messenger config (unchanged)
  - `MessengerConfig` class with API URL, Chrome profile path, check intervals, response delays

- **`stealth_driver.py`** (214 lines): Selenium stealth driver (unchanged)
- **`setup_chrome_profile.py`** (175 lines): Chrome profile setup utility (unchanged)
- **`run.py`** (127 lines): Standalone bot runner (unchanged)

**Dependencies**: `integrations/messenger/bot.py` → `bot_loop`, `config`, `stealth_driver`; `bot_loop` → `bot_messages`, `bot_actions`

**Flow**:
1. API `POST /api/messenger/start` → creates `MessengerBot`, starts in thread
2. Bot: launch Chrome → wait for login → `run_main_loop()`
3. Loop: detect unread (bold text in sidebar) → open conversation → extract message
4. Check if already processed (hash-based deduplication)
5. Call `http://localhost:8000/chat` via requests → get RAG response
6. Send response in Messenger via Selenium
7. Mark processed, update stats, write status file
8. Sleep (random interval, interruptible by "process unread now" trigger)

---

### 9. `models/` — Database Models

**Purpose**: SQLAlchemy models and session management.

**Files**:
- **`database.py`** (83 lines): Models and session
  - `AppSettings` — singleton row (id=1) with LLM config, chunking config, prompt template
  - `ChatHistory` — Q&A log with model, response time, source, metadata (JSONB)
  - `get_db_session()` — context manager for session lifecycle

**Dependencies**: `models` → `config` (for `DATABASE_URL`)

**Schema**:
- `app_settings`: single row config (updated via `/api/settings` PUT)
- `chat_history`: log of all Q&A interactions (inserted by `chat/history_logger`)

---

### 10. `evaluation/` — RAG Evaluation

**Purpose**: Evaluate RAG system using LLM-as-judge on test datasets.

**Files**:
- **`config.py`** (18 lines): Evaluation constants
  - `EVAL_FILE_NAME`, `OUTPUT_DIR_NAME`, `OUTPUT_FILE_PREFIX`, `JUDGE_LLM_TEMPERATURE`, `MEMORY_CLEAR_INTERVAL`

- **`judge_prompt.py`** (66 lines): Judge prompt and parser
  - `JUDGE_PROMPT_TEMPLATE` — scoring rubric (1–5) prompt
  - `parse_judge_response(response)` — extract score and explanation from LLM output

- **`evaluate_rag.py`** (226 lines): Evaluation orchestrator
  - Load eval dataset from `shared/EVAL_FILE_NAME`
  - Init RAG service, judge LLM
  - For each question: get RAG answer, judge answer, log score
  - Calculate statistics (avg score, distribution)
  - Save results to JSON in `evaluation_results/`

**Dependencies**: `evaluation/evaluate_rag.py` → `chat`, `llm`, `config`, `evaluation/config`, `evaluation/judge_prompt`

**Usage**: `python -m src.evaluation.evaluate_rag`

---

### 11. `utils/` — CLI Tools

**Purpose**: Command-line utilities for manual interaction.

**Files**:
- **`query_cli.py`** (51 lines): Interactive query loop
  - Init `RAGService`, loop: read input → query → print answer

- **`ingest_cli.py`** (45 lines): Manual document ingestion
  - Init `IngestService`, call `ingest_all_documents()`

**Usage**:
- `python -m src.utils.query_cli`
- `python -m src.utils.ingest_cli`

---

## Dependency Graph (High-Level)

```
config ──┐
         ├─→ models
         │
         ├─→ embeddings
         ├─→ llm
         ├─→ prompts
         │
         └─→ chat ──┐
                    ├─→ chain
                    ├─→ history_logger
                    └─→ service
         
         ├─→ ingest ──┐
         │            ├─→ partition
         │            ├─→ chunking
         │            └─→ vector_store
         │
         └─→ api ──┐
                   ├─→ app
                   ├─→ dependencies
                   └─→ routes/* ──→ integrations/messenger/*, models

integrations/messenger/ ──┐
                          ├─→ bot
                          ├─→ bot_loop → bot_messages, bot_actions
                          ├─→ registry
                          └─→ status_file

evaluation/ → chat, llm, config
```

**No circular dependencies** — all imports flow downward from config to services to API.

---

## Entry Points

| Entry | Module | Description |
|------|--------|-------------|
| FastAPI app | `src.api.app:app` | Main HTTP server (uvicorn) |
| Query CLI | `src.utils.query_cli` | Interactive RAG query tool |
| Ingest CLI | `src.utils.ingest_cli` | Manual document ingestion |
| Evaluation | `src.evaluation.evaluate_rag` | RAG evaluation script |
| Messenger bot (standalone) | `src.integrations.messenger.run` | Standalone Messenger bot runner |

**Docker command**: `uvicorn src.api.app:app --host 0.0.0.0 --port 8000`

---

## File Count and Line Count Summary

| Module | Files | Approx Lines |
|--------|-------|--------------|
| `config/` | 3 | 270 |
| `api/` | 6 | 700 |
| `chat/` | 3 | 196 |
| `prompts/` | 2 | 20 |
| `llm/` | 7 | 180 |
| `embeddings/` | 2 | 35 |
| `ingest/` | 5 | 410 |
| `integrations/messenger/` | 10 | 1,400 |
| `models/` | 1 | 83 |
| `evaluation/` | 3 | 300 |
| `utils/` | 2 | 96 |
| **Total** | **44** | **~3,690** |

**Average file size**: ~84 lines (within the ~150 line target; largest files are orchestrators like `ingest/service.py` and `integrations/messenger/bot_messages.py`).

---

## Key Design Principles

1. **Single Responsibility**: Each file has one clear purpose (e.g., `chain.py` builds chains, `history_logger.py` logs to DB).
2. **Feature-Based Organization**: Modules organized by feature/concern (chat, ingest, messenger), not by technical layer (services, models).
3. **Dependency Direction**: Config → Core modules → Services → API. No circular imports.
4. **Singleton Pattern**: Embedding model and RAG service are singletons (lazy-initialized).
5. **Configuration Centralization**: All env vars in `config/env.py`, all DB-backed settings in `config/settings.py`.
6. **Behavior Preservation**: Refactor changed only structure and imports — no logic changes.

---

## Testing the Refactor

**Start the application**:
```bash
docker compose up -d --build
```

**Verify endpoints**:
- `http://localhost:8000/` — API status
- `http://localhost:8000/health` — health check
- `POST http://localhost:8000/chat` with `{"message": "Hello"}` — RAG query

**Check logs**:
```bash
docker compose logs -f api
```

**Manual tests**:
- Query CLI: `docker compose exec api python -m src.utils.query_cli`
- Ingest CLI: `docker compose exec api python -m src.utils.ingest_cli`
- Evaluation: `docker compose exec api python -m src.evaluation.evaluate_rag`

All functionality should work exactly as before the refactor.
