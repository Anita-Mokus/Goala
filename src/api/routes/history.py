"""
API routes for chat history management.
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional

from src.models.database import ChatHistory, get_db_session

router = APIRouter(prefix="/api/history", tags=["history"])


class ChatHistoryResponse(BaseModel):
    """Response model for chat history entry."""
    id: int
    question: str
    answer: str
    model_used: Optional[str]
    response_time_ms: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


class ChatHistoryListResponse(BaseModel):
    """Response model for paginated chat history."""
    items: List[ChatHistoryResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


@router.get("", response_model=ChatHistoryListResponse)
def get_chat_history(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search in questions and answers")
):
    """
    Get paginated chat history.
    
    Args:
        page: Page number (starts at 1)
        page_size: Number of items per page (max 100)
        search: Optional search term to filter questions/answers
        
    Returns:
        ChatHistoryListResponse: Paginated chat history
    """
    try:
        with get_db_session() as session:
            # Build query
            query = session.query(ChatHistory)
            
            # Apply search filter if provided
            if search:
                search_pattern = f"%{search}%"
                query = query.filter(
                    (ChatHistory.question.ilike(search_pattern)) |
                    (ChatHistory.answer.ilike(search_pattern))
                )
            
            # Get total count
            total = query.count()
            
            # Calculate pagination
            total_pages = (total + page_size - 1) // page_size
            offset = (page - 1) * page_size
            
            # Get paginated results (most recent first)
            items = query.order_by(ChatHistory.created_at.desc()).offset(offset).limit(page_size).all()
            
            return ChatHistoryListResponse(
                items=items,
                total=total,
                page=page,
                page_size=page_size,
                total_pages=total_pages
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve chat history: {str(e)}")


@router.get("/{history_id}", response_model=ChatHistoryResponse)
def get_chat_history_by_id(history_id: int):
    """
    Get a specific chat history entry by ID.
    
    Args:
        history_id: Chat history entry ID
        
    Returns:
        ChatHistoryResponse: Single chat history entry
    """
    try:
        with get_db_session() as session:
            history = session.query(ChatHistory).filter(ChatHistory.id == history_id).first()
            
            if not history:
                raise HTTPException(status_code=404, detail="Chat history entry not found")
            
            return history
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve chat history: {str(e)}")
