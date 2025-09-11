"""
Email Config Repository
Data access layer for EmailIngestionConfig model operations
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.exc import SQLAlchemyError
from .base_repository import BaseRepository, RepositoryError
from ..models import EmailIngestionConfigModel

logger = logging.getLogger(__name__)


class EmailConfigRepository(BaseRepository[EmailIngestionConfigModel]):
    """Repository for email configuration operations"""
    
    @property
    def model_class(self):
        return EmailIngestionConfigModel
    
    def get_all_configs(self) -> List[EmailIngestionConfigModel]:
        """Get all configurations with business-specific ordering: active first, then by recency"""
        try:
            with self.connection_manager.session_scope() as session:
                return session.query(self.model_class).order_by(
                    self.model_class.is_active.desc(),
                    self.model_class.updated_at.desc()
                ).all()
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting all configurations: {e}")
            raise RepositoryError(f"Failed to get all configurations: {e}") from e    
    
    def get_active_config(self) -> Optional[EmailIngestionConfigModel]:
        """Get the currently active configuration"""
        try:
            with self.connection_manager.session_scope() as session:
                config = session.query(self.model_class).filter(
                    self.model_class.is_active == True
                ).first()
                
                if not config:
                    return None
                
                # Force load all attributes that services need while session is active
                _ = config.filter_rules
                _ = config.name
                _ = config.is_active
                _ = config.emails_processed
                _ = config.created_at
                _ = config.updated_at
                _ = config.last_used_at
                _ = config.last_error_message
                _ = config.last_error_at
                _ = config.pdfs_found
                _ = config.is_running
                _ = config.created_by
                
                # Remove from session but keep loaded data
                session.expunge(config)
                return config
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting active configuration: {e}")
            raise RepositoryError(f"Failed to get active configuration: {e}") from e
    
    def deactivate_all_configs(self) -> None:
        """Deactivate all configurations"""
        try:
            with self.connection_manager.session_scope() as session:
                session.query(self.model_class).update({
                    'is_active': False,
                    'is_running': False,
                    'updated_at': datetime.now(timezone.utc)
                })
                session.commit()
                logger.info("Deactivated all email configurations")
                
        except SQLAlchemyError as e:
            logger.error(f"Error deactivating all configurations: {e}")
            raise RepositoryError(f"Failed to deactivate configurations: {e}") from e
    
    def set_config_active(self, config_id: int) -> Optional[EmailIngestionConfigModel]:
        """Activate specific configuration and deactivate others"""
        try:
            with self.connection_manager.session_scope() as session:
                current_time = datetime.now(timezone.utc)
                
                # First deactivate all configs
                session.query(self.model_class).update({
                    'is_active': False,
                    'is_running': False,
                    'updated_at': current_time
                })
                
                # Then update the specific config to be active
                updated_rows = session.query(self.model_class).filter(
                    self.model_class.id == config_id
                ).update({
                    'is_active': True,
                    'last_used_at': current_time,
                    'updated_at': current_time
                })
                
                if updated_rows > 0:
                    # Get the updated config to return
                    config = session.query(self.model_class).get(config_id)
                    session.commit()
                    logger.info(f"Activated email configuration: {config_id}")
                    return config
                else:
                    logger.warning(f"Configuration {config_id} not found for activation")
                    return None
                
        except SQLAlchemyError as e:
            logger.error(f"Error setting config {config_id} active: {e}")
            raise RepositoryError(f"Failed to activate configuration: {e}") from e
    
    def update_runtime_status(self, config_id: int, is_running: bool) -> Optional[EmailIngestionConfigModel]:
        """Update runtime status"""
        if config_id is None:
            raise ValueError("config_id cannot be None")
        
        try:
            update_data = {
                'is_running': is_running,
                'updated_at': datetime.now(timezone.utc)
            }
            
            if is_running:
                update_data['last_used_at'] = datetime.now(timezone.utc)
            
            updated_config = self.update(config_id, update_data)
            if updated_config:
                status_text = "running" if is_running else "stopped"
                logger.debug(f"Updated configuration {config_id} runtime status to: {status_text}")
            
            return updated_config
            
        except Exception as e:
            logger.error(f"Error updating runtime status for config {config_id}: {e}")
            raise RepositoryError(f"Failed to update runtime status: {e}") from e
    
    def increment_processing_stats(self, config_id: int, emails: int, pdfs: int) -> Optional[EmailIngestionConfigModel]:
        """Update processing statistics"""
        if config_id is None:
            raise ValueError("config_id cannot be None")
        
        if emails < 0 or pdfs < 0:
            raise ValueError("emails and pdfs must be non-negative")
        
        try:
            # Get current config to increment stats
            current_config = self.get_by_id(config_id)
            
            if not current_config:
                logger.warning(f"Configuration {config_id} not found for stats update")
                return None
            
            # Calculate new statistics
            new_emails_processed = (current_config.emails_processed or 0) + emails
            new_pdfs_found = (current_config.pdfs_found or 0) + pdfs
            
            # Update using BaseRepository method
            update_data = {
                'emails_processed': new_emails_processed,
                'pdfs_found': new_pdfs_found,
                'last_used_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc)
            }
            
            updated_config = self.update(config_id, update_data)
            if updated_config:
                logger.debug(f"Updated stats for config {config_id}: +{emails} emails, +{pdfs} PDFs")
            
            return updated_config
            
        except SQLAlchemyError as e:
            logger.error(f"Error updating processing stats for config {config_id}: {e}")
            raise RepositoryError(f"Failed to update processing stats: {e}") from e
    
    def record_error(self, config_id: int, error_message: str) -> Optional[EmailIngestionConfigModel]:
        """Record processing error"""
        if config_id is None:
            raise ValueError("config_id cannot be None")
        
        if not error_message:
            raise ValueError("error_message cannot be empty")
        
        try:
            update_data = {
                'last_error_message': error_message,
                'last_error_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc)
            }
            
            updated_config = self.update(config_id, update_data)
            if updated_config:
                logger.debug(f"Recorded error for configuration {config_id}: {error_message}")
            
            return updated_config
            
        except Exception as e:
            logger.error(f"Error recording error for config {config_id}: {e}")
            raise RepositoryError(f"Failed to record error: {e}") from e
    
