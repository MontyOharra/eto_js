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
    EmailFilterSchema,
    EmailConfigConnectionSchema,
    EmailConfigMonitoringSchema,
    EmailConfigCreateRequest,
    EmailConfigUpdateRequest,
    EmailConfigSummaryResponse,
    EmailConfigDetailResponse,
    EmailConfigStatsResponse,
    EmailConfigTemplateResponse,
    EmailConfigValidateRequest,
    EmailConfigActivateRequest,
    EmailConfigActivateResponse
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

    'EmailFilterSchema',
    'EmailConfigConnectionSchema',
    'EmailConfigMonitoringSchema',
    'EmailConfigCreateRequest',
    'EmailConfigUpdateRequest',
    'EmailConfigSummaryResponse',
    'EmailConfigDetailResponse',
    'EmailConfigStatsResponse',
    'EmailConfigTemplateResponse',
    'EmailConfigValidateRequest',
    'EmailConfigActivateRequest',
    'EmailConfigActivateResponse',
    
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