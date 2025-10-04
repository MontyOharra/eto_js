"""
Graph Pruner
Prunes pipeline to action-reachable modules only (§3.1 from spec)
"""
from typing import Set
from src.shared.models.pipeline import PipelineState


class GraphPruner:
    """
    Prunes pipeline graph to action-reachable modules only

    Removes "dead branch" modules that don't contribute to action execution.
    Dead branches are modules that have no path to any action module.
    """

    @staticmethod
    def prune(
        pipeline_state: PipelineState,
        reachable_modules: Set[str]
    ) -> PipelineState:
        """
        Prune pipeline to reachable modules only

        Algorithm:
        1. Build set of reachable pin node_ids (from reachable modules)
        2. Filter modules: keep only those in reachable_modules set
        3. Filter connections: keep only those where both pins are reachable
        4. Keep all entry points (they're external inputs, always needed)

        Args:
            pipeline_state: Original validated pipeline state
            reachable_modules: Set of module_instance_ids that are reachable from actions

        Returns:
            Pruned PipelineState with only action-reachable modules

        Note:
            Original pipeline_state is not modified (returns new instance)
        """
        # Step 1: Build set of reachable pin node_ids
        reachable_pins = set()

        for module in pipeline_state.modules:
            if module.module_instance_id in reachable_modules:
                # Add all pins from this reachable module
                for pin in module.inputs:
                    reachable_pins.add(pin.node_id)
                for pin in module.outputs:
                    reachable_pins.add(pin.node_id)

        # Also add entry point node_ids (they can connect to reachable modules)
        for entry_point in pipeline_state.entry_points:
            reachable_pins.add(entry_point.node_id)

        # Step 2: Filter modules to reachable only
        pruned_modules = [
            module for module in pipeline_state.modules
            if module.module_instance_id in reachable_modules
        ]

        # Step 3: Filter connections to those between reachable pins
        pruned_connections = [
            conn for conn in pipeline_state.connections
            if conn.from_node_id in reachable_pins and conn.to_node_id in reachable_pins
        ]

        # Step 4: Keep all entry points (they're pipeline inputs, always needed)
        pruned_entry_points = pipeline_state.entry_points

        # Return new PipelineState with pruned data
        return PipelineState(
            entry_points=pruned_entry_points,
            modules=pruned_modules,
            connections=pruned_connections
        )
