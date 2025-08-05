"""Database migration utilities and management."""

import os
import subprocess
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Engine
from .config import get_engine

logger = logging.getLogger(__name__)


class MigrationManager:
    """Manages database migrations using Alembic."""
    
    def __init__(self, engine: Optional[Engine] = None):
        """Initialize migration manager.
        
        Args:
            engine: Optional SQLAlchemy engine
        """
        self.engine = engine or get_engine()
        self.project_root = Path(__file__).parent.parent.parent
        self.alembic_cfg_path = self.project_root / "alembic.ini"
        
        if not self.alembic_cfg_path.exists():
            raise FileNotFoundError(f"Alembic configuration not found: {self.alembic_cfg_path}")
        
        self.alembic_cfg = Config(str(self.alembic_cfg_path))
    
    def create_migration(self, message: str, autogenerate: bool = True) -> str:
        """Create a new migration.
        
        Args:
            message: Migration message/description
            autogenerate: Whether to auto-generate migration from model changes
            
        Returns:
            Migration revision ID
        """
        try:
            logger.info(f"Creating migration: {message}")
            
            # Create revision
            if autogenerate:
                revision = command.revision(
                    self.alembic_cfg, 
                    message=message, 
                    autogenerate=True
                )
            else:
                revision = command.revision(
                    self.alembic_cfg, 
                    message=message
                )
            
            revision_id = revision.revision
            logger.info(f"Created migration {revision_id}: {message}")
            return revision_id
            
        except Exception as e:
            logger.error(f"Failed to create migration: {e}")
            raise
    
    def run_migrations(self, target_revision: str = "head") -> None:
        """Run migrations up to target revision.
        
        Args:
            target_revision: Target revision (default: "head" for latest)
        """
        try:
            logger.info(f"Running migrations to {target_revision}")
            command.upgrade(self.alembic_cfg, target_revision)
            logger.info(f"Successfully upgraded to {target_revision}")
        except Exception as e:
            logger.error(f"Failed to run migrations: {e}")
            raise
    
    def downgrade_migrations(self, target_revision: str) -> None:
        """Downgrade migrations to target revision.
        
        Args:
            target_revision: Target revision to downgrade to
        """
        try:
            logger.info(f"Downgrading migrations to {target_revision}")
            command.downgrade(self.alembic_cfg, target_revision)
            logger.info(f"Successfully downgraded to {target_revision}")
        except Exception as e:
            logger.error(f"Failed to downgrade migrations: {e}")
            raise
    
    def get_current_revision(self) -> Optional[str]:
        """Get current database revision.
        
        Returns:
            Current revision ID or None if no migrations applied
        """
        try:
            with self.engine.connect() as connection:
                context = MigrationContext.configure(connection)
                return context.get_current_revision()
        except Exception as e:
            logger.error(f"Failed to get current revision: {e}")
            return None
    
    def get_migration_history(self) -> List[Dict[str, Any]]:
        """Get migration history.
        
        Returns:
            List of migration information
        """
        try:
            script_dir = ScriptDirectory.from_config(self.alembic_cfg)
            revisions = []
            
            for revision in script_dir.walk_revisions():
                revisions.append({
                    'revision': revision.revision,
                    'down_revision': revision.down_revision,
                    'branch_labels': revision.branch_labels,
                    'depends_on': revision.depends_on,
                    'doc': revision.doc,
                    'module_path': revision.module_path
                })
            
            return revisions
        except Exception as e:
            logger.error(f"Failed to get migration history: {e}")
            return []
    
    def get_pending_migrations(self) -> List[str]:
        """Get list of pending migrations.
        
        Returns:
            List of pending migration revision IDs
        """
        try:
            current = self.get_current_revision()
            script_dir = ScriptDirectory.from_config(self.alembic_cfg)
            
            if current is None:
                # No migrations applied yet, all are pending
                return [rev.revision for rev in script_dir.walk_revisions()]
            
            # Get revisions from current to head
            pending = []
            for revision in script_dir.walk_revisions("head", current):
                if revision.revision != current:
                    pending.append(revision.revision)
            
            return pending
        except Exception as e:
            logger.error(f"Failed to get pending migrations: {e}")
            return []
    
    def get_migration_status(self) -> Dict[str, Any]:
        """Get comprehensive migration status.
        
        Returns:
            Dictionary containing migration status information
        """
        try:
            current_revision = self.get_current_revision()
            pending_migrations = self.get_pending_migrations()
            migration_history = self.get_migration_history()
            
            status = {
                'current_revision': current_revision,
                'pending_migrations': pending_migrations,
                'pending_count': len(pending_migrations),
                'total_migrations': len(migration_history),
                'up_to_date': len(pending_migrations) == 0,
                'migration_history': migration_history
            }
            
            # Get head revision
            if migration_history:
                status['head_revision'] = migration_history[0]['revision']
            else:
                status['head_revision'] = None
            
            return status
        except Exception as e:
            logger.error(f"Failed to get migration status: {e}")
            return {
                'error': str(e),
                'current_revision': None,
                'pending_migrations': [],
                'pending_count': 0,
                'total_migrations': 0,
                'up_to_date': False,
                'migration_history': []
            }
    
    def stamp_database(self, revision: str = "head") -> None:
        """Stamp database with revision without running migrations.
        
        Args:
            revision: Revision to stamp with
        """
        try:
            logger.info(f"Stamping database with revision {revision}")
            command.stamp(self.alembic_cfg, revision)
            logger.info(f"Successfully stamped database with {revision}")
        except Exception as e:
            logger.error(f"Failed to stamp database: {e}")
            raise
    
    def show_migration(self, revision: str) -> str:
        """Show migration details.
        
        Args:
            revision: Migration revision to show
            
        Returns:
            Migration content
        """
        try:
            return command.show(self.alembic_cfg, revision)
        except Exception as e:
            logger.error(f"Failed to show migration {revision}: {e}")
            raise


# Global migration manager instance
_migration_manager = None


def get_migration_manager(engine: Optional[Engine] = None) -> MigrationManager:
    """Get global migration manager instance.
    
    Args:
        engine: Optional engine override
        
    Returns:
        MigrationManager instance
    """
    global _migration_manager
    if _migration_manager is None or engine is not None:
        _migration_manager = MigrationManager(engine)
    return _migration_manager


# Convenience functions
def create_migration(message: str, autogenerate: bool = True, engine: Optional[Engine] = None) -> str:
    """Create a new migration.
    
    Args:
        message: Migration message
        autogenerate: Whether to auto-generate
        engine: Optional engine override
        
    Returns:
        Migration revision ID
    """
    manager = get_migration_manager(engine)
    return manager.create_migration(message, autogenerate)


def run_migrations(target_revision: str = "head", engine: Optional[Engine] = None) -> None:
    """Run migrations.
    
    Args:
        target_revision: Target revision
        engine: Optional engine override
    """
    manager = get_migration_manager(engine)
    manager.run_migrations(target_revision)


def get_migration_status(engine: Optional[Engine] = None) -> Dict[str, Any]:
    """Get migration status.
    
    Args:
        engine: Optional engine override
        
    Returns:
        Migration status information
    """
    manager = get_migration_manager(engine)
    return manager.get_migration_status()