"""Shared Pydantic models for domain objects"""

from .db.email_config import (
    EmailFilterRule,
    EmailConfigCreate,
    EmailConfigUpdate,
    EmailConfig,
    EmailConfigSummary
)

from .db.email import (
    Email,
    EmailCreate,
    EmailSummary,
)

from .db.eto_run import (
    EtoRunCreate,
    EtoDataExtractionResult,
    EtoTransformationResult,
    EtoRun,
    EtoEmailInfo,
    EtoRunSummary,
    EtoRunWithPdfData,
    EtoRunStatusUpdate,
    EtoRunTemplateMatchUpdate,
    EtoRunDataExtractionUpdate,
    EtoRunTransformationUpdate,
    EtoRunOrderUpdate,
    EtoRunResetResult,
)

from .db.module_catalog import (
    ModuleCatalog,
    ModuleCatalogCreate,
    ModuleCatalogUpdate,
)

from .db.pdf_file import (
    PdfFile,
    PdfFileCreate,
    PdfDetailData,
)

from .db.pdf_template_version import (
    PdfTemplateVersion,
    PdfTemplateVersionCreate,
)

from .db.pdf_template import (
    PdfTemplate,
    PdfTemplateCreate,
    PdfTemplateUpdate,
)

from .db.pipeline_definition_steps import (
    PipelineDefinitionStep,
    PipelineDefinitionStepCreate,
)

from .db.pipeline_definitions import (
    PipelineDefinition,
    PipelineDefinitionCreate,
    PipelineDefinitionSummary,
)

from .db.pipeline_execution_run import (
    PipelineExecutionRun,
    PipelineExecutionRunCreate,
)

from .db.pipeline_execution_step import (
    PipelineExecutionStep,
    PipelineExecutionStepCreate,
)

from .email_integration import (
    EmailProvider,
    EmailMessage,
    EmailAttachment,
    EmailFolder,
    EmailAccount,
    EmailSearchCriteria,
    EmailIntegrationConfig,
    OutlookComConfig,
    GmailApiConfig,
    ImapConfig,
    ConnectionTestResult,
    ProviderInfo,
)

from .enums import (
    AllowedModuleTypes,
    ModuleKind,
    EtoRunStatus,
    EtoProcessingStep,
    EtoErrorType
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

from .pdfs import (
    BasePdfObject,
    TextWordPdfObject,
    TextLinePdfObject,
    GraphicRectPdfObject,
    GraphicLinePdfObject,
    GraphicCurvePdfObject,
    ImagePdfObject,
    TablePdfObject,
    PdfObjects,
    ExtractionField,
    PdfTemplateMatchResult
)

from .pipeline_execution import (
    PipelineExecutionError,
    PipelineExecutionRunResult,
)

from .pipelines import (
    InstanceNodePin,
    ModuleInstance,
    NodeConnection,
    EntryPoint,
    PipelineState,
    ModulePosition,
    VisualState,
)

from .pipeline_validation import (
    PipelineValidationErrorCode,
    PipelineValidationError,
    PipelineValidationResult,
    PinInfo,
    PipelineIndices,
)

from .services import (
    ServiceHealth,
    ServiceStatusResponse
)

__all__ = [
    # === DB TYPES ===
    
    # Email Config
    'EmailFilterRule',
    'EmailConfigCreate',
    'EmailConfigUpdate',
    'EmailConfig',
    'EmailConfigSummary',
    
    # Email
    'Email',
    'EmailCreate',
    'EmailSummary',
    
    # Eto Run
    'EtoRunCreate',
    'EtoDataExtractionResult',
    'EtoTransformationResult',
    'EtoRun',
    'EtoEmailInfo',
    'EtoRunSummary',
    'EtoRunWithPdfData',
    'EtoRunStatusUpdate',
    'EtoRunTemplateMatchUpdate',
    'EtoRunDataExtractionUpdate',
    'EtoRunTransformationUpdate',
    'EtoRunOrderUpdate',
    'EtoRunResetResult',
    
    # PDF File
    'PdfFile',
    'PdfFileCreate',
    'PdfDetailData',
    
    # PDF Template Version
    'PdfTemplateVersionCreate',
    'PdfTemplateVersion',
    
    # PDF Template
    'PdfTemplate',
    'PdfTemplateCreate',
    'PdfTemplateUpdate',
    
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
    
    # Email Integration
    'EmailProvider',
    'EmailMessage',
    'EmailAttachment',
    'EmailFolder',
    'EmailAccount',
    'EmailSearchCriteria',
    'EmailIntegrationConfig',
    'OutlookComConfig',
    'GmailApiConfig',
    'ImapConfig',
    'ConnectionTestResult',
    'ProviderInfo',
    
    # Enums
    'AllowedModuleTypes',
    'ModuleKind',
    'EtoRunStatus',
    'EtoProcessingStep',
    'EtoErrorType',
    
    # Modules
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

    # PDF Processing
    'BasePdfObject',
    'TextWordPdfObject',
    'TextLinePdfObject',
    'GraphicRectPdfObject',
    'GraphicLinePdfObject',
    'GraphicCurvePdfObject',
    'ImagePdfObject',
    'TablePdfObject',
    'PdfObjects',
    'ExtractionField',
    'PdfTemplateMatchResult',

    # Pipeline Execution
    'PipelineExecutionError',
    'PipelineExecutionRunResult',

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
    'PipelineIndices',
    
    'ServiceHealth',
    'ServiceStatusResponse'
]