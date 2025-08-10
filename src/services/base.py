"""Base service class for common functionality."""

from typing import TypeVar, Generic, Type, Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from pydantic import BaseModel
import logging

from ..models.base import BaseModel as SQLBaseModel

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=SQLBaseModel)
CreateSchemaType = TypeVar('CreateSchemaType', bound=BaseModel)
UpdateSchemaType = TypeVar('UpdateSchemaType', bound=BaseModel)


class ServiceException(Exception):
    """Base service exception."""
    pass


class ValidationException(ServiceException):
    """Validation error exception."""
    pass


class NotFoundError(ServiceException):
    """Entity not found error."""
    pass


class DatabaseError(ServiceException):
    """Database operation error."""
    pass


class BaseService(Generic[T, CreateSchemaType, UpdateSchemaType]):
    """Base service class providing common CRUD operations."""
    
    def __init__(self, db_session: Session, model_class: Type[T]):
        """Initialize service with database session and model class.
        
        Args:
            db_session: SQLAlchemy database session
            model_class: SQLAlchemy model class
        """
        self.db = db_session
        self.model_class = model_class
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def get_by_id(self, entity_id: int) -> Optional[T]:
        """Get entity by ID.
        
        Args:
            entity_id: Entity ID
            
        Returns:
            Entity if found, None otherwise
            
        Raises:
            DatabaseError: If database error occurs
        """
        try:
            return self.db.query(self.model_class).filter(self.model_class.id == entity_id).first()
        except SQLAlchemyError as e:
            self._logger.error(f"Database error in get_by_id: {e}")
            raise DatabaseError(f"Failed to get {self.model_class.__name__} by ID") from e
    
    def get_by_id_or_404(self, entity_id: int) -> T:
        """Get entity by ID or raise NotFoundError.
        
        Args:
            entity_id: Entity ID
            
        Returns:
            Entity if found
            
        Raises:
            NotFoundError: If entity not found
            DatabaseError: If database error occurs
        """
        entity = self.get_by_id(entity_id)
        if entity is None:
            raise NotFoundError(f"{self.model_class.__name__} with ID {entity_id} not found")
        return entity
    
    def list(self, 
             limit: int = 100, 
             offset: int = 0, 
             filters: Optional[Dict[str, Any]] = None,
             order_by: Optional[str] = None) -> List[T]:
        """Get list of entities with pagination and filtering.
        
        Args:
            limit: Maximum number of entities to return
            offset: Number of entities to skip
            filters: Dictionary of filter criteria
            order_by: Column name to order by
            
        Returns:
            List of entities
            
        Raises:
            DatabaseError: If database error occurs
        """
        try:
            query = self.db.query(self.model_class)
            
            # Apply filters
            if filters:
                for field, value in filters.items():
                    if hasattr(self.model_class, field):
                        query = query.filter(getattr(self.model_class, field) == value)
            
            # Apply ordering
            if order_by and hasattr(self.model_class, order_by):
                query = query.order_by(getattr(self.model_class, order_by))
            
            # Apply pagination
            return query.offset(offset).limit(limit).all()
        except SQLAlchemyError as e:
            self._logger.error(f"Database error in list: {e}")
            raise DatabaseError(f"Failed to list {self.model_class.__name__} entities") from e
    
    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count entities with optional filtering.
        
        Args:
            filters: Dictionary of filter criteria
            
        Returns:
            Count of matching entities
            
        Raises:
            DatabaseError: If database error occurs
        """
        try:
            query = self.db.query(self.model_class)
            
            # Apply filters
            if filters:
                for field, value in filters.items():
                    if hasattr(self.model_class, field):
                        query = query.filter(getattr(self.model_class, field) == value)
            
            return query.count()
        except SQLAlchemyError as e:
            self._logger.error(f"Database error in count: {e}")
            raise DatabaseError(f"Failed to count {self.model_class.__name__} entities") from e
    
    def create(self, obj_in: CreateSchemaType) -> T:
        """Create a new entity.
        
        Args:
            obj_in: Create schema with entity data
            
        Returns:
            Created entity
            
        Raises:
            ValidationException: If validation fails
            DatabaseError: If database error occurs
        """
        try:
            # Convert Pydantic model to dict
            obj_data = obj_in.model_dump() if hasattr(obj_in, 'model_dump') else obj_in.dict()
            
            # Create SQLAlchemy model instance
            db_obj = self.model_class(**obj_data)
            
            # Add and commit
            self.db.add(db_obj)
            self.db.commit()
            self.db.refresh(db_obj)
            
            self._logger.info(f"Created {self.model_class.__name__} with ID {db_obj.id}")
            return db_obj
        except SQLAlchemyError as e:
            self.db.rollback()
            self._logger.error(f"Database error in create: {e}")
            raise DatabaseError(f"Failed to create {self.model_class.__name__}") from e
        except Exception as e:
            self.db.rollback()
            self._logger.error(f"Validation error in create: {e}")
            raise ValidationException(f"Invalid data for {self.model_class.__name__}") from e
    
    def update(self, entity_id: int, obj_in: UpdateSchemaType) -> T:
        """Update an entity.
        
        Args:
            entity_id: Entity ID to update
            obj_in: Update schema with new data
            
        Returns:
            Updated entity
            
        Raises:
            NotFoundError: If entity not found
            ValidationException: If validation fails
            DatabaseError: If database error occurs
        """
        try:
            # Get existing entity
            db_obj = self.get_by_id_or_404(entity_id)
            
            # Convert update schema to dict, excluding unset fields
            obj_data = obj_in.model_dump(exclude_unset=True) if hasattr(obj_in, 'model_dump') else obj_in.dict(exclude_unset=True)
            
            # Update fields
            for field, value in obj_data.items():
                if hasattr(db_obj, field):
                    setattr(db_obj, field, value)
            
            # Commit changes
            self.db.commit()
            self.db.refresh(db_obj)
            
            self._logger.info(f"Updated {self.model_class.__name__} with ID {entity_id}")
            return db_obj
        except (NotFoundError, ValidationException):
            raise
        except SQLAlchemyError as e:
            self.db.rollback()
            self._logger.error(f"Database error in update: {e}")
            raise DatabaseError(f"Failed to update {self.model_class.__name__}") from e
        except Exception as e:
            self.db.rollback()
            self._logger.error(f"Validation error in update: {e}")
            raise ValidationException(f"Invalid update data for {self.model_class.__name__}") from e
    
    def delete(self, entity_id: int) -> bool:
        """Delete an entity.
        
        Args:
            entity_id: Entity ID to delete
            
        Returns:
            True if deleted successfully
            
        Raises:
            NotFoundError: If entity not found
            DatabaseError: If database error occurs
        """
        try:
            # Get existing entity
            db_obj = self.get_by_id_or_404(entity_id)
            
            # Delete entity
            self.db.delete(db_obj)
            self.db.commit()
            
            self._logger.info(f"Deleted {self.model_class.__name__} with ID {entity_id}")
            return True
        except NotFoundError:
            raise
        except SQLAlchemyError as e:
            self.db.rollback()
            self._logger.error(f"Database error in delete: {e}")
            raise DatabaseError(f"Failed to delete {self.model_class.__name__}") from e
    
    def exists(self, entity_id: int) -> bool:
        """Check if entity exists.
        
        Args:
            entity_id: Entity ID to check
            
        Returns:
            True if exists, False otherwise
            
        Raises:
            DatabaseError: If database error occurs
        """
        try:
            return self.db.query(self.model_class).filter(self.model_class.id == entity_id).first() is not None
        except SQLAlchemyError as e:
            self._logger.error(f"Database error in exists: {e}")
            raise DatabaseError(f"Failed to check if {self.model_class.__name__} exists") from e
    
    def bulk_create(self, objects_in: List[CreateSchemaType]) -> List[T]:
        """Create multiple entities in bulk.
        
        Args:
            objects_in: List of create schemas
            
        Returns:
            List of created entities
            
        Raises:
            ValidationException: If validation fails
            DatabaseError: If database error occurs
        """
        try:
            db_objects = []
            for obj_in in objects_in:
                obj_data = obj_in.model_dump() if hasattr(obj_in, 'model_dump') else obj_in.dict()
                db_obj = self.model_class(**obj_data)
                db_objects.append(db_obj)
            
            # Add all objects
            self.db.add_all(db_objects)
            self.db.commit()
            
            # Refresh all objects
            for db_obj in db_objects:
                self.db.refresh(db_obj)
            
            self._logger.info(f"Bulk created {len(db_objects)} {self.model_class.__name__} entities")
            return db_objects
        except SQLAlchemyError as e:
            self.db.rollback()
            self._logger.error(f"Database error in bulk_create: {e}")
            raise DatabaseError(f"Failed to bulk create {self.model_class.__name__} entities") from e
        except Exception as e:
            self.db.rollback()
            self._logger.error(f"Validation error in bulk_create: {e}")
            raise ValidationException(f"Invalid data for bulk create {self.model_class.__name__}") from e