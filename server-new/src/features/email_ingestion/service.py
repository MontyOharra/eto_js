"""
Email Ingestion Service
Service layer for email configuration management and monitoring
Uses registry-based integrations with dataclass types
"""
import logging
import threading
from typing import TYPE_CHECKING
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import partial

# Import dataclass types from new type system
from shared.types.email_integrations import (
    EmailAccount,
    EmailFolder,
    EmailMessage,
    EmailAttachment,
    ConnectionTestResult,
)
from shared.types.email import EmailCreate
from shared.types.email_configs import EmailConfig

from shared.database.repositories.email import EmailRepository
from shared.database.repositories.email_config import EmailConfigRepository
from shared.exceptions import ServiceError, ValidationError

# Import new registry-based integration system
from features.email_ingestion.integrations import IntegrationRegistry
from features.email_ingestion.integrations.base_integration import BaseEmailIntegration
from features.email_ingestion.utils.email_listener_thread import EmailListenerThread

# TYPE_CHECKING imports for forward references
if TYPE_CHECKING:
    from features.pdf_files.service import PdfFilesService
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
    start_time: datetime | None
    last_check_time: datetime | None
    error_count: int
    emails_processed: int
    pdfs_found: int


class EmailIngestionService:
    """
    Service for email ingestion functionality.
    Manages configurations, integrations, listeners, and email processing.
    Uses registry-based integrations with dataclass types.
    """

    def __init__(
        self,
        connection_manager: 'DatabaseConnectionManager',
        pdf_service: 'PdfFilesService',
        eto_service: 'EtoProcessingService'
    ):
        """
        Initialize email ingestion service

        Args:
            connection_manager: Database connection manager
            pdf_service: PDF processing service instance
            eto_service: ETO processing service instance
        """
        self.connection_manager = connection_manager
        self.pdf_service = pdf_service
        self.eto_service = eto_service

        self.config_repository = EmailConfigRepository(connection_manager=connection_manager)
        self.email_repository = EmailRepository(connection_manager=connection_manager)

        # Active integrations and listeners (thread-safe)
        self.active_integrations: dict[int, BaseEmailIntegration] = {}
        self.active_listeners: dict[int, EmailListenerThread] = {}
        self.lock = threading.RLock()

        logger.info("EmailIngestionService initialized")

    # ========== Public Methods: Account/Folder Discovery ==========

    def discover_email_accounts(self, provider_type: str = "outlook_com") -> list[EmailAccount]:
        """
        Discover available email accounts for the specified provider.

        Creates a temporary integration instance to query the email provider
        for available accounts. Does not establish a persistent connection.

        Implementation:
        1. Validate provider is supported via IntegrationRegistry
        2. Create temporary integration (no connection needed)
        3. Call integration.discover_accounts()
        4. Return list of EmailAccount dataclasses

        Args:
            provider_type: Email provider to query (default: "outlook_com")

        Returns:
            List of EmailAccount dataclasses with account information

        Raises:
            ValidationError: If provider_type is not supported
            ServiceError: If account discovery fails
        """
        try:
            logger.info(f"Discovering email accounts for provider: {provider_type}")

            # Validate provider is supported
            if not IntegrationRegistry.is_supported(provider_type):
                available = IntegrationRegistry.get_available_providers()
                raise ValidationError(
                    f"Provider '{provider_type}' is not supported. "
                    f"Available providers: {', '.join(available)}"
                )

            # Create temporary integration for discovery
            # No specific email_address needed for account discovery
            integration = IntegrationRegistry.create(
                provider_type=provider_type,
                email_address=None,
                folder_name=None
            )

            logger.debug(f"Created temporary integration for {provider_type}")

            # Discover accounts (no connection needed for Outlook COM)
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

        except ValidationError:
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

    def discover_folders(
        self,
        email_address: str,
        provider_type: str = "outlook_com"
    ) -> list[EmailFolder]:
        """
        Discover available folders for a specific email account.

        Creates a temporary integration instance, connects to the email account,
        retrieves folder information, and then disconnects. This is a one-time
        operation and does not maintain a persistent connection.

        Implementation:
        1. Validate inputs (email_address required, provider supported)
        2. Create temporary integration for this account
        3. Connect to email provider (required for folder discovery)
        4. Call integration.discover_folders()
        5. Disconnect from provider (in finally block)
        6. Return list of EmailFolder dataclasses

        Args:
            email_address: Email address to discover folders for
            provider_type: Email provider to use (default: "outlook_com")

        Returns:
            List of EmailFolder dataclasses with folder information

        Raises:
            ValidationError: If provider not supported or email_address invalid
            ServiceError: If connection or discovery fails
        """
        try:
            # Validate inputs
            if not email_address:
                raise ValidationError("email_address is required")

            if not IntegrationRegistry.is_supported(provider_type):
                available = IntegrationRegistry.get_available_providers()
                raise ValidationError(
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
                folder_name="Inbox"
            )

            logger.debug(f"Created temporary integration for {email_address}")

            # Connect to email provider (required for folder discovery)
            if not integration.connect(email_address):
                raise ServiceError(
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

        except ValidationError:
            # Re-raise validation errors as-is
            raise

        except ServiceError:
            # Re-raise service errors as-is
            raise

        except Exception as e:
            logger.error(
                f"Error discovering folders for '{email_address}': {e}",
                exc_info=True
            )
            raise ServiceError(
                f"Failed to discover folders: {str(e)}"
            ) from e

    # ========== Public Methods: Connection Testing ==========

    def test_connection(
        self,
        email_address: str,
        folder_name: str,
        provider_type: str = "outlook_com"
    ) -> ConnectionTestResult:
        """
        Test connection to email account and folder (wizard step 4 validation).

        Creates temporary integration, tests connection, tests folder access.
        Returns result with success/error information.

        Implementation:
        1. Validate inputs (email_address and folder_name required)
        2. Create temporary integration
        3. Test connection via integration.connect()
        4. Test folder access via integration.test_folder_access()
        5. Disconnect (in finally block)
        6. Return ConnectionTestResult dataclass

        Args:
            email_address: Email address to test
            folder_name: Folder name to test access
            provider_type: Email provider (default: "outlook_com")

        Returns:
            ConnectionTestResult dataclass with success, message, error, details

        Raises:
            ValidationError: If inputs invalid
        """
        try:
            # Validate inputs
            if not email_address:
                raise ValidationError("email_address is required")
            if not folder_name:
                raise ValidationError("folder_name is required")

            # Create temporary integration
            integration = IntegrationRegistry.create(
                provider_type=provider_type,
                email_address=email_address,
                folder_name=folder_name
            )

            # Test connection
            if not integration.connect(email_address):
                return ConnectionTestResult(
                    success=False,
                    message=f"Cannot connect to email account '{email_address}'",
                    error=f"Connection to '{email_address}' failed",
                    details=None
                )

            try:
                # Test folder access (check if folder exists)
                folders = integration.discover_folders(email_address)
                folder_names = [f.name for f in folders]

                if folder_name not in folder_names:
                    return ConnectionTestResult(
                        success=False,
                        message=f"Folder '{folder_name}' does not exist or is not accessible",
                        error=f"Folder '{folder_name}' not found. Available folders: {', '.join(folder_names[:5])}",
                        details={"available_folders": folder_names[:10]}
                    )

                # Success
                return ConnectionTestResult(
                    success=True,
                    message=f"Successfully connected to '{email_address}' and accessed folder '{folder_name}'",
                    error=None,
                    details=None
                )

            finally:
                # Always disconnect
                try:
                    integration.disconnect()
                except Exception as disconnect_error:
                    logger.warning(f"Error disconnecting during test: {disconnect_error}")

        except ValidationError:
            raise

        except Exception as e:
            logger.error(f"Error testing connection: {e}", exc_info=True)
            return ConnectionTestResult(
                success=False,
                message="Connection test failed",
                error=f"Connection test failed: {str(e)}",
                details=None
            )

    # ========== Public Methods: Listener Lifecycle ==========

    def start_monitoring(self, config: EmailConfig) -> ListenerStatus:
        """
        Start email monitoring for a configuration (creates listener thread).

        Called by EmailConfigService.activate_config() when user activates a config.
        Creates integration, connects, creates and starts listener thread.

        Implementation:
        1. Acquire lock (thread-safe operation)
        2. Check if already running (raise ServiceError if so)
        3. Create persistent integration via IntegrationRegistry
        4. Connect to email provider
        5. Create EmailListenerThread with callbacks
        6. Start thread
        7. Track in active_integrations and active_listeners dicts
        8. Return ListenerStatus dataclass

        Args:
            config: EmailConfig dataclass with configuration to monitor

        Returns:
            ListenerStatus dataclass with thread information

        Raises:
            ServiceError: If already running or startup fails
        """
        with self.lock:
            # Check if already running
            if config.id in self.active_listeners:
                raise ServiceError(f"Configuration {config.id} is already being monitored")

            try:
                # Create persistent integration
                integration = IntegrationRegistry.create(
                    provider_type='outklook_com',
                    email_address=config.email_address,
                    folder_name=config.folder_name
                )

                # Connect to provider
                if not integration.connect(config.email_address):
                    raise ServiceError(
                        f"Failed to connect to email account '{config.email_address}'"
                    )

                # Create listener thread with callbacks
                listener = EmailListenerThread(
                    config_id=config.id,
                    integration=integration,
                    filter_rules=config.filter_rules,
                    poll_interval=config.poll_interval_seconds,
                    process_callback=self._process_email,
                    error_callback=self._handle_listener_error
                )

                # Start thread
                listener.start()

                # Track active listener
                self.active_integrations[config.id] = integration
                self.active_listeners[config.id] = listener

                logger.info(f"Started monitoring for config {config.id}")

                # Return status
                return ListenerStatus(
                    config_id=config.id,
                    email_address=config.email_address,
                    folder_name=config.folder_name,
                    is_active=True,
                    is_running=True,
                    start_time=datetime.now(timezone.utc),
                    last_check_time=None,
                    error_count=0,
                    emails_processed=0,
                    pdfs_found=0
                )

            except Exception as e:
                logger.error(f"Failed to start monitoring for config {config.id}: {e}", exc_info=True)
                raise ServiceError(f"Failed to start monitoring: {str(e)}") from e

    def stop_monitoring(self, config_id: int) -> bool:
        """
        Stop email monitoring for a configuration (stops listener thread).

        Called by EmailConfigService.deactivate_config() or delete_config().
        Stops listener thread, disconnects integration, cleans up resources.

        Implementation:
        1. Acquire lock (thread-safe operation)
        2. Check if running (return False if not)
        3. Call listener.stop() to signal thread to stop
        4. Call listener.join(timeout=5.0) to wait for thread
        5. Check if thread stopped (raise ServiceError if still alive)
        6. Disconnect integration
        7. Remove from active_listeners and active_integrations dicts
        8. Return True

        Args:
            config_id: Configuration ID to stop monitoring

        Returns:
            True if stopped successfully, False if not running

        Raises:
            ServiceError: If shutdown fails (thread won't stop)
        """
        with self.lock:
            # Check if running
            if config_id not in self.active_listeners:
                logger.warning(f"Config {config_id} is not being monitored")
                return False

            try:
                # Stop listener thread
                listener = self.active_listeners[config_id]
                listener.stop()
                listener.join(timeout=5.0)  # Wait up to 5 seconds

                if listener.is_alive():
                    logger.error(f"Listener thread for config {config_id} did not stop")
                    raise ServiceError("Listener thread did not stop gracefully")

                # Disconnect integration
                integration = self.active_integrations[config_id]
                try:
                    integration.disconnect()
                except Exception as disconnect_error:
                    logger.warning(f"Error disconnecting integration for config {config_id}: {disconnect_error}")

                # Remove from active tracking
                del self.active_listeners[config_id]
                del self.active_integrations[config_id]

                logger.info(f"Stopped monitoring for config {config_id}")
                return True

            except Exception as e:
                logger.error(f"Failed to stop monitoring for config {config_id}: {e}", exc_info=True)
                raise ServiceError(f"Failed to stop monitoring: {str(e)}") from e

    def is_listener_active(self, config_id: int) -> bool:
        """
        Check if listener thread is running for a configuration.

        Called by router to enrich GET /email-configs/{id} response with is_running.
        Thread-safe operation.

        Implementation:
        1. Acquire lock
        2. Check if config_id in active_listeners dict
        3. If not, return False
        4. Call listener.is_alive() and return result

        Args:
            config_id: Configuration ID to check

        Returns:
            True if listener is active and running, False otherwise
        """
        with self.lock:
            if config_id not in self.active_listeners:
                return False

            listener = self.active_listeners[config_id]
            return listener.is_alive()

    # ========== Internal Methods: Email Processing ==========

    def _process_email(
        self,
        config_id: int,
        email_msg: EmailMessage,
        attachments: list[EmailAttachment]
    ) -> None:
        """
        Process single email from listener thread (callback).

        Called by EmailListenerThread when new email is found.
        Stores email, extracts PDFs, triggers ETO processing.

        Pipeline:
        1. Check for duplicates via email_repository.get_by_message_id()
        2. If duplicate, log and return (skip processing)
        3. Store email record via email_repository.create()
        4. For each attachment:
           a. Check if PDF (attachment.content_type or filename)
           b. Store PDF via pdf_service.store_pdf()
           c. Trigger ETO processing via eto_service.process_pdf()
        5. Update config statistics (optional)

        Args:
            config_id: Configuration ID that received this email
            email_msg: EmailMessage dataclass from integration
            attachments: List of EmailAttachment dataclasses

        Note:
            - Called from background thread - must be thread-safe
            - Errors should be caught and passed to _handle_listener_error()
        """
        try:
            # Check for duplicate
            existing = self.email_repository.get_by_message_id(email_msg.message_id)
            if existing:
                logger.debug(f"Email {email_msg.message_id} already processed, skipping")
                return

            # Store email record
            email_create = EmailCreate(
                config_id=config_id,
                message_id=email_msg.message_id,
                sender_email=email_msg.sender_email,
                subject=email_msg.subject,
                received_date=email_msg.received_date,
                folder_name=email_msg.folder_name
            )
            email_record = self.email_repository.create(email_create)

            logger.info(
                f"Stored email record {email_record.id} for message {email_msg.message_id[:20]}..."
            )

            # Process PDF attachments
            pdf_count = 0
            for attachment in attachments:
                # Check if PDF
                is_pdf = (
                    (attachment.content_type and 'pdf' in attachment.content_type.lower()) or
                    (attachment.filename and attachment.filename.lower().endswith('.pdf'))
                )

                if is_pdf:
                    logger.info(
                        f"Processing PDF attachment: {attachment.filename} "
                        f"({attachment.size_bytes} bytes)"
                    )

                    # Store PDF via pdf_service
                    # Note: pdf_service will be implemented later
                    # For now, just log that we would process it
                    logger.info(f"PDF {attachment.filename} would be stored and processed by ETO")
                    pdf_count += 1

                    # TODO: When pdf_service is implemented:
                    # pdf_record = self.pdf_service.store_pdf(
                    #     file_bytes=attachment.content,
                    #     filename=attachment.filename,
                    #     email_id=email_record.id
                    # )
                    #
                    # # Trigger ETO processing
                    # self.eto_service.process_pdf(pdf_record.id)

            logger.info(
                f"Processed email {email_msg.message_id[:20]}... "
                f"(config {config_id}): {pdf_count} PDFs found"
            )

        except Exception as e:
            logger.error(
                f"Error processing email {email_msg.message_id}: {e}",
                exc_info=True
            )
            # Don't re-raise - let listener continue with next email
            # Error is already logged and will be tracked by listener

    def _handle_listener_error(self, config_id: int, error: Exception) -> None:
        """
        Handle errors from listener threads (callback).

        Called by EmailListenerThread when errors occur during email polling
        or processing. Logs error, updates config error tracking.

        Implementation:
        1. Log error with exc_info=True
        2. Update config error tracking via config_repository.update():
           - Set last_error_message to str(error)
           - Set last_error_at to current time
        3. Optional: Implement retry logic, error counting, auto-deactivation

        Args:
            config_id: Configuration ID that encountered error
            error: Exception that occurred

        Note:
            - Called from background thread - must be thread-safe
            - Should not raise exceptions (would crash thread)
        """
        logger.error(
            f"Listener error for config {config_id}: {error}",
            exc_info=True
        )

        try:
            # Update config error tracking
            from shared.types.email_configs import EmailConfigUpdate

            error_update = EmailConfigUpdate(
                last_error_message=str(error)[:500],  # Truncate to 500 chars
                last_error_at=datetime.now(timezone.utc)
            )

            self.config_repository.update(config_id, error_update)

            logger.debug(f"Updated error tracking for config {config_id}")

        except Exception as update_error:
            # Don't raise - just log the error
            # This prevents cascading failures in the listener thread
            logger.error(
                f"Error updating error tracking for config {config_id}: {update_error}",
                exc_info=True
            )
