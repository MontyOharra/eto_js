"""
Access Database Connection Management
Handles Microsoft Access database connections using pyodbc
Separate from SQLAlchemy-based connection manager due to Access limitations
"""
import logging
import threading
from typing import Any
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class AccessConnectionError(Exception):
    """Custom exception for Access database connection issues"""
    pass


class AccessConnectionManager:
    """
    Manages Microsoft Access database connections using pyodbc.

    Design considerations for Access:
    - No connection pooling (Access doesn't handle concurrent connections well)
    - File-based database with potential locking issues
    - Single connection with thread safety
    - Direct SQL via cursor (no ORM)

    Note: Requires Microsoft Access Database Engine or full Access installation
    with matching bitness (32-bit vs 64-bit) to Python installation.
    """

    def __init__(self, connection_string: str):
        """
        Initialize connection manager with Access connection string.

        Args:
            connection_string: pyodbc connection string, e.g.:
                "Driver={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=C:/path/to/db.accdb;"

        Raises:
            ValueError: If connection string is empty
        """
        if not connection_string:
            raise ValueError("Access connection string is required")

        self.connection_string = connection_string
        self.connection: Any = None  # pyodbc.Connection
        self._initialized = False
        self._lock = threading.Lock()

        logger.info(f"AccessConnectionManager initialized for: {self._safe_connection_info()}")

    def initialize_connection(self):
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
                import pyodbc

                logger.debug(f"Initializing Access database connection...")

                # Create connection (no pooling for Access)
                self.connection = pyodbc.connect(
                    self.connection_string,
                    autocommit=False,  # Explicit transaction control
                    timeout=30  # 30 second connection timeout
                )

                # Test connection with a simple query
                assert self.connection is not None
                cursor = self.connection.cursor()
                cursor.execute("SELECT 1")
                cursor.close()

                self._initialized = True
                logger.info("Access database connection initialized successfully")

            except ImportError:
                error_msg = "pyodbc is not installed. Install it with: pip install pyodbc"
                logger.error(error_msg)
                raise AccessConnectionError(error_msg)

            except Exception as e:
                error_msg = f"Failed to connect to Access database: {str(e)}"
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

    def get_connection(self):
        """
        Get the raw pyodbc connection object.

        Returns:
            pyodbc.Connection: The active connection

        Raises:
            AccessConnectionError: If not initialized or connection unavailable
        """
        if not self._initialized:
            raise AccessConnectionError(
                "Connection not initialized. Call initialize_connection() first."
            )

        if not self.connection:
            raise AccessConnectionError("Connection not available")

        return self.connection

    @contextmanager
    def cursor(self):
        """
        Create a cursor with automatic commit/rollback.

        This is the primary way to interact with the Access database.
        Automatically commits on success and rolls back on exception.

        Usage:
            with connection_manager.cursor() as cursor:
                cursor.execute("INSERT INTO Orders (CustomerID) VALUES (?)", (123,))
                # Auto-commits on success, auto-rolls back on exception

        Yields:
            pyodbc.Cursor: Database cursor for executing queries

        Raises:
            AccessConnectionError: If connection not initialized
        """
        if not self._initialized:
            raise AccessConnectionError(
                "Connection not initialized. Call initialize_connection() first."
            )

        if not self.connection:
            raise AccessConnectionError("Connection not available")

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
            bool: True if connection test succeeds, False otherwise
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

    def close(self):
        """Close Access database connection and cleanup"""
        with self._lock:
            if self.connection:
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
            str: Safe connection info showing only database file path
        """
        try:
            # Extract DBQ (database file path) from connection string
            parts = self.connection_string.split(';')
            for part in parts:
                if part.strip().upper().startswith('DBQ='):
                    db_path = part.split('=', 1)[1]
                    return f"Access DB at {db_path}"
            return "Access database"
        except:
            return "Access database"
