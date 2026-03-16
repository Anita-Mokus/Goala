"""
FastAPI application initialization.
Configures app, CORS, routers, and startup event.
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import (
    API_TITLE,
    API_DESCRIPTION,
    API_VERSION,
    CORS_ORIGINS,
    CORS_CREDENTIALS,
    CORS_METHODS,
    CORS_HEADERS,
)
from src.api.routes import settings, history, messenger, chat


# Initialize FastAPI app
app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION,
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=CORS_CREDENTIALS,
    allow_methods=CORS_METHODS,
    allow_headers=CORS_HEADERS,
)

# Register API routers
app.include_router(chat.router)
app.include_router(settings.router)
app.include_router(history.router)
app.include_router(messenger.router)


@app.on_event("startup")
def startup_event():
    """Run ingestion on startup if vector database doesn't have documents."""
    # Clear stale Messenger bot status file from previous container runs
    try:
        from src.integrations.messenger.config import MessengerConfig
        if MessengerConfig.STATUS_FILE and os.path.exists(MessengerConfig.STATUS_FILE):
            os.remove(MessengerConfig.STATUS_FILE)
            print("Cleared stale Messenger bot status file")
    except Exception as e:
        print(f"Warning: Could not clear Messenger status file: {e}")
    
    try:
        from src.ingest import IngestService
        ingest_service = IngestService()
        
        # Check if collection already has documents
        has_documents = ingest_service.check_collection_exists()
        
        if not has_documents:
            print("\n" + "="*50)
            print("Vector database empty. Starting document ingestion...")
            print("="*50 + "\n")
            
            ingest_service.ingest_all_documents()
            
            print("\n" + "="*50)
            print("Document ingestion completed successfully!")
            print("="*50 + "\n")
        else:
            print("Vector database found with documents. Skipping ingestion.")
    except Exception as e:
        print(f"Warning: Failed to initialize vector database: {e}")
        print("The service will start, but /chat endpoint may not work until database is initialized.")
