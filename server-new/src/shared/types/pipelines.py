"""
Pipeline Structure Types
Core data structures for pipeline execution and visualization using dataclasses
"""
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


@dataclass(frozen=True)
class NodeInstance:
    """Runtime instance of a pin in a module instance"""
    node_id: str
    type: str  # Selected type: "str", "int", "float", "bool", "datetime", etc.
    name: str
    position_index: int
    group_index: int  # Index of the NodeGroup in meta.io_shape.inputs.nodes or outputs.nodes


@dataclass(frozen=True)
class EntryPoint:
    """Entry point for pipeline input"""
    node_id: str
    name: str


@dataclass(frozen=True)
class ModuleInstance:
    """A module instance placed on the canvas"""
    module_instance_id: str
    module_ref: str  # e.g., "text_cleaner:1.0.0"
    config: Dict[str, Any]  # Module-specific configuration
    inputs: List[NodeInstance] = field(default_factory=list)  # Flat list, grouped by group_index
    outputs: List[NodeInstance] = field(default_factory=list)


@dataclass(frozen=True)
class NodeConnection:
    """Connection between two nodes"""
    from_node_id: str
    to_node_id: str


@dataclass(frozen=True)
class Position:
    """2D position for visual layout"""
    x: float
    y: float


@dataclass(frozen=True)
class PipelineState:
    """The actual pipeline structure (execution data)"""
    entry_points: List[EntryPoint] = field(default_factory=list)
    modules: List[ModuleInstance] = field(default_factory=list)
    connections: List[NodeConnection] = field(default_factory=list)


@dataclass(frozen=True)
class VisualState:
    """Visual positioning data for the UI"""
    modules: Dict[str, Position] = field(default_factory=dict)
    entry_points: Dict[str, Position] = field(default_factory=dict)


@dataclass(frozen=True)
class PinInfo:
    """Information about a pin for index lookups"""
    node_id: str
    type: str
    direction: str  # "entry" | "in" | "out"
    name: str
    module_instance_id: Optional[str] = None


@dataclass(frozen=True)
class PipelineIndices:
    """
    Index structures for fast pipeline lookups.

    Built once during pipeline processing to avoid repeated iterations.
    """
    pin_by_id: Dict[str, PinInfo] = field(default_factory=dict)
    module_by_id: Dict[str, ModuleInstance] = field(default_factory=dict)
    input_to_upstream: Dict[str, str] = field(default_factory=dict)  # Input pin → upstream output pin


@dataclass
class ModuleExecutionContext:
    """
    Context passed to module handlers during execution.

    Contains node metadata and references to services with helper methods
    for accessing pin information.
    """
    inputs: List[NodeInstance]  # Input pins metadata
    outputs: List[NodeInstance]  # Output pins metadata
    module_instance_id: str  # For debugging/logging
    services: Optional[Any] = None  # Access to service container (ServiceContainer type)

    def get_input_type(self, index: int = 0) -> str:
        """Get type of input at given index"""
        if not self.inputs:
            raise IndexError("No inputs in context")
        if index >= len(self.inputs):
            raise IndexError(f"Input index {index} out of range")
        return self.inputs[index].type

    def get_output_type(self, index: int = 0) -> str:
        """Get type of output at given index"""
        if not self.outputs:
            raise IndexError("No outputs in context")
        if index >= len(self.outputs):
            raise IndexError(f"Output index {index} out of range")
        return self.outputs[index].type

    def get_input_names(self) -> Dict[str, str]:
        """Get mapping of node_id to user-assigned names"""
        return {pin.node_id: pin.name for pin in self.inputs}

    def get_output_names(self) -> Dict[str, str]:
        """Get mapping of node_id to user-assigned names"""
        return {pin.node_id: pin.name for pin in self.outputs}

    def resolve_placeholders(self, template: str, inputs: Dict[str, Any]) -> str:
        """Replace {name} placeholders with actual values"""
        result = template
        # Replace input placeholders
        for pin in self.inputs:
            placeholder = f"{{{pin.name}}}"
            value = inputs.get(pin.node_id, "")
            result = result.replace(placeholder, str(value))
        # Also support output placeholders for prompts
        for pin in self.outputs:
            placeholder = f"{{{pin.name}}}"
            # Keep output placeholders as-is for LLM to understand
            result = result.replace(placeholder, f"[{pin.name}]")
        return result

    def get_input_by_name(self, name: str, inputs: Dict[str, Any]) -> Any:
        """Get input value by user-assigned name"""
        for pin in self.inputs:
            if pin.name == name:
                return inputs.get(pin.node_id)
        raise KeyError(f"No input with name '{name}'")

    def get_input_groups(self) -> Dict[int, List[NodeInstance]]:
        """Get inputs organized by group"""
        groups: Dict[int, List[NodeInstance]] = {}
        for pin in self.inputs:
            if pin.group_index not in groups:
                groups[pin.group_index] = []
            groups[pin.group_index].append(pin)
        return groups

    def get_output_groups(self) -> Dict[int, List[NodeInstance]]:
        """Get outputs organized by group"""
        groups: Dict[int, List[NodeInstance]] = {}
        for pin in self.outputs:
            if pin.group_index not in groups:
                groups[pin.group_index] = []
            groups[pin.group_index].append(pin)
        return groups