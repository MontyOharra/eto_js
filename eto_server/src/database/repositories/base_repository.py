"""
Base Repository
Abstract base class providing common CRUD operations for all repositories
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Type, TypeVar
from sqlalchemy.orm import Session
from ..connection import DatabaseConnectionManager

# Generic type for model classes
ModelType = TypeVar('ModelType')


class BaseRepository(ABC):
    """
    Abstract base repository providing common CRUD operations
    All model-specific repositories should inherit from this class
    """
    
    def __init__(self, connection_manager: DatabaseConnectionManager):
        """Initialize repository with connection manager"""
        pass
    
    @property
    @abstractmethod
    def model_class(self) -> Type[ModelType]:
        """Return the SQLAlchemy model class this repository manages"""
        pass
    
    def get_session(self) -> Session:
        """Get a new database session from connection manager"""
        pass
    
    def get_by_id(self, id_value: Any) -> Optional[ModelType]:
        """Get a single record by ID"""
        pass
    
    def get_all(self, limit: Optional[int] = None, offset: Optional[int] = None) -> List[ModelType]:
        """Get all records with optional pagination"""
        pass
    
    def create(self, data: Dict[str, Any]) -> ModelType:
        """Create a new record"""
        pass
    
    def update(self, id_value: Any, data: Dict[str, Any]) -> Optional[ModelType]:
        """Update an existing record by ID"""
        pass
    
    def delete(self, id_value: Any) -> bool:
        """Delete a record by ID"""
        pass
    
    def count(self) -> int:
        """Count total records"""
        pass
    
    def exists(self, id_value: Any) -> bool:
        """Check if record exists by ID"""
        pass