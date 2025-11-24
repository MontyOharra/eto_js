"""
Database initialization and connection management
"""
from .models import (
    BaseModel,
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
    EtoSubRunModel,
    EtoSubRunExtractionModel,
    EtoSubRunPipelineExecutionModel,
    EtoSubRunPipelineExecutionStepModel,
)

from .connection import DatabaseConnectionManager, init_database_connection, get_connection_manager
from .access_connection import AccessConnectionManager
from .unit_of_work import UnitOfWork

__all__ = [
    # Base
    'BaseModel',
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
    'EtoSubRunModel',
    'EtoSubRunExtractionModel',
    'EtoSubRunPipelineExecutionModel',
    'EtoSubRunPipelineExecutionStepModel',
    # Connection management
    'DatabaseConnectionManager',
    'AccessConnectionManager',
    'init_database_connection',
    'get_connection_manager',
    # Unit of Work
    'UnitOfWork',
]
