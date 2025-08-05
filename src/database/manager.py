"""Database management utilities for schema operations."""

import logging
from typing import Optional, List, Dict, Any
from sqlalchemy import Engine, text, inspect
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError, ProgrammingError
from src.models.base import Base
from .config import get_engine, get_session

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database operations including schema creation and validation."""
    
    def __init__(self, engine: Optional[Engine] = None):
        """Initialize database manager.
        
        Args:
            engine: Optional SQLAlchemy engine
        """
        self.engine = engine or get_engine()
        self.SessionLocal = get_session(self.engine)
    
    def create_all_tables(self) -> None:
        """Create all tables defined in the models."""
        try:
            logger.info("Creating all database tables...")
            Base.metadata.create_all(bind=self.engine)
            logger.info("Successfully created all tables")
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise
    
    def drop_all_tables(self) -> None:
        """Drop all tables (WARNING: This will delete all data!)."""
        try:
            logger.warning("Dropping all database tables...")
            Base.metadata.drop_all(bind=self.engine)
            logger.info("Successfully dropped all tables")
        except Exception as e:
            logger.error(f"Failed to drop tables: {e}")
            raise
    
    def recreate_all_tables(self) -> None:
        """Drop and recreate all tables (WARNING: This will delete all data!)."""
        self.drop_all_tables()
        self.create_all_tables()
    
    def get_table_names(self) -> List[str]:
        """Get list of all table names in the database.
        
        Returns:
            List of table names
        """
        inspector = inspect(self.engine)
        return inspector.get_table_names()
    
    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists in the database.
        
        Args:
            table_name: Name of the table to check
            
        Returns:
            True if table exists, False otherwise
        """
        return table_name in self.get_table_names()
    
    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """Get information about a specific table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            Dictionary containing table information
        """
        if not self.table_exists(table_name):
            raise ValueError(f"Table '{table_name}' does not exist")
        
        inspector = inspect(self.engine)
        columns = inspector.get_columns(table_name)
        indexes = inspector.get_indexes(table_name)
        foreign_keys = inspector.get_foreign_keys(table_name)
        primary_key = inspector.get_pk_constraint(table_name)
        
        return {
            'name': table_name,
            'columns': columns,
            'indexes': indexes,
            'foreign_keys': foreign_keys,
            'primary_key': primary_key
        }
    
    def validate_schema(self) -> Dict[str, Any]:
        """Validate that the database schema matches the models.
        
        Returns:
            Dictionary containing validation results
        """
        results = {
            'valid': True,
            'missing_tables': [],
            'extra_tables': [],
            'model_tables': [],
            'db_tables': []
        }
        
        # Get expected tables from models
        model_tables = set(Base.metadata.tables.keys())
        results['model_tables'] = sorted(model_tables)
        
        # Get actual tables from database
        try:
            db_tables = set(self.get_table_names())
            results['db_tables'] = sorted(db_tables)
        except Exception as e:
            logger.error(f"Failed to get database table names: {e}")
            results['valid'] = False
            results['error'] = str(e)
            return results
        
        # Find missing and extra tables
        results['missing_tables'] = sorted(model_tables - db_tables)
        results['extra_tables'] = sorted(db_tables - model_tables)
        
        if results['missing_tables'] or results['extra_tables']:
            results['valid'] = False
        
        return results
    
    def test_connection(self) -> Dict[str, Any]:
        """Test database connection and basic operations.
        
        Returns:
            Dictionary containing connection test results
        """
        results = {
            'connected': False,
            'readable': False,
            'writable': False,
            'error': None
        }
        
        try:
            # Test basic connection
            with self.engine.connect() as conn:
                results['connected'] = True
                
                # Test read operation
                try:
                    conn.execute(text("SELECT 1"))
                    results['readable'] = True
                except Exception as e:
                    logger.error(f"Database read test failed: {e}")
                    results['error'] = str(e)
                    return results
                
                # Test write operation (create temporary table)
                try:
                    conn.execute(text("CREATE TEMPORARY TABLE test_write (id INTEGER)"))
                    conn.execute(text("INSERT INTO test_write (id) VALUES (1)"))
                    conn.execute(text("DROP TABLE test_write"))
                    results['writable'] = True
                    conn.commit()
                except Exception as e:
                    logger.error(f"Database write test failed: {e}")
                    results['error'] = str(e)
                    return results
                    
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            results['error'] = str(e)
        
        return results
    
    def get_database_info(self) -> Dict[str, Any]:
        """Get general information about the database.
        
        Returns:
            Dictionary containing database information
        """
        info = {
            'url': str(self.engine.url).replace(self.engine.url.password or '', '***'),
            'dialect': self.engine.dialect.name,
            'driver': self.engine.dialect.driver,
            'server_version': None,
            'connection_test': self.test_connection(),
            'schema_validation': self.validate_schema()
        }
        
        # Try to get server version
        try:
            with self.engine.connect() as conn:
                if self.engine.dialect.name == 'postgresql':
                    result = conn.execute(text("SELECT version()"))
                    info['server_version'] = result.scalar()
                elif self.engine.dialect.name == 'sqlite':
                    result = conn.execute(text("SELECT sqlite_version()"))
                    info['server_version'] = f"SQLite {result.scalar()}"
                elif self.engine.dialect.name == 'mysql':
                    result = conn.execute(text("SELECT @@version"))
                    info['server_version'] = result.scalar()
        except Exception as e:
            logger.warning(f"Could not get server version: {e}")
        
        return info
    
    def execute_sql(self, sql: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Execute raw SQL query.
        
        Args:
            sql: SQL query string
            params: Optional query parameters
            
        Returns:
            Query result
        """
        with self.engine.connect() as conn:
            if params:
                return conn.execute(text(sql), params)
            else:
                return conn.execute(text(sql))
    
    def get_session(self) -> Session:
        """Get a new database session.
        
        Returns:
            SQLAlchemy Session instance
        """
        return self.SessionLocal()