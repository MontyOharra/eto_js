"""
Base Repository
Abstract base class providing common CRUD operations for all repositories
"""
import logging
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Type, TypeVar, Generic, Protocol
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from ..connection import DatabaseConnectionManager
from ...exceptions import RepositoryError


logger = logging.getLogger(__name__)


class HasId(Protocol):
    """Protocol for models that have an id attribute"""
    id: Any

ModelType = TypeVar('ModelType', bound=HasId)

class BaseRepository(ABC, Generic[ModelType]):
    """
    Abstract base repository providing common CRUD operations
    All model-specific repositories should inherit from this class
    """
    
    def __init__(self, connection_manager: DatabaseConnectionManager):
        """Initialize repository with connection manager"""
        if not connection_manager:
            raise ValueError("DatabaseConnectionManager is required")
        
        self.connection_manager = connection_manager
        logger.debug(f"Initialized {self.__class__.__name__}")
    
    @property
    @abstractmethod
    def model_class(self) -> Type[ModelType]:
        """Return the SQLAlchemy model class this repository manages"""
        pass
    
    def get_session(self) -> Session:
        """Get a new database session from connection manager"""
        return self.connection_manager.get_session()
    
    def get_by_id(self, id_value: Any) -> Optional[ModelType]:
        """Get a single record by ID"""
        if id_value is None:
            return None
            
        try:
            with self.connection_manager.session_scope() as session:
                model = session.get(self.model_class, id_value)
                return model                
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting {self.model_class.__name__} by ID {id_value}: {e}")
            raise RepositoryError(f"Failed to get record by ID: {e}") from e
    
    def get_all(self, order_by: Optional[str] = None, desc: bool = False, 
               limit: Optional[int] = None, offset: Optional[int] = None) -> List[ModelType]:
        """Get all records with optional sorting and pagination"""
        try:
            with self.connection_manager.session_scope() as session:
                query = session.query(self.model_class)
                
                # Apply sorting if specified
                if order_by:
                    if hasattr(self.model_class, order_by):
                        column = getattr(self.model_class, order_by)
                        query = query.order_by(column.desc() if desc else column)
                    else:
                        logger.warning(f"Field '{order_by}' does not exist on {self.model_class.__name__}, skipping sort")
                
                if offset is not None:
                    query = query.offset(offset)
                
                if limit is not None:
                    query = query.limit(limit)
                
                return query.all()
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting all {self.model_class.__name__} records: {e}")
            raise RepositoryError(f"Failed to get records: {e}") from e
    
    def create(self, data: Dict[str, Any]) -> ModelType:
        """Create a new record"""
        if not data:
            raise ValueError("Data dictionary cannot be empty")
            
        try:
            with self.connection_manager.session_scope() as session:
                # Create new instance of the model
                instance = self.model_class(**data)
                
                # Add to session and flush to get ID
                session.add(instance)
                session.flush()  # This populates the ID without committing
                
                # Refresh to get updated fields (like auto-generated timestamps)
                session.refresh(instance)
                session.expunge(instance)  # Remove from session to prevent future commits
                
                logger.debug(f"Created {self.model_class.__name__} with ID: {instance.id}")
                return instance
                
        except SQLAlchemyError as e:
            logger.error(f"Error creating {self.model_class.__name__}: {e}")
            raise RepositoryError(f"Failed to create record: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error creating {self.model_class.__name__}: {e}")
            raise RepositoryError(f"Unexpected error: {e}") from e
    
    def create_and_get_id(self, data: Dict[str, Any]) -> int:
        """Create a new record and return just the ID"""
        if not data:
            raise ValueError("Data dictionary cannot be empty")
            
        try:
            with self.connection_manager.session_scope() as session:
                # Create new instance of the model
                instance = self.model_class(**data)
                
                # Add to session and flush to get ID
                session.add(instance)
                session.flush()  # This populates the ID without committing
                
                # Access ID while session is still open
                record_id = instance.id
                
                logger.debug(f"Created {self.model_class.__name__} with ID: {record_id}")
                return record_id
                
        except SQLAlchemyError as e:
            logger.error(f"Error creating {self.model_class.__name__}: {e}")
            raise RepositoryError(f"Failed to create record: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error creating {self.model_class.__name__}: {e}")
            raise RepositoryError(f"Unexpected error: {e}") from e
    
    def update(self, id_value: Any, data: Dict[str, Any]) -> Optional[ModelType]:
        """Update an existing record by ID"""
        if id_value is None:
            raise ValueError("ID value cannot be None")
        
        if not data:
            raise ValueError("Update data cannot be empty")
            
        try:
            with self.connection_manager.session_scope() as session:
                # Get existing record
                instance = session.query(self.model_class).filter(
                    self.model_class.id == id_value
                ).first()
                
                if not instance:
                    logger.warning(f"{self.model_class.__name__} with ID {id_value} not found")
                    return None
                
                # Update fields
                for key, value in data.items():
                    if hasattr(instance, key):
                        setattr(instance, key, value)
                    else:
                        logger.warning(f"Ignoring unknown field '{key}' for {self.model_class.__name__}")
                
                # Flush to update in database
                session.flush()
                session.refresh(instance)
                
                logger.debug(f"Updated {self.model_class.__name__} with ID: {id_value}")
                return instance
                
        except SQLAlchemyError as e:
            logger.error(f"Error updating {self.model_class.__name__} {id_value}: {e}")
            raise RepositoryError(f"Failed to update record: {e}") from e
    
    def delete(self, id_value: Any) -> bool:
        """Delete a record by ID"""
        if id_value is None:
            raise ValueError("ID value cannot be None")
            
        try:
            with self.connection_manager.session_scope() as session:
                # Get existing record
                instance = session.query(self.model_class).filter(
                    self.model_class.id == id_value
                ).first()
                
                if not instance:
                    logger.warning(f"{self.model_class.__name__} with ID {id_value} not found")
                    return False
                
                # Delete the record
                session.delete(instance)
                
                logger.debug(f"Deleted {self.model_class.__name__} with ID: {id_value}")
                return True
                
        except SQLAlchemyError as e:
            logger.error(f"Error deleting {self.model_class.__name__} {id_value}: {e}")
            raise RepositoryError(f"Failed to delete record: {e}") from e
    
    def count(self) -> int:
        """Count total records"""
        try:
            with self.connection_manager.session_scope() as session:
                return session.query(self.model_class).count()
                
        except SQLAlchemyError as e:
            logger.error(f"Error counting {self.model_class.__name__} records: {e}")
            raise RepositoryError(f"Failed to count records: {e}") from e
    
    def exists(self, id_value: Any) -> bool:
        """Check if record exists by ID"""
        if id_value is None:
            return False
            
        try:
            with self.connection_manager.session_scope() as session:
                return session.query(self.model_class).filter(
                    self.model_class.id == id_value
                ).first() is not None
                
        except SQLAlchemyError as e:
            logger.error(f"Error checking existence of {self.model_class.__name__} {id_value}: {e}")
            raise RepositoryError(f"Failed to check record existence: {e}") from e
    
    def get_by_field(self, field_name: str, field_value: Any) -> List[ModelType]:
        """Get records by a specific field value"""
        if not hasattr(self.model_class, field_name):
            raise ValueError(f"Field '{field_name}' does not exist on {self.model_class.__name__}")
            
        try:
            with self.connection_manager.session_scope() as session:
                return session.query(self.model_class).filter(
                    getattr(self.model_class, field_name) == field_value
                ).all()
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting {self.model_class.__name__} by {field_name}: {e}")
            raise RepositoryError(f"Failed to get records by field: {e}") from e
    
    def get_by_field_single(self, field_name: str, field_value: Any) -> Optional[ModelType]:
        """Get single record by a specific field value"""
        if not hasattr(self.model_class, field_name):
            raise ValueError(f"Field '{field_name}' does not exist on {self.model_class.__name__}")
            
        try:
            with self.connection_manager.session_scope() as session:
                return session.query(self.model_class).filter(
                    getattr(self.model_class, field_name) == field_value
                ).first()
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting {self.model_class.__name__} by {field_name}: {e}")
            raise RepositoryError(f"Failed to get record by field: {e}") from e