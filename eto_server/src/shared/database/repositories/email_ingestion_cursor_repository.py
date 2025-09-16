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
from src.features.email_ingestion.types import EmailIngestionCursor


logger = logging.getLogger(__name__)


class EmailIngestionCursorRepository(BaseRepository[EmailIngestionCursorModel]):
    """Repository for EmailIngestionCursorModel model operations"""
    
    @property
    def model_class(self):
        return EmailIngestionCursorModel
    
    def _convert_to_domain_object(self, cursor_model: EmailIngestionCursorModel) -> EmailIngestionCursor:
        """Convert database model to domain object while session is active"""
        cursor_data = {
            'id': getattr(cursor_model, 'id'),
            'email_address': getattr(cursor_model, 'email_address'),
            'folder_name': getattr(cursor_model, 'folder_name'),
            'last_processed_message_id': getattr(cursor_model, 'last_processed_message_id'),
            'last_processed_received_date': getattr(cursor_model, 'last_processed_received_date'),
            'last_check_time': getattr(cursor_model, 'last_check_time'),
            'total_emails_processed': getattr(cursor_model, 'total_emails_processed') or 0,
            'total_pdfs_found': getattr(cursor_model, 'total_pdfs_found') or 0,
            'created_at': getattr(cursor_model, 'created_at'),
            'updated_at': getattr(cursor_model, 'updated_at')
        }
        return EmailIngestionCursor(**cursor_data)
    
    def get_by_id(self, id: int) -> Optional[EmailIngestionCursor]:
        """Override BaseRepository method to return domain object"""
        try:
            with self.connection_manager.session_scope() as session:
                # Get the model from the session using SQLAlchemy 2.x pattern
                model = session.get(self.model_class, id)
                
                if model:
                    # Convert to domain object while session is still active
                    logger.debug(f"Retrieved email cursor: {getattr(model, 'email_address')}/{getattr(model, 'folder_name')}")
                    return self._convert_to_domain_object(model)
                else:
                    return None
        except SQLAlchemyError as e:
            logger.error(f"Error getting cursor {id}: {e}")
            raise RepositoryError(f"Failed to get cursor: {e}") from e
    
    def update(self, id: int, data: Dict[str, Any]) -> Optional[EmailIngestionCursor]:
        """Override BaseRepository method to return domain object"""
        try:
            with self.connection_manager.session_scope() as session:
                # Get the model from the session using SQLAlchemy 2.x pattern
                model = session.get(self.model_class, id)
                
                if not model:
                    return None
                
                # Update the model attributes using setattr
                for key, value in data.items():
                    if hasattr(model, key):
                        setattr(model, key, value)
                
                # Convert to domain object while session is still active
                logger.debug(f"Updated email cursor: {getattr(model, 'email_address')}/{getattr(model, 'folder_name')}")
                return self._convert_to_domain_object(model)
                
        except SQLAlchemyError as e:
            logger.error(f"Error updating cursor {id}: {e}")
            raise RepositoryError(f"Failed to update cursor: {e}") from e
    
    def get_by_email_and_folder(self, email_address: str, folder_name: str) -> Optional[EmailIngestionCursor]:
        """Get cursor for specific email and folder combination"""
        if not email_address or not folder_name:
            return None
        
        try:
            with self.connection_manager.session_scope() as session:
                cursor_model = session.query(self.model_class).filter(
                    self.model_class.email_address == email_address,
                    self.model_class.folder_name == folder_name
                ).first()
                
                if cursor_model:
                    logger.debug(f"Retrieved cursor for {email_address}/{folder_name}")
                    return self._convert_to_domain_object(cursor_model)
                return None
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting cursor for {email_address}/{folder_name}: {e}")
            raise RepositoryError(f"Failed to get cursor: {e}") from e
    
    
    def update_processing_stats(self, cursor_id: int, emails_processed: int, pdfs_found: int) -> Optional[EmailIngestionCursor]:
        """Update processing statistics for a cursor"""
        if cursor_id is None:
            raise ValueError("cursor_id cannot be None")
        
        if emails_processed < 0 or pdfs_found < 0:
            raise ValueError("emails_processed and pdfs_found must be non-negative")
        
        try:
            with self.connection_manager.session_scope() as session:
                # Get the model using SQLAlchemy 2.x pattern
                model = session.get(self.model_class, cursor_id)
                
                if not model:
                    logger.warning(f"Cursor with ID {cursor_id} not found")
                    return None
                
                # Calculate new statistics
                current_emails = getattr(model, 'total_emails_processed') or 0
                current_pdfs = getattr(model, 'total_pdfs_found') or 0
                new_emails_processed = current_emails + emails_processed
                new_pdfs_found = current_pdfs + pdfs_found
                
                # Update the model attributes using setattr
                current_time = datetime.now(timezone.utc)
                setattr(model, 'total_emails_processed', new_emails_processed)
                setattr(model, 'total_pdfs_found', new_pdfs_found)
                setattr(model, 'last_check_time', current_time)
                
                logger.debug(f"Updated stats for cursor {getattr(model, 'email_address')}/{getattr(model, 'folder_name')}: +{emails_processed} emails, +{pdfs_found} PDFs")
                
                # Convert to domain object while session is active
                return self._convert_to_domain_object(model)
                
        except SQLAlchemyError as e:
            logger.error(f"Error updating processing stats for cursor {cursor_id}: {e}")
            raise RepositoryError(f"Failed to update processing stats: {e}") from e
    
    def get_all_active_cursors(self) -> List[EmailIngestionCursor]:
        """Get all email cursors ordered by last check time"""
        try:
            with self.connection_manager.session_scope() as session:
                models = session.query(self.model_class).order_by(
                    self.model_class.last_check_time.desc()
                ).all()
                
                # Convert to domain objects while session is active
                logger.debug(f"Retrieved {len(models)} email cursors")
                return [self._convert_to_domain_object(model) for model in models]
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting all active cursors: {e}")
            raise RepositoryError(f"Failed to get active cursors: {e}") from e

