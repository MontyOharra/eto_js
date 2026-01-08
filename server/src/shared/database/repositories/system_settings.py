"""
System Settings Repository
Repository for system_settings table with key-value operations

Note: This repository does not extend BaseRepository because SystemSettingModel
uses 'key' as its primary key instead of 'id'. It handles its own session management.
"""
import logging
from contextlib import contextmanager
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from shared.database.connection import DatabaseConnectionManager
from shared.database.models import SystemSettingModel

logger = logging.getLogger(__name__)


class SystemSettingsRepository:
    """
    Repository for system settings key-value operations.

    Provides simple get/set operations for application-wide settings.
    Values are stored as strings (JSON-serialized for complex types).

    Note: Does not extend BaseRepository since SystemSettingModel uses
    'key' as primary key instead of 'id'.
    """

    def __init__(
        self,
        session: Session | None = None,
        connection_manager: DatabaseConnectionManager | None = None
    ):
        """
        Initialize repository.

        Args:
            session: If provided, use this session (we're in a UoW transaction)
            connection_manager: If no session, use this to create sessions per operation

        Raises:
            ValueError: If neither or both parameters are provided
        """
        if session is None and connection_manager is None:
            raise ValueError("Must provide either session or connection_manager")

        if session is not None and connection_manager is not None:
            raise ValueError("Provide either session OR connection_manager, not both")

        self.session = session
        self.connection_manager = connection_manager

    @contextmanager
    def _get_session(self):
        """
        Get session for an operation.

        If we have a session (in UoW), use it without committing.
        Otherwise create a new session for this operation and commit after.
        """
        if self.session:
            yield self.session
        else:
            assert self.connection_manager is not None
            with self.connection_manager.session() as session:
                yield session

    def get(self, key: str) -> str | None:
        """
        Get a setting value by key.

        Args:
            key: Setting key (e.g., "email.default_sender_account_id")

        Returns:
            Setting value as string, or None if not set
        """
        with self._get_session() as session:
            stmt = select(SystemSettingModel).where(SystemSettingModel.key == key)
            result = session.execute(stmt).scalar_one_or_none()

            if result is None:
                return None

            return result.value

    def set(self, key: str, value: str | None) -> None:
        """
        Set a setting value by key.

        Creates the setting if it doesn't exist, updates if it does.

        Args:
            key: Setting key (e.g., "email.default_sender_account_id")
            value: Setting value as string (or None to clear)
        """
        with self._get_session() as session:
            stmt = select(SystemSettingModel).where(SystemSettingModel.key == key)
            existing = session.execute(stmt).scalar_one_or_none()

            if existing is not None:
                existing.value = value
                existing.updated_at = datetime.now(timezone.utc)
                logger.info(f"Updated system setting: {key}")
            else:
                setting = SystemSettingModel(
                    key=key,
                    value=value,
                )
                session.add(setting)
                logger.info(f"Created system setting: {key}")

    def delete(self, key: str) -> bool:
        """
        Delete a setting by key.

        Args:
            key: Setting key to delete

        Returns:
            True if setting was deleted, False if it didn't exist
        """
        with self._get_session() as session:
            stmt = select(SystemSettingModel).where(SystemSettingModel.key == key)
            existing = session.execute(stmt).scalar_one_or_none()

            if existing is not None:
                session.delete(existing)
                logger.info(f"Deleted system setting: {key}")
                return True

            return False

    def get_all(self) -> dict[str, str | None]:
        """
        Get all settings as a dictionary.

        Returns:
            Dictionary of key -> value for all settings
        """
        with self._get_session() as session:
            stmt = select(SystemSettingModel)
            results = session.execute(stmt).scalars().all()

            return {setting.key: setting.value for setting in results}

    def get_by_prefix(self, prefix: str) -> dict[str, str | None]:
        """
        Get all settings with keys starting with a prefix.

        Args:
            prefix: Key prefix (e.g., "email." to get all email settings)

        Returns:
            Dictionary of key -> value for matching settings
        """
        with self._get_session() as session:
            stmt = select(SystemSettingModel).where(
                SystemSettingModel.key.like(f"{prefix}%")
            )
            results = session.execute(stmt).scalars().all()

            return {setting.key: setting.value for setting in results}
