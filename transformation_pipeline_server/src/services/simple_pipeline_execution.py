"""
Simple Pipeline Execution Service

Clean, simplified pipeline execution that:
1. Takes analyzed transformation steps
2. Takes input data dictionary
3. Takes output field names list
4. Executes transformations step by step
5. Returns final output dictionary
"""

import logging
from typing import Dict, List, Any
from ..modules import get_module_registry

logger = logging.getLogger(__name__)


class SimplePipelineExecutor:
    """
    Simple pipeline executor that takes analyzed steps and executes them
    """
    
    def __init__(self):
        self.logger = logger
        self.module_registry = get_module_registry()
        
    def execute_pipeline(
        self,
        transformation_steps: List[Dict[str, Any]],
        input_data: Dict[str, Any],
        field_mappings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute pipeline with analyzed transformation steps using field names directly
        
        Args:
            transformation_steps: List of transformation steps (from analysis)
            input_data: Dictionary of user field names to values
            field_mappings: Simple field mapping information
            
        Returns:
            Dictionary with final output field values
        """
        
        self.logger.info(f"Executing pipeline with {len(transformation_steps)} steps")
        self.logger.info(f"Input data: {input_data}")
        
        # Use input data directly as our data store
        data_store = input_data.copy()
        self.logger.info(f"Data store: {data_store}")
        
        try:
            # Execute each transformation step using field names directly
            for step in transformation_steps:
                step_number = step['step_number']
                template_id = step['template_id']
                input_field_name = step['input_field_name']
                output_field_name = step['output_field_name']
                config = step.get('config', {})
                
                self.logger.info(f"Step {step_number}: {input_field_name} -> [{template_id}] -> {output_field_name}")
                
                # Get input value using field name directly
                if input_field_name not in data_store:
                    raise ValueError(f"Input field '{input_field_name}' not found in data store. Available: {list(data_store.keys())}")
                
                input_value = data_store[input_field_name]
                self.logger.info(f"  Input: {input_field_name} = '{input_value}'")
                
                # Prepare module inputs
                module_inputs = self._prepare_module_inputs(template_id, input_field_name, input_value)
                
                # Execute the module
                outputs = self.module_registry.execute_module(template_id, module_inputs, config)
                
                # Extract the output value
                output_value = self._extract_module_output(template_id, outputs, output_field_name)
                
                # Store the result using field name directly
                data_store[output_field_name] = output_value
                self.logger.info(f"  Output: {output_field_name} = '{output_value}'")
            
            # Extract final outputs based on output field mapping
            output_field_mapping = field_mappings.get('output_fields', {})
            final_outputs = {}
            
            for field_name in output_field_mapping:
                if field_name in data_store:
                    final_outputs[field_name] = data_store[field_name]
            
            self.logger.info(f"Pipeline execution completed successfully")
            self.logger.info(f"Final outputs: {final_outputs}")
            
            return final_outputs
            
        except Exception as e:
            self.logger.error(f"Pipeline execution failed: {e}")
            raise
    
    def _prepare_module_inputs(
        self,
        template_id: str,
        input_field_name: str,
        input_value: Any
    ) -> Dict[str, Any]:
        """
        Prepare inputs for module execution by mapping to the module's expected input field names
        
        Args:
            template_id: Module template ID
            input_field_name: Our internal field name
            input_value: The value to pass
            
        Returns:
            Dictionary with module's expected input field names
        """
        
        # Get the module to find its expected input field names
        module = self.module_registry.get_module(template_id)
        if not module:
            raise ValueError(f"Module not found: {template_id}")
        
        # Get module's input schema
        import json
        module_info = module.get_module_info()
        if 'input_schema' not in module_info:
            # Fallback: use generic input name
            return {'input': input_value}
        
        input_schema = json.loads(module_info['input_schema'])
        if not input_schema:
            # Fallback: use generic input name
            return {'input': input_value}
        
        # Use the first input field name from the schema
        expected_input_name = input_schema[0]['name']
        
        self.logger.info(f"  🔗 Mapping '{input_field_name}' → '{expected_input_name}' for module {template_id}")
        
        return {expected_input_name: input_value}
    
    def _extract_module_output(
        self,
        template_id: str,
        module_outputs: Dict[str, Any],
        output_field_name: str
    ) -> Any:
        """
        Extract output value from module results
        
        Args:
            template_id: Module template ID
            module_outputs: Dictionary of outputs from module execution
            output_field_name: Our internal output field name
            
        Returns:
            The output value
        """
        
        if not module_outputs:
            raise ValueError(f"Module {template_id} returned no outputs")
        
        # For now, just take the first output value
        # In the future, this could be enhanced to map specific output fields
        output_values = list(module_outputs.values())
        if not output_values:
            raise ValueError(f"Module {template_id} returned empty outputs")
        
        output_value = output_values[0]
        self.logger.info(f"  🔗 Mapped module output to '{output_field_name}': '{output_value}'")
        
        return output_value
    


# Global executor instance
_simple_executor = None

def get_simple_pipeline_executor() -> SimplePipelineExecutor:
    """Get global simple pipeline executor instance"""
    global _simple_executor
    if _simple_executor is None:
        _simple_executor = SimplePipelineExecutor()
    return _simple_executor