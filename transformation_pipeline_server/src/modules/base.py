"""
Base Module System for ETO Transformation Pipeline

This module provides the base classes and interfaces for all transformation modules.
"""

import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class ModuleExecutionError(Exception):
    """Raised when a module fails to execute"""
    pass

class ModuleValidationError(Exception):
    """Raised when module input or config validation fails"""
    pass

class BaseModuleExecutor(ABC):
    """Abstract base class for all transformation pipeline modules"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
    
    @abstractmethod
    def get_module_id(self) -> str:
        """Return the unique module ID"""
        pass
    
    @abstractmethod
    def get_module_info(self) -> Dict[str, Any]:
        """Return the module template information for database storage"""
        pass
    
    @abstractmethod
    def execute(self, inputs: Dict[str, Any], config: Dict[str, Any], output_names: List[str] = None) -> Dict[str, Any]:
        """Execute the module with given inputs and configuration
        
        Args:
            inputs: Dictionary of input values keyed by input name
            config: Dictionary of configuration values keyed by config name
            output_names: List of expected output names (for variable output modules)
            
        Returns:
            Dictionary of output values keyed by output name
            
        Raises:
            ModuleExecutionError: If execution fails
        """
        pass
    
    def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        """Validate input data against module schema
        
        Args:
            inputs: Dictionary of input values to validate
            
        Returns:
            True if valid
            
        Raises:
            ModuleValidationError: If validation fails
        """
        module_info = self.get_module_info()
        input_schema = json.loads(module_info['input_schema'])
        
        # Check required inputs
        for input_def in input_schema:
            if input_def.get('required', False) and input_def['name'] not in inputs:
                raise ModuleValidationError(f"Required input '{input_def['name']}' is missing")
        
        # Validate input types (basic validation)
        for input_def in input_schema:
            input_name = input_def['name']
            if input_name in inputs:
                expected_type = input_def['type']
                value = inputs[input_name]
                
                if not self._validate_type(value, expected_type):
                    raise ModuleValidationError(
                        f"Input '{input_name}' expected type '{expected_type}' but got {type(value).__name__}"
                    )
        
        return True
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate configuration against module schema
        
        Args:
            config: Dictionary of config values to validate
            
        Returns:
            True if valid
            
        Raises:
            ModuleValidationError: If validation fails
        """
        module_info = self.get_module_info()
        config_schema_str = module_info.get('config_schema')
        if not config_schema_str:
            return True  # No config schema to validate against
            
        config_schema = json.loads(config_schema_str)
        
        # Check required config
        for config_def in config_schema:
            if config_def.get('required', False) and config_def['name'] not in config:
                raise ModuleValidationError(f"Required config '{config_def['name']}' is missing")
        
        return True
    
    def _validate_type(self, value: Any, expected_type: str) -> bool:
        """Validate a value against an expected type string"""
        if expected_type == 'string':
            return isinstance(value, str)
        elif expected_type == 'number':
            return isinstance(value, (int, float))
        elif expected_type == 'boolean':
            return isinstance(value, bool)
        elif expected_type == 'datetime':
            # For now, accept strings that could be datetime
            return isinstance(value, str)
        else:
            return True  # Unknown type, assume valid
    
    def get_safe_execution_context(self) -> Dict[str, Any]:
        """Get execution context info for logging/debugging"""
        return {
            'module_id': self.get_module_id(),
            'module_class': self.__class__.__name__
        }
    
    def get_dynamic_outputs(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate dynamic output schema based on configuration
        
        Override this method in modules that support variable outputs.
        
        Args:
            config: Current configuration values
            
        Returns:
            List of output definitions
        """
        # Default implementation returns static outputs from module info
        module_info = self.get_module_info()
        output_schema_str = module_info.get('output_schema', '[]')
        return json.loads(output_schema_str)
    
    def supports_dynamic_outputs(self) -> bool:
        """Check if this module supports dynamic outputs"""
        module_info = self.get_module_info()
        return module_info.get('dynamic_outputs', False)