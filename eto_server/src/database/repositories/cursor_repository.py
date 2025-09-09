"""
Cursor Repository
Data access layer for EmailCursor model operations
"""
from typing import Optional, List
from datetime import datetime
from .base_repository import BaseRepository
from ..models import EmailCursor


class CursorRepository(BaseRepository):
    """Repository for EmailCursor model operations"""
    
    @property
    def model_class(self):
        return EmailCursor
    
    def get_by_email_and_folder(self, email_address: str, folder_name: str) -> Optional[EmailCursor]:
        """Get cursor for specific email and folder combination"""
        pass
    
    def create_or_update_cursor(self, email_address: str, folder_name: str, cursor_data: dict) -> EmailCursor:
        """Create new cursor or update existing one"""
        pass
    
    def update_processing_stats(self, cursor_id: int, emails_processed: int, pdfs_found: int) -> Optional[EmailCursor]:
        """Update processing statistics for a cursor"""
        pass
    
    def get_all_active_cursors(self) -> List[EmailCursor]:
        """Get all email cursors"""
        pass