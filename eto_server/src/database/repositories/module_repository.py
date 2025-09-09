"""
Module Repository
Data access layer for BaseModule and CustomModule model operations
"""
from typing import Optional, List
from .base_repository import BaseRepository
from ..models import BaseModule


class ModuleRepository(BaseRepository):
    """Repository for BaseModule model operations"""
    
    @property
    def model_class(self):
        return BaseModule
    
    def get_active_modules(self) -> List[BaseModule]:
        """Get all active base modules"""
        pass
    
    def get_by_category(self, category: str) -> List[BaseModule]:
        """Get modules by category"""
        pass
    
    def get_by_name(self, name: str) -> Optional[BaseModule]:
        """Get module by name"""
        pass
    
    def populate_base_modules(self, modules_data: List[dict]) -> int:
        """Bulk insert/update base modules, return count"""
        pass