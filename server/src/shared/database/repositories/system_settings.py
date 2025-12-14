"""
System Settings Repository
Repository for system_settings table with key-value operations
"""
import logging
from datetime import datetime, timezone
from typing import Optional, Type

from sqlalchemy import select

from shared.database.repositories.base import BaseRepository
from shared.database.models import SystemSettingModel

logger = logging.getLogger(__name__)


class SystemSettingsRepository(BaseRepository[SystemSettingModel]):
    """
    Repository for system settings key-value operations.

    Provides simple get/set operations for application-wide settings.
    Values are stored as strings (JSON-serialized for complex types).
    """

    @property
    def model_class(self) -> Type[SystemSettingModel]:
        """Return the SQLAlchemy model class this repository manages"""
        return SystemSettingModel

    def get(self, key: str) -> Optional[str]:
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

    def set(self, key: str, value: Optional[str]) -> None:
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

    def get_all(self) -> dict[str, Optional[str]]:
        """
        Get all settings as a dictionary.

        Returns:
            Dictionary of key -> value for all settings
        """
        with self._get_session() as session:
            stmt = select(SystemSettingModel)
            results = session.execute(stmt).scalars().all()

            return {setting.key: setting.value for setting in results}

    def get_by_prefix(self, prefix: str) -> dict[str, Optional[str]]:
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
