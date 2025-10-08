"""
Topological Sorter
Computes execution order by organizing modules into dependency layers
"""

from typing import List, Dict
import networkx as nx

from shared.typespipeline_definitions import PipelineState


class TopologicalSorter:
    """
    Computes topological execution layers for pipeline modules

    Modules are organized into layers where:
    - All modules in a layer can execute in parallel (no dependencies between them)
    - Each layer depends only on previous layers
    - Layer ordering provides execution sequence
    """

    @staticmethod
    def sort(pruned_pipeline: PipelineState) -> List[List[str]]:
        """
        Compute execution layers using topological sort

        Algorithm:
        1. Build module-level dependency graph (modules as nodes, dependencies as edges)
        2. Use NetworkX topological_generations to compute layers
        3. Return ordered list of layers

        Args:
            pruned_pipeline: Pruned PipelineState with only reachable modules

        Returns:
            List of execution layers, where each layer is a list of module_instance_ids

        Example:
            Input: entry → [A, B] → C → action
            Output: [['A', 'B'], ['C'], ['action']]

        Note:
            - Assumes pipeline is a valid DAG (already validated)
            - Entry points are not modules, so they're not in the layers
            - Execution proceeds layer by layer (0, 1, 2, ...)
        """
        # Step 1: Build module-level dependency graph
        module_graph = TopologicalSorter._build_module_graph(pruned_pipeline)

        # Step 2: Compute topological generations (layers)
        layers = list(nx.topological_generations(module_graph))

        # Step 3: Return layers
        return layers

    @staticmethod
    def _build_module_graph(pipeline: PipelineState) -> nx.DiGraph:
        """
        Build module-level dependency graph

        Creates a directed graph where:
        - Nodes: module_instance_ids
        - Edges: A → B if output of A connects to input of B

        Args:
            pipeline: PipelineState with modules and connections

        Returns:
            NetworkX DiGraph with modules as nodes
        """
        graph = nx.DiGraph()

        # Step 1: Build pin-to-module lookup
        pin_to_module: Dict[str, str] = {}

        for module in pipeline.modules:
            # Map all input pins to this module
            for pin in module.inputs:
                pin_to_module[pin.node_id] = module.module_instance_id
            # Map all output pins to this module
            for pin in module.outputs:
                pin_to_module[pin.node_id] = module.module_instance_id

        # Step 2: Add all modules as nodes
        for module in pipeline.modules:
            graph.add_node(module.module_instance_id)

        # Step 3: Add edges based on connections
        for connection in pipeline.connections:
            from_pin = connection.from_node_id
            to_pin = connection.to_node_id

            # Get modules for these pins
            from_module = pin_to_module.get(from_pin)
            to_module = pin_to_module.get(to_pin)

            # Add edge if both pins belong to modules (skip entry points)
            # and modules are different (skip self-loops)
            if from_module and to_module and from_module != to_module:
                graph.add_edge(from_module, to_module)

        return graph
