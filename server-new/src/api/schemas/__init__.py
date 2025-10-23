"""
API Schemas Package
Pydantic models for all API endpoints
"""

# Email Configurations
from .email_configs import (
    EmailConfigSummaryItem,
    ListEmailConfigsResponse,
    FilterRule,
    EmailConfigDetail,
    FilterRuleCreate,
    CreateEmailConfigRequest,
    CreateEmailConfigResponse,
    FilterRuleUpdate,
    UpdateEmailConfigRequest,
    UpdateEmailConfigResponse,
    ActivateEmailConfigResponse,
    DeactivateEmailConfigResponse,
    EmailAccount,
    DiscoverEmailAccountsResponse,
    EmailFolderItem,
    DiscoverEmailFoldersResponse,
    ValidateEmailConfigRequest,
    ValidateEmailConfigResponse,
)

# ETO Runs
from .eto_runs import (
    EtoRunPdfInfo,
    EtoRunSourceInfo,
    EtoRunMatchedTemplate,
    EtoRunListItem,
    ListEtoRunsResponse,
    EtoRunPdfInfoDetail,
    EtoRunTemplateMatchingStage,
    EtoRunDataExtractionStage,
    PipelineStepPinValue,
    PipelineStepError,
    PipelineExecutionStep,
    ExecutedAction,
    EtoRunPipelineExecutionStage,
    EtoRunDetail,
    UploadPdfForProcessingResponse,
    BulkReprocessRequest,
    BulkSkipRequest,
    BulkDeleteRequest,
)

# PDF Files
from .pdf_files import (
    GetPdfMetadataResponse,
    TextWordObject,
    TextLineObject,
    GraphicRectObject,
    GraphicLineObject,
    GraphicCurveObject,
    ImageObject,
    TableObject,
    PdfObjects,
    GetPdfObjectsResponse,
    ProcessPdfObjectsResponse,
)

# PDF Templates
from .pdf_templates import (
    SignatureObjectBase,
    ExtractionField,
    PipelineEntryPoint,
    PipelineNodePin,
    PipelineModuleInstance,
    PipelineConnection,
    PipelineState,
    VisualState,
    TemplateVersionSummary,
    TemplateListItem,
    ListPdfTemplatesResponse,
    TemplateVersionDetail,
    PdfTemplateDetail,
    CreatePdfTemplateRequest,
    CreatePdfTemplateResponse,
    UpdatePdfTemplateRequest,
    UpdatePdfTemplateResponse,
    ActivatePdfTemplateResponse,
    DeactivatePdfTemplateResponse,
    TemplateVersionListItem,
    ListTemplateVersionsResponse,
    GetTemplateVersionResponse,
    SimulateTemplateRequestStored,
    SimulateTemplateRequestUpload,
    ValidationResult,
    DataExtractionSimulation,
    PipelineStepSimulation,
    SimulatedAction,
    PipelineExecutionSimulation,
    SimulateTemplateResponse,
)

# Modules
from .modules import (
    ModuleInputPin,
    ModuleOutputPin,
    ModuleMeta,
    ModuleCatalogItem,
    ListModulesResponse,
)

# Pipelines
# Note: PipelineState, VisualState, etc. are duplicated in pipelines.py but we only export from pdf_templates
from .pipelines import (
    PipelineListItem,
    ListPipelinesResponse,
    GetPipelineResponse,
    CreatePipelineRequest,
    CreatePipelineResponse,
    UpdatePipelineRequest,
    UpdatePipelineResponse,
)

# Health
from .health import (
    ServerStatus,
    ServiceStatus,
    ServicesStatus,
    HealthCheckResponse,
)


__all__ = [
    # Email Configurations
    "EmailConfigSummaryItem",
    "ListEmailConfigsResponse",
    "FilterRule",
    "EmailConfigDetail",
    "FilterRuleCreate",
    "CreateEmailConfigRequest",
    "CreateEmailConfigResponse",
    "FilterRuleUpdate",
    "UpdateEmailConfigRequest",
    "UpdateEmailConfigResponse",
    "ActivateEmailConfigResponse",
    "DeactivateEmailConfigResponse",
    "EmailAccount",
    "DiscoverEmailAccountsResponse",
    "EmailFolderItem",
    "DiscoverEmailFoldersResponse",
    "ValidateEmailConfigRequest",
    "ValidateEmailConfigResponse",

    # ETO Runs
    "EtoRunPdfInfo",
    "EtoRunSourceInfo",
    "EtoRunMatchedTemplate",
    "EtoRunListItem",
    "ListEtoRunsResponse",
    "EtoRunPdfInfoDetail",
    "EtoRunTemplateMatchingStage",
    "EtoRunDataExtractionStage",
    "PipelineStepPinValue",
    "PipelineStepError",
    "PipelineExecutionStep",
    "ExecutedAction",
    "EtoRunPipelineExecutionStage",
    "EtoRunDetail",
    "UploadPdfForProcessingResponse",
    "BulkReprocessRequest",
    "BulkSkipRequest",
    "BulkDeleteRequest",

    # PDF Files
    "GetPdfMetadataResponse",
    "TextWordObject",
    "TextLineObject",
    "GraphicRectObject",
    "GraphicLineObject",
    "GraphicCurveObject",
    "ImageObject",
    "TableObject",
    "PdfObjects",
    "GetPdfObjectsResponse",
    "ProcessPdfObjectsResponse",

    # PDF Templates
    "SignatureObjectBase",
    "ExtractionField",
    "PipelineEntryPoint",
    "PipelineNodePin",
    "PipelineModuleInstance",
    "PipelineConnection",
    "PipelineState",
    "VisualState",
    "TemplateVersionSummary",
    "TemplateListItem",
    "ListPdfTemplatesResponse",
    "TemplateVersionDetail",
    "PdfTemplateDetail",
    "CreatePdfTemplateRequest",
    "CreatePdfTemplateResponse",
    "UpdatePdfTemplateRequest",
    "UpdatePdfTemplateResponse",
    "ActivatePdfTemplateResponse",
    "DeactivatePdfTemplateResponse",
    "TemplateVersionListItem",
    "ListTemplateVersionsResponse",
    "GetTemplateVersionResponse",
    "SimulateTemplateRequestStored",
    "SimulateTemplateRequestUpload",
    "ValidationResult",
    "DataExtractionSimulation",
    "PipelineStepSimulation",
    "SimulatedAction",
    "PipelineExecutionSimulation",
    "SimulateTemplateResponse",

    # Modules
    "ModuleInputPin",
    "ModuleOutputPin",
    "ModuleMeta",
    "ModuleCatalogItem",
    "ListModulesResponse",

    # Pipelines
    "PipelineListItem",
    "ListPipelinesResponse",
    "GetPipelineResponse",
    "CreatePipelineRequest",
    "CreatePipelineResponse",
    "UpdatePipelineRequest",
    "UpdatePipelineResponse",

    # Health
    "ServerStatus",
    "ServiceStatus",
    "ServicesStatus",
    "HealthCheckResponse",
]
