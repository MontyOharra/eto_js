"""
Email Repository
Data access layer for Email model operations
"""
import logging
from typing import Optional, List
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
from .base_repository import BaseRepository, RepositoryError
from ..models import Email


logger = logging.getLogger(__name__)


class EmailRepository(BaseRepository[Email]):
    """Repository for Email model operations"""
    
    @property
    def model_class(self):
        return Email
    
    def get_by_message_id(self, message_id: str) -> Optional[Email]:
        """Get email by Outlook message ID"""
        if not message_id:
            return None
        
        return self.get_by_field_single('message_id', message_id)
    
    def get_by_sender(self, sender_email: str, limit: Optional[int] = None) -> List[Email]:
        """Get emails by sender email address"""
        if not sender_email:
            return []
        
        try:
            with self.connection_manager.session_scope() as session:
                query = session.query(self.model_class).filter(
                    self.model_class.sender_email == sender_email
                ).order_by(self.model_class.received_date.desc())
                
                if limit is not None:
                    query = query.limit(limit)
                
                return query.all()
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting emails by sender {sender_email}: {e}")
            raise RepositoryError(f"Failed to get emails by sender: {e}") from e
    
    def get_recent_emails(self, limit: int = 10) -> List[Email]:
        """Get most recent emails by received date"""
        try:
            with self.connection_manager.session_scope() as session:
                return session.query(self.model_class).order_by(
                    self.model_class.received_date.desc()
                ).limit(limit).all()
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting recent emails: {e}")
            raise RepositoryError(f"Failed to get recent emails: {e}") from e
    
    def get_emails_with_attachments(self, limit: Optional[int] = None) -> List[Email]:
        """Get emails that have PDF attachments"""
        try:
            with self.connection_manager.session_scope() as session:
                query = session.query(self.model_class).filter(
                    self.model_class.has_pdf_attachments == True
                ).order_by(self.model_class.received_date.desc())
                
                if limit is not None:
                    query = query.limit(limit)
                
                return query.all()
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting emails with attachments: {e}")
            raise RepositoryError(f"Failed to get emails with attachments: {e}") from e
    
    def get_emails_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Email]:
        """Get emails within date range"""
        if not start_date or not end_date:
            raise ValueError("Both start_date and end_date are required")
        
        if start_date > end_date:
            raise ValueError("start_date cannot be after end_date")
        
        try:
            with self.connection_manager.session_scope() as session:
                return session.query(self.model_class).filter(
                    self.model_class.received_date >= start_date,
                    self.model_class.received_date <= end_date
                ).order_by(self.model_class.received_date.desc()).all()
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting emails by date range {start_date} to {end_date}: {e}")
            raise RepositoryError(f"Failed to get emails by date range: {e}") from e
    
    def get_emails_by_folder(self, folder_name: str, limit: Optional[int] = None) -> List[Email]:
        """Get emails from specific folder"""
        if not folder_name:
            return []
        
        try:
            with self.connection_manager.session_scope() as session:
                query = session.query(self.model_class).filter(
                    self.model_class.folder_name == folder_name
                ).order_by(self.model_class.received_date.desc())
                
                if limit is not None:
                    query = query.limit(limit)
                
                return query.all()
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting emails by folder {folder_name}: {e}")
            raise RepositoryError(f"Failed to get emails by folder: {e}") from e