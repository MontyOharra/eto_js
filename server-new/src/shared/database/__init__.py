"""
Database initialization and connection management
"""
from .models import (
    BaseModel,
    # Enums
    EtoStepStatus,
    EtoRunStatus,
    EtoRunProcessingStep,
    PdfTemplateStatus,
    # Email models
    EmailConfigModel,
    EmailModel,
    # PDF models
    PdfFileModel,
    PdfTemplateModel,
    PdfTemplateVersionModel,
    # Module catalog
    ModuleModel,
    # Pipeline models
    PipelineCompiledPlanModel,
    PipelineDefinitionModel,
    PipelineDefinitionStepModel,
    # ETO run models
    EtoRunModel,
    EtoRunTemplateMatchingModel,
    EtoRunExtractionModel,
    EtoRunPipelineExecutionModel,
    EtoRunPipelineExecutionStepModel,
)

from .connection import DatabaseConnectionManager, init_database_connection, get_connection_manager
from .unit_of_work import UnitOfWork

__all__ = [
    # Base
    'BaseModel',
    # Enums
    'EtoStepStatus',
    'EtoRunStatus',
    'EtoRunProcessingStep',
    'PdfTemplateStatus',
    # Email models
    'EmailConfigModel',
    'EmailModel',
    # PDF models
    'PdfFileModel',
    'PdfTemplateModel',
    'PdfTemplateVersionModel',
    # Module catalog
    'ModuleModel',
    # Pipeline models
    'PipelineCompiledPlanModel',
    'PipelineDefinitionModel',
    'PipelineDefinitionStepModel',
    # ETO run models
    'EtoRunModel',
    'EtoRunTemplateMatchingModel',
    'EtoRunExtractionModel',
    'EtoRunPipelineExecutionModel',
    'EtoRunPipelineExecutionStepModel',
    # Connection management
    'DatabaseConnectionManager',
    'init_database_connection',
    'get_connection_manager',
    # Unit of Work
    'UnitOfWork',
]
