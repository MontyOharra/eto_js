"""
Shared Database Infrastructure
Database models, connection management, and repositories
"""
from .connection import DatabaseConnectionManager, DatabaseCreator, init_database_connection, get_connection_manager
from .models import *
from .repositories import *

__all__ = [
    # Connection management
    'DatabaseConnectionManager',
    'DatabaseCreator', 
    'init_database_connection',
    'get_connection_manager',
    
    # Models (imported from models module)
    'Base',
    'EmailModel',
    'PdfFileModel', 
    'PdfTemplateModel',
    'TemplateExtractionRuleModel',
    'TemplateExtractionStepModel',
    'EtoRunModel',
    'EmailCursorModel',
    'TransformationPipelineModuleModel',
    'TransformationPipelineModel',
    'EmailIngestionConfigModel',
    
    # Repositories (imported from repositories module)
    'BaseRepository',
    'RepositoryError',
    'EmailConfigRepository',
    'CursorRepository',
    'EtoRunRepository', 
    'PdfRepository',
    'TemplateRepository',
    'TransformationPipelineModuleRepository',
    'TransformationPipelineRepository',
]