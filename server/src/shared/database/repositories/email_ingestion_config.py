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
        """Convert list of FilterRule dataclasses to JSON string"""
        if not filter_rules:
            return "[]"

        rules_dicts = [
            {
                "field": rule.field,
                "operation": rule.operation,
                "value": rule.value,
                "case_sensitive": rule.case_sensitive,
            }
            for rule in filter_rules
        ]
        return json.dumps(rules_dicts)

    def _filter_rules_from_json(self, filter_rules_json: str | None) -> list[FilterRule]:
        """Convert JSON string from database to list of FilterRule dataclasses"""
        if not filter_rules_json:
            return []

        rules_dicts = json.loads(filter_rules_json)
        return [
            FilterRule(
                field=rule["field"],
                operation=rule["operation"],
                value=rule["value"],
                case_sensitive=rule.get("case_sensitive", False),
            )
            for rule in rules_dicts
        ]

    def _model_to_dataclass(self, model: EmailIngestionConfigModel) -> EmailIngestionConfig:
        """Convert ORM model to EmailIngestionConfig dataclass"""
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
        """Convert ORM model to EmailIngestionConfigSummary dataclass"""
        return EmailIngestionConfigSummary(
            id=model.id,
            name=model.name,
            account_id=model.account_id,
            folder_name=model.folder_name,
            is_active=model.is_active,
            last_check_time=model.last_check_time,
        )

    def _model_to_with_account(self, model: EmailIngestionConfigModel) -> EmailIngestionConfigWithAccount:
        """Convert ORM model to EmailIngestionConfigWithAccount dataclass"""
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
            List of EmailIngestionConfigSummary dataclasses
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
            List of EmailIngestionConfigWithAccount dataclasses
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
            List of active EmailIngestionConfig dataclasses
        """
        with self._get_session() as session:
            models = session.query(self.model_class).filter(
                self.model_class.is_active == True
            ).all()

            return [self._model_to_dataclass(model) for model in models]

    def get_by_account_id(self, account_id: int) -> list[EmailIngestionConfig]:
        """
        Get all ingestion configs for a specific account.

        Args:
            account_id: Account ID

        Returns:
            List of EmailIngestionConfig dataclasses
        """
        with self._get_session() as session:
            models = session.query(self.model_class).filter(
                self.model_class.account_id == account_id
            ).all()

            return [self._model_to_dataclass(model) for model in models]

    def get_by_id(self, config_id: int) -> EmailIngestionConfig | None:
        """
        Get ingestion config by ID.

        Args:
            config_id: Config ID

        Returns:
            EmailIngestionConfig dataclass or None if not found
        """
        with self._get_session() as session:
            model = session.get(self.model_class, config_id)

            if model is None:
                return None

            return self._model_to_dataclass(model)

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
            config_data: EmailIngestionConfigCreate dataclass

        Returns:
            Created EmailIngestionConfig dataclass
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

            return self._model_to_dataclass(model)

    def update(self, config_id: int, config_update: EmailIngestionConfigUpdate) -> EmailIngestionConfig:
        """
        Update ingestion config.

        Args:
            config_id: Config ID
            config_update: EmailIngestionConfigUpdate dataclass

        Returns:
            Updated EmailIngestionConfig dataclass

        Raises:
            ObjectNotFoundError: If config not found
        """
        with self._get_session() as session:
            model = session.get(self.model_class, config_id)

            if model is None:
                raise ObjectNotFoundError(f"Ingestion config {config_id} not found")

            # Update only provided fields
            if config_update.name is not None:
                model.name = config_update.name

            if config_update.description is not None:
                model.description = config_update.description

            if config_update.folder_name is not None:
                model.folder_name = config_update.folder_name

            if config_update.filter_rules is not None:
                model.filter_rules = self._filter_rules_to_json(config_update.filter_rules)

            if config_update.poll_interval_seconds is not None:
                model.poll_interval_seconds = config_update.poll_interval_seconds

            if config_update.use_idle is not None:
                model.use_idle = config_update.use_idle

            if config_update.is_active is not None:
                model.is_active = config_update.is_active

            if config_update.activated_at is not None:
                model.activated_at = config_update.activated_at

            if config_update.last_check_time is not None:
                model.last_check_time = config_update.last_check_time

            if config_update.reset_last_processed_uid:
                model.last_processed_uid = None
            elif config_update.last_processed_uid is not None:
                model.last_processed_uid = config_update.last_processed_uid

            if config_update.clear_errors:
                model.last_error_message = None
                model.last_error_at = None
            else:
                if config_update.last_error_message is not None:
                    model.last_error_message = config_update.last_error_message
                if config_update.last_error_at is not None:
                    model.last_error_at = config_update.last_error_at

            session.flush()

            logger.debug(f"Updated ingestion config {config_id}")

            return self._model_to_dataclass(model)

    def delete(self, config_id: int) -> EmailIngestionConfig:
        """
        Delete ingestion config.

        Args:
            config_id: Config ID

        Returns:
            Deleted EmailIngestionConfig dataclass

        Raises:
            ObjectNotFoundError: If config not found
        """
        with self._get_session() as session:
            model = session.get(self.model_class, config_id)

            if model is None:
                raise ObjectNotFoundError(f"Ingestion config {config_id} not found")

            result = self._model_to_dataclass(model)

            session.delete(model)
            session.flush()

            logger.info(f"Deleted ingestion config {config_id}")

            return result
