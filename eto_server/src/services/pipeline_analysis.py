"""
Pipeline Analysis Service

This service provides functionality to analyze transformation pipelines,
including dependency resolution, topological sorting, and parallel optimization.
"""

import logging
from typing import Dict, List, Tuple, Set, Any, Optional
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class SimpleFieldMapper:
    """
    Simple field mapper that uses user field names directly without unique ID generation
    """
    
    def __init__(self):
        self._field_names = set()  # Track all field names used
    
    def add_field_name(self, field_name: str) -> str:
        """
        Add a field name to the tracker and return it as-is
        
        Args:
            field_name: The user field name
            
        Returns:
            The same field name (no ID generation)
        """
        self._field_names.add(field_name)
        logger.info(f"Added field name: {field_name}")
        return field_name
    
    def get_all_field_names(self) -> Set[str]:
        """Get all field names that have been added"""
        return self._field_names.copy()
    
    def get_identity_mapping(self) -> Dict[str, str]:
        """Get identity mapping where field names map to themselves"""
        return {name: name for name in self._field_names}


class PipelineAnalysisError(Exception):
    """Custom exception for pipeline analysis errors"""
    pass


class PipelineAnalyzer:
    """
    Analyzes transformation pipelines for execution order and dependencies
    """
    
    def __init__(self):
        self.logger = logger
    
    def analyze_pipeline_with_steps(
        self,
        modules: List[Dict[str, Any]],
        connections: List[Dict[str, Any]],
        input_definitions: List[Dict[str, Any]],
        output_definitions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze a pipeline using step-based dependency algorithm
        
        Args:
            modules: List of processing modules (excludes I/O definers)
            connections: List of connections between modules and I/O definitions
            input_definitions: List of input definitions (entry points)
            output_definitions: List of output definitions (exit points)
            
        Returns:
            Dictionary containing step-based execution plan
        """
        try:
            self.logger.info("Starting step-based pipeline analysis")
            self.logger.info(f"Modules: {len(modules)}, Connections: {len(connections)}")
            self.logger.info(f"Inputs: {len(input_definitions)}, Outputs: {len(output_definitions)}")
            
            # Create unified module list for step calculation - exclude outputs from processing
            all_entities = input_definitions + modules + output_definitions
            entity_lookup = {entity['id']: entity for entity in all_entities}
            
            # Step 1: Initialize all input modules as step 0
            step_assignments = {}
            for input_def in input_definitions:
                step_assignments[input_def['id']] = 0
                self.logger.info(f"Input '{input_def['id']}' assigned to step 0")
            
            # Step 2-N: Apply step-based dependency algorithm
            current_step = 0
            max_iterations = len(all_entities) + 10  # Prevent infinite loops
            iteration = 0
            
            while iteration < max_iterations:
                iteration += 1
                current_step_modules = [
                    entity_id for entity_id, step in step_assignments.items() 
                    if step == current_step
                ]
                
                if not current_step_modules:
                    self.logger.info(f"No modules found at step {current_step}, ending algorithm")
                    break
                
                self.logger.info(f"Processing step {current_step} with modules: {current_step_modules}")
                
                next_step = current_step + 1
                assigned_any = False
                
                # Find all modules connected to current step modules via output connections
                for connection in connections:
                    from_module_id = connection['fromModuleId']
                    to_module_id = connection['toModuleId']
                    
                    # If source module is in current step, assign target to next step
                    if from_module_id in current_step_modules:
                        # Skip output definitions - they don't perform computations
                        target_entity = entity_lookup.get(to_module_id)
                        if target_entity and target_entity in output_definitions:
                            self.logger.info(f"Skipping output endpoint '{to_module_id}' - no computation step needed")
                            continue
                        
                        # Assign target to next step (overwrite if already assigned)
                        step_assignments[to_module_id] = next_step
                        assigned_any = True
                        self.logger.info(f"Module '{to_module_id}' assigned to step {next_step} (connected from '{from_module_id}')")
                
                if not assigned_any:
                    self.logger.info(f"No new assignments made at step {current_step}, algorithm complete")
                    break
                
                current_step = next_step
            
            if iteration >= max_iterations:
                self.logger.warning("Algorithm reached maximum iterations - possible circular dependency")
            
            # Organize results by steps - only include entities with step assignments
            steps_result = {}
            for entity_id, step_num in step_assignments.items():
                if step_num not in steps_result:
                    steps_result[step_num] = []
                
                entity = entity_lookup[entity_id]
                entity_type = "input" if entity in input_definitions else "module"  # Output definitions excluded
                
                steps_result[step_num].append({
                    "id": entity_id,
                    "type": entity_type,
                    "name": entity.get('name', entity_id),
                    "template_id": entity.get('templateId', ''),
                    "entity": entity
                })
            
            # Output definitions are tracked separately since they're not in execution steps
            output_endpoints = []
            for output_def in output_definitions:
                output_endpoints.append({
                    "id": output_def['id'],
                    "type": "output",
                    "name": output_def.get('name', output_def['id']),
                    "template_id": output_def.get('templateId', ''),
                    "entity": output_def
                })
            
            # Calculate execution metrics
            total_steps = max(step_assignments.values()) + 1 if step_assignments else 0
            parallel_opportunities = sum(1 for step_modules in steps_result.values() if len(step_modules) > 1)
            
            return {
                'success': True,
                'algorithm': 'step_based_dependency',
                'steps': dict(sorted(steps_result.items())),
                'step_assignments': step_assignments,
                'output_endpoints': output_endpoints,  # Separate from steps
                'total_steps': total_steps,
                'parallel_opportunities': parallel_opportunities,
                'input_count': len(input_definitions),
                'output_count': len(output_definitions),
                'processing_module_count': len(modules),
                'total_entities': len(all_entities)
            }
            
        except Exception as e:
            self.logger.error(f"Step-based pipeline analysis failed: {e}")
            raise PipelineAnalysisError(f"Step-based analysis failed: {str(e)}")

    def analyze_pipeline(
        self,
        modules: List[Dict[str, Any]],
        connections: List[Dict[str, Any]],
        target_module_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze a pipeline and return execution plan
        
        Args:
            modules: List of module configurations
            connections: List of connections between modules
            target_module_id: Optional specific target module (defaults to Order Generation)
            
        Returns:
            Dictionary containing execution plan with parallel steps
        """
        try:
            # Debug: Log all template IDs
            template_ids = [m.get('templateId', 'NO_TEMPLATE_ID') for m in modules]
            self.logger.info(f"All template IDs: {template_ids}")
            
            # Separate modules by type - more flexible identification
            input_modules = []
            output_modules = []
            processing_modules = []
            
            for module in modules:
                template_id = module.get('templateId', '')
                template_name = module.get('template', {}).get('name', '').lower()
                
                # Identify input modules (various patterns)
                if (template_id.startswith('input_') or 
                    template_id.startswith('extracted_') or 
                    'input' in template_name):
                    input_modules.append(module)
                # Identify output modules (various patterns)  
                elif (template_id in ['order_generation', 'mock_order_generation'] or
                      template_id.startswith('output_') or
                      'output' in template_name or
                      'order' in template_name):
                    output_modules.append(module)
                # Everything else is a processing module
                else:
                    processing_modules.append(module)
            
            self.logger.info(f"Input modules: {[m.get('templateId') for m in input_modules]}")
            self.logger.info(f"Processing modules: {[m.get('templateId') for m in processing_modules]}")
            self.logger.info(f"Output modules: {[m.get('templateId') for m in output_modules]}")
            self.logger.info(f"Found {len(input_modules)} input modules, {len(processing_modules)} processing modules, {len(output_modules)} output modules")
            
            # NOTE: Input/Output modules are optional for analysis - they're used during execution
            # Analysis focuses on transformation steps between processing modules
            
            # Simple field mapping system (no unique IDs)
            field_mapper = SimpleFieldMapper()
            
            # Build transformation steps for processing modules
            if processing_modules:
                transformation_steps = self._build_transformation_steps_simple(
                    processing_modules, connections, input_modules, output_modules, field_mapper
                )
            else:
                transformation_steps = []
                self.logger.info("No processing modules found - pipeline contains only input/output configuration")
            
            # Extract input and output field mappings (simple names) - optional for analysis
            input_field_mapping = self._extract_input_fields_simple(input_modules, connections, field_mapper) if input_modules else {}
            output_field_mapping = self._extract_output_fields_simple(output_modules, connections, processing_modules, input_modules, field_mapper) if output_modules else {}
            
            return {
                'success': True,
                'transformation_steps': transformation_steps,
                'field_mappings': {
                    'input_fields': input_field_mapping,
                    'output_fields': output_field_mapping,
                    'id_to_name': field_mapper.get_identity_mapping(),
                    'all_field_names': list(field_mapper.get_all_field_names())
                },
                'total_steps': len(transformation_steps)
            }
            
        except Exception as e:
            self.logger.error(f"Pipeline analysis failed: {e}")
            raise PipelineAnalysisError(f"Analysis failed: {str(e)}")
    
    def _build_dependency_graph(
        self, 
        modules: List[Dict[str, Any]], 
        connections: List[Dict[str, Any]]
    ) -> Dict[str, Dict]:
        """
        Build dependency graph from modules and connections
        
        Returns:
            Dictionary with module dependencies and reverse dependencies
        """
        # Initialize graph structure
        graph = {
            'dependencies': defaultdict(set),  # module_id -> set of dependencies
            'dependents': defaultdict(set),    # module_id -> set of dependents
            'modules': {m['id']: m for m in modules}
        }
        
        # Build dependency relationships from connections
        for connection in connections:
            from_module = connection['from']['moduleId']
            to_module = connection['to']['moduleId']
            
            # to_module depends on from_module
            graph['dependencies'][to_module].add(from_module)
            graph['dependents'][from_module].add(to_module)
        
        return graph
    
    def _find_target_module(
        self, 
        modules: List[Dict[str, Any]], 
        target_module_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Find the target module (Order Generation by default)
        """
        self.logger.info(f"Looking for target module. Specific target: {target_module_id}")
        
        if target_module_id:
            target = next((m for m in modules if m['id'] == target_module_id), None)
            self.logger.info(f"Found specific target module: {target is not None}")
            return target
        
        # Look for Order Generation module (prefer backend version over mock)
        available_templates = [m.get('templateId') for m in modules]
        self.logger.info(f"Available template IDs: {available_templates}")
        
        # First try to find the real order_generation module
        for module in modules:
            template_id = module.get('templateId')
            if template_id == 'order_generation':
                self.logger.info(f"Found Order Generation module: {module.get('id')}")
                return module
        
        # If not found, look for mock version as fallback
        for module in modules:
            template_id = module.get('templateId')
            if template_id == 'mock_order_generation':
                self.logger.info(f"Found Mock Order Generation module as fallback: {module.get('id')}")
                return module
        
        self.logger.warning("No Order Generation module found")
        return None
    
    def _find_required_modules(
        self, 
        dependency_graph: Dict[str, Dict], 
        target_module_id: str
    ) -> Set[str]:
        """
        Find all modules required to reach the target module using BFS
        """
        required = set()
        queue = deque([target_module_id])
        visited = set()
        
        while queue:
            current = queue.popleft()
            if current in visited:
                continue
                
            visited.add(current)
            required.add(current)
            
            # Add all dependencies of current module
            dependencies = dependency_graph['dependencies'].get(current, set())
            for dep in dependencies:
                if dep not in visited:
                    queue.append(dep)
        
        return required
    
    def _create_execution_plan(
        self,
        modules: List[Dict[str, Any]],
        dependency_graph: Dict[str, Dict],
        required_modules: Set[str]
    ) -> Dict[str, Any]:
        """
        Create optimized execution plan with parallel steps
        """
        # Filter to only required modules
        required_module_data = {
            m['id']: m for m in modules if m['id'] in required_modules
        }
        
        # Calculate in-degrees for topological sort
        in_degree = defaultdict(int)
        for module_id in required_modules:
            dependencies = dependency_graph['dependencies'].get(module_id, set())
            # Only count dependencies that are in required modules
            in_degree[module_id] = len(dependencies.intersection(required_modules))
        
        # Topological sort with parallel optimization
        steps = []
        remaining = set(required_modules)
        parallel_count = 0
        
        while remaining:
            # Find all modules with no remaining dependencies (can run in parallel)
            ready = [
                module_id for module_id in remaining 
                if in_degree[module_id] == 0
            ]
            
            if not ready:
                raise PipelineAnalysisError("Circular dependency detected in pipeline")
            
            # Create parallel execution step
            step_modules = []
            for module_id in ready:
                module_data = required_module_data[module_id]
                step_modules.append({
                    'id': module_id,
                    'templateId': module_data['templateId'],
                    'config': module_data.get('config', {}),
                    'position': module_data.get('position', {}),
                    'nodes': module_data.get('nodes', [])
                })
            
            steps.append({
                'step_number': len(steps) + 1,
                'modules': step_modules,
                'parallel': len(step_modules) > 1
            })
            
            if len(step_modules) > 1:
                parallel_count += 1
            
            # Remove ready modules and update in-degrees
            for module_id in ready:
                remaining.remove(module_id)
                
                # Decrease in-degree for dependent modules
                dependents = dependency_graph['dependents'].get(module_id, set())
                for dependent in dependents:
                    if dependent in remaining:
                        in_degree[dependent] -= 1
        
        return {
            'steps': steps,
            'parallel_count': parallel_count,
            'total_modules': len(required_modules)
        }
    
    def validate_pipeline(
        self,
        modules: List[Dict[str, Any]],
        connections: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Validate pipeline structure and requirements
        """
        try:
            # Check for Order Generation module
            has_order_gen = any(
                m.get('templateId') == 'order_generation' for m in modules
            )
            
            if not has_order_gen:
                return {
                    'valid': False,
                    'error': 'Pipeline must contain an Order Generation module'
                }
            
            # Build dependency graph to check for cycles
            dependency_graph = self._build_dependency_graph(modules, connections)
            
            # Try to find execution order (will fail if cycles exist)
            target_module = self._find_target_module(modules)
            required_modules = self._find_required_modules(
                dependency_graph, target_module['id']
            )
            
            self._create_execution_plan(modules, dependency_graph, required_modules)
            
            return {
                'valid': True,
                'modules_count': len(modules),
                'connections_count': len(connections),
                'required_modules_count': len(required_modules)
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': str(e),
                'stack': e.__traceback__
            }
    
    def _build_transformation_steps(
        self,
        processing_modules: List[Dict[str, Any]],
        connections: List[Dict[str, Any]],
        input_modules: List[Dict[str, Any]],
        output_modules: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Build transformation steps excluding input/output modules"""
        
        # Build dependency graph for processing modules only
        processing_graph = self._build_processing_dependency_graph(
            processing_modules, connections, input_modules, output_modules
        )
        
        # Create execution steps in topological order
        steps = []
        remaining_modules = set(m['id'] for m in processing_modules)
        in_degree = {m_id: 0 for m_id in remaining_modules}
        
        # Calculate in-degrees for processing modules
        for connection in connections:
            from_module = connection['from']['moduleId']
            to_module = connection['to']['moduleId']
            
            # Only count dependencies between processing modules
            if from_module in remaining_modules and to_module in remaining_modules:
                in_degree[to_module] += 1
        
        step_number = 1
        while remaining_modules:
            # Find modules with no dependencies
            ready_modules = [m_id for m_id in remaining_modules if in_degree[m_id] == 0]
            
            if not ready_modules:
                raise PipelineAnalysisError("Circular dependency detected in processing modules")
            
            # Create step for ready modules
            for module_id in ready_modules:
                module = next(m for m in processing_modules if m['id'] == module_id)
                
                # Find input and output field names for this module
                input_field = self._find_step_input_field(module_id, connections, input_modules, processing_modules)
                output_field = self._find_step_output_field(module_id, connections, output_modules, processing_modules)
                
                step = {
                    'step_number': step_number,
                    'module_id': module_id,
                    'template_id': module['templateId'],
                    'input_field': input_field,
                    'output_field': output_field,
                    'config': module.get('config', {})
                }
                steps.append(step)
                step_number += 1
            
            # Remove processed modules and update in-degrees
            for module_id in ready_modules:
                remaining_modules.remove(module_id)
                
                # Update in-degrees for dependent modules
                for connection in connections:
                    if connection['from']['moduleId'] == module_id:
                        to_module = connection['to']['moduleId']
                        if to_module in remaining_modules:
                            in_degree[to_module] -= 1
        
        return steps
    
    def _build_processing_dependency_graph(
        self,
        processing_modules: List[Dict[str, Any]],
        connections: List[Dict[str, Any]],
        input_modules: List[Dict[str, Any]],
        output_modules: List[Dict[str, Any]]
    ) -> Dict[str, Dict]:
        """Build dependency graph for processing modules only"""
        processing_ids = set(m['id'] for m in processing_modules)
        
        graph = {
            'dependencies': defaultdict(set),
            'dependents': defaultdict(set)
        }
        
        for connection in connections:
            from_module = connection['from']['moduleId']
            to_module = connection['to']['moduleId']
            
            # Only track dependencies between processing modules
            if from_module in processing_ids and to_module in processing_ids:
                graph['dependencies'][to_module].add(from_module)
                graph['dependents'][from_module].add(to_module)
        
        return graph
    
    def _find_step_input_field(
        self,
        module_id: str,
        connections: List[Dict[str, Any]],
        input_modules: List[Dict[str, Any]],
        processing_modules: List[Dict[str, Any]]
    ) -> str:
        """Find the input field name for a processing step"""
        
        # Find connection that feeds into this module
        for connection in connections:
            if connection['to']['moduleId'] == module_id:
                from_module_id = connection['from']['moduleId']
                from_output_idx = connection['from']['outputIndex']
                
                # Check if input comes from an input module
                input_module = next((m for m in input_modules if m['id'] == from_module_id), None)
                if input_module:
                    outputs = input_module.get('nodes', {}).get('outputs', [])
                    if from_output_idx < len(outputs):
                        return outputs[from_output_idx].get('name', f'input_{from_output_idx}')
                
                # Check if input comes from another processing module
                proc_module = next((m for m in processing_modules if m['id'] == from_module_id), None)
                if proc_module:
                    outputs = proc_module.get('nodes', {}).get('outputs', [])
                    if from_output_idx < len(outputs):
                        return outputs[from_output_idx].get('name', f'input_{from_output_idx}')
        
        return 'input'
    
    def _find_step_output_field(
        self,
        module_id: str,
        connections: List[Dict[str, Any]],
        output_modules: List[Dict[str, Any]],
        processing_modules: List[Dict[str, Any]]
    ) -> str:
        """Find the output field name for a processing step"""
        
        # Find this module's output field name
        module = next((m for m in processing_modules if m['id'] == module_id), None)
        if module:
            outputs = module.get('nodes', {}).get('outputs', [])
            if outputs:
                return outputs[0].get('name', 'output')
        
        return 'output'
    
    def _extract_input_fields(
        self,
        input_modules: List[Dict[str, Any]],
        connections: List[Dict[str, Any]]
    ) -> List[str]:
        """Extract input field names from input modules"""
        input_fields = []
        
        for module in input_modules:
            outputs = module.get('nodes', {}).get('outputs', [])
            for output in outputs:
                field_name = output.get('name', '')
                if field_name:
                    input_fields.append(field_name)
        
        return input_fields
    
    def _extract_output_fields(
        self,
        output_modules: List[Dict[str, Any]],
        connections: List[Dict[str, Any]]
    ) -> List[str]:
        """Extract output field names that are connected to output modules"""
        output_fields = []
        
        # We need to find all modules that connect TO the output modules
        # These are the fields that should be in the final output
        for module in output_modules:
            module_id = module['id']
            
            # Find connections that feed into this output module
            for connection in connections:
                if connection['to']['moduleId'] == module_id:
                    from_module_id = connection['from']['moduleId']
                    from_output_idx = connection['from']['outputIndex']
                    
                    # Find the source module to get the actual field name
                    source_module = None
                    for m in connections:  # We need access to all modules, not just output modules
                        # This is a limitation of the current design - we need all modules here
                        pass
                    
                    # For now, we'll extract this differently in the main analysis method
                    output_fields.append(f'output_field_{from_output_idx}')
        
        return output_fields
    
    def _extract_output_fields_from_all_modules(
        self,
        output_modules: List[Dict[str, Any]],
        connections: List[Dict[str, Any]],
        processing_modules: List[Dict[str, Any]],
        input_modules: List[Dict[str, Any]]
    ) -> List[str]:
        """Extract actual output field names by finding modules that connect to output modules"""
        output_fields = []
        all_modules = input_modules + processing_modules + output_modules
        
        for output_module in output_modules:
            output_module_id = output_module['id']
            
            # Find connections that feed into this output module
            for connection in connections:
                if connection['to']['moduleId'] == output_module_id:
                    from_module_id = connection['from']['moduleId']
                    from_output_idx = connection['from']['outputIndex']
                    
                    # Find the source module
                    source_module = next((m for m in all_modules if m['id'] == from_module_id), None)
                    if source_module:
                        outputs = source_module.get('nodes', {}).get('outputs', [])
                        if from_output_idx < len(outputs):
                            field_name = outputs[from_output_idx].get('name', f'output_{from_output_idx}')
                            output_fields.append(field_name)
                            self.logger.info(f"Found output field: {field_name} from module {from_module_id}")
                        else:
                            self.logger.warning(f"Output index {from_output_idx} out of range for module {from_module_id}")
                    else:
                        self.logger.warning(f"Source module {from_module_id} not found")
        
        return output_fields
    
    def _build_transformation_steps_simple(
        self,
        processing_modules: List[Dict[str, Any]],
        connections: List[Dict[str, Any]],
        input_modules: List[Dict[str, Any]],
        output_modules: List[Dict[str, Any]],
        field_mapper: SimpleFieldMapper
    ) -> List[Dict[str, Any]]:
        """Build transformation steps using user field names directly (no unique IDs)"""
        
        # Use the basic transformation steps method
        basic_steps = self._build_transformation_steps(
            processing_modules, connections, input_modules, output_modules
        )
        
        # Add field names to the mapper and return steps with field names as IDs
        simple_steps = []
        for step in basic_steps:
            input_field_name = step['input_field']
            output_field_name = step['output_field']
            
            # Add field names to the mapper
            field_mapper.add_field_name(input_field_name)
            field_mapper.add_field_name(output_field_name)
            
            # Use field names as IDs directly
            simple_step = {
                **step,
                'input_field_id': input_field_name,
                'output_field_id': output_field_name,
                'input_field_name': input_field_name,
                'output_field_name': output_field_name
            }
            simple_steps.append(simple_step)
            
            self.logger.info(f"Step {step['step_number']}: {input_field_name} -> [{step['template_id']}] -> {output_field_name}")
        
        return simple_steps
    
    
    def _extract_input_fields_simple(
        self,
        input_modules: List[Dict[str, Any]],
        connections: List[Dict[str, Any]],
        field_mapper: SimpleFieldMapper
    ) -> Dict[str, str]:
        """Extract input field names (simple mapping)"""
        input_field_mapping = {}  # field_name -> field_name (identity mapping)
        
        for module in input_modules:
            outputs = module.get('nodes', {}).get('outputs', [])
            for output in outputs:
                field_name = output.get('name', '')
                if field_name:
                    field_mapper.add_field_name(field_name)
                    input_field_mapping[field_name] = field_name
        
        return input_field_mapping
    
    def _extract_output_fields_simple(
        self,
        output_modules: List[Dict[str, Any]],
        connections: List[Dict[str, Any]],
        processing_modules: List[Dict[str, Any]],
        input_modules: List[Dict[str, Any]],
        field_mapper: SimpleFieldMapper
    ) -> Dict[str, str]:
        """Extract output field names (simple mapping)"""
        output_field_mapping = {}  # field_name -> field_name (identity mapping)
        all_modules = input_modules + processing_modules + output_modules
        
        for output_module in output_modules:
            output_module_id = output_module['id']
            
            # Find connections that feed into this output module
            for connection in connections:
                if connection['to']['moduleId'] == output_module_id:
                    from_module_id = connection['from']['moduleId']
                    from_output_idx = connection['from']['outputIndex']
                    
                    # Find the source module
                    source_module = next((m for m in all_modules if m['id'] == from_module_id), None)
                    if source_module:
                        outputs = source_module.get('nodes', {}).get('outputs', [])
                        if from_output_idx < len(outputs):
                            field_name = outputs[from_output_idx].get('name', f'output_{from_output_idx}')
                            field_mapper.add_field_name(field_name)
                            output_field_mapping[field_name] = field_name
                            self.logger.info(f"Output field mapping: {field_name} -> {field_name}")
        
        return output_field_mapping
    


# Global analyzer instance
_analyzer = None

def get_pipeline_analyzer() -> PipelineAnalyzer:
    """Get global pipeline analyzer instance"""
    global _analyzer
    if _analyzer is None:
        _analyzer = PipelineAnalyzer()
    return _analyzer