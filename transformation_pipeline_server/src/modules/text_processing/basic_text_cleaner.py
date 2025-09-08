"""
Basic Text Cleaner Module for ETO Transformation Pipeline

Simple text cleaner with no configuration options.
"""

import json
import re
from typing import Dict, Any, List, Optional
from ...types import (
    ModuleID, ModuleInfo, ExecutionInputs, ExecutionConfig, 
    ExecutionOutputs, ExecutionNodeInfo, NodeSchema, NodeConfiguration
)
from ..module import BaseModuleExecutor, ModuleExecutionError


class BasicTextCleanerModule(BaseModuleExecutor):
    """Simple text cleaner with no configuration options"""
    
    def get_module_id(self) -> ModuleID:
        return "basic_text_cleaner"
    
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
        
        return {
            'id': 'basic_text_cleaner',
            'name': 'Basic Text Cleaner',
            'description': 'Simple text cleaner with no configuration options',
            'version': '1.0.0',
            'input_config': json.dumps(input_config),
            'output_config': json.dumps(output_config),
            'config_schema': json.dumps([]),  # No configuration options
            'service_endpoint': None,
            'handler_name': 'BasicTextCleanerModule',
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
        """Clean the input text"""
        try:
            # Validate inputs first
            self.validate_inputs(inputs)
            
            # Get the first (and only) input value
            input_values = list(inputs.values())
            if not input_values:
                raise ModuleExecutionError("No input text provided")
            
            input_text = str(input_values[0])
            
            # Basic cleaning operations
            cleaned_text = input_text.strip()
            
            # Normalize whitespace - replace multiple spaces/tabs/newlines with single spaces
            cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
            
            # Remove leading/trailing whitespace
            cleaned_text = cleaned_text.strip()
            
            self.logger.info(f"Text cleaned: {len(input_text)} -> {len(cleaned_text)} characters")
            
            # Get the first (and only) output node ID
            output_node_ids = [node['nodeId'] for node in node_info['outputs']]
            if not output_node_ids:
                raise ModuleExecutionError("No output node configured")
            
            return {
                output_node_ids[0]: cleaned_text
            }
            
        except Exception as e:
            self.logger.error(f"Text cleaning failed: {e}")
            raise ModuleExecutionError(f"Failed to clean text: {str(e)}")