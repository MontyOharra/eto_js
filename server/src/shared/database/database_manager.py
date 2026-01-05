"""
Database Manager
Provides unified interface for accessing multiple database connections
"""
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Provides unified access to database connections.

    Used by pipeline modules and validation logic to access configured databases.
    This class wraps existing ConnectionManager instances to provide a simple
    get_connection(name) interface.
    """

    def __init__(self, connection_managers: Dict[str, Any]):
        """
        Initialize database manager with connection managers.

        Args:
            connection_managers: Dictionary mapping database names to their ConnectionManager instances
                                e.g., {'main': manager1, 'htc_300': manager2}
        """
        self.connection_managers = connection_managers
        logger.info(f"DatabaseManager initialized with {len(connection_managers)} connections: {', '.join(connection_managers.keys())}")

    def get_connection(self, database_name: str) -> Any:
        """
        Get a database connection by name.

        Args:
            database_name: Name of the database connection (e.g., "htc_300", "htc_000_db")

        Returns:
            Database connection object (pyodbc connection or SQLAlchemy engine)

        Raises:
            ValueError: If database connection not found or not configured

        Example:
            >>> db_manager = DatabaseManager({'htc_300': manager})
            >>> conn = db_manager.get_connection("htc_300")
            >>> cursor = conn.cursor()
        """
        if database_name not in self.connection_managers:
            available = list(self.connection_managers.keys())
            raise ValueError(
                f"Unknown database connection: '{database_name}'. "
                f"Available connections: {available}"
            )

        connection_manager = self.connection_managers[database_name]

        # Get the underlying connection
        # For Access databases, the connection is stored in connection_manager.connection (pyodbc)
        # For SQL Server databases, it's in connection_manager.engine.raw_connection() (SQLAlchemy)
        if hasattr(connection_manager, 'connection') and connection_manager.connection is not None:
            # Access database (pyodbc) - AccessConnectionManager
            connection = connection_manager.connection
        elif hasattr(connection_manager, 'engine'):
            # SQLAlchemy database - DatabaseConnectionManager
            connection = connection_manager.engine.raw_connection()
        else:
            raise ValueError(f"Unknown connection manager type for '{database_name}'")

        logger.debug(f"Retrieved connection for database: {database_name}")
        return connection

    def list_databases(self) -> list[str]:
        """
        List all available database connection names.

        Returns:
            List of database connection names
        """
        return list(self.connection_managers.keys())
