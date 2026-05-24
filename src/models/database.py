"""
SQLAlchemy models for application database tables.
"""
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, Text, TIMESTAMP, CheckConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.dialects.postgresql import JSONB
from contextlib import contextmanager

from src.config import normalize_database_url

# Create SQLAlchemy engine
engine = create_engine(normalize_database_url())
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


class AppSettings(Base):
    """
    Application settings table (singleton pattern).
    Stores configurable RAG parameters.
    """
    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True, default=1)
    llm_provider = Column(String(50), nullable=False, default="openrouter")
    llm_model = Column(String(100), nullable=False, default="openai/gpt-oss-120b:exacto")
    llm_temperature = Column(Float, nullable=False, default=0.3)
    retriever_k = Column(Integer, nullable=False, default=8)
    pdf_language = Column(String(10), nullable=False, default="hun")
    pdf_strategy = Column(String(20), nullable=False, default="auto")
    chunk_max_characters = Column(Integer, nullable=False, default=1000)
    chunk_new_after_n_chars = Column(Integer, nullable=False, default=800)
    chunk_overlap = Column(Integer, nullable=False, default=200)
    rag_prompt_template = Column(Text, nullable=False)
    updated_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        CheckConstraint('llm_temperature >= 0 AND llm_temperature <= 1', name='check_temperature_range'),
        CheckConstraint('retriever_k >= 1 AND retriever_k <= 20', name='check_retriever_k_range'),
        CheckConstraint('id = 1', name='single_row_constraint'),
    )


class ChatHistory(Base):
    """
    Chat history table.
    Logs all question-answer interactions.
    """
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    model_used = Column(String(100), nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    source = Column(String(50), nullable=False, default='api')
    message_metadata = Column(JSONB, nullable=True)
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)


@contextmanager
def get_db_session() -> Session:
    """
    Context manager for database sessions.
    Ensures proper session cleanup.
    
    Usage:
        with get_db_session() as session:
            settings = session.query(AppSettings).first()
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
