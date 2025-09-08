"""
Module Registry System for ETO Transformation Pipeline

This module manages the registration and discovery of all available transformation modules.
"""

import json
import logging
from typing import Dict, Type, List, Optional, Set
from ..types import (
    ModuleID, ModuleInfo, FrontendModuleInfo, ModuleExecutor, NodeSchema,
    ExecutionInputs, ExecutionConfig, ExecutionOutputs, ExecutionNodeInfo,
    ModuleExecutionError, ModuleValidationError
)
from .module import BaseModuleExecutor
from .definitions.text_processing.basic_text_cleaner import BasicTextCleanerModule
from .definitions.text_processing.advanced_text_cleaner import AdvancedTextCleanerModule
from .definitions.data_processing.sql_parser import SQLParserModule
from .definitions.data_processing.type_converter import TypeConverterModule

logger = logging.getLogger(__name__)

class ModuleRegistry:
    """Central registry for all available transformation modules"""
    
    def __init__(self) -> None:
        self._modules: Dict[ModuleID, Type[BaseModuleExecutor]] = {}
        self._register_builtin_modules()
    
    def _register_builtin_modules(self) -> None:
        """Register all built-in modules"""
        builtin_modules: List[Type[BaseModuleExecutor]] = [
            BasicTextCleanerModule,
            AdvancedTextCleanerModule,
            SQLParserModule,
            TypeConverterModule,
        ]
        
        for module_class in builtin_modules:
            # Create instance to get module ID
            instance = module_class()
            module_id = instance.get_module_id()
            self.register(module_id, module_class)
            logger.info(f"Registered built-in module: {module_id}")
    
    def register(self, module_id: ModuleID, module_class: Type[BaseModuleExecutor]) -> None:
        """Register a module class
        
        Args:
            module_id: Unique identifier for the module
            module_class: Class that implements BaseModuleExecutor
            
        Raises:
            ValueError: If module class doesn't inherit from BaseModuleExecutor
        """
        if not issubclass(module_class, BaseModuleExecutor):
            raise ValueError(f"Module class {module_class} must inherit from BaseModuleExecutor")
        
        self._modules[module_id] = module_class
        logger.info(f"Module registered: {module_id}")
    
    def get_module(self, module_id: ModuleID) -> Optional[BaseModuleExecutor]:
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
    
    def get_all_module_ids(self) -> List[ModuleID]:
        """Get list of all registered module IDs"""
        return list(self._modules.keys())
    
    def get_all_module_info(self) -> List[ModuleInfo]:
        """Get all module templates for database storage
        
        Returns:
            List of module info dictionaries ready for database insertion
        """
        modules_info: List[ModuleInfo] = []
        for module_id in self._modules.keys():
            module = self.get_module(module_id)
            if module:
                modules_info.append(module.get_module_info())
        return modules_info
    
    def execute_module(
        self, 
        module_id: ModuleID, 
        inputs: ExecutionInputs, 
        config: ExecutionConfig,
        node_info: ExecutionNodeInfo,
        output_names: Optional[List[str]] = None
    ) -> ExecutionOutputs:
        """Execute a module by ID
        
        Args:
            module_id: ID of module to execute
            inputs: Input values
            config: Configuration values
            node_info: Information about input/output node IDs and their types
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
        try:
            return module.execute(inputs, config, node_info, output_names)
        except Exception as e:
            logger.error(f"Module execution failed for {module_id}: {e}")
            raise ModuleExecutionError(f"Failed to execute module {module_id}: {str(e)}")
    
    def validate_module_inputs(self, module_id: ModuleID, inputs: ExecutionInputs) -> bool:
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
        
        try:
            return module.validate_inputs(inputs)
        except Exception as e:
            logger.error(f"Input validation failed for {module_id}: {e}")
            raise ModuleValidationError(f"Invalid inputs for module {module_id}: {str(e)}")
    
    def validate_module_config(self, module_id: ModuleID, config: ExecutionConfig) -> bool:
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
        
        try:
            return module.validate_config(config)
        except Exception as e:
            logger.error(f"Config validation failed for {module_id}: {e}")
            raise ModuleValidationError(f"Invalid config for module {module_id}: {str(e)}")
    
    def has_module(self, module_id: ModuleID) -> bool:
        """Check if a module is registered
        
        Args:
            module_id: ID of module to check
            
        Returns:
            True if module exists
        """
        return module_id in self._modules
    
    def get_registered_module_count(self) -> int:
        """Get the total number of registered modules"""
        return len(self._modules)
    
    def get_dynamic_input_template(self, module_id: ModuleID, config: ExecutionConfig) -> Optional[NodeSchema]:
        """Get template for creating new dynamic input nodes
        
        Args:
            module_id: ID of module
            config: Current configuration values
            
        Returns:
            NodeSchema template for new input nodes, or None if not dynamic
            
        Raises:
            ValueError: If module not found
        """
        module = self.get_module(module_id)
        if not module:
            raise ValueError(f"Module not found: {module_id}")
        
        return module.get_dynamic_input_template(config)
    
    def get_dynamic_output_template(self, module_id: ModuleID, config: ExecutionConfig) -> Optional[NodeSchema]:
        """Get template for creating new dynamic output nodes
        
        Args:
            module_id: ID of module
            config: Current configuration values
            
        Returns:
            NodeSchema template for new output nodes, or None if not dynamic
            
        Raises:
            ValueError: If module not found
        """
        module = self.get_module(module_id)
        if not module:
            raise ValueError(f"Module not found: {module_id}")
        
        return module.get_dynamic_output_template(config)
    
    def get_base_input_nodes(self, module_id: ModuleID) -> List[NodeSchema]:
        """Get base input nodes that are created when module is instantiated
        
        Args:
            module_id: ID of module
            
        Returns:
            List of base input node schemas
            
        Raises:
            ValueError: If module not found
        """
        module = self.get_module(module_id)
        if not module:
            raise ValueError(f"Module not found: {module_id}")
        
        return module.get_base_input_nodes()
    
    def get_base_output_nodes(self, module_id: ModuleID) -> List[NodeSchema]:
        """Get base output nodes that are created when module is instantiated
        
        Args:
            module_id: ID of module
            
        Returns:
            List of base output node schemas
            
        Raises:
            ValueError: If module not found
        """
        module = self.get_module(module_id)
        if not module:
            raise ValueError(f"Module not found: {module_id}")
        
        return module.get_base_output_nodes()
    
    def supports_dynamic_inputs(self, module_id: ModuleID) -> bool:
        """Check if module supports dynamic input nodes
        
        Args:
            module_id: ID of module
            
        Returns:
            True if module supports variable input nodes
            
        Raises:
            ValueError: If module not found
        """
        module = self.get_module(module_id)
        if not module:
            raise ValueError(f"Module not found: {module_id}")
        
        return module.supports_dynamic_inputs()
    
    def supports_dynamic_outputs(self, module_id: ModuleID) -> bool:
        """Check if module supports dynamic output nodes
        
        Args:
            module_id: ID of module
            
        Returns:
            True if module supports variable output nodes
            
        Raises:
            ValueError: If module not found
        """
        module = self.get_module(module_id)
        if not module:
            raise ValueError(f"Module not found: {module_id}")
        
        return module.supports_dynamic_outputs()

# Global registry instance
_registry: Optional[ModuleRegistry] = None

def get_module_registry() -> ModuleRegistry:
    """Get the global module registry instance"""
    global _registry
    if _registry is None:
        _registry = ModuleRegistry()
    return _registry

def populate_database_with_modules() -> bool:
    """Populate database with all registered modules
    
    Returns:
        True if successful, False otherwise
    """
    try:
        from ..database import get_unified_db_service, BaseModule
        
        db_service = get_unified_db_service()
        if not db_service:
            logger.error("Database service not available")
            return False
        
        registry = get_module_registry()
        modules_info = registry.get_all_module_info()
        
        if not modules_info:
            logger.warning("No modules found in registry")
            return False
        
        session = db_service.get_session()
        try:
            # Clear existing base modules
            deleted_count = session.query(BaseModule).delete()
            logger.info(f"Cleared {deleted_count} existing base modules from database")
            
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
            
    except ImportError as e:
        logger.error(f"Failed to import database components: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during database population: {e}")
        return False