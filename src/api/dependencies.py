"""FastAPI dependencies for dependency injection."""

from typing import Generator
from fastapi import Request, HTTPException
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)


def get_db_session(request: Request) -> Generator[Session, None, None]:
    """Get database session from request state."""
    if not hasattr(request.state, 'db_session'):
        raise HTTPException(
            status_code=503, 
            detail="Database connection not available"
        )
    
    try:
        yield request.state.db_session
    except Exception as e:
        logger.error(f"Database session error: {str(e)}")
        request.state.db_session.rollback()
        raise HTTPException(status_code=500, detail="Database error")