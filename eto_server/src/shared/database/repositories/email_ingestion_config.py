"""
Email Ingestion Config Repository
Data access layer for EmailIngestionConfig model operations with Pydantic typing
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.exc import SQLAlchemyError

from shared.database.repositories import BaseRepository
from shared.exceptions import RepositoryError, ObjectNotFoundError, ValidationError
from shared.database.models import EmailIngestionConfigModel
from shared.models.email_config import EmailConfig, EmailConfigCreate, EmailConfigUpdate

logger = logging.getLogger(__name__)


class EmailIngestionConfigRepository(BaseRepository[EmailIngestionConfigModel]):
    """Repository for email ingestion configuration operations with Pydantic models"""
    
    @property
    def model_class(self):
        return EmailIngestionConfigModel
    
    # ========== CRUD Operations with Pydantic Types ==========
    
    def create(self, config_create: EmailConfigCreate) -> EmailConfig:
        """
        Create new email configuration from Pydantic model
        
        Args:
            config_create: EmailConfigCreate model with configuration data
            
        Returns:
            Created EmailConfig domain model
        """
        try:
            with self.connection_manager.session_scope() as session:
                # Convert to database format with JSON serialization
                data = config_create.model_dump_for_db()
                
                # Create model instance
                model = self.model_class(**data)
                session.add(model)
                session.flush()  # Get ID before commit
                
                logger.debug(f"Created email configuration: {model.name}")
                
                # Return domain model
                return EmailConfig.from_db_model(model)
                
        except SQLAlchemyError as e:
            logger.error(f"Error creating email configuration: {e}")
            raise RepositoryError(f"Failed to create configuration: {e}") from e
    
    def update(self, config_id: int, config_update: EmailConfigUpdate) -> Optional[EmailConfig]:
        """
        Update existing configuration from Pydantic update model
        
        Args:
            config_id: Configuration ID to update
            config_update: EmailConfigUpdate model with fields to update
            
        Returns:
            Updated EmailConfig or None if not found
        """
        try:
            with self.connection_manager.session_scope() as session:
                model = session.get(self.model_class, config_id)
                
                if not model:
                    return None
                
                # Get update dict with JSON serialization for modified fields only
                updates = config_update.model_dump_for_db()
                
                # Apply updates
                for key, value in updates.items():
                    setattr(model, key, value)
                
                # Timestamp updated by onupdate=func.now() in model
                
                logger.debug(f"Updated email configuration: {model.name}")
                
                # Return updated domain model
                return EmailConfig.from_db_model(model)
                
        except SQLAlchemyError as e:
            logger.error(f"Error updating config {config_id}: {e}")
            raise RepositoryError(f"Failed to update config: {e}") from e
    
    def get_by_id(self, config_id: int) -> Optional[EmailConfig]:
        """
        Get configuration by ID
        
        Args:
            config_id: Configuration ID
            
        Returns:
            EmailConfig domain model or None if not found
        """
        try:
            with self.connection_manager.session_scope() as session:
                model = session.get(self.model_class, config_id)
                
                if model:
                    logger.debug(f"Retrieved email configuration: {model.name}")
                    return EmailConfig.from_db_model(model)
                return None
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting config {config_id}: {e}")
            raise RepositoryError(f"Failed to get config: {e}") from e
    
    def get_all(self, order_by: str = 'created_at', desc: bool = False) -> List[EmailConfig]:
        """
        Get all configurations with sorting options
        
        Args:
            order_by: Field to sort by (created_at, updated_at, name, is_active, last_used_at, emails_processed)
            desc: Sort in descending order
            
        Returns:
            List of EmailConfig domain models
        """
        try:
            with self.connection_manager.session_scope() as session:
                query = session.query(self.model_class)
                
                # Apply ordering
                if hasattr(self.model_class, order_by):
                    order_column = getattr(self.model_class, order_by)
                    if desc:
                        query = query.order_by(order_column.desc())
                    else:
                        query = query.order_by(order_column.asc())
                else:
                    # Default fallback to created_at descending
                    logger.warning(f"Invalid order_by field: {order_by}, using created_at")
                    query = query.order_by(self.model_class.created_at.desc())
                
                models = query.all()
                
                logger.debug(f"Retrieved {len(models)} email configurations")
                return [EmailConfig.from_db_model(model) for model in models]
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting all configurations: {e}")
            raise RepositoryError(f"Failed to get all configurations: {e}") from e
    
    def delete(self, config_id: int) -> EmailConfig:
        """
        Delete configuration by ID
        
        Args:
            config_id: Configuration ID to delete
            
        Returns:
            Deleted EmailConfig domain model
            
        Raises:
            ObjectNotFoundError: If configuration not found
            ValidationError: If configuration is active
        """
        try:
            with self.connection_manager.session_scope() as session:
                config = session.get(self.model_class, config_id)
                
                if not config:
                    raise ObjectNotFoundError('EmailConfig', config_id)
                
                # Check if active
                if getattr(config, 'is_active'):
                    raise ValidationError(f"Cannot delete active configuration {config_id}. Please deactivate it first.")
                
                # Convert to domain model before deletion
                deleted_config = EmailConfig.from_db_model(config)
                
                config_name = getattr(config, 'name')
                session.delete(config)
                
                logger.debug(f"Deleted email configuration: {config_name}")
                return deleted_config
                
        except (ObjectNotFoundError, ValidationError):
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error deleting config {config_id}: {e}")
            raise RepositoryError(f"Failed to delete config: {e}") from e
    
    # ========== Business Operations ==========
    
    def activate(self, config_id: int) -> EmailConfig:
        """
        Activate specific configuration and deactivate all others
        
        Args:
            config_id: Configuration ID to activate
            
        Returns:
            Activated EmailConfig
            
        Raises:
            ObjectNotFoundError: If configuration not found
        """
        try:
            with self.connection_manager.session_scope() as session:
                current_time = datetime.now(timezone.utc)
                
                # Check target exists
                target_config = session.get(self.model_class, config_id)
                if not target_config:
                    raise ObjectNotFoundError('EmailConfig', config_id)
                
                # Deactivate all configs first
                session.query(self.model_class).update({
                    'is_active': False,
                    'is_running': False,
                    'updated_at': current_time
                })
                
                # Activate the target config
                setattr(target_config, 'is_active', True)
                setattr(target_config, 'is_running', False)  # Will be set to True when service starts
                
                logger.debug(f"Activated email configuration: {target_config.name}")
                
                return EmailConfig.from_db_model(target_config)
            
        except SQLAlchemyError as e:
            logger.error(f"Error activating config {config_id}: {e}")
            raise RepositoryError(f"Failed to activate configuration: {e}") from e
    
    def deactivate(self, config_id: int) -> EmailConfig:
        """
        Deactivate specific configuration
        
        Args:
            config_id: Configuration ID to deactivate
            
        Returns:
            Deactivated EmailConfig
            
        Raises:
            ObjectNotFoundError: If configuration not found
        """
        try:
            with self.connection_manager.session_scope() as session:
                config = session.get(self.model_class, config_id)
                
                if not config:
                    raise ObjectNotFoundError('EmailConfig', config_id)
                
                # Deactivate the config
                setattr(config, 'is_active', False)
                setattr(config, 'is_running', False)
                # updated_at handled by onupdate=func.now() in model
                
                logger.debug(f"Deactivated email configuration: {config.name}")
                
                return EmailConfig.from_db_model(config)
            
        except ObjectNotFoundError:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error deactivating config {config_id}: {e}")
            raise RepositoryError(f"Failed to deactivate configuration: {e}") from e
    
    def get_active(self) -> Optional[EmailConfig]:
        """
        Get the currently active configuration
        
        Returns:
            Active EmailConfig or None if no active config
        """
        try:
            with self.connection_manager.session_scope() as session:
                config = session.query(self.model_class).filter(
                    self.model_class.is_active == True
                ).first()
                
                if config:
                    logger.debug(f"Retrieved active email configuration: {config.name}")
                    return EmailConfig.from_db_model(config)
                  
                return None
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting active configuration: {e}")
            raise RepositoryError(f"Failed to get active configuration: {e}") from e
    
    # ========== Convenience Query Methods ==========
    
    def get_all_active_first(self) -> List[EmailConfig]:
        """
        Get all configs with business-specific ordering: active first, then by recency
        Useful for dropdown menus and default listings
        
        Returns:
            List of EmailConfig domain models
        """
        try:
            with self.connection_manager.session_scope() as session:
                models = session.query(self.model_class).order_by(
                    self.model_class.is_active.desc(),
                    self.model_class.updated_at.desc()
                ).all()
                
                logger.debug(f"Retrieved {len(models)} email configurations (active first)")
                return [EmailConfig.from_db_model(model) for model in models]
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting configs active first: {e}")
            raise RepositoryError(f"Failed to get configurations: {e}") from e
    
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
        """
        try:
            with self.connection_manager.session_scope() as session:
                model = session.get(self.model_class, config_id)
                
                if not model:
                    raise ObjectNotFoundError('EmailConfig', config_id)
                
                current_time = datetime.now(timezone.utc)
                setattr(model, 'is_running', is_running)
                # updated_at handled by onupdate=func.now() in model
                
                if is_running:
                    setattr(model, 'last_used_at', current_time)
                
                status_text = "running" if is_running else "stopped"
                logger.debug(f"Updated configuration {model.name} runtime status to: {status_text}")
                
                return EmailConfig.from_db_model(model)
                
        except SQLAlchemyError as e:
            logger.error(f"Error updating runtime status for config {config_id}: {e}")
            raise RepositoryError(f"Failed to update runtime status: {e}") from e
    
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
        """
        if emails < 0 or pdfs < 0:
            raise ValidationError("emails and pdfs must be non-negative")
        
        try:
            with self.connection_manager.session_scope() as session:
                model = session.get(self.model_class, config_id)
                
                if not model:
                    raise ObjectNotFoundError('EmailConfig', config_id)
                
                # Calculate new statistics
                current_emails = getattr(model, 'emails_processed', 0) or 0
                current_pdfs = getattr(model, 'pdfs_found', 0) or 0
                
                current_time = datetime.now(timezone.utc)
                setattr(model, 'emails_processed', current_emails + emails)
                setattr(model, 'pdfs_found', current_pdfs + pdfs)
                setattr(model, 'last_used_at', current_time)
                # updated_at handled by onupdate=func.now() in model
                
                logger.debug(f"Updated stats for config {model.name}: +{emails} emails, +{pdfs} PDFs")
                
                return EmailConfig.from_db_model(model)
                
        except SQLAlchemyError as e:
            logger.error(f"Error updating stats for config {config_id}: {e}")
            raise RepositoryError(f"Failed to update processing stats: {e}") from e
    
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
        """
        if not error_message:
            raise ValidationError("error_message cannot be empty")
        
        try:
            with self.connection_manager.session_scope() as session:
                model = session.get(self.model_class, config_id)
                
                if not model:
                    raise ObjectNotFoundError('EmailConfig', config_id)
                
                current_time = datetime.now(timezone.utc)
                setattr(model, 'last_error_message', error_message[:500])  # Truncate if too long
                setattr(model, 'last_error_at', current_time)
                # updated_at handled by onupdate=func.now() in model
                
                logger.debug(f"Recorded error for configuration {model.name}: {error_message}")
                
                return EmailConfig.from_db_model(model)
                
        except SQLAlchemyError as e:
            logger.error(f"Error recording error for config {config_id}: {e}")
            raise RepositoryError(f"Failed to record error: {e}") from e