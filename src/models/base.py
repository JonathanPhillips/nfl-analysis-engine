"""Base model classes and database configuration."""

from datetime import datetime
from typing import Optional
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
from pydantic import BaseModel as PydanticBaseModel, Field, ConfigDict
import os

# SQLAlchemy Base
Base = declarative_base()

# Database configuration
def get_database_url() -> str:
    """Get database URL from environment variables."""
    db_url = os.getenv('DATABASE_URL')
    if db_url:
        return db_url
    
    # Fallback to individual components
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME', 'nfl_analysis')
    db_user = os.getenv('DB_USER', 'nfl_user')
    db_password = os.getenv('DB_PASSWORD', 'nfl_password')
    
    return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

def create_database_engine():
    """Create database engine with proper configuration."""
    database_url = get_database_url()
    return create_engine(
        database_url,
        echo=False,  # Set to True for SQL debugging
        pool_size=20,
        max_overflow=0,
        pool_pre_ping=True
    )

def get_session_factory():
    """Get SQLAlchemy session factory."""
    engine = create_database_engine()
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)

class BaseModel(Base):
    """Base SQLAlchemy model with common fields."""
    __abstract__ = True
    
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

class BasePydanticModel(PydanticBaseModel):
    """Base Pydantic model for API serialization."""
    
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None
        }
    )