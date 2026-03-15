"""
API routes for application settings management.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime

from src.models.database import AppSettings, get_db_session
from src.config.settings import clear_settings_cache

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingsResponse(BaseModel):
    """Response model for settings."""
    id: int
    llm_provider: str
    llm_model: str
    llm_temperature: float
    retriever_k: int
    pdf_language: str
    pdf_strategy: str
    chunk_max_characters: int
    chunk_new_after_n_chars: int
    chunk_overlap: int
    rag_prompt_template: str
    updated_at: datetime

    class Config:
        from_attributes = True


class SettingsUpdate(BaseModel):
    """Request model for updating settings."""
    llm_provider: str = Field(..., pattern="^(groq|deepseek|openrouter|ollama)$")
    llm_model: str = Field(..., min_length=1, max_length=100)
    llm_temperature: float = Field(..., ge=0.0, le=1.0)
    retriever_k: int = Field(..., ge=1, le=20)
    pdf_language: str = Field(..., min_length=1, max_length=10)
    pdf_strategy: str = Field(..., pattern="^(auto|fast|hi_res|ocr_only)$")
    chunk_max_characters: int = Field(..., ge=100, le=5000)
    chunk_new_after_n_chars: int = Field(..., ge=100, le=5000)
    chunk_overlap: int = Field(..., ge=0, le=1000)
    rag_prompt_template: str = Field(..., min_length=10)


@router.get("", response_model=SettingsResponse)
def get_settings():
    """
    Get current application settings.
    
    Returns:
        SettingsResponse: Current settings from database
    """
    try:
        with get_db_session() as session:
            settings = session.query(AppSettings).filter(AppSettings.id == 1).first()
            
            if not settings:
                raise HTTPException(
                    status_code=404,
                    detail="Settings not found. Database may not be initialized."
                )
            
            # Convert to dict while session is still active
            return SettingsResponse(
                id=settings.id,
                llm_provider=settings.llm_provider,
                llm_model=settings.llm_model,
                llm_temperature=settings.llm_temperature,
                retriever_k=settings.retriever_k,
                pdf_language=settings.pdf_language,
                pdf_strategy=settings.pdf_strategy,
                chunk_max_characters=settings.chunk_max_characters,
                chunk_new_after_n_chars=settings.chunk_new_after_n_chars,
                chunk_overlap=settings.chunk_overlap,
                rag_prompt_template=settings.rag_prompt_template,
                updated_at=settings.updated_at
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve settings: {str(e)}")


@router.put("", response_model=SettingsResponse)
def update_settings(settings_update: SettingsUpdate):
    """
    Update application settings.
    
    Args:
        settings_update: New settings values
        
    Returns:
        SettingsResponse: Updated settings
    """
    try:
        with get_db_session() as session:
            settings = session.query(AppSettings).filter(AppSettings.id == 1).first()
            
            if not settings:
                raise HTTPException(
                    status_code=404,
                    detail="Settings not found. Database may not be initialized."
                )
            
            # Update all fields
            settings.llm_provider = settings_update.llm_provider
            settings.llm_model = settings_update.llm_model
            settings.llm_temperature = settings_update.llm_temperature
            settings.retriever_k = settings_update.retriever_k
            settings.pdf_language = settings_update.pdf_language
            settings.pdf_strategy = settings_update.pdf_strategy
            settings.chunk_max_characters = settings_update.chunk_max_characters
            settings.chunk_new_after_n_chars = settings_update.chunk_new_after_n_chars
            settings.chunk_overlap = settings_update.chunk_overlap
            settings.rag_prompt_template = settings_update.rag_prompt_template
            settings.updated_at = datetime.utcnow()
            
            session.commit()
            session.refresh(settings)
            
            # Clear the settings cache so next request gets fresh values
            clear_settings_cache()
            
            # Convert to dict while session is still active
            return SettingsResponse(
                id=settings.id,
                llm_provider=settings.llm_provider,
                llm_model=settings.llm_model,
                llm_temperature=settings.llm_temperature,
                retriever_k=settings.retriever_k,
                pdf_language=settings.pdf_language,
                pdf_strategy=settings.pdf_strategy,
                chunk_max_characters=settings.chunk_max_characters,
                chunk_new_after_n_chars=settings.chunk_new_after_n_chars,
                chunk_overlap=settings.chunk_overlap,
                rag_prompt_template=settings.rag_prompt_template,
                updated_at=settings.updated_at
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update settings: {str(e)}")
