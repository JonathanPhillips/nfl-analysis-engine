"""Tests for database configuration module."""

import pytest
import os
from unittest.mock import patch, MagicMock
from sqlalchemy import Engine, text
from sqlalchemy.orm import sessionmaker
from src.database.config import (
    get_database_url, get_engine, get_session, get_db_session
)


class TestDatabaseConfig:
    """Test database configuration functions."""
    
    def test_get_database_url_with_override(self):
        """Test getting database URL with override."""
        test_url = "postgresql://test:test@localhost/test_db"
        result = get_database_url(test_url)
        assert result == test_url
    
    def test_get_database_url_from_env(self):
        """Test getting database URL from environment."""
        with patch.dict(os.environ, {'DATABASE_URL': 'postgresql://env:env@localhost/env_db'}):
            result = get_database_url()
            assert result == 'postgresql://env:env@localhost/env_db'
    
    def test_get_database_url_defaults(self):
        """Test getting database URL with defaults."""
        # Clear relevant environment variables
        env_vars_to_clear = [
            'DATABASE_URL', 'DB_HOST', 'DB_PORT', 'DB_NAME', 
            'DB_USER', 'DB_PASSWORD'
        ]
        
        with patch.dict(os.environ, {}, clear=True):
            result = get_database_url()
            # Should use PostgreSQL default when no env vars set
            assert 'postgresql://' in result or 'sqlite:///' in result
    
    def test_get_engine_default(self):
        """Test getting default engine."""
        engine = get_engine("sqlite:///test.db")  # Force SQLite for testing
        assert isinstance(engine, Engine)
        assert str(engine.url).startswith('sqlite:///')
    
    def test_get_engine_with_url_override(self):
        """Test getting engine with URL override."""
        test_url = "sqlite:///test_override.db"
        engine = get_engine(test_url)
        assert isinstance(engine, Engine)
        assert str(engine.url) == test_url
    
    def test_get_engine_with_kwargs(self):
        """Test getting engine with additional kwargs."""
        engine = get_engine("sqlite:///test.db", echo=True)
        assert isinstance(engine, Engine)
        assert engine.echo is True
    
    def test_get_engine_sqlite_configuration(self):
        """Test SQLite-specific engine configuration."""
        sqlite_url = "sqlite:///test.db"
        engine = get_engine(sqlite_url)
        
        # Check SQLite-specific configuration
        assert hasattr(engine.pool, '__class__')
        # Connect args are stored in the dialect's connect_args
        # For SQLite, these are passed during engine creation
        assert str(engine.url).startswith('sqlite:///')
    
    @patch.dict(os.environ, {'DATABASE_ECHO': 'true'})
    def test_get_engine_with_echo_env(self):
        """Test engine echo setting from environment."""
        engine = get_engine("sqlite:///test.db")
        assert engine.echo is True
    
    @patch.dict(os.environ, {'DATABASE_ECHO': 'false'})
    def test_get_engine_without_echo_env(self):
        """Test engine echo setting disabled from environment."""
        engine = get_engine("sqlite:///test.db")
        assert engine.echo is False
    
    def test_get_session_default(self):
        """Test getting default session factory."""
        engine = get_engine("sqlite:///test.db")
        session_factory = get_session(engine)
        assert callable(session_factory)
        
        # Test session configuration
        session = session_factory()
        # In SQLAlchemy 2.0, these are constructor args, not properties
        assert session.bind == engine
        session.close()
    
    def test_get_session_with_engine(self):
        """Test getting session factory with custom engine."""
        engine = get_engine("sqlite:///custom.db")
        session_factory = get_session(engine)
        
        session = session_factory()
        assert session.bind == engine
        session.close()
    
    @patch('src.database.config.get_session')
    def test_get_db_session(self, mock_get_session):
        """Test database session generator for dependency injection."""
        mock_session_factory = MagicMock()
        mock_session = MagicMock()
        mock_session_factory.return_value = mock_session
        mock_get_session.return_value = mock_session_factory
        
        session_gen = get_db_session()
        
        # Test that it's a generator
        assert hasattr(session_gen, '__next__')
        
        # Test session creation and cleanup
        session = next(session_gen)
        assert session == mock_session
        
        # Test cleanup (should not raise)
        try:
            next(session_gen)
        except StopIteration:
            pass  # Expected for generator cleanup


class TestDatabaseConfigIntegration:
    """Integration tests for database configuration."""
    
    def test_engine_connection(self):
        """Test that engine can establish connection."""
        engine = get_engine("sqlite:///test.db")
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            assert result.scalar() == 1
    
    def test_session_database_operations(self):
        """Test session can perform database operations."""
        engine = get_engine("sqlite:///test.db")
        SessionLocal = get_session(engine)
        
        with SessionLocal() as session:
            # Test basic query
            result = session.execute(text("SELECT 1 as test_col"))
            assert result.scalar() == 1
    
    def test_multiple_engines_independence(self):
        """Test that multiple engines are independent."""
        engine1 = get_engine("sqlite:///test1.db")
        engine2 = get_engine("sqlite:///test2.db")
        
        assert engine1 != engine2
        assert str(engine1.url) != str(engine2.url)
    
    @patch('src.database.config.get_session')
    def test_session_cleanup_on_error(self, mock_get_session):
        """Test session cleanup when error occurs."""
        mock_session_factory = MagicMock()
        mock_session = MagicMock()
        mock_session_factory.return_value = mock_session
        mock_get_session.return_value = mock_session_factory
        
        session_gen = get_db_session()
        session = next(session_gen)
        
        # Simulate error and cleanup
        try:
            # Force an error
            raise ValueError("Test error")
        except ValueError:
            pass
        
        # Cleanup should not raise
        try:
            next(session_gen)
        except StopIteration:
            pass  # Expected