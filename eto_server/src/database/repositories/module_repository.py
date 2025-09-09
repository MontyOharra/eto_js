"""
Module Repository
Data access layer for BaseModule and CustomModule model operations
"""
import logging
from typing import Optional, List, Dict, Any
from sqlalchemy.exc import SQLAlchemyError
from .base_repository import BaseRepository, RepositoryError
from ..models import BaseModule


logger = logging.getLogger(__name__)


class ModuleRepository(BaseRepository[BaseModule]):
    """Repository for BaseModule model operations"""
    
    @property
    def model_class(self):
        return BaseModule
    
    def get_active_modules(self) -> List[BaseModule]:
        """Get all active base modules"""
        try:
            with self.connection_manager.session_scope() as session:
                return session.query(self.model_class).filter(
                    self.model_class.is_active == True
                ).order_by(self.model_class.category.asc(), 
                           self.model_class.name.asc()).all()
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting active modules: {e}")
            raise RepositoryError(f"Failed to get active modules: {e}") from e
    
    def get_by_category(self, category: str) -> List[BaseModule]:
        """Get modules by category"""
        if not category:
            return []
        
        try:
            with self.connection_manager.session_scope() as session:
                return session.query(self.model_class).filter(
                    self.model_class.category == category,
                    self.model_class.is_active == True
                ).order_by(self.model_class.name.asc()).all()
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting modules by category {category}: {e}")
            raise RepositoryError(f"Failed to get modules by category: {e}") from e
    
    def get_by_name(self, name: str) -> Optional[BaseModule]:
        """Get module by name"""
        if not name:
            return None
        
        return self.get_by_field_single('name', name)
    
    def populate_base_modules(self, modules_data: List[Dict[str, Any]]) -> int:
        """Bulk insert/update base modules, return count"""
        if not modules_data:
            return 0
        
        try:
            updated_count = 0
            created_count = 0
            
            for module_data in modules_data:
                if 'id' not in module_data:
                    logger.warning(f"Skipping module data without ID: {module_data}")
                    continue
                
                module_id = module_data['id']
                
                # Check if module already exists
                existing_module = self.get_by_id(module_id)
                
                if existing_module:
                    # Update existing module
                    # Remove id from update data to avoid updating primary key
                    update_data = {k: v for k, v in module_data.items() if k != 'id'}
                    if update_data:  # Only update if there's data to update
                        updated_module = self.update(module_id, update_data)
                        if updated_module:
                            updated_count += 1
                            logger.debug(f"Updated module: {module_id}")
                else:
                    # Create new module
                    created_module = self.create(module_data)
                    if created_module:
                        created_count += 1
                        logger.debug(f"Created module: {module_id}")
            
            total_processed = updated_count + created_count
            logger.info(f"Module population complete: {created_count} created, {updated_count} updated, {total_processed} total")
            return total_processed
            
        except Exception as e:
            logger.error(f"Error populating base modules: {e}")
            raise RepositoryError(f"Failed to populate base modules: {e}") from e