"""
Shared Database Infrastructure
Database models, connection management, and repositories
"""
from .connection import DatabaseConnectionManager, init_database_connection, get_connection_manager
from .models import *
from .repositories import *

__all__ = [
    # Connection management
    'DatabaseConnectionManager',
    'init_database_connection',
    'get_connection_manager',
    
    # Models (imported from models module)
    'Base',
    'EmailModel',
    'PdfFileModel',
    'PdfTemplateModel',
    'EtoRunModel',
    'EmailIngestionCursorModel',
    'TransformationPipelineModuleModel',
    'TransformationPipelineModel',
    'TransformationPipelineStepModel',
    'CustomTransformationModuleModel',
    'EmailIngestionConfigModel',
    
    # Repositories (imported from repositories module)
    'BaseRepository',
    'RepositoryError',
    'EmailIngestionConfigRepository',
    'EmailIngestionCursorRepository',
    'EtoRunRepository', 
    'PdfRepository',
    'TemplateRepository',
    'TransformationPipelineModuleRepository',
    'TransformationPipelineRepository',
]