"""
Data Database Manager
Provides access to business/data databases only (excludes meta/system database)
"""
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class DataDatabaseManager:
    """
    Provides access to business/data database connections ONLY.

    This manager is specifically for pipeline modules and excludes the meta/system
    database ('main') which stores ETO system data (pipelines, templates, runs, etc.).

    Separation ensures:
    - Pipeline modules cannot access or modify ETO system data
    - Clear architectural boundary between meta and business data
    - Business databases can be scaled/managed independently
    """

    def __init__(self, connection_managers: Dict[str, Any]):
        """
        Initialize data database manager with business database connection managers.

        Args:
            connection_managers: Dictionary mapping database names to ConnectionManager instances.
                                Should NOT include 'main' or other system databases.
                                e.g., {'htc_db': manager1, 'htc_000_db': manager2}

        Raises:
            ValueError: If 'main' database is included (should be excluded)
        """
        # Validate that 'main' is not included
        if 'main' in connection_managers:
            raise ValueError(
                "DataDatabaseManager should not include 'main' database. "
                "The 'main' database is reserved for ETO system metadata and should "
                "only be accessed via repositories, not pipeline modules."
            )

        self.connection_managers = connection_managers
        logger.info(
            f"DataDatabaseManager initialized with {len(connection_managers)} "
            f"business database(s): {', '.join(connection_managers.keys())}"
        )

    def get_connection(self, database_name: str) -> Any:
        """
        Get a business database connection by name.

        Args:
            database_name: Name of the business database (e.g., "htc_db", "htc_000_db")

        Returns:
            For Access databases: AccessConnectionManager instance (use .cursor() context manager)
            For SQLAlchemy databases: Raw database connection

        Raises:
            ValueError: If database connection not found or not configured

        Example:
            >>> data_db_manager = DataDatabaseManager({'htc_db': manager})
            >>> conn = data_db_manager.get_connection("htc_db")
            >>> with conn.cursor() as cursor:
            ...     cursor.execute("SELECT * FROM table")
        """
        if database_name not in self.connection_managers:
            available = list(self.connection_managers.keys())
            raise ValueError(
                f"Unknown business database connection: '{database_name}'. "
                f"Available business databases: {available}"
            )

        connection_manager = self.connection_managers[database_name]

        # Return the appropriate connection type
        # For Access databases: return the AccessConnectionManager (provides thread-safe cursor())
        # For SQL Server databases: return raw connection from SQLAlchemy engine
        if hasattr(connection_manager, 'connection') and connection_manager.connection is not None:
            # Access database (pyodbc) - return AccessConnectionManager for thread-safe cursor access
            # The AccessConnectionManager.cursor() context manager handles locking to prevent
            # concurrent access errors ("Function sequence error") when multiple threads
            # try to use the same Access connection simultaneously.
            connection = connection_manager
        elif hasattr(connection_manager, 'engine'):
            # SQLAlchemy database - DatabaseConnectionManager
            connection = connection_manager.engine.raw_connection()
        else:
            raise ValueError(f"Unknown connection manager type for '{database_name}'")

        logger.debug(f"Retrieved business database connection: {database_name}")
        return connection

    def list_databases(self) -> list[str]:
        """
        List all available business database connection names.

        Returns:
            List of business database connection names (excludes 'main')
        """
        return list(self.connection_managers.keys())
