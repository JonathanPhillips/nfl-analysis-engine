"""Custom middleware for the FastAPI application."""

import time
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import sessionmaker

from ..database.config import get_engine

logger = logging.getLogger(__name__)


class DatabaseMiddleware(BaseHTTPMiddleware):
    """Middleware to manage database sessions."""
    
    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        self.engine = None
        self.session_maker = None
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with database session management."""
        # Initialize database connection if not already done
        if not self.engine:
            try:
                self.engine = get_engine()
                self.session_maker = sessionmaker(bind=self.engine)
                logger.info("Database connection initialized")
            except Exception as e:
                logger.error(f"Failed to initialize database: {str(e)}")
                # Continue without database for non-database endpoints
        
        # Add database session to request state
        if self.session_maker:
            request.state.db_session = self.session_maker()
        
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            logger.error(f"Request failed: {str(e)}")
            raise
        finally:
            # Clean up database session
            if hasattr(request.state, 'db_session'):
                request.state.db_session.close()


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request/response logging."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log request and response details."""
        start_time = time.time()
        
        # Log request
        logger.info(
            f"Request: {request.method} {request.url.path} "
            f"from {request.client.host if request.client else 'unknown'}"
        )
        
        # Process request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Log response
        logger.info(
            f"Response: {response.status_code} for {request.method} {request.url.path} "
            f"({process_time:.3f}s)"
        )
        
        # Add processing time to response headers
        response.headers["X-Process-Time"] = str(process_time)
        
        return response