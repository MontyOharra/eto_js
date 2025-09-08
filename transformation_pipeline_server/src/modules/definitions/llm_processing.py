"""
LLM Processing Modules for ETO Transformation Pipeline

This module contains LLM-based transformation modules that support variable inputs/outputs.
"""

import json
import re
from typing import Dict, Any, List
from ..module import BaseModuleExecutor, ModuleExecutionError

class VariableLLMModule(BaseModuleExecutor):
    """LLM module that can parse any number of inputs into any number of outputs"""
    
    def get_module_id(self) -> str:
        return "variable_llm"
    
    def get_module_info(self) -> Dict[str, Any]:
        """Return the module template information for database storage"""
        return {
            'id': 'variable_llm',
            'name': 'Variable LLM Parser',
            'description': 'Uses LLM to parse and transform data with configurable inputs and outputs',
            'version': '1.0.0',
            'input_schema': json.dumps([
                {
                    'name': 'input_1',
                    'type': 'string',
                    'description': 'First data input',
                    'required': True,
                    'dynamicType': {
                        'configKey': 'input_1_type',
                        'options': ['string', 'number', 'boolean', 'datetime']
                    }
                }
            ]),
            'output_schema': json.dumps([
                {
                    'name': 'output_1',
                    'type': 'string',
                    'description': 'Parsed output 1',
                    'dynamicType': {
                        'configKey': 'output_1_type',
                        'options': ['string', 'number', 'boolean', 'datetime']
                    }
                }
            ]),
            # Support unlimited variable inputs and outputs
            'max_inputs': None,
            'max_outputs': None,
            'dynamic_inputs': json.dumps({
                'enabled': True,
                'minNodes': 1,
                'maxNodes': 10,
                'defaultTemplate': {
                    'name': 'input_{{index}}',
                    'type': 'string',
                    'description': 'Data input {{index}}',
                    'required': False,
                    'dynamicType': {
                        'configKey': 'input_{{index}}_type',
                        'options': ['string', 'number', 'boolean', 'datetime']
                    }
                },
                'allowTypeConfiguration': True
            }),
            'dynamic_outputs': json.dumps({
                'enabled': True,
                'minNodes': 1,
                'maxNodes': 10,
                'defaultTemplate': {
                    'name': 'output_{{index}}',
                    'type': 'string',
                    'description': 'Parsed output {{index}}',
                    'dynamicType': {
                        'configKey': 'output_{{index}}_type',
                        'options': ['string', 'number', 'boolean', 'datetime']
                    }
                },
                'allowTypeConfiguration': True
            }),
            'color': '#7C3AED',  # Purple for LLM processing
            'category': 'LLM Processing',
            'config_schema': json.dumps([
                # Hidden config fields for dynamic types (controlled by UI dropdowns)
                {
                    'name': 'input_1_type',
                    'type': 'select',
                    'description': 'Type for input 1',
                    'required': True,
                    'defaultValue': 'string',
                    'options': ['string', 'number', 'boolean', 'datetime'],
                    'hidden': True
                },
                {
                    'name': 'output_1_type',
                    'type': 'select',
                    'description': 'Type for output 1',
                    'required': True,
                    'defaultValue': 'string',
                    'options': ['string', 'number', 'boolean', 'datetime'],
                    'hidden': True
                },
                # Visible configuration
                {
                    'name': 'llm_prompt',
                    'type': 'textarea',
                    'description': 'LLM prompt template for parsing (use {{input_name}} placeholders)',
                    'required': True,
                    'defaultValue': 'Parse the following data and extract the requested fields:\\n\\nInput: {{input_1}}\\n\\nExtract: {{output_1}}',
                    'placeholder': 'Enter your LLM prompt template...'
                },
                {
                    'name': 'model',
                    'type': 'select',
                    'description': 'LLM model to use',
                    'required': True,
                    'defaultValue': 'gpt-3.5-turbo',
                    'options': ['gpt-3.5-turbo', 'gpt-4', 'claude-3-haiku', 'claude-3-sonnet']
                },
                {
                    'name': 'temperature',
                    'type': 'number',
                    'description': 'LLM temperature (0.0 to 1.0)',
                    'required': False,
                    'defaultValue': 0.1
                }
            ]),
            'service_endpoint': None,
            'handler_name': 'VariableLLMModule',
            'is_active': True
        }
    
    def execute(self, inputs: Dict[str, Any], config: Dict[str, Any], output_names: List[str] = None) -> Dict[str, Any]:
        """Execute LLM parsing with variable inputs and outputs"""
        try:
            # Validate inputs and config
            self.validate_inputs(inputs)
            self.validate_config(config)
            
            llm_prompt = config.get('llm_prompt', '')
            model = config.get('model', 'gpt-3.5-turbo')
            temperature = float(config.get('temperature', 0.1))
            
            # Get expected output names from the frontend
            expected_outputs = output_names or ['output_1']
            
            # Replace placeholders in prompt with actual input values
            processed_prompt = llm_prompt
            for input_name, input_value in inputs.items():
                placeholder = f'{{{{{input_name}}}}}'
                processed_prompt = processed_prompt.replace(placeholder, str(input_value))
            
            # For now, simulate LLM processing (in real implementation, call actual LLM API)
            self.logger.info(f"Simulating LLM call with model: {model}, temperature: {temperature}")
            self.logger.info(f"Prompt: {processed_prompt}")
            
            # Simulate LLM response based on the prompt and expected outputs
            result = {}
            for i, output_name in enumerate(expected_outputs):
                # Simple simulation - in real implementation, parse LLM response
                if 'hawb' in output_name.lower():
                    result[output_name] = 'HAW123456789'
                elif 'mawb' in output_name.lower():
                    result[output_name] = 'MAW987654321'
                elif 'carrier' in output_name.lower():
                    result[output_name] = 'Forward Air Inc'
                elif 'weight' in output_name.lower():
                    result[output_name] = '25.5'
                else:
                    # Generic extraction based on input
                    first_input_value = list(inputs.values())[0] if inputs else ''
                    words = str(first_input_value).split()
                    if i < len(words):
                        result[output_name] = words[i]
                    else:
                        result[output_name] = f'extracted_{output_name}_{i+1}'
            
            self.logger.info(f"LLM parsing completed: {len(inputs)} inputs -> {len(result)} outputs")
            
            return result
            
        except Exception as e:
            self.logger.error(f"LLM parsing failed: {e}")
            raise ModuleExecutionError(f"Failed to parse with LLM: {str(e)}")
