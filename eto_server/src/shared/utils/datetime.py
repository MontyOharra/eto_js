"""
DateTime utilities for consistent timezone-aware handling throughout the application
All datetime operations should use timezone-aware UTC for consistency
"""
from datetime import datetime, timezone
from typing import Optional


class DateTimeUtils:
    """Centralized datetime utilities for timezone-aware operations"""

    @staticmethod
    def utc_now() -> datetime:
        """
        Get current time as timezone-aware UTC

        Returns:
            Current datetime in UTC with timezone info
        """
        return datetime.now(timezone.utc)

    @staticmethod
    def ensure_utc_aware(dt: Optional[datetime]) -> Optional[datetime]:
        """
        Ensure datetime is timezone-aware UTC

        Args:
            dt: Datetime that may be naive or aware

        Returns:
            Timezone-aware UTC datetime, or None if input was None
        """
        if dt is None:
            return None

        if dt.tzinfo is None:
            # Assume naive datetimes are UTC (common from database)
            return dt.replace(tzinfo=timezone.utc)

        # Convert to UTC if different timezone
        return dt.astimezone(timezone.utc)

    @staticmethod
    def for_database(dt: Optional[datetime]) -> Optional[datetime]:
        """
        Convert timezone-aware datetime to naive UTC for SQL Server storage
        SQL Server DATETIME2 columns store naive datetimes, so we store as naive UTC

        Args:
            dt: Timezone-aware datetime

        Returns:
            Naive UTC datetime for database storage, or None if input was None
        """
        if dt is None:
            return None

        if dt.tzinfo is None:
            return dt  # Already naive, assume UTC

        # Convert to UTC and remove timezone info for database storage
        return dt.astimezone(timezone.utc).replace(tzinfo=None)