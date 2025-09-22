"""
Shared Pydantic Models
Hierarchical type system with Base/Create/Domain models
"""

# Base models (core business data)
from .email_config import EmailConfig, EmailConfigCreate, EmailConfigUpdate, EmailConfigSummary
from .email_integration import EmailMessage, EmailAttachment, EmailAccount, EmailFolder, ConnectionTestResult, EmailProvider, OutlookComConfig
from .email import Email, EmailCreate, EmailSummary, EmailBase
from .eto import EtoRunBase, EtoRunCreate, EtoRun, EtoRunSummary
from .pdf_file import PdfFileBase, PdfFileCreate, PdfFileUpdate, PdfFileSummary, PdfFile
from .pdf_processing import PdfObject, ExtractionField, PdfObjectExtractionResult
from .pdf_template import PdfTemplateBase, PdfTemplateVersionBase, PdfTemplateCreate, PdfTemplateUpdate, PdfTemplateVersionCreate, PdfTemplate, PdfTemplateVersion



from .common import TemplateMatchResult

__all__ = [
  
    # Email config models
    'EmailConfig',
    'EmailConfigCreate',
    'EmailConfigUpdate',
    'EmailConfigSummary',
    
    # Email integration models
    'EmailMessage',
    'EmailAttachment',
    'EmailAccount',
    'EmailFolder',
    'ConnectionTestResult',
    'EmailProvider',
    'OutlookComConfig', 
    
    # Email models
    'Email',
    'EmailCreate',
    'EmailSummary',
    'EmailBase',
  
    # ETO models
    'EtoRunBase',
    'EtoRunCreate',
    'EtoRun',
    'EtoRunSummary',
    
    # PDF file models
    'PdfFileBase',
    'PdfFileCreate',
    'PdfFileUpdate',
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
]