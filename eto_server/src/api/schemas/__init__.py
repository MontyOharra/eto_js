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

# from .eto_processing import (  # Commented out - ETO not implemented yet
#     EtoRunListRequest,
#     EtoRunListResponse,
#     EtoRunDetailResponse,
#     ReprocessEtoRunRequest,
#     ReprocessEtoRunResponse,
#     SkipEtoRunRequest,
#     SkipEtoRunResponse,
#     DeleteEtoRunResponse,
#     EtoRunResultsResponse,
#     EtoRunPdfDataResponse,
#     EtoRunAuditResponse,
#     TemplateSuggestionsResponse,
#     AssignTemplateResponse,
#     BulkReprocessResponse,
#     EtoRunsSummaryResponse,
#     EtoStatisticsResponse
# )

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

from .pdf_templates import (
    PdfObjectRequest,
    ExtractionFieldRequest,
    PdfTemplateVersionCreateRequest,
    PdfTemplateCreateResponse,
    PdfTemplateVersionCreateResponse,
    TemplateUpdateRequest,
    TemplateSetCurrentVersionRequest,
    TemplateListResponse,
    TemplateVersionSummary,
    TemplateDetailResponse
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

    # ETO processing schemas (commented out - ETO not implemented yet)
    # 'EtoRunListRequest',
    # 'EtoRunListResponse',
    # 'EtoRunDetailResponse',
    # 'ReprocessEtoRunRequest',
    # 'ReprocessEtoRunResponse',
    # 'SkipEtoRunRequest',
    # 'SkipEtoRunResponse',
    # 'DeleteEtoRunResponse',
    # 'EtoRunResultsResponse',
    # 'EtoRunPdfDataResponse',
    # 'EtoRunAuditResponse',
    # 'TemplateSuggestionsResponse',
    # 'AssignTemplateResponse',
    # 'BulkReprocessResponse',
    # 'EtoRunsSummaryResponse',
    # 'EtoStatisticsResponse',
    
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

    # PDF templates schemas
    'PdfObjectRequest',
    'ExtractionFieldRequest',
    'PdfTemplateVersionCreateRequest',
    'PdfTemplateCreateResponse',
    'PdfTemplateVersionCreateResponse',
    'TemplateUpdateRequest',
    'TemplateSetCurrentVersionRequest',
    'TemplateListResponse',
    'TemplateVersionSummary',
    'TemplateDetailResponse',
]