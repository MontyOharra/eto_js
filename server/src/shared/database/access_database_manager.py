"""
Access Database Manager
Provides unified access to Access database connections (excludes main SQL Server database)
"""
from __future__ import annotations

import logging

from shared.database.access_connection import AccessConnectionManager

logger = logging.getLogger(__name__)


class AccessDatabaseManager:
    """
    Provides unified access to Microsoft Access database connections.

    This manager wraps AccessConnectionManager instances and excludes the meta/system
    database ('main') which is SQL Server and stores ETO system data.
    """

    def __init__(self, connection_managers: dict[str, AccessConnectionManager]) -> None:
        """
        Initialize Access database manager with Access database connection managers.

        Args:
            connection_managers: Dictionary mapping database names to AccessConnectionManager instances.
                                Should NOT include 'main' (SQL Server system database).
                                e.g., {'htc_300': manager1, 'htc_000': manager2}

        Raises:
            ValueError: If 'main' database is included (should be excluded)
        """
        if 'main' in connection_managers:
            raise ValueError(
                "AccessDatabaseManager should not include 'main' database. "
                "The 'main' database is SQL Server for ETO system metadata and should "
                "only be accessed via repositories, not pipeline modules."
            )

        self.connection_managers = connection_managers
        logger.info(
            f"AccessDatabaseManager initialized with {len(connection_managers)} "
            f"Access database(s): {', '.join(connection_managers.keys())}"
        )

    def get_connection(self, database_name: str) -> AccessConnectionManager:
        """
        Get an Access database connection by name.

        Args:
            database_name: Name of the Access database (e.g., "htc_300", "htc_000")

        Returns:
            AccessConnectionManager instance - use .cursor() context manager for queries

        Raises:
            ValueError: If database connection not found
        """
        if database_name not in self.connection_managers:
            available = list(self.connection_managers.keys())
            raise ValueError(
                f"Unknown Access database: '{database_name}'. "
                f"Available databases: {available}"
            )

        logger.debug(f"Retrieved Access database connection: {database_name}")
        return self.connection_managers[database_name]

    def list_databases(self) -> list[str]:
        """
        List all available Access database connection names.

        Returns:
            List of Access database connection names
        """
        return list(self.connection_managers.keys())
