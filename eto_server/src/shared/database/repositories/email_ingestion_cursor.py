"""
Email Ingestion Cursor Repository
Simplified cursor operations
"""
import logging
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy.exc import SQLAlchemyError

from shared.database.repositories import BaseRepository
from shared.exceptions import RepositoryError, ObjectNotFoundError
from shared.database.models import EmailIngestionCursorModel
from shared.models.email_cursor import EmailCursor, EmailCursorCreate

logger = logging.getLogger(__name__)


class EmailIngestionCursorRepository(BaseRepository[EmailIngestionCursorModel]):
    """Simplified cursor repository"""
    
    @property
    def model_class(self):
        return EmailIngestionCursorModel
    
    def _convert_to_domain_object(self, cursor: EmailIngestionCursorModel) -> EmailCursor:
        """Convert SQLAlchemy model to domain object"""
        return EmailCursor.from_db_model(cursor)
    
    def create(self, cursor_create: EmailCursorCreate) -> EmailCursor:
        """Create new cursor from Pydantic model"""
        try:
            with self.connection_manager.session_scope() as session:
                data = cursor_create.model_dump_for_db()
                model = self.model_class(**data)
                session.add(model)
                session.flush()
                
                logger.debug(f"Created cursor for config {model.config_id}")
                return self._convert_to_domain_object(model)
                
        except SQLAlchemyError as e:
            logger.error(f"Error creating cursor: {e}")
            raise RepositoryError(f"Failed to create cursor: {e}") from e
    
    def get_by_config_id(self, config_id: int) -> Optional[EmailCursor]:
        """Get cursor for a specific configuration"""
        try:
            with self.connection_manager.session_scope() as session:
                model = session.query(self.model_class).filter(
                    self.model_class.config_id == config_id
                ).first()
                
                if model:
                    return self._convert_to_domain_object(model)
                return None
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting cursor for config {config_id}: {e}")
            raise RepositoryError(f"Failed to get cursor: {e}") from e
    
    def update_check_time_and_stats(self, config_id: int, 
                                   emails_processed: int = 0,
                                   pdfs_found: int = 0) -> EmailCursor:
        """Update last check time and increment statistics"""
        try:
            with self.connection_manager.session_scope() as session:
                model = session.query(self.model_class).filter(
                    self.model_class.config_id == config_id
                ).first()
                
                if not model:
                    raise ObjectNotFoundError('EmailCursor', config_id)
                
                # Update check time
                model.last_check_time = datetime.now(timezone.utc)
                
                # Increment statistics
                model.total_emails_processed = (model.total_emails_processed or 0) + emails_processed
                model.total_pdfs_found = (model.total_pdfs_found or 0) + pdfs_found
                
                session.flush()
                
                logger.debug(f"Updated cursor for config {config_id}: +{emails_processed} emails, +{pdfs_found} PDFs")
                return self._convert_to_domain_object(model)
                
        except ObjectNotFoundError:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error updating cursor for config {config_id}: {e}")
            raise RepositoryError(f"Failed to update cursor: {e}") from e
    
    def delete_by_config_id(self, config_id: int) -> bool:
        """Delete cursor by config ID"""
        try:
            with self.connection_manager.session_scope() as session:
                model = session.query(self.model_class).filter(
                    self.model_class.config_id == config_id
                ).first()
                
                if model:
                    session.delete(model)
                    logger.debug(f"Deleted cursor for config {config_id}")
                    return True
                return False
                
        except SQLAlchemyError as e:
            logger.error(f"Error deleting cursor for config {config_id}: {e}")
            raise RepositoryError(f"Failed to delete cursor: {e}") from e