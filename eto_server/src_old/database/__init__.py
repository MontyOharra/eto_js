"""
ETO Database Package
Unified database architecture combining email processing and transformation pipelines
"""

# Connection management
from .connection import (
    DatabaseConnectionManager,
    DatabaseCreator,
    init_database_connection,
    get_connection_manager
)

# Models
from .models import (
    Base,
    EmailModel,
    PdfFileModel,
    PdfTemplateModel,
    TemplateExtractionRuleModel,
    TemplateExtractionStepModel,
    EtoRunModel,
    EmailCursorModel,
    TransformationPipelineModuleModel,
    TransformationPipelineModel,
    EmailIngestionConfigModel
)

# Repositories
from .repositories import (
    BaseRepository,
    EmailRepository,
    PdfRepository,
    TemplateRepository,
    EtoRunRepository,
    TransformationPipelineModuleRepository,
    TransformationPipelineRepository,
    CursorRepository,
    EmailConfigRepository
)

# Main database service
from .database_service import DatabaseService

# Public API
__all__ = [
    # High-level service (recommended for most use cases)
    'DatabaseService',
    
    # Connection management
    'init_database_connection',
    'get_connection_manager',
    'DatabaseConnectionManager',
    'DatabaseCreator',
    
    # Models (for type hints)
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
    
    # For advanced usage
    'EmailRepository',
    'PdfRepository',
    'TemplateRepository',
    'EtoRunRepository',
    'TransformationPipelineModuleRepository',
    'TransformationPipelineRepository',
    'CursorRepository',
    'EmailConfigRepository'
]


# Convenience initialization function
def setup_database(database_url: str) -> DatabaseService:
    """
    Setup database with connection string and return service
    
    Args:
        database_url: SQLAlchemy database URL for SQL Server
        
    Returns:
        Configured DatabaseService instance
    """
    connection_manager = init_database_connection(database_url)
    return DatabaseService(connection_manager)