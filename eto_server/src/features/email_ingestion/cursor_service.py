"""
Email Ingestion Cursor Service
Simplified cursor management for email configurations
"""
import logging
from typing import Optional
from datetime import datetime, timezone

from shared.database.repositories.email_ingestion_cursor import EmailIngestionCursorRepository
from shared.models.email_cursor import EmailCursor, EmailCursorCreate
from shared.exceptions import ServiceError, ObjectNotFoundError

logger = logging.getLogger(__name__)


class CursorService:
    """Internal service for cursor management"""
    
    def __init__(self, cursor_repository: EmailIngestionCursorRepository):
        self.cursor_repository = cursor_repository
        logger.info("CursorService initialized")
    
    def create_cursor(self, config_id: int) -> EmailCursor:
        """Create new cursor for a configuration"""
        try:
            # Check if cursor already exists
            existing = self.cursor_repository.get_by_config_id(config_id)
            if existing:
                logger.debug(f"Cursor already exists for config {config_id}")
                return existing
            
            # Create new cursor
            cursor_create = EmailCursorCreate(
                config_id=config_id,
                last_check_time=None,
                total_emails_processed=0,
                total_pdfs_found=0
            )
            
            cursor = self.cursor_repository.create(cursor_create)
            logger.info(f"Created cursor for config {config_id}")
            return cursor
            
        except Exception as e:
            logger.error(f"Failed to create cursor for config {config_id}: {e}")
            raise ServiceError(f"Failed to create cursor: {e}") from e
    
    def get_cursor(self, config_id: int) -> Optional[EmailCursor]:
        """Get cursor for a configuration"""
        try:
            return self.cursor_repository.get_by_config_id(config_id)
        except Exception as e:
            logger.error(f"Failed to get cursor for config {config_id}: {e}")
            raise ServiceError(f"Failed to get cursor: {e}") from e
    
    def update_after_check(self, config_id: int, 
                          emails_processed: int = 0,
                          pdfs_found: int = 0) -> EmailCursor:
        """Update cursor after email check"""
        try:
            cursor = self.cursor_repository.update_check_time_and_stats(
                config_id=config_id,
                emails_processed=emails_processed,
                pdfs_found=pdfs_found
            )
            
            logger.debug(f"Updated cursor for config {config_id}: "
                        f"+{emails_processed} emails, +{pdfs_found} PDFs")
            return cursor
            
        except ObjectNotFoundError:
            # Create cursor if it doesn't exist
            logger.warning(f"Cursor not found for config {config_id}, creating new one")
            self.create_cursor(config_id)
            # Try update again
            return self.cursor_repository.update_check_time_and_stats(
                config_id=config_id,
                emails_processed=emails_processed,
                pdfs_found=pdfs_found
            )
        except Exception as e:
            logger.error(f"Failed to update cursor for config {config_id}: {e}")
            raise ServiceError(f"Failed to update cursor: {e}") from e
    
    def delete_cursor_by_config(self, config_id: int) -> bool:
        """Delete cursor when config is deactivated"""
        try:
            result = self.cursor_repository.delete_by_config_id(config_id)
            if result:
                logger.info(f"Deleted cursor for deactivated config {config_id}")
            else:
                logger.debug(f"No cursor to delete for config {config_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to delete cursor for config {config_id}: {e}")
            raise ServiceError(f"Failed to delete cursor: {e}") from e
    
    def get_statistics(self, config_id: int) -> dict:
        """Get processing statistics for a config"""
        cursor = self.get_cursor(config_id)
        if not cursor:
            return {
                "last_check_time": None,
                "total_emails_processed": 0,
                "total_pdfs_found": 0,
                "has_cursor": False
            }
        
        return {
            "last_check_time": cursor.last_check_time,
            "total_emails_processed": cursor.total_emails_processed,
            "total_pdfs_found": cursor.total_pdfs_found,
            "has_cursor": True
        }