"""
Graph Builder
Builds NetworkX graph from pipeline state for cycle detection and topological sorting
"""
import networkx as nx

from shared.types import PipelineState, PipelineIndices


class GraphBuilder:
    """
    Builds NetworkX directed graph from pipeline connections

    The graph represents data flow at the pin level:
    - Nodes: All pin node_ids (entry points, inputs, outputs)
    - Edges: Connections from output pins to input pins
    """

    @staticmethod
    def build_pin_graph(pipeline_state: PipelineState, indices: PipelineIndices) -> nx.DiGraph:
        """
        Build directed graph from pipeline connections

        Args:
            pipeline_state: Pipeline state with connections
            indices: Pre-built indices for pin lookups

        Returns:
            NetworkX DiGraph with pins as nodes and connections as edges
        """
        graph = nx.DiGraph()

        # Add all pins as nodes with their metadata
        for node_id, pin_info in indices.pin_by_id.items():
            graph.add_node(
                node_id,
                type=pin_info.type,
                direction=pin_info.direction,
                module_instance_id=pin_info.module_instance_id,
                name=pin_info.name
            )

        # Add edges from connections (from_node_id -> to_node_id)
        for connection in pipeline_state.connections:
            graph.add_edge(
                connection.from_node_id,
                connection.to_node_id
            )

        # Add internal module edges (inputs -> outputs within each module)
        # This represents data flow through module processing
        for module in pipeline_state.modules:
            # Connect all inputs to all outputs within the module
            # (since processing a module means all inputs affect all outputs)
            for input_pin in module.inputs:
                for output_pin in module.outputs:
                    graph.add_edge(input_pin.node_id, output_pin.node_id)

        return graph

    @staticmethod
    def find_cycles(graph: nx.DiGraph) -> list:
        """
        Find all simple cycles in the graph

        Args:
            graph: NetworkX DiGraph to check

        Returns:
            List of cycles, where each cycle is a list of node_ids
        """
        try:
            # nx.simple_cycles returns generator of cycles
            cycles = list(nx.simple_cycles(graph))
            return cycles
        except Exception:
            # If graph analysis fails, return empty list
            return []
