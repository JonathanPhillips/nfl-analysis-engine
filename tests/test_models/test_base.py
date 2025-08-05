"""Tests for base model functionality."""

import pytest
import os
from datetime import datetime
from unittest.mock import patch
from src.models.base import get_database_url, BaseModel, BasePydanticModel


class TestDatabaseConfiguration:
    """Test database configuration functionality."""
    
    def test_get_database_url_from_database_url_env(self):
        """Test database URL creation from DATABASE_URL environment variable."""
        test_url = "postgresql://test:pass@testhost:5432/testdb"
        
        with patch.dict(os.environ, {'DATABASE_URL': test_url}):
            result = get_database_url()
            assert result == test_url
    
    def test_get_database_url_from_individual_components(self):
        """Test database URL creation from individual environment variables."""
        env_vars = {
            'DB_HOST': 'myhost',
            'DB_PORT': '5433',
            'DB_NAME': 'mydb',
            'DB_USER': 'myuser',
            'DB_PASSWORD': 'mypass'
        }
        
        # Clear DATABASE_URL to force individual component usage
        with patch.dict(os.environ, env_vars, clear=True):
            result = get_database_url()
            expected = "postgresql://myuser:mypass@myhost:5433/mydb"
            assert result == expected
    
    def test_get_database_url_with_defaults(self):
        """Test database URL creation with default values."""
        # Clear all database-related env vars
        with patch.dict(os.environ, {}, clear=True):
            result = get_database_url()
            expected = "postgresql://nfl_user:nfl_password@localhost:5432/nfl_analysis"
            assert result == expected


class TestBaseModel:
    """Test base SQLAlchemy model functionality."""
    
    def test_base_model_has_required_fields(self):
        """Test that BaseModel has all required common fields."""
        # For abstract base, check the defined columns directly
        assert hasattr(BaseModel, 'id')
        assert hasattr(BaseModel, 'created_at')
        assert hasattr(BaseModel, 'updated_at')
        assert hasattr(BaseModel, 'is_active')
        
        # Verify these are SQLAlchemy Column objects by checking their types
        from sqlalchemy import Column
        assert isinstance(BaseModel.id, Column)
        assert isinstance(BaseModel.created_at, Column) 
        assert isinstance(BaseModel.updated_at, Column)
        assert isinstance(BaseModel.is_active, Column)
    
    def test_base_model_is_abstract(self):
        """Test that BaseModel is properly marked as abstract."""
        assert BaseModel.__abstract__ is True


class TestBasePydanticModel:
    """Test base Pydantic model functionality."""
    
    def test_base_pydantic_model_config(self):
        """Test BasePydanticModel configuration."""
        config = BasePydanticModel.model_config
        
        assert config['from_attributes'] is True
        assert datetime in config['json_encoders']
    
    def test_datetime_json_encoder(self):
        """Test datetime JSON encoder functionality."""
        config = BasePydanticModel.model_config
        encoder = config['json_encoders'][datetime]
        
        # Test with valid datetime
        test_datetime = datetime(2024, 1, 15, 12, 30, 45)
        result = encoder(test_datetime)
        assert result == "2024-01-15T12:30:45"
        
        # Test with None
        result = encoder(None)
        assert result is None