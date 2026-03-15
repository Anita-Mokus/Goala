"""
Chat history logging.
Logs Q&A interactions to the database.
"""
from typing import Optional


def log_chat_to_history(
    question: str,
    answer: str,
    model_used: str,
    response_time_ms: int,
    source: str = "api",
    message_metadata: Optional[dict] = None
):
    """
    Log Q&A to chat history table.
    
    Args:
        question: The user's question
        answer: The AI-generated answer
        model_used: The model used for generation
        response_time_ms: Response time in milliseconds
        source: The source of the message (api, messenger, etc.)
        message_metadata: Additional metadata (e.g., sender info)
    """
    try:
        from src.models.database import ChatHistory, get_db_session
        
        with get_db_session() as session:
            history_entry = ChatHistory(
                question=question,
                answer=answer,
                model_used=model_used,
                response_time_ms=response_time_ms,
                source=source,
                message_metadata=message_metadata
            )
            session.add(history_entry)
            session.commit()
    except Exception as e:
        print(f"Warning: Failed to log chat history: {e}")
