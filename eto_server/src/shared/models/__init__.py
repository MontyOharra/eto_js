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

from .eto_processing import (
    EtoRunStatus, EtoProcessingStep, EtoErrorType,
    EtoRunBase, EtoRunCreate, EtoRun, EtoRunSummary, EtoEmailInfo,
    EtoProcessingState, EtoErrorInfo, EtoTemplateMatchingResult,
    EtoDataExtractionResult, EtoTransformationResult, EtoOrderIntegration,
    EtoRunStatusUpdate, EtoRunTemplateMatchUpdate, EtoRunDataExtractionUpdate,
    EtoRunTransformationUpdate, EtoRunOrderUpdate, EtoProcessingStatistics,
    EtoRunResetResult
)

from .pdf_file import (
    PdfFileBase, PdfFileCreate,
    PdfFileSummary, PdfFile
)

from .pdf_processing import (
    PdfObject, ExtractionField, 
    PdfObjectExtractionResult
)

from .pdf_template import (
    PdfTemplateBase, PdfTemplateVersionBase,
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
    'EtoProcessingStatistics',
    'EtoRunResetResult',
    
    # PDF file models
    'PdfFileBase',
    'PdfFileCreate',
    'PdfFileSummary',
    'PdfFile',
    'PdfObject',
    'ExtractionField',
    'PdfObjectExtractionResult',
    
    # PDF template models
    'PdfTemplateBase',
    'PdfTemplateVersionBase',
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