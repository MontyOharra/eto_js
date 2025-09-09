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
    
    def get_email_processing_summary(self, email_id: int) -> dict:
        """Get complete processing summary for an email (email, PDFs, ETO runs)"""
        pass
    
    def get_template_match_candidates(self, pdf_id: int) -> List[dict]:
        """Get potential template matches for a PDF"""
        pass
    
    def create_eto_run_for_pdf(self, pdf_id: int) -> dict:
        """Create a new ETO run for a PDF file"""
        pass
    
    def get_processing_dashboard_data(self) -> dict:
        """Get dashboard data for processing statistics"""
        pass
    
    def get_system_health_metrics(self) -> dict:
        """Get system health and database metrics"""
        pass
    
    # Transaction management for complex operations
    def execute_in_transaction(self, operation_func, *args, **kwargs):
        """Execute an operation within a database transaction"""
        pass