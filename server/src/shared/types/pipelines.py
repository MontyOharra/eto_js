"""
Pipeline Structure Types
Core data structures for pipeline execution and visualization using Pydantic
"""
from typing import Any, TypeAlias

from pydantic import BaseModel, ConfigDict, Field


class NodeInstance(BaseModel):
    """Runtime instance of a pin in a module instance"""
    model_config = ConfigDict(frozen=True)

    node_id: str
    type: str  # Selected type: "str", "int", "float", "bool", "datetime", etc.
    name: str
    position_index: int
    group_index: int  # Index of the NodeGroup in meta.io_shape.inputs.nodes or outputs.nodes


class EntryPoint(BaseModel):
    """Entry point for pipeline - structured like a module with outputs"""
    model_config = ConfigDict(frozen=True)

    entry_point_id: str
    name: str
    outputs: list[NodeInstance] = Field(default_factory=list)


class ModuleInstance(BaseModel):
    """A module instance placed on the canvas"""
    model_config = ConfigDict(frozen=True)

    module_instance_id: str
    module_id: int  # e.g., "text_cleaner:1.0.0"
    config: dict[str, Any]  # Module-specific configuration
    inputs: list[NodeInstance] = Field(default_factory=list)  # Flat list, grouped by group_index
    outputs: list[NodeInstance] = Field(default_factory=list)


class NodeConnection(BaseModel):
    """Connection between two nodes"""
    model_config = ConfigDict(frozen=True)

    from_node_id: str
    to_node_id: str


class OutputChannelInstance(BaseModel):
    """Output channel instance for collecting pipeline outputs"""
    model_config = ConfigDict(frozen=True)

    output_channel_instance_id: str  # Format: OC01, OC02, etc.
    channel_type: str                 # e.g., "hawb", "pickup_address"
    inputs: list[NodeInstance] = Field(default_factory=list)  # Single input pin


class Position(BaseModel):
    """2D position for visual layout"""
    model_config = ConfigDict(frozen=True)

    x: float
    y: float


class PipelineState(BaseModel):
    """The actual pipeline structure (execution data)"""
    model_config = ConfigDict(frozen=True)

    entry_points: list[EntryPoint] = Field(default_factory=list)
    modules: list[ModuleInstance] = Field(default_factory=list)
    connections: list[NodeConnection] = Field(default_factory=list)
    output_channels: list[OutputChannelInstance] = Field(default_factory=list)


VisualState: TypeAlias = dict[str, Position]


class PinInfo(BaseModel):
    """Information about a pin for index lookups"""
    model_config = ConfigDict(frozen=True)

    node_id: str
    type: str
    direction: str  # "entry" | "in" | "out" | "output_channel"
    name: str
    module_instance_id: str | None = None
    output_channel_instance_id: str | None = None


class PipelineIndices(BaseModel):
    """
    Index structures for fast pipeline lookups.

    Built once during pipeline processing to avoid repeated iterations.
    """
    model_config = ConfigDict(frozen=True)

    pin_by_id: dict[str, PinInfo] = Field(default_factory=dict)
    module_by_id: dict[str, ModuleInstance] = Field(default_factory=dict)
    input_to_upstream: dict[str, str] = Field(default_factory=dict)  # Input pin → upstream output pin


class ModuleExecutionContext(BaseModel):
    """
    Context passed to module handlers during execution.

    Contains I/O metadata for the module instance.
    Module handlers should access fields directly (e.g., context.outputs[0].node_id).

    Note: Services are passed as a separate parameter to run(), not via context.
    """
    model_config = ConfigDict(frozen=True)

    inputs: list[NodeInstance]  # Input pins metadata
    outputs: list[NodeInstance]  # Output pins metadata
    module_instance_id: str  # For debugging/logging
