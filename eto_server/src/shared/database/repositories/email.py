"""
Email Repository
Data access layer for Email model operations (append-only pattern)
"""
import logging
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from shared.database.repositories import BaseRepository
from shared.exceptions import RepositoryError, ValidationError
from shared.database.models import EmailModel
from shared.models import Email, EmailCreate, EmailSummary
from shared.utils import DateTimeUtils

logger = logging.getLogger(__name__)


class EmailRepository(BaseRepository[EmailModel]):
    """
    Repository for Email model operations.
    Follows append-only pattern - no updates or deletes.
    """
    
    @property
    def model_class(self):
        return EmailModel
    
    def _convert_to_domain_object(self, email_model: EmailModel) -> Email:
        """
        Convert database model to Pydantic domain object
        
        Args:
            email_model: Database model instance
            
        Returns:
            Email domain object
        """
        return Email.from_db_model(email_model)
    
    def create(self, email_create: EmailCreate) -> Email:
        """
        Create new email record
        
        Args:
            email_create: EmailCreate model with email data
            
        Returns:
            Created Email domain object
            
        Raises:
            ValidationError: If email with same message_id already exists for config
            RepositoryError: If database operation fails
        """
        try:
            with self.connection_manager.session_scope() as session:
                # Check for duplicate
                existing = session.query(self.model_class).filter(
                    self.model_class.config_id == email_create.config_id,
                    self.model_class.message_id == email_create.message_id
                ).first()
                
                if existing:
                    raise ValidationError(
                        f"Email with message_id {email_create.message_id} "
                        f"already exists for config {email_create.config_id}"
                    )
                
                # Create new model instance
                model = self.model_class()
                
                # Set fields from EmailCreate
                data = email_create.model_dump_for_db()
                for field, value in data.items():
                    if hasattr(model, field):
                        setattr(model, field, value)
                
                # Set timestamps
                current_time = DateTimeUtils.utc_now()
                setattr(model, 'processed_at', current_time)
                setattr(model, 'created_at', current_time)
                
                # Add to session and flush to get ID
                session.add(model)
                session.flush()
                
                logger.info(f"Created email record: {email_create.subject} from {email_create.sender_email}")
                
                # Convert to domain object while session is active
                return self._convert_to_domain_object(model)
                
        except IntegrityError as e:
            logger.warning(f"Integrity error creating email: {e}")
            raise ValidationError(f"Email already exists or invalid data: {e}") from e
        except SQLAlchemyError as e:
            logger.error(f"Error creating email record: {e}")
            raise RepositoryError(f"Failed to create email record: {e}") from e
    
    def get(self, email_id: int) -> Optional[Email]:
        """
        Get email by ID
        
        Args:
            email_id: Database ID
            
        Returns:
            Email if found, None otherwise
        """
        try:
            with self.connection_manager.session_scope() as session:
                model = session.get(self.model_class, email_id)
                
                if model:
                    logger.debug(f"Retrieved email {email_id}")
                    return self._convert_to_domain_object(model)
                return None
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting email {email_id}: {e}")
            raise RepositoryError(f"Failed to get email: {e}") from e
    
    def get_by_message_id(self, config_id: int, message_id: str) -> Optional[Email]:
        """
        Get email by config ID and message ID
        
        Args:
            config_id: Email configuration ID
            message_id: Email message ID from provider
            
        Returns:
            Email if found, None otherwise
        """
        if not message_id:
            return None
        
        try:
            with self.connection_manager.session_scope() as session:
                model = session.query(self.model_class).filter(
                    self.model_class.config_id == config_id,
                    self.model_class.message_id == message_id
                ).first()
                
                if model:
                    logger.debug(f"Retrieved email by message_id: {message_id} for config {config_id}")
                    return self._convert_to_domain_object(model)
                return None
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting email by message_id {message_id}: {e}")
            raise RepositoryError(f"Failed to get email by message_id: {e}") from e
    
    def exists_by_message_id(self, config_id: int, message_id: str) -> bool:
        """
        Check if email exists for config and message ID
        
        Args:
            config_id: Email configuration ID
            message_id: Email message ID from provider
            
        Returns:
            True if email exists, False otherwise
        """
        if not message_id:
            return False
            
        try:
            with self.connection_manager.session_scope() as session:
                exists = session.query(self.model_class).filter(
                    self.model_class.config_id == config_id,
                    self.model_class.message_id == message_id
                ).first() is not None
                
                logger.debug(f"Email exists check for config {config_id}, message_id {message_id}: {exists}")
                return exists
                
        except SQLAlchemyError as e:
            logger.error(f"Error checking email existence: {e}")
            raise RepositoryError(f"Failed to check email existence: {e}") from e
    
    def get_by_config(self, config_id: int, limit: int = 100, offset: int = 0) -> List[Email]:
        """
        Get emails for a specific configuration
        
        Args:
            config_id: Email configuration ID
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List of Email objects, ordered by received_date desc
        """
        try:
            with self.connection_manager.session_scope() as session:
                query = session.query(self.model_class).filter(
                    self.model_class.config_id == config_id
                ).order_by(
                    self.model_class.received_date.desc()
                )
                
                if offset:
                    query = query.offset(offset)
                if limit:
                    query = query.limit(limit)
                
                models = query.all()
                
                logger.debug(f"Retrieved {len(models)} emails for config {config_id}")
                return [self._convert_to_domain_object(model) for model in models]
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting emails by config: {e}")
            raise RepositoryError(f"Failed to get emails by config: {e}") from e
    
    def get_with_pdfs(self, config_id: Optional[int] = None, limit: int = 100) -> List[Email]:
        """
        Get emails that have PDF attachments
        
        Args:
            config_id: Optional config ID to filter by
            limit: Maximum number of records to return
            
        Returns:
            List of Email objects with PDF attachments
        """
        try:
            with self.connection_manager.session_scope() as session:
                query = session.query(self.model_class).filter(
                    self.model_class.has_pdf_attachments == True
                )
                
                if config_id:
                    query = query.filter(self.model_class.config_id == config_id)
                
                query = query.order_by(self.model_class.received_date.desc())
                
                if limit:
                    query = query.limit(limit)
                
                models = query.all()
                
                logger.debug(f"Retrieved {len(models)} emails with PDF attachments")
                return [self._convert_to_domain_object(model) for model in models]
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting emails with PDFs: {e}")
            raise RepositoryError(f"Failed to get emails with PDFs: {e}") from e
    
    def get_recent(self, hours: int = 24, config_id: Optional[int] = None, limit: int = 100) -> List[Email]:
        """
        Get recent emails within specified hours
        
        Args:
            hours: Number of hours to look back
            config_id: Optional config ID to filter by
            limit: Maximum number of records to return
            
        Returns:
            List of recent Email objects
        """
        try:
            with self.connection_manager.session_scope() as session:
                cutoff_time = DateTimeUtils.utc_now() - timedelta(hours=hours)
                
                query = session.query(self.model_class).filter(
                    self.model_class.received_date >= cutoff_time
                )
                
                if config_id:
                    query = query.filter(self.model_class.config_id == config_id)
                
                query = query.order_by(
                    self.model_class.received_date.desc()
                ).limit(limit)
                
                models = query.all()
                
                logger.debug(f"Retrieved {len(models)} recent emails (last {hours}h)")
                return [self._convert_to_domain_object(model) for model in models]
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting recent emails: {e}")
            raise RepositoryError(f"Failed to get recent emails: {e}") from e
    
    def get_summaries_by_config(self, config_id: int, limit: int = 100) -> List[EmailSummary]:
        """
        Get email summaries for UI display
        
        Args:
            config_id: Email configuration ID
            limit: Maximum number of records to return
            
        Returns:
            List of EmailSummary objects
        """
        try:
            with self.connection_manager.session_scope() as session:
                models = session.query(self.model_class).filter(
                    self.model_class.config_id == config_id
                ).order_by(
                    self.model_class.received_date.desc()
                ).limit(limit).all()
                
                summaries = []
                for model in models:
                    summary = EmailSummary(
                        id=model.id,
                        config_id=model.config_id,
                        subject=model.subject,
                        sender_email=model.sender_email,
                        received_date=model.received_date,
                        has_pdf_attachments=model.has_pdf_attachments,
                        pdf_count=model.pdf_count,
                        created_at=model.created_at
                    )
                    summaries.append(summary)
                
                logger.debug(f"Retrieved {len(summaries)} email summaries for config {config_id}")
                return summaries
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting email summaries: {e}")
            raise RepositoryError(f"Failed to get email summaries: {e}") from e
    
    def count_by_config(self, config_id: int) -> int:
        """
        Count total emails for a configuration
        
        Args:
            config_id: Email configuration ID
            
        Returns:
            Total count of emails
        """
        try:
            with self.connection_manager.session_scope() as session:
                count = session.query(self.model_class).filter(
                    self.model_class.config_id == config_id
                ).count()
                
                logger.debug(f"Counted {count} emails for config {config_id}")
                return count
                
        except SQLAlchemyError as e:
            logger.error(f"Error counting emails: {e}")
            raise RepositoryError(f"Failed to count emails: {e}") from e
    
    def count_pdfs_by_config(self, config_id: int) -> int:
        """
        Count total PDF attachments for a configuration
        
        Args:
            config_id: Email configuration ID
            
        Returns:
            Total count of PDFs across all emails
        """
        try:
            with self.connection_manager.session_scope() as session:
                from sqlalchemy import func
                
                result = session.query(
                    func.sum(self.model_class.pdf_count)
                ).filter(
                    self.model_class.config_id == config_id
                ).scalar()
                
                count = result or 0
                logger.debug(f"Counted {count} PDFs for config {config_id}")
                return count
                
        except SQLAlchemyError as e:
            logger.error(f"Error counting PDFs: {e}")
            raise RepositoryError(f"Failed to count PDFs: {e}") from e