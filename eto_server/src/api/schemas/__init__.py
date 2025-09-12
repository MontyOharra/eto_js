"""
API Schemas Package
Pydantic models for request/response validation
"""
from .common import (
    APIResponse,
    SuccessResponse, 
    ErrorResponse,
    PaginationParams,
    PaginatedResponse,
    HealthCheck,
    ValidationError,
    ValidationResponse
)

from .email_ingestion import (
    EmailFilterRuleSchema,
    EmailConnectionConfigSchema,
    EmailMonitoringConfigSchema,
    CreateEmailConfigRequest,
    UpdateEmailConfigRequest,
    EmailConfigSummaryResponse,
    EmailConfigDetailResponse,
    EmailConfigStatsResponse,
    ConfigTemplateResponse,
    ValidateConfigRequest,
    ActivateConfigRequest,
    ActivateConfigResponse
)

from .eto_processing import (
    EtoRunSummaryResponse,
    EtoRunDetailResponse,
    ProcessingStepResultResponse,
    ReprocessEtoRunRequest,
    SkipEtoRunRequest,
    EtoRunStatsResponse,
    EtoRunListRequest
)

from .pdf_processing import (
    PdfObjectResponse,
    PdfExtractionBoundsResponse,
    PdfFileResponse,
    PdfTemplateResponse,
    CreatePdfTemplateRequest,
    UpdatePdfTemplateRequest,
    TemplateMatchResultResponse,
    PdfAnalysisRequest,
    PdfAnalysisResponse,
    PdfTemplateStatsResponse
)

__all__ = [
    # Common schemas
    'APIResponse',
    'SuccessResponse',
    'ErrorResponse', 
    'PaginationParams',
    'PaginatedResponse',
    'HealthCheck',
    'ValidationError',
    'ValidationResponse',
    
    # Email configuration schemas
    'EmailFilterRuleSchema',
    'EmailConnectionConfigSchema',
    'EmailMonitoringConfigSchema',
    'CreateEmailConfigRequest',
    'UpdateEmailConfigRequest',
    'EmailConfigSummaryResponse',
    'EmailConfigDetailResponse',
    'EmailConfigStatsResponse',
    'ConfigTemplateResponse',
    'ValidateConfigRequest',
    'ActivateConfigRequest',
    'ActivateConfigResponse',
    
    # ETO processing schemas
    'EtoRunSummaryResponse',
    'EtoRunDetailResponse',
    'ProcessingStepResultResponse',
    'ReprocessEtoRunRequest',
    'SkipEtoRunRequest',
    'EtoRunStatsResponse',
    'EtoRunListRequest',
    
    # PDF processing schemas
    'PdfObjectResponse',
    'PdfExtractionBoundsResponse',
    'PdfFileResponse',
    'PdfTemplateResponse',
    'CreatePdfTemplateRequest',
    'UpdatePdfTemplateRequest',
    'TemplateMatchResultResponse',
    'PdfAnalysisRequest',
    'PdfAnalysisResponse',
    'PdfTemplateStatsResponse',
]