"""Shared Pydantic models for domain objects"""

from .db.email_config import (
    EmailFilterRule,
    EmailConfigCreate,
    EmailConfigUpdate,
    EmailConfig,
    EmailConfigSummary
)

from .db.email import (
    Email,
    EmailCreate,
    EmailSummary,
)

from .db.eto_run import (
    EtoRunCreate,
    EtoRun,
    EtoEmailInfo,
    EtoRunSummary,
    EtoRunWithPdfData,
    EtoRunStatusUpdate,
    EtoRunTemplateMatchUpdate,
    EtoRunDataExtractionUpdate,
    EtoRunTransformationUpdate,
    EtoRunOrderUpdate,
    EtoRunResetResult,
)

from .db.module_catalog import (
    ModuleCatalog,
    ModuleCatalogCreate,
    ModuleCatalogUpdate,
)

from .db.pdf_file import (
    PdfFile,
    PdfFileCreate,
    PdfDetailData,
)

from .db.pdf_template_version import (
    PdfTemplateVersion,
    PdfTemplateVersionCreate,
)

from .db.pdf_template import (
    PdfTemplate,
    PdfTemplateCreate,
    PdfTemplateUpdate,
)

from .db.pipeline_definition_step import (
    PipelineDefinitionStep,
    PipelineDefinitionStepCreate,
)

from .db.pipeline_definition import (
    PipelineDefinition,
    PipelineDefinitionCreate,
    PipelineDefinitionSummary,
)


__all__ = [
    # === DB TYPES ===
    
    # Email Config
    'EmailFilterRule',
    'EmailConfigCreate',
    'EmailConfigUpdate',
    'EmailConfig',
    'EmailConfigSummary',
    
    # Email
    'Email',
    'EmailCreate',
    'EmailSummary',
    
    # Eto Run
    'EtoRunCreate',
    'EtoRun',
    'EtoEmailInfo',
    'EtoRunSummary',
    'EtoRunWithPdfData',
    'EtoRunStatusUpdate',
    'EtoRunTemplateMatchUpdate',
    'EtoRunDataExtractionUpdate',
    'EtoRunTransformationUpdate',
    'EtoRunOrderUpdate',
    'EtoRunResetResult',
    
    # PDF File
    'PdfFile',
    'PdfFileCreate',
    'PdfDetailData',
    
    # PDF Template Version
    'PdfTemplateVersionCreate',
    'PdfTemplateVersion',
    
    # PDF Template
    'PdfTemplate',
    'PdfTemplateCreate',
    'PdfTemplateUpdate',
    
    # Module Catalog
    'ModuleCatalogCreate',
    'ModuleCatalogUpdate',
    'ModuleCatalog',

    # Pipeline Definition Steps
    'PipelineDefinitionStepCreate',
    'PipelineDefinitionStep',

    # Pipeline Definitions
    'PipelineDefinitionCreate',
    'PipelineDefinition',
    'PipelineDefinitionSummary',
]