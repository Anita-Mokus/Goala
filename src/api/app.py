"""
FastAPI application initialization.
Configures app, CORS, routers, and startup event.
"""
import asyncio
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
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

RUN_STARTUP_INGEST = os.getenv("RUN_STARTUP_INGEST", "false").lower() == "true"


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


@app.websocket("/websockify")
async def websocket_vnc_proxy(websocket: WebSocket):
    """Proxy browser websocket frames to the local VNC TCP server."""
    await websocket.accept()

    try:
        reader, writer = await asyncio.open_connection("127.0.0.1", 5900)
    except Exception:
        await websocket.close(code=1011)
        return

    async def websocket_to_vnc() -> None:
        try:
            while True:
                message = await websocket.receive()
                payload_bytes = message.get("bytes")
                payload_text = message.get("text")

                if payload_bytes is not None:
                    writer.write(payload_bytes)
                    await writer.drain()
                elif payload_text is not None:
                    writer.write(payload_text.encode("utf-8"))
                    await writer.drain()
                elif message.get("type") == "websocket.disconnect":
                    break
        except WebSocketDisconnect:
            pass
        except Exception:
            pass

    async def vnc_to_websocket() -> None:
        try:
            while True:
                data = await reader.read(65536)
                if not data:
                    break
                await websocket.send_bytes(data)
        except Exception:
            pass

    tasks = [
        asyncio.create_task(websocket_to_vnc()),
        asyncio.create_task(vnc_to_websocket()),
    ]

    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

    for task in pending:
        task.cancel()

    for task in done:
        try:
            task.result()
        except Exception:
            pass

    try:
        writer.close()
        await writer.wait_closed()
    except Exception:
        pass

    try:
        await websocket.close()
    except Exception:
        pass


@app.on_event("startup")
def startup_event():
    """Run ingestion on startup if vector database doesn't have documents."""
    if not RUN_STARTUP_INGEST:
        return

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
