"""Tests for database manager module."""

import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from src.database.manager import DatabaseManager
from src.database.config import get_engine
from src.models.base import Base


class TestDatabaseManager:
    """Test DatabaseManager class."""
    
    @pytest.fixture
    def temp_db_manager(self):
        """Create temporary database manager for testing."""
        # Create temporary SQLite database
        temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        temp_db.close()
        
        engine = create_engine(f"sqlite:///{temp_db.name}")
        manager = DatabaseManager(engine)
        
        yield manager
        
        # Cleanup
        manager.engine.dispose()
        os.unlink(temp_db.name)
    
    @patch('src.database.manager.get_engine')
    def test_database_manager_init_default(self, mock_get_engine):
        """Test DatabaseManager initialization with default engine."""
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine
        
        manager = DatabaseManager()
        assert manager.engine == mock_engine
        assert manager.SessionLocal is not None
    
    def test_database_manager_init_custom_engine(self, temp_db_manager):
        """Test DatabaseManager initialization with custom engine."""
        assert temp_db_manager.engine is not None
        assert temp_db_manager.SessionLocal is not None
    
    def test_create_all_tables(self, temp_db_manager):
        """Test creating all tables."""
        temp_db_manager.create_all_tables()
        
        # Verify tables were created
        table_names = temp_db_manager.get_table_names()
        expected_tables = {'teams', 'players', 'games', 'plays'}
        assert expected_tables.issubset(set(table_names))
    
    def test_drop_all_tables(self, temp_db_manager):
        """Test dropping all tables."""
        # First create tables
        temp_db_manager.create_all_tables()
        assert len(temp_db_manager.get_table_names()) > 0
        
        # Then drop them
        temp_db_manager.drop_all_tables()
        table_names = temp_db_manager.get_table_names()
        
        # Should have no application tables (might have alembic tables)
        expected_tables = {'teams', 'players', 'games', 'plays'}
        assert not expected_tables.intersection(set(table_names))
    
    def test_recreate_all_tables(self, temp_db_manager):
        """Test recreating all tables."""
        # Create tables first
        temp_db_manager.create_all_tables()
        original_tables = set(temp_db_manager.get_table_names())
        
        # Recreate tables
        temp_db_manager.recreate_all_tables()
        new_tables = set(temp_db_manager.get_table_names())
        
        # Should have same tables
        expected_tables = {'teams', 'players', 'games', 'plays'}
        assert expected_tables.issubset(new_tables)
    
    def test_get_table_names(self, temp_db_manager):
        """Test getting table names."""
        # Initially should be empty or minimal
        initial_tables = temp_db_manager.get_table_names()
        
        # Create tables
        temp_db_manager.create_all_tables()
        table_names = temp_db_manager.get_table_names()
        
        assert len(table_names) > len(initial_tables)
        expected_tables = {'teams', 'players', 'games', 'plays'}
        assert expected_tables.issubset(set(table_names))
    
    def test_table_exists(self, temp_db_manager):
        """Test checking if table exists."""
        # Initially tables should not exist
        assert not temp_db_manager.table_exists('teams')
        assert not temp_db_manager.table_exists('nonexistent_table')
        
        # Create tables
        temp_db_manager.create_all_tables()
        
        # Now tables should exist
        assert temp_db_manager.table_exists('teams')
        assert temp_db_manager.table_exists('players')
        assert not temp_db_manager.table_exists('nonexistent_table')
    
    def test_get_table_info(self, temp_db_manager):
        """Test getting table information."""
        temp_db_manager.create_all_tables()
        
        # Test getting info for existing table
        table_info = temp_db_manager.get_table_info('teams')
        
        assert table_info['name'] == 'teams'
        assert 'columns' in table_info
        assert 'indexes' in table_info
        assert 'foreign_keys' in table_info
        assert 'primary_key' in table_info
        
        # Check that we have expected columns
        column_names = [col['name'] for col in table_info['columns']]
        expected_columns = {'id', 'team_abbr', 'team_name', 'team_nick'}
        assert expected_columns.issubset(set(column_names))
    
    def test_get_table_info_nonexistent(self, temp_db_manager):
        """Test getting info for nonexistent table."""
        with pytest.raises(ValueError, match="Table 'nonexistent' does not exist"):
            temp_db_manager.get_table_info('nonexistent')
    
    def test_validate_schema_empty_db(self, temp_db_manager):
        """Test schema validation on empty database."""
        validation = temp_db_manager.validate_schema()
        
        assert validation['valid'] is False
        assert len(validation['missing_tables']) > 0
        expected_missing = {'teams', 'players', 'games', 'plays'}
        assert expected_missing.issubset(set(validation['missing_tables']))
        assert validation['extra_tables'] == []
    
    def test_validate_schema_complete_db(self, temp_db_manager):
        """Test schema validation on complete database."""
        temp_db_manager.create_all_tables()
        validation = temp_db_manager.validate_schema()
        
        assert validation['valid'] is True
        assert validation['missing_tables'] == []
        # Might have extra tables like alembic_version
        expected_model_tables = {'teams', 'players', 'games', 'plays'}
        assert expected_model_tables.issubset(set(validation['model_tables']))
    
    def test_validate_schema_with_extra_tables(self, temp_db_manager):
        """Test schema validation with extra tables."""
        temp_db_manager.create_all_tables()
        
        # Add an extra table
        with temp_db_manager.engine.connect() as conn:
            conn.execute(text("CREATE TABLE extra_table (id INTEGER)"))
            conn.commit()
        
        validation = temp_db_manager.validate_schema()
        
        assert validation['valid'] is False
        assert 'extra_table' in validation['extra_tables']
        assert validation['missing_tables'] == []
    
    def test_test_connection_success(self, temp_db_manager):
        """Test successful connection test."""
        result = temp_db_manager.test_connection()
        
        assert result['connected'] is True
        assert result['readable'] is True
        assert result['writable'] is True
        assert result['error'] is None
    
    def test_test_connection_failure(self):
        """Test connection test failure."""
        # Create manager with invalid database URL
        bad_engine = create_engine("postgresql://invalid:invalid@nonexistent:5432/invalid")
        manager = DatabaseManager(bad_engine)
        
        result = manager.test_connection()
        
        assert result['connected'] is False
        assert result['readable'] is False
        assert result['writable'] is False
        assert result['error'] is not None
    
    def test_get_database_info(self, temp_db_manager):
        """Test getting database information."""
        info = temp_db_manager.get_database_info()
        
        assert 'url' in info
        assert 'dialect' in info
        assert 'driver' in info
        assert 'connection_test' in info
        assert 'schema_validation' in info
        
        # URL should be masked
        assert '***' in info['url'] or 'sqlite' in info['url']
        
        # Should have SQLite info
        assert info['dialect'] == 'sqlite'
        assert 'server_version' in info
    
    def test_execute_sql(self, temp_db_manager):
        """Test executing raw SQL."""
        # Test simple query
        result = temp_db_manager.execute_sql("SELECT 1 as test_col")
        assert result.scalar() == 1
        
        # Test query with parameters
        result = temp_db_manager.execute_sql(
            "SELECT :value as param_col", 
            {'value': 42}
        )
        assert result.scalar() == 42
    
    def test_get_session(self, temp_db_manager):
        """Test getting database session."""
        session = temp_db_manager.get_session()
        assert session is not None
        
        # Test session works
        result = session.execute(text("SELECT 1"))
        assert result.scalar() == 1
        
        session.close()


class TestDatabaseManagerIntegration:
    """Integration tests for DatabaseManager."""
    
    def test_full_database_lifecycle(self):
        """Test complete database lifecycle."""
        # Create temporary database
        temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        temp_db.close()
        
        try:
            engine = create_engine(f"sqlite:///{temp_db.name}")
            manager = DatabaseManager(engine)
            
            # 1. Initial state - no tables
            assert len(manager.get_table_names()) == 0
            validation = manager.validate_schema()
            assert not validation['valid']
            
            # 2. Create tables
            manager.create_all_tables()
            validation = manager.validate_schema()
            assert validation['valid']
            
            # 3. Test connection
            connection_test = manager.test_connection()
            assert connection_test['connected']
            assert connection_test['readable']
            assert connection_test['writable']
            
            # 4. Get database info
            info = manager.get_database_info()
            assert info['dialect'] == 'sqlite'
            assert info['connection_test']['connected']
            assert info['schema_validation']['valid']
            
            # 5. Drop tables
            manager.drop_all_tables()
            validation = manager.validate_schema()
            assert not validation['valid']
            
        finally:
            # Cleanup
            engine.dispose()
            os.unlink(temp_db.name)
    
    def test_manager_with_models_integration(self):
        """Test manager integration with actual models."""
        temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        temp_db.close()
        
        try:
            engine = create_engine(f"sqlite:///{temp_db.name}")
            manager = DatabaseManager(engine)
            
            # Create tables
            manager.create_all_tables()
            
            # Verify all model tables exist
            table_names = set(manager.get_table_names())
            expected_tables = {'teams', 'players', 'games', 'plays'}
            assert expected_tables.issubset(table_names)
            
            # Test table info for each model
            for table_name in expected_tables:
                info = manager.get_table_info(table_name)
                assert info['name'] == table_name
                assert len(info['columns']) > 0
                
                # Check for common fields
                column_names = [col['name'] for col in info['columns']]
                assert 'id' in column_names
                assert 'created_at' in column_names
                assert 'updated_at' in column_names
                
        finally:
            engine.dispose()
            os.unlink(temp_db.name)