# Session Continuity Document

## Current Status (2025-12-03)

### Session Summary

This session focused on two main areas:
1. **Frontend fixes** - Scrolling issues and status display in ETO list view
2. **Backend fixes** - Thread safety for Access database operations in output execution

---

## Recently Completed

### 1. ETO Run Detail Page Scrolling Fix

**Problem:** When viewing an ETO run detail page with many matched templates, users couldn't scroll down to see items at the bottom.

**Root Cause:** The `EtoRunDetailViewWrapper` component had `<div className="p-6">` without scroll handling, and was rendered inside a parent container with `overflow-hidden`.

**Fix:** Added `h-full overflow-auto` to both:
- `client/src/renderer/features/eto/components/EtoRunDetailView/EtoRunDetailViewWrapper.tsx` (line 282)
- `client/src/renderer/pages/dashboard/eto/$runId.tsx` (line 291)

### 2. ETO List View Status Display Fix

**Problem:** When runs had failed sub-runs, the status column showed a gray "-" instead of colored circles with counts.

**Root Cause:** The API returned `sub_runs: null` in the list view. The frontend fallback logic had a bug that only calculated page counts when there were NO failures.

**Solution:** Simplified the API to return sub-run counts by status instead of page counts.

**Backend Changes:**
- `server/src/api/schemas/eto_runs.py` - Simplified `EtoSubRunsSummary` to:
  ```python
  class EtoSubRunsSummary(BaseModel):
      status_counts: Dict[str, int]  # {"success": 2, "failure": 1, ...}
  ```
- `server/src/api/mappers/eto_runs.py` - Updated mapper to populate `status_counts`

**Frontend Changes:**
- `client/src/renderer/features/eto/types.ts` - Updated `EtoSubRunsSummary` interface
- `client/src/renderer/features/eto/components/EtoRunsTable/EtoRunsTable.tsx`:
  - Updated `StatusCell` to use `summary.status_counts` directly
  - Updated `ActionsCell` to use `statusCounts.failure` and `statusCounts.needs_template`

### 3. Thread Safety for Order Number Generation

**Problem:** When multiple worker threads processed sub-runs simultaneously, some failed with:
```
pyodbc.Error: ('HY010', '[HY010] [Microsoft][ODBC Driver Manager] Function sequence error (0) (SQLFetch)')
```

**Root Cause:**
- pyodbc has thread safety level 1 (threads cannot share connections)
- All worker threads were sharing the same Access database connection
- Concurrent cursor operations caused ODBC function sequence errors

**Solution:** Added a class-level threading lock to `OrderHelpers`:

```python
# server/src/features/pipeline_results/helpers/orders.py
import threading

class OrderHelpers:
    _order_number_lock = threading.Lock()

    def generate_next_order_number(self) -> float:
        with self._order_number_lock:
            # ... database operations now serialized
```

**Why this approach:**
- Order number generation must be atomic anyway (read-increment-write)
- Access has practical limit of ~10-20 concurrent connections for writes
- Simple solution with minimal code changes
- Lock is class-level so all threads share the same lock

---

## Architecture Notes

### Output Execution Flow

The current ETO processing pipeline has three stages:

```
Stage 1: Data Extraction
  └─ Extract fields from PDF using template bbox coordinates
  └─ Store in eto_sub_run_extractions table

Stage 2: Pipeline Execution
  └─ Execute transformation pipeline (modules)
  └─ Store steps in eto_sub_run_pipeline_execution_steps table
  └─ Returns PipelineExecutionResult with output_module_id and inputs

Stage 3: Output Execution (NEW)
  └─ If pipeline has output module, call PipelineResultService
  └─ OrderHelpers.generate_next_order_number() (thread-safe)
  └─ Store results in eto_sub_run_output_executions table
```

### Key Services

- **PipelineResultService** (`features/pipeline_results/service.py`)
  - Singleton registered in ServiceContainer
  - Manages output definitions (e.g., TestOutputDefinition)
  - Provides OrderHelpers to output definitions

- **OrderHelpers** (`features/pipeline_results/helpers/orders.py`)
  - Wraps Access database operations for order management
  - `generate_next_order_number()` - Thread-safe order number generation
  - Uses class-level `_order_number_lock` for serialization

- **ServiceContainer Eager Loading**
  - `pipeline_results` service is eagerly loaded at startup
  - Prevents race condition where multiple threads try to resolve ServiceProxy simultaneously

---

## Important Files Reference

### Backend - Output Execution
- `server/src/features/pipeline_results/service.py` - PipelineResultService
- `server/src/features/pipeline_results/helpers/orders.py` - OrderHelpers with thread-safe lock
- `server/src/features/pipeline_results/output_definitions/base.py` - OutputDefinitionBase
- `server/src/features/pipeline_results/output_definitions/test_output.py` - Test output module
- `server/src/features/eto_runs/service.py` - EtoRunsService with Stage 3 integration

### Backend - API Changes
- `server/src/api/schemas/eto_runs.py` - Simplified EtoSubRunsSummary
- `server/src/api/mappers/eto_runs.py` - status_counts mapping

### Frontend - ETO List/Detail
- `client/src/renderer/features/eto/types.ts` - Updated EtoSubRunsSummary type
- `client/src/renderer/features/eto/components/EtoRunsTable/EtoRunsTable.tsx` - StatusCell, ActionsCell
- `client/src/renderer/features/eto/components/EtoRunDetailView/EtoRunDetailViewWrapper.tsx` - Scroll fix
- `client/src/renderer/pages/dashboard/eto/$runId.tsx` - Scroll fix

---

## Known Issues & Considerations

### Access Database Limits
- Theoretical limit: 255 concurrent connections
- Practical limit: 10-20 simultaneous active users for writes
- Current mitigation: Thread lock serializes order number generation

### SSE Connection Management
- Single SSE connection established at page level (`eto/index.tsx`)
- Fallback polling every 10 seconds
- Fixed earlier issue with duplicate connections from nested components

---

## Next Session Priorities

### High Priority
1. **Real Output Module Implementation**
   - Create actual order output module (not just test)
   - Implement order creation in Access tables
   - Map pipeline outputs to order fields

2. **Output Execution Persistence**
   - Verify eto_sub_run_output_executions table is being populated
   - Add output execution details to sub-run detail view

### Medium Priority
3. **Error Handling Improvements**
   - Better error messages for output execution failures
   - Retry logic for transient database errors

4. **Performance Monitoring**
   - Track order number generation times
   - Monitor lock contention under load

### Low Priority
5. **Testing**
   - Unit tests for OrderHelpers
   - Integration tests for output execution flow

---

## Testing Commands

```bash
# Run server (from server directory)
make dev

# The server will process ETO runs with output execution
# Check logs for "[TEST OUTPUT]" messages

# Access database order numbers are in:
# - HTC300_G040_T000 Last OrderNo Assigned (LON table)
# - HTC300_G040_T005 Orders In Work (OIW table)
```

---

**Last Updated:** 2025-12-03 Evening
**Next Session:** Continue with real order output module implementation

**Session Notes:**
- Thread safety issue resolved with class-level lock
- Frontend status display now shows sub-run counts correctly
- Scrolling issues fixed on detail pages
- Output execution pipeline is functional with test module
