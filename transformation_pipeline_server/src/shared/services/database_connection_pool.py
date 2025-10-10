"""
Database Connection Pool Service
Manages connections to external databases for action modules
"""
import os
from typing import Dict, Optional
from sqlalchemy import create_engine, Engine
from sqlalchemy.pool import NullPool
import logging

logger = logging.getLogger(__name__)


class DatabaseConnectionPool:
    """
    Manages database connections for external databases used by action modules
    Separate from the main application database
    """

    def __init__(self):
        self._engines: Dict[str, Engine] = {}
        self._load_connections()

    def _load_connections(self):
        """
        Load database connections from environment variables

        Expected format:
        DB_CONNECTIONS=orders_db,analytics_db
        ORDERS_DB_CONNECTION_STRING=mssql+pyodbc://...
        ANALYTICS_DB_CONNECTION_STRING=postgresql://...
        """
        connections_str = os.getenv("DB_CONNECTIONS", "")

        if not connections_str:
            logger.warning("No external database connections configured (DB_CONNECTIONS not set)")
            return

        connection_names = [name.strip() for name in connections_str.split(",")]

        for name in connection_names:
            if not name:
                continue

            # Build env var name: orders_db -> ORDERS_DB_CONNECTION_STRING
            env_var = f"{name.upper()}_CONNECTION_STRING"
            connection_string = os.getenv(env_var)

            if not connection_string:
                logger.warning(f"Connection '{name}' listed in DB_CONNECTIONS but {env_var} not found")
                continue

            try:
                # Create engine with NullPool to avoid connection persistence issues
                engine = create_engine(
                    connection_string,
                    poolclass=NullPool,
                    echo=False
                )
                self._engines[name] = engine
                logger.info(f"Database connection '{name}' initialized successfully")
            except Exception as e:
                logger.error(f"Failed to create engine for '{name}': {str(e)}")

    def get_engine(self, connection_name: str) -> Engine:
        """
        Get database engine by connection name

        Args:
            connection_name: Name of the connection (e.g., 'orders_db')

        Returns:
            SQLAlchemy Engine instance

        Raises:
            KeyError: If connection name not found
        """
        if connection_name not in self._engines:
            available = list(self._engines.keys())
            raise KeyError(
                f"Database connection '{connection_name}' not found. "
                f"Available connections: {available}"
            )

        return self._engines[connection_name]

    def get_connection(self, connection_name: str):
        """
        Get a database connection (context manager)

        Usage:
            with db_pool.get_connection('orders_db') as conn:
                conn.execute(...)
        """
        engine = self.get_engine(connection_name)
        return engine.connect()

    def list_connections(self) -> list[str]:
        """List all available connection names"""
        return list(self._engines.keys())

    def close_all(self):
        """Close all database connections"""
        for name, engine in self._engines.items():
            try:
                engine.dispose()
                logger.info(f"Closed database connection '{name}'")
            except Exception as e:
                logger.error(f"Error closing connection '{name}': {str(e)}")

        self._engines.clear()
