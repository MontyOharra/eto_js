"""
Email Config Repository
Data access layer for EmailIngestionConfig model operations
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.exc import SQLAlchemyError
from .base_repository import BaseRepository, RepositoryError
from ..models import EmailIngestionConfig

logger = logging.getLogger(__name__)


class EmailConfigRepository(BaseRepository[EmailIngestionConfig]):
    """Repository for email configuration operations"""
    
    @property
    def model_class(self):
        return EmailIngestionConfig
    
    def get_active_config(self) -> Optional[EmailIngestionConfig]:
        """Get the currently active configuration"""
        try:
            with self.connection_manager.session_scope() as session:
                return session.query(self.model_class).filter(
                    self.model_class.is_active == True
                ).first()
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting active configuration: {e}")
            raise RepositoryError(f"Failed to get active configuration: {e}") from e
    
    def get_active_config_data(self) -> Optional[Dict[str, Any]]:
        """Get the currently active configuration data without session binding"""
        try:
            with self.connection_manager.session_scope() as session:
                config = session.query(self.model_class).filter(
                    self.model_class.is_active == True
                ).first()
                
                if not config:
                    return None
                
                # Extract all needed data while session is open
                config_data = {
                    'id': config.id,
                    'name': config.name,
                    'description': config.description,
                    'email_address': config.email_address,
                    'folder_name': config.folder_name,
                    'filter_rules': config.filter_rules,
                    'poll_interval_seconds': config.poll_interval_seconds,
                    'max_backlog_hours': config.max_backlog_hours,
                    'error_retry_attempts': config.error_retry_attempts,
                    'is_active': config.is_active,
                    'is_running': config.is_running,
                    'created_by': config.created_by,
                    'created_at': config.created_at,
                    'updated_at': config.updated_at,
                    'last_used_at': config.last_used_at,
                    'emails_processed': config.emails_processed,
                    'pdfs_found': config.pdfs_found,
                    'last_error_message': config.last_error_message,
                    'last_error_at': config.last_error_at
                }
                
                return config_data
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting active configuration data: {e}")
            raise RepositoryError(f"Failed to get active configuration data: {e}") from e
    
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
    
    def set_config_active(self, config_id: int) -> Optional[EmailIngestionConfig]:
        """Activate specific configuration and deactivate others"""
        try:
            with self.connection_manager.session_scope() as session:
                # First deactivate all configs
                session.query(self.model_class).update({
                    'is_active': False,
                    'is_running': False,
                    'updated_at': datetime.now(timezone.utc)
                })
                
                # Then activate the specific config
                config = session.query(self.model_class).filter(
                    self.model_class.id == config_id
                ).first()
                
                if config:
                    config.is_active = True
                    config.last_used_at = datetime.now(timezone.utc)
                    config.updated_at = datetime.now(timezone.utc)
                    session.commit()
                    logger.info(f"Activated email configuration: {config_id}")
                    return config
                else:
                    logger.warning(f"Configuration {config_id} not found for activation")
                    return None
                
        except SQLAlchemyError as e:
            logger.error(f"Error setting config {config_id} active: {e}")
            raise RepositoryError(f"Failed to activate configuration: {e}") from e
    
    def set_config_active_and_get_name(self, config_id: int) -> Optional[str]:
        """Activate specific configuration and return its name"""
        try:
            with self.connection_manager.session_scope() as session:
                # First deactivate all configs
                session.query(self.model_class).update({
                    'is_active': False,
                    'is_running': False,
                    'updated_at': datetime.now(timezone.utc)
                })
                
                # Then activate the specific config
                config = session.query(self.model_class).filter(
                    self.model_class.id == config_id
                ).first()
                
                if config:
                    config.is_active = True
                    config.last_used_at = datetime.now(timezone.utc)
                    config.updated_at = datetime.now(timezone.utc)
                    
                    # Get the name while session is still open
                    config_name = config.name
                    
                    session.commit()
                    logger.info(f"Activated email configuration: {config_id}")
                    return config_name
                else:
                    logger.warning(f"Configuration {config_id} not found for activation")
                    return None
                
        except SQLAlchemyError as e:
            logger.error(f"Error setting config {config_id} active: {e}")
            raise RepositoryError(f"Failed to activate configuration: {e}") from e
    
    def update_runtime_status(self, config_id: int, is_running: bool) -> Optional[EmailIngestionConfig]:
        """Update runtime status"""
        if config_id is None:
            raise ValueError("config_id cannot be None")
        
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
    
    def increment_processing_stats(self, config_id: int, emails: int, pdfs: int) -> Optional[EmailIngestionConfig]:
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
            
        except Exception as e:
            logger.error(f"Error updating processing stats for config {config_id}: {e}")
            raise RepositoryError(f"Failed to update processing stats: {e}") from e
    
    def record_error(self, config_id: int, error_message: str) -> Optional[EmailIngestionConfig]:
        """Record processing error"""
        if config_id is None:
            raise ValueError("config_id cannot be None")
        
        if not error_message:
            raise ValueError("error_message cannot be empty")
        
        update_data = {
            'last_error_message': error_message,
            'last_error_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc)
        }
        
        updated_config = self.update(config_id, update_data)
        if updated_config:
            logger.debug(f"Recorded error for configuration {config_id}: {error_message}")
        
        return updated_config
    
    def get_runtime_statistics(self, config_id: int) -> Dict[str, Any]:
        """Get detailed runtime statistics for configuration"""
        try:
            config = self.get_by_id(config_id)
            
            if not config:
                return {"error": f"Configuration {config_id} not found"}
            
            stats = {
                "config_id": config.id,
                "name": config.name,
                "is_active": config.is_active,
                "is_running": config.is_running,
                "emails_processed": config.emails_processed or 0,
                "pdfs_found": config.pdfs_found or 0,
                "last_used_at": config.last_used_at.isoformat() if config.last_used_at else None,
                "last_error_message": config.last_error_message,
                "last_error_at": config.last_error_at.isoformat() if config.last_error_at else None,
                "created_at": config.created_at.isoformat() if config.created_at else None,
                "updated_at": config.updated_at.isoformat() if config.updated_at else None
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting runtime statistics for config {config_id}: {e}")
            raise RepositoryError(f"Failed to get runtime statistics: {e}") from e
    
    def get_all_configs_summary(self) -> List[Dict[str, Any]]:
        """Get summary of all configurations"""
        try:
            with self.connection_manager.session_scope() as session:
                configs = session.query(self.model_class).order_by(
                    self.model_class.is_active.desc(),
                    self.model_class.updated_at.desc()
                ).all()
                
                summaries = []
                for config in configs:
                    summary = {
                        "id": config.id,
                        "name": config.name,
                        "description": config.description,
                        "email_address": config.email_address,
                        "folder_name": config.folder_name,
                        "is_active": config.is_active,
                        "is_running": config.is_running,
                        "emails_processed": config.emails_processed or 0,
                        "pdfs_found": config.pdfs_found or 0,
                        "created_by": config.created_by,
                        "created_at": config.created_at.isoformat() if config.created_at else None,
                        "last_used_at": config.last_used_at.isoformat() if config.last_used_at else None
                    }
                    summaries.append(summary)
                
                return summaries
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting all config summaries: {e}")
            raise RepositoryError(f"Failed to get config summaries: {e}") from e