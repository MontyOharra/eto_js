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
    ProviderType,
    ProviderSettings,
    StandardProviderSettings,
    Credentials,
    PasswordCredentials,
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
        """Convert provider settings model to JSON string"""
        settings_dict = {
            'type': type(settings).__name__,
            'data': settings.model_dump()
        }
        return json.dumps(settings_dict)

    def _provider_settings_from_json(self, settings_json: str, provider_type: ProviderType) -> ProviderSettings:
        """Convert JSON string to provider settings model"""
        settings_dict = json.loads(settings_json)
        data = settings_dict.get('data', settings_dict)  # Handle both formats

        if provider_type == 'standard':
            return StandardProviderSettings(**data)

    def _credentials_to_json(self, credentials: Credentials) -> str:
        """Convert credentials model to JSON string"""
        creds_dict = {
            'type': type(credentials).__name__,
            'data': credentials.model_dump()
        }
        return json.dumps(creds_dict)

    def _credentials_from_json(self, credentials_json: str) -> Credentials:
        """Convert JSON string to credentials model"""
        creds_dict = json.loads(credentials_json)
        data = creds_dict.get('data', creds_dict)
        return PasswordCredentials(**data)

    def _model_to_domain(self, model: EmailAccountModel) -> EmailAccount:
        """Convert ORM model to EmailAccount domain model"""
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
            last_error_message=model.last_error_message,
            last_error_at=model.last_error_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _model_to_summary(self, model: EmailAccountModel) -> EmailAccountSummary:
        """Convert ORM model to EmailAccountSummary (no credentials)"""
        return EmailAccountSummary(
            id=model.id,
            name=model.name,
            email_address=model.email_address,
            provider_type=model.provider_type,
            is_validated=model.is_validated,
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
            List of EmailAccountSummary
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
            EmailAccount or None if not found
        """
        with self._get_session() as session:
            model = session.get(self.model_class, account_id)

            if model is None:
                return None

            return self._model_to_domain(model)

    def get_by_email_address(self, email_address: str) -> EmailAccount | None:
        """
        Get email account by email address.

        Args:
            email_address: Email address to look up

        Returns:
            EmailAccount or None if not found
        """
        with self._get_session() as session:
            model = session.query(self.model_class).filter(
                self.model_class.email_address == email_address
            ).first()

            if model is None:
                return None

            return self._model_to_domain(model)

    def create(self, account_data: EmailAccountCreate) -> EmailAccount:
        """
        Create new email account.

        Args:
            account_data: EmailAccountCreate with account data

        Returns:
            Created EmailAccount
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
                last_error_message=None,
                last_error_at=None,
            )

            session.add(model)
            session.flush()

            logger.info(f"Created email account {model.id}: {account_data.name} ({account_data.email_address})")

            return self._model_to_domain(model)

    def update(self, account_id: int, account_update: EmailAccountUpdate) -> EmailAccount:
        """
        Update email account.

        Only fields explicitly set on the update model are updated.
        Uses Pydantic's model_fields_set to distinguish between:
        - Field not provided (not in model_fields_set): unchanged
        - Field set to None: set to NULL in database
        - Field set to value: updated to that value

        Args:
            account_id: Account ID
            account_update: EmailAccountUpdate with fields to update

        Returns:
            Updated EmailAccount

        Raises:
            ObjectNotFoundError: If account not found
        """
        with self._get_session() as session:
            model = session.get(self.model_class, account_id)

            if model is None:
                raise ObjectNotFoundError(f"Email account {account_id} not found")

            # Update only fields that were explicitly set
            for field_name in account_update.model_fields_set:
                value = getattr(account_update, field_name)

                # Handle serialization for JSON fields
                if field_name == 'provider_settings' and value is not None:
                    value = self._provider_settings_to_json(value)
                elif field_name == 'credentials' and value is not None:
                    value = self._credentials_to_json(value)

                setattr(model, field_name, value)

            session.flush()

            logger.debug(f"Updated email account {account_id}")

            return self._model_to_domain(model)

    def delete(self, account_id: int) -> EmailAccount:
        """
        Delete email account.

        Note: This will cascade delete all related ingestion configs.

        Args:
            account_id: Account ID

        Returns:
            Deleted EmailAccount

        Raises:
            ObjectNotFoundError: If account not found
        """
        with self._get_session() as session:
            model = session.get(self.model_class, account_id)

            if model is None:
                raise ObjectNotFoundError(f"Email account {account_id} not found")

            # Store dataclass before deletion
            result = self._model_to_domain(model)

            session.delete(model)
            session.flush()

            logger.info(f"Deleted email account {account_id}")

            return result
