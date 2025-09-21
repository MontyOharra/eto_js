"""
Email Ingestion Cursor Repository
Enhanced with config association and proper Pydantic typing
"""
import logging
from typing import Optional, List
from datetime import datetime, timezone
from sqlalchemy.exc import SQLAlchemyError

from shared.database.repositories import BaseRepository
from shared.exceptions import RepositoryError, ObjectNotFoundError
from shared.database.models import EmailIngestionCursorModel
from shared.models.email_cursor import EmailCursor, EmailCursorCreate, EmailCursorUpdate

logger = logging.getLogger(__name__)


class EmailIngestionCursorRepository(BaseRepository[EmailIngestionCursorModel]):
    """Repository for cursor operations with config association"""
    
    @property
    def model_class(self):
        return EmailIngestionCursorModel
    
    def create(self, cursor_create: EmailCursorCreate) -> EmailCursor:
        """Create new cursor from Pydantic model"""
        try:
            with self.connection_manager.session_scope() as session:
                data = cursor_create.model_dump_for_db()
                model = self.model_class(**data)
                session.add(model)
                session.flush()
                
                logger.debug(f"Created cursor for config {model.config_id}")
                return EmailCursor.from_db_model(model)
                
        except SQLAlchemyError as e:
            logger.error(f"Error creating cursor: {e}")
            raise RepositoryError(f"Failed to create cursor: {e}") from e
    
    def get_by_id(self, cursor_id: int) -> Optional[EmailCursor]:
        """Get cursor by ID"""
        try:
            with self.connection_manager.session_scope() as session:
                model = session.get(self.model_class, cursor_id)
                
                if model:
                    return EmailCursor.from_db_model(model)
                return None
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting cursor {cursor_id}: {e}")
            raise RepositoryError(f"Failed to get cursor: {e}") from e
    
    def get_by_config_id(self, config_id: int) -> Optional[EmailCursor]:
        """Get cursor for a specific configuration"""
        try:
            with self.connection_manager.session_scope() as session:
                model = session.query(self.model_class).filter(
                    self.model_class.config_id == config_id
                ).first()
                
                if model:
                    return EmailCursor.from_db_model(model)
                return None
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting cursor for config {config_id}: {e}")
            raise RepositoryError(f"Failed to get cursor: {e}") from e
    
    def update_position(self, cursor_id: int, last_message_id: str,
                       last_received_date: datetime,
                       increment_emails: int = 0,
                       increment_pdfs: int = 0) -> EmailCursor:
        """Update cursor position and increment statistics"""
        try:
            with self.connection_manager.session_scope() as session:
                model = session.get(self.model_class, cursor_id)
                
                if not model:
                    raise ObjectNotFoundError('EmailCursor', cursor_id)
                
                # Update position
                model.last_processed_message_id = last_message_id
                model.last_processed_received_date = last_received_date
                model.last_check_time = datetime.now(timezone.utc)
                
                # Increment statistics
                model.total_emails_processed = (model.total_emails_processed or 0) + increment_emails
                model.total_pdfs_found = (model.total_pdfs_found or 0) + increment_pdfs
                
                session.flush()
                
                logger.debug(f"Updated cursor {cursor_id} position")
                return EmailCursor.from_db_model(model)
                
        except ObjectNotFoundError:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error updating cursor {cursor_id}: {e}")
            raise RepositoryError(f"Failed to update cursor: {e}") from e
    
    def delete(self, cursor_id: int) -> EmailCursor:
        """Delete cursor by ID"""
        try:
            with self.connection_manager.session_scope() as session:
                model = session.get(self.model_class, cursor_id)
                
                if not model:
                    raise ObjectNotFoundError('EmailCursor', cursor_id)
                
                deleted_cursor = EmailCursor.from_db_model(model)
                session.delete(model)
                
                logger.debug(f"Deleted cursor {cursor_id}")
                return deleted_cursor
                
        except ObjectNotFoundError:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error deleting cursor {cursor_id}: {e}")
            raise RepositoryError(f"Failed to delete cursor: {e}") from e
    
    def get_all_by_email(self, email_address: str) -> List[EmailCursor]:
        """Get all cursors for an email address"""
        try:
            with self.connection_manager.session_scope() as session:
                models = session.query(self.model_class).filter(
                    self.model_class.email_address == email_address
                ).all()
                
                return [EmailCursor.from_db_model(model) for model in models]
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting cursors for {email_address}: {e}")
            raise RepositoryError(f"Failed to get cursors: {e}") from e
    
    def get_by_email_and_folder(self, email_address: str, folder_name: str) -> Optional[EmailCursor]:
        """Get cursor for specific email and folder combination"""
        try:
            with self.connection_manager.session_scope() as session:
                model = session.query(self.model_class).filter(
                    self.model_class.email_address == email_address,
                    self.model_class.folder_name == folder_name
                ).first()
                
                if model:
                    return EmailCursor.from_db_model(model)
                return None
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting cursor for {email_address}/{folder_name}: {e}")
            raise RepositoryError(f"Failed to get cursor: {e}") from e