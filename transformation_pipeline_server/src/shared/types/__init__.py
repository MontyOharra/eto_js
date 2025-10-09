"""Shared Pydantic models for domain objects"""

from db.module_catalog import (
    ModuleCatalogCreate,
    ModuleCatalogUpdate,
    ModuleCatalog
)

from db.pipeline_definition_steps import (
    PipelineDefinitionStepCreate,
    PipelineDefinitionStep
)

from db.pipeline_definitions import (
    PipelineDefinitionCreate,
    PipelineDefinition,
    PipelineDefinitionSummary
)

from db.pipeline_execution_run import (
    PipelineExecutionRunCreate,
    PipelineExecutionRun
)

from db.pipeline_execution_step import (
    PipelineExecutionStepCreate,
    PipelineExecutionStep
)

from .execution_context import (
    ExecutionContext
)

from .execution_result import (
    ExecutionError,
    RunResult
)

from .modules import (
    AllowedModuleTypes,
    ModuleKind,
    NodeTypeRule,
    NodeGroup,
    IOSideShape,
    IOShape,
    ModuleMeta,
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
    
    # Execution Context
    'ExecutionContext',

    # Execution Result
    'ExecutionError', 
    'RunResult',

    # Modules
    'AllowedModuleTypes',
    'ModuleKind',
    'NodeTypeRule',
    'NodeGroup',
    'IOSideShape',
    'IOShape',
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
    'PipelineValidationResult',
    'PinInfo',
    'PipelineIndices'
]