"""
Email Config Service
Thin orchestration layer for email config management with business validation
"""
import logging
from typing import List, Optional
from datetime import datetime, timezone

from shared.models.email_config import EmailConfig, EmailConfigCreate, EmailConfigUpdate
from shared.database.repositories.email_ingestion_config import EmailIngestionConfigRepository
from shared.exceptions import ObjectNotFoundError, ValidationError, RepositoryError

logger = logging.getLogger(__name__)


class EmailIngestionConfigService:
    """Thin orchestration layer for email config with business validation"""
    
    def __init__(self, connection_manager):
        if not connection_manager:
            raise RuntimeError("Database connection manager is required")
        
        self.connection_manager = connection_manager
        
        # Repository layer - with explicit type annotation for IDE support
        self.config_repo: EmailIngestionConfigRepository = EmailIngestionConfigRepository(self.connection_manager)
        
        self.logger = logging.getLogger(__name__)
    
    # ========== CRUD Operations ==========
    
    def create_config(self, config_create: EmailConfigCreate) -> EmailConfig:
        """
        Create new email configuration
        
        Args:
            config_create: EmailConfigCreate model with configuration data
            
        Returns:
            Created EmailConfig
            
        Raises:
            RepositoryError: If database operation fails
        """
        self.logger.debug(f"Creating new email config: {config_create.name}")
        
        # Repository handles all serialization and database operations
        config = self.config_repo.create(config_create)
        
        self.logger.info(f"Created email config '{config.name}' with ID {config.id}")
        return config
    
    def update_config(self, config_id: int, config_update: EmailConfigUpdate) -> EmailConfig:
        """
        Update existing email configuration
        
        Args:
            config_id: Configuration ID to update
            config_update: EmailConfigUpdate model with fields to update
            
        Returns:
            Updated EmailConfig
            
        Raises:
            ObjectNotFoundError: If configuration not found
            RepositoryError: If database operation fails
        
        Note:
            email_address and folder_name are immutable and not included in EmailConfigUpdate
        """
        self.logger.debug(f"Updating email config ID {config_id}")
        
        # Repository handles partial updates and serialization
        config = self.config_repo.update(config_id, config_update)
        
        if config:
            self.logger.info(f"Updated email config '{config.name}'")
            return config
        else:
            # Repository returns None for not found in update
            raise ObjectNotFoundError('EmailConfig', config_id)
    
    def get_config(self, config_id: int) -> Optional[EmailConfig]:
        """
        Get single configuration by ID
        
        Args:
            config_id: Configuration ID
            
        Returns:
            EmailConfig or None if not found
            
        Raises:
            RepositoryError: If database operation fails
        """
        return self.config_repo.get_by_id(config_id)
    
    def list_configs(self, is_active: Optional[bool] = None, order_by: str = 'created_at', desc: bool = False) -> List[EmailConfig]:
        """
        List all configurations with sorting
        
        Args:
            is_active: Filter by active status (None for all configs)
            order_by: Field to sort by (created_at, updated_at, name, is_active, last_used_at, emails_processed)
            desc: Sort in descending order
            
        Returns:
            List of EmailConfig models
            
        Raises:
            RepositoryError: If database operation fails
        """
        # Validate sort field
        allowed_fields = ['created_at', 'updated_at', 'name', 'is_active', 'last_used_at', 'emails_processed', 'pdfs_found']
        if order_by not in allowed_fields:
            self.logger.warning(f"Invalid order_by field '{order_by}', using 'created_at'")
            order_by = 'created_at'
        
        # Get all configs with sorting
        configs = self.config_repo.get_all(order_by=order_by, desc=desc)
        
        # Filter by active status if specified
        if is_active is not None:
            configs = [c for c in configs if c.is_active == is_active]
        
        return configs
    
    def delete_config(self, config_id: int) -> EmailConfig:
        """
        Delete email configuration
        
        Args:
            config_id: Configuration ID to delete
            
        Returns:
            Deleted EmailConfig
            
        Raises:
            ObjectNotFoundError: If configuration not found
            ValidationError: If configuration is active
            RepositoryError: If database operation fails
        """
        self.logger.debug(f"Deleting email config ID {config_id}")
        
        # Repository handles validation and raises appropriate exceptions
        config = self.config_repo.delete(config_id)
        
        self.logger.info(f"Deleted email config '{config.name}'")
        return config
    
    # ========== Business Operations ==========
    
    def activate_config(self, config_id: int, activation_time: Optional[datetime] = None) -> EmailConfig:
        """
        Activate email configuration with progress tracking
        
        Args:
            config_id: Configuration ID to activate
            activation_time: When the activation occurred (defaults to now)
            
        Returns:
            Activated EmailConfig
            
        Raises:
            ObjectNotFoundError: If configuration not found
            RepositoryError: If database operation fails
        """
        if activation_time is None:
            activation_time = datetime.now(timezone.utc)
            
        self.logger.debug(f"Activating email config ID {config_id} at {activation_time}")
        
        # Repository handles activation with progress reset
        config = self.config_repo.activate(config_id, activation_time)
        
        self.logger.info(f"Activated email config '{config.name}'")
        return config
    
    def deactivate_config(self, config_id: int) -> EmailConfig:
        """
        Deactivate email configuration
        
        Args:
            config_id: Configuration ID to deactivate
            
        Returns:
            Deactivated EmailConfig
            
        Raises:
            ObjectNotFoundError: If configuration not found
            RepositoryError: If database operation fails
        """
        self.logger.debug(f"Deactivating email config ID {config_id}")
        
        config = self.config_repo.deactivate(config_id)
        
        self.logger.info(f"Deactivated email config '{config.name}'")
        return config
    
    def get_active_configs(self) -> List[EmailConfig]:
        """
        Get all currently active configurations
        
        Returns:
            List of active EmailConfig models
            
        Raises:
            RepositoryError: If database operation fails
        """
        configs = self.config_repo.get_active_configs()
        
        if configs:
            self.logger.debug(f"Retrieved {len(configs)} active configs")
        else:
            self.logger.debug("No active email configs found")
        
        return configs
    
    def get_active_config(self) -> Optional[EmailConfig]:
        """
        Get first active configuration (for backward compatibility)
        
        Returns:
            First active EmailConfig or None if no active config
            
        Raises:
            RepositoryError: If database operation fails
        """
        configs = self.get_active_configs()
        return configs[0] if configs else None
    
    # ========== Convenience Methods ==========
    
    def list_configs_active_first(self) -> List[EmailConfig]:
        """
        List all configurations with active configs first
        Useful for UI dropdowns and default listings
        
        Returns:
            List of EmailConfig models
            
        Raises:
            RepositoryError: If database operation fails
        """
        return self.config_repo.get_all_active_first()
    
    # ========== Runtime Operations ==========
    
    def update_runtime_status(self, config_id: int, is_running: bool) -> EmailConfig:
        """
        Update runtime status of configuration
        
        Args:
            config_id: Configuration ID
            is_running: New running status
            
        Returns:
            Updated EmailConfig
            
        Raises:
            ObjectNotFoundError: If configuration not found
            RepositoryError: If database operation fails
        """
        self.logger.debug(f"Updating runtime status for config {config_id} to: {'running' if is_running else 'stopped'}")
        
        # Repository raises ObjectNotFoundError if not found
        config = self.config_repo.update_runtime_status(config_id, is_running)
        
        self.logger.info(f"Updated runtime status for config '{config.name}' to: {'running' if is_running else 'stopped'}")
        return config
    
    def increment_stats(self, config_id: int, emails: int, pdfs: int) -> EmailConfig:
        """
        Increment processing statistics
        
        Args:
            config_id: Configuration ID
            emails: Number of emails to add
            pdfs: Number of PDFs to add
            
        Returns:
            Updated EmailConfig
            
        Raises:
            ObjectNotFoundError: If configuration not found
            ValidationError: If emails or pdfs are negative
            RepositoryError: If database operation fails
        """
        self.logger.debug(f"Incrementing stats for config {config_id}: +{emails} emails, +{pdfs} PDFs")
        
        # Repository validates and raises appropriate exceptions
        config = self.config_repo.increment_stats(config_id, emails, pdfs)
        
        self.logger.debug(f"Updated stats for config '{config.name}': total {config.emails_processed} emails, {config.pdfs_found} PDFs")
        return config
    
    def record_error(self, config_id: int, error_message: str) -> EmailConfig:
        """
        Record processing error
        
        Args:
            config_id: Configuration ID
            error_message: Error message to record
            
        Returns:
            Updated EmailConfig
            
        Raises:
            ObjectNotFoundError: If configuration not found
            ValidationError: If error_message is empty
            RepositoryError: If database operation fails
        """
        self.logger.debug(f"Recording error for config {config_id}: {error_message[:100]}...")
        
        # Repository validates and raises appropriate exceptions
        config = self.config_repo.record_error(config_id, error_message)
        
        self.logger.warning(f"Recorded error for config '{config.name}': {error_message[:100]}...")
        return config
    
    def update_progress(self, config_id: int, emails_processed: int = 0, pdfs_found: int = 0) -> EmailConfig:
        """
        Update progress tracking after email check
        
        Args:
            config_id: Configuration ID
            emails_processed: Number of new emails processed
            pdfs_found: Number of new PDFs found
            
        Returns:
            Updated EmailConfig
            
        Raises:
            ObjectNotFoundError: If configuration not found
            RepositoryError: If database operation fails
        """
        self.logger.debug(f"Updating progress for config {config_id}: +{emails_processed} emails, +{pdfs_found} PDFs")
        
        # Repository handles progress tracking update
        config = self.config_repo.update_progress(config_id, emails_processed, pdfs_found)
        
        self.logger.debug(f"Updated progress for config '{config.name}': total {config.total_emails_processed} emails, {config.total_pdfs_found} PDFs")
        return config