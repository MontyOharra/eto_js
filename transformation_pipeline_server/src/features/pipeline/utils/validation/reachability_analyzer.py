"""
Reachability Analyzer
Analyzes which modules are reachable from action modules (§2.6 from spec)
"""

import networkx as nx

from typing import Set, List, Tuple
from shared.types import PipelineState, PipelineIndices

from shared.exceptions import PipelineValidationError, PipelineValidationErrorCode


class ReachabilityAnalyzer:
    """
    Analyzes action-reachability in pipelines

    Ensures:
    - Pipeline has at least one action module
    - Identifies modules reachable from actions (for compilation)
    """

    @staticmethod
    def analyze(pipeline_state: PipelineState, indices: PipelineIndices, pin_graph: nx.DiGraph) -> Tuple[Set[str], List[PipelineValidationError]]:
        """
        Analyze action-reachability

        Args:
            pipeline_state: Pipeline state to analyze
            indices: Pre-built indices
            pin_graph: Pin-level directed graph

        Returns:
            Tuple of (reachable_module_ids, validation_errors)
        """
        errors = []
        reachable_module_ids = set()

        # Step 1: Identify action modules
        action_modules = [
            module
            for module in pipeline_state.modules
            if module.module_kind == "action"
        ]

        if not action_modules:
            errors.append(
                PipelineValidationError(
                    code=PipelineValidationErrorCode.NO_ACTIONS,
                    message="Pipeline must contain at least one action module",
                    where={"module_count": len(pipeline_state.modules)},
                )
            )
            return set(), errors

        # Step 2: Find all modules reachable from action inputs
        # We traverse backward from action input pins to find all upstream modules
        action_input_pins = []
        for action_module in action_modules:
            action_input_pins.extend([pin.node_id for pin in action_module.inputs])

        # Reverse BFS from action inputs
        visited_pins = set()
        to_visit = list(action_input_pins)

        while to_visit:
            pin_id = to_visit.pop(0)

            if pin_id in visited_pins:
                continue

            visited_pins.add(pin_id)

            # Get pin info to find its module
            pin_info = indices.pin_by_id.get(pin_id)
            if pin_info and pin_info.module_instance_id:
                reachable_module_ids.add(pin_info.module_instance_id)

            # Find upstream pins (predecessors in the graph)
            if pin_id in pin_graph:
                predecessors = list(pin_graph.predecessors(pin_id))
                to_visit.extend(predecessors)

        # Add action modules themselves to reachable set
        for action_module in action_modules:
            reachable_module_ids.add(action_module.module_instance_id)

        return reachable_module_ids, errors
