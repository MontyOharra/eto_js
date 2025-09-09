"""
Email Repository
Data access layer for Email model operations
"""
from typing import Optional, List
from datetime import datetime
from .base_repository import BaseRepository
from ..models import Email


class EmailRepository(BaseRepository):
    """Repository for Email model operations"""
    
    @property
    def model_class(self):
        return Email
    
    def get_by_message_id(self, message_id: str) -> Optional[Email]:
        """Get email by Outlook message ID"""
        pass
    
    def get_by_sender(self, sender_email: str, limit: Optional[int] = None) -> List[Email]:
        """Get emails by sender email address"""
        pass
    
    def get_recent_emails(self, limit: int = 10) -> List[Email]:
        """Get most recent emails by received date"""
        pass
    
    def get_emails_with_attachments(self, limit: Optional[int] = None) -> List[Email]:
        """Get emails that have PDF attachments"""
        pass
    
    def get_emails_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Email]:
        """Get emails within date range"""
        pass
    
    def get_emails_by_folder(self, folder_name: str, limit: Optional[int] = None) -> List[Email]:
        """Get emails from specific folder"""
        pass