"""Shared Pydantic models for domain objects"""

from .db.module_catalog import (
    ModuleCatalogCreate,
    ModuleCatalogUpdate,
    ModuleCatalog
)

from .db.pipeline_definition_steps import (
    PipelineDefinitionStepCreate,
    PipelineDefinitionStep
)

from .db.pipeline_definitions import (
    PipelineDefinitionCreate,
    PipelineDefinition,
    PipelineDefinitionSummary
)

from .db.pipeline_execution_run import (
    PipelineExecutionRunCreate,
    PipelineExecutionRun
)

from .db.pipeline_execution_step import (
    PipelineExecutionStepCreate,
    PipelineExecutionStep
)

from .enums import (
    AllowedModuleTypes,
    ModuleKind
)

from .pipeline_execution import (
    PipelineExecutionError,
    PipelineExecutionRunResult
)

from .modules import (
    NodeTypeRule,
    NodeGroup,
    IOSideShape,
    IOShape,
    ModuleMeta,
    ModuleExecutionContext,
    BaseModule,
    TransformModule,
    ActionModule,
    LogicModule,
    ComparatorModule,
)

from .pipeline_state import (
    InstanceNodePin,
    ModuleInstance,
    NodeConnection,
    EntryPoint,
    PipelineState,
    ModulePosition,
    VisualState
)

from .pipeline_validation import (
    PipelineValidationErrorCode,
    PipelineValidationError,
    PipelineValidationResult,
    PinInfo,
    PipelineIndices
)


__all__ = [
    # === DB TYPES ===
    
    # Module Catalog
    'ModuleCatalogCreate',
    'ModuleCatalogUpdate',
    'ModuleCatalog',

    # Pipeline Definition Steps
    'PipelineDefinitionStepCreate',
    'PipelineDefinitionStep',

    # Pipeline Definitions
    'PipelineDefinitionCreate',
    'PipelineDefinition',
    'PipelineDefinitionSummary',

    # Pipeline Execution Runs
    'PipelineExecutionRunCreate',
    'PipelineExecutionRun',

    # Pipeline Execution Steps
    'PipelineExecutionStepCreate',
    'PipelineExecutionStep',

    # === GENERAL DOMAIN TYPES ===
    
    'PipelineExecutionError',
    'PipelineExecutionRunResult',

    # Modules
    'AllowedModuleTypes',
    'ModuleKind',
    'NodeTypeRule',
    'NodeGroup',
    'IOSideShape',
    'IOShape',
    'ModuleExecutionContext',
    'ModuleMeta',
    'BaseModule',
    'TransformModule',
    'ActionModule',
    'LogicModule',
    'ComparatorModule',

    # Pipeline State
    'InstanceNodePin',
    'ModuleInstance',
    'NodeConnection',
    'EntryPoint',
    'PipelineState',
    'ModulePosition',
    'VisualState',

    # Pipeline Validation
    'PipelineValidationErrorCode',
    'PipelineValidationError',
    'PipelineValidationResult',
    'PinInfo',
    'PipelineIndices'
]