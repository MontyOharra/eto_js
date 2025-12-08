"""
Pipeline Compilation
Compiles pruned pipeline into ordered execution steps with proper layer-based topological sorting
"""
from typing import List, Dict, Set
import logging

from shared.types.pipelines import PipelineState, PipelineIndices, ModuleInstance, NodeConnection, OutputChannelInstance
from shared.types.pipeline_definition_step import PipelineDefinitionStepCreate

logger = logging.getLogger(__name__)


class PipelineCompiler:
    """
    Compiles pruned pipeline into executable steps.

    Uses layer-based topological sorting to enable parallel execution in Dask.
    Each layer contains modules that can run in parallel (no dependencies between them).
    """

    @staticmethod
    def compile(pruned_pipeline: PipelineState, indices: PipelineIndices) -> List[PipelineDefinitionStepCreate]:
        """
        Compile pruned pipeline to ordered execution steps.

        Args:
            pruned_pipeline: Validated and pruned pipeline state
            indices: Pre-built indices for efficient lookups

        Returns:
            List of PipelineDefinitionStepCreate objects ordered by layer

        Raises:
            RuntimeError: If topological sort fails (indicates cycle, should be caught in validation)
        """
        # Step 1: Compute topological layers for parallel execution
        layers = PipelineCompiler._compute_topological_layers(pruned_pipeline, indices)

        logger.debug(f"Computed {len(layers)} execution layers with {sum(len(layer) for layer in layers)} modules")

        # Step 2: Build execution steps from layers
        steps = PipelineCompiler._build_steps(pruned_pipeline, layers, indices)

        return steps

    @staticmethod
    def _compute_topological_layers(
        pipeline: PipelineState,
        indices: PipelineIndices
    ) -> List[List[str]]:
        """
        Compute topological execution layers using Kahn's algorithm with layer tracking.

        Each layer contains modules that can execute in parallel.
        Modules in layer N depend only on modules in layers < N.

        Args:
            pipeline: Pipeline state
            indices: Pipeline indices

        Returns:
            List of layers, where each layer is a list of module_instance_ids
            Example: [["m1", "m2"], ["m3"], ["m4", "m5"]]

        Raises:
            RuntimeError: If cycle detected (shouldn't happen after validation)
        """
        # Build adjacency list and in-degree count
        adjacency: Dict[str, Set[str]] = {
            module.module_instance_id: set() for module in pipeline.modules
        }
        in_degree: Dict[str, int] = {
            module.module_instance_id: 0 for module in pipeline.modules
        }

        # Build dependency graph (module-level)
        for connection in pipeline.connections:
            source_pin = indices.pin_by_id.get(connection.from_node_id)
            target_pin = indices.pin_by_id.get(connection.to_node_id)

            # Skip if pins not found or if source is entry point
            if not source_pin or not target_pin:
                continue
            if source_pin.module_instance_id is None:
                continue
            if target_pin.module_instance_id is None:
                continue

            source_module = source_pin.module_instance_id
            target_module = target_pin.module_instance_id

            # Skip self-loops
            if source_module == target_module:
                continue

            # Add edge if not already present
            if target_module not in adjacency[source_module]:
                adjacency[source_module].add(target_module)
                in_degree[target_module] += 1

        # Kahn's algorithm with layer tracking
        layers: List[List[str]] = []
        current_layer = [module_id for module_id, degree in in_degree.items() if degree == 0]
        processed_count = 0

        while current_layer:
            # Sort current layer for deterministic ordering
            current_layer.sort()
            layers.append(current_layer)
            processed_count += len(current_layer)

            # Build next layer
            next_layer = []
            for module_id in current_layer:
                # Decrease in-degree for all downstream modules
                for downstream in adjacency[module_id]:
                    in_degree[downstream] -= 1
                    if in_degree[downstream] == 0:
                        next_layer.append(downstream)

            current_layer = next_layer

        # Sanity check: all modules should be processed
        if processed_count != len(pipeline.modules):
            raise RuntimeError(
                f"Topological sort failed: processed {processed_count} of {len(pipeline.modules)} modules. "
                f"This indicates a cycle (should have been caught in validation)."
            )

        return layers

    @staticmethod
    def _build_steps(
        pipeline: PipelineState,
        layers: List[List[str]],
        indices: PipelineIndices
    ) -> List[PipelineDefinitionStepCreate]:
        """
        Build PipelineDefinitionStepCreate objects from topological layers.

        Args:
            pipeline: Pruned pipeline state
            layers: Topological layers of module_instance_ids
            indices: Pipeline indices

        Returns:
            List of step creation objects
        """
        steps: List[PipelineDefinitionStepCreate] = []

        for layer_number, layer in enumerate(layers):
            for module_id in layer:
                module = indices.module_by_id[module_id]

                # DEBUG: Log module inputs before creating node_metadata
                logger.debug(f"[COMPILATION DEBUG] module_id={module_id}")
                logger.debug(f"[COMPILATION DEBUG] module.inputs={module.inputs}")
                for inp in module.inputs:
                    logger.debug(f"[COMPILATION DEBUG]   Input pin: node_id={inp.node_id}, name={inp.name}, group_index={inp.group_index}")

                # Build input field mappings
                input_field_mappings = PipelineCompiler._build_input_mappings(
                    module, pipeline.connections
                )

                # Build node metadata (preserve pin information for executor)
                node_metadata = {
                    "inputs": list(module.inputs),
                    "outputs": list(module.outputs)
                }

                # DEBUG: Log what's in node_metadata
                logger.debug(f"[COMPILATION DEBUG] node_metadata inputs={node_metadata['inputs']}")

                # Extract module_id from module_ref (format: "module_id:version")
                # The module_ref column has FK to module_catalog.id which only contains module_id
                module_id = module.module_ref.split(":")[0] if ":" in module.module_ref else module.module_ref

                # Create step
                step = PipelineDefinitionStepCreate(
                    pipeline_definition_id=0,  # Will be set by service layer
                    module_instance_id=module.module_instance_id,
                    module_ref=module_id,  # Just the module ID (not "id:version")
                    module_config=module.config,
                    input_field_mappings=input_field_mappings,
                    node_metadata=node_metadata,
                    step_number=layer_number  # Layer number, not sequential!
                )
                steps.append(step)

        # Build output channel steps (terminal collection points)
        output_channel_steps = PipelineCompiler._build_output_channel_steps(
            pipeline, layers
        )
        steps.extend(output_channel_steps)

        return steps

    @staticmethod
    def _build_input_mappings(
        module: ModuleInstance,
        connections: List[NodeConnection]
    ) -> Dict[str, str]:
        """
        Build input field mappings for a module.

        Maps each input pin to its source (upstream output pin or entry point).

        Args:
            module: Module to build mappings for
            connections: All pipeline connections

        Returns:
            Dict mapping input_pin_id → source_pin_id

        Example:
            {
                "m2:i0": "entry_hawb",    # From entry point
                "m2:i1": "m1:o0"          # From upstream module
            }
        """
        mappings: Dict[str, str] = {}

        # Get all input pin IDs for this module
        input_pin_ids = {pin.node_id for pin in module.inputs}

        # Find connections that target these inputs
        for conn in connections:
            if conn.to_node_id in input_pin_ids:
                # This connection feeds one of our inputs
                mappings[conn.to_node_id] = conn.from_node_id

        return mappings

    @staticmethod
    def _build_output_channel_steps(
        pipeline: PipelineState,
        layers: List[List[str]]
    ) -> List[PipelineDefinitionStepCreate]:
        """
        Build steps for output channels (terminal collection points).

        Output channels are placed in the layer after all modules,
        ensuring they execute last and collect final values.

        Args:
            pipeline: Pruned pipeline state
            layers: Topological layers of module_instance_ids

        Returns:
            List of output channel step creation objects
        """
        if not pipeline.output_channels:
            return []

        # Output channels go in the layer after all modules
        final_layer = len(layers) if layers else 0

        steps: List[PipelineDefinitionStepCreate] = []

        for output_channel in pipeline.output_channels:
            # Build input mappings (channel input pin → upstream source)
            input_field_mappings = PipelineCompiler._build_output_channel_input_mappings(
                output_channel, pipeline.connections
            )

            # Build node metadata (inputs only, no outputs for terminal nodes)
            node_metadata = {
                "inputs": list(output_channel.inputs),
                "outputs": []
            }

            # Create step with NULL module_ref to indicate output channel
            step = PipelineDefinitionStepCreate(
                pipeline_definition_id=0,  # Will be set by service layer
                module_instance_id=output_channel.output_channel_instance_id,
                module_ref=None,  # NULL indicates output channel step
                module_config={"channel_type": output_channel.channel_type},
                input_field_mappings=input_field_mappings,
                node_metadata=node_metadata,
                step_number=final_layer
            )
            steps.append(step)

            logger.debug(
                f"Created output channel step: {output_channel.output_channel_instance_id} "
                f"(channel_type={output_channel.channel_type}, layer={final_layer})"
            )

        logger.info(f"Added {len(steps)} output channel steps at layer {final_layer}")

        return steps

    @staticmethod
    def _build_output_channel_input_mappings(
        output_channel: OutputChannelInstance,
        connections: List[NodeConnection]
    ) -> Dict[str, str]:
        """
        Build input field mappings for an output channel.

        Maps the output channel's input pin to its upstream source.

        Args:
            output_channel: Output channel to build mappings for
            connections: All pipeline connections

        Returns:
            Dict mapping input_pin_id → source_pin_id
        """
        mappings: Dict[str, str] = {}

        # Get all input pin IDs for this output channel
        input_pin_ids = {pin.node_id for pin in output_channel.inputs}

        # Find connections that target these inputs
        for conn in connections:
            if conn.to_node_id in input_pin_ids:
                mappings[conn.to_node_id] = conn.from_node_id

        return mappings
