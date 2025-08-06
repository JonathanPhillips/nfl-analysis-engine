"""Main FastAPI application."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
import logging

from .routers import teams, players, games, plays, predictions, data, vegas
from . import insights
from ..web.routes import router as web_router
from .middleware import DatabaseMiddleware, LoggingMiddleware
from ..database.config import get_engine

logger = logging.getLogger(__name__)

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    app = FastAPI(
        title="NFL Analysis Engine",
        description="Professional-grade NFL data analysis and prediction API",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:8000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add custom middleware
    app.add_middleware(DatabaseMiddleware)
    app.add_middleware(LoggingMiddleware)
    
    # Include routers
    app.include_router(teams.router, prefix="/api/v1/teams", tags=["teams"])
    app.include_router(players.router, prefix="/api/v1/players", tags=["players"])
    app.include_router(games.router, prefix="/api/v1/games", tags=["games"])
    app.include_router(plays.router, prefix="/api/v1/plays", tags=["plays"])
    app.include_router(predictions.router, prefix="/api/v1/predictions", tags=["predictions"])
    app.include_router(vegas.router, prefix="/api/v1/vegas", tags=["vegas"])
    app.include_router(data.router, prefix="/api/v1/data", tags=["data"])
    app.include_router(insights.router, prefix="/api/v1", tags=["insights"])
    
    # Include web interface
    app.include_router(web_router, prefix="/web", include_in_schema=False)
    
    @app.get("/")
    async def root():
        """Redirect to web interface."""
        return RedirectResponse(url="/web/")
    
    @app.get("/api/v1/health")
    async def health_check():
        """Health check endpoint."""
        try:
            # Test database connection
            engine = get_engine()
            return {
                "status": "healthy",
                "service": "NFL Analysis Engine",
                "version": "1.0.0",
                "database": "connected"
            }
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            raise HTTPException(status_code=503, detail="Service unavailable")
    
    return app

# Create the app instance
app = create_app()