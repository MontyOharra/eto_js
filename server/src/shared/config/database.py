"""
Database configuration supporting multiple named database connections

Allows the application to connect to different databases for different purposes:
- main: Primary application database (ETO runs, PDFs, pipelines, templates)
- orders_db: Legacy HTC orders database (for CreateOrder action module)
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

        Args:
            name: Logical name for this connection (e.g., "orders_db", "main")
            env_var_name: Environment variable name (e.g., "ORDERS_DB_CONNECTION_STRING")
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

        logger.info(f"Configured database connection: {name}")

        return cls(
            name=name,
            connection_string=connection_string,
            description=description
        )


@dataclass(frozen=True)
class DatabaseConfig:
    """
    Complete database configuration for the application.

    Supports multiple named database connections for different purposes:
    - main: Primary application database (ETO runs, PDFs, pipelines, etc.)
    - orders_db: Legacy HTC orders database for CreateOrder action (optional)
    """
    main: DatabaseConnectionConfig
    orders_db: Optional[DatabaseConnectionConfig] = None

    def get_connection(self, name: str) -> DatabaseConnectionConfig:
        """
        Get a database connection config by name.

        Args:
            name: Connection name ("main" or "orders_db")

        Returns:
            DatabaseConnectionConfig for the requested connection

        Raises:
            ValueError: If connection name not found or not configured
        """
        if name == "main":
            return self.main
        elif name == "orders_db":
            if not self.orders_db:
                raise ValueError(
                    "Orders database not configured. "
                    "Set ORDERS_DB_CONNECTION_STRING environment variable in .env file."
                )
            return self.orders_db
        else:
            raise ValueError(f"Unknown database connection: {name}")

    @classmethod
    def from_environment(cls) -> 'DatabaseConfig':
        """
        Load database configuration from environment variables.

        Expected configuration:

        Main Database (required):
        - Environment: DATABASE_URL

        Orders Database (optional):
        - Environment: ORDERS_DB_CONNECTION_STRING

        Returns:
            DatabaseConfig instance

        Raises:
            ValueError: If required configuration (DATABASE_URL) is missing
        """
        # Main database (required)
        main = DatabaseConnectionConfig.from_environment(
            name="main",
            env_var_name="DATABASE_URL",
            description="Primary application database",
            required=True
        )

        # Orders database (optional)
        orders_db = DatabaseConnectionConfig.from_environment(
            name="orders_db",
            env_var_name="ORDERS_DB_CONNECTION_STRING",
            description="Legacy HTC orders database",
            required=False
        )

        return cls(
            main=main,
            orders_db=orders_db
        )

    def get_all_connections(self) -> Dict[str, DatabaseConnectionConfig]:
        """
        Get all configured database connections.

        Returns:
            Dictionary mapping connection names to their configs
        """
        connections = {"main": self.main}
        if self.orders_db:
            connections["orders_db"] = self.orders_db
        return connections
