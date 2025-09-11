"""
Advanced Text Cleaner Module for ETO Transformation Pipeline

Advanced text cleaner with configurable cleaning options.
"""

import json
import re
from typing import Dict, Any, List, Optional
from ....types import (
    ModuleID, ModuleInfo, ExecutionInputs, ExecutionConfig, 
    ExecutionOutputs, ExecutionNodeInfo, NodeSchema, NodeConfiguration, ConfigSchema
)
from ...module import BaseModuleExecutor, ModuleExecutionError


class AdvancedTextCleanerModule(BaseModuleExecutor):
    """Advanced text cleaner with configuration options"""
    
    def get_module_id(self) -> ModuleID:
        return "advanced_text_cleaner"
    
    def get_module_info(self) -> ModuleInfo:
        """Return the module template information for database storage"""
        
        # Input configuration - single text input
        input_config: NodeConfiguration = {
            "nodes": [
                {
                    "defaultName": "input_text",
                    "type": "string"
                }
            ],
            "dynamic": None,  # Static node count
            "allowedTypes": ["string"]  # Only string inputs allowed
        }
        
        # Output configuration - single cleaned text output
        output_config: NodeConfiguration = {
            "nodes": [
                {
                    "defaultName": "cleaned_text",
                    "type": "string"
                }
            ],
            "dynamic": None,  # Static node count
            "allowedTypes": ["string"]  # Only string outputs
        }
        
        # Configuration schema
        config_schema: List[ConfigSchema] = [
            {
                "name": "remove_special_chars",
                "type": "boolean",
                "description": "Remove special characters",
                "required": False,
                "defaultValue": False
            },
            {
                "name": "convert_to_lowercase",
                "type": "boolean", 
                "description": "Convert text to lowercase",
                "required": False,
                "defaultValue": False
            },
            {
                "name": "remove_extra_spaces",
                "type": "boolean",
                "description": "Remove extra whitespace",
                "required": False,
                "defaultValue": True
            },
            {
                "name": "custom_replacements",
                "type": "textarea",
                "description": "Custom text replacements (JSON format: {\"old\": \"new\"})",
                "required": False,
                "defaultValue": ""
            }
        ]
        
        return {
            'id': 'advanced_text_cleaner',
            'name': 'Advanced Text Cleaner',
            'description': 'Advanced text cleaner with configurable cleaning options',
            'version': '1.0.0',
            'input_config': json.dumps(input_config),
            'output_config': json.dumps(output_config),
            'config_schema': json.dumps(config_schema),
            'service_endpoint': None,
            'handler_name': 'AdvancedTextCleanerModule',
            'color': '#3B82F6',
            'category': 'Text Processing',
            'is_active': True
        }
    
    def execute(
        self, 
        inputs: ExecutionInputs, 
        config: ExecutionConfig,
        node_info: ExecutionNodeInfo,
        output_names: Optional[List[str]] = None
    ) -> ExecutionOutputs:
        """Clean the input text with advanced options"""
        try:
            # Validate inputs and config
            self.validate_inputs(inputs)
            self.validate_config(config)
            
            # Get the first (and only) input value
            input_values = list(inputs.values())
            if not input_values:
                raise ModuleExecutionError("No input text provided")
            
            input_text = str(input_values[0])
            cleaned_text = input_text
            
            # Apply custom replacements first if provided
            custom_replacements = config.get('custom_replacements', '')
            if custom_replacements:
                try:
                    replacements = json.loads(custom_replacements)
                    for old, new in replacements.items():
                        cleaned_text = cleaned_text.replace(old, new)
                except json.JSONDecodeError:
                    self.logger.warning("Invalid JSON in custom_replacements config, skipping")
            
            # Convert to lowercase if requested
            if config.get('convert_to_lowercase', False):
                cleaned_text = cleaned_text.lower()
            
            # Remove special characters if requested
            if config.get('remove_special_chars', False):
                # Keep only alphanumeric characters, spaces, and basic punctuation
                cleaned_text = re.sub(r'[^a-zA-Z0-9\s\.\,\!\?\-]', '', cleaned_text)
            
            # Remove extra spaces (default behavior)
            if config.get('remove_extra_spaces', True):
                cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
                cleaned_text = cleaned_text.strip()
            
            self.logger.info(f"Advanced text cleaned: {len(input_text)} -> {len(cleaned_text)} characters")
            
            # Get the first (and only) output node ID
            output_node_ids = [node['nodeId'] for node in node_info['outputs']]
            if not output_node_ids:
                raise ModuleExecutionError("No output node configured")
            
            return ExecutionOutputs({
                output_node_ids[0]: cleaned_text
            })
            
        except Exception as e:
            self.logger.error(f"Advanced text cleaning failed: {e}")
            raise ModuleExecutionError(f"Failed to clean text: {str(e)}")