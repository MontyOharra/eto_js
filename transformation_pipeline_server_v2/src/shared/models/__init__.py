"""Shared Pydantic models for domain objects"""

from .pipeline import (
    # Supporting types
    NodePin,
    ModuleInstance,
    NodeConnection,
    EntryPoint,
    PipelineState,
    ModulePosition,
    VisualState,
    # CRUD models
    PipelineBase,
    PipelineCreate,
    PipelineUpdate,
    Pipeline,
    PipelineSummary
)

from .module_catalog import (
    DynamicSide,
    ModuleMeta,
    ModuleCatalogCreate,
    ModuleCatalogUpdate,
    ModuleCatalog
)

__all__ = [
    # Pipeline types
    "NodePin",
    "ModuleInstance",
    "NodeConnection",
    "EntryPoint",
    "PipelineState",
    "ModulePosition",
    "VisualState",
    "PipelineBase",
    "PipelineCreate",
    "PipelineUpdate",
    "Pipeline",
    "PipelineSummary",
    # Module catalog types
    "DynamicSide",
    "ModuleMeta",
    "ModuleCatalogCreate",
    "ModuleCatalogUpdate",
    "ModuleCatalog"
]