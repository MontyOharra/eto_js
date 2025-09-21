"""
Shared Pydantic Models
Hierarchical type system with Base/Create/Domain models
"""

# Base models (core business data)
from .pdf_template import PdfTemplateBase, PdfTemplateVersionBase, PdfTemplateCreate, PdfTemplateUpdate, PdfTemplateVersionCreate, PdfTemplate, PdfTemplateVersion
from .email_config import EmailConfig, EmailConfigCreate, EmailConfigUpdate, EmailConfigSummary
# Supporting models
from .pdf_processing import PdfObject, ExtractionField, PdfFile, PdfObjectExtractionResult
from .common import TemplateMatchResult

__all__ = [
    # Base models
    'PdfTemplateBase',
    'PdfTemplateVersionBase',
    
    # Create models  
    'PdfTemplateCreate',
    'PdfTemplateVersionCreate',
    
    # Update models
    'PdfTemplateUpdate',
    
    # Domain models
    'PdfTemplate',
    'PdfTemplateVersion',
    
    # Supporting models
    'PdfObject',
    'ExtractionField',
    'PdfFile',
    'PdfObjectExtractionResult',
    'TemplateMatchResult',
    
    # Email config models
    'EmailConfig',
    'EmailConfigCreate',
    'EmailConfigUpdate',
    'EmailConfigSummary'  
]