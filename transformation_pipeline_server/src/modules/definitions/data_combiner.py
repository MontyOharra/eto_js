import json
import re
from typing import Dict, Any, List
from ..module import BaseModuleExecutor, ModuleExecutionError

class DataCombinerModule(BaseModuleExecutor):
    """Data combiner that matches the frontend test module exactly"""
    
    def get_module_id(self) -> str:
        return "data_combiner"
    
    def get_module_info(self) -> Dict[str, Any]:
        """Return the module template information for database storage"""
        return {
            'id': 'data_combiner',
            'name': 'Data Combiner',
            'description': 'Combines multiple data inputs into outputs with configurable types',
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
                    'description': 'Combined data output',
                    'dynamicType': {
                        'configKey': 'output_1_type',
                        'options': ['string', 'number', 'boolean', 'datetime']
                    }
                }
            ]),
            'max_inputs': None,  # Variable inputs
            'max_outputs': None,  # Variable outputs
            'dynamic_inputs': json.dumps({
                'enabled': True,
                'minNodes': 1,
                'maxNodes': 8,
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
                'maxNodes': 5,
                'defaultTemplate': {
                    'name': 'output_{{index}}',
                    'type': 'string',
                    'description': 'Combined output {{index}}',
                    'dynamicType': {
                        'configKey': 'output_{{index}}_type',
                        'options': ['string', 'number', 'boolean', 'datetime']
                    }
                },
                'allowTypeConfiguration': True
            }),
            'color': '#0EA5E9',  # Sky blue
            'category': 'Data Processing',
            'config_schema': json.dumps([
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
                {
                    'name': 'combination_method',
                    'type': 'select',
                    'description': 'How to combine the input data',
                    'required': True,
                    'defaultValue': 'concatenate',
                    'options': ['concatenate', 'sum', 'average', 'first_non_empty', 'custom']
                }
            ]),
            'service_endpoint': None,
            'handler_name': 'DataCombinerModule',
            'is_active': True
        }
    
    def execute(self, inputs: Dict[str, Any], config: Dict[str, Any], output_names: List[str]) -> Dict[str, Any]:
        """Combine multiple inputs into outputs"""
        try:
            # Validate inputs and config
            self.validate_inputs(inputs)
            self.validate_config(config)
            
            combination_method = config.get('combination_method', 'concatenate')
            expected_outputs = output_names or ['output_1']
            
            # Get all input values
            input_values = list(inputs.values())
            
            # Combine data based on method
            result = {}
            for output_name in expected_outputs:
                if combination_method == 'concatenate':
                    result[output_name] = ' '.join(str(val) for val in input_values)
                elif combination_method == 'sum':
                    try:
                        result[output_name] = str(sum(float(val) for val in input_values if val))
                    except (ValueError, TypeError):
                        result[output_name] = str(sum(len(str(val)) for val in input_values))
                elif combination_method == 'average':
                    try:
                        numeric_values = [float(val) for val in input_values if val]
                        result[output_name] = str(sum(numeric_values) / len(numeric_values)) if numeric_values else '0'
                    except (ValueError, TypeError):
                        result[output_name] = str(sum(len(str(val)) for val in input_values) / len(input_values))
                elif combination_method == 'first_non_empty':
                    result[output_name] = next((str(val) for val in input_values if val), '')
                else:
                    # Default to concatenate
                    result[output_name] = ' '.join(str(val) for val in input_values)
            
            self.logger.info(f"Data combined: {len(inputs)} inputs -> {len(result)} outputs using {combination_method}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Data combination failed: {e}")
            raise ModuleExecutionError(f"Failed to combine data: {str(e)}")