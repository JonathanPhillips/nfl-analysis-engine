"""Database configuration and connection management."""

import os
from typing import Optional
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from src.models.base import get_database_url as get_url_from_models


def get_database_url(database_url: Optional[str] = None) -> str:
    """Get database URL for the application.
    
    Args:
        database_url: Optional database URL override
        
    Returns:
        Database URL string
    """
    if database_url:
        return database_url
    
    # Use the configuration from models.base
    return get_url_from_models()


def get_engine(database_url: Optional[str] = None, **kwargs) -> Engine:
    """Create SQLAlchemy engine with proper configuration.
    
    Args:
        database_url: Optional database URL override
        **kwargs: Additional engine parameters
        
    Returns:
        SQLAlchemy Engine instance
    """
    url = get_database_url(database_url)
    
    # Default engine configuration
    engine_kwargs = {
        'echo': os.getenv('DATABASE_ECHO', 'false').lower() == 'true',
        'pool_pre_ping': True,
    }
    
    # Special configuration for SQLite (testing)
    if url.startswith('sqlite'):
        engine_kwargs.update({
            'poolclass': StaticPool,
            'connect_args': {
                'check_same_thread': False,
                'timeout': 20
            }
        })
    
    # Override with provided kwargs
    engine_kwargs.update(kwargs)
    
    return create_engine(url, **engine_kwargs)


def get_session(engine: Optional[Engine] = None) -> sessionmaker[Session]:
    """Create SQLAlchemy session factory.
    
    Args:
        engine: Optional engine instance
        
    Returns:
        Session factory
    """
    if engine is None:
        engine = get_engine()
    
    return sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False
    )


# Global session factory for application use
# Only create global session if not in test environment
SessionLocal = None


def get_db_session() -> Session:
    """Get database session for dependency injection.
    
    Yields:
        Database session
    """
    global SessionLocal
    if SessionLocal is None:
        SessionLocal = get_session()
    
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()