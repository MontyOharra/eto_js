"""
Email Configuration Service
Outward-facing service for managing email configuration CRUD and lifecycle
"""
import logging
from datetime import datetime, timezone

from shared.database import DatabaseConnectionManager
from shared.database.repositories import EmailConfigRepository
from shared.types.email_configs import EmailConfig, EmailConfigSummary, EmailConfigCreate, EmailConfigUpdate
from shared.exceptions.service import ObjectNotFoundError, ConflictError, ServiceError

from features.email_ingestion import EmailIngestionService

logger = logging.getLogger(__name__)


class EmailConfigService:
    """
    Email configuration management service.

    Handles CRUD operations and lifecycle management for email configurations.
    Delegates activation/deactivation to EmailIngestionService for listener management.
    """

    connection_manager: DatabaseConnectionManager
    config_repository: EmailConfigRepository

    def __init__(
        self,
        connection_manager: DatabaseConnectionManager,
        ingestion_service: 'EmailIngestionService'  # Type hint as string to avoid circular import
    ) -> None:
        """
        Initialize email config service

        Args:
            connection_manager: Database connection manager
            ingestion_service: Email ingestion service for starting/stopping monitoring
        """
        self.connection_manager = connection_manager
        self.ingestion_service = ingestion_service
        self.config_repository = EmailConfigRepository(connection_manager=connection_manager)

    def list_configs_summary(
        self,
        order_by: str = "name",
        desc: bool = False
    ) -> list[EmailConfigSummary]:
        """
        List all email configurations with summary information.

        Args:
            order_by: Field to sort by ("name", "is_active", "last_check_time")
            desc: Sort descending if True

        Returns:
            List of EmailConfigSummary dataclasses
        """
        return self.config_repository.get_all_summaries(order_by, desc)

    def get_config(self, config_id: int) -> EmailConfig:
        """
        Get email configuration by ID.

        Args:
            config_id: Configuration ID

        Returns:
            EmailConfig dataclass or None if not found
        """
        config = self.config_repository.get_by_id(config_id)

        if not config:
            raise ObjectNotFoundError(f"Configuration {config_id} not found")

        return config

    def create_config(self, config_data: EmailConfigCreate) -> EmailConfig:
        """
        Create new email configuration.

        Config starts as inactive (is_active=False).
        No connection validation on creation - user must activate to start monitoring.

        Args:
            config_data: EmailConfigCreate dataclass with configuration data

        Returns:
            Created EmailConfig dataclass
        """
        return self.config_repository.create(config_data)

    def update_config(
        self,
        config_id: int,
        config_update: EmailConfigUpdate
    ) -> EmailConfig:
        """
        Update email configuration.

        Validation:
        - Config must exist (raises ObjectNotFoundError)
        - Config must be inactive (raises ConflictError if active)

        Args:
            config_id: Configuration ID
            config_update: EmailConfigUpdate dataclass with fields to update

        Returns:
            Updated EmailConfig dataclass

        Raises:
            ObjectNotFoundError: If config not found
            ConflictError: If config is active (cannot update active config)
        """
        # Get config to validate
        config = self.config_repository.get_by_id(config_id)
        if not config:
            raise ObjectNotFoundError(f"Configuration {config_id} not found")

        # Business validation - cannot update active config (state conflict)
        if config.is_active:
            raise ConflictError(
                "Cannot update active configuration. Deactivate first."
            )

        # Perform update
        return self.config_repository.update(config_id, config_update)

    def delete_config(self, config_id: int) -> EmailConfig:
        """
        Delete email configuration.

        Validation:
        - Config must exist (raises ObjectNotFoundError)
        - If active, automatically deactivates first

        Args:
            config_id: Configuration ID

        Returns:
            EmailConfig dataclass of the deleted configuration

        Raises:
            ObjectNotFoundError: If config not found
            ServiceError: If failed to stop monitoring
        """
        # Get config to validate
        config = self.config_repository.get_by_id(config_id)
        if not config:
            raise ObjectNotFoundError(f"Configuration {config_id} not found")

        # If active, deactivate first
        if config.is_active:
            raise ConflictError("Cannot deactivate active configuration. Deactivate first.")
 

        # Delete config
        config = self.config_repository.delete(config_id)

        logger.info(f"Deleted configuration {config_id}")
        return config

    def activate_config(self, config_id: int) -> EmailConfig:
        """
        Activate email configuration (starts email monitoring).

        Process:
        1. Get config from repository
        2. Validate config exists and is inactive
        3. Delegate to EmailIngestionService to start listener
        4. Update config in DB (is_active=True, activated_at=now)
        5. Return updated config

        Args:
            config_id: Configuration ID

        Returns:
            Updated EmailConfig dataclass with is_active=True

        Raises:
            ObjectNotFoundError: If config not found
            ConflictError: If already active
            ServiceError: If activation fails (infrastructure failure)
        """
        try:
            # Get config
            config = self.config_repository.get_by_id(config_id)
            if not config:
                raise ObjectNotFoundError(f"Configuration {config_id} not found")

            # Validate not already active (state conflict)
            if config.is_active:
                raise ConflictError("Configuration is already active")

            # Start monitoring via ingestion service (infrastructure operation)
            listener_status = self.ingestion_service.start_monitoring(config)

            # Update DB status
            updated_config = self.config_repository.update(
                config_id,
                EmailConfigUpdate(
                    is_active=True,
                    activated_at=datetime.now(timezone.utc)
                )
            )

            logger.info(f"Activated configuration {config_id}")
            return updated_config

        except ObjectNotFoundError:
            # Preserve 404 errors
            raise

        except ConflictError:
            # Preserve 409 errors
            raise

        except Exception as e:
            # Wrap infrastructure failures as 500
            logger.error(f"Failed to activate config {config_id}: {e}", exc_info=True)
            raise ServiceError(f"Failed to start email monitoring: {str(e)}") from e

    def deactivate_config(self, config_id: int) -> EmailConfig:
        """
        Deactivate email configuration (stops email monitoring).

        Process:
        1. Get config from repository
        2. Validate config exists and is active
        3. Delegate to EmailIngestionService to stop listener
        4. Update config in DB (is_active=False)
        5. Return updated config

        Args:
            config_id: Configuration ID

        Returns:
            Updated EmailConfig dataclass with is_active=False

        Raises:
            ObjectNotFoundError: If config not found
            ConflictError: If not active
            ServiceError: If deactivation fails (infrastructure failure)
        """
        try:
            # Get config
            config = self.config_repository.get_by_id(config_id)
            if not config:
                raise ObjectNotFoundError(f"Configuration {config_id} not found")

            # Validate is active (state conflict if not)
            if not config.is_active:
                raise ConflictError("Configuration is not active")

            # Stop monitoring via ingestion service (infrastructure operation)
            self.ingestion_service.stop_monitoring(config_id)

            # Update DB status
            updated_config = self.config_repository.update(
                config_id,
                EmailConfigUpdate(is_active=False)
            )

            logger.info(f"Deactivated configuration {config_id}")
            return updated_config

        except ObjectNotFoundError:
            # Preserve 404 errors
            raise

        except ConflictError:
            # Preserve 409 errors
            raise

        except Exception as e:
            # Wrap infrastructure failures as 500
            logger.error(f"Failed to deactivate config {config_id}: {e}", exc_info=True)
            raise ServiceError(f"Failed to stop email monitoring: {str(e)}") from e
