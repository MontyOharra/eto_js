"""
Access Database Connection Management
Handles Microsoft Access database connections using pyodbc
"""
from __future__ import annotations

import logging
import threading
from contextlib import contextmanager
from typing import Generator

import pyodbc

logger = logging.getLogger(__name__)


class AccessConnectionError(Exception):
    """Custom exception for Access database connection issues"""
    pass


class AccessConnection:
    """
    Individual Microsoft Access database connection using pyodbc.

    Design considerations for Access:
    - No connection pooling (Access doesn't handle concurrent connections well)
    - File-based database with potential locking issues
    - Single connection with thread safety
    - Direct SQL via cursor (no ORM)
    """

    def __init__(self, connection_string: str) -> None:
        """
        Initialize connection with Access connection string.

        Args:
            connection_string: pyodbc connection string, e.g.:
                "Driver={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=C:/path/to/db.accdb;"

        Raises:
            ValueError: If connection string is empty
        """
        if not connection_string:
            raise ValueError("Access connection string is required")

        self.connection_string = connection_string
        self.connection: pyodbc.Connection | None = None
        self._initialized = False
        self._lock = threading.Lock()

        logger.info(f"AccessConnection initialized for: {self._safe_connection_info()}")

    def initialize(self) -> None:
        """
        Initialize the Access database connection.
        Tests connectivity by attempting to connect and execute a simple query.

        Raises:
            AccessConnectionError: If connection fails
        """
        with self._lock:
            if self._initialized:
                logger.debug("Access connection already initialized")
                return

            try:
                logger.debug("Initializing Access database connection...")

                # Create connection (no pooling for Access)
                self.connection = pyodbc.connect(
                    self.connection_string,
                    autocommit=False,  # Explicit transaction control
                    timeout=30  # 30 second connection timeout
                )

                # Test connection with a simple query
                cursor = self.connection.cursor()
                cursor.execute("SELECT 1")
                cursor.close()

                self._initialized = True
                logger.info("Access database connection initialized successfully")

            except Exception as e:
                error_msg = f"Failed to connect to Access database: {e}"
                logger.error(error_msg)

                # Provide helpful error messages for common issues
                error_str = str(e).lower()
                if "driver" in error_str:
                    logger.error(
                        "Hint: Install Microsoft Access Database Engine "
                        "(https://www.microsoft.com/en-us/download/details.aspx?id=54920). "
                        "Ensure 32-bit vs 64-bit matches your Python installation."
                    )
                elif "could not find file" in error_str or "not a valid path" in error_str:
                    logger.error(
                        f"Hint: Check that the database file exists at the specified path. "
                        f"Connection string: {self._safe_connection_info()}"
                    )

                raise AccessConnectionError(error_msg) from e

    @contextmanager
    def cursor(self) -> Generator[pyodbc.Cursor, None, None]:
        """
        Create a cursor with automatic commit/rollback and thread safety.

        This is the primary way to interact with the Access database.
        Automatically commits on success and rolls back on exception.

        Thread Safety:
            Uses a lock to serialize all cursor operations. This is required
            because pyodbc + Access does not support multiple cursors executing
            simultaneously on the same connection (causes "Function sequence error").

        Usage:
            with connection.cursor() as cursor:
                cursor.execute("INSERT INTO Orders (CustomerID) VALUES (?)", (123,))
                # Auto-commits on success, auto-rolls back on exception

        Yields:
            Database cursor for executing queries

        Raises:
            AccessConnectionError: If connection not initialized
        """
        if not self._initialized:
            raise AccessConnectionError(
                "Connection not initialized. Call initialize() first."
            )

        if self.connection is None:
            raise AccessConnectionError("Connection not available")

        # Serialize all cursor operations to prevent concurrent access errors
        with self._lock:
            cursor = self.connection.cursor()
            try:
                yield cursor
                self.connection.commit()
                logger.debug("Access transaction committed")
            except Exception:
                self.connection.rollback()
                logger.debug("Access transaction rolled back due to exception")
                raise
            finally:
                cursor.close()

    def test_connection(self) -> bool:
        """
        Test if Access database connection is working.

        Returns:
            True if connection test succeeds, False otherwise
        """
        try:
            if not self._initialized:
                return False

            with self.cursor() as cursor:
                cursor.execute("SELECT 1")

            logger.debug("Access connection test successful")
            return True

        except Exception as e:
            logger.warning(f"Access connection test failed: {e}")
            return False

    def close(self) -> None:
        """Close Access database connection and cleanup."""
        with self._lock:
            if self.connection is not None:
                try:
                    self.connection.close()
                    logger.info("Closed Access database connection")
                except Exception as e:
                    logger.warning(f"Error closing Access connection: {e}")
                finally:
                    self.connection = None
                    self._initialized = False

    def _safe_connection_info(self) -> str:
        """
        Return safe connection info for logging (masks sensitive data).

        Returns:
            Safe connection info showing only database file path
        """
        try:
            # Extract DBQ (database file path) from connection string
            parts = self.connection_string.split(';')
            for part in parts:
                if part.strip().upper().startswith('DBQ='):
                    db_path = part.split('=', 1)[1]
                    return f"Access DB at {db_path}"
            return "Access database"
        except Exception:
            return "Access database"


class AccessConnectionManager:
    """
    Manages multiple Microsoft Access database connections.

    This manager wraps AccessConnection instances and provides unified access
    to multiple Access databases. It excludes the 'main' SQL Server database
    which is handled separately by DatabaseConnectionManager.

    Usage:
        manager = AccessConnectionManager({"htc_300": conn_str1, "htc_350d": conn_str2})
        connection = manager.get_connection("htc_300")
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM Customers")
    """

    def __init__(self, connection_strings: dict[str, str]) -> None:
        """
        Initialize Access connection manager with connection strings.

        Args:
            connection_strings: Dictionary mapping database names to connection strings.
                e.g., {'htc_300': 'Driver=...;DBQ=...', 'htc_350d': 'Driver=...;DBQ=...'}

        Raises:
            ValueError: If 'main' database is included (should be excluded)
        """
        if 'main' in connection_strings:
            raise ValueError(
                "AccessConnectionManager should not include 'main' database. "
                "The 'main' database is SQL Server and should be accessed via "
                "DatabaseConnectionManager, not AccessConnectionManager."
            )

        self._connections: dict[str, AccessConnection] = {}

        # Create and initialize connections
        for name, conn_string in connection_strings.items():
            connection = AccessConnection(conn_string)
            connection.initialize()
            self._connections[name] = connection

        logger.info(
            f"AccessConnectionManager initialized with {len(self._connections)} "
            f"database(s): {', '.join(self._connections.keys())}"
        )

    def get_connection(self, database_name: str) -> AccessConnection:
        """
        Get an Access database connection by name.

        Args:
            database_name: Name of the Access database (e.g., "htc_300", "htc_350d")

        Returns:
            AccessConnection instance - use .cursor() context manager for queries

        Raises:
            ValueError: If database connection not found
        """
        if database_name not in self._connections:
            available = list(self._connections.keys())
            raise ValueError(
                f"Unknown Access database: '{database_name}'. "
                f"Available databases: {available}"
            )

        logger.debug(f"Retrieved Access database connection: {database_name}")
        return self._connections[database_name]

    def list_databases(self) -> list[str]:
        """
        List all available Access database connection names.

        Returns:
            List of Access database connection names
        """
        return list(self._connections.keys())

    def close_all(self) -> None:
        """Close all Access database connections."""
        for name, connection in self._connections.items():
            try:
                connection.close()
                logger.debug(f"Closed Access connection: {name}")
            except Exception as e:
                logger.warning(f"Error closing Access connection '{name}': {e}")

        self._connections.clear()
        logger.info("All Access database connections closed")
