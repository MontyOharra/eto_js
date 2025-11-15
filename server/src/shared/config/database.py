"""
Database configuration supporting multiple named database connections

Allows the application to connect to different databases for different purposes:
- main: Primary application database (ETO runs, PDFs, pipelines, templates)
- htc_db: Legacy HTC orders database (for CreateOrder action module)
- (future databases can be added as needed)
"""
import os
import logging
from typing import Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DatabaseConnectionConfig:
    """Configuration for a single database connection"""
    name: str
    connection_string: str
    connection_type: str = "sqlalchemy"  # "sqlalchemy" or "access"
    description: Optional[str] = None

    @classmethod
    def from_environment(
        cls,
        name: str,
        env_var_name: str,
        description: Optional[str] = None,
        required: bool = True
    ) -> Optional['DatabaseConnectionConfig']:
        """
        Create database connection config from environment variable.

        Automatically detects connection type based on connection string format:
        - Starts with "Driver=" → Access database (pyodbc)
        - Otherwise → SQLAlchemy-compatible (SQL Server, PostgreSQL, etc.)

        Args:
            name: Logical name for this connection (e.g., "htc_db", "main")
            env_var_name: Environment variable name (e.g., "htc_db_CONNECTION_STRING")
            description: Human-readable description
            required: If True, raises ValueError when env var not found

        Returns:
            DatabaseConnectionConfig instance, or None if not required and not found

        Raises:
            ValueError: If required=True and connection string not found
        """
        connection_string = os.getenv(env_var_name)

        if not connection_string:
            if required:
                raise ValueError(
                    f"Database connection string not found for '{name}'. "
                    f"Set {env_var_name} environment variable."
                )
            else:
                logger.info(f"Optional database connection '{name}' not configured (no {env_var_name})")
                return None

        # Auto-detect connection type based on connection string format
        connection_type = "access" if connection_string.strip().startswith("Driver=") else "sqlalchemy"

        logger.info(f"Configured database connection: {name} (type: {connection_type})")

        return cls(
            name=name,
            connection_string=connection_string,
            connection_type=connection_type,
            description=description
        )


@dataclass(frozen=True)
class DatabaseConfig:
    """
    Complete database configuration for the application.

    Supports multiple named database connections dynamically loaded from environment:
    - main: Primary application database (ETO runs, PDFs, pipelines, etc.)
    - Any other database with a *_CONNECTION_STRING environment variable
    """
    connections: Dict[str, DatabaseConnectionConfig]

    def get_connection(self, name: str) -> DatabaseConnectionConfig:
        """
        Get a database connection config by name.

        Args:
            name: Connection name (e.g., "main", "htc_300_db", "htc_000_db")

        Returns:
            DatabaseConnectionConfig for the requested connection

        Raises:
            ValueError: If connection name not found or not configured
        """
        if name not in self.connections:
            available = list(self.connections.keys())
            raise ValueError(
                f"Unknown database connection: '{name}'. "
                f"Available connections: {available}"
            )
        return self.connections[name]

    @classmethod
    def from_environment(cls) -> 'DatabaseConfig':
        """
        Load database configuration from environment variables.

        Automatically discovers all database connections from environment variables:
        - DATABASE_URL → main database (required)
        - *_CONNECTION_STRING → additional databases (optional)

        Examples:
        - HTC_300_DB_CONNECTION_STRING → htc_300_db
        - HTC_000_DB_CONNECTION_STRING → htc_000_db
        - MY_DB_CONNECTION_STRING → my_db

        Returns:
            DatabaseConfig instance

        Raises:
            ValueError: If required configuration (DATABASE_URL) is missing
        """
        connections = {}

        # Main database (required)
        main = DatabaseConnectionConfig.from_environment(
            name="main",
            env_var_name="DATABASE_URL",
            description="Primary application database",
            required=True
        )
        if not main:
            raise ValueError("DATABASE_URL environment variable not set")

        connections["main"] = main
        logger.info("Loaded main database connection")

        # Auto-discover additional databases from environment
        # Look for any env vars ending with _CONNECTION_STRING
        discovered_count = 0
        for env_var_name, env_var_value in os.environ.items():
            if env_var_name.endswith("_CONNECTION_STRING") and env_var_value:
                # Convert env var name to database name
                # HTC_300_DB_CONNECTION_STRING → htc_300_db
                db_name = env_var_name.replace("_CONNECTION_STRING", "").lower()

                try:
                    db_config = DatabaseConnectionConfig.from_environment(
                        name=db_name,
                        env_var_name=env_var_name,
                        description=f"Database: {db_name}",
                        required=False
                    )

                    if db_config:
                        connections[db_name] = db_config
                        discovered_count += 1
                        logger.info(f"Auto-discovered database connection: {db_name} (type: {db_config.connection_type})")
                except Exception as e:
                    logger.warning(f"Failed to load database connection from {env_var_name}: {e}")

        logger.info(f"Database configuration complete: 1 main + {discovered_count} additional connections")

        return cls(connections=connections)

    def get_all_connections(self) -> Dict[str, DatabaseConnectionConfig]:
        """
        Get all configured database connections.

        Returns:
            Dictionary mapping connection names to their configs
        """
        return dict(self.connections)
