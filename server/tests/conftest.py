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

# Add src to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from shared.database.database_manager import DatabaseManager
from shared.database.connection import DatabaseConnectionManager
from shared.database.access_connection import AccessConnectionManager


@pytest.fixture(scope="session")
def test_connection_managers():
    """
    Initialize test database connections.

    Uses TEST_*_CONNECTION_STRING env vars for test databases.
    Connections are created once per test session and reused across all tests.

    Environment variables expected:
    - TEST_HTC_300_DB_CONNECTION_STRING: Access database connection
    - TEST_HTC_000_DB_CONNECTION_STRING: Access database connection
    - TEST_DATABASE_URL: Main SQL Server test database

    Returns:
        dict: Mapping of database names to ConnectionManager instances
    """
    managers = {}

    # Load all test database connections from environment
    # Look for env vars like TEST_HTC_300_DB_CONNECTION_STRING
    test_env_vars = {
        k: v for k, v in os.environ.items()
        if k.startswith('TEST_') and k.endswith('_CONNECTION_STRING')
    }

    for env_var, conn_string in test_env_vars.items():
        # Extract database name: TEST_HTC_300_DB_CONNECTION_STRING -> htc_300_db
        db_name = env_var.replace('TEST_', '').replace('_CONNECTION_STRING', '').lower()

        # Detect connection type based on connection string format
        if conn_string.strip().startswith("Driver="):
            # Access database (pyodbc)
            manager = AccessConnectionManager(conn_string)
            manager.initialize_connection()
        else:
            # SQLAlchemy database (SQL Server, PostgreSQL, etc.)
            manager = DatabaseConnectionManager(conn_string)

        managers[db_name] = manager
        print(f"✓ Test database connected: {db_name}")

    # Also add main test database if configured
    if 'TEST_DATABASE_URL' in os.environ:
        main_manager = DatabaseConnectionManager(os.environ['TEST_DATABASE_URL'])
        managers['main'] = main_manager
        print("✓ Test database connected: main")

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
