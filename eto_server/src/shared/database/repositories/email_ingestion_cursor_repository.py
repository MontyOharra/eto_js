"""
Email Ingestion Cursor Repository
Data access layer for EmailIngestionCursor model operations
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from .base_repository import BaseRepository, RepositoryError
from ..models import EmailIngestionCursorModel


logger = logging.getLogger(__name__)


class EmailIngestionCursorRepository(BaseRepository[EmailIngestionCursorModel]):
    """Repository for EmailIngestionCursorModel model operations"""
    
    @property
    def model_class(self):
        return EmailIngestionCursorModel
    
    def get_by_email_and_folder(self, email_address: str, folder_name: str) -> Optional[EmailIngestionCursorModel]:
        """Get cursor for specific email and folder combination"""
        if not email_address or not folder_name:
            return None
        
        try:
            with self.connection_manager.session_scope() as session:
                return session.query(self.model_class).filter(
                    self.model_class.email_address == email_address,
                    self.model_class.folder_name == folder_name
                ).first()
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting cursor for {email_address}/{folder_name}: {e}")
            raise RepositoryError(f"Failed to get cursor: {e}") from e
    
    
    def update_processing_stats(self, cursor_id: int, emails_processed: int, pdfs_found: int) -> Optional[EmailIngestionCursorModel]:
        """Update processing statistics for a cursor"""
        if cursor_id is None:
            raise ValueError("cursor_id cannot be None")
        
        if emails_processed < 0 or pdfs_found < 0:
            raise ValueError("emails_processed and pdfs_found must be non-negative")
        
        try:
            # Get existing cursor to calculate new stats
            cursor = self.get_by_id(cursor_id)
            
            if not cursor:
                logger.warning(f"Cursor with ID {cursor_id} not found")
                return None
            
            # Calculate new statistics
            new_emails_processed = (cursor.total_emails_processed or 0) + emails_processed
            new_pdfs_found = (cursor.total_pdfs_found or 0) + pdfs_found
            
            # Update using BaseRepository method
            update_data = {
                'total_emails_processed': new_emails_processed,
                'total_pdfs_found': new_pdfs_found,
                'last_check_time': datetime.now(timezone.utc)
            }
            
            updated_cursor = self.update(cursor_id, update_data)
            logger.debug(f"Updated stats for cursor {cursor_id}: +{emails_processed} emails, +{pdfs_found} PDFs")
            return updated_cursor
                
        except SQLAlchemyError as e:
            logger.error(f"Error updating processing stats for cursor {cursor_id}: {e}")
            raise RepositoryError(f"Failed to update processing stats: {e}") from e
    
    def get_all_active_cursors(self) -> List[EmailIngestionCursorModel]:
        """Get all email cursors ordered by last check time"""
        try:
            with self.connection_manager.session_scope() as session:
                return session.query(self.model_class).order_by(
                    self.model_class.last_check_time.desc()
                ).all()
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting all active cursors: {e}")
            raise RepositoryError(f"Failed to get active cursors: {e}") from e

