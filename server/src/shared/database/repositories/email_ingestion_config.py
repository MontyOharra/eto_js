"""
Email Ingestion Config Repository
Repository for email_ingestion_configs table with CRUD operations
"""
import json
import logging
from datetime import datetime, timezone
from typing import Type

from sqlalchemy.orm import joinedload

from shared.database.repositories.base import BaseRepository
from shared.database.models import EmailIngestionConfigModel, EmailAccountModel
from shared.types.email_ingestion_configs import (
    EmailIngestionConfig,
    EmailIngestionConfigSummary,
    EmailIngestionConfigWithAccount,
    EmailIngestionConfigCreate,
    EmailIngestionConfigUpdate,
    FilterRule,
)
from shared.exceptions.service import ObjectNotFoundError

logger = logging.getLogger(__name__)


class EmailIngestionConfigRepository(BaseRepository[EmailIngestionConfigModel]):
    """
    Repository for email ingestion config CRUD operations.

    Handles storage and retrieval of email listener configurations.
    References email_accounts for credentials.

    Supports dual-mode operation:
    - Standalone: Pass connection_manager, auto-commits
    - UoW: Pass session, caller controls transaction
    """

    @property
    def model_class(self) -> Type[EmailIngestionConfigModel]:
        """Return the SQLAlchemy model class this repository manages"""
        return EmailIngestionConfigModel

    # ========== Helper Methods ==========

    def _filter_rules_to_json(self, filter_rules: list[FilterRule]) -> str:
        """Convert list of FilterRule models to JSON string"""
        if not filter_rules:
            return "[]"
        return json.dumps([rule.model_dump() for rule in filter_rules])

    def _filter_rules_from_json(self, filter_rules_json: str | None) -> list[FilterRule]:
        """Convert JSON string from database to list of FilterRule models"""
        if not filter_rules_json:
            return []
        rules_dicts = json.loads(filter_rules_json)
        return [FilterRule(**rule) for rule in rules_dicts]

    def _model_to_domain(self, model: EmailIngestionConfigModel) -> EmailIngestionConfig:
        """Convert ORM model to EmailIngestionConfig domain model"""
        return EmailIngestionConfig(
            id=model.id,
            name=model.name,
            description=model.description,
            account_id=model.account_id,
            folder_name=model.folder_name,
            filter_rules=self._filter_rules_from_json(model.filter_rules),
            poll_interval_seconds=model.poll_interval_seconds,
            use_idle=model.use_idle,
            is_active=model.is_active,
            activated_at=model.activated_at,
            last_check_time=model.last_check_time,
            last_processed_uid=model.last_processed_uid,
            last_error_message=model.last_error_message,
            last_error_at=model.last_error_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _model_to_summary(self, model: EmailIngestionConfigModel) -> EmailIngestionConfigSummary:
        """Convert ORM model to EmailIngestionConfigSummary"""
        return EmailIngestionConfigSummary(
            id=model.id,
            name=model.name,
            account_id=model.account_id,
            folder_name=model.folder_name,
            is_active=model.is_active,
            last_check_time=model.last_check_time,
        )

    def _model_to_with_account(self, model: EmailIngestionConfigModel) -> EmailIngestionConfigWithAccount:
        """Convert ORM model to EmailIngestionConfigWithAccount"""
        return EmailIngestionConfigWithAccount(
            id=model.id,
            name=model.name,
            description=model.description,
            account_id=model.account_id,
            account_name=model.account.name if model.account else "Unknown",
            account_email=model.account.email_address if model.account else "Unknown",
            folder_name=model.folder_name,
            is_active=model.is_active,
            last_check_time=model.last_check_time,
            last_error_message=model.last_error_message,
        )

    # ========== Public Repository Methods ==========

    def get_all_summaries(
        self,
        order_by: str = "name",
        desc: bool = False
    ) -> list[EmailIngestionConfigSummary]:
        """
        Get all ingestion configs as summary objects.

        Args:
            order_by: Field to order by (name, id, last_check_time)
            desc: Sort descending if True

        Returns:
            List of EmailIngestionConfigSummary
        """
        with self._get_session() as session:
            query = session.query(self.model_class)

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

    def get_all_with_accounts(
        self,
        order_by: str = "name",
        desc: bool = False
    ) -> list[EmailIngestionConfigWithAccount]:
        """
        Get all ingestion configs with related account info.

        Args:
            order_by: Field to order by
            desc: Sort descending if True

        Returns:
            List of EmailIngestionConfigWithAccount
        """
        with self._get_session() as session:
            query = session.query(self.model_class).options(
                joinedload(self.model_class.account)
            )

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
            return [self._model_to_with_account(model) for model in models]

    def get_active_configs(self) -> list[EmailIngestionConfig]:
        """
        Get all active ingestion configs.

        Returns:
            List of active EmailIngestionConfiges
        """
        with self._get_session() as session:
            models = session.query(self.model_class).filter(
                self.model_class.is_active == True
            ).all()

            return [self._model_to_domain(model) for model in models]

    def get_by_account_id(self, account_id: int) -> list[EmailIngestionConfig]:
        """
        Get all ingestion configs for a specific account.

        Args:
            account_id: Account ID

        Returns:
            List of EmailIngestionConfiges
        """
        with self._get_session() as session:
            models = session.query(self.model_class).filter(
                self.model_class.account_id == account_id
            ).all()

            return [self._model_to_domain(model) for model in models]

    def get_by_id(self, config_id: int) -> EmailIngestionConfig | None:
        """
        Get ingestion config by ID.

        Args:
            config_id: Config ID

        Returns:
            EmailIngestionConfig or None if not found
        """
        with self._get_session() as session:
            model = session.get(self.model_class, config_id)

            if model is None:
                return None

            return self._model_to_domain(model)

    def get_by_id_with_account(self, config_id: int) -> EmailIngestionConfigWithAccount | None:
        """
        Get ingestion config by ID with account info.

        Args:
            config_id: Config ID

        Returns:
            EmailIngestionConfigWithAccount dataclass or None if not found
        """
        with self._get_session() as session:
            model = session.query(self.model_class).options(
                joinedload(self.model_class.account)
            ).filter(
                self.model_class.id == config_id
            ).first()

            if model is None:
                return None

            return self._model_to_with_account(model)

    def create(self, config_data: EmailIngestionConfigCreate) -> EmailIngestionConfig:
        """
        Create new ingestion config.

        Args:
            config_data: EmailIngestionConfigCreate with config data

        Returns:
            Created EmailIngestionConfig
        """
        with self._get_session() as session:
            model = self.model_class(
                name=config_data.name,
                description=config_data.description,
                account_id=config_data.account_id,
                folder_name=config_data.folder_name,
                filter_rules=self._filter_rules_to_json(config_data.filter_rules),
                poll_interval_seconds=config_data.poll_interval_seconds,
                use_idle=config_data.use_idle,
                is_active=False,  # Always start inactive
                activated_at=None,
                last_check_time=None,
                last_processed_uid=None,
                last_error_message=None,
                last_error_at=None,
            )

            session.add(model)
            session.flush()

            logger.info(f"Created ingestion config {model.id}: {config_data.name}")

            return self._model_to_domain(model)

    def update(self, config_id: int, config_update: EmailIngestionConfigUpdate) -> EmailIngestionConfig:
        """
        Update ingestion config.

        Only fields explicitly set on the update model are updated.
        Uses Pydantic's model_fields_set to distinguish between:
        - Field not provided (not in model_fields_set): unchanged
        - Field set to None: set to NULL in database
        - Field set to value: updated to that value

        Args:
            config_id: Config ID
            config_update: EmailIngestionConfigUpdate with fields to update

        Returns:
            Updated EmailIngestionConfig

        Raises:
            ObjectNotFoundError: If config not found
        """
        with self._get_session() as session:
            model = session.get(self.model_class, config_id)

            if model is None:
                raise ObjectNotFoundError(f"Ingestion config {config_id} not found")

            # Update only fields that were explicitly set
            for field_name in config_update.model_fields_set:
                value = getattr(config_update, field_name)

                # Handle serialization for JSON fields
                if field_name == 'filter_rules' and value is not None:
                    value = self._filter_rules_to_json(value)

                setattr(model, field_name, value)

            session.flush()

            logger.debug(f"Updated ingestion config {config_id}")

            return self._model_to_domain(model)

    def delete(self, config_id: int) -> EmailIngestionConfig:
        """
        Delete ingestion config.

        Args:
            config_id: Config ID

        Returns:
            Deleted EmailIngestionConfig

        Raises:
            ObjectNotFoundError: If config not found
        """
        with self._get_session() as session:
            model = session.get(self.model_class, config_id)

            if model is None:
                raise ObjectNotFoundError(f"Ingestion config {config_id} not found")

            result = self._model_to_domain(model)

            session.delete(model)
            session.flush()

            logger.info(f"Deleted ingestion config {config_id}")

            return result
