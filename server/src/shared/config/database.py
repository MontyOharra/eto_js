"""
Database configuration supporting multiple named database connections

Allows the application to connect to different databases for different purposes:
- main: Primary application database (ETO runs, PDFs, pipelines, templates)
- htc_*: Legacy HTC Access databases (for CreateOrder action module, auth, etc.)
"""
import os
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# =============================================================================
# HTC Database Configuration
# =============================================================================

# Maps database connection names to their filenames (without .accdb extension)
# These databases are located in the HTC_APPS_DIR directory
HTC_DATABASE_FILES: dict[str, str] = {
    "htc_000": "HTC000_Data_Staff",
    "htc_300": "HTC300_Data-01-01",
    "htc_350d": "HTC350D_Database",
}


def get_htc_apps_dir() -> str | None:
    """
    Get the HTC Apps directory from environment.

    Returns:
        HTC_APPS_DIR path (normalized with forward slashes) or None if not set
    """
    htc_apps_dir = os.getenv("HTC_APPS_DIR")
    if htc_apps_dir:
        return htc_apps_dir.replace("\\", "/")
    return None


@dataclass(frozen=True)
class ConnectionInfo:
    """Configuration for a single database connection."""
    name: str
    connection_string: str
    connection_type: str  # "sqlalchemy" or "access"
    description: str | None = None


def _detect_connection_type(connection_string: str) -> str:
    """Detect connection type based on connection string format."""
    return "access" if connection_string.strip().startswith("Driver=") else "sqlalchemy"


def _load_main_connection() -> ConnectionInfo:
    """Load the main database connection from DATABASE_URL."""
    connection_string = os.getenv("DATABASE_URL")
    if not connection_string:
        raise ValueError(
            "Database connection string not found for 'main'. "
            "Set DATABASE_URL environment variable."
        )

    logger.info("Configured database connection: main")
    return ConnectionInfo(
        name="main",
        connection_string=connection_string,
        connection_type=_detect_connection_type(connection_string),
        description="Primary application database",
    )


def _load_htc_connections() -> dict[str, ConnectionInfo]:
    """
    Build HTC Access database connections from HTC_APPS_DIR environment variable.

    If HTC_APPS_DIR is set, builds connection strings for all databases in
    HTC_DATABASE_FILES mapping.
    """
    connections = {}

    htc_apps_dir = get_htc_apps_dir()
    if not htc_apps_dir:
        logger.debug("HTC_APPS_DIR not set, skipping HTC database auto-configuration")
        return connections

    logger.info(f"Building HTC database connections from HTC_APPS_DIR: {htc_apps_dir}")

    for db_name, filename in HTC_DATABASE_FILES.items():
        db_path = f"{htc_apps_dir}/{filename}.accdb"
        connection_string = f"Driver={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={db_path};"

        connections[db_name] = ConnectionInfo(
            name=db_name,
            connection_string=connection_string,
            connection_type="access",
            description=f"HTC Access database: {filename}",
        )
        logger.info(f"Configured HTC database connection: {db_name} (file: {filename}.accdb)")

    return connections


def _load_additional_connections() -> dict[str, ConnectionInfo]:
    """
    Auto-discover additional databases from *_CONNECTION_STRING environment variables.

    These can override HTC_APPS_DIR-based connections if needed.
    """
    connections = {}

    for env_var_name, env_var_value in os.environ.items():
        if env_var_name.endswith("_CONNECTION_STRING") and env_var_value:
            # Convert env var name to database name: HTC_300_CONNECTION_STRING → htc_300
            db_name = env_var_name.replace("_CONNECTION_STRING", "").lower()

            connections[db_name] = ConnectionInfo(
                name=db_name,
                connection_string=env_var_value,
                connection_type=_detect_connection_type(env_var_value),
                description=f"Database: {db_name}",
            )
            logger.info(f"Auto-discovered database connection: {db_name}")

    return connections


def load_database_connections() -> dict[str, ConnectionInfo]:
    """
    Load all database connections from environment variables.

    Configuration sources (in order of priority):
    1. DATABASE_URL → main database (required)
    2. HTC_APPS_DIR → builds HTC Access database connections from mapping
    3. *_CONNECTION_STRING → additional databases (can override HTC_APPS_DIR)

    Returns:
        Dictionary mapping connection names to ConnectionInfo instances

    Raises:
        ValueError: If required configuration (DATABASE_URL) is missing
    """
    connections = {}

    # Main database (required)
    connections["main"] = _load_main_connection()
    logger.info("Loaded main database connection")

    # HTC databases from HTC_APPS_DIR
    htc_connections = _load_htc_connections()
    connections.update(htc_connections)
    if htc_connections:
        logger.info(f"Loaded {len(htc_connections)} HTC database connection(s) from HTC_APPS_DIR")

    # Additional databases from *_CONNECTION_STRING env vars (can override)
    additional = _load_additional_connections()
    for db_name, conn_info in additional.items():
        if db_name in connections:
            logger.info(f"Overriding {db_name} connection with explicit {db_name.upper()}_CONNECTION_STRING")
        connections[db_name] = conn_info

    logger.info(f"Database configuration complete: {len(connections)} connection(s)")

    return connections
