"""
Email Service

Unified service for email functionality including:
- Account management (CRUD, validation)
- Ingestion configuration management
- (Future) Email sending
"""
import logging
from datetime import datetime, timezone

from shared.database import DatabaseConnectionManager
from shared.database.repositories.email_account import EmailAccountRepository
from shared.database.repositories.email_ingestion_config import EmailIngestionConfigRepository
from shared.types.email_accounts import (
    EmailAccount,
    EmailAccountSummary,
    EmailAccountCreate,
    EmailAccountUpdate,
    EmailAccountValidationResult,
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
from features.email.integrations.imap_integration import ImapIntegration

logger = logging.getLogger(__name__)


class EmailService:
    """
    Unified email service for account management and email operations.

    Account Management:
    - validate_connection: Test credentials without persisting
    - create_account: Persist a validated account
    - list_accounts: Get all account summaries
    - get_account: Get single account by ID
    - update_account: Update account details
    - delete_account: Remove account (if no active dependencies)

    Ingestion Config Management:
    - list_ingestion_configs: Get all configs with account info
    - get_ingestion_config: Get single config by ID
    - create_ingestion_config: Create new config for an account
    - update_ingestion_config: Update config settings
    - delete_ingestion_config: Remove config

    Future:
    - Ingestion runtime management (start/stop listeners)
    - Email sending functionality
    """

    def __init__(self, connection_manager: DatabaseConnectionManager) -> None:
        """
        Initialize email service.

        Args:
            connection_manager: Database connection manager
        """
        self.connection_manager = connection_manager
        self.account_repository = EmailAccountRepository(connection_manager=connection_manager)
        self.ingestion_config_repository = EmailIngestionConfigRepository(connection_manager=connection_manager)

        logger.info("EmailService initialized")

    # ========== Connection Testing ==========

    def validate_connection(
        self,
        provider_type: str,
        email_address: str,
        provider_settings: ProviderSettings,
        credentials: Credentials,
    ) -> EmailAccountValidationResult:
        """
        Test email connection without persisting anything.

        Validates credentials by attempting to connect to the email provider.
        On success, discovers server capabilities (for IMAP).

        Args:
            provider_type: Type of email provider ("imap", "gmail_api", etc.)
            email_address: Email address for the account
            provider_settings: Provider-specific connection settings
            credentials: Authentication credentials

        Returns:
            EmailAccountValidationResult with success status, message,
            and discovered capabilities
        """
        logger.info(f"Validating connection for {email_address} via {provider_type}")

        try:
            integration = self._create_integration(
                provider_type=provider_type,
                email_address=email_address,
                provider_settings=provider_settings,
                credentials=credentials,
            )

            # Attempt connection
            success = integration.connect()

            if success:
                # Get capabilities if IMAP
                capabilities: list[str] = []
                if isinstance(integration, ImapIntegration):
                    imap_integration: ImapIntegration = integration
                    capabilities = imap_integration.get_capabilities()

                integration.disconnect()

                logger.info(
                    f"Connection validated for {email_address}: "
                    f"capabilities={capabilities}"
                )

                return EmailAccountValidationResult(
                    success=True,
                    message="Connection successful",
                    capabilities=capabilities,
                )
            else:
                logger.warning(f"Connection validation failed for {email_address}")
                return EmailAccountValidationResult(
                    success=False,
                    message="Connection failed - check credentials",
                    capabilities=[],
                )

        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Connection validation error for {email_address}: {e}", exc_info=True)
            return EmailAccountValidationResult(
                success=False,
                message=f"Connection failed: {str(e)}",
                capabilities=[],
            )

    def _create_integration(
        self,
        provider_type: str,
        email_address: str,
        provider_settings: ProviderSettings,
        credentials: Credentials,
    ):
        """
        Create an integration instance for the given provider type.

        Args:
            provider_type: Type of provider ("imap", "gmail_api", etc.)
            email_address: Email address for authentication
            provider_settings: Provider-specific settings
            credentials: Authentication credentials

        Returns:
            Integration instance

        Raises:
            ValidationError: If provider type is not supported or settings are invalid
        """
        if not IntegrationRegistry.is_supported(provider_type):
            available = IntegrationRegistry.get_available_providers()
            raise ValidationError(
                f"Unsupported provider type: {provider_type}. "
                f"Available: {', '.join(available)}"
            )

        if provider_type == "imap":
            if not isinstance(provider_settings, ImapProviderSettings):
                raise ValidationError("Invalid provider settings for IMAP")
            if not isinstance(credentials, PasswordCredentials):
                raise ValidationError("IMAP currently only supports password credentials")

            return IntegrationRegistry.create(
                provider_type=provider_type,
                host=provider_settings.host,
                port=provider_settings.port,
                email_address=email_address,
                password=credentials.password,
                use_ssl=provider_settings.use_ssl,
            )

        # Future: Add other provider types here
        raise ValidationError(f"Provider type '{provider_type}' not yet implemented")

    # ========== Account Management ==========

    def list_accounts(
        self,
        order_by: str = "name",
        desc: bool = False,
        validated_only: bool = False,
    ) -> list[EmailAccountSummary]:
        """
        List all email accounts as summaries (no credentials).

        Args:
            order_by: Field to sort by ("name", "email_address", "created_at")
            desc: Sort descending if True
            validated_only: Only return validated accounts

        Returns:
            List of EmailAccountSummary dataclasses
        """
        return self.account_repository.get_all_summaries(
            order_by=order_by,
            desc=desc,
            validated_only=validated_only,
        )

    def get_account(self, account_id: int) -> EmailAccount:
        """
        Get email account by ID (includes credentials).

        Args:
            account_id: Account ID

        Returns:
            EmailAccount dataclass

        Raises:
            ObjectNotFoundError: If account not found
        """
        account = self.account_repository.get_by_id(account_id)

        if not account:
            raise ObjectNotFoundError(f"Email account {account_id} not found")

        return account

    def list_account_folders(self, account_id: int) -> list[str]:
        """
        List available folders/mailboxes for an email account.

        Connects to the email server and retrieves the folder list.

        Args:
            account_id: Account ID

        Returns:
            List of folder names (e.g., ["INBOX", "Sent", "Drafts"])

        Raises:
            ObjectNotFoundError: If account not found
            ValidationError: If account not validated or connection fails
        """
        # Get the account
        account = self.account_repository.get_by_id(account_id)
        if not account:
            raise ObjectNotFoundError(f"Email account {account_id} not found")

        # Check account is validated
        if not account.is_validated:
            raise ValidationError(
                f"Email account {account_id} is not validated. "
                "Please validate the account first."
            )

        # Create integration and connect
        integration = self._create_integration(
            provider_type=account.provider_type,
            email_address=account.email_address,
            provider_settings=account.provider_settings,
            credentials=account.credentials,
        )

        try:
            success = integration.connect()
            if not success:
                raise ValidationError(
                    f"Failed to connect to email account {account_id}. "
                    "The account may need to be re-validated."
                )

            # Get folders (IMAP-specific)
            folders: list[str] = []
            if isinstance(integration, ImapIntegration):
                imap_integration: ImapIntegration = integration
                folders = imap_integration.list_folders()

            return folders

        finally:
            integration.disconnect()

    def create_account(self, account_data: EmailAccountCreate) -> EmailAccount:
        """
        Create a new email account.

        The account should have been validated via validate_connection() first.
        This method persists the account with is_validated=True.

        Args:
            account_data: EmailAccountCreate with account details

        Returns:
            Created EmailAccount dataclass

        Raises:
            ConflictError: If email address already exists
        """
        # Check for duplicate email address
        existing = self.account_repository.get_by_email_address(account_data.email_address)
        if existing:
            raise ConflictError(f"Email account with address {account_data.email_address} already exists")

        # Create the account
        account = self.account_repository.create(account_data)

        logger.info(f"Created email account {account.id}: {account.name} ({account.email_address})")

        return account

    def create_validated_account(
        self,
        account_data: EmailAccountCreate,
        capabilities: list[str],
    ) -> EmailAccount:
        """
        Create a new email account that has been validated.

        This is a convenience method that creates the account and immediately
        marks it as validated with the discovered capabilities.

        Args:
            account_data: EmailAccountCreate with account details
            capabilities: Capabilities discovered during validation

        Returns:
            Created and validated EmailAccount dataclass
        """
        # Check for duplicate email address
        existing = self.account_repository.get_by_email_address(account_data.email_address)
        if existing:
            raise ConflictError(f"Email account with address {account_data.email_address} already exists")

        # Create the account
        account = self.account_repository.create(account_data)

        # Mark as validated
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
        """
        Update email account.

        Note: If credentials are updated, the account should be re-validated
        using validate_connection() and then updated with new validation status.

        Args:
            account_id: Account ID
            account_update: Fields to update

        Returns:
            Updated EmailAccount dataclass

        Raises:
            ObjectNotFoundError: If account not found
        """
        # Verify account exists
        existing = self.account_repository.get_by_id(account_id)
        if not existing:
            raise ObjectNotFoundError(f"Email account {account_id} not found")

        # Perform update
        account = self.account_repository.update(account_id, account_update)

        logger.info(f"Updated email account {account_id}")

        return account

    def delete_account(self, account_id: int) -> EmailAccount:
        """
        Delete email account.

        Args:
            account_id: Account ID

        Returns:
            Deleted EmailAccount dataclass

        Raises:
            ObjectNotFoundError: If account not found
            ConflictError: If account has active ingestion configs
        """
        # Verify account exists
        existing = self.account_repository.get_by_id(account_id)
        if not existing:
            raise ObjectNotFoundError(f"Email account {account_id} not found")

        # TODO: Check for active ingestion configs using this account
        # For now, cascade delete will handle ingestion configs

        # Delete account
        account = self.account_repository.delete(account_id)

        logger.info(f"Deleted email account {account_id}: {account.email_address}")

        return account

    def mark_account_invalid(
        self,
        account_id: int,
        error_message: str,
    ) -> EmailAccount:
        """
        Mark an account as invalid due to authentication failure.

        Called internally when operations fail due to auth errors.

        Args:
            account_id: Account ID
            error_message: Description of the error

        Returns:
            Updated EmailAccount dataclass
        """
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
        """
        List all ingestion configs with account info.

        Args:
            order_by: Field to sort by ("name", "created_at", etc.)
            desc: Sort descending if True

        Returns:
            List of EmailIngestionConfigWithAccount dataclasses
        """
        return self.ingestion_config_repository.get_all_with_accounts(
            order_by=order_by,
            desc=desc,
        )

    def get_ingestion_config(self, config_id: int) -> EmailIngestionConfigWithAccount:
        """
        Get ingestion config by ID with account info.

        Args:
            config_id: Config ID

        Returns:
            EmailIngestionConfigWithAccount dataclass

        Raises:
            ObjectNotFoundError: If config not found
        """
        config = self.ingestion_config_repository.get_by_id_with_account(config_id)

        if not config:
            raise ObjectNotFoundError(f"Ingestion config {config_id} not found")

        return config

    def validate_ingestion_config(
        self,
        account_id: int,
        folder_name: str,
    ) -> bool:
        """
        Validate that an ingestion config can be created.

        Checks:
        1. Account exists and is validated
        2. Folder is accessible on the account

        Args:
            account_id: Account ID to use
            folder_name: Folder to monitor

        Returns:
            True if valid

        Raises:
            ObjectNotFoundError: If account not found
            ValidationError: If account not validated or folder not accessible
        """
        # Check account exists
        account = self.account_repository.get_by_id(account_id)
        if not account:
            raise ObjectNotFoundError(f"Email account {account_id} not found")

        # Check account is validated
        if not account.is_validated:
            raise ValidationError(
                f"Email account {account_id} is not validated. "
                "Please validate the account first."
            )

        # TODO: Check folder is accessible by connecting and listing folders
        # For now, we trust the folder name is valid

        logger.info(f"Validated ingestion config for account {account_id}, folder {folder_name}")
        return True

    def create_ingestion_config(
        self,
        config_data: EmailIngestionConfigCreate,
    ) -> EmailIngestionConfig:
        """
        Create a new ingestion config.

        The config is created in inactive state. Use activate_ingestion_config()
        to start monitoring.

        Args:
            config_data: EmailIngestionConfigCreate with config details

        Returns:
            Created EmailIngestionConfig dataclass

        Raises:
            ObjectNotFoundError: If account not found
            ValidationError: If account not validated
        """
        # Validate the config can be created
        self.validate_ingestion_config(
            account_id=config_data.account_id,
            folder_name=config_data.folder_name,
        )

        # Create the config
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
        """
        Update ingestion config.

        Note: Cannot update an active config. Deactivate first.

        Args:
            config_id: Config ID
            config_update: Fields to update

        Returns:
            Updated EmailIngestionConfig dataclass

        Raises:
            ObjectNotFoundError: If config not found
            ConflictError: If config is active
        """
        # Get existing config
        existing = self.ingestion_config_repository.get_by_id(config_id)
        if not existing:
            raise ObjectNotFoundError(f"Ingestion config {config_id} not found")

        # Cannot update active config
        if existing.is_active:
            raise ConflictError(
                f"Cannot update active ingestion config {config_id}. "
                "Deactivate it first."
            )

        # Perform update
        config = self.ingestion_config_repository.update(config_id, config_update)

        logger.info(f"Updated ingestion config {config_id}")

        return config

    def delete_ingestion_config(self, config_id: int) -> EmailIngestionConfig:
        """
        Delete ingestion config.

        Note: Cannot delete an active config. Deactivate first.

        Args:
            config_id: Config ID

        Returns:
            Deleted EmailIngestionConfig dataclass

        Raises:
            ObjectNotFoundError: If config not found
            ConflictError: If config is active
        """
        # Get existing config
        existing = self.ingestion_config_repository.get_by_id(config_id)
        if not existing:
            raise ObjectNotFoundError(f"Ingestion config {config_id} not found")

        # Cannot delete active config
        if existing.is_active:
            raise ConflictError(
                f"Cannot delete active ingestion config {config_id}. "
                "Deactivate it first."
            )

        # Delete config
        config = self.ingestion_config_repository.delete(config_id)

        logger.info(f"Deleted ingestion config {config_id}")

        return config

    def get_ingestion_configs_for_account(
        self,
        account_id: int,
    ) -> list[EmailIngestionConfig]:
        """
        Get all ingestion configs for a specific account.

        Args:
            account_id: Account ID

        Returns:
            List of EmailIngestionConfig dataclasses
        """
        return self.ingestion_config_repository.get_by_account_id(account_id)
