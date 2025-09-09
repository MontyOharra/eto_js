"""
Template Repository
Data access layer for PdfTemplate model operations
"""
from typing import Optional, List
from datetime import datetime
from .base_repository import BaseRepository
from ..models import PdfTemplate


class TemplateRepository(BaseRepository):
    """Repository for PdfTemplate model operations"""
    
    @property
    def model_class(self):
        return PdfTemplate
    
    def get_active_templates(self) -> List[PdfTemplate]:
        """Get all active templates"""
        pass
    
    def get_by_customer(self, customer_name: str) -> List[PdfTemplate]:
        """Get templates by customer name"""
        pass
    
    def get_by_status(self, status: str, limit: Optional[int] = None) -> List[PdfTemplate]:
        """Get templates by status (active, archived, draft)"""
        pass
    
    def get_current_versions(self) -> List[PdfTemplate]:
        """Get only current version templates"""
        pass
    
    def get_most_used(self, limit: int = 10) -> List[PdfTemplate]:
        """Get most frequently used templates"""
        pass
    
    def update_usage_stats(self, template_id: int, last_used_at: datetime) -> Optional[PdfTemplate]:
        """Update usage count and last used timestamp"""
        pass
    
    def get_template_statistics(self) -> dict:
        """Get template usage statistics"""
        pass