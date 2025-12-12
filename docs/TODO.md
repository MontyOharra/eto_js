# ETO System - TODO List

This document tracks outstanding issues and features to be implemented. Each item will be expanded with detailed requirements as we work through them.

---

## 1. Pipeline Execution Error Display

**Status:** COMPLETED

**Issue:** Errors are not being displayed on modules within the executed pipeline viewer in the ETO sub-run detail view, even though client-side support exists and works correctly in simulation mode.

**Root Cause Identified:**
Mismatch between error save format and retrieve format:

1. **Saving** (`eto_runs/service.py:1013`): Error is saved as a plain string
   ```python
   error=step_result.error  # "ValueError: some message"
   ```
   **Confirmed:** Errors ARE being saved to DB correctly as strings (verified in database query)

2. **Retrieving** (`api/mappers/eto_runs.py:340-342`): Mapper expects a dict
   ```python
   error_data = PipelineExecutionStepError(
       type=error.get("type", ""),     # Fails: string has no .get()
       message=error.get("message", ""),
       details=error.get("details"),
   )
   ```
   This raises `AttributeError` which is silently caught, resulting in `error: null` in API response.

**Solution Options:**
1. **Fix on save**: Serialize error as JSON dict `{"type": "ExceptionType", "message": "error message"}` before saving
2. **Fix on retrieve**: Handle string format in the mapper (parse "ExceptionType: message" into type/message)

**Recommended:** Option 2 - Fix on retrieve side since errors are already saved correctly as strings. Parse the string format `"ExceptionType: message"` into `{type, message}` structure.

**Files Modified:**
- `server/src/api/mappers/eto_runs.py` - Parse string error into PipelineExecutionStepError object
- `server/src/features/eto_runs/service.py` - Fixed silent error discarding in `get_sub_run_detail()` where `json.loads()` was failing on plain string errors

**Fix Applied:** Both the mapper and service now handle string error format correctly. The service preserves the original string when JSON parsing fails, and the mapper parses "ExceptionType: message" format into structured error objects.

---

## 2. Pipeline Output Visibility in ETO Details

**Status:** Not Started

**Issue:** Need to display pipeline output data from the list view in the ETO details page for successful sub-runs.

**Details:**
- Success sub-runs should show what data was extracted/transformed
- Output should be visible without having to drill into each module
- Consider a summary view of key outputs

---

## 3. Pending Order Confirmation Workflow

**Status:** Not Started

**Issue:** Orders are being created immediately. Need a pending/confirmation state where users must approve creation.

**Details:**
- Add new status state for orders awaiting user confirmation
- System should process orders to this pending state instead of auto-creating
- User must explicitly confirm before HTC order creation
- Consider batch approval functionality

---

## 4. Order Update Functionality

**Status:** Not Started

**Issue:** Update functionality for existing orders has not been built out.

**Details:**
- pending_updates table exists but UI workflow is incomplete
- Need UI to review proposed updates
- Approve/reject workflow for field changes
- Apply approved updates to HTC database

---

## 5. Templates Page Improvements

**Status:** Not Started

**Issues:**
1. Templates are filtered on frontend, should be backend-filtered (like ETO page)
2. Need filter/toggle for autoskip templates
3. Card components take too much space and don't show enough useful data

**Details:**
- Add backend filtering endpoint with query parameters
- Add autoskip filter option
- Redesign template cards to be more compact and informative
- Consider list view option vs card grid

---

## 6. Pending Orders Page Improvements

**Status:** Not Started

**Issue:** Pending orders page needs improvements (details TBD).

**Details:**
- To be discussed and expanded during review
- May include: better filtering, sorting, bulk actions, improved detail view

---

## 7. Remove Pipelines Page

**Status:** Not Started

**Issue:** The standalone pipelines page can be removed.

**Details:**
- Pipeline management is done through template builder
- Remove route and page component
- Clean up any dead navigation links

---

## 8. Email Sending for Order Management

**Status:** Not Started

**Issue:** Need email notifications as part of order management process.

**Details:**
- Send emails on order creation
- Send emails on order updates
- Make email functionality configurable via settings page
- Consider: recipients, templates, enable/disable toggle

---

## 9. New Pipeline Modules

**Status:** Not Started

**Issue:** Need general-purpose regex and LLM modules.

### 9a. Regex Module
- General regex pattern matching/extraction
- Configurable pattern input
- Multiple capture group support

### 9b. LLM Module
- Similar to SQL lookup module pattern
- Long text input with referenceable pass-in values
- Example: `"Please extract important info from {notes_input}. Return in datetime format..."`
- **Challenge:** Need to design customizable output schema
  - How to define expected output structure?
  - Type inference for downstream connections?
  - Validation of LLM responses?

---

## 10. IDE / Syntax Error Cleanup

**Status:** Not Started

**Issue:** General cleanup of IDE warnings and syntax errors across codebase.

**Details:**
- Review TypeScript errors/warnings
- Review Python linting issues
- Fix any type mismatches
- Remove unused imports/variables

---

## 11. HTC Database Configuration

**Status:** Not Started

**Issue:** HTC database connection is only configurable via environment variables. Need in-app configuration.

**Details:**
- Add settings page section for HTC database configuration
- Store connection settings in application database or config file
- Support for connection testing
- Migrate from env-only to app-configurable approach
- Consider security implications of storing credentials

---

## 12. Access Database Concurrent Query Errors (ODBC Function Sequence Error)

**Status:** COMPLETED

**Issue:** When multiple pipeline modules attempt to query the Access database simultaneously during batch processing, ODBC "Function Sequence Error" occurs.

**Error from logs:**
```
pyodbc.Error: ('HY010', '[HY010] [Microsoft][ODBC Driver Manager] Function sequence error (0) (SQLRowCount)')
```

**Root Cause:**
- Access databases via pyodbc do not handle concurrent queries well on a shared connection
- When Dask executes multiple pipeline modules in parallel, they all try to use the same Access connection
- This causes cursor conflicts and "function sequence errors"

**Solution Applied:** Serialize Access DB queries using threading lock

**Files Modified:**
1. `server/src/shared/database/access_connection.py`
   - Added `with self._lock:` around cursor operations in the `cursor()` context manager
   - All Access DB operations are now serialized to prevent concurrent access errors

2. `server/src/shared/database/data_database_manager.py`
   - Changed `get_connection()` to return `AccessConnectionManager` instance instead of raw pyodbc connection
   - Ensures pipeline modules use the thread-safe `cursor()` method

---

## Priority Notes

_To be determined as we review each item._

---

## Completed Items

_Items will be moved here as they are completed._
