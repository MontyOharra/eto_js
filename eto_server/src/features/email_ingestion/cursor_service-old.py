"""
Email Cursor Service
Manages processing cursors with config association
"""
import logging
from typing import Optional, Dict, List
from datetime import datetime, timezone

from shared.database.repositories import EmailIngestionCursorRepository
from shared.models.email_cursor import EmailCursor, EmailCursorCreate
from shared.exceptions import ObjectNotFoundError, ValidationError

logger = logging.getLogger(__name__)


class EmailIngestionCursorService:
    """
    Manages processing cursors for email configurations.
    Internal service - no direct API access.
    """
    
    def __init__(self, cursor_repository: EmailIngestionCursorRepository):
        self.cursor_repo = cursor_repository
        self.logger = logging.getLogger(__name__)
    
    # === CRUD Operations ===
    
    def create_cursor(self, config_id: int, email_address: str, folder_name: str) -> EmailCursor:
        """Create a new cursor for a configuration"""
        try:
            # Check if cursor already exists for this config
            existing = self.cursor_repo.get_by_config_id(config_id)
            if existing:
                raise ValidationError(f"Cursor already exists for config {config_id}")
            
            cursor_create = EmailCursorCreate(
                config_id=config_id,
                email_address=email_address,
                folder_name=folder_name,
                last_processed_message_id=f"init_{int(datetime.now(timezone.utc).timestamp())}",
                last_processed_received_date=datetime.now(timezone.utc),
                last_check_time=datetime.now(timezone.utc),
                total_emails_processed=0,
                total_pdfs_found=0
            )
            
            cursor = self.cursor_repo.create(cursor_create)
            logger.info(f"Created cursor for config {config_id}: {email_address}/{folder_name}")
            return cursor
            
        except Exception as e:
            logger.error(f"Failed to create cursor for config {config_id}: {e}")
            raise
    
    def get_cursor_by_config(self, config_id: int) -> Optional[EmailCursor]:
        """Get cursor for a specific configuration"""
        return self.cursor_repo.get_by_config_id(config_id)
    
    def get_or_create_cursor(self, config_id: int, email_address: str, folder_name: str) -> EmailCursor:
        """Get existing cursor or create new one"""
        cursor = self.get_cursor_by_config(config_id)
        if not cursor:
            cursor = self.create_cursor(config_id, email_address, folder_name)
        return cursor
    
    def update_cursor(self, config_id: int, last_message_id: str, 
                     last_received_date: datetime, 
                     increment_emails: int = 0, 
                     increment_pdfs: int = 0) -> EmailCursor:
        """Update cursor position and statistics"""
        cursor = self.cursor_repo.get_by_config_id(config_id)
        if not cursor:
            raise ObjectNotFoundError('EmailCursor', config_id)
        
        return self.cursor_repo.update_position(
            cursor_id=cursor.id,
            last_message_id=last_message_id,
            last_received_date=last_received_date,
            increment_emails=increment_emails,
            increment_pdfs=increment_pdfs
        )
    
    def delete_cursor_by_config(self, config_id: int) -> bool:
        """Delete cursor associated with a configuration"""
        cursor = self.cursor_repo.get_by_config_id(config_id)
        if cursor:
            self.cursor_repo.delete(cursor.id)
            logger.info(f"Deleted cursor for config {config_id}")
            return True
        return False
    
    def get_cursor_stats_by_config(self, config_id: int) -> Optional[Dict]:
        """Get cursor statistics for a configuration"""
        cursor = self.cursor_repo.get_by_config_id(config_id)
        if not cursor:
            return None
        
        return {
            "config_id": config_id,
            "email_address": cursor.email_address,
            "folder_name": cursor.folder_name,
            "total_emails_processed": cursor.total_emails_processed,
            "total_pdfs_found": cursor.total_pdfs_found,
            "last_processed_date": cursor.last_processed_received_date,
            "last_check_time": cursor.last_check_time
        }