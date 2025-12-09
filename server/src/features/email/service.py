"""
Email Service

Unified service for email functionality including:
- Account management (CRUD, validation)
- Ingestion configuration management
- Integration lifecycle management (connection pooling)
- Polling runtime (start/stop pollers)
- Email processing (PDF extraction, ETO run creation)
"""
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from shared.database import DatabaseConnectionManager
from shared.database.repositories.email_account import EmailAccountRepository
from shared.database.repositories.email_ingestion_config import EmailIngestionConfigRepository
from shared.database.repositories.email import EmailRepository
from shared.types.email_accounts import (
    EmailAccount,
    EmailAccountSummary,
    EmailAccountCreate,
    EmailAccountUpdate,
    ProviderSettings,
    Credentials,
    ImapProviderSettings,
    PasswordCredentials,
)
from shared.types.email_ingestion_configs import (
    EmailIngestionConfig,
    EmailIngestionConfigSummary,
    EmailIngestionConfigWithAccount,
    EmailIngestionConfigCreate,
    EmailIngestionConfigUpdate,
)
from shared.exceptions.service import ObjectNotFoundError, ValidationError, ConflictError

from features.email.integrations import IntegrationRegistry
from features.email.integrations.base_integration import (
    BaseEmailIntegration,
    EmailMessage,
    ValidationResult,
)
from features.email.poller import PollerWorker
from features.email.processing import EmailProcessingHandler

if TYPE_CHECKING:
    from features.pdf_files.service import PdfFilesService
    from features.eto_runs.service import EtoRunsService

logger = logging.getLogger(__name__)


class EmailService:
    """
    Unified email service for account management, ingestion configs, and runtime.

    Architecture:
    - One integration instance per account (cached, reused across configs)
    - One poller worker per active config
    - Service manages integration lifecycle (startup/shutdown)
    - All email operations go through protocol-agnostic interface

    Account Management:
    - validate_connection: Test credentials without persisting
    - create_account: Persist a validated account
    - list_accounts / get_account / update_account / delete_account

    Ingestion Config Management:
    - list_ingestion_configs / get_ingestion_config
    - create_ingestion_config / update_ingestion_config / delete_ingestion_config
    - activate_config / deactivate_config

    Runtime:
    - startup(): Load active configs, start pollers
    - shutdown(): Stop all pollers, close connections
    - get_emails_since_uid(): Protocol-agnostic email fetching
    """

    def __init__(
        self,
        connection_manager: DatabaseConnectionManager,
        pdf_files_service: "PdfFilesService | None" = None,
        eto_runs_service: "EtoRunsService | None" = None,
    ) -> None:
        """
        Initialize email service.

        Args:
            connection_manager: Database connection manager
            pdf_files_service: Service for storing PDF files (optional, enables processing)
            eto_runs_service: Service for creating ETO runs (optional, enables processing)
        """
        self.connection_manager = connection_manager
        self.account_repository = EmailAccountRepository(connection_manager=connection_manager)
        self.ingestion_config_repository = EmailIngestionConfigRepository(connection_manager=connection_manager)
        self.email_repository = EmailRepository(connection_manager=connection_manager)

        # Store service references for processing handler
        self._pdf_files_service = pdf_files_service
        self._eto_runs_service = eto_runs_service

        # Create processing handler if dependencies are available
        if pdf_files_service and eto_runs_service:
            self._processing_handler = EmailProcessingHandler(
                email_repository=self.email_repository,
                pdf_files_service=pdf_files_service,
                eto_runs_service=eto_runs_service,
            )
            logger.info("EmailService: Processing handler initialized (PDF extraction enabled)")
        else:
            self._processing_handler = None
            logger.warning("EmailService: Processing handler NOT initialized (missing pdf_files_service or eto_runs_service)")

        # Integration instances (one per account)
        self._integrations: dict[int, BaseEmailIntegration] = {}

        # Poller workers (one per active config)
        self._pollers: dict[int, PollerWorker] = {}

        # Count of active configs per account (for integration lifecycle)
        self._config_counts: dict[int, int] = {}

        logger.info("EmailService initialized")

    # ========== Runtime Lifecycle ==========

    def startup(self) -> None:
        """
        Initialize the service and start polling for active configs.

        Should be called on server startup.
        """
        logger.info("=" * 60)
        logger.info("EMAILSERVICE STARTUP")
        logger.info("=" * 60)

        # Load all active configs and start pollers
        active_configs = self.ingestion_config_repository.get_active_configs()

        logger.info(f"Found {len(active_configs)} active ingestion configs to restore")

        for config in active_configs:
            try:
                self._activate_config_internal(config)
            except Exception as e:
                logger.error(f"Failed to activate config {config.id}: {e}")
                # Record error but continue with other configs
                self._record_config_error_internal(config.id, str(e))

        logger.info("-" * 60)
        logger.info(f"EMAILSERVICE STARTED")
        logger.info(f"  Active integrations: {len(self._integrations)}")
        logger.info(f"  Active pollers: {len(self._pollers)}")
        for account_id in self._integrations:
            config_count = self._config_counts.get(account_id, 0)
            logger.info(f"    Account {account_id}: {config_count} config(s) using shared connection")
        logger.info("=" * 60)

    def shutdown(self) -> None:
        """
        Stop all pollers and close all connections.

        Should be called on server shutdown.
        """
        logger.info("=" * 60)
        logger.info("EMAILSERVICE SHUTDOWN")
        logger.info("=" * 60)
        logger.info(f"Stopping {len(self._pollers)} poller(s) and {len(self._integrations)} integration(s)")

        # Stop all pollers
        for config_id in list(self._pollers.keys()):
            try:
                logger.info(f"  Stopping poller for config {config_id}...")
                self._deactivate_config_internal(config_id, update_db=False)
            except Exception as e:
                logger.error(f"Error stopping poller {config_id}: {e}")

        # Shutdown all integrations
        for account_id, integration in list(self._integrations.items()):
            try:
                logger.info(f"  Closing connection for account {account_id}...")
                integration.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down integration for account {account_id}: {e}")

        self._integrations.clear()
        self._config_counts.clear()

        logger.info("EMAILSERVICE SHUTDOWN COMPLETE")
        logger.info("=" * 60)

    # ========== Integration Management ==========

    def _get_or_create_integration(self, account_id: int) -> BaseEmailIntegration:
        """
        Get cached integration or create new one via registry.

        Does NOT call startup() - caller must handle lifecycle.
        """
        if account_id in self._integrations:
            return self._integrations[account_id]

        account = self.account_repository.get_by_id(account_id)
        if not account:
            raise ObjectNotFoundError(f"Email account {account_id} not found")

        integration = self._create_integration_from_account(account)
        self._integrations[account_id] = integration

        return integration

    def _create_integration_from_account(self, account: EmailAccount) -> BaseEmailIntegration:
        """Create integration instance from account data using registry."""
        params = self._build_integration_params(account)
        return IntegrationRegistry.create(account.provider_type, **params)

    def _build_integration_params(self, account: EmailAccount) -> dict:
        """Build constructor params for integration based on provider type."""
        provider_type = account.provider_type

        if provider_type == "imap":
            settings = account.provider_settings
            credentials = account.credentials

            if not isinstance(settings, ImapProviderSettings):
                raise ValidationError("Invalid provider settings for IMAP")
            if not isinstance(credentials, PasswordCredentials):
                raise ValidationError("IMAP currently only supports password credentials")

            return {
                "host": settings.host,
                "port": settings.port,
                "email_address": account.email_address,
                "password": credentials.password,
                "use_ssl": settings.use_ssl,
            }

        # Future: Add other provider types here
        raise ValidationError(f"Provider type '{provider_type}' not yet implemented")

    # ========== Protocol-Agnostic Email Operations ==========

    def get_emails_since_uid(
        self,
        config: EmailIngestionConfig,
        since_uid: int | None = None,
        limit: int = 100,
    ) -> list[EmailMessage]:
        """
        Get emails for a config since the given UID.

        Protocol-agnostic - works for any provider type.

        Args:
            config: Ingestion config
            since_uid: UID to start from (default: config's last_processed_uid)
            limit: Max emails to fetch

        Returns:
            List of EmailMessage dataclasses
        """
        integration = self._get_or_create_integration(config.account_id)

        uid = since_uid if since_uid is not None else (config.last_processed_uid or 0)

        return integration.get_emails_since_uid(
            folder_name=config.folder_name,
            since_uid=uid,
            limit=limit,
        )

    # ========== Connection Testing ==========

    def validate_connection(
        self,
        provider_type: str,
        email_address: str,
        provider_settings: ProviderSettings,
        credentials: Credentials,
    ) -> ValidationResult:
        """
        Test email connection without persisting anything.

        Creates a transient integration, validates, and discards.
        """
        logger.info(f"Validating connection for {email_address} via {provider_type}")

        if not IntegrationRegistry.is_supported(provider_type):
            available = IntegrationRegistry.get_available_providers()
            raise ValidationError(
                f"Unsupported provider type: {provider_type}. "
                f"Available: {', '.join(available)}"
            )

        # Build params and create transient integration
        params = self._build_validation_params(
            provider_type, email_address, provider_settings, credentials
        )
        integration = IntegrationRegistry.create(provider_type, **params)

        # Validate using integration's method
        result = integration.validate_credentials()

        if result.success:
            logger.info(f"Connection validated for {email_address}")
        else:
            logger.warning(f"Connection validation failed for {email_address}: {result.message}")

        return result

    def _build_validation_params(
        self,
        provider_type: str,
        email_address: str,
        provider_settings: ProviderSettings,
        credentials: Credentials,
    ) -> dict:
        """Build params for validation integration."""
        if provider_type == "imap":
            if not isinstance(provider_settings, ImapProviderSettings):
                raise ValidationError("Invalid provider settings for IMAP")
            if not isinstance(credentials, PasswordCredentials):
                raise ValidationError("IMAP currently only supports password credentials")

            return {
                "host": provider_settings.host,
                "port": provider_settings.port,
                "email_address": email_address,
                "password": credentials.password,
                "use_ssl": provider_settings.use_ssl,
            }

        raise ValidationError(f"Provider type '{provider_type}' not yet implemented")

    # ========== Account Management ==========

    def list_accounts(
        self,
        order_by: str = "name",
        desc: bool = False,
        validated_only: bool = False,
    ) -> list[EmailAccountSummary]:
        """List all email accounts as summaries (no credentials)."""
        return self.account_repository.get_all_summaries(
            order_by=order_by,
            desc=desc,
            validated_only=validated_only,
        )

    def get_account(self, account_id: int) -> EmailAccount:
        """Get email account by ID (includes credentials)."""
        account = self.account_repository.get_by_id(account_id)
        if not account:
            raise ObjectNotFoundError(f"Email account {account_id} not found")
        return account

    def list_account_folders(self, account_id: int) -> list[str]:
        """
        List available folders for an email account.

        Uses cached integration if available, otherwise creates transient one.
        """
        account = self.account_repository.get_by_id(account_id)
        if not account:
            raise ObjectNotFoundError(f"Email account {account_id} not found")

        if not account.is_validated:
            raise ValidationError(
                f"Email account {account_id} is not validated. "
                "Please validate the account first."
            )

        # Check if we have a running integration
        if account_id in self._integrations:
            return self._integrations[account_id].list_folders()

        # Create transient integration for folder listing
        integration = self._create_integration_from_account(account)
        try:
            integration.startup()
            return integration.list_folders()
        finally:
            integration.shutdown()

    def create_account(self, account_data: EmailAccountCreate) -> EmailAccount:
        """Create a new email account."""
        existing = self.account_repository.get_by_email_address(account_data.email_address)
        if existing:
            raise ConflictError(f"Email account with address {account_data.email_address} already exists")

        account = self.account_repository.create(account_data)
        logger.info(f"Created email account {account.id}: {account.name} ({account.email_address})")
        return account

    def create_validated_account(
        self,
        account_data: EmailAccountCreate,
        capabilities: list[str],
    ) -> EmailAccount:
        """Create a new email account that has been validated."""
        existing = self.account_repository.get_by_email_address(account_data.email_address)
        if existing:
            raise ConflictError(f"Email account with address {account_data.email_address} already exists")

        account = self.account_repository.create(account_data)

        account = self.account_repository.update(
            account.id,
            EmailAccountUpdate(
                is_validated=True,
                validated_at=datetime.now(timezone.utc),
                capabilities=capabilities,
                clear_errors=True,
            )
        )

        logger.info(
            f"Created validated email account {account.id}: {account.name} "
            f"({account.email_address}) with capabilities: {capabilities}"
        )
        return account

    def update_account(
        self,
        account_id: int,
        account_update: EmailAccountUpdate,
    ) -> EmailAccount:
        """Update email account."""
        existing = self.account_repository.get_by_id(account_id)
        if not existing:
            raise ObjectNotFoundError(f"Email account {account_id} not found")

        account = self.account_repository.update(account_id, account_update)
        logger.info(f"Updated email account {account_id}")
        return account

    def delete_account(self, account_id: int) -> EmailAccount:
        """Delete email account."""
        existing = self.account_repository.get_by_id(account_id)
        if not existing:
            raise ObjectNotFoundError(f"Email account {account_id} not found")

        # Check for active configs
        active_configs = [
            c for c in self.ingestion_config_repository.get_by_account_id(account_id)
            if c.is_active
        ]
        if active_configs:
            raise ConflictError(
                f"Cannot delete account {account_id} with {len(active_configs)} active ingestion configs. "
                "Deactivate them first."
            )

        account = self.account_repository.delete(account_id)
        logger.info(f"Deleted email account {account_id}: {account.email_address}")
        return account

    def mark_account_invalid(
        self,
        account_id: int,
        error_message: str,
    ) -> EmailAccount:
        """Mark an account as invalid due to authentication failure."""
        account = self.account_repository.update(
            account_id,
            EmailAccountUpdate(
                is_validated=False,
                last_error_message=error_message,
                last_error_at=datetime.now(timezone.utc),
            )
        )
        logger.warning(f"Marked email account {account_id} as invalid: {error_message}")
        return account

    # ========== Ingestion Config Management ==========

    def list_ingestion_configs(
        self,
        order_by: str = "name",
        desc: bool = False,
    ) -> list[EmailIngestionConfigWithAccount]:
        """List all ingestion configs with account info."""
        return self.ingestion_config_repository.get_all_with_accounts(
            order_by=order_by,
            desc=desc,
        )

    def get_ingestion_config(self, config_id: int) -> EmailIngestionConfigWithAccount:
        """Get ingestion config by ID with account info."""
        config = self.ingestion_config_repository.get_by_id_with_account(config_id)
        if not config:
            raise ObjectNotFoundError(f"Ingestion config {config_id} not found")
        return config

    def validate_ingestion_config(
        self,
        account_id: int,
        folder_name: str,
    ) -> bool:
        """Validate that an ingestion config can be created."""
        account = self.account_repository.get_by_id(account_id)
        if not account:
            raise ObjectNotFoundError(f"Email account {account_id} not found")

        if not account.is_validated:
            raise ValidationError(
                f"Email account {account_id} is not validated. "
                "Please validate the account first."
            )

        # Verify folder exists
        folders = self.list_account_folders(account_id)
        if folder_name not in folders:
            raise ValidationError(
                f"Folder '{folder_name}' not found in account {account_id}. "
                f"Available folders: {', '.join(folders[:10])}{'...' if len(folders) > 10 else ''}"
            )

        logger.info(f"Validated ingestion config for account {account_id}, folder {folder_name}")
        return True

    def create_ingestion_config(
        self,
        config_data: EmailIngestionConfigCreate,
    ) -> EmailIngestionConfig:
        """Create a new ingestion config (inactive by default)."""
        self.validate_ingestion_config(
            account_id=config_data.account_id,
            folder_name=config_data.folder_name,
        )

        config = self.ingestion_config_repository.create(config_data)

        logger.info(
            f"Created ingestion config {config.id}: {config.name} "
            f"(account={config.account_id}, folder={config.folder_name})"
        )
        return config

    def update_ingestion_config(
        self,
        config_id: int,
        config_update: EmailIngestionConfigUpdate,
    ) -> EmailIngestionConfig:
        """Update ingestion config (cannot update active config)."""
        existing = self.ingestion_config_repository.get_by_id(config_id)
        if not existing:
            raise ObjectNotFoundError(f"Ingestion config {config_id} not found")

        if existing.is_active:
            raise ConflictError(
                f"Cannot update active ingestion config {config_id}. "
                "Deactivate it first."
            )

        config = self.ingestion_config_repository.update(config_id, config_update)
        logger.info(f"Updated ingestion config {config_id}")
        return config

    def delete_ingestion_config(self, config_id: int) -> EmailIngestionConfig:
        """Delete ingestion config (cannot delete active config)."""
        existing = self.ingestion_config_repository.get_by_id(config_id)
        if not existing:
            raise ObjectNotFoundError(f"Ingestion config {config_id} not found")

        if existing.is_active:
            raise ConflictError(
                f"Cannot delete active ingestion config {config_id}. "
                "Deactivate it first."
            )

        config = self.ingestion_config_repository.delete(config_id)
        logger.info(f"Deleted ingestion config {config_id}")
        return config

    def get_ingestion_configs_for_account(
        self,
        account_id: int,
    ) -> list[EmailIngestionConfig]:
        """Get all ingestion configs for a specific account."""
        return self.ingestion_config_repository.get_by_account_id(account_id)

    # ========== Config Activation ==========

    def activate_config(self, config_id: int) -> EmailIngestionConfig:
        """
        Activate an ingestion config and start polling.

        Starts the integration if needed, then starts a poller.
        """
        config = self.ingestion_config_repository.get_by_id(config_id)
        if not config:
            raise ObjectNotFoundError(f"Ingestion config {config_id} not found")

        if config.is_active:
            logger.warning(f"Config {config_id} is already active")
            return config

        # Update DB first
        config = self.ingestion_config_repository.update(
            config_id,
            EmailIngestionConfigUpdate(
                is_active=True,
                activated_at=datetime.now(timezone.utc),
            )
        )

        # Start polling
        self._activate_config_internal(config)

        logger.info(f"Activated ingestion config {config_id}")
        return config

    def deactivate_config(self, config_id: int) -> EmailIngestionConfig:
        """
        Deactivate an ingestion config and stop polling.

        Stops the poller, shuts down integration if no more active configs.
        """
        config = self.ingestion_config_repository.get_by_id(config_id)
        if not config:
            raise ObjectNotFoundError(f"Ingestion config {config_id} not found")

        if not config.is_active:
            logger.warning(f"Config {config_id} is already inactive")
            return config

        # Stop polling and update DB
        self._deactivate_config_internal(config_id, update_db=True)

        # Reload updated config
        config = self.ingestion_config_repository.get_by_id(config_id)
        if config is None:
            raise ObjectNotFoundError(f"Ingestion config {config_id} not found")

        logger.info(f"Deactivated ingestion config {config_id}")
        return config

    def _activate_config_internal(self, config: EmailIngestionConfig) -> None:
        """Internal: Start integration and poller for config."""
        account_id = config.account_id

        logger.info("-" * 40)
        logger.info(f"ACTIVATING CONFIG {config.id}: {config.name}")
        logger.info(f"  Account ID: {account_id}")
        logger.info(f"  Folder: {config.folder_name}")
        logger.info(f"  Poll interval: {config.poll_interval_seconds}s")

        # Ensure integration exists
        if account_id not in self._integrations:
            logger.info(f"  Creating NEW connection for account {account_id}...")
            integration = self._get_or_create_integration(account_id)
            integration.startup()
            self._config_counts[account_id] = 0
            logger.info(f"  Connection established for account {account_id}")
        else:
            logger.info(f"  REUSING existing connection for account {account_id}")

        self._config_counts[account_id] = self._config_counts.get(account_id, 0) + 1
        logger.info(f"  Account {account_id} now has {self._config_counts[account_id]} active config(s)")

        # Initialize UID if needed
        if config.last_processed_uid is None:
            try:
                integration = self._integrations[account_id]
                highest_uid = integration.get_highest_uid(config.folder_name)
                if highest_uid is not None:
                    self.ingestion_config_repository.update(
                        config.id,
                        EmailIngestionConfigUpdate(last_processed_uid=highest_uid)
                    )
                    # Update local config copy
                    updated_config = self.ingestion_config_repository.get_by_id(config.id)
                    if updated_config is None:
                        raise ObjectNotFoundError(f"Ingestion config {config.id} not found after update")
                    config = updated_config
                    logger.info(f"  Initialized last_processed_uid to {highest_uid}")
            except Exception as e:
                logger.warning(f"  Failed to initialize UID: {e}")

        # Start poller with internal callback
        poller = PollerWorker(
            config=config,
            service=self,
            email_repository=self.email_repository,
            on_emails_received=self._on_emails_received,
        )
        self._pollers[config.id] = poller
        poller.start()
        logger.info(f"  Poller started for config {config.id}")
        logger.info(f"CONFIG {config.id} ACTIVATED")
        logger.info("-" * 40)

    def _on_emails_received(
        self,
        config: EmailIngestionConfig,
        emails: list[EmailMessage],
    ) -> None:
        """
        Internal callback when poller receives new emails.

        Routes to processing handler which downloads attachments,
        stores PDFs, creates email records, and creates ETO runs.
        """
        if not self._processing_handler:
            logger.warning(
                f"[EMAIL] Received {len(emails)} email(s) for config {config.id} "
                f"but processing handler not available - emails will not be processed"
            )
            return

        # Get the integration for this account (to download attachments)
        integration = self._integrations.get(config.account_id)
        if not integration:
            logger.error(
                f"[EMAIL] No integration found for account {config.account_id} - "
                f"cannot process {len(emails)} email(s)"
            )
            return

        # Process the emails
        self._processing_handler.process_emails(
            config=config,
            emails=emails,
            integration=integration,
        )

    def _deactivate_config_internal(self, config_id: int, update_db: bool = True) -> None:
        """
        Internal: Stop poller and maybe shutdown integration.

        Works even if no poller exists (e.g., DB says active but server restarted
        and poller was never started). Will still update DB if requested.
        """
        poller = self._pollers.pop(config_id, None)

        # Get config info - try from poller first, fall back to DB
        if poller is not None:
            config = poller.config
            account_id = config.account_id
            config_name = config.name
            folder_name = config.folder_name
        else:
            # No poller - get config from DB
            config = self.ingestion_config_repository.get_by_id(config_id)
            if config is None:
                logger.warning(f"No poller or config found for config_id {config_id}")
                return
            account_id = config.account_id
            config_name = config.name
            folder_name = config.folder_name

        logger.info("-" * 40)
        logger.info(f"DEACTIVATING CONFIG {config_id}: {config_name}")
        logger.info(f"  Account ID: {account_id}")
        logger.info(f"  Folder: {folder_name}")

        # Stop poller if it exists
        if poller is not None:
            poller.stop()
            logger.info(f"  Poller stopped")
        else:
            logger.info(f"  No active poller (DB-only deactivation)")

        # Update DB if requested
        if update_db:
            self.ingestion_config_repository.update(
                config_id,
                EmailIngestionConfigUpdate(
                    is_active=False,
                    reset_last_processed_uid=True,  # Reset so reactivation starts fresh
                )
            )
            logger.info(f"  Database updated (is_active=False, last_processed_uid=NULL)")

        # Only manage integration lifecycle if we had a poller
        # (If no poller, the integration may not be running for this account)
        if poller is not None:
            # Decrement config count
            self._config_counts[account_id] = self._config_counts.get(account_id, 1) - 1
            remaining = self._config_counts.get(account_id, 0)
            logger.info(f"  Account {account_id} now has {remaining} active config(s)")

            # Shutdown integration if no more configs
            if remaining <= 0:
                integration = self._integrations.pop(account_id, None)
                if integration:
                    logger.info(f"  CLOSING connection for account {account_id} (no more active configs)")
                    integration.shutdown()
                self._config_counts.pop(account_id, None)
            else:
                logger.info(f"  KEEPING connection open for account {account_id} ({remaining} config(s) still active)")

        logger.info(f"CONFIG {config_id} DEACTIVATED")
        logger.info("-" * 40)

    # ========== Poller Update Methods ==========

    def update_config_uid(self, config_id: int, uid: int) -> None:
        """Update last_processed_uid for a config."""
        self.ingestion_config_repository.update(
            config_id,
            EmailIngestionConfigUpdate(last_processed_uid=uid)
        )

    def update_config_last_check(self, config_id: int) -> None:
        """Update last_check_time for a config."""
        self.ingestion_config_repository.update(
            config_id,
            EmailIngestionConfigUpdate(last_check_time=datetime.now(timezone.utc))
        )

    def record_config_error(self, config_id: int, error_message: str) -> None:
        """Record an error for a config."""
        self._record_config_error_internal(config_id, error_message)

    def _record_config_error_internal(self, config_id: int, error_message: str) -> None:
        """Internal: Record error without raising."""
        try:
            self.ingestion_config_repository.update(
                config_id,
                EmailIngestionConfigUpdate(
                    last_error_message=error_message,
                    last_error_at=datetime.now(timezone.utc),
                )
            )
        except Exception as e:
            logger.error(f"Failed to record error for config {config_id}: {e}")
