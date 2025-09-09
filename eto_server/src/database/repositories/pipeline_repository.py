"""
Pipeline Repository  
Data access layer for Pipeline model operations
"""
import logging
from typing import Optional, List
from sqlalchemy.exc import SQLAlchemyError
from .base_repository import BaseRepository, RepositoryError
from ..models import Pipeline


logger = logging.getLogger(__name__)


class PipelineRepository(BaseRepository[Pipeline]):
    """Repository for Pipeline model operations"""
    
    @property
    def model_class(self):
        return Pipeline
    
    def get_by_user(self, user_id: str) -> List[Pipeline]:
        """Get pipelines created by a specific user"""
        if not user_id:
            return []
        
        try:
            with self.connection_manager.session_scope() as session:
                return session.query(self.model_class).filter(
                    self.model_class.created_by_user == user_id
                ).order_by(self.model_class.updated_at.desc()).all()
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting pipelines by user {user_id}: {e}")
            raise RepositoryError(f"Failed to get pipelines by user: {e}") from e
    
    def get_by_status(self, status: str) -> List[Pipeline]:
        """Get pipelines by status (draft, active, archived)"""
        if not status:
            return []
        
        try:
            with self.connection_manager.session_scope() as session:
                return session.query(self.model_class).filter(
                    self.model_class.status == status
                ).order_by(self.model_class.updated_at.desc()).all()
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting pipelines by status {status}: {e}")
            raise RepositoryError(f"Failed to get pipelines by status: {e}") from e
    
    def get_active_pipelines(self) -> List[Pipeline]:
        """Get all active pipelines"""
        try:
            with self.connection_manager.session_scope() as session:
                return session.query(self.model_class).filter(
                    self.model_class.is_active == True,
                    self.model_class.status == 'active'
                ).order_by(self.model_class.updated_at.desc()).all()
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting active pipelines: {e}")
            raise RepositoryError(f"Failed to get active pipelines: {e}") from e
    
    def get_by_name(self, name: str) -> Optional[Pipeline]:
        """Get pipeline by name"""
        if not name:
            return None
        
        return self.get_by_field_single('name', name)