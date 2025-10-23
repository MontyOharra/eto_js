"""
Email Configuration Repository
Repository for email_configs table with CRUD operations
"""
import json
import logging
from datetime import datetime, timezone
from typing import Type

from shared.database.repositories.base import BaseRepository
from shared.database.models import EmailConfigModel
from shared.types.email_configs import (
    EmailConfig,
    EmailConfigSummary,
    EmailConfigCreate,
    EmailConfigUpdate,
    FilterRule,
)
from shared.exceptions import ObjectNotFoundError

logger = logging.getLogger(__name__)


class EmailConfigRepository(BaseRepository[EmailConfigModel]):
    """
    Repository for email configuration CRUD operations.

    Supports dual-mode operation:
    - Standalone: Pass connection_manager, auto-commits
    - UoW: Pass session, caller controls transaction
    """

    @property
    def model_class(self) -> Type[EmailConfigModel]:
        """Return the SQLAlchemy model class this repository manages"""
        return EmailConfigModel

    # ========== Helper Methods ==========

    def _filter_rules_to_json(self, filter_rules: list[FilterRule]) -> str:
        """Convert list of FilterRule dataclasses to JSON string for database storage"""
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
                case_sensitive=rule["case_sensitive"],
            )
            for rule in rules_dicts
        ]

    def _model_to_dataclass(self, model: EmailConfigModel) -> EmailConfig:
        """Convert ORM model to EmailConfig dataclass"""
        return EmailConfig(
            id=model.id,
            name=model.name,
            description=model.description,
            email_address=model.email_address,
            folder_name=model.folder_name,
            filter_rules=self._filter_rules_from_json(model.filter_rules),
            poll_interval_seconds=model.poll_interval_seconds,
            max_backlog_hours=model.max_backlog_hours,
            error_retry_attempts=model.error_retry_attempts,
            is_active=model.is_active,
            activated_at=model.activated_at,
            last_check_time=model.last_check_time,
            last_error_message=model.last_error_message,
            last_error_at=model.last_error_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _model_to_summary(self, model: EmailConfigModel) -> EmailConfigSummary:
        """Convert ORM model to EmailConfigSummary dataclass"""
        return EmailConfigSummary(
            id=model.id,
            name=model.name,
            is_active=model.is_active,
            last_check_time=model.last_check_time,
        )

    # ========== Public Repository Methods ==========

    def get_all_summaries(
        self,
        order_by: str = "name",
        desc: bool = False
    ) -> list[EmailConfigSummary]:
        """
        Get all email configurations as summary objects.

        Args:
            order_by: Field to order by (name, id, last_check_time)
            desc: Sort descending if True

        Returns:
            List of EmailConfigSummary dataclasses
        """
        with self._get_session() as session:
            # Build query
            query = session.query(self.model_class)

            # Apply ordering
            if hasattr(self.model_class, order_by):
                order_column = getattr(self.model_class, order_by)
                if desc:
                    query = query.order_by(order_column.desc())
                else:
                    query = query.order_by(order_column)
            else:
                logger.warning(f"Field '{order_by}' does not exist on {self.model_class.__name__}, using default")
                query = query.order_by(self.model_class.name)

            # Execute and convert
            models = query.all()
            return [self._model_to_summary(model) for model in models]

    def get_by_id(self, config_id: int) -> EmailConfig | None:
        """
        Get email configuration by ID.

        Args:
            config_id: Configuration ID

        Returns:
            EmailConfig dataclass or None if not found
        """
        with self._get_session() as session:
            model = session.get(self.model_class, config_id)

            if model is None:
                return None

            return self._model_to_dataclass(model)

    def create(self, config_data: EmailConfigCreate) -> EmailConfig:
        """
        Create new email configuration.

        Args:
            config_data: EmailConfigCreate dataclass with configuration data

        Returns:
            Created EmailConfig dataclass
        """
        with self._get_session() as session:
            # Create ORM model
            model = self.model_class(
                name=config_data.name,
                description=config_data.description,
                email_address=config_data.email_address,
                folder_name=config_data.folder_name,
                filter_rules=self._filter_rules_to_json(config_data.filter_rules),
                poll_interval_seconds=config_data.poll_interval_seconds,
                max_backlog_hours=config_data.max_backlog_hours,
                error_retry_attempts=config_data.error_retry_attempts,
                is_active=False,  # Always start inactive
                activated_at=None,
                is_running=False,
                last_check_time=None,
                last_error_message=None,
                last_error_at=None,
            )

            session.add(model)
            session.flush()  # Get ID assigned

            logger.info(f"Created email config {model.id}: {config_data.name}")

            return self._model_to_dataclass(model)

    def update(
        self,
        config_id: int,
        config_update: EmailConfigUpdate
    ) -> EmailConfig:
        """
        Update email configuration.

        Args:
            config_id: Configuration ID
            config_update: EmailConfigUpdate dataclass with fields to update

        Returns:
            Updated EmailConfig dataclass

        Raises:
            ObjectNotFoundError: If config not found
        """
        with self._get_session() as session:
            # Get existing config
            model = session.get(self.model_class, config_id)

            if model is None:
                raise ObjectNotFoundError(f"Configuration {config_id} not found")

            # Update only provided fields
            if config_update.description is not None:
                model.description = config_update.description

            if config_update.filter_rules is not None:
                model.filter_rules = self._filter_rules_to_json(config_update.filter_rules)

            if config_update.poll_interval_seconds is not None:
                model.poll_interval_seconds = config_update.poll_interval_seconds

            if config_update.max_backlog_hours is not None:
                model.max_backlog_hours = config_update.max_backlog_hours

            if config_update.error_retry_attempts is not None:
                model.error_retry_attempts = config_update.error_retry_attempts

            if config_update.is_active is not None:
                model.is_active = config_update.is_active

            if config_update.activated_at is not None:
                model.activated_at = config_update.activated_at

            if config_update.last_check_time is not None:
                model.last_check_time = config_update.last_check_time

            if config_update.last_error_message is not None:
                model.last_error_message = config_update.last_error_message

            if config_update.last_error_at is not None:
                model.last_error_at = config_update.last_error_at

            session.flush()

            logger.info(f"Updated email config {config_id}")

            return self._model_to_dataclass(model)

    def delete(self, config_id: int) -> None:
        """
        Delete email configuration.

        Args:
            config_id: Configuration ID

        Raises:
            ObjectNotFoundError: If config not found
        """
        with self._get_session() as session:
            # Get existing config
            model = session.get(self.model_class, config_id)

            if model is None:
                raise ObjectNotFoundError(f"Configuration {config_id} not found")

            session.delete(model)
            session.flush()

            logger.info(f"Deleted email config {config_id}")
