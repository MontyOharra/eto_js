"""
Pipeline Compiler
Orchestrates compilation: pruning, checksum calculation, topological sorting, and step building
"""

import json
from typing import List, Tuple, Dict

from shared.types import (
    PipelineState,
    PipelineDefinitionStepCreate,
    ModuleInstance,
    NodeConnection,
)

from .topological_sorter import TopologicalSorter


class CompilationResult:
    """Result of pipeline compilation"""

    def __init__(self, steps: List[PipelineDefinitionStepCreate], checksum: str):
        self.steps = steps
        self.checksum = checksum
        self.step_count = len(steps)
        # Calculate layer count from step numbers
        self.layer_count = (
            max((s.step_number for s in steps), default=-1) + 1 if steps else 0
        )


class PipelineCompiler:
    """
    Builds pipeline step domain objects from a pruned pipeline

    This is a pure transformation utility - it doesn't touch the database.
    The Service layer handles pruning, checksum calculation, cache checking, and persistence.

    Responsibility:
        - Take a PRUNED pipeline and checksum
        - Compute topological layers
        - Build PipelineStepCreate domain objects
    """

    @staticmethod
    def compile(
        pruned_pipeline: PipelineState, checksum: str
    ) -> List[PipelineDefinitionStepCreate]:
        """
        Compile pruned pipeline to executable step domain objects

        Args:
            pruned_pipeline: ALREADY PRUNED pipeline (action-reachable modules only)
            checksum: Plan checksum (already calculated by service)

        Returns:
            List[PipelineStepCreate] - Domain objects ready to save to DB

        Note:
            This method assumes the pipeline is already:
            1. Validated (by PipelineValidator)
            2. Pruned (by GraphPruner)
            3. Checksummed (by ChecksumCalculator)

            The service layer orchestrates these steps.

        Example:
            # In service:
            pruned = GraphPruner.prune(pipeline, reachable_modules)
            checksum = ChecksumCalculator.compute(pruned)
            steps = PipelineCompiler.compile(pruned, checksum)
            step_repo.save_steps(steps)
        """
        # Step 1: Compute topological layers for execution order
        layers = TopologicalSorter.sort(pruned_pipeline)

        # Step 2: Build PipelineStepCreate domain objects
        steps = PipelineCompiler._build_steps(pruned_pipeline, layers, checksum)

        return steps

    @staticmethod
    def _build_steps(
        pipeline: PipelineState, layers: List[List[str]], checksum: str
    ) -> List[PipelineDefinitionStepCreate]:
        """
        Build PipelineStepCreate domain objects from topological layers

        Args:
            pipeline: Pruned pipeline state
            layers: List of layers, each containing module_instance_ids
                   Example: [["m1", "m2"], ["m3"], ["m4", "m5"]]
                   Layer 0 can run in parallel, then layer 1, etc.
            checksum: Plan checksum for all steps

        Returns:
            List of PipelineStepCreate domain objects (not yet saved to DB)
        """
        # Build lookups for fast access
        pin_to_module = PipelineCompiler._build_pin_to_module_lookup(pipeline)
        module_lookup = {m.module_instance_id: m for m in pipeline.modules}

        # Flatten layers into steps with step_number
        steps = []
        step_number = 0

        for layer in layers:
            for module_id in layer:
                module = module_lookup[module_id]

                # Build input/output mappings for this module
                input_mappings = PipelineCompiler._build_input_mappings(
                    module, pipeline.connections, pin_to_module
                )
                output_names = PipelineCompiler._build_output_names(module)

                # Build node metadata from module's pin information
                node_metadata = {
                    "inputs": module.inputs,  # List[InstanceNodePin]
                    "outputs": module.outputs,  # List[InstanceNodePin]
                }

                # Create PipelineStepCreate domain object
                step = PipelineDefinitionStepCreate(
                    plan_checksum=checksum,
                    module_instance_id=module.module_instance_id,
                    module_ref=module.module_ref,
                    module_kind=module.module_kind,
                    module_config=module.config,  # Dict (will be JSON-ified by model_dump_for_db)
                    input_field_mappings=input_mappings,  # Dict
                    node_metadata=node_metadata,  # NEW: Preserve complete pin metadata
                    step_number=step_number,
                )
                steps.append(step)
                step_number += 1

        return steps

    @staticmethod
    def _build_pin_to_module_lookup(pipeline: PipelineState) -> Dict[str, str]:
        """
        Build lookup: pin_node_id → module_instance_id (or "entry")

        This allows us to trace connections back to their source modules.
        Entry points map to "entry" as their source.

        Args:
            pipeline: Pipeline state

        Returns:
            Dict mapping pin node_id to module_instance_id or "entry"

        Example:
            {
                "entry_1": "entry",
                "m1:i0": "m1",
                "m1:o0": "m1",
                "m2:i0": "m2",
                ...
            }
        """
        lookup = {}

        # Entry points map to "entry"
        for entry in pipeline.entry_points:
            lookup[entry.node_id] = "entry"

        # Module pins map to their module
        for module in pipeline.modules:
            for pin in module.inputs:
                lookup[pin.node_id] = module.module_instance_id
            for pin in module.outputs:
                lookup[pin.node_id] = module.module_instance_id

        return lookup

    @staticmethod
    def _build_input_mappings(
        module: ModuleInstance,
        connections: List[NodeConnection],
        pin_to_module: Dict[str, str],
    ) -> Dict[str, str]:
        """
        Build input field mappings for a module

        For each input pin, find the connection that feeds it and
        determine the source (entry point or upstream module output).

        Args:
            module: The module to build mappings for
            connections: All pipeline connections
            pin_to_module: Lookup from pin_id to module_id

        Returns:
            Dict mapping input_pin_id to source_node_id

        Example:
            {
                "m1:i0": "entry_email",      # From entry point
                "m1:i1": "upstream_m0:o0"    # From upstream module output
            }
        """
        mappings = {}

        # Get all input pin IDs for this module
        input_pin_ids = {pin.node_id for pin in module.inputs}

        # Find connections that target these inputs
        for conn in connections:
            if conn.to_node_id in input_pin_ids:
                # This connection feeds one of our inputs
                mappings[conn.to_node_id] = conn.from_node_id

        return mappings

    @staticmethod
    def _build_output_names(module: ModuleInstance) -> Dict[str, str]:
        """
        Build output display names for a module

        Creates human-readable labels for each output pin.
        These are used for UI display and debugging.

        Args:
            module: The module to build names for

        Returns:
            Dict mapping output_pin_id to display name

        Example:
            {
                "m1:o0": "Cleaned Text",
                "m1:o1": "Metadata"
            }
        """
        names = {}

        for pin in module.outputs:
            # Use pin name, fallback to position index
            display_name = pin.name or f"Output {pin.position_index}"
            names[pin.node_id] = display_name

        return names
