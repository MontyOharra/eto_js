"""
Step-Based Pipeline Execution Service

Executes pipelines using step-based dependency analysis with parallel processing
within steps while maintaining dependency safety.
"""

import logging
import asyncio
from typing import Dict, List, Any, Set
from ..modules import get_module_registry

logger = logging.getLogger(__name__)


class StepBasedPipelineExecutor:
    """
    Executes pipelines using step-based dependency analysis
    
    - Executes modules in dependency order based on calculated steps
    - Runs modules within each step in parallel for maximum efficiency
    - Uses node IDs for precise data routing between modules
    - Maintains data safety by completing each step before proceeding
    """
    
    def __init__(self):
        self.logger = logger
        self.module_registry = get_module_registry()
        
    async def execute_pipeline_with_steps(
        self,
        steps: Dict[int, List[Dict[str, Any]]],
        connections: List[Dict[str, Any]],
        input_data: Dict[str, Any],
        output_endpoints: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Execute pipeline using step-based analysis results
        
        Args:
            steps: Dictionary of step_number -> list of entities to execute
            connections: List of connections for data routing
            input_data: Dictionary of input node IDs to values
            output_endpoints: List of output endpoint definitions
            
        Returns:
            Dictionary with final output values by field names
        """
        
        self.logger.info(f"🚀 Starting step-based pipeline execution with {len(steps)} steps")
        self.logger.info(f"📥 Input data keys: {list(input_data.keys())}")
        
        # Global data store using node IDs
        node_data_store: Dict[str, Any] = input_data.copy()
        self.logger.info(f"📊 Initial data store: {list(node_data_store.keys())}")
        
        # Build connection mapping for efficient data routing
        connection_map = self._build_connection_map(connections)
        
        try:
            # Execute each step sequentially, modules within steps in parallel
            for step_number in sorted(steps.keys()):
                step_entities = steps[step_number]
                
                # Filter to only processing modules (skip inputs which are already in data store)
                processing_modules = [
                    entity for entity in step_entities 
                    if entity['type'] == 'module'
                ]
                
                if not processing_modules:
                    self.logger.info(f"⏭️ Step {step_number}: No processing modules to execute")
                    continue
                
                self.logger.info(f"⚙️ Step {step_number}: Executing {len(processing_modules)} modules in parallel")
                
                # Execute all modules in this step in parallel
                await self._execute_step_modules(
                    step_number, processing_modules, connection_map, node_data_store
                )
                
                self.logger.info(f"✅ Step {step_number} completed")
            
            # Extract final outputs based on output endpoints
            final_outputs = self._extract_final_outputs(
                output_endpoints, connection_map, node_data_store
            )
            
            self.logger.info(f"🎯 Pipeline execution completed successfully")
            self.logger.info(f"📤 Final outputs: {final_outputs}")
            
            return final_outputs
            
        except Exception as e:
            self.logger.error(f"❌ Step-based pipeline execution failed: {e}")
            raise
    
    async def _execute_step_modules(
        self,
        step_number: int,
        modules: List[Dict[str, Any]],
        connection_map: Dict[str, List[Dict[str, Any]]],
        node_data_store: Dict[str, Any]
    ) -> None:
        """
        Execute all modules in a step in parallel
        
        Args:
            step_number: Current step number
            modules: List of module entities to execute
            connection_map: Connection mapping for data routing
            node_data_store: Global node data store (modified in place)
        """
        
        # Create async tasks for all modules in this step
        tasks = []
        for module in modules:
            task = self._execute_single_module(
                module, connection_map, node_data_store
            )
            tasks.append(task)
        
        # Wait for all modules in this step to complete
        module_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results and update data store
        for i, result in enumerate(module_results):
            module = modules[i]
            if isinstance(result, Exception):
                self.logger.error(f"Module {module['id']} failed: {result}")
                raise result
            else:
                # result is tuple of (module_id, module_outputs)
                module_id, module_outputs = result
                self._route_module_outputs(
                    module_id, module_outputs, connection_map, node_data_store
                )
    
    async def _execute_single_module(
        self,
        module: Dict[str, Any],
        connection_map: Dict[str, List[Dict[str, Any]]],
        node_data_store: Dict[str, Any]
    ) -> tuple[str, Dict[str, Any]]:
        """
        Execute a single module with input data routing
        
        Args:
            module: Module entity to execute
            connection_map: Connection mapping for data routing
            node_data_store: Global node data store
            
        Returns:
            Tuple of (module_id, module_outputs)
        """
        
        module_id = module['id']
        template_id = module['template_id']
        config = module['entity'].get('config', {})
        
        self.logger.info(f"  🔧 Executing module {module_id} (template: {template_id})")
        
        # Gather inputs for this module from connected sources
        module_inputs = self._gather_module_inputs(
            module_id, connection_map, node_data_store
        )
        
        self.logger.info(f"    📥 Module inputs: {module_inputs}")
        
        # Construct node info from module entity
        node_info = self._build_node_info(module['entity'], module_inputs)
        
        # Execute the module (this could be made async if needed)
        outputs = self.module_registry.execute_module(template_id, module_inputs, config, node_info)
        
        self.logger.info(f"    📤 Module outputs: {outputs}")
        
        return module_id, outputs
    
    def _gather_module_inputs(
        self,
        module_id: str,
        connection_map: Dict[str, List[Dict[str, Any]]],
        node_data_store: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Gather inputs for a module by following incoming connections
        
        Args:
            module_id: Target module ID
            connection_map: Connection mapping
            node_data_store: Global node data store
            
        Returns:
            Dictionary of input field names to values
        """
        
        module_inputs = {}
        
        # Find all connections that target this module
        incoming_connections = [
            conn for conn in connection_map.get(module_id, [])
            if conn['toModuleId'] == module_id
        ]
        
        for connection in incoming_connections:
            from_module_id = connection['fromModuleId']
            from_output_index = connection['fromOutputIndex']
            to_input_index = connection['toInputIndex']
            
            # Generate source node ID
            source_node_id = f"{from_module_id}_output_{from_output_index}"
            
            # Check if data is available
            if source_node_id not in node_data_store:
                raise ValueError(f"Required input data not found: {source_node_id}")
            
            # Map to module's expected input field name
            target_input_name = f"input_{to_input_index}"  # Simple naming for now
            module_inputs[target_input_name] = node_data_store[source_node_id]
            
            self.logger.info(f"    🔗 Routed {source_node_id} → {target_input_name}")
        
        return module_inputs
    
    def _route_module_outputs(
        self,
        module_id: str,
        module_outputs: Dict[str, Any],
        connection_map: Dict[str, List[Dict[str, Any]]],
        node_data_store: Dict[str, Any]
    ) -> None:
        """
        Route module outputs to node data store using connection information
        
        Args:
            module_id: Source module ID
            module_outputs: Dictionary of module outputs
            connection_map: Connection mapping
            node_data_store: Global node data store (modified in place)
        """
        
        # Store outputs by output index (assuming ordered outputs)
        output_values = list(module_outputs.values())
        for output_index, output_value in enumerate(output_values):
            output_node_id = f"{module_id}_output_{output_index}"
            node_data_store[output_node_id] = output_value
            self.logger.info(f"    📝 Stored {output_node_id} = {output_value}")
    
    def _extract_final_outputs(
        self,
        output_endpoints: List[Dict[str, Any]],
        connection_map: Dict[str, List[Dict[str, Any]]],
        node_data_store: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extract final outputs based on output endpoint connections
        
        Args:
            output_endpoints: List of output endpoint definitions
            connection_map: Connection mapping
            node_data_store: Global node data store
            
        Returns:
            Dictionary of output field names to values
        """
        
        final_outputs = {}
        
        for output_endpoint in output_endpoints:
            endpoint_id = output_endpoint['id']
            field_name = output_endpoint['name']
            
            # Find connection that feeds this output endpoint
            incoming_connections = [
                conn for conn_list in connection_map.values()
                for conn in conn_list
                if conn['toModuleId'] == endpoint_id
            ]
            
            if incoming_connections:
                connection = incoming_connections[0]  # Take first connection
                source_module_id = connection['fromModuleId']
                source_output_index = connection['fromOutputIndex']
                
                source_node_id = f"{source_module_id}_output_{source_output_index}"
                
                if source_node_id in node_data_store:
                    final_outputs[field_name] = node_data_store[source_node_id]
                    self.logger.info(f"    🎯 Output {field_name} = {node_data_store[source_node_id]}")
                else:
                    self.logger.warning(f"Output data not found for {field_name}: {source_node_id}")
            else:
                self.logger.warning(f"No connection found for output endpoint: {endpoint_id}")
        
        return final_outputs
    
    def _build_connection_map(
        self, connections: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Build a mapping of module_id -> list of connections for efficient lookup
        
        Args:
            connections: List of connection definitions
            
        Returns:
            Dictionary mapping module IDs to their connections
        """
        
        connection_map = {}
        
        for connection in connections:
            from_module_id = connection['fromModuleId']
            to_module_id = connection['toModuleId']
            
            # Add to target module's incoming connections
            if to_module_id not in connection_map:
                connection_map[to_module_id] = []
            connection_map[to_module_id].append(connection)
        
        return connection_map
    
    def _build_node_info(
        self, 
        module_entity: Dict[str, Any], 
        module_inputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Build ExecutionNodeInfo from module entity and current inputs
        
        Args:
            module_entity: Module entity with nodes information
            module_inputs: Current module input values
            
        Returns:
            ExecutionNodeInfo dictionary
        """
        
        # Extract node information from the module entity
        nodes = module_entity.get('nodes', {})
        input_nodes = nodes.get('inputs', [])
        output_nodes = nodes.get('outputs', [])
        
        # Build input node info
        input_node_info = []
        for i, input_node in enumerate(input_nodes):
            input_node_info.append({
                'nodeId': f"{module_entity['id']}_input_{i}",
                'type': input_node.get('type', 'string')
            })
        
        # Build output node info
        output_node_info = []
        for i, output_node in enumerate(output_nodes):
            output_node_info.append({
                'nodeId': f"{module_entity['id']}_output_{i}",
                'type': output_node.get('type', 'string')
            })
        
        return {
            'inputs': input_node_info,
            'outputs': output_node_info
        }


# Global executor instance
_step_executor = None

def get_step_based_pipeline_executor() -> StepBasedPipelineExecutor:
    """Get global step-based pipeline executor instance"""
    global _step_executor
    if _step_executor is None:
        _step_executor = StepBasedPipelineExecutor()
    return _step_executor