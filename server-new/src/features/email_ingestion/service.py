"""
Email Ingestion Service
Service layer for email configuration management and monitoring
Uses registry-based integrations with dataclass types
"""
import logging
import threading
import time
from typing import Dict, Optional, List, Any
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import partial

# Import dataclass types from new type system
from shared.types.email_integrations import (
    EmailAccount,
    EmailFolder,
    EmailMessage,
    ConnectionTestResult,
)

# Import Pydantic types for email config database operations
from shared.types import (
    EmailConfig,
    EmailConfigCreate,
    EmailConfigUpdate,
    EmailConfigSummary,
)

from shared.database.repositories.email import EmailRepository
from shared.utils import DateTimeUtils
from shared.database.repositories.email_config import EmailConfigRepository
from shared.exceptions import ServiceError, ObjectNotFoundError
from shared.services import ServiceContainer

# Import new registry-based integration system
from features.email_ingestion.integrations import IntegrationRegistry
from features.email_ingestion.integrations.base_integration import BaseEmailIntegration
from features.email_ingestion.utils.email_listener_thread import EmailListenerThread

# TYPE_CHECKING imports for forward references
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from features.pdf_processing.service import PdfProcessingService
    from features.eto_processing.service import EtoProcessingService
    from shared.database.connection import DatabaseConnectionManager


logger = logging.getLogger(__name__)


@dataclass
class ListenerStatus:
    """Status information for an active listener"""
    config_id: int
    email_address: str
    folder_name: str
    is_active: bool
    is_running: bool
    start_time: Optional[datetime]
    last_check_time: Optional[datetime]
    error_count: int
    emails_processed: int
    pdfs_found: int


class EmailIngestionService:
    """
    Service for email ingestion functionality.
    Manages configurations, integrations, listeners, and email processing.
    Uses registry-based integrations with dataclass types.
    """

    def __init__(self,
                 connection_manager: 'DatabaseConnectionManager' = None,
                 pdf_service: 'PdfProcessingService' = None,
                 eto_service: 'EtoProcessingService' = None):
        """
        Initialize email ingestion service

        Args:
            connection_manager: Database connection manager (optional for now)
            pdf_service: PDF processing service instance (optional for now)
            eto_service: ETO processing service instance (optional for now)

        Note: Dependencies are optional during development.
        They will be required when implementing activation/processing methods.
        """
        self.connection_manager = connection_manager
        self.pdf_service = pdf_service
        self.eto_service = eto_service

        # Initialize repositories if connection manager provided
        if connection_manager:
            self.config_repository: EmailConfigRepository = EmailConfigRepository(connection_manager)
            self.email_repository: EmailRepository = EmailRepository(connection_manager)
        else:
            self.config_repository = None
            self.email_repository = None

        # Active integrations and listeners
        # Will be populated when we implement activate_config()
        self.active_integrations: Dict[int, BaseEmailIntegration] = {}
        self.active_listeners: Dict[int, EmailListenerThread] = {}

        # Thread safety for managing active integrations/listeners
        self.lock = threading.RLock()

        logger.info("EmailIngestionService initialized")
    
    # ========== Account/Folder Discovery ==========

    async def discover_email_accounts(self, provider_type: str = "outlook_com") -> list[EmailAccount]:
        """
        Discover available email accounts for the specified provider.

        Creates a temporary integration instance to query the email provider
        for available accounts. Does not establish a persistent connection.

        Args:
            provider_type: Email provider to query (default: "outlook_com")
                          Available providers can be checked via:
                          IntegrationRegistry.get_available_providers()

        Returns:
            List of EmailAccount dataclasses with account information

        Raises:
            ValueError: If provider_type is not supported
            ServiceError: If account discovery fails

        Example:
            >>> service = EmailIngestionService()
            >>> accounts = await service.discover_email_accounts("outlook_com")
            >>> for account in accounts:
            ...     print(f"{account.email_address} - {account.display_name}")
        """
        try:
            logger.info(f"Discovering email accounts for provider: {provider_type}")

            # Validate provider is supported
            if not IntegrationRegistry.is_supported(provider_type):
                available = IntegrationRegistry.get_available_providers()
                raise ValueError(
                    f"Provider '{provider_type}' is not supported. "
                    f"Available providers: {', '.join(available)}"
                )

            # Create temporary integration for discovery
            # No specific email_address needed for account discovery
            integration = IntegrationRegistry.create(
                provider_type=provider_type,
                email_address=None,
                folder_name="Inbox"  # Default, not used for discovery
            )

            logger.debug(f"Created temporary integration for {provider_type}")

            # Discover accounts
            # For Outlook COM, this doesn't require connection (reads local config)
            # For cloud providers (Gmail, Graph), this might require auth
            accounts = integration.discover_accounts()

            logger.info(
                f"Successfully discovered {len(accounts)} account(s) "
                f"for provider '{provider_type}'"
            )

            # Log discovered accounts (without sensitive data)
            for i, account in enumerate(accounts, 1):
                logger.debug(
                    f"  Account {i}: {account.email_address} "
                    f"({account.display_name}) - Default: {account.is_default}"
                )

            return accounts

        except ValueError:
            # Re-raise validation errors as-is
            raise

        except Exception as e:
            logger.error(
                f"Error discovering email accounts for provider '{provider_type}': {e}",
                exc_info=True
            )
            raise ServiceError(
                f"Failed to discover email accounts: {str(e)}"
            ) from e

    async def discover_folders(
        self,
        email_address: str,
        provider_type: str = "outlook_com"
    ) -> list[EmailFolder]:
        """
        Discover available folders for a specific email account.

        Creates a temporary integration instance, connects to the email account,
        retrieves folder information, and then disconnects. This is a one-time
        operation and does not maintain a persistent connection.

        Args:
            email_address: Email address to discover folders for
            provider_type: Email provider to use (default: "outlook_com")

        Returns:
            List of EmailFolder dataclasses with folder information
            Each folder includes: name, full_path, message_count, folder_type, etc.

        Raises:
            ValueError: If provider_type is not supported or email_address is invalid
            ConnectionError: If unable to connect to the email account
            ServiceError: If folder discovery fails

        Example:
            >>> service = EmailIngestionService()
            >>> folders = await service.discover_folders("user@example.com")
            >>> for folder in folders:
            ...     print(f"{folder.name} ({folder.message_count} messages)")
        """
        try:
            # Validate inputs
            if not email_address:
                raise ValueError("email_address is required")

            if not IntegrationRegistry.is_supported(provider_type):
                available = IntegrationRegistry.get_available_providers()
                raise ValueError(
                    f"Provider '{provider_type}' is not supported. "
                    f"Available providers: {', '.join(available)}"
                )

            logger.info(
                f"Discovering folders for '{email_address}' "
                f"using provider '{provider_type}'"
            )

            # Create temporary integration for this specific account
            integration = IntegrationRegistry.create(
                provider_type=provider_type,
                email_address=email_address,
                folder_name="Inbox"  # Default folder, not used for discovery
            )

            logger.debug(
                f"Created temporary integration for {email_address}"
            )

            # Connect to email provider
            # This is required for folder discovery (need to access account structure)
            if not integration.connect(email_address):
                raise ConnectionError(
                    f"Failed to connect to email account '{email_address}'. "
                    f"Please verify the account exists and is accessible."
                )

            logger.debug(f"Successfully connected to {email_address}")

            try:
                # Discover folders while connected
                folders = integration.discover_folders(email_address)

                logger.info(
                    f"Successfully discovered {len(folders)} folder(s) "
                    f"for '{email_address}'"
                )

                # Log discovered folders
                for folder in folders:
                    logger.debug(
                        f"  Folder: {folder.full_path} "
                        f"({folder.message_count} messages, "
                        f"type: {folder.folder_type or 'custom'})"
                    )

                return folders

            finally:
                # Always disconnect, even if discovery fails
                try:
                    integration.disconnect()
                    logger.debug(f"Disconnected from {email_address}")
                except Exception as disconnect_error:
                    logger.warning(
                        f"Error disconnecting from {email_address}: {disconnect_error}"
                    )

        except ValueError:
            # Re-raise validation errors as-is
            raise

        except ConnectionError:
            # Re-raise connection errors as-is
            raise

        except Exception as e:
            logger.error(
                f"Error discovering folders for '{email_address}': {e}",
                exc_info=True
            )
            raise ServiceError(
                f"Failed to discover folders: {str(e)}"
            ) from e

    async def validate_email_config(
        self,
        email_address: str,
        folder_name: str,
        provider_type: str = "outlook_com"
    ) -> ConnectionTestResult:
        """
        Validate an email configuration before creating it.

        Creates a temporary integration and tests if:
        1. The email account exists and is accessible
        2. The specified folder exists
        3. The folder can be accessed

        This is useful for validating user input before saving a config to the database.

        Args:
            email_address: Email address to validate
            folder_name: Folder name to validate
            provider_type: Email provider to use (default: "outlook_com")

        Returns:
            ConnectionTestResult dataclass with:
            - success: bool (True if validation passed)
            - message: Optional success message
            - error: Optional error message (if success=False)
            - details: Optional dict with additional info

        Example:
            >>> service = EmailIngestionService()
            >>> result = await service.validate_email_config(
            ...     email_address="user@example.com",
            ...     folder_name="Inbox"
            ... )
            >>> if result.success:
            ...     print("Config is valid!")
            >>> else:
            ...     print(f"Validation failed: {result.error}")
        """
        try:
            # Validate inputs
            if not email_address:
                return ConnectionTestResult(
                    success=False,
                    error="email_address is required"
                )

            if not folder_name:
                return ConnectionTestResult(
                    success=False,
                    error="folder_name is required"
                )

            if not IntegrationRegistry.is_supported(provider_type):
                available = IntegrationRegistry.get_available_providers()
                return ConnectionTestResult(
                    success=False,
                    error=(
                        f"Provider '{provider_type}' is not supported. "
                        f"Available providers: {', '.join(available)}"
                    )
                )

            logger.info(
                f"Validating email config: {email_address}/{folder_name} "
                f"(provider: {provider_type})"
            )

            # Create temporary integration
            integration = IntegrationRegistry.create(
                provider_type=provider_type,
                email_address=email_address,
                folder_name=folder_name
            )

            logger.debug(f"Created temporary integration for validation")

            # Test connection
            # This will verify account exists and folder is accessible
            result = integration.test_connection()

            if result.success:
                logger.info(
                    f"Email config validation successful: "
                    f"{email_address}/{folder_name}"
                )
            else:
                logger.warning(
                    f"Email config validation failed: {result.error}"
                )

            return result

        except ValueError as e:
            logger.error(f"Validation error: {e}")
            return ConnectionTestResult(
                success=False,
                error=str(e)
            )

        except Exception as e:
            logger.error(
                f"Unexpected error during validation: {e}",
                exc_info=True
            )
            return ConnectionTestResult(
                success=False,
                error=f"Validation failed: {str(e)}"
            )

    # ========== Helper Methods ==========

    def get_available_providers(self) -> list[str]:
        """
        Get list of all available email providers.

        Returns:
            List of provider type strings (e.g., ["outlook_com", "gmail_api"])

        Example:
            >>> service = EmailIngestionService()
            >>> providers = service.get_available_providers()
            >>> print(f"Available providers: {', '.join(providers)}")
        """
        return IntegrationRegistry.get_available_providers()

    def get_provider_info(self, provider_type: str) -> Optional[dict]:
        """
        Get metadata about a specific provider.

        Args:
            provider_type: Provider to get info for

        Returns:
            Dictionary with provider metadata (name, description, platforms, etc.)
            or None if provider not found

        Example:
            >>> service = EmailIngestionService()
            >>> info = service.get_provider_info("outlook_com")
            >>> print(f"{info['name']}: {info['description']}")
        """
        return IntegrationRegistry.get_provider_metadata(provider_type)

    def get_all_providers_info(self) -> dict[str, dict]:
        """
        Get metadata for all registered providers.

        Returns:
            Dictionary mapping provider_type to metadata

        Example:
            >>> service = EmailIngestionService()
            >>> all_info = service.get_all_providers_info()
            >>> for provider, info in all_info.items():
            ...     print(f"{provider}: {info.get('name')}")
        """
        return IntegrationRegistry.get_all_provider_info()

    # ========== Configuration CRUD Operations ==========

    async def create_config(self, config_create: 'EmailConfigCreate') -> 'EmailConfig':
        """
        Create a new email configuration.

        Args:
            config_create: EmailConfigCreate Pydantic model with configuration data

        Returns:
            Created EmailConfig Pydantic model

        Raises:
            ValueError: If connection_manager not initialized
            ValidationError: If config validation fails
            ServiceError: If creation fails

        Example:
            >>> from shared.types import EmailConfigCreate, EmailFilterRule
            >>> config_data = EmailConfigCreate(
            ...     name="Personal Email",
            ...     email_address="user@example.com",
            ...     folder_name="Inbox",
            ...     filter_rules=[],
            ...     poll_interval_seconds=30
            ... )
            >>> config = await service.create_config(config_data)
            >>> print(f"Created config {config.id}: {config.name}")
        """
        try:
            # Validate service is properly initialized
            if not self.config_repository:
                raise ValueError(
                    "EmailConfigRepository not initialized. "
                    "Service requires connection_manager to create configurations."
                )

            logger.info(
                f"Creating email configuration: {config_create.name} "
                f"({config_create.email_address}/{config_create.folder_name})"
            )

            # Create via repository
            config = self.config_repository.create(config_create)

            logger.info(
                f"Successfully created email configuration {config.id}: {config.name}"
            )

            return config

        except ValueError:
            # Re-raise validation errors as-is
            raise

        except Exception as e:
            logger.error(
                f"Error creating email configuration: {e}",
                exc_info=True
            )
            raise ServiceError(
                f"Failed to create email configuration: {str(e)}"
            ) from e

    async def get_config(self, config_id: int) -> 'EmailConfig':
        """
        Get email configuration by ID.

        Args:
            config_id: Configuration ID to retrieve

        Returns:
            EmailConfig Pydantic model

        Raises:
            ValueError: If connection_manager not initialized
            ObjectNotFoundError: If configuration not found
            ServiceError: If retrieval fails

        Example:
            >>> config = await service.get_config(1)
            >>> print(f"Config: {config.name} - Active: {config.is_active}")
        """
        try:
            # Validate service is properly initialized
            if not self.config_repository:
                raise ValueError(
                    "EmailConfigRepository not initialized. "
                    "Service requires connection_manager to retrieve configurations."
                )

            logger.debug(f"Retrieving email configuration {config_id}")

            # Get via repository
            config = self.config_repository.get_by_id(config_id)

            if not config:
                raise ObjectNotFoundError('EmailConfig', config_id)

            logger.debug(f"Retrieved email configuration: {config.name}")

            return config

        except (ValueError, ObjectNotFoundError):
            # Re-raise as-is
            raise

        except Exception as e:
            logger.error(
                f"Error retrieving email configuration {config_id}: {e}",
                exc_info=True
            )
            raise ServiceError(
                f"Failed to retrieve email configuration: {str(e)}"
            ) from e

    async def update_config(
        self,
        config_id: int,
        config_update: 'EmailConfigUpdate'
    ) -> 'EmailConfig':
        """
        Update existing email configuration.

        Note: Cannot update name, email_address, or folder_name.
        To change these, create a new configuration.

        Args:
            config_id: Configuration ID to update
            config_update: EmailConfigUpdate Pydantic model with fields to update

        Returns:
            Updated EmailConfig Pydantic model

        Raises:
            ValueError: If connection_manager not initialized or config is active
            ObjectNotFoundError: If configuration not found
            ServiceError: If update fails

        Example:
            >>> from shared.types import EmailConfigUpdate
            >>> updates = EmailConfigUpdate(
            ...     description="Updated description",
            ...     poll_interval_seconds=60
            ... )
            >>> config = await service.update_config(1, updates)
            >>> print(f"Updated config: {config.name}")
        """
        try:
            # Validate service is properly initialized
            if not self.config_repository:
                raise ValueError(
                    "EmailConfigRepository not initialized. "
                    "Service requires connection_manager to update configurations."
                )

            logger.info(f"Updating email configuration {config_id}")

            # Check if config exists and is not active
            existing = self.config_repository.get_by_id(config_id)
            if not existing:
                raise ObjectNotFoundError('EmailConfig', config_id)

            # Prevent updates to active configurations
            # User must deactivate first to avoid runtime conflicts
            if existing.is_active:
                raise ValueError(
                    f"Cannot update active configuration {config_id}. "
                    f"Please deactivate it first."
                )

            # Update via repository
            config = self.config_repository.update(config_id, config_update)

            logger.info(f"Successfully updated email configuration {config_id}")

            return config

        except (ValueError, ObjectNotFoundError):
            # Re-raise as-is
            raise

        except Exception as e:
            logger.error(
                f"Error updating email configuration {config_id}: {e}",
                exc_info=True
            )
            raise ServiceError(
                f"Failed to update email configuration: {str(e)}"
            ) from e

    async def delete_config(self, config_id: int) -> 'EmailConfig':
        """
        Delete email configuration.

        Configuration must be inactive (not active/running) to be deleted.

        Args:
            config_id: Configuration ID to delete

        Returns:
            Deleted EmailConfig Pydantic model

        Raises:
            ValueError: If connection_manager not initialized
            ObjectNotFoundError: If configuration not found
            ValidationError: If configuration is active
            ServiceError: If deletion fails

        Example:
            >>> deleted = await service.delete_config(1)
            >>> print(f"Deleted configuration: {deleted.name}")
        """
        try:
            # Validate service is properly initialized
            if not self.config_repository:
                raise ValueError(
                    "EmailConfigRepository not initialized. "
                    "Service requires connection_manager to delete configurations."
                )

            logger.info(f"Deleting email configuration {config_id}")

            # Delete via repository
            # Repository will check if active and raise ValidationError if so
            deleted_config = self.config_repository.delete(config_id)

            logger.info(
                f"Successfully deleted email configuration {config_id}: {deleted_config.name}"
            )

            return deleted_config

        except (ValueError, ObjectNotFoundError):
            # Re-raise as-is
            raise

        except Exception as e:
            logger.error(
                f"Error deleting email configuration {config_id}: {e}",
                exc_info=True
            )
            raise ServiceError(
                f"Failed to delete email configuration: {str(e)}"
            ) from e

    async def list_configs(
        self,
        order_by: str = 'created_at',
        desc: bool = True
    ) -> list['EmailConfig']:
        """
        List all email configurations with sorting options.

        Args:
            order_by: Field to sort by (created_at, updated_at, name, is_active,
                     last_used_at, emails_processed). Defaults to 'created_at'
            desc: Sort in descending order. Defaults to True

        Returns:
            List of EmailConfig Pydantic models

        Raises:
            ValueError: If connection_manager not initialized
            ServiceError: If listing fails

        Example:
            >>> # Get all configs, most recent first
            >>> configs = await service.list_configs()
            >>> for config in configs:
            ...     status = "Active" if config.is_active else "Inactive"
            ...     print(f"{config.name} - {status}")

            >>> # Get all configs by name, alphabetically
            >>> configs = await service.list_configs(order_by='name', desc=False)
        """
        try:
            # Validate service is properly initialized
            if not self.config_repository:
                raise ValueError(
                    "EmailConfigRepository not initialized. "
                    "Service requires connection_manager to list configurations."
                )

            logger.debug(f"Listing email configurations (order_by={order_by}, desc={desc})")

            # Get all via repository
            configs = self.config_repository.get_all(order_by=order_by, desc=desc)

            logger.debug(f"Retrieved {len(configs)} email configurations")

            return configs

        except ValueError:
            # Re-raise validation errors as-is
            raise

        except Exception as e:
            logger.error(
                f"Error listing email configurations: {e}",
                exc_info=True
            )
            raise ServiceError(
                f"Failed to list email configurations: {str(e)}"
            ) from e

    async def list_configs_summary(self) -> list['EmailConfigSummary']:
        """
        List all configurations with summary information only.

        Returns lighter-weight summary objects suitable for list views.

        Returns:
            List of EmailConfigSummary Pydantic models

        Raises:
            ValueError: If connection_manager not initialized
            ServiceError: If listing fails

        Example:
            >>> summaries = await service.list_configs_summary()
            >>> for summary in summaries:
            ...     print(f"{summary.name}: {summary.emails_processed} emails, "
            ...           f"{summary.pdfs_found} PDFs")
        """
        try:
            # Validate service is properly initialized
            if not self.config_repository:
                raise ValueError(
                    "EmailConfigRepository not initialized. "
                    "Service requires connection_manager to list configurations."
                )

            logger.debug("Listing email configuration summaries")

            # Get summaries via repository
            summaries = self.config_repository.get_all_summaries()

            logger.debug(f"Retrieved {len(summaries)} email configuration summaries")

            return summaries

        except ValueError:
            # Re-raise validation errors as-is
            raise

        except Exception as e:
            logger.error(
                f"Error listing email configuration summaries: {e}",
                exc_info=True
            )
            raise ServiceError(
                f"Failed to list email configuration summaries: {str(e)}"
            ) from e

    # ========== Activation/Deactivation Operations ==========

    async def activate_config(self, config_id: int) -> 'EmailConfig':
        """
        Activate an email configuration and start monitoring.

        This will:
        1. Mark the configuration as active in the database
        2. Create a persistent integration instance
        3. Start an email listener thread for this configuration

        Args:
            config_id: Configuration ID to activate

        Returns:
            Activated EmailConfig Pydantic model

        Raises:
            ValueError: If connection_manager or required services not initialized
            ObjectNotFoundError: If configuration not found
            ConnectionError: If unable to connect to email provider
            ServiceError: If activation fails

        Example:
            >>> config = await service.activate_config(1)
            >>> print(f"Activated: {config.name} - Running: {config.is_running}")
        """
        try:
            # Validate service is properly initialized
            if not self.config_repository:
                raise ValueError(
                    "EmailConfigRepository not initialized. "
                    "Service requires connection_manager to activate configurations."
                )

            # PDF and ETO services are optional for now but will be needed for processing
            # We'll allow activation without them during development
            if not self.pdf_service:
                logger.warning(
                    "PDF processing service not initialized. "
                    "PDFs will be detected but not processed."
                )

            if not self.eto_service:
                logger.warning(
                    "ETO processing service not initialized. "
                    "ETOs will not be processed."
                )

            logger.info(f"Activating email configuration {config_id}")

            # Get configuration
            config = self.config_repository.get_by_id(config_id)
            if not config:
                raise ObjectNotFoundError('EmailConfig', config_id)

            # Check if already active
            if config.is_active:
                logger.warning(f"Configuration {config_id} is already active")
                return config

            # Activate in database with current time
            activation_time = DateTimeUtils.utc_now()
            config = self.config_repository.activate(config_id, activation_time)

            logger.info(
                f"Marked configuration {config_id} as active in database "
                f"(activated_at: {activation_time})"
            )

            # Create persistent integration instance
            # For now, we'll hardcode provider_type to "outlook_com"
            # In the future, this could be stored in the config
            provider_type = "outlook_com"

            try:
                with self.lock:
                    # Create integration instance
                    integration = IntegrationRegistry.create(
                        provider_type=provider_type,
                        email_address=config.email_address,
                        folder_name=config.folder_name
                    )

                    logger.debug(
                        f"Created integration for {config.email_address}/{config.folder_name}"
                    )

                    # Test connection
                    test_result = integration.test_connection()
                    if not test_result.success:
                        # Deactivate in database before raising error
                        self.config_repository.deactivate(config_id)
                        raise ConnectionError(
                            f"Failed to connect to email provider: {test_result.error}"
                        )

                    logger.info(f"Successfully connected to email provider for config {config_id}")

                    # Store integration in active integrations
                    self.active_integrations[config_id] = integration

                    # Create and start listener thread
                    listener = EmailListenerThread(
                        config_id=config_id,
                        email_address=config.email_address,
                        folder_name=config.folder_name,
                        integration=integration,
                        poll_interval_seconds=config.poll_interval_seconds,
                        max_backlog_hours=config.max_backlog_hours,
                        filter_rules=config.filter_rules,
                        on_email_callback=self._process_email,
                        on_error_callback=self._handle_listener_error,
                        config_repository=self.config_repository
                    )

                    # Start the listener thread
                    listener.start()

                    # Store listener
                    self.active_listeners[config_id] = listener

                    # Update runtime status to running
                    config = self.config_repository.update_runtime_status(config_id, True)

                    logger.info(
                        f"Successfully activated configuration {config_id}: {config.name} "
                        f"(listener started)"
                    )

                    return config

            except Exception as integration_error:
                # Clean up on failure
                logger.error(
                    f"Error during integration setup for config {config_id}: {integration_error}",
                    exc_info=True
                )

                # Deactivate in database
                try:
                    self.config_repository.deactivate(config_id)
                    logger.info(f"Deactivated config {config_id} after integration failure")
                except Exception as deactivate_error:
                    logger.error(
                        f"Error deactivating config {config_id} after failure: {deactivate_error}"
                    )

                # Re-raise original error
                raise

        except (ValueError, ObjectNotFoundError, ConnectionError):
            # Re-raise as-is
            raise

        except Exception as e:
            logger.error(
                f"Error activating email configuration {config_id}: {e}",
                exc_info=True
            )
            raise ServiceError(
                f"Failed to activate email configuration: {str(e)}"
            ) from e

    async def deactivate_config(self, config_id: int) -> 'EmailConfig':
        """
        Deactivate an email configuration and stop monitoring.

        This will:
        1. Stop the email listener thread
        2. Disconnect the integration
        3. Mark the configuration as inactive in the database
        4. Clear progress tracking data

        Args:
            config_id: Configuration ID to deactivate

        Returns:
            Deactivated EmailConfig Pydantic model

        Raises:
            ValueError: If connection_manager not initialized
            ObjectNotFoundError: If configuration not found
            ServiceError: If deactivation fails

        Example:
            >>> config = await service.deactivate_config(1)
            >>> print(f"Deactivated: {config.name} - Active: {config.is_active}")
        """
        try:
            # Validate service is properly initialized
            if not self.config_repository:
                raise ValueError(
                    "EmailConfigRepository not initialized. "
                    "Service requires connection_manager to deactivate configurations."
                )

            logger.info(f"Deactivating email configuration {config_id}")

            # Get configuration
            config = self.config_repository.get_by_id(config_id)
            if not config:
                raise ObjectNotFoundError('EmailConfig', config_id)

            # Check if already inactive
            if not config.is_active:
                logger.warning(f"Configuration {config_id} is already inactive")
                return config

            with self.lock:
                # Stop listener thread if exists
                if config_id in self.active_listeners:
                    listener = self.active_listeners[config_id]
                    try:
                        logger.debug(f"Stopping listener for config {config_id}")
                        listener.stop()
                        listener.join(timeout=10)  # Wait up to 10 seconds for clean shutdown

                        if listener.is_alive():
                            logger.warning(
                                f"Listener for config {config_id} did not stop gracefully"
                            )
                    except Exception as listener_error:
                        logger.error(
                            f"Error stopping listener for config {config_id}: {listener_error}"
                        )

                    # Remove from active listeners
                    del self.active_listeners[config_id]

                # Disconnect integration if exists
                if config_id in self.active_integrations:
                    integration = self.active_integrations[config_id]
                    try:
                        logger.debug(f"Disconnecting integration for config {config_id}")
                        integration.disconnect()
                    except Exception as disconnect_error:
                        logger.error(
                            f"Error disconnecting integration for config {config_id}: {disconnect_error}"
                        )

                    # Remove from active integrations
                    del self.active_integrations[config_id]

            # Deactivate in database
            config = self.config_repository.deactivate(config_id)

            logger.info(
                f"Successfully deactivated configuration {config_id}: {config.name} "
                f"(listener stopped, integration disconnected)"
            )

            return config

        except (ValueError, ObjectNotFoundError):
            # Re-raise as-is
            raise

        except Exception as e:
            logger.error(
                f"Error deactivating email configuration {config_id}: {e}",
                exc_info=True
            )
            raise ServiceError(
                f"Failed to deactivate email configuration: {str(e)}"
            ) from e

    async def get_active_configs(self) -> list['EmailConfig']:
        """
        Get all currently active email configurations.

        Returns:
            List of active EmailConfig Pydantic models

        Raises:
            ValueError: If connection_manager not initialized
            ServiceError: If retrieval fails

        Example:
            >>> active_configs = await service.get_active_configs()
            >>> print(f"Active configurations: {len(active_configs)}")
            >>> for config in active_configs:
            ...     print(f"  - {config.name} ({config.email_address})")
        """
        try:
            # Validate service is properly initialized
            if not self.config_repository:
                raise ValueError(
                    "EmailConfigRepository not initialized. "
                    "Service requires connection_manager to retrieve configurations."
                )

            logger.debug("Retrieving active email configurations")

            # Get active configs via repository
            configs = self.config_repository.get_active_configs()

            logger.debug(f"Retrieved {len(configs)} active email configurations")

            return configs

        except ValueError:
            # Re-raise validation errors as-is
            raise

        except Exception as e:
            logger.error(
                f"Error retrieving active email configurations: {e}",
                exc_info=True
            )
            raise ServiceError(
                f"Failed to retrieve active email configurations: {str(e)}"
            ) from e

    def get_listener_status(self, config_id: int) -> Optional[ListenerStatus]:
        """
        Get runtime status of an active listener.

        Args:
            config_id: Configuration ID

        Returns:
            ListenerStatus dataclass if listener is active, None otherwise

        Example:
            >>> status = service.get_listener_status(1)
            >>> if status:
            ...     print(f"Listener for {status.email_address}: "
            ...           f"Processed {status.emails_processed} emails")
        """
        with self.lock:
            listener = self.active_listeners.get(config_id)
            if not listener:
                return None

            return listener.get_status()

    def get_all_listener_statuses(self) -> list[ListenerStatus]:
        """
        Get runtime status of all active listeners.

        Returns:
            List of ListenerStatus dataclasses for all active listeners

        Example:
            >>> statuses = service.get_all_listener_statuses()
            >>> for status in statuses:
            ...     print(f"{status.email_address}: {status.emails_processed} emails, "
            ...           f"{status.pdfs_found} PDFs")
        """
        statuses = []
        with self.lock:
            for config_id, listener in self.active_listeners.items():
                try:
                    status = listener.get_status()
                    statuses.append(status)
                except Exception as e:
                    logger.warning(
                        f"Error getting status for listener {config_id}: {e}"
                    )

        return statuses

    # ========== Helper/Callback Methods ==========

    def _process_email(
        self,
        config_id: int,
        email_message: EmailMessage
    ) -> None:
        """
        Callback for processing a single email.

        This is called by the listener thread when a new email is found.

        Args:
            config_id: Configuration ID that found the email
            email_message: EmailMessage dataclass with email data and cached attachments
        """
        try:
            logger.info(
                f"Processing email from config {config_id}: "
                f"{email_message.subject} (from {email_message.sender_email})"
            )

            # TODO: Implement email processing logic
            # 1. Filter email based on config.filter_rules
            # 2. Extract PDF attachments from cached_attachments
            # 3. Pass PDFs to PDF processing service
            # 4. Update config statistics

            logger.debug(f"Email processing not yet implemented (placeholder)")

        except Exception as e:
            logger.error(
                f"Error processing email from config {config_id}: {e}",
                exc_info=True
            )

    def _handle_listener_error(
        self,
        config_id: int,
        error_message: str
    ) -> None:
        """
        Callback for handling listener errors.

        This is called by the listener thread when an error occurs.

        Args:
            config_id: Configuration ID that encountered the error
            error_message: Error message
        """
        try:
            logger.error(f"Listener error for config {config_id}: {error_message}")

            # Record error in database
            if self.config_repository:
                self.config_repository.record_error(config_id, error_message)

        except Exception as e:
            logger.error(
                f"Error recording listener error for config {config_id}: {e}",
                exc_info=True
            )