"""
Base Module System for ETO Transformation Pipeline

This module provides the base classes and interfaces for all transformation modules.
"""

import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from ..types import (
    ModuleID, ModuleInfo, NodeSchema, NodeConfiguration, ExecutionInputs, 
    ExecutionConfig, ExecutionOutputs, NodeType, ExecutionNodeInfo, NodeTypeInfo,
    ModuleExecutionError, ModuleValidationError
)

logger = logging.getLogger(__name__)

class BaseModuleExecutor(ABC):
    """Abstract base class for all transformation pipeline modules"""
    
    def __init__(self) -> None:
        self.logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
    
    @abstractmethod
    def get_module_id(self) -> ModuleID:
        """Return the unique module ID"""
        pass
    
    @abstractmethod
    def get_module_info(self) -> ModuleInfo:
        """Return the module template information for database storage"""
        pass
    
    @abstractmethod
    def execute(
        self, 
        inputs: ExecutionInputs, 
        config: ExecutionConfig, 
        node_info: ExecutionNodeInfo,
        output_names: Optional[List[str]] = None
    ) -> ExecutionOutputs:
        """Execute the module with given inputs and configuration
        
        Args:
            inputs: Dictionary of input values keyed by node ID
            config: Dictionary of configuration values keyed by config name
            node_info: Information about input/output node IDs and their types
            output_names: List of expected output node IDs (for variable output modules)
            
        Returns:
            Dictionary of output values keyed by node ID
            
        Raises:
            ModuleExecutionError: If execution fails
        """
        pass
    
    def validate_inputs(self, inputs: ExecutionInputs) -> bool:
        """Validate actual runtime input data against module constraints
        
        Args:
            inputs: Dictionary of input values to validate
            
        Returns:
            True if valid
            
        Raises:
            ModuleValidationError: If validation fails
        """
        module_info = self.get_module_info()
        input_config = json.loads(module_info['input_config'])
        
        # 1. Ensure at least one input is present
        if len(inputs) == 0:
            raise ModuleValidationError("Module must have at least one input")
        
        # 2. Validate node count constraints
        if input_config['dynamic'] is None:
            # Static module - must match base nodes count exactly
            expected_count = len(input_config['nodes'])
            if len(inputs) != expected_count:
                raise ModuleValidationError(f"Static module expects exactly {expected_count} inputs, got {len(inputs)}")
        else:
            # Dynamic module - check max limit
            max_nodes = input_config['dynamic']['maxNodes']
            if max_nodes is not None and len(inputs) > max_nodes:
                raise ModuleValidationError(f"Too many inputs: {len(inputs)}, max allowed: {max_nodes}")
        
        # 3. Validate actual data types against allowedTypes
        allowed_types = input_config['allowedTypes']
        if allowed_types:  # If not empty, enforce type restrictions
            for node_id, value in inputs.items():
                if not self._validate_value_against_allowed_types(value, allowed_types):
                    actual_type = type(value).__name__
                    raise ModuleValidationError(
                        f"Input '{node_id}' has invalid type '{actual_type}'. Allowed types: {allowed_types}"
                    )
        
        return True
    
    def validate_config(self, config: ExecutionConfig) -> bool:
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
        
        # Check required config options
        for config_def in config_schema:
            if config_def.get('required', False) and config_def['name'] not in config:
                raise ModuleValidationError(f"Required config '{config_def['name']}' is missing")
        
        # Validate config option types and values
        for config_def in config_schema:
            config_name = config_def['name']
            if config_name in config:
                expected_type = config_def['type']
                value = config[config_name]
                
                # Basic type validation for config values
                if not self._validate_config_type(value, expected_type):
                    raise ModuleValidationError(
                        f"Config '{config_name}' expected type '{expected_type}' but got {type(value).__name__}"
                    )
                
                # Validate select options if provided
                if expected_type == 'select' and 'options' in config_def:
                    if value not in config_def['options']:
                        raise ModuleValidationError(
                            f"Config '{config_name}' value '{value}' not in allowed options: {config_def['options']}"
                        )
        
        return True
    
    def validate_outputs(self, outputs: ExecutionOutputs, output_names: Optional[List[str]] = None) -> bool:
        """Validate actual runtime output data against module constraints
        
        Args:
            outputs: Dictionary of output values to validate
            output_names: Expected output names (for variable output modules)
            
        Returns:
            True if valid
            
        Raises:
            ModuleValidationError: If validation fails
        """
        module_info = self.get_module_info()
        output_config = json.loads(module_info['output_config'])
        
        # 1. Ensure at least one output is present
        if len(outputs) == 0:
            raise ModuleValidationError("Module must produce at least one output")
        
        # 2. Validate node count constraints
        if output_config['dynamic'] is None:
            # Static module - must match base nodes count exactly
            expected_count = len(output_config['nodes'])
            if len(outputs) != expected_count:
                raise ModuleValidationError(f"Static module expects exactly {expected_count} outputs, got {len(outputs)}")
        else:
            # Dynamic module - validate against expected output_names if provided
            if output_names is not None:
                if len(outputs) != len(output_names):
                    raise ModuleValidationError(f"Expected {len(output_names)} outputs, got {len(outputs)}")
            
            # Check max limit
            max_nodes = output_config['dynamic']['maxNodes']
            if max_nodes is not None and len(outputs) > max_nodes:
                raise ModuleValidationError(f"Too many outputs: {len(outputs)}, max allowed: {max_nodes}")
        
        # 3. Validate actual data types against allowedTypes
        allowed_types = output_config['allowedTypes']
        if allowed_types:  # If not empty, enforce type restrictions
            for node_id, value in outputs.items():
                if not self._validate_value_against_allowed_types(value, allowed_types):
                    actual_type = type(value).__name__
                    raise ModuleValidationError(
                        f"Output '{node_id}' has invalid type '{actual_type}'. Allowed types: {allowed_types}"
                    )
        
        return True
    
    def execute_with_validation(
        self, 
        inputs: ExecutionInputs, 
        config: ExecutionConfig, 
        node_info: ExecutionNodeInfo,
        output_names: Optional[List[str]] = None
    ) -> ExecutionOutputs:
        """Execute module with full input and output validation
        
        This is a safe wrapper around the execute method that validates:
        1. Input data against module schema
        2. Configuration against module schema
        3. Output data against module schema
        
        Args:
            inputs: Dictionary of input values keyed by input name
            config: Dictionary of configuration values keyed by config name
            output_names: List of expected output names (for variable output modules)
            
        Returns:
            Dictionary of output values keyed by output name
            
        Raises:
            ModuleValidationError: If validation fails
            ModuleExecutionError: If execution fails
        """
        # Validate inputs first
        try:
            self.validate_inputs(inputs)
        except ModuleValidationError as e:
            self.logger.error(f"Input validation failed for {self.get_module_id()}: {e}")
            raise
        
        # Validate configuration
        try:
            self.validate_config(config)
        except ModuleValidationError as e:
            self.logger.error(f"Config validation failed for {self.get_module_id()}: {e}")
            raise
        
        # Execute the module
        try:
            self.logger.info(f"Executing module {self.get_module_id()} with validated inputs and config")
            outputs = self.execute(inputs, config, node_info, output_names)
        except Exception as e:
            self.logger.error(f"Execution failed for {self.get_module_id()}: {e}")
            if isinstance(e, ModuleExecutionError):
                raise
            else:
                raise ModuleExecutionError(f"Module execution failed: {str(e)}")
        
        # Validate outputs
        try:
            self.validate_outputs(outputs, output_names)
            # Also validate that runtime types match expected node types
            self.validate_runtime_types(inputs, outputs, node_info)
        except ModuleValidationError as e:
            self.logger.error(f"Output validation failed for {self.get_module_id()}: {e}")
            raise
        
        self.logger.info(f"Module {self.get_module_id()} executed successfully with validated outputs")
        return outputs
    
    def _validate_type(self, value: Any, expected_type: NodeType) -> bool:
        """Validate a value against an expected type string
        
        Args:
            value: The value to validate
            expected_type: Expected NodeType ('string', 'number', 'boolean', 'datetime')
            
        Returns:
            True if value matches expected type
        """
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
    
    def _validate_value_against_allowed_types(self, value: Any, allowed_types: List[NodeType]) -> bool:
        """Validate a value against a list of allowed types
        
        Args:
            value: The value to validate
            allowed_types: List of allowed NodeTypes
            
        Returns:
            True if value matches any allowed type
        """
        if not allowed_types:  # Empty list = all types allowed
            return True
        
        for allowed_type in allowed_types:
            if self._validate_type(value, allowed_type):
                return True
        return False
    
    def _validate_config_type(self, value: Any, expected_type: str) -> bool:
        """Validate a configuration value against an expected type
        
        Args:
            value: The value to validate
            expected_type: Expected config type ('string', 'number', 'boolean', 'select', 'textarea')
            
        Returns:
            True if value matches expected type
        """
        if expected_type in ['string', 'textarea', 'select']:
            return isinstance(value, str)
        elif expected_type == 'number':
            return isinstance(value, (int, float))
        elif expected_type == 'boolean':
            return isinstance(value, bool)
        else:
            return True  # Unknown type, assume valid
    
    def validate_runtime_types(self, inputs: ExecutionInputs, outputs: ExecutionOutputs, node_info: ExecutionNodeInfo) -> bool:
        """Validate that runtime values match their expected node types
        
        Args:
            inputs: Input values to validate
            outputs: Output values to validate  
            node_info: Node type information
            
        Returns:
            True if all values match their expected types
            
        Raises:
            ModuleValidationError: If type validation fails
        """
        # Validate input types match expected node types
        for node_type_info in node_info['inputs']:
            node_id = node_type_info['nodeId'] 
            expected_type = node_type_info['type']
            
            if node_id in inputs:
                value = inputs[node_id]
                if not self._validate_type(value, expected_type):
                    raise ModuleValidationError(
                        f"Input node '{node_id}' expected type '{expected_type}' but got {type(value).__name__}"
                    )
        
        # Validate output types match expected node types  
        for node_type_info in node_info['outputs']:
            node_id = node_type_info['nodeId']
            expected_type = node_type_info['type']
            
            if node_id in outputs:
                value = outputs[node_id]
                if not self._validate_type(value, expected_type):
                    raise ModuleValidationError(
                        f"Output node '{node_id}' expected type '{expected_type}' but got {type(value).__name__}"
                    )
        
        return True
    
    def resolve_config_template(self, template: str, node_info: ExecutionNodeInfo) -> str:
        """Resolve placeholder references in config templates
        
        Args:
            template: Template string with {input_X} and {output_X} placeholders
            node_info: Node information for mapping placeholders to actual node IDs
            
        Returns:
            Resolved template string with actual node IDs
        """
        resolved = template
        
        # Replace input placeholders: {input_0}, {input_1}, etc.
        for i, input_node in enumerate(node_info['inputs']):
            placeholder = f"{{input_{i}}}"
            resolved = resolved.replace(placeholder, input_node['nodeId'])
        
        # Replace output placeholders: {output_0}, {output_1}, etc.  
        for i, output_node in enumerate(node_info['outputs']):
            placeholder = f"{{output_{i}}}"
            resolved = resolved.replace(placeholder, output_node['nodeId'])
        
        return resolved
    
    def validate_config_template_references(self, config: ExecutionConfig, node_info: ExecutionNodeInfo) -> bool:
        """Validate that config templates reference valid nodes
        
        Args:
            config: Configuration values to check
            node_info: Available node information
            
        Returns:
            True if all template references are valid
            
        Raises:
            ModuleValidationError: If template references invalid nodes
        """
        # Override in subclasses that use config templates
        return True
    
    def get_safe_execution_context(self) -> Dict[str, Any]:
        """Get execution context info for logging/debugging
        
        Returns:
            Dictionary with module identification info for safe logging
        """
        return {
            'module_id': self.get_module_id(),
            'module_class': self.__class__.__name__
        }
    
    def get_dynamic_input_template(self, config: ExecutionConfig) -> Optional[NodeSchema]:
        """Get template for creating new dynamic input nodes
        
        Args:
            config: Current configuration values
            
        Returns:
            NodeSchema template for new nodes, or None if not dynamic
        """
        module_info = self.get_module_info()
        input_config = json.loads(module_info['input_config'])
        
        if input_config['dynamic'] is None:
            return None
        
        return input_config['dynamic']['defaultNode']
    
    def get_dynamic_output_template(self, config: ExecutionConfig) -> Optional[NodeSchema]:
        """Get template for creating new dynamic output nodes
        
        Args:
            config: Current configuration values
            
        Returns:
            NodeSchema template for new nodes, or None if not dynamic
        """
        module_info = self.get_module_info()
        output_config = json.loads(module_info['output_config'])
        
        if output_config['dynamic'] is None:
            return None
        
        return output_config['dynamic']['defaultNode']
    
    def get_base_input_nodes(self) -> List[NodeSchema]:
        """Get base input nodes that are created when module is instantiated
        
        Returns:
            List of base input node schemas
        """
        module_info = self.get_module_info()
        input_config = json.loads(module_info['input_config'])
        return input_config['nodes']
    
    def get_base_output_nodes(self) -> List[NodeSchema]:
        """Get base output nodes that are created when module is instantiated
        
        Returns:
            List of base output node schemas
        """
        module_info = self.get_module_info()
        output_config = json.loads(module_info['output_config'])
        return output_config['nodes']
    
    def supports_dynamic_inputs(self) -> bool:
        """Check if this module supports dynamic input nodes
        
        Returns:
            True if module supports variable input nodes
        """
        module_info = self.get_module_info()
        input_config = json.loads(module_info['input_config'])
        return input_config['dynamic'] is not None
    
    def supports_dynamic_outputs(self) -> bool:
        """Check if this module supports dynamic output nodes
        
        Returns:
            True if module supports variable output nodes
        """
        module_info = self.get_module_info()
        output_config = json.loads(module_info['output_config'])
        return output_config['dynamic'] is not None