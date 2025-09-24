"""
Pipeline Execution Service

This service handles the execution of transformation pipelines with data flow management.
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
import json

from .pipeline_analysis import get_pipeline_analyzer, PipelineAnalysisError
from ..modules import get_module_registry

logger = logging.getLogger(__name__)


class PipelineExecutionError(Exception):
    """Custom exception for pipeline execution errors"""
    pass


class DataFlowManager:
    """
    Manages data flow between modules during pipeline execution
    """
    
    def __init__(self):
        self.data_store = {}  # module_id -> {output_name: data}
        self.connections_map = {}  # (from_module, from_output) -> [(to_module, to_input), ...]
        
    def initialize_connections(self, connections: List[Dict[str, Any]]):
        """Initialize connection mappings for data flow"""
        self.connections_map = {}
        
        for conn in connections:
            from_key = (conn['from']['moduleId'], conn['from']['outputIndex'])
            to_info = (conn['to']['moduleId'], conn['to']['inputIndex'])
            
            if from_key not in self.connections_map:
                self.connections_map[from_key] = []
            self.connections_map[from_key].append(to_info)
    
    def store_module_outputs(self, module_id: str, outputs: Dict[str, Any]):
        """Store outputs from a module execution"""
        self.data_store[module_id] = outputs
        logger.info(f"Stored outputs for module {module_id}: {list(outputs.keys())}")
    
    def get_module_inputs(
        self, 
        module_id: str, 
        module_config: Dict[str, Any],
        base_inputs: Dict[str, Any] = None,
        mock_data_modules: Dict[str, Dict[str, Any]] = None,
        module_registry = None
    ) -> Dict[str, Any]:
        """
        Get inputs for a module based on connections and base inputs
        """
        inputs = {}
        
        # Add base inputs if provided (for extracted data modules)
        if base_inputs:
            inputs.update(base_inputs)
        
        # Find all connections that feed into this module
        for (from_module, from_output_idx), targets in self.connections_map.items():
            for to_module, to_input_idx in targets:
                if to_module == module_id:
                    # Check if source is a mock extracted data module
                    if from_module in (mock_data_modules or {}):
                        # Use mock data as input
                        mock_module_data = mock_data_modules[from_module]
                        template_id = mock_module_data.get('templateId', '')
                        
                        # Generate sample data based on extracted data type
                        sample_data = self._generate_mock_data(template_id)
                        inputs[f"input_{to_input_idx}"] = sample_data
                        continue
                    
                    # Get the output data from the source module (normal execution)
                    if from_module in self.data_store:
                        from_outputs = self.data_store[from_module]
                        
                        # Map output index to actual output name/data
                        if isinstance(from_outputs, dict):
                            output_keys = list(from_outputs.keys())
                            if from_output_idx < len(output_keys):
                                output_key = output_keys[from_output_idx]
                                output_data = from_outputs[output_key]
                                
                                # Get the actual input field name from the module registry
                                logger.info(f"Attempting to map input for module {module_id}, template_id: {module_config.get('templateId')}")
                                if module_registry:
                                    template_id = module_config.get('templateId')
                                    logger.info(f"Looking up template_id: {template_id}")
                                    if template_id:
                                        module = module_registry.get_module(template_id)
                                        logger.info(f"Module found: {module is not None}")
                                        if module:
                                            # Get the module's input schema
                                            import json
                                            module_info = module.get_module_info()
                                            logger.info(f"Module info keys: {list(module_info.keys())}")
                                            if 'input_schema' in module_info:
                                                input_schema = json.loads(module_info['input_schema'])
                                                logger.info(f"Input schema: {input_schema}")
                                                if to_input_idx < len(input_schema):
                                                    input_field_name = input_schema[to_input_idx]['name']
                                                    inputs[input_field_name] = output_data
                                                    logger.info(f"Mapped connection data to input field '{input_field_name}' for module {module_id}")
                                                else:
                                                    logger.warning(f"Input index {to_input_idx} out of range for schema length {len(input_schema)}")
                                                    inputs[f"input_{to_input_idx}"] = output_data
                                            else:
                                                logger.warning(f"No input_schema found in module info")
                                                inputs[f"input_{to_input_idx}"] = output_data
                                        else:
                                            logger.warning(f"Module not found for template_id: {template_id}")
                                            inputs[f"input_{to_input_idx}"] = output_data
                                    else:
                                        logger.warning(f"No template_id in module_config")
                                        inputs[f"input_{to_input_idx}"] = output_data
                                else:
                                    logger.warning(f"No module_registry provided")
                                    inputs[f"input_{to_input_idx}"] = output_data
        
        logger.info(f"Prepared inputs for module {module_id}: {list(inputs.keys())}")
        return inputs
    
    def _generate_mock_data(self, template_id: str) -> Any:
        """Generate sample data for mock extracted data modules"""
        mock_data_map = {
            'mock_extracted_hawb': 'AWB123456789',
            'mock_extracted_carrier_name': 'FedEx Express',
            'mock_extracted_pickup_address': '123 Pickup St, City, State 12345',
            'mock_extracted_pickup_phone': '+1-555-0123',
            'mock_extracted_delivery_address': '456 Delivery Ave, City, State 67890',
            'mock_extracted_delivery_phone': '+1-555-0456',
            'mock_extracted_weight': '2.5 kg',
            'mock_extracted_dimensions': '30x20x15 cm',
            'mock_extracted_service_type': 'Express Delivery',
            'mock_extracted_tracking_number': 'TRK789012345'
        }
        
        return mock_data_map.get(template_id, f'Sample data for {template_id}')


class PipelineExecutor:
    """
    Executes transformation pipelines with parallel optimization
    """
    
    def __init__(self):
        self.logger = logger
        self.module_registry = get_module_registry()
        self.analyzer = get_pipeline_analyzer()
    
    async def execute_pipeline(
        self,
        modules: List[Dict[str, Any]],
        connections: List[Dict[str, Any]],
        base_inputs: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Execute a complete transformation pipeline
        
        Args:
            modules: List of module configurations
            connections: List of connections between modules  
            base_inputs: Base input data (from extracted data modules)
            
        Returns:
            Dictionary with execution results and order data
        """
        try:
            # Analyze pipeline for execution plan
            analysis_result = self.analyzer.analyze_pipeline(modules, connections)
            
            if not analysis_result['success']:
                raise PipelineExecutionError("Pipeline analysis failed")
            
            execution_plan = analysis_result['execution_plan']
            target_module = analysis_result['target_module']
            
            # Initialize data flow manager
            data_flow = DataFlowManager()
            data_flow.initialize_connections(connections)
            
            # Separate mock data modules from executable modules
            mock_data_modules = {
                m['id']: m for m in modules 
                if m.get('templateId', '').startswith('mock_extracted_')
            }
            
            self.logger.info(f"Identified {len(mock_data_modules)} mock data modules")
            
            # Execute pipeline steps
            execution_results = await self._execute_steps(
                execution_plan['steps'],
                data_flow,
                base_inputs or {},
                mock_data_modules
            )
            
            # Get final results from target module (Order Generation)
            target_outputs = data_flow.data_store.get(target_module['id'], {})
            
            # Extract order field names and calculated values
            order_data = self._extract_order_data(target_outputs)
            
            return {
                'success': True,
                'execution_results': execution_results,
                'order_data': order_data,
                'target_module_id': target_module['id'],
                'steps_executed': len(execution_plan['steps']),
                'parallel_optimizations': execution_plan['parallel_count']
            }
            
        except Exception as e:
            self.logger.error(f"Pipeline execution failed: {e}")
            raise PipelineExecutionError(f"Execution failed: {str(e)}")
    
    async def _execute_steps(
        self,
        steps: List[Dict[str, Any]],
        data_flow: DataFlowManager,
        base_inputs: Dict[str, Any],
        mock_data_modules: Dict[str, Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Execute pipeline steps with parallel optimization"""
        results = []
        
        for step in steps:
            step_number = step['step_number']
            step_modules = step['modules']
            is_parallel = step['parallel']
            
            self.logger.info(
                f"Executing step {step_number} with {len(step_modules)} modules "
                f"({'parallel' if is_parallel else 'sequential'})"
            )
            
            if is_parallel:
                # Execute modules in parallel
                step_results = await self._execute_parallel_modules(
                    step_modules, data_flow, base_inputs, mock_data_modules
                )
            else:
                # Execute single module
                step_results = [await self._execute_module(
                    step_modules[0], data_flow, base_inputs, mock_data_modules
                )]
            
            results.append({
                'step': step_number,
                'parallel': is_parallel,
                'modules_executed': len(step_modules),
                'results': step_results
            })
        
        return results
    
    async def _execute_parallel_modules(
        self,
        modules: List[Dict[str, Any]],
        data_flow: DataFlowManager,
        base_inputs: Dict[str, Any],
        mock_data_modules: Dict[str, Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Execute multiple modules in parallel"""
        
        # Use ThreadPoolExecutor for parallel execution
        with ThreadPoolExecutor(max_workers=min(len(modules), 4)) as executor:
            # Submit all module executions
            future_to_module = {
                executor.submit(
                    self._execute_module_sync, module, data_flow, base_inputs, mock_data_modules
                ): module for module in modules
            }
            
            results = []
            for future in as_completed(future_to_module):
                module = future_to_module[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    self.logger.error(f"Module {module['id']} failed: {e}")
                    raise PipelineExecutionError(
                        f"Module {module['id']} execution failed: {str(e)}"
                    )
            
            return results
    
    def _execute_module_sync(
        self,
        module: Dict[str, Any],
        data_flow: DataFlowManager,
        base_inputs: Dict[str, Any],
        mock_data_modules: Dict[str, Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Synchronous module execution for thread pool"""
        return asyncio.run(self._execute_module(module, data_flow, base_inputs, mock_data_modules))
    
    async def _execute_module(
        self,
        module: Dict[str, Any],
        data_flow: DataFlowManager,
        base_inputs: Dict[str, Any],
        mock_data_modules: Dict[str, Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a single module"""
        module_id = module['id']
        template_id = module['templateId']
        config = module.get('config', {})
        
        try:
            # Handle special endpoint modules
            if template_id.startswith('mock_') or template_id == 'order_generation':
                self.logger.info(f"Handling endpoint module {module_id} ({template_id})")
                
                # Get inputs for logging (even for endpoint modules)
                module_config_with_template = {**config, 'templateId': template_id}
                inputs = data_flow.get_module_inputs(module_id, module_config_with_template, base_inputs, mock_data_modules, self.module_registry)
                self.logger.info(f"Order Generation inputs received: {inputs}")
                
                # For order generation modules, return the inputs as order data
                if template_id in ['mock_order_generation', 'order_generation']:
                    # Convert inputs to order format
                    order_outputs = {
                        'order_data': inputs,
                        'order_id': 'ORD-' + str(hash(module_id))[-6:],
                        'processed_at': '2025-09-04T20:15:00Z',
                        'status': 'processed'
                    }
                    
                    # Log the order data for debugging
                    self.logger.info(f"ORDER GENERATION COMPLETE:")
                    self.logger.info(f"Order Field Names: {list(inputs.keys())}")
                    self.logger.info(f"💰 Calculated Values: {inputs}")
                    
                elif template_id.startswith('mock_extracted_'):
                    # For mock extracted data modules, return the sample data from baseInputs
                    # Find the corresponding data in base_inputs
                    extracted_data = {}
                    
                    # Look for matching field in base_inputs based on module's output field name
                    module_nodes = module.get('nodes', {})
                    outputs = module_nodes.get('outputs', [])
                    
                    if outputs and len(outputs) > 0:
                        output_field_name = outputs[0].get('name', '')
                        if output_field_name and output_field_name in (base_inputs or {}):
                            extracted_data[output_field_name] = base_inputs[output_field_name]
                            self.logger.info(f"📤 Mock extracted data: {output_field_name} = '{base_inputs[output_field_name]}'")
                        else:
                            # Fallback: use the mock data generation
                            sample_data = self._generate_mock_data(template_id)
                            if output_field_name:
                                extracted_data[output_field_name] = sample_data
                            else:
                                extracted_data['output'] = sample_data
                            self.logger.info(f"📤 Generated mock data: {extracted_data}")
                    
                    order_outputs = extracted_data
                else:
                    # For other mock modules, return empty outputs
                    order_outputs = {}
                
                # Store outputs
                data_flow.store_module_outputs(module_id, order_outputs)
                
                return {
                    'module_id': module_id,
                    'template_id': template_id,
                    'success': True,
                    'inputs_count': len(inputs),
                    'outputs_count': len(order_outputs),
                    'outputs': order_outputs,
                    'endpoint': True
                }
            
            # Get inputs for this module
            module_config_with_template = {**config, 'templateId': template_id}
            inputs = data_flow.get_module_inputs(module_id, module_config_with_template, base_inputs, mock_data_modules, self.module_registry)
            
            # Execute the module
            outputs = self.module_registry.execute_module(
                template_id, inputs, config
            )
            
            # Store outputs in data flow
            data_flow.store_module_outputs(module_id, outputs)
            
            self.logger.info(f"Successfully executed module {module_id} ({template_id})")
            
            return {
                'module_id': module_id,
                'template_id': template_id,
                'success': True,
                'inputs_count': len(inputs),
                'outputs_count': len(outputs),
                'outputs': outputs
            }
            
        except Exception as e:
            self.logger.error(f"Module {module_id} execution failed: {e}")
            raise PipelineExecutionError(
                f"Module {module_id} ({template_id}) failed: {str(e)}"
            )
    
    def _extract_order_data(self, target_outputs: Dict[str, Any]) -> Dict[str, Any]:
        """Extract order field names and calculated values from target module outputs"""
        if not target_outputs:
            return {}
        
        # For Order Generation module, extract the order data structure
        order_data = {}
        
        for output_name, output_value in target_outputs.items():
            if isinstance(output_value, dict):
                # If output is a dictionary, it might contain order fields
                order_data.update(output_value)
            else:
                # Otherwise, use the output name as the field name
                order_data[output_name] = output_value
        
        return order_data
    
    def validate_execution_requirements(
        self,
        modules: List[Dict[str, Any]],
        connections: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Validate that pipeline can be executed"""
        try:
            self.logger.info(f"Validating pipeline with {len(modules)} modules")
            
            # Use pipeline analyzer for validation
            validation_result = self.analyzer.validate_pipeline(modules, connections)
            self.logger.info(f"Pipeline analyzer validation result: {validation_result}")
            
            if not validation_result['valid']:
                return validation_result
            
            # Additional execution-specific validations
            module_templates = [m.get('templateId') for m in modules]
            self.logger.info(f"Checking module templates: {module_templates}")
            
            # Filter out mock modules - they're just UI placeholders for data inputs
            executable_templates = []
            mock_extracted_modules = []
            
            for template_id in module_templates:
                if template_id:
                    if template_id.startswith('mock_extracted_'):
                        # These are data input placeholders
                        mock_extracted_modules.append(template_id)
                    elif template_id in ['mock_order_generation', 'order_generation']:
                        # Skip order generation modules - they're just target endpoints
                        continue
                    elif template_id.startswith('backend_') or not template_id.startswith('mock_'):
                        # These are actual executable modules
                        executable_templates.append(template_id)
            
            self.logger.info(f"Executable templates to validate: {executable_templates}")
            self.logger.info(f"Mock data input modules (skipped): {mock_extracted_modules}")
            
            missing_templates = []
            
            for template_id in executable_templates:
                module = self.module_registry.get_module(template_id)
                has_module = module is not None
                self.logger.info(f"Template '{template_id}' available: {has_module}")
                if not has_module:
                    missing_templates.append(template_id)
            
            if missing_templates:
                error_msg = f"Missing module templates: {', '.join(missing_templates)}"
                self.logger.error(error_msg)
                return {
                    'valid': False,
                    'error': error_msg
                }
            
            self.logger.info("Pipeline validation passed")
            return validation_result
            
        except Exception as e:
            error_msg = f"Validation error: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return {
                'valid': False,
                'error': error_msg
            }


# Global executor instance
_executor = None

def get_pipeline_executor() -> PipelineExecutor:
    """Get global pipeline executor instance"""
    global _executor
    if _executor is None:
        _executor = PipelineExecutor()
    return _executor