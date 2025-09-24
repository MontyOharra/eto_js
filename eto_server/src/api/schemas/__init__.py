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

from .eto_processing import (
    EtoRunPdfDataResponse
)

from .pdf_templates import (
    PdfTemplateVersionCreateRequest
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

    # ETO processing schemas - minimal set for actual API usage
    'EtoRunPdfDataResponse',

    # PDF templates schemas - minimal set for actual API usage
    'PdfTemplateVersionCreateRequest',
]