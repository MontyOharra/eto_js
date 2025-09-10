"""
Database Service
Main database service that aggregates all repositories
Provides high-level database operations for application services
"""
from typing import Optional, List, Dict, Any
from .connection import DatabaseConnectionManager
from .repositories import (
    EmailRepository,
    PdfRepository, 
    TemplateRepository,
    EtoRunRepository,
    ModuleRepository,
    PipelineRepository,
    CursorRepository
)


class DatabaseService:
    """
    Main database service aggregating all repositories
    Provides unified interface for all database operations
    """
    
    def __init__(self, connection_manager: DatabaseConnectionManager):
        """Initialize database service with all repositories"""
        # Email processing repositories
        self.emails = EmailRepository(connection_manager)
        self.pdfs = PdfRepository(connection_manager)
        self.templates = TemplateRepository(connection_manager)
        self.eto_runs = EtoRunRepository(connection_manager)
        self.cursors = CursorRepository(connection_manager)
        
        # Transformation pipeline repositories
        self.modules = ModuleRepository(connection_manager)
        self.pipelines = PipelineRepository(connection_manager)
        
        # Store connection manager for complex transactions
        self.connection_manager = connection_manager
    
    # High-level business operations that span multiple repositories
    
    def create_email_with_attachments(self, email_data: dict, pdf_attachments: List[dict]) -> dict:
        """Create email record with associated PDF attachments"""
        pass