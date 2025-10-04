"""
Index Builder
Builds lookup indices for efficient validation (§2.2 from spec)
"""
from typing import Dict, List, Optional
from pydantic import BaseModel
from src.shared.models.pipeline import PipelineState, ModuleInstance


class PinInfo(BaseModel):
    """Information about a pin for index lookups"""
    node_id: str
    type: str
    module_instance_id: Optional[str] = None  # None for entry points
    direction: str  # "entry" | "in" | "out"
    name: str


class PipelineIndices:
    """
    Lookup indices for efficient validation (§2.2)
    Built once and used by all validation stages
    Can be persisted throughout the validation service process
    """

    def __init__(self, pipeline_state: PipelineState):
        """
        Build all indices from pipeline state

        Args:
            pipeline_state: Pipeline state to index
        """
        self.pin_by_id: Dict[str, PinInfo] = {}
        self.module_by_id: Dict[str, ModuleInstance] = {}
        self.input_to_upstream: Dict[str, str] = {}
        self.output_to_downstreams: Dict[str, List[str]] = {}

        self._build_indices(pipeline_state)

    def _build_indices(self, pipeline_state: PipelineState):
        """Build all indices from pipeline state"""
        self._build_pin_index(pipeline_state)
        self._build_module_index(pipeline_state)
        self._build_connection_indices(pipeline_state)

    def _build_pin_index(self, pipeline_state: PipelineState):
        """
        Build pin_by_id index from entry points and module pins

        Entry points are indexed with direction="entry" and type="str"
        Module pins are indexed with their actual types and directions
        """
        # Entry points - always output str
        for ep in pipeline_state.entry_points:
            self.pin_by_id[ep.node_id] = PinInfo(
                node_id=ep.node_id,
                type="str",  # Entry points always output str
                module_instance_id=None,
                direction="entry",
                name=ep.name
            )

        # Module pins
        for module in pipeline_state.modules:
            # Input pins
            for pin in module.inputs:
                self.pin_by_id[pin.node_id] = PinInfo(
                    node_id=pin.node_id,
                    type=pin.type,
                    module_instance_id=module.module_instance_id,
                    direction="in",
                    name=pin.name
                )

            # Output pins
            for pin in module.outputs:
                self.pin_by_id[pin.node_id] = PinInfo(
                    node_id=pin.node_id,
                    type=pin.type,
                    module_instance_id=module.module_instance_id,
                    direction="out",
                    name=pin.name
                )

    def _build_module_index(self, pipeline_state: PipelineState):
        """Build module_by_id index for fast module lookups"""
        for module in pipeline_state.modules:
            self.module_by_id[module.module_instance_id] = module

    def _build_connection_indices(self, pipeline_state: PipelineState):
        """
        Build connection indices

        input_to_upstream: Maps each input pin to its upstream output pin
        output_to_downstreams: Maps each output pin to all downstream input pins
        """
        for conn in pipeline_state.connections:
            # Each input has exactly one upstream
            self.input_to_upstream[conn.to_node_id] = conn.from_node_id

            # Each output can have multiple downstreams (fan-out)
            if conn.from_node_id not in self.output_to_downstreams:
                self.output_to_downstreams[conn.from_node_id] = []
            self.output_to_downstreams[conn.from_node_id].append(conn.to_node_id)
