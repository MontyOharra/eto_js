"""
Pytest Configuration and Shared Fixtures

This file contains pytest fixtures that are available to all tests.
The main fixture is `db_services` which provides DatabaseManager
configured with test database connections.

Usage in tests:
    def test_my_module(db_services):
        result = module.run(inputs, config, context, services=db_services)
"""
import pytest
import os
import sys
from pathlib import Path

# Add src to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✓ Loaded environment from {env_path}")
except ImportError:
    pass  # python-dotenv not installed, rely on actual env vars

from shared.database.database_manager import DatabaseManager
from shared.database.connection import DatabaseConnectionManager
from shared.database.access_connection import AccessConnectionManager


@pytest.fixture(scope="session")
def test_connection_managers():
    """
    Initialize test database connections.

    Auto-discovers .accdb files in tests/test_databases/ and creates connections.
    Also supports TEST_*_CONNECTION_STRING env vars for additional databases.

    Auto-discovery mapping (filename -> database name):
    - "HTC300_Data-01-01.accdb" -> "htc300_data_01_01"
    - "HTC000_Data_Staff.accdb" -> "htc000_data_staff"
    - "HTC350D ETO Parameters.accdb" -> "htc350d_eto_parameters"

    Connections are created once per test session and reused across all tests.

    Returns:
        dict: Mapping of database names to ConnectionManager instances
    """
    managers = {}

    # Auto-discover .accdb files in test_databases/
    test_db_dir = Path(__file__).parent / "test_databases"

    if test_db_dir.exists():
        for db_file in test_db_dir.glob("*.accdb"):
            # Generate database name from filename
            # "HTC300_Data-01-01.accdb" -> "htc300_data_01_01"
            db_name = db_file.stem.lower().replace("-", "_").replace(" ", "_")

            # Build connection string
            conn_string = f"Driver={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={db_file.absolute()};"

            try:
                # Create connection manager
                manager = AccessConnectionManager(conn_string)
                manager.initialize_connection()

                managers[db_name] = manager
                print(f"✓ Test database connected: {db_name} ({db_file.name})")
            except Exception as e:
                print(f"✗ Failed to connect to {db_file.name}: {e}")

    # Also load test database connections from environment variables (backward compatibility)
    test_env_vars = {
        k: v for k, v in os.environ.items()
        if k.startswith('TEST_') and k.endswith('_CONNECTION_STRING')
    }

    for env_var, conn_string in test_env_vars.items():
        # Extract database name: TEST_HTC_300_DB_CONNECTION_STRING -> htc_300_db
        db_name = env_var.replace('TEST_', '').replace('_CONNECTION_STRING', '').lower()

        # Skip if already added via auto-discovery
        if db_name in managers:
            continue

        # Detect connection type based on connection string format
        try:
            if conn_string.strip().startswith("Driver="):
                # Access database (pyodbc)
                manager = AccessConnectionManager(conn_string)
                manager.initialize_connection()
            else:
                # SQLAlchemy database (SQL Server, PostgreSQL, etc.)
                manager = DatabaseConnectionManager(conn_string)

            managers[db_name] = manager
            print(f"✓ Test database connected: {db_name} (from env)")
        except Exception as e:
            print(f"✗ Failed to connect to {db_name}: {e}")

    # Also add main test database if configured
    if 'TEST_DATABASE_URL' in os.environ and 'main' not in managers:
        try:
            main_manager = DatabaseConnectionManager(os.environ['TEST_DATABASE_URL'])
            managers['main'] = main_manager
            print("✓ Test database connected: main")
        except Exception as e:
            print(f"✗ Failed to connect to main database: {e}")

    if not managers:
        print("⚠ Warning: No test databases found. Place .accdb files in tests/test_databases/")

    yield managers

    # Cleanup: Close all connections after all tests complete
    for db_name, manager in managers.items():
        if hasattr(manager, 'close'):
            manager.close()
            print(f"✓ Test database closed: {db_name}")


@pytest.fixture
def db_services(test_connection_managers):
    """
    Provide DatabaseManager with test database connections.

    Use this fixture in tests that need database access.
    The DatabaseManager provides the same interface as used in production
    via the `services` parameter in module run() methods.

    Args:
        test_connection_managers: Session-scoped fixture with all test DB connections

    Returns:
        DatabaseManager: Configured with test database connections

    Example:
        def test_sql_lookup(db_services):
            module = SqlLookup()
            config = SqlLookupConfig(database="htc_300_db", ...)
            result = module.run(inputs, config, context, services=db_services)
            assert result["field"] == expected_value
    """
    return DatabaseManager(test_connection_managers)
