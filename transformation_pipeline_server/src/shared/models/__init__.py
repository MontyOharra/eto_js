"""Shared Pydantic models for domain objects"""

from .pipeline import (
    # Supporting types
    NodePin,
    NodeGroup,
    ModuleInstance,
    NodeConnection,
    EntryPoint,
    PipelineState,
    ModulePosition,
    VisualState,
    # CRUD models
    PipelineBase,
    PipelineCreate,
    Pipeline,
    PipelineSummary
)

from .module_catalog import (
    ModuleMeta,
    ModuleCatalogCreate,
    ModuleCatalogUpdate,
    ModuleCatalog
)

__all__ = [
    # Pipeline types
    "NodePin",
    "NodeGroup",
    "ModuleInstance",
    "NodeConnection",
    "EntryPoint",
    "PipelineState",
    "ModulePosition",
    "VisualState",
    "PipelineBase",
    "PipelineCreate",
    "Pipeline",
    "PipelineSummary",
    # Module catalog types
    "ModuleMeta",
    "ModuleCatalogCreate",
    "ModuleCatalogUpdate",
    "ModuleCatalog"
]