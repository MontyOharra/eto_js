# Session Continuity Document

## Current Status (2025-11-16)

### ✅ Recently Completed

#### Pipeline Infrastructure Improvements
- **Database Architecture Separation** - Separated meta database ('main') from business databases with DataDatabaseManager
- **Fuzzy Database Lookup Module** - Transform module for fuzzy string matching against database columns
- **Next Order Number Generator** - Misc module replicating VBA logic for order number generation
- **Pipeline Edit Functionality** - Added Edit button to pipeline viewer that opens builder with existing data

#### Frontend UX Improvements
- **Auto-resizing Textareas** - Config input fields now auto-grow based on content (no more horizontal overflow)
- **Pipeline Editing Workflow** - Quick iteration on pipelines without rebuilding from scratch

#### Development Environment
- **Conda Integration Fixes** - Resolved logging visibility and Ctrl+C interrupt issues in Git Bash/MINGW64

---

## Architecture Overview

### Database Manager Hierarchy
```
ServiceContainer
├─ _connection_manager          # 'main' meta/system database
├─ _connection_managers          # All named connections (dict)
│   ├─ 'main'                   # Meta database
│   └─ 'htc_db'                 # Business database
└─ _data_database_manager        # Business databases only (for modules)
    └─ get_connection(name)      # Used by pipeline modules
```

**Key Principle:** Pipeline modules should NEVER see the 'main' database in dropdowns. Only business databases (htc_db, etc.) should be available for module configuration.

### Module Database Access Pattern
```python
# In module's config_schema() method:
data_db_manager = ServiceContainer._data_database_manager
available_connections = data_db_manager.list_databases()  # ['htc_db']
schema['properties']['database']['enum'] = available_connections

# In module's run() method:
connection = services.get_connection(cfg.database)  # services = DataDatabaseManager
with connection.cursor() as cursor:
    cursor.execute(sql)
    rows = cursor.fetchall()
# Commit happens automatically when cursor context exits
```

---

## New Modules Implemented

### 1. Fuzzy Database Lookup (`fuzzy_database_lookup`)
**Location:** `server/src/pipeline_modules/transform/fuzzy_database_lookup.py`

**Purpose:** Find best matching value in a database column using fuzzy string matching

**Configuration:**
- `database`: Database name (dropdown from business databases)
- `table`: Table to search in
- `search_column`: Column to match against
- `return_column`: Column to return as matched value
- `algorithm`: Matching algorithm (ratio, partial_ratio, token_sort_ratio, token_set_ratio)
- `where_clause`: Optional SQL WHERE clause filter
- `limit`: Optional row limit for performance
- `case_sensitive`: Whether matching is case-sensitive

**I/O:**
- **Input:** `search_text` (str) - Text to search for
- **Output:**
  - `matched_value` (str | None) - Best matching value from return_column
  - `confidence` (float) - Match confidence score (0-100)
  - `match_found` (bool) - Whether a match was found

**Dependencies:** rapidfuzz library (added to requirements.txt)

**Use Case Example:**
```
Input: "123 Main Street"
Database: htc_db, Table: Addresses, search_column: address_line1
Output: matched_value="123 Main St", confidence=92.5, match_found=true
```

### 2. Next Order Number (`next_order_number`)
**Location:** `server/src/pipeline_modules/misc/next_order_number.py`

**Purpose:** Generate next available order number using legacy VBA logic

**Configuration:**
- `database`: Database name (dropdown from business databases, default: "htc_db")

**I/O:**
- **Input:** None (no inputs)
- **Output:** `order_number` (float) - Next available order number

**Logic Flow:**
1. Read last order number from LON table (`HTC300_G040_T000 Last OrderNo Assigned`)
2. Check if number exists in OIW table (`HTC300_G040_T005 Orders In Work`)
3. If exists, increment and check again (loop until unused)
4. Update LON table with new number
5. Insert new order into OIW table
6. Return new order number

**Hardcoded Values:** CoID=1, BrID=1 (for local system)

**VBA Reference:** `vba-code/HTC_200_Func_GetNextOrderNbrToAssign.vba`

---

## Frontend Improvements

### Auto-resizing Textareas
**File:** `client/src/renderer/features/pipelines/components/PipelineGraph/ConfigSection.tsx`

**Changes:**
- Replaced `<input type="text">` with `<textarea>` for string fields
- Added auto-resize logic using useRef and useEffect
- Textareas adjust height based on scrollHeight when content changes
- Prevents horizontal overflow in module config sections

### Pipeline Edit Functionality
**Files:**
- `client/src/renderer/features/pipelines/components/PipelineBuilderModal/PipelineBuilderModal.tsx`
- `client/src/renderer/features/pipelines/components/PipelineViewerModal/PipelineViewerModal.tsx`

**How It Works:**
1. Added `initialData?: PipelineData` prop to PipelineBuilderModal
2. State initialization uses initialData when provided
3. Added "Edit" button to PipelineViewerModal header
4. Clicking Edit opens builder pre-populated with current pipeline data
5. Saving creates a NEW pipeline (no PUT endpoint needed for testing)

**Use Case:** Quickly iterate on pipeline designs by editing existing pipelines instead of rebuilding from scratch

---

## Development Environment

### Conda Integration (Git Bash/MINGW64)
**File:** `server/Makefile`

**Issues Fixed:**
1. **Logging not visible:** Added `--no-capture-output` flag to conda run commands
2. **Ctrl+C hangs on "terminate batch job":** Changed `dev` target to use conda activation instead of conda run

**Current Solution:**
```makefile
# For non-interactive commands (tests, sync, etc.)
PYTHON = conda run --no-capture-output -p $(CONDA_ENV_DIR) python

# For interactive dev server
dev:
	@bash -c "eval \"$(conda shell.bash hook)\" && conda activate ./$(CONDA_ENV_DIR) && DEBUG=true RELOAD=true PYTHONUNBUFFERED=1 python main.py"
```

**Result:** Logs now appear in terminal, Ctrl+C works cleanly without hanging

---

## Known Issues & Future Work

### Pipeline Branching Problem (Discussed but Not Implemented)
**Problem:** When using conditional branching (e.g., fuzzy_database_lookup → if_branch), if the lookup fails (FALSE path), the original input data needed to create a new record is lost because if_branch only passes the condition value.

**Example Scenario:**
```
fuzzy_lookup(address) → match_found=false
Need original address fields to create new record
But if_branch only passes boolean, not original data
```

**Proposed Solutions (User's Ideas):**
1. **Guard Clause Pattern:** if_branch with only true output (filters data)
2. **Two Data Inputs:** if_branch with separate true_data and false_data inputs

**Status:** User found "a different solution" and decided not to implement the above patterns yet. This is a deferred architectural decision.

### Order Creation Module (Planned, Not Started)
**Context:** User has schemas for order tables ready:
- `HTC300_G040_T010A_Open_Orders.json` (75 columns) - main table
- `HTC300_G040_T011A_Open_Order_Assessorials.json` (17 columns)
- `HTC300_G040_T012A_Open_Order_Dims.json` (11 columns)
- `HTC300_G040_T013A_Open_Order_Drivers.json` (10 columns)
- `HTC300_G040_T014A_Open_Order_Attachments.json` (6 columns)

**Next Step:** Create a module to insert new orders into these tables. This will likely be a complex module with many configuration fields.

**Blockers:** None - schemas are ready, database architecture is in place

---

## Next Session Priorities

### High Priority
1. **Order Creation Module**
   - Review order table schemas (already extracted)
   - Design module configuration (75+ fields from main table)
   - Implement INSERT logic for main table + related tables
   - Consider using transactions for multi-table inserts
   - Test with next_order_number module integration

### Medium Priority
2. **Pipeline Branching Architecture**
   - Revisit the branching problem if it blocks order creation workflow
   - User mentioned they found "a different solution" - may want to document it
   - Consider implementing one of the proposed if_branch improvements if needed

3. **Module Testing & Validation**
   - Test fuzzy_database_lookup with real address data
   - Test next_order_number with actual database
   - Integration test: fuzzy lookup → create order if no match

### Low Priority
4. **Database Dropdown Enhancement**
   - Consider adding table name dropdown for modules (user asked about this but deferred)
   - Would require metadata service and API endpoint
   - Useful for sql_lookup, fuzzy_database_lookup, and future modules

---

## Important Files Reference

### Backend - Core Services
- `server/src/shared/services/service_container.py` - Dependency injection, database manager access
- `server/src/shared/database/data_database_manager.py` - Business database manager (excludes 'main')
- `server/src/app.py` - ServiceContainer initialization with database managers

### Backend - New Modules
- `server/src/pipeline_modules/transform/fuzzy_database_lookup.py` - Fuzzy matching module
- `server/src/pipeline_modules/misc/next_order_number.py` - Order number generator
- `server/tests/test_modules/transform/test_fuzzy_database_lookup.py` - Fuzzy lookup tests

### Frontend - Pipeline UX
- `client/src/renderer/features/pipelines/components/PipelineViewerModal/PipelineViewerModal.tsx` - Pipeline viewer with Edit button
- `client/src/renderer/features/pipelines/components/PipelineBuilderModal/PipelineBuilderModal.tsx` - Builder with initialData support
- `client/src/renderer/features/pipelines/components/PipelineGraph/ConfigSection.tsx` - Auto-resizing textareas

### Documentation
- `docs/access_db_schemas/HTC300_Data-01-01/` - Order table schemas (5 tables)
- `vba-code/HTC_200_Func_GetNextOrderNbrToAssign.vba` - Original VBA reference

### Environment
- `server/Makefile` - Conda integration, dev server, testing targets
- `server/requirements.txt` - Python dependencies (includes rapidfuzz)

---

## Testing Commands

```bash
# Run all tests
make test-all

# Run specific test
make test TEST=server/tests/test_modules/transform/test_fuzzy_database_lookup.py

# Run dev server
make dev  # Now works properly with Ctrl+C

# Sync modules to database
make modules-sync
```

---

## Common Patterns

### Adding a New Module with Database Dropdown

```python
from shared.services.service_container import ServiceContainer

@register
class MyModule(TransformModule):
    @classmethod
    def config_schema(cls) -> Dict[str, Any]:
        schema = cls.ConfigModel.model_json_schema()

        # Inject business database connections
        try:
            if ServiceContainer.is_initialized():
                data_db_manager = ServiceContainer._data_database_manager
                if data_db_manager:
                    available_connections = data_db_manager.list_databases()
                    schema['properties']['database']['enum'] = available_connections
        except Exception as e:
            logger.warning(f"Could not inject database connections: {e}")

        return schema

    def run(self, inputs, cfg, context, services=None):
        # services is DataDatabaseManager instance
        connection = services.get_connection(cfg.database)
        with connection.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()
        # Auto-commits on context exit
```

### Using Cursor Context Managers (Access Database)

```python
# CORRECT: Use cursor context manager
with connection.cursor() as cursor:
    cursor.execute("INSERT INTO table VALUES (?)", (value,))
    # Commit happens automatically when context exits

# WRONG: Don't call commit() on connection
connection.commit()  # ❌ AccessConnectionManager doesn't have commit()
```

---

**Last Updated:** 2025-11-16 Evening
**Next Session:** Start with order creation module design and implementation

**Session Notes:**
- User is actively testing pipelines and iterating quickly
- Database architecture is solid - no more 'main' showing up in module dropdowns
- Conda environment is working smoothly now
- Ready to tackle more complex modules (order creation with 75+ fields)
- Pipeline branching problem is acknowledged but deferred pending user's solution
