# SQL Lookup Database Dropdown Implementation

## Context

The `sql_lookup` module has a `database` config field that needs to be rendered as a dropdown showing available database connections from the environment.

## Current State

**Module Location**: `server/src/pipeline_modules/transform/sql_lookup.py`

**Current Config Schema**:
```python
class SqlLookupConfig(BaseModel):
    sql_template: str = Field(...)
    database: str = Field(default="DATABASE_ETO", ...)
    on_multiple_rows: Literal["error", "first", "last"] = Field(...)
    on_no_rows: Literal["error", "null"] = Field(...)
```

**Problem**: The `database` field is currently a plain string field. It needs to become a dropdown populated with available database connection names from the environment.

## How Database Connections Work

**Service**: `DatabaseConnectionPool` (`server/src/shared/services/database_connection_pool.py`)

**Environment Setup**:
```bash
DB_CONNECTIONS=htc_db,orders_db,analytics_db
HTC_DB_CONNECTION_STRING=mssql+pyodbc://...
ORDERS_DB_CONNECTION_STRING=mssql+pyodbc://...
ANALYTICS_DB_CONNECTION_STRING=postgresql://...
```

**Available Methods**:
- `list_connections()` → `['htc_db', 'orders_db', 'analytics_db']`
- `get_connection(name)` → Returns SQLAlchemy connection context manager
- `get_engine(name)` → Returns SQLAlchemy Engine

## Implementation Options Discussed

### Option A: Dynamic Config Schema (Recommended)

Override `config_schema()` in the `SqlLookup` module to inject available databases:

```python
@classmethod
def config_schema(cls) -> Dict[str, Any]:
    """Generate schema with dynamic database enum"""
    from shared.services import ServiceContainer

    # Get base schema from Pydantic
    schema = cls.ConfigModel.model_json_schema()

    # Inject available databases into the 'database' field enum
    try:
        db_pool = ServiceContainer.get_database_pool()
        available_dbs = db_pool.list_connections()
        if available_dbs:
            schema['properties']['database']['enum'] = available_dbs
            # Remove default value if it's not in available list
            if 'default' in schema['properties']['database']:
                if schema['properties']['database']['default'] not in available_dbs:
                    del schema['properties']['database']['default']
    except Exception as e:
        # Fallback if services not initialized yet
        logger.warning(f"Could not load database connections for schema: {e}")

    return schema
```

**Pros**:
- Self-contained in the module
- Frontend just renders the enum (same as `on_multiple_rows`)
- Works with existing frontend logic
- No new API endpoints needed

**Cons**:
- Schema is generated at module sync time (not runtime)
- Need to re-sync modules if environment changes
- Might fail during startup if ServiceContainer not ready

### Option B: Frontend API Endpoint

Create a dedicated API endpoint that returns available databases:

```python
# In server/src/api/routers/admin.py or new databases.py
@router.get("/databases")
def list_databases():
    """Return list of available database connections"""
    from shared.services import ServiceContainer
    db_pool = ServiceContainer.get_database_pool()
    return {"databases": db_pool.list_connections()}
```

Then update frontend to:
1. Check if config field name is "database"
2. Fetch options from `GET /api/admin/databases`
3. Render as dropdown

**Pros**:
- Always returns current environment state
- No module re-sync needed
- Cleaner separation of concerns

**Cons**:
- Requires frontend changes
- New API endpoint
- Special-case logic in frontend for "database" field

## Related Architecture Changes (Already Completed)

### Services Parameter Separation

The module `run()` signature has been updated to pass services as a separate parameter:

**Before**:
```python
def run(self, inputs, cfg, context):
    # context.services.get_connection('htc_db')
```

**After**:
```python
def run(self, inputs, cfg, context, services=None):
    # services.get_connection('htc_db')
```

**Changes Made**:
1. Updated `BaseModule.run()` signature in `shared/types/modules.py`
2. Updated `ModuleExecutionContext` in `shared/types/pipelines.py` (removed `services` field)
3. Updated `pipeline_execution/service.py` to pass `services` separately
4. Updated all 16 existing module `run()` signatures

**Files Updated**:
- `shared/types/modules.py`
- `shared/types/pipelines.py`
- `features/pipeline_execution/service.py`
- All modules in `pipeline_modules/` directory

## Next Steps

1. **Decide on approach**: Choose between Option A (dynamic schema) or Option B (API endpoint)
2. **Implement chosen approach**:
   - Option A: Override `config_schema()` in `sql_lookup.py`
   - Option B: Create API endpoint + update frontend config renderer
3. **Test with multiple database connections** in environment
4. **Implement SQL lookup execution logic** (currently raises NotImplementedError)

## SQL Lookup Execution Requirements

When implementing the actual execution:

1. Get database connection: `services.get_connection(cfg.database)`
2. Parse SQL template to extract `{placeholders}` → map to input pin names
3. Parse SELECT clause to extract column names/aliases → map to output pin names
4. Execute parameterized query (protect against SQL injection)
5. Handle row count based on `on_multiple_rows` and `on_no_rows` config
6. Map result columns to output pins by name

**Example**:
```python
# Config
sql_template = "SELECT order_id, customer_name AS cust FROM orders WHERE hawb = {hawb_input}"

# Input pins required: hawb_input
# Output pins required: order_id, cust

# Execution
with services.get_connection(cfg.database) as conn:
    result = conn.execute(text(parameterized_sql), params)
    rows = result.fetchall()
    # Handle rows based on config
    # Map columns to output pins
```

## Testing Considerations

1. **No database connections**: Should gracefully handle when `DB_CONNECTIONS` is empty
2. **Missing connection string**: Handle when listed in `DB_CONNECTIONS` but env var missing
3. **Invalid database name**: Handle when config specifies non-existent database
4. **Module sync timing**: Ensure schema generation doesn't break during startup
5. **Multiple SQL dialects**: Support both PostgreSQL and SQL Server syntax
