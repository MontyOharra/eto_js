"""
Pipeline Repository  
Data access layer for Pipeline model operations
"""
from typing import Optional, List
from .base_repository import BaseRepository
from ..models import Pipeline


class PipelineRepository(BaseRepository):
    """Repository for Pipeline model operations"""
    
    @property
    def model_class(self):
        return Pipeline
    
    def get_by_user(self, user_id: str) -> List[Pipeline]:
        """Get pipelines created by a specific user"""
        pass
    
    def get_by_status(self, status: str) -> List[Pipeline]:
        """Get pipelines by status (draft, active, archived)"""
        pass
    
    def get_active_pipelines(self) -> List[Pipeline]:
        """Get all active pipelines"""
        pass
    
    def get_by_name(self, name: str) -> Optional[Pipeline]:
        """Get pipeline by name"""
        pass