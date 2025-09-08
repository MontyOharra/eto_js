"""
Type Converter Module for ETO Transformation Pipeline

Converts between different data types based on node type selectors.
Uses the clever approach where conversion types are determined by the actual
node types rather than configuration options.
"""

import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from ....types import (
    ModuleID, ModuleInfo, ExecutionInputs, ExecutionConfig, 
    ExecutionOutputs, ExecutionNodeInfo, NodeSchema, NodeConfiguration, 
    ConfigSchema, NodeType
)
from ...module import BaseModuleExecutor, ModuleExecutionError


class TypeConverterModule(BaseModuleExecutor):
    """Type converter that uses node type selectors to determine conversion"""
    
    def get_module_id(self) -> ModuleID:
        return "type_converter"
    
    def get_module_info(self) -> ModuleInfo:
        """Return the module template information for database storage"""
        
        # Input configuration - dynamic inputs that accept any type
        input_config: NodeConfiguration = {
            "nodes": [
                {
                    "defaultName": "input_value",
                    "type": "string"  # Default to string, but user can change
                }
            ],
            "dynamic": {
                "maxNodes": 10,
                "defaultNode": {
                    "defaultName": "input_value",
                    "type": "string"
                }
            },
            "allowedTypes": []  # Empty = all types allowed
        }
        
        # Output configuration - dynamic outputs that can be any type
        output_config: NodeConfiguration = {
            "nodes": [
                {
                    "defaultName": "converted_value",
                    "type": "string"  # Default to string, but user can change
                }
            ],
            "dynamic": {
                "maxNodes": 10,
                "defaultNode": {
                    "defaultName": "converted_value", 
                    "type": "string"
                }
            },
            "allowedTypes": []  # Empty = all types allowed
        }
        
        # Configuration schema - minimal, just error handling
        config_schema: List[ConfigSchema] = [
            {
                "name": "error_handling",
                "type": "select",
                "description": "How to handle conversion errors",
                "required": False,
                "defaultValue": "skip",
                "options": ["skip", "error", "default_value"]
            },
            {
                "name": "default_value",
                "type": "string",
                "description": "Default value to use when conversion fails (if error_handling is 'default_value')",
                "required": False,
                "defaultValue": ""
            }
        ]
        
        return {
            'id': 'type_converter',
            'name': 'Type Converter',
            'description': 'Converts between different data types based on node type selectors',
            'version': '1.0.0',
            'input_config': json.dumps(input_config),
            'output_config': json.dumps(output_config),
            'config_schema': json.dumps(config_schema),
            'service_endpoint': None,
            'handler_name': 'TypeConverterModule',
            'color': '#8B5CF6',
            'category': 'Data Processing',
            'is_active': True
        }
    
    def execute(
        self, 
        inputs: ExecutionInputs, 
        config: ExecutionConfig,
        node_info: ExecutionNodeInfo,
        output_names: Optional[List[str]] = None
    ) -> ExecutionOutputs:
        """Convert input values to output types based on node type selectors"""
        try:
            # Validate inputs and config
            self.validate_inputs(inputs)
            self.validate_config(config)
            
            error_handling = config.get('error_handling', 'skip')
            default_value = config.get('default_value', '')
            
            # Create mapping of input node IDs to their types
            input_types = {node['nodeId']: node['type'] for node in node_info['inputs']}
            output_types = {node['nodeId']: node['type'] for node in node_info['outputs']}
            
            results: ExecutionOutputs = ExecutionOutputs({})
            
            # Process each output node
            for output_node in node_info['outputs']:
                output_node_id = output_node['nodeId']
                target_type = output_node['type']
                
                # For each output, try to convert from corresponding input
                # Match by index if possible, otherwise use first available input
                output_index = next(
                    (i for i, node in enumerate(node_info['outputs']) if node['nodeId'] == output_node_id), 
                    0
                )
                
                # Get corresponding input (by index if available)
                if output_index < len(node_info['inputs']):
                    input_node = node_info['inputs'][output_index]
                    input_node_id = input_node['nodeId']
                    source_type = input_node['type']
                else:
                    # Use first available input
                    input_node = node_info['inputs'][0] if node_info['inputs'] else None
                    if not input_node:
                        if error_handling == 'error':
                            raise ModuleExecutionError(f"No input available for output {output_node_id}")
                        continue
                    input_node_id = input_node['nodeId']
                    source_type = input_node['type']
                
                # Get input value
                if input_node_id not in inputs:
                    if error_handling == 'error':
                        raise ModuleExecutionError(f"Missing input value for {input_node_id}")
                    continue
                
                input_value = inputs[input_node_id]
                
                # Convert value
                try:
                    converted_value = self._convert_value(input_value, source_type, target_type)
                    results[output_node_id] = converted_value
                    
                    self.logger.info(
                        f"Converted {input_node_id} ({source_type}) -> {output_node_id} ({target_type}): "
                        f"{input_value} -> {converted_value}"
                    )
                    
                except Exception as e:
                    if error_handling == 'error':
                        raise ModuleExecutionError(
                            f"Failed to convert {input_value} from {source_type} to {target_type}: {e}"
                        )
                    elif error_handling == 'default_value':
                        results[output_node_id] = default_value
                        self.logger.warning(
                            f"Conversion failed for {input_node_id} -> {output_node_id}, using default: {e}"
                        )
                    # If 'skip', just don't add to results
            
            return results
            
        except Exception as e:
            self.logger.error(f"Type conversion failed: {e}")
            raise ModuleExecutionError(f"Failed to convert types: {str(e)}")
    
    def _convert_value(self, value: Any, source_type: NodeType, target_type: NodeType) -> Any:
        """Convert a value from source type to target type"""
        
        # If types are the same, no conversion needed
        if source_type == target_type:
            return value
        
        # Convert to string
        if target_type == 'string':
            return str(value)
        
        # Convert to number
        elif target_type == 'number':
            if isinstance(value, (int, float)):
                return value
            elif isinstance(value, str):
                # Try int first, then float
                try:
                    return int(value)
                except ValueError:
                    return float(value)
            elif isinstance(value, bool):
                return 1 if value else 0
            else:
                raise ValueError(f"Cannot convert {type(value).__name__} to number")
        
        # Convert to boolean
        elif target_type == 'boolean':
            if isinstance(value, bool):
                return value
            elif isinstance(value, str):
                return value.lower() in ('true', '1', 'yes', 'on', 'enabled')
            elif isinstance(value, (int, float)):
                return value != 0
            else:
                raise ValueError(f"Cannot convert {type(value).__name__} to boolean")
        
        # Convert to datetime
        elif target_type == 'datetime':
            if isinstance(value, str):
                # Try common datetime formats
                formats = [
                    '%Y-%m-%d %H:%M:%S',
                    '%Y-%m-%d',
                    '%m/%d/%Y',
                    '%d/%m/%Y',
                    '%Y-%m-%dT%H:%M:%S',
                    '%Y-%m-%dT%H:%M:%SZ'
                ]
                
                for fmt in formats:
                    try:
                        dt = datetime.strptime(value, fmt)
                        return dt.isoformat()
                    except ValueError:
                        continue
                
                # If no format worked, try parsing as timestamp
                try:
                    timestamp = float(value)
                    dt = datetime.fromtimestamp(timestamp)
                    return dt.isoformat()
                except ValueError:
                    raise ValueError(f"Cannot parse '{value}' as datetime")
            else:
                raise ValueError(f"Cannot convert {type(value).__name__} to datetime")
        
        else:
            raise ValueError(f"Unknown target type: {target_type}")