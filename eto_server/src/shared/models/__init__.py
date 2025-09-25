"""
Shared Pydantic Models
Hierarchical type system with Base/Create/Domain models
"""

# Base models (core business data)
from .email_config import (
    EmailConfigBase, EmailConfig, EmailConfigCreate,
    EmailConfigUpdate, EmailConfigSummary, EmailFilterRule
)

from .email_integration import (
    EmailMessage, EmailAttachment, EmailAccount, 
    EmailFolder, ConnectionTestResult, EmailProvider, 
    OutlookComConfig, EmailSearchCriteria,
    EmailIntegrationConfig, GmailApiConfig, ImapConfig,
    ProviderInfo
)

from .email import (
    Email, EmailCreate, EmailSummary, EmailBase
)

from .eto_run import (
    EtoRunStatus, EtoProcessingStep, EtoErrorType,
    EtoRunBase, EtoRunCreate, EtoRun, EtoRunSummary, EtoEmailInfo,
    EtoProcessingState, EtoErrorInfo, EtoTemplateMatchingResult,
    EtoDataExtractionResult, EtoTransformationResult, EtoOrderIntegration,
    EtoRunStatusUpdate, EtoRunTemplateMatchUpdate, EtoRunDataExtractionUpdate,
    EtoRunTransformationUpdate, EtoRunOrderUpdate,
    EtoRunResetResult, EtoRunWithPdfData
)

from .pdf_file import (
    PdfFileBase, PdfFileCreate,
    PdfFile, PdfDetailData
)

from .pdf_processing import (
    BasePdfObject, TextWordPdfObject, TextLinePdfObject, GraphicRectPdfObject,
    GraphicLinePdfObject, GraphicCurvePdfObject, ImagePdfObject, TablePdfObject,
    PdfObjects
)

from .pdf_template import (
    PdfTemplateBase, PdfTemplateVersionBase, ExtractionField,
    PdfTemplateCreate, PdfTemplateUpdate,
    PdfTemplateVersionCreate, PdfTemplate,
    PdfTemplateVersion, PdfTemplateMatchResult
)

from .status import (
    ServiceHealth, ServiceStatusResponse
)

__all__ = [
  
    # Email config models
    'EmailConfigBase',
    'EmailConfig',
    'EmailConfigCreate',
    'EmailConfigUpdate',
    'EmailConfigSummary',
    'EmailFilterRule',
    
    # Email integration models
    'EmailMessage',
    'EmailAttachment',
    'EmailAccount',
    'EmailFolder',
    'ConnectionTestResult',
    'EmailProvider',
    'OutlookComConfig', 
    'EmailSearchCriteria',
    'EmailIntegrationConfig',
    'GmailApiConfig',
    'ImapConfig',
    'ProviderInfo',
    
    # Email models
    'Email',
    'EmailCreate',
    'EmailSummary',
    'EmailBase',
  
    # ETO models
    'EtoRunStatus',
    'EtoProcessingStep',
    'EtoErrorType',
    'EtoRunBase',
    'EtoRunCreate',
    'EtoRun',
    'EtoRunSummary',
    'EtoEmailInfo',
    'EtoProcessingState',
    'EtoErrorInfo',
    'EtoTemplateMatchingResult',
    'EtoDataExtractionResult',
    'EtoTransformationResult',
    'EtoOrderIntegration',
    'EtoRunStatusUpdate',
    'EtoRunTemplateMatchUpdate',
    'EtoRunDataExtractionUpdate',
    'EtoRunTransformationUpdate',
    'EtoRunOrderUpdate',
    'EtoRunResetResult',
    
    # PDF file models
    'PdfFileBase',
    'PdfFileCreate',
    'PdfFile',
    'PdfDetailData',

    # PDF object models
    'BasePdfObject',
    'TextWordPdfObject',
    'TextLinePdfObject',
    'GraphicRectPdfObject',
    'GraphicLinePdfObject',
    'GraphicCurvePdfObject',
    'ImagePdfObject',
    'TablePdfObject',
    'PdfObjects',
    'EtoRunWithPdfData',

    # PDF template models
    'PdfTemplateBase',
    'PdfTemplateVersionBase',
    'ExtractionField',
    'PdfTemplateCreate',
    'PdfTemplateUpdate',
    'PdfTemplateVersionCreate',
    'PdfTemplate',
    'PdfTemplateVersion',
    'PdfTemplateMatchResult',

    # Status models
    'ServiceHealth',
    'ServiceStatusResponse',
]