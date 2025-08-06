"""Tests for database migrations module."""

import pytest
import tempfile
import os
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine, text
from src.database.migrations import (
    MigrationManager, get_migration_manager, create_migration, 
    run_migrations, get_migration_status
)


class TestMigrationManager:
    """Test MigrationManager class."""
    
    @pytest.fixture
    def temp_migration_env(self):
        """Create temporary migration environment for testing."""
        # Create temporary directory structure
        temp_dir = tempfile.mkdtemp()
        temp_project = Path(temp_dir)
        
        # Create minimal alembic.ini
        alembic_ini = temp_project / "alembic.ini"
        alembic_ini.write_text("""
[alembic]
script_location = %(here)s/migrations
prepend_sys_path = .

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARNING
handlers = console
qualname =

[logger_sqlalchemy]
level = WARNING
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
""")
        
        # Create migrations directory
        migrations_dir = temp_project / "migrations"
        migrations_dir.mkdir()
        
        # Create versions directory
        versions_dir = migrations_dir / "versions"
        versions_dir.mkdir()
        
        # Create basic env.py
        env_py = migrations_dir / "env.py"
        env_py.write_text("""
from alembic import context
from sqlalchemy import engine_from_config, pool
from logging.config import fileConfig

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None

def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
""")
        
        # Create script.py.mako
        script_mako = migrations_dir / "script.py.mako"
        script_mako.write_text("""
\"\"\"${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

\"\"\"
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
""")
        
        # Create temporary database
        temp_db = temp_project / "test.db"
        engine = create_engine(f"sqlite:///{temp_db}")
        
        yield temp_project, engine
        
        # Cleanup
        engine.dispose()
        shutil.rmtree(temp_dir)
    
    def test_migration_manager_init(self, temp_migration_env):
        """Test MigrationManager initialization."""
        temp_project, engine = temp_migration_env
        
        # Mock the project root to point to our temp directory
        with patch('src.database.migrations.Path') as mock_path:
            mock_path.return_value.parent.parent.parent = temp_project
            
            manager = MigrationManager(engine)
            assert manager.engine == engine
            assert manager.alembic_cfg is not None
    
    def test_migration_manager_init_missing_config(self):
        """Test MigrationManager initialization with missing config."""
        temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        temp_db.close()
        
        try:
            engine = create_engine(f"sqlite:///{temp_db.name}")
            
            # Mock path to non-existent directory
            with patch('src.database.migrations.Path') as mock_path:
                mock_path.return_value.parent.parent.parent = Path("/nonexistent")
                
                with pytest.raises(FileNotFoundError):
                    MigrationManager(engine)
        finally:
            os.unlink(temp_db.name)
    
    def test_get_current_revision_no_migrations(self, temp_migration_env):
        """Test getting current revision when no migrations applied."""
        temp_project, engine = temp_migration_env
        
        with patch('src.database.migrations.Path') as mock_path:
            mock_path.return_value.parent.parent.parent = temp_project
            
            manager = MigrationManager(engine)
            current = manager.get_current_revision()
            assert current is None
    
    def test_get_migration_history_empty(self, temp_migration_env):
        """Test getting migration history when no migrations exist."""
        temp_project, engine = temp_migration_env
        
        with patch('src.database.migrations.Path') as mock_path:
            mock_path.return_value.parent.parent.parent = temp_project
            
            manager = MigrationManager(engine)
            history = manager.get_migration_history()
            assert history == []
    
    def test_get_pending_migrations_no_current(self, temp_migration_env):
        """Test getting pending migrations when no current revision."""
        temp_project, engine = temp_migration_env
        
        with patch('src.database.migrations.Path') as mock_path:
            mock_path.return_value.parent.parent.parent = temp_project
            
            manager = MigrationManager(engine)
            pending = manager.get_pending_migrations()
            # Should return empty list since no migrations exist
            assert pending == []
    
    def test_get_migration_status_clean_state(self, temp_migration_env):
        """Test getting migration status in clean state."""
        temp_project, engine = temp_migration_env
        
        with patch('src.database.migrations.Path') as mock_path:
            mock_path.return_value.parent.parent.parent = temp_project
            
            manager = MigrationManager(engine)
            status = manager.get_migration_status()
            
            assert status['current_revision'] is None
            assert status['pending_migrations'] == []
            assert status['pending_count'] == 0
            assert status['total_migrations'] == 0
            assert status['up_to_date'] is True
            assert status['migration_history'] == []
            assert status['head_revision'] is None
    
    @patch('src.database.migrations.command.stamp')
    def test_stamp_database(self, mock_stamp, temp_migration_env):
        """Test stamping database with revision."""
        temp_project, engine = temp_migration_env
        
        with patch('src.database.migrations.Path') as mock_path:
            mock_path.return_value.parent.parent.parent = temp_project
            
            manager = MigrationManager(engine)
            manager.stamp_database("abc123")
            
            mock_stamp.assert_called_once_with(manager.alembic_cfg, "abc123")
    
    @patch('src.database.migrations.command.stamp')
    def test_stamp_database_default_head(self, mock_stamp, temp_migration_env):
        """Test stamping database with default head revision."""
        temp_project, engine = temp_migration_env
        
        with patch('src.database.migrations.Path') as mock_path:
            mock_path.return_value.parent.parent.parent = temp_project
            
            manager = MigrationManager(engine)
            manager.stamp_database()
            
            mock_stamp.assert_called_once_with(manager.alembic_cfg, "head")


class TestMigrationManagerConvenienceFunctions:
    """Test convenience functions for migration management."""
    
    @patch('src.database.migrations.MigrationManager')
    def test_get_migration_manager_singleton(self, mock_manager_class):
        """Test singleton behavior of get_migration_manager."""
        mock_instance = MagicMock()
        mock_manager_class.return_value = mock_instance
        
        # First call should create instance
        manager1 = get_migration_manager()
        assert manager1 == mock_instance
        mock_manager_class.assert_called_once()
        
        # Second call should return same instance
        manager2 = get_migration_manager()
        assert manager2 == mock_instance
        # Should not create new instance
        assert mock_manager_class.call_count == 1
    
    @patch('src.database.migrations.MigrationManager')
    def test_get_migration_manager_with_engine_override(self, mock_manager_class):
        """Test get_migration_manager with engine override."""
        mock_instance = MagicMock()
        mock_manager_class.return_value = mock_instance
        
        engine = MagicMock()
        manager = get_migration_manager(engine)
        
        mock_manager_class.assert_called_once_with(engine)
        assert manager == mock_instance
    
    @patch('src.database.migrations.get_migration_manager')
    def test_create_migration_convenience(self, mock_get_manager):
        """Test create_migration convenience function."""
        mock_manager = MagicMock()
        mock_get_manager.return_value = mock_manager
        mock_manager.create_migration.return_value = "abc123"
        
        result = create_migration("test migration", autogenerate=False)
        
        mock_get_manager.assert_called_once_with(None)
        mock_manager.create_migration.assert_called_once_with("test migration", False)
        assert result == "abc123"
    
    @patch('src.database.migrations.get_migration_manager')
    def test_run_migrations_convenience(self, mock_get_manager):
        """Test run_migrations convenience function."""
        mock_manager = MagicMock()
        mock_get_manager.return_value = mock_manager
        
        run_migrations("target_rev")
        
        mock_get_manager.assert_called_once_with(None)
        mock_manager.run_migrations.assert_called_once_with("target_rev")
    
    @patch('src.database.migrations.get_migration_manager')
    def test_get_migration_status_convenience(self, mock_get_manager):
        """Test get_migration_status convenience function."""
        mock_manager = MagicMock()
        mock_get_manager.return_value = mock_manager
        mock_manager.get_migration_status.return_value = {"status": "ok"}
        
        result = get_migration_status()
        
        mock_get_manager.assert_called_once_with(None)
        mock_manager.get_migration_status.assert_called_once()
        assert result == {"status": "ok"}


class TestMigrationManagerErrorHandling:
    """Test error handling in MigrationManager."""
    
    def test_get_current_revision_error(self):
        """Test error handling in get_current_revision."""
        # Create engine that will fail (use SQLite to avoid psycopg2 dependency)
        engine = create_engine("sqlite:///nonexistent_directory/invalid.db")
        
        temp_dir = tempfile.mkdtemp()
        try:
            temp_project = Path(temp_dir)
            alembic_ini = temp_project / "alembic.ini"
            alembic_ini.write_text("[alembic]\nscript_location = migrations\n")
            
            with patch('src.database.migrations.Path') as mock_path:
                mock_path.return_value.parent.parent.parent = temp_project
                
                manager = MigrationManager(engine)
                result = manager.get_current_revision()
                assert result is None
        finally:
            shutil.rmtree(temp_dir)
    
    def test_get_migration_history_error(self):
        """Test error handling in get_migration_history."""
        engine = create_engine("sqlite:///:memory:")
        
        temp_dir = tempfile.mkdtemp()
        try:
            temp_project = Path(temp_dir)
            alembic_ini = temp_project / "alembic.ini"
            alembic_ini.write_text("[alembic]\nscript_location = nonexistent\n")
            
            with patch('src.database.migrations.Path') as mock_path:
                mock_path.return_value.parent.parent.parent = temp_project
                
                manager = MigrationManager(engine)
                result = manager.get_migration_history()
                assert result == []
        finally:
            shutil.rmtree(temp_dir)
    
    def test_get_migration_status_error(self):
        """Test error handling in get_migration_status."""
        engine = create_engine("sqlite:///nonexistent_directory/invalid.db")
        
        temp_dir = tempfile.mkdtemp()
        try:
            temp_project = Path(temp_dir)
            alembic_ini = temp_project / "alembic.ini"
            alembic_ini.write_text("[alembic]\nscript_location = nonexistent\n")
            
            with patch('src.database.migrations.Path') as mock_path:
                mock_path.return_value.parent.parent.parent = temp_project
                
                manager = MigrationManager(engine)
                
                # Mock get_current_revision to raise an exception to trigger top-level error handling
                with patch.object(manager, 'get_current_revision', side_effect=Exception("Test error")):
                    status = manager.get_migration_status()
                    
                    assert 'error' in status
                    assert status['current_revision'] is None
                    assert status['up_to_date'] is False
        finally:
            shutil.rmtree(temp_dir)