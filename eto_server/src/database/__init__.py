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
    Email,
    PdfFile,
    PdfTemplate,
    TemplateExtractionRule,
    TemplateExtractionStep,
    EtoRun,
    EmailCursor,
    BaseModule,
    Pipeline,
    EmailIngestionConfig
)

# Repositories
from .repositories import (
    BaseRepository,
    EmailRepository,
    PdfRepository,
    TemplateRepository,
    EtoRunRepository,
    ModuleRepository,
    PipelineRepository,
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
    'Email',
    'PdfFile',
    'PdfTemplate', 
    'TemplateExtractionRule',
    'TemplateExtractionStep',
    'EtoRun',
    'EmailCursor',
    'BaseModule',
    'Pipeline',
    'EmailIngestionConfig',
    
    # For advanced usage
    'EmailRepository',
    'PdfRepository',
    'TemplateRepository',
    'EtoRunRepository',
    'ModuleRepository',
    'PipelineRepository',
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