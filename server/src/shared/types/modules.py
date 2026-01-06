"""
Module domain types.

Contains type definitions for module metadata and catalog entries.
Base classes for module implementations are in features/modules/base.py.
"""
from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


# Type alias for allowed node types
AllowedNodeType = Literal[
    "str", "float", "datetime", "bool", "int", "list[str]", "dim", "list[dim]"
]


class ModuleKind(str, Enum):
    """Module kind."""
    TRANSFORM = "transform"
    LOGIC = "logic"
    COMPARATOR = "comparator"
    MISC = "misc"
    OUTPUT = "output"


# ========== Module Metadata Types ==========

class NodeTypeRule(BaseModel):
    """Type rule for a node group - either allowed_types list or type_var."""
    model_config = ConfigDict(frozen=True)

    allowed_types: list[AllowedNodeType] | None = None  # Per-pin whitelist; user picks independently
    type_var: str | None = None  # e.g., "T" (unifies across pins)


class NodeGroup(BaseModel):
    """Definition of a group of nodes (pins) with cardinality constraints."""
    model_config = ConfigDict(frozen=True)

    typing: NodeTypeRule
    label: str
    min_count: int = 1
    max_count: int | None = 1


class IOSideShape(BaseModel):
    """Shape definition for one side of I/O (inputs or outputs)."""
    model_config = ConfigDict(frozen=True)

    nodes: list[NodeGroup] = []


class IOShape(BaseModel):
    """Complete I/O shape definition for a module."""
    model_config = ConfigDict(frozen=True)

    inputs: IOSideShape = IOSideShape()
    outputs: IOSideShape = IOSideShape()
    type_params: dict[str, list[AllowedNodeType]] = {}


class ModuleMeta(BaseModel):
    """Metadata defining I/O constraints for a module."""
    model_config = ConfigDict(frozen=True)

    io_shape: IOShape = IOShape()


# ========== Module Catalog Domain Types ==========

class ModuleCreate(BaseModel):
    """Data for creating a new module catalog entry."""
    model_config = ConfigDict(frozen=True)

    identifier: str  # e.g., "text_cleaner"
    version: str  # e.g., "1.0.0"
    name: str  # Display name
    description: str | None
    module_kind: ModuleKind
    meta: ModuleMeta
    config_schema: dict[str, Any]
    handler_name: str
    color: str = "#3B82F6"
    category: str = "Processing"
    is_active: bool = True


class ModuleUpdate(BaseModel):
    """
    Data for updating a module catalog entry.

    Uses Pydantic's model_fields_set to distinguish between:
    - Field not provided: not in model_fields_set (don't update)
    - Field set to None: in model_fields_set with None value (set NULL)
    - Field set to value: in model_fields_set with value (update)
    """
    name: str | None = None
    description: str | None = None
    module_kind: ModuleKind | None = None
    meta: ModuleMeta | None = None
    config_schema: dict[str, Any] | None = None
    handler_name: str | None = None
    color: str | None = None
    category: str | None = None
    is_active: bool | None = None


class Module(BaseModel):
    """Full module catalog domain object retrieved from database."""
    model_config = ConfigDict(frozen=True)

    id: int  # Auto-increment PK
    identifier: str  # e.g., "text_cleaner"
    version: str  # e.g., "1.0.0"
    name: str  # Display name
    description: str | None
    module_kind: ModuleKind
    meta: ModuleMeta
    config_schema: dict[str, Any]
    handler_name: str
    color: str
    category: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
