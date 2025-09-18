"""
Shared Domain Types
Central location for all domain objects used across features
"""

from .email_ingestion import (
    EmailFilterRule,
    EmailIngestionConfigCreate,
    EmailIngestionConfig,
    EmailIngestionCursorCreate,
    EmailIngestionCursor,
    EmailIngestionCursorStatistics,
    EmailIngestionConnectionConfig,
    EmailServiceConnectionStatus,
    EmailConfigSummary,
    EmailData,
    EmailIngestionStats,
    EmailServiceHealth,
    EmailCreate,
    Email,
    EmailServiceStartResponse,
    EmailServiceStopResponse,
    EmailServiceStatusResponse,
)

from .eto_processing import (
    EtoRun,
    EtoRunStatus,
    EtoProcessingStep,
    EtoErrorType
)

from .pdf_processing import (
    PdfFile,
    PdfObject,
    PdfObjectExtractionResult,
    PdfStoreRequest,
)

from .pdf_template import (
    PdfTemplate,
    TemplateMatchResult,
    ExtractionField,
    TemplateCreateRequest,
    TemplateVersionRequest
)

__all__ = [
    # ETO Processing Domain Types
    'EtoRun',
    'EtoRunStatus',
    'EtoProcessingStep',
    'EtoErrorType',

    # PDF Template Domain Types
    'PdfTemplate',
    'TemplateMatchResult',
    'PdfObject',
    'ExtractionField',
    'TemplateCreateRequest',
    'TemplateVersionRequest',

    # Email Ingestion Domain Types
    'EmailFilterRule',
    'EmailIngestionConfigCreate',
    'EmailIngestionConfig',
    'EmailIngestionCursorCreate',
    'EmailIngestionCursor',
    'EmailIngestionCursorStatistics',
    'EmailIngestionConnectionConfig',
    'EmailServiceConnectionStatus',
    'EmailConfigSummary',
    'EmailData',
    'EmailIngestionStats',
    'EmailServiceHealth',
    'EmailCreate',
    'Email',
    'EmailServiceStartResponse',
    'EmailServiceStopResponse',
    'EmailServiceStatusResponse',

    # Pdf Processing Domain Types
    'PdfObject',
    'PdfStoreRequest',
    'PdfObjectExtractionResult',
    'PdfFile',
    
    # Pdf Template Domain Types
    'PdfTemplate',
    'TemplateMatchResult',
    'ExtractionField',
    'TemplateCreateRequest',
    'TemplateVersionRequest',
]