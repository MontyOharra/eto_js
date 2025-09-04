"""
Module Registry System for ETO Transformation Pipeline

This module manages the registration and discovery of all available transformation modules.
"""

import json
import logging
from typing import Dict, Type, List, Optional
from .base import BaseModuleExecutor
from .text_processing import BasicTextCleanerModule, AdvancedTextCleanerModule, TextSplitterModule
from .llm_processing import VariableLLMModule, DataCombinerModule

logger = logging.getLogger(__name__)

class ModuleRegistry:
    """Central registry for all available transformation modules"""
    
    def __init__(self):
        self._modules: Dict[str, Type[BaseModuleExecutor]] = {}
        self._register_builtin_modules()
    
    def _register_builtin_modules(self):
        """Register all built-in modules"""
        builtin_modules = [
            BasicTextCleanerModule,
            AdvancedTextCleanerModule,
            TextSplitterModule,
            VariableLLMModule,
            DataCombinerModule,
        ]
        
        for module_class in builtin_modules:
            # Create instance to get module ID
            instance = module_class()
            module_id = instance.get_module_id()
            self.register(module_id, module_class)
            logger.info(f"Registered built-in module: {module_id}")
    
    def register(self, module_id: str, module_class: Type[BaseModuleExecutor]):
        """Register a module class
        
        Args:
            module_id: Unique identifier for the module
            module_class: Class that implements BaseModuleExecutor
        """
        if not issubclass(module_class, BaseModuleExecutor):
            raise ValueError(f"Module class {module_class} must inherit from BaseModuleExecutor")
        
        self._modules[module_id] = module_class
        logger.info(f"Module registered: {module_id}")
    
    def get_module(self, module_id: str) -> Optional[BaseModuleExecutor]:
        """Get instantiated module by ID
        
        Args:
            module_id: Unique identifier for the module
            
        Returns:
            Instantiated module or None if not found
        """
        module_class = self._modules.get(module_id)
        if module_class:
            return module_class()
        return None
    
    def get_all_module_ids(self) -> List[str]:
        """Get list of all registered module IDs"""
        return list(self._modules.keys())
    
    def get_all_module_info(self) -> List[Dict]:
        """Get all module templates for database storage
        
        Returns:
            List of module info dictionaries ready for database insertion
        """
        modules_info = []
        for module_id in self._modules.keys():
            module = self.get_module(module_id)
            if module:
                modules_info.append(module.get_module_info())
        return modules_info
    
    def execute_module(self, module_id: str, inputs: Dict, config: Dict, output_names: List[str] = None) -> Dict:
        """Execute a module by ID
        
        Args:
            module_id: ID of module to execute
            inputs: Input values
            config: Configuration values
            output_names: Expected output names (for variable output modules)
            
        Returns:
            Module output
            
        Raises:
            ValueError: If module not found
            ModuleExecutionError: If execution fails
        """
        module = self.get_module(module_id)
        if not module:
            raise ValueError(f"Module not found: {module_id}")
        
        logger.info(f"Executing module: {module_id}")
        return module.execute(inputs, config, output_names)
    
    def validate_module_inputs(self, module_id: str, inputs: Dict) -> bool:
        """Validate inputs for a specific module
        
        Args:
            module_id: ID of module to validate for
            inputs: Input values to validate
            
        Returns:
            True if valid
            
        Raises:
            ValueError: If module not found
            ModuleValidationError: If validation fails
        """
        module = self.get_module(module_id)
        if not module:
            raise ValueError(f"Module not found: {module_id}")
        
        return module.validate_inputs(inputs)
    
    def validate_module_config(self, module_id: str, config: Dict) -> bool:
        """Validate config for a specific module
        
        Args:
            module_id: ID of module to validate for
            config: Config values to validate
            
        Returns:
            True if valid
            
        Raises:
            ValueError: If module not found
            ModuleValidationError: If validation fails
        """
        module = self.get_module(module_id)
        if not module:
            raise ValueError(f"Module not found: {module_id}")
        
        return module.validate_config(config)

# Global registry instance
_registry = None

def get_module_registry() -> ModuleRegistry:
    """Get the global module registry instance"""
    global _registry
    if _registry is None:
        _registry = ModuleRegistry()
    return _registry

def populate_database_with_modules():
    """Populate database with all registered modules"""
    from ..database import get_db_service, BaseModule
    
    db_service = get_db_service()
    if not db_service:
        logger.error("Database service not available")
        return False
    
    registry = get_module_registry()
    modules_info = registry.get_all_module_info()
    
    session = db_service.get_session()
    try:
        # Clear existing base modules
        session.query(BaseModule).delete()
        
        # Insert new modules
        for module_info in modules_info:
            base_module = BaseModule(**module_info)
            session.add(base_module)
        
        session.commit()
        logger.info(f"Successfully populated database with {len(modules_info)} base modules")
        return True
        
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to populate database with modules: {e}")
        return False
    finally:
        session.close()