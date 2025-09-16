"""
Email Config Service
Manages email ingestion config with validation and admin operations
"""
import json
import logging
from typing import Dict, List, Any, Optional

from .types import EmailIngestionConfig, EmailFilterRule
from ...shared.database.repositories import EmailIngestionConfigRepository

logger = logging.getLogger(__name__)


class EmailIngestionConfigService:
    """Manages email ingestion config with validation and admin operations"""
    
    def __init__(self, config_repo: EmailIngestionConfigRepository):
        self.config_repo = config_repo
        self.logger = logging.getLogger(__name__)

    # === High-Level API Methods ===
    def create_config(self, config: EmailIngestionConfig) -> EmailIngestionConfig:
        """Create new email ingestion config from domain object"""
        try:
            self.logger.debug(f"Creating new email config: {config.name}")

            # Serialize filter rules to JSON for database storage
            filter_rules_json = json.dumps([
                {
                    "field": rule.field,
                    "operation": rule.operation,
                    "value": rule.value,
                    "case_sensitive": rule.case_sensitive
                }
                for rule in config.filter_rules
            ])

            # Create config record and get ID
            config_id = self.config_repo.create_and_get_id({
                "name": config.name,
                "description": config.description,
                "email_address": config.email_address,
                "folder_name": config.folder_name,
                "filter_rules": filter_rules_json,
                "poll_interval_seconds": config.poll_interval_seconds,
                "max_backlog_hours": config.max_backlog_hours,
                "error_retry_attempts": config.error_retry_attempts,
                "is_active": False,  # New configs start inactive
                "is_running": False,
                "created_by": config.created_by,
                "emails_processed": 0,
                "pdfs_found": 0
            })
            
            self.logger.info(f"Created email config {config.name} with ID {config_id}")

            # Return the created config from repository
            created_config = self.config_repo.get_by_id(config_id)
            if not created_config:
                raise Exception(f"Failed to retrieve created config with ID {config_id}")

            return created_config

        except Exception as e:
            self.logger.exception(f"Error creating config: {e}")
            raise
    
    def update_config(self, config_id: int, config_update: EmailIngestionConfig) -> EmailIngestionConfig:
        """Update existing email ingestion config from domain object"""
        try:
            self.logger.debug(f"Updating email config ID {config_id}")

            # Serialize filter rules to JSON for database storage
            filter_rules_json = json.dumps([
                {
                    "field": rule.field,
                    "operation": rule.operation,
                    "value": rule.value,
                    "case_sensitive": rule.case_sensitive
                }
                for rule in config_update.filter_rules
            ])

            # Update config record
            config = self.config_repo.update(config_id, {
                "email_address": config_update.email_address,
                "folder_name": config_update.folder_name,
                "filter_rules": filter_rules_json,
                "poll_interval_seconds": config_update.poll_interval_seconds,
                "max_backlog_hours": config_update.max_backlog_hours,
                "error_retry_attempts": config_update.error_retry_attempts,
            })
            
            if not config:
                raise Exception(f"Config with ID {config_id} not found")

            # Extract name to avoid Column type issues
            config_name = config.name
            self.logger.info(f"Updated email config {config_name}")

            return config

        except Exception as e:
            self.logger.exception(f"Error updating config: {e}")
            raise
    
    def activate_config(self, config_id: int) -> EmailIngestionConfig:
        """Activate an email ingestion config (deactivates all others)"""
        try:
            self.logger.debug(f"Activating email config ID {config_id}")
            
            # Set this config as active
            config = self.config_repo.set_config_active(config_id)
            
            if not config:
                raise Exception(f"Config with ID {config_id} not found")

            # Extract name to avoid Column type issues
            config_name = config.name
            self.logger.info(f"Activated email config: {config_name}")

            return config

        except Exception as e:
            self.logger.exception(f"Error activating config: {e}")
            raise
    
    def get_active_config(self) -> Optional[EmailIngestionConfig]:
        """Get currently active email ingestion config as domain object"""
        try:
            config = self.config_repo.get_active_config()
            
            if not config:
                self.logger.warning("No active email config found")
                return None
            
            return config  # Repository now returns domain object directly
        
        except Exception as e:
            self.logger.exception(f"Error getting active config: {e}")
            return None
    
    def get_config(self, config_id: int) -> Optional[EmailIngestionConfig]:
        """Get specific email ingestion config by ID as domain object"""
        try:
            return self.config_repo.get_by_id(config_id)
        
        except Exception as e:
            self.logger.exception(f"Error getting config {config_id}: {e}")
            return None
    
    def list_configs(self, order_by: Optional[str] = None, desc: bool = False) -> List[EmailIngestionConfig]:
        """List all email ingestion configs with full details"""
        try:
            if order_by:
                # For custom ordering, would need to update repository to support this
                # For now, just use get_all_configs which returns domain objects
                configs = self.config_repo.get_all_configs()
            else:
                configs = self.config_repo.get_all_configs()
            
            # Repository now returns domain objects directly
            return configs
        
        except Exception as e:
            self.logger.exception(f"Error listing configs: {e}")
            return []
    
    def delete_config(self, config_id: int) -> bool:
        """Delete an email ingestion config"""
        try:
            self.logger.debug(f"Deleting email config ID {config_id}")
            
            # Delegate to repository for atomic delete operation
            result = self.config_repo.delete_if_inactive(config_id)

            if not result["success"]:
                raise Exception(result["message"])

            self.logger.info(f"Deleted email config: {result['name']}")

            return True

        except Exception as e:
            self.logger.exception(f"Error deleting config: {e}")
            raise
    
    def update_runtime_status(self, config_id: int, is_running: bool) -> EmailIngestionConfig:
        """Update runtime status of config"""
        try:
            self.logger.debug(f"Updating runtime status for config {config_id} to: {'running' if is_running else 'stopped'}")
            
            config = self.config_repo.update_runtime_status(config_id, is_running)

            if not config:
                raise Exception(f"Config with ID {config_id} not found")

            # Extract name to avoid Column type issues
            config_name = config.name
            self.logger.info(f"Updated runtime status for config: {config_name}")

            return config

        except Exception as e:
            self.logger.exception(f"Error updating runtime status for config {config_id}: {e}")
            raise
    
    def increment_processing_stats(self, config_id: int, emails: int, pdfs: int) -> Optional[EmailIngestionConfig]:
        """Increment processing statistics for config"""
        try:
            self.logger.debug(f"Incrementing stats for config {config_id}: +{emails} emails, +{pdfs} PDFs")
            
            config = self.config_repo.increment_processing_stats(config_id, emails, pdfs)
            
            if not config:
                self.logger.warning(f"Config with ID {config_id} not found for stats update")
                return None
            
            return config
        
        except Exception as e:
            self.logger.exception(f"Error incrementing processing stats for config {config_id}: {e}")
            return None

    # === Helper Methods ===