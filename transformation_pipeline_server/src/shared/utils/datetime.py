"""
DateTime utilities for consistent timezone-aware handling throughout the application
All datetime operations should use timezone-aware UTC for consistency
"""
from datetime import datetime, timezone


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
    def ensure_utc_aware(dt: datetime) -> datetime:
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
    def for_database(dt: datetime) -> datetime:
        """
        Convert timezone-aware datetime to naive UTC for SQL Server storage
        SQL Server DATETIME2 columns store naive datetimes, so we store as naive UTC

        Args:
            dt: Timezone-aware datetime

        Returns:
            Naive UTC datetime for database storage, or None if input was None
        """

        if dt.tzinfo is None:
            return dt  # Already naive, assume UTC

        # Convert to UTC and remove timezone info for database storage
        return dt.astimezone(timezone.utc).replace(tzinfo=None)

    @staticmethod
    def parse_iso_datetime(dt_string: str) -> datetime:
        """
        Parse ISO 8601 datetime string to timezone-aware UTC datetime

        Args:
            dt_string: ISO 8601 datetime string (e.g., "2024-01-15T10:30:00Z" or "2024-01-15T10:30:00+00:00")

        Returns:
            Timezone-aware UTC datetime

        Raises:
            ValueError: If the datetime string is invalid
        """
        try:
            # Handle common ISO formats
            if dt_string.endswith('Z'):
                # Remove Z and add +00:00 for consistent parsing
                dt_string = dt_string[:-1] + '+00:00'

            # Parse with timezone info
            dt = datetime.fromisoformat(dt_string)

            # Ensure UTC
            return DateTimeUtils.ensure_utc_aware(dt)

        except ValueError as e:
            raise ValueError(f"Invalid ISO datetime format: {e}")