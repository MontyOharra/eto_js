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


# VisualState is now a simple Dict[str, Position] for flat structure
# FLAT STRUCTURE (new format after refactoring):
# All nodes (modules and entry points) stored in single flat dict
# - Module positions: {"module_id": {"x": float, "y": float}}
# - Entry point positions: {"entry-entry_id": {"x": float, "y": float}}
# Note: This replaces the old nested format {modules: {...}, entry_points: {...}}
VisualState = Dict[str, Position]


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


@dataclass(frozen=True)
class ModuleExecutionContext:
    """
    Context passed to module handlers during execution.

    Contains node metadata and references to services.
    Module handlers should access fields directly (e.g., context.outputs[0].node_id).
    """
    inputs: List[NodeInstance]  # Input pins metadata
    outputs: List[NodeInstance]  # Output pins metadata
    module_instance_id: str  # For debugging/logging
    services: Optional[Any] = None  # Access to service container (ServiceContainer type)