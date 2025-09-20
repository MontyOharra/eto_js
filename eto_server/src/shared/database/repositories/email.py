"""
Email Repository
Data access layer for Email model operations
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from sqlalchemy.exc import SQLAlchemyError

from shared.database.repositories import BaseRepository
from shared.exceptions import RepositoryError, ObjectNotFoundError, ValidationError
from shared.database.models import EmailModel
from shared.domain import Email

logger = logging.getLogger(__name__)


class EmailRepository(BaseRepository[EmailModel]):
    """Repository for Email model operations"""
    
    @property
    def model_class(self):
        return EmailModel
    
    def _convert_to_domain_object(self, email_model: EmailModel) -> Email:
        """Convert database model to domain object while session is active"""
        email_data = {
            'id': getattr(email_model, 'id'),
            'message_id': getattr(email_model, 'message_id'),
            'subject': getattr(email_model, 'subject'),
            'sender_email': getattr(email_model, 'sender_email'),
            'sender_name': getattr(email_model, 'sender_name'),
            'received_date': getattr(email_model, 'received_date'),
            'folder_name': getattr(email_model, 'folder_name'),
            'has_pdf_attachments': getattr(email_model, 'has_pdf_attachments'),
            'attachment_count': getattr(email_model, 'attachment_count'),
            'created_at': getattr(email_model, 'created_at')
        }
        return Email(**email_data)
    
    def get_by_id(self, id: int) -> Optional[Email]:
        """Override BaseRepository method to return domain object"""
        try:
            with self.connection_manager.session_scope() as session:
                # Get the model from the session using SQLAlchemy 2.x pattern
                model = session.get(self.model_class, id)
                
                if model:
                    # Convert to domain object while session is still active
                    logger.debug(f"Retrieved email: {getattr(model, 'subject')} from {getattr(model, 'sender_email')}")
                    return self._convert_to_domain_object(model)
                else:
                    return None
        except SQLAlchemyError as e:
            logger.error(f"Error getting email {id}: {e}")
            raise RepositoryError(f"Failed to get email: {e}") from e
    
    def get_by_message_id(self, message_id: str) -> Optional[Email]:
        """Get email by message ID"""
        if not message_id:
            return None
        
        try:
            with self.connection_manager.session_scope() as session:
                email_model = session.query(self.model_class).filter(
                    self.model_class.message_id == message_id
                ).first()
                
                if email_model:
                    logger.debug(f"Retrieved email by message_id: {message_id}")
                    return self._convert_to_domain_object(email_model)
                return None
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting email by message_id {message_id}: {e}")
            raise RepositoryError(f"Failed to get email by message_id: {e}") from e
    
    def get_emails_by_date_range(self, start_date: datetime, end_date: datetime, 
                                folder_name: Optional[str] = None) -> List[Email]:
        """Get emails within date range, optionally filtered by folder"""
        try:
            with self.connection_manager.session_scope() as session:
                query = session.query(self.model_class).filter(
                    self.model_class.received_date >= start_date,
                    self.model_class.received_date <= end_date
                )
                
                if folder_name:
                    query = query.filter(self.model_class.folder_name == folder_name)
                
                models = query.order_by(self.model_class.received_date.desc()).all()
                
                # Convert to domain objects while session is active
                logger.debug(f"Retrieved {len(models)} emails for date range {start_date} to {end_date}")
                return [self._convert_to_domain_object(model) for model in models]
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting emails by date range: {e}")
            raise RepositoryError(f"Failed to get emails by date range: {e}") from e
    
    def get_emails_with_pdf_attachments(self, folder_name: Optional[str] = None, 
                                      limit: Optional[int] = None) -> List[Email]:
        """Get emails that have PDF attachments"""
        try:
            with self.connection_manager.session_scope() as session:
                query = session.query(self.model_class).filter(
                    self.model_class.has_pdf_attachments == True
                )
                
                if folder_name:
                    query = query.filter(self.model_class.folder_name == folder_name)
                
                query = query.order_by(self.model_class.received_date.desc())
                
                if limit:
                    query = query.limit(limit)
                
                models = query.all()
                
                # Convert to domain objects while session is active
                logger.debug(f"Retrieved {len(models)} emails with PDF attachments")
                return [self._convert_to_domain_object(model) for model in models]
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting emails with PDF attachments: {e}")
            raise RepositoryError(f"Failed to get emails with PDF attachments: {e}") from e
    
    def get_recent_emails(self, folder_name: str, hours: int = 24, limit: int = 100) -> List[Email]:
        """Get recent emails from specific folder"""
        try:
            with self.connection_manager.session_scope() as session:
                cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
                
                models = session.query(self.model_class).filter(
                    self.model_class.folder_name == folder_name,
                    self.model_class.received_date >= cutoff_time
                ).order_by(
                    self.model_class.received_date.desc()
                ).limit(limit).all()
                
                # Convert to domain objects while session is active
                logger.debug(f"Retrieved {len(models)} recent emails from {folder_name} (last {hours}h)")
                return [self._convert_to_domain_object(model) for model in models]
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting recent emails: {e}")
            raise RepositoryError(f"Failed to get recent emails: {e}") from e
    
    def create(self, 
               message_id: str,
               subject: str, 
               sender_email: str,
               sender_name: Optional[str],
               received_date: datetime,
               folder_name: str,
               has_pdf_attachments: bool,
               attachment_count: int) -> Email:
        """Create new email record"""
        try:
            with self.connection_manager.session_scope() as session:
                # Create new email model
                model = self.model_class()
                
                # Set attributes from parameters
                setattr(model, 'message_id', message_id)
                setattr(model, 'subject', subject)
                setattr(model, 'sender_email', sender_email)
                setattr(model, 'sender_name', sender_name)
                setattr(model, 'received_date', received_date)
                setattr(model, 'folder_name', folder_name)
                setattr(model, 'has_pdf_attachments', has_pdf_attachments)
                setattr(model, 'attachment_count', attachment_count)
                setattr(model, 'created_at', datetime.now(timezone.utc))
                
                # Add to session
                session.add(model)
                session.flush()  # Get the ID
                
                logger.debug(f"Created email record: {subject} from {sender_email}")
                
                # Convert to domain object while session is active
                return self._convert_to_domain_object(model)
                
        except SQLAlchemyError as e:
            logger.error(f"Error creating email record: {e}")
            raise RepositoryError(f"Failed to create email record: {e}") from e
    
    def email_exists_by_message_id(self, message_id: str) -> bool:
        """Check if email exists by message ID"""
        try:
            with self.connection_manager.session_scope() as session:
                exists = session.query(self.model_class).filter(
                    self.model_class.message_id == message_id
                ).first() is not None
                
                logger.debug(f"Email exists check for message_id {message_id}: {exists}")
                return exists
                
        except SQLAlchemyError as e:
            logger.error(f"Error checking email existence: {e}")
            raise RepositoryError(f"Failed to check email existence: {e}") from e