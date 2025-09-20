"""
Shared Domain Types
Central location for all domain objects used across features
"""

from .email_ingestion import (
    EmailFilterRule,
    EmailIngestionConfig,
    EmailIngestionCursor,
    EmailIngestionCursorStatistics,
    EmailIngestionConnectionConfig,
    EmailServiceConnectionStatus,
    EmailConfigSummary,
    EmailData,
    EmailIngestionStats,
    EmailServiceHealth,
    Email,
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
)

from .pdf_template import (
    PdfTemplate,
    PdfTemplateVersion,
    ExtractionField
)

__all__ = [
    # ETO Processing Domain Types
    'EtoRun',
    'EtoRunStatus',
    'EtoProcessingStep',
    'EtoErrorType',


    # Email Ingestion Domain Types
    'EmailFilterRule',
    'EmailIngestionConfig',
    'EmailIngestionCursor',
    'EmailIngestionCursorStatistics',
    'EmailIngestionConnectionConfig',
    'EmailServiceConnectionStatus',
    'EmailConfigSummary',
    'EmailData',
    'EmailIngestionStats',
    'EmailServiceHealth',
    'Email',
    # Pdf Processing Domain Types
    'PdfObject',
    'PdfObjectExtractionResult',
    'PdfFile',
    
    # Pdf Template Domain Types
    'PdfTemplate',
    'PdfTemplateVersion',
]