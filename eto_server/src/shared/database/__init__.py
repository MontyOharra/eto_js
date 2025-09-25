"""
Shared Database Infrastructure
Database models, connection management, and repositories
"""
from .connection import DatabaseConnectionManager, init_database_connection, get_connection_manager
from .models import *
# Import repositories individually to avoid circular imports
# Repositories can be imported directly when needed: from shared.database.repositories import SpecificRepository

__all__ = [
    # Connection management
    'DatabaseConnectionManager',
    'init_database_connection',
    'get_connection_manager',
    
    # Models (imported from models module)
    'BaseModel',
    'EmailModel',
    'PdfFileModel',
    'PdfTemplateModel',
    'PdfTemplateVersionModel',
    'EtoRunModel',  # Keep model for DB table creation - only repository/service layer is disabled
    'TransformationPipelineModuleModel',
    'TransformationPipelineModel',
    'TransformationPipelineStepModel',
    'CustomTransformationModuleModel',
    'EmailConfigModel',
]