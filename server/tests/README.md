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
make install-deps
```

### 2. Add Test Databases (Auto-Discovery)

Simply place your Access database files (`.accdb`) in `tests/test_databases/`:

```
tests/test_databases/
├── HTC300_Data-01-01.accdb
├── HTC000_Data_Staff.accdb
└── HTC350D ETO Parameters.accdb
```

**That's it!** The test framework will automatically discover and connect to these databases.

**Database Name Mapping (filename → database name in tests):**
- `HTC300_Data-01-01.accdb` → `htc300_data_01_01`
- `HTC000_Data_Staff.accdb` → `htc000_data_staff`
- `HTC350D ETO Parameters.accdb` → `htc350d_eto_parameters`

**Note:** These files are gitignored and will not be committed.

### 3. (Optional) Additional Databases via Environment Variables

If you need to connect to databases outside `test_databases/`, use environment variables:

```bash
# .env.test (optional)
TEST_DATABASE_URL="mssql+pyodbc://test:test@localhost:49172/eto_test?driver=ODBC+Driver+17+for+SQL+Server&TrustServerCertificate=yes"
```

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
def test_fuzzy_lookup(db_services):
    # Access auto-discovered databases by name
    config = FuzzyDatabaseLookupConfig(
        database="htc300_data_01_01",  # Auto-discovered from HTC300_Data-01-01.accdb
        table="Addresses",
        search_column="AddressText",
        return_column="AddressID"
    )
    result = module.run(inputs, config, context, services=db_services)
```

## Test Markers

- `@pytest.mark.integration` - Tests that require database connections
- `@pytest.mark.unit` - Tests that don't require databases
- `@pytest.mark.slow` - Long-running tests

## Quick Start

1. Place `.accdb` files in `tests/test_databases/`
2. Run `make test-all` to verify setup
3. Start writing tests!

## Database Name Reference

To find the database name for your tests, use this formula:
1. Take the filename (without `.accdb`)
2. Convert to lowercase
3. Replace `-` and spaces with `_`

Examples:
- `My Database.accdb` → `my_database`
- `Data-2024-01.accdb` → `data_2024_01`
