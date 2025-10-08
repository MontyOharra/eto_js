from pydantic import BaseModel, Field
from typing import Dict, Any, List

from .modules import ModuleKind

# Supporting types for pipeline structure
class InstanceNodePin(BaseModel):
    """Runtime instance of a pin in a module instance"""
    node_id: str
    type: str  # Selected type: "str", "int", "float", "bool", "datetime", etc.
    name: str
    position_index: int
    group_index: int  # Index of the NodeGroup in meta.io_shape.inputs.nodes or outputs.nodes


class ModuleInstance(BaseModel):
    """A module instance placed on the canvas"""
    module_instance_id: str
    module_ref: str  # e.g., "text_cleaner:1.0.0"
    module_kind: ModuleKind
    config: Dict[str, Any]  # Module-specific configuration
    inputs: List[InstanceNodePin] = Field(default_factory=list)  # Flat list, grouped by group_index
    outputs: List[InstanceNodePin] = Field(default_factory=list)


class NodeConnection(BaseModel):
    """Connection between two nodes"""
    from_node_id: str
    to_node_id: str


class EntryPoint(BaseModel):
    """Entry point for pipeline input"""
    node_id: str
    name: str


class PipelineState(BaseModel):
    """The actual pipeline structure (execution data)"""
    entry_points: List[EntryPoint] = Field(default_factory=list)
    modules: List[ModuleInstance] = Field(default_factory=list)
    connections: List[NodeConnection] = Field(default_factory=list)


class ModulePosition(BaseModel):
    """Position of a module on the canvas"""
    x: float
    y: float


class VisualState(BaseModel):
    """Visual positioning data for the UI"""
    modules: Dict[str, ModulePosition] = Field(default_factory=dict)
    entry_points: Dict[str, ModulePosition] = Field(default_factory=dict)
