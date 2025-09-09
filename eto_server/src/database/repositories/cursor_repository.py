"""
Cursor Repository
Data access layer for EmailCursor model operations
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from .base_repository import BaseRepository, RepositoryError
from ..models import EmailCursor


logger = logging.getLogger(__name__)


class CursorRepository(BaseRepository[EmailCursor]):
    """Repository for EmailCursor model operations"""
    
    @property
    def model_class(self):
        return EmailCursor
    
    def get_by_email_and_folder(self, email_address: str, folder_name: str) -> Optional[EmailCursor]:
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
    
    def create_or_update_cursor(self, email_address: str, folder_name: str, cursor_data: Dict[str, Any]) -> EmailCursor:
        """Create new cursor or update existing one"""
        if not email_address or not folder_name:
            raise ValueError("email_address and folder_name are required")
        
        if not cursor_data:
            raise ValueError("cursor_data cannot be empty")
        
        try:
            # Check if cursor already exists
            existing_cursor = self.get_by_email_and_folder(email_address, folder_name)
            
            if existing_cursor:
                # Update existing cursor
                update_data = {
                    **cursor_data,
                    'last_check_time': datetime.utcnow()
                }
                updated_cursor = self.update(existing_cursor.id, update_data)
                logger.debug(f"Updated cursor for {email_address}/{folder_name}")
                return updated_cursor
            else:
                # Create new cursor
                create_data = {
                    'email_address': email_address,
                    'folder_name': folder_name,
                    'last_check_time': datetime.utcnow(),
                    'total_emails_processed': 0,
                    'total_pdfs_found': 0,
                    **cursor_data
                }
                new_cursor = self.create(create_data)
                logger.debug(f"Created new cursor for {email_address}/{folder_name}")
                return new_cursor
                
        except IntegrityError as e:
            # Handle race condition where another process created the cursor
            if "_email_folder_cursor_uc" in str(e) or "UNIQUE constraint" in str(e):
                logger.warning(f"Cursor already exists for {email_address}/{folder_name}, retrying update")
                existing_cursor = self.get_by_email_and_folder(email_address, folder_name)
                if existing_cursor:
                    update_data = {
                        **cursor_data,
                        'last_check_time': datetime.utcnow()
                    }
                    return self.update(existing_cursor.id, update_data)
            raise RepositoryError(f"Failed to create or update cursor: {e}") from e
        except Exception as e:
            logger.error(f"Error creating/updating cursor for {email_address}/{folder_name}: {e}")
            raise RepositoryError(f"Failed to create or update cursor: {e}") from e
    
    def update_processing_stats(self, cursor_id: int, emails_processed: int, pdfs_found: int) -> Optional[EmailCursor]:
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
                'last_check_time': datetime.utcnow()
            }
            
            updated_cursor = self.update(cursor_id, update_data)
            logger.debug(f"Updated stats for cursor {cursor_id}: +{emails_processed} emails, +{pdfs_found} PDFs")
            return updated_cursor
                
        except SQLAlchemyError as e:
            logger.error(f"Error updating processing stats for cursor {cursor_id}: {e}")
            raise RepositoryError(f"Failed to update processing stats: {e}") from e
    
    def get_all_active_cursors(self) -> List[EmailCursor]:
        """Get all email cursors ordered by last check time"""
        try:
            with self.connection_manager.session_scope() as session:
                return session.query(self.model_class).order_by(
                    self.model_class.last_check_time.desc()
                ).all()
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting all active cursors: {e}")
            raise RepositoryError(f"Failed to get active cursors: {e}") from e