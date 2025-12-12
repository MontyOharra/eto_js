"""
Email Account Repository
Repository for email_accounts table with CRUD operations
"""
import json
import logging
from datetime import datetime, timezone
from typing import Type

from shared.database.repositories.base import BaseRepository
from shared.database.models import EmailAccountModel
from shared.types.email_accounts import (
    EmailAccount,
    EmailAccountSummary,
    EmailAccountCreate,
    EmailAccountUpdate,
    ProviderSettings,
    StandardProviderSettings,
    Credentials,
    PasswordCredentials,
    OAuthCredentials,
)
from shared.exceptions.service import ObjectNotFoundError

logger = logging.getLogger(__name__)


class EmailAccountRepository(BaseRepository[EmailAccountModel]):
    """
    Repository for email account CRUD operations.

    Handles storage and retrieval of email account credentials.
    Credentials are stored as JSON (to be encrypted in future).

    Supports dual-mode operation:
    - Standalone: Pass connection_manager, auto-commits
    - UoW: Pass session, caller controls transaction
    """

    @property
    def model_class(self) -> Type[EmailAccountModel]:
        """Return the SQLAlchemy model class this repository manages"""
        return EmailAccountModel

    # ========== Helper Methods ==========

    def _provider_settings_to_json(self, settings: ProviderSettings) -> str:
        """Convert provider settings dataclass to JSON string"""
        settings_dict = {
            'type': type(settings).__name__,
            'data': {k: v for k, v in settings.__dict__.items()}
        }
        return json.dumps(settings_dict)

    def _provider_settings_from_json(self, settings_json: str, provider_type: str) -> ProviderSettings:
        """Convert JSON string to provider settings dataclass"""
        settings_dict = json.loads(settings_json)
        data = settings_dict.get('data', settings_dict)  # Handle both formats

        if provider_type == 'standard':
            return StandardProviderSettings(**data)

        # Default fallback
        return StandardProviderSettings(**data)

    def _credentials_to_json(self, credentials: Credentials) -> str:
        """Convert credentials dataclass to JSON string"""
        creds_dict = {
            'type': type(credentials).__name__,
            'data': {}
        }

        if isinstance(credentials, PasswordCredentials):
            creds_dict['data'] = {'password': credentials.password}
        elif isinstance(credentials, OAuthCredentials):
            creds_dict['data'] = {
                'access_token': credentials.access_token,
                'refresh_token': credentials.refresh_token,
                'token_expiry': credentials.token_expiry.isoformat() if credentials.token_expiry else None,
            }

        return json.dumps(creds_dict)

    def _credentials_from_json(self, credentials_json: str) -> Credentials:
        """Convert JSON string to credentials dataclass"""
        creds_dict = json.loads(credentials_json)
        creds_type = creds_dict.get('type', 'PasswordCredentials')
        data = creds_dict.get('data', creds_dict)

        if creds_type == 'OAuthCredentials':
            token_expiry = None
            if data.get('token_expiry'):
                token_expiry = datetime.fromisoformat(data['token_expiry'])
            return OAuthCredentials(
                access_token=data['access_token'],
                refresh_token=data.get('refresh_token'),
                token_expiry=token_expiry,
            )
        else:
            # Default to password credentials
            return PasswordCredentials(password=data.get('password', ''))

    def _capabilities_to_json(self, capabilities: list[str] | None) -> str | None:
        """Convert capabilities list to JSON string"""
        if not capabilities:
            return None
        return json.dumps(capabilities)

    def _capabilities_from_json(self, capabilities_json: str | None) -> list[str]:
        """Convert JSON string to capabilities list"""
        if not capabilities_json:
            return []
        return json.loads(capabilities_json)

    def _model_to_dataclass(self, model: EmailAccountModel) -> EmailAccount:
        """Convert ORM model to EmailAccount dataclass"""
        return EmailAccount(
            id=model.id,
            name=model.name,
            description=model.description,
            provider_type=model.provider_type,
            email_address=model.email_address,
            provider_settings=self._provider_settings_from_json(model.provider_settings, model.provider_type),
            credentials=self._credentials_from_json(model.credentials),
            is_validated=model.is_validated,
            validated_at=model.validated_at,
            capabilities=self._capabilities_from_json(model.capabilities),
            last_error_message=model.last_error_message,
            last_error_at=model.last_error_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _model_to_summary(self, model: EmailAccountModel) -> EmailAccountSummary:
        """Convert ORM model to EmailAccountSummary dataclass (no credentials)"""
        return EmailAccountSummary(
            id=model.id,
            name=model.name,
            email_address=model.email_address,
            provider_type=model.provider_type,
            is_validated=model.is_validated,
            capabilities=self._capabilities_from_json(model.capabilities),
        )

    # ========== Public Repository Methods ==========

    def get_all_summaries(
        self,
        order_by: str = "name",
        desc: bool = False,
        validated_only: bool = False
    ) -> list[EmailAccountSummary]:
        """
        Get all email accounts as summary objects (no credentials).

        Args:
            order_by: Field to order by (name, email_address, created_at)
            desc: Sort descending if True
            validated_only: Only return validated accounts

        Returns:
            List of EmailAccountSummary dataclasses
        """
        with self._get_session() as session:
            query = session.query(self.model_class)

            # Filter by validation status if requested
            if validated_only:
                query = query.filter(self.model_class.is_validated == True)

            # Apply ordering
            if hasattr(self.model_class, order_by):
                order_column = getattr(self.model_class, order_by)
                if desc:
                    query = query.order_by(order_column.desc())
                else:
                    query = query.order_by(order_column)
            else:
                query = query.order_by(self.model_class.name)

            models = query.all()
            return [self._model_to_summary(model) for model in models]

    def get_by_id(self, account_id: int) -> EmailAccount | None:
        """
        Get email account by ID (includes credentials).

        Args:
            account_id: Account ID

        Returns:
            EmailAccount dataclass or None if not found
        """
        with self._get_session() as session:
            model = session.get(self.model_class, account_id)

            if model is None:
                return None

            return self._model_to_dataclass(model)

    def get_by_email_address(self, email_address: str) -> EmailAccount | None:
        """
        Get email account by email address.

        Args:
            email_address: Email address to look up

        Returns:
            EmailAccount dataclass or None if not found
        """
        with self._get_session() as session:
            model = session.query(self.model_class).filter(
                self.model_class.email_address == email_address
            ).first()

            if model is None:
                return None

            return self._model_to_dataclass(model)

    def create(self, account_data: EmailAccountCreate) -> EmailAccount:
        """
        Create new email account.

        Args:
            account_data: EmailAccountCreate dataclass with account data

        Returns:
            Created EmailAccount dataclass
        """
        with self._get_session() as session:
            model = self.model_class(
                name=account_data.name,
                description=account_data.description,
                provider_type=account_data.provider_type,
                email_address=account_data.email_address,
                provider_settings=self._provider_settings_to_json(account_data.provider_settings),
                credentials=self._credentials_to_json(account_data.credentials),
                is_validated=False,
                validated_at=None,
                capabilities=None,
                last_error_message=None,
                last_error_at=None,
            )

            session.add(model)
            session.flush()

            logger.info(f"Created email account {model.id}: {account_data.name} ({account_data.email_address})")

            return self._model_to_dataclass(model)

    def update(self, account_id: int, account_update: EmailAccountUpdate) -> EmailAccount:
        """
        Update email account.

        Args:
            account_id: Account ID
            account_update: EmailAccountUpdate dataclass with fields to update

        Returns:
            Updated EmailAccount dataclass

        Raises:
            ObjectNotFoundError: If account not found
        """
        with self._get_session() as session:
            model = session.get(self.model_class, account_id)

            if model is None:
                raise ObjectNotFoundError(f"Email account {account_id} not found")

            # Update only provided fields
            if account_update.name is not None:
                model.name = account_update.name

            if account_update.description is not None:
                model.description = account_update.description

            if account_update.provider_settings is not None:
                model.provider_settings = self._provider_settings_to_json(account_update.provider_settings)

            if account_update.credentials is not None:
                model.credentials = self._credentials_to_json(account_update.credentials)

            if account_update.is_validated is not None:
                model.is_validated = account_update.is_validated

            if account_update.validated_at is not None:
                model.validated_at = account_update.validated_at

            if account_update.capabilities is not None:
                model.capabilities = self._capabilities_to_json(account_update.capabilities)

            if account_update.clear_errors:
                model.last_error_message = None
                model.last_error_at = None
            else:
                if account_update.last_error_message is not None:
                    model.last_error_message = account_update.last_error_message
                if account_update.last_error_at is not None:
                    model.last_error_at = account_update.last_error_at

            session.flush()

            logger.debug(f"Updated email account {account_id}")

            return self._model_to_dataclass(model)

    def delete(self, account_id: int) -> EmailAccount:
        """
        Delete email account.

        Note: This will cascade delete all related ingestion configs.

        Args:
            account_id: Account ID

        Returns:
            Deleted EmailAccount dataclass

        Raises:
            ObjectNotFoundError: If account not found
        """
        with self._get_session() as session:
            model = session.get(self.model_class, account_id)

            if model is None:
                raise ObjectNotFoundError(f"Email account {account_id} not found")

            # Store dataclass before deletion
            result = self._model_to_dataclass(model)

            session.delete(model)
            session.flush()

            logger.info(f"Deleted email account {account_id}")

            return result
