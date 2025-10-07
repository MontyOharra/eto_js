"""Shared Pydantic models for domain objects"""

from .modules import ModuleKind

from .modules import (
    Scalar,
    NodeTypeRule,
    NodeGroup,
    IOSideShape,
    IOShape,
    ModuleMeta,
    ModuleKind,
    BaseModule,
    TransformModule,
    ActionModule,
    LogicModule,
    ComparatorModule
)

from .pipeline import (
    # Supporting types
    InstanceNodePin,
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

from .pipeline_step import (
    PipelineStepBase,
    PipelineStepCreate,
    PipelineStep
)

from .module_catalog import (
    ModuleCatalogCreate,
    ModuleCatalogUpdate,
    ModuleCatalog
)

__all__ = [
    # Module types
    "ModuleKind",
    # Module metadata types
    "Scalar",
    "NodeTypeRule",
    "NodeGroup",
    "IOSideShape",
    "IOShape",
    "ModuleMeta",
    # Module base classes
    "BaseModule",
    "TransformModule",
    "ActionModule",
    "LogicModule",
    "ComparatorModule",
    # Pipeline types
    "InstanceNodePin",
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
    # Pipeline step types
    "PipelineStepBase",
    "PipelineStepCreate",
    "PipelineStep",
    # Module catalog types
    "ModuleCatalogCreate",
    "ModuleCatalogUpdate",
    "ModuleCatalog"
]