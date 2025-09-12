"""
Email Ingestion Config Repository
Data access layer for EmailIngestionConfig model operations
"""
import logging
import json
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.exc import SQLAlchemyError
from .base_repository import BaseRepository, RepositoryError
from ..models import EmailIngestionConfigModel
from src.features.email_ingestion.types import EmailIngestionConfig, EmailConfigSummary, EmailFilterRule

logger = logging.getLogger(__name__)


class EmailIngestionConfigRepository(BaseRepository[EmailIngestionConfigModel]):
    """Repository for email ingestion configuration operations"""
    
    @property
    def model_class(self):
        return EmailIngestionConfigModel
    
    def _convert_to_domain_object(self, config_model: EmailIngestionConfigModel) -> EmailIngestionConfig:
        """Convert database model to domain object while session is active"""
        # Parse filter rules from JSON
        try:
            filter_rules_data = json.loads(config_model.filter_rules or "[]")
            filter_rules = [
                EmailFilterRule(
                    field=rule["field"],
                    operation=rule["operation"],
                    value=rule["value"],
                    case_sensitive=rule.get("case_sensitive", False)
                )
                for rule in filter_rules_data
            ]
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Invalid filter rules JSON in config {config_model.id}: {e}")
            filter_rules = []
        
        # Extract all values to force SQLAlchemy type evaluation while session is active
        config_data = {
            'id': config_model.id,
            'name': config_model.name,
            'description': config_model.description,
            'email_address': config_model.email_address,
            'folder_name': config_model.folder_name,
            'filter_rules': filter_rules,
            'poll_interval_seconds': config_model.poll_interval_seconds,
            'max_backlog_hours': config_model.max_backlog_hours,
            'error_retry_attempts': config_model.error_retry_attempts,
            'is_active': config_model.is_active,
            'is_running': config_model.is_running,
            'created_by': config_model.created_by,
            'created_at': config_model.created_at,
            'updated_at': config_model.updated_at,
            'last_used_at': config_model.last_used_at,
            'emails_processed': config_model.emails_processed,
            'pdfs_found': config_model.pdfs_found,
            'last_error_message': config_model.last_error_message,
            'last_error_at': config_model.last_error_at
        }
        return EmailIngestionConfig(**config_data)
    
    def _convert_to_summary(self, config_model: EmailIngestionConfigModel) -> EmailConfigSummary:
        """Convert database model to summary domain object while session is active"""
        summary_data = {
            'id': config_model.id,
            'name': config_model.name,
            'folder_name': config_model.folder_name,
            'is_active': config_model.is_active,
            'is_running': config_model.is_running,
            'emails_processed': config_model.emails_processed,
            'pdfs_found': config_model.pdfs_found,
            'last_used_at': config_model.last_used_at,
            'created_at': config_model.created_at,
            'updated_at': config_model.updated_at
        }
        return EmailConfigSummary(**summary_data)
    
    def get_by_id(self, id: int) -> Optional[EmailIngestionConfig]:
        """Override BaseRepository method to return domain object"""
        model = super().get_by_id(id)
        if model:
            # Need to be careful about session scope here
            with self.connection_manager.session_scope() as session:
                # Reattach to current session
                config = session.merge(model)
                return self._convert_to_domain_object(config)
        return None
    
    def update(self, id: int, data: Dict[str, Any]) -> Optional[EmailIngestionConfig]:
        """Override BaseRepository method to return domain object"""
        model = super().update(id, data)
        if model:
            with self.connection_manager.session_scope() as session:
                config = session.merge(model)
                return self._convert_to_domain_object(config)
        return None
    
    def get_all_configs(self) -> List[EmailConfigSummary]:
        """Get all configurations with business-specific ordering: active first, then by recency"""
        try:
            with self.connection_manager.session_scope() as session:
                models = session.query(self.model_class).order_by(
                    self.model_class.is_active.desc(),
                    self.model_class.updated_at.desc()
                ).all()
                
                # Convert to domain objects while session is active
                return [self._convert_to_summary(model) for model in models]
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting all configurations: {e}")
            raise RepositoryError(f"Failed to get all configurations: {e}") from e    
    
    def get_active_config(self) -> Optional[EmailIngestionConfig]:
        """Get the currently active configuration"""
        try:
            with self.connection_manager.session_scope() as session:
                config = session.query(self.model_class).filter(
                    self.model_class.is_active == True
                ).first()
                
                if not config:
                    return None
                
                # Convert to domain object while session is active
                return self._convert_to_domain_object(config)
                
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
    
    def set_config_active(self, config_id: int) -> Optional[EmailIngestionConfig]:
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
                    # Convert to domain object while session is active
                    return self._convert_to_domain_object(config)
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
        
        try:
            update_data = {
                'is_running': is_running,
                'updated_at': datetime.now(timezone.utc)
            }
            
            if is_running:
                update_data['last_used_at'] = datetime.now(timezone.utc)
            
            updated_config = self.update(config_id, update_data)
            if updated_config:
                logger.debug(f"Updated configuration {config_id} runtime status to: {"running" if is_running else "stopped"}")
            
            return updated_config
            
        except Exception as e:
            logger.error(f"Error updating runtime status for config {config_id}: {e}")
            raise RepositoryError(f"Failed to update runtime status: {e}") from e
    
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
    
    def delete_if_inactive(self, config_id: int) -> Dict[str, Any]:
        """Delete configuration only if it's not active. Returns result with name for logging."""
        try:
            with self.connection_manager.session_scope() as session:
                # Get config to check if it exists and is not active
                config = session.query(self.model_class).get(config_id)
                
                if not config:
                    return {
                        "success": False,
                        "message": f"Configuration with ID {config_id} not found"
                    }
                
                # Extract values while still in session
                is_active = config.is_active
                config_name = config.name
                
                if is_active:
                    return {
                        "success": False,
                        "message": "Cannot delete active configuration. Please activate another configuration first."
                    }
                
                # Delete the configuration
                session.delete(config)
                session.commit()
                
                logger.info(f"Deleted email configuration: {config_name}")
                
                return {
                    "success": True,
                    "name": config_name
                }
                
        except Exception as e:
            logger.error(f"Error deleting configuration {config_id}: {e}")
            raise RepositoryError(f"Failed to delete configuration: {e}") from e
    
