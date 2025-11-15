# Testing Infrastructure

## Directory Structure

```
tests/
├── __init__.py
├── conftest.py              # Pytest fixtures (database setup)
├── test_databases/          # Test database copies (gitignored)
│   └── .gitkeep
└── test_modules/            # Module tests
    ├── __init__.py
    └── transform/
        └── __init__.py
```

## Setup Instructions

### 1. Install Development Dependencies

```bash
cd server
pip install -r requirements-dev.txt
```

### 2. Copy Test Databases

Copy your production Access databases to `tests/test_databases/` with `_Test` suffix:

```
tests/test_databases/
├── HTC300_Data_Test.accdb
└── HTC000_Data_Test.accdb
```

**Note:** These files are gitignored and will not be committed.

### 3. Configure Test Environment Variables

Create a `.env.test` file in the `server/` directory (or add to existing `.env`):

```bash
# Test Database Connections
TEST_HTC_300_DB_CONNECTION_STRING="Driver={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=C:/Users/YourUser/software_projects/eto_js/server/tests/test_databases/HTC300_Data_Test.accdb;"
TEST_HTC_000_DB_CONNECTION_STRING="Driver={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=C:/Users/YourUser/software_projects/eto_js/server/tests/test_databases/HTC000_Data_Test.accdb;"
TEST_DATABASE_URL="mssql+pyodbc://test:test@localhost:49172/eto_test?driver=ODBC+Driver+17+for+SQL+Server&TrustServerCertificate=yes"
```

**Important:** Update the `DBQ=` paths to match your actual file locations.

## Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run integration tests only
pytest -m integration

# Run specific test file
pytest tests/test_modules/transform/test_sql_lookup.py

# Run with print output visible
pytest -s

# Run with coverage report
pytest --cov=src --cov-report=html
```

## Writing Tests

### Example Test Structure

```python
import pytest
from pipeline_modules.transform.my_module import MyModule, MyModuleConfig

@pytest.mark.integration
def test_my_module(db_services):
    """Test module with real test database"""

    # Arrange
    module = MyModule()
    config = MyModuleConfig(
        database="htc_300_db",
        # ... other config
    )
    inputs = {"field": "value"}
    context = {}

    # Act
    result = module.run(inputs, config, context, services=db_services)

    # Assert
    assert "output_field" in result
    assert result["output_field"] == expected_value
```

### Using the `db_services` Fixture

The `db_services` fixture provides a `DatabaseManager` instance configured with test database connections. Use it exactly like the `services` parameter in production:

```python
def test_sql_lookup(db_services):
    # db_services.get_connection("htc_300_db") returns test database connection
    result = module.run(inputs, config, context, services=db_services)
```

## Test Markers

- `@pytest.mark.integration` - Tests that require database connections
- `@pytest.mark.unit` - Tests that don't require databases
- `@pytest.mark.slow` - Long-running tests

## Next Steps

1. Copy your production databases to `tests/test_databases/`
2. Update `.env.test` with correct file paths
3. Run `pytest` to verify setup
4. Start writing tests for your modules!
