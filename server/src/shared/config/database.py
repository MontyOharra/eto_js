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


# =============================================================================
# HTC Database Configuration
# =============================================================================

# Maps database connection names to their filenames (without .accdb extension)
# These databases are located in the HTC_APPS_DIR directory
HTC_DATABASE_FILES: Dict[str, str] = {
    "htc_000_data_staff": "HTC000_Data_Staff",
    "htc_300_db": "HTC300_Data-01-01",
    "htc_350d_db": "HTC350D_Database",
}


def get_htc_apps_dir() -> Optional[str]:
    """
    Get the HTC Apps directory from environment.

    Returns:
        HTC_APPS_DIR path (normalized with forward slashes) or None if not set
    """
    htc_apps_dir = os.getenv("HTC_APPS_DIR")
    if htc_apps_dir:
        return htc_apps_dir.replace("\\", "/")
    return None


def _build_htc_connections() -> Dict[str, 'DatabaseConnectionConfig']:
    """
    Build HTC Access database connections from HTC_APPS_DIR environment variable.

    If HTC_APPS_DIR is set, builds connection strings for all databases in
    HTC_DATABASE_FILES mapping.

    Returns:
        Dictionary mapping connection names to DatabaseConnectionConfig instances
    """
    connections = {}

    htc_apps_dir = get_htc_apps_dir()
    if not htc_apps_dir:
        logger.debug("HTC_APPS_DIR not set, skipping HTC database auto-configuration")
        return connections

    logger.info(f"Building HTC database connections from HTC_APPS_DIR: {htc_apps_dir}")

    for db_name, filename in HTC_DATABASE_FILES.items():
        # Build Access connection string
        db_path = f"{htc_apps_dir}/{filename}.accdb"
        connection_string = f"Driver={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={db_path};"

        connections[db_name] = DatabaseConnectionConfig(
            name=db_name,
            connection_string=connection_string,
            connection_type="access",
            description=f"HTC Access database: {filename}"
        )

        logger.info(f"Configured HTC database connection: {db_name} (file: {filename}.accdb)")

    return connections


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

        Configuration sources (in order of priority):
        1. DATABASE_URL → main database (required)
        2. HTC_APPS_DIR → builds HTC Access database connections from mapping
        3. *_CONNECTION_STRING → additional databases (fallback/override)

        For HTC databases, prefer setting HTC_APPS_DIR over individual connection strings.
        Individual *_CONNECTION_STRING vars will override HTC_APPS_DIR-based connections.

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

        # Build HTC database connections from HTC_APPS_DIR
        htc_connections = _build_htc_connections()
        connections.update(htc_connections)
        if htc_connections:
            logger.info(f"Loaded {len(htc_connections)} HTC database connection(s) from HTC_APPS_DIR")

        # Auto-discover additional databases from environment
        # Look for any env vars ending with _CONNECTION_STRING
        # These can override HTC_APPS_DIR-based connections if needed
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
                        if db_name in connections:
                            logger.info(f"Overriding {db_name} connection with explicit {env_var_name}")
                        connections[db_name] = db_config
                        discovered_count += 1
                        logger.info(f"Auto-discovered database connection: {db_name} (type: {db_config.connection_type})")
                except Exception as e:
                    logger.warning(f"Failed to load database connection from {env_var_name}: {e}")

        logger.info(f"Database configuration complete: 1 main + {len(connections) - 1} additional connections")

        return cls(connections=connections)

    def get_all_connections(self) -> Dict[str, DatabaseConnectionConfig]:
        """
        Get all configured database connections.

        Returns:
            Dictionary mapping connection names to their configs
        """
        return dict(self.connections)
