"""
Email Ingestion Config Repository
Data access layer for EmailIngestionConfig model operations
"""
import logging
import json
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.exc import SQLAlchemyError

from shared.database.repositories import BaseRepository
from shared.exceptions import RepositoryError, ObjectNotFoundError, ValidationError
from shared.database.models import EmailIngestionConfigModel
from shared.models import EmailConfig

logger = logging.getLogger(__name__)


class EmailIngestionConfigRepository(BaseRepository[EmailIngestionConfigModel]):
    """Repository for email ingestion configuration operations"""
    
    @property
    def model_class(self):
        return EmailIngestionConfigModel
    
    def _convert_to_domain_object(self, config_model: EmailIngestionConfigModel) -> EmailConfig:
        """Convert database model to domain object while session is active"""
        return EmailConfig.from_db_model(config_model)
    
    
    def get_all_configs(self) -> List[EmailConfig]:
        """Get all configurations with business-specific ordering: active first, then by recency"""
        try:
            with self.connection_manager.session_scope() as session:
                models = session.query(self.model_class).order_by(
                    self.model_class.is_active.desc(),
                    self.model_class.updated_at.desc()
                ).all()
                
                # Convert to domain objects while session is active
                logger.debug(f"Retrieved {len(models)} email configurations")
                return [self._convert_to_domain_object(model) for model in models]
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting all configurations: {e}")
            raise RepositoryError(f"Failed to get all configurations: {e}") from e    
    
    def get_active_config(self) -> Optional[EmailConfig]:
        """Get the currently active configuration"""
        try:
            with self.connection_manager.session_scope() as session:
                config = session.query(self.model_class).filter(
                    self.model_class.is_active == True
                ).first()
                
                if not config:
                    return None
                
                # Convert to domain object while session is active
                logger.debug(f"Retrieved active email configuration: {config.name}")
                return self._convert_to_domain_object(config)
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting active configuration: {e}")
            raise RepositoryError(f"Failed to get active configuration: {e}") from e    
    
    def update(self, id: int, data: Dict[str, Any]) -> Optional[EmailIngestionConfig]:
        """Override BaseRepository method to return domain object"""
        try:
            with self.connection_manager.session_scope() as session:
                # Get the model from the session
                model = session.get(self.model_class, id)
                
                if not model:
                    return None
                
                # Update the model attributes
                for key, value in data.items():
                    if hasattr(model, key):
                        setattr(model, key, value)
                
                # Convert to domain object while session is still active
                logger.debug(f"Updated email configuration: {model.name}")
                return self._convert_to_domain_object(model)
                
        except SQLAlchemyError as e:
            logger.error(f"Error updating config {id}: {e}")
            raise RepositoryError(f"Failed to update config: {e}") from e

    def deactivate_all_configs(self) -> None:
        """Deactivate all configurations"""
        try:
            with self.connection_manager.session_scope() as session:
                session.query(self.model_class).update({
                    'is_active': False,
                    'is_running': False,
                    'updated_at': datetime.now(timezone.utc)
                })
                # session_scope handles commit automatically
                logger.debug("Deactivated all email configurations")
                
        except SQLAlchemyError as e:
            logger.error(f"Error deactivating all configurations: {e}")
            raise RepositoryError(f"Failed to deactivate configurations: {e}") from e
    
    def set_config_active(self, config_id: int) -> Optional[EmailIngestionConfig]:
        """Activate specific configuration and deactivate others"""
        try:
            with self.connection_manager.session_scope() as session:
                current_time = datetime.now(timezone.utc)
                
                # First check if the target config exists using SQLAlchemy 2.x pattern
                target_config = session.get(self.model_class, config_id)
                
                if not target_config:
                    logger.warning(f"Configuration {config_id} not found for activation")
                    raise RepositoryError(f"Configuration {config_id} not found")
                
                # Deactivate all configs first
                session.query(self.model_class).update({
                    'is_active': False,
                    'is_running': False,
                    'updated_at': current_time
                })
                
                # Activate the target config
                setattr(target_config, 'is_active', True)
                setattr(target_config, 'is_running', False)  # Will be set to True when service starts
                setattr(target_config, 'updated_at', current_time)
                
                logger.debug(f"Activated email configuration: {target_config.name}")
                
                return self._convert_to_domain_object(target_config)
            
        except SQLAlchemyError as e:
            logger.error(f"Error setting config {config_id} active: {e}")
            raise RepositoryError(f"Failed to activate configuration: {e}") from e
    
    def update_runtime_status(self, config_id: int, is_running: bool) -> Optional[EmailIngestionConfig]:
        """Update runtime status"""
        if config_id is None:
            raise ValueError("config_id cannot be None")
        
        try:
            with self.connection_manager.session_scope() as session:
                # Get the model using SQLAlchemy 2.x pattern
                model = session.get(self.model_class, config_id)
                
                if not model:
                    return None
                
                # Update the model attributes using setattr
                current_time = datetime.now(timezone.utc)
                setattr(model, 'is_running', is_running)
                setattr(model, 'updated_at', current_time)
                
                if is_running:
                    setattr(model, 'last_used_at', current_time)
                
                logger.debug(f"Updated configuration {model.name} runtime status to: {"running" if is_running else "stopped"}")
                
                # Convert to domain object while session is active
                return self._convert_to_domain_object(model)
                
        except SQLAlchemyError as e:
            logger.error(f"Error updating runtime status for config {config_id}: {e}")
            raise RepositoryError(f"Failed to update runtime status: {e}") from e
    
    def increment_processing_stats(self, config_id: int, emails: int, pdfs: int) -> Optional[EmailIngestionConfig]:
        """Update processing statistics"""
        if config_id is None:
            raise ValueError("config_id cannot be None")
        
        if emails < 0 or pdfs < 0:
            raise ValueError("emails and pdfs must be non-negative")
        
        try:
            with self.connection_manager.session_scope() as session:
                # Get the model using SQLAlchemy 2.x pattern
                model = session.get(self.model_class, config_id)
                
                if not model:
                    logger.warning(f"Configuration {config_id} not found for stats update")
                    return None
                
                # Calculate new statistics
                current_emails = model.emails_processed or 0
                current_pdfs = model.pdfs_found or 0
                new_emails_processed = current_emails + emails
                new_pdfs_found = current_pdfs + pdfs
                
                # Update the model attributes using setattr
                current_time = datetime.now(timezone.utc)
                setattr(model, 'emails_processed', new_emails_processed)
                setattr(model, 'pdfs_found', new_pdfs_found)
                setattr(model, 'last_used_at', current_time)
                setattr(model, 'updated_at', current_time)
                
                logger.debug(f"Updated stats for config {model.name}: +{emails} emails, +{pdfs} PDFs")
                
                # Convert to domain object while session is active
                return self._convert_to_domain_object(model)
                
        except SQLAlchemyError as e:
            logger.error(f"Error updating processing stats for config {config_id}: {e}")
            raise RepositoryError(f"Failed to update processing stats: {e}") from e
    
    def record_error(self, config_id: int, error_message: str) -> Optional[EmailIngestionConfig]:
        """Record processing error"""
        if config_id is None:
            raise ValueError("config_id cannot be None")
        
        if not error_message:
            raise ValueError("error_message cannot be empty")
        
        try:
            with self.connection_manager.session_scope() as session:
                # Get the model using SQLAlchemy 2.x pattern
                model = session.get(self.model_class, config_id)
                
                if not model:
                    return None
                
                # Update the model attributes using setattr
                current_time = datetime.now(timezone.utc)
                setattr(model, 'last_error_message', error_message)
                setattr(model, 'last_error_at', current_time)
                setattr(model, 'updated_at', current_time)
                
                logger.debug(f"Recorded error for configuration {model.name}: {error_message}")
                
                # Convert to domain object while session is active
                return self._convert_to_domain_object(model)
                
        except SQLAlchemyError as e:
            logger.error(f"Error recording error for config {config_id}: {e}")
            raise RepositoryError(f"Failed to record error: {e}") from e
    
    def delete_if_inactive(self, config_id: int) -> Dict[str, Any]:
        """Delete configuration only if it's not active. Returns result with name for logging."""
        try:
            with self.connection_manager.session_scope() as session:
                # Get config to check if it exists and is not active using SQLAlchemy 2.x pattern
                config = session.get(self.model_class, config_id)
                
                if not config:
                    return {
                        "success": False,
                        "message": f"Configuration with ID {config_id} not found"
                    }
                
                # Extract values while still in session using getattr for proper column access
                is_active = getattr(config, 'is_active')
                config_name = getattr(config, 'name')
                
                if is_active:
                    return {
                        "success": False,
                        "message": "Cannot delete active configuration. Please activate another configuration first."
                    }
                
                # Delete the configuration
                session.delete(config)
                # session_scope handles commit automatically
                
                logger.debug(f"Deleted email configuration: {config_name}")
                
                return {
                    "success": True,
                    "name": config_name
                }
                
        except Exception as e:
            logger.error(f"Error deleting configuration {config_id}: {e}")
            raise RepositoryError(f"Failed to delete configuration: {e}") from e