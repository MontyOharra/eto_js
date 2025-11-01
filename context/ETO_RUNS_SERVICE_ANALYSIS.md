# ETO Runs Service - Comprehensive Analysis

**File:** `server-new/src/features/eto_runs/service.py`
**Lines:** 1,292 lines
**Purpose:** Main orchestrator for Email-to-Order workflow with 3-stage processing

---

## Table of Contents
1. [Service Overview](#service-overview)
2. [Dependencies & Initialization](#dependencies--initialization)
3. [Method Inventory](#method-inventory)
4. [Problems Identified](#problems-identified)
5. [Recommendations](#recommendations)

---

## Service Overview

### Responsibilities
- Create ETO runs from PDF files
- Orchestrate 3-stage processing workflow:
  1. **Template Matching** - Match PDF to best template
  2. **Data Extraction** - Extract field values from PDF
  3. **Data Transformation** - Execute pipeline with extracted data
- Manage run lifecycle and status transitions
- Provide query operations for runs
- Handle errors and record failure details
- Background worker for processing runs

### Callers
- Email Ingestion Service (creates initial runs)
- ETO Worker (processes runs in background)
- API endpoints (query operations, manual triggers)

---

## Dependencies & Initialization

### Service Dependencies
```python
connection_manager: DatabaseConnectionManager
pdf_template_service: PdfTemplateService     # For template matching
pdf_files_service: PdfFilesService           # For PDF access
pipeline_execution_service: PipelineExecutionService  # For pipeline execution
```

### Repositories Initialized
```python
eto_run_repo: EtoRunRepository
pipeline_execution_repo: EtoRunPipelineExecutionRepository
template_matching_repo: EtoRunTemplateMatchingRepository
extraction_repo: EtoRunExtractionRepository
# TODO: pipeline_execution_step_repo (not yet initialized)
```

### Worker Configuration (from environment)
- `ETO_WORKER_ENABLED` (default: true)
- `ETO_MAX_CONCURRENT_RUNS` (default: 10)
- `ETO_POLLING_INTERVAL` (default: 2 seconds)
- `ETO_SHUTDOWN_TIMEOUT` (default: 30 seconds)

### Worker State
- `worker_running: bool` - Is worker active
- `worker_paused: bool` - Is worker paused (emergency stop)
- `worker_task: Optional[asyncio.Task]` - Current worker task
- `currently_processing_runs: Set[int]` - IDs being processed

---

## Method Inventory

### Public API Methods (Query Operations)

#### 1. `create_run(pdf_file_id: int) -> EtoRun` (Lines 161-208)
**Purpose:** Create new ETO run with status = "not_started"

**Implementation Status:** ✅ **COMPLETE**

**Process:**
1. Validates PDF file exists via `pdf_files_service.get_pdf_file()`
2. Creates run with `eto_run_repo.create()`
3. Broadcasts `run_created` event via SSE

**Error Handling:**
- Re-raises `ObjectNotFoundError` if PDF not found
- Wraps other errors in `ServiceError`

**Event Broadcasting:** ✅ Yes (run_created)

---

#### 2. `list_runs(...) -> List[EtoRun]` (Lines 210-247)
**Purpose:** List ETO runs with optional filtering, pagination, sorting

**Implementation Status:** ✅ **COMPLETE**

**Parameters:**
- `status: Optional[EtoRunStatus]` - Filter by status
- `limit: Optional[int]` - Max results
- `offset: Optional[int]` - Pagination offset
- `order_by: str` - Field to sort by (default: "created_at")
- `desc: bool` - Sort descending (default: True)

**Returns:** List of `EtoRun` dataclasses (core data only, no joins)

**Error Handling:** Wraps exceptions in `ServiceError`

**Note:** Returns basic run data only - no related data (PDF, email, template)

---

#### 3. `list_runs_with_relations(...) -> List[EtoRunListView]` (Lines 249-290)
**Purpose:** List runs with all related data for API list view

**Implementation Status:** ✅ **COMPLETE**

**Parameters:** Same as `list_runs()`

**Returns:** List of `EtoRunListView` with:
- Core run fields
- PDF file info (id, filename, size, page_count)
- Email source (if applicable)
- Matched template info (if applicable)

**Performance:** Single SQL query with LEFT JOINs (efficient)

**Usage:** Used by `GET /api/eto-runs` endpoint

---

#### 4. `get_run(run_id: int) -> EtoRun` (Lines 292-316)
**Purpose:** Get single ETO run by ID (core data only)

**Implementation Status:** ✅ **COMPLETE**

**Returns:** `EtoRun` dataclass

**Error Handling:** Raises `ObjectNotFoundError` if not found

**Note:** Does not fetch related stage data - only core run record

---

#### 5. `get_run_with_detail() -> EtoRunDetailView` (Lines 318-319)
**Purpose:** Get complete run detail with all stage data

**Implementation Status:** ❌ **STUB - NOT IMPLEMENTED**

**Expected Behavior:**
- Fetch core run data + PDF + email
- Fetch stage 1 data (template matching)
- Fetch stage 2 data (extraction with parsed JSON)
- Fetch stage 3 data (pipeline execution with parsed JSON)
- Return `EtoRunDetailView`

**Current State:** Empty pass statement

**Should Call:** `eto_run_repo.get_detail_with_stages()` (which we just implemented)

---

### Bulk Operation Methods

#### 6. `reprocess_runs(run_ids: List[int]) -> None` (Lines 323-403)
**Purpose:** Reprocess failed or skipped runs

**Implementation Status:** ✅ **COMPLETE**

**Workflow (per run):**
1. Validates run exists and status is "failure" or "skipped"
2. Deletes all stage records (template_matching, extraction, pipeline_execution)
3. Resets run to "not_started"
4. Clears error fields and timestamps
5. Broadcasts `run_updated` event

**Error Handling:**
- Raises `ObjectNotFoundError` if run not found
- Raises `ValidationError` if invalid status

**Event Broadcasting:** ✅ Yes (run_updated per run)

**Issue:** ⚠️ There's a **DUPLICATE METHOD** at lines 1252-1265 that raises `NotImplementedError`

---

#### 7. `skip_runs(run_ids: List[int]) -> None` (Lines 405-461)
**Purpose:** Mark runs as skipped

**Implementation Status:** ✅ **COMPLETE**

**Workflow (per run):**
1. Validates run exists and status is "failure" or "needs_template"
2. Sets status to "skipped"
3. Preserves all stage data

**Error Handling:**
- Raises `ObjectNotFoundError` if run not found
- Raises `ValidationError` if invalid status

**Event Broadcasting:** ✅ Yes (run_updated per run)

**Issue:** ⚠️ There's a **DUPLICATE METHOD** at lines 1267-1277 that raises `NotImplementedError`

---

#### 8. `delete_runs(run_ids: List[int]) -> None` (Lines 463-534)
**Purpose:** Permanently delete runs

**Implementation Status:** ✅ **COMPLETE**

**Workflow (per run):**
1. Validates run exists and status is "skipped"
2. Deletes all stage records explicitly
3. Deletes run record
4. Broadcasts `run_deleted` event

**Restrictions:** Can only delete "skipped" runs

**Error Handling:**
- Raises `ObjectNotFoundError` if run not found
- Raises `ValidationError` if invalid status

**Event Broadcasting:** ✅ Yes (run_deleted per run)

**Issue:** ⚠️ There's a **DUPLICATE METHOD** at lines 1279-1291 that raises `NotImplementedError`

---

### Processing Methods (Worker)

#### 9. `process_run(run_id: int) -> bool` (Lines 538-635)
**Purpose:** Execute full 3-stage ETO workflow

**Implementation Status:** ✅ **COMPLETE**

**Workflow:**
1. Updates status to "processing"
2. Broadcasts `run_updated` event
3. Calls `_execute_template_matching()`
4. Calls `_execute_data_extraction()`
5. Calls `_execute_data_transformation()`
6. Marks run as "success" or "failure"

**Error Handling:**
- Each stage wrapped in try-except
- Catches `Exception` and calls `_mark_run_failure()`
- Stage-specific error types: TemplateMatchingError, DataExtractionError, DataTransformationError
- Unexpected errors: UnexpectedSystemError

**Event Broadcasting:** ✅ Yes (run_updated at start)

**Returns:** `True` if successful, `False` if failed

---

#### 10. `_execute_template_matching(run_id: int) -> bool` (Lines 637-774)
**Purpose:** Stage 1 - Match PDF to template

**Implementation Status:** ✅ **COMPLETE**

**Process:**
1. Updates processing_step to "template_matching"
2. Creates template_matching record with status="processing"
3. Gets PDF objects from pdf_files_service
4. Calls `pdf_template_service.match_template()`
5. Handles match result:
   - **No match:** Updates run to "needs_template", returns False
   - **Match found:** Updates template_matching to "success", returns True

**Error Handling:**
- On error: Updates template_matching to "failure", re-raises exception
- Caught by `process_run()`'s try-except

**Event Broadcasting:** ✅ Yes (run_updated for processing_step and status changes)

**Returns:** `True` if match found, `False` if needs_template

---

#### 11. `_execute_data_extraction(run_id: int) -> bool` (Lines 776-843)
**Purpose:** Stage 2 - Extract data from PDF

**Implementation Status:** ⚠️ **STUB - FAKE DATA**

**Current Behavior:**
1. Updates processing_step to "data_extraction"
2. Creates extraction record
3. **Generates FAKE extracted data** (hardcoded invoice data)
4. Updates extraction to "success"

**Fake Data:**
```python
{
  "invoice_number": "FAKE-INV-12345",
  "invoice_date": "2025-10-29",
  "vendor_name": "Test Vendor Inc.",
  "total_amount": "1234.56",
  "line_items": [...]
}
```

**Event Broadcasting:** ✅ Yes (run_updated for processing_step)

**Returns:** `True` (always succeeds with fake data)

**TODO:** Replace with real extraction logic using matched template

---

#### 12. `_execute_data_transformation(run_id: int) -> bool` (Lines 845-914)
**Purpose:** Stage 3 - Execute pipeline with extracted data

**Implementation Status:** ⚠️ **STUB - FAKE DATA**

**Current Behavior:**
1. Updates processing_step to "data_transformation"
2. Creates pipeline_execution record
3. **Generates FAKE executed actions** (hardcoded steps)
4. Updates pipeline_execution to "success"

**Fake Data:**
```python
{
  "steps_executed": [
    {"step": "validate_invoice", "status": "success", ...},
    {"step": "transform_format", "status": "success", ...},
    {"step": "calculate_totals", "status": "success", ...}
  ],
  "total_steps": 3,
  "successful_steps": 3,
  "failed_steps": 0
}
```

**Event Broadcasting:** ✅ Yes (run_updated for processing_step)

**Returns:** `True` (always succeeds with fake data)

**TODO:** Replace with real pipeline execution using `pipeline_execution_service`

---

### Helper Methods

#### 13. `_mark_run_success(run_id: int) -> None` (Lines 918-944)
**Purpose:** Mark run as successfully completed

**Implementation Status:** ✅ **COMPLETE**

**Process:**
1. Updates status to "success"
2. Sets completed_at timestamp
3. Broadcasts `run_updated` event

---

#### 14. `_mark_run_failure(run_id, error, error_type) -> None` (Lines 946-985)
**Purpose:** Mark run as failed and record error details

**Implementation Status:** ✅ **COMPLETE**

**Process:**
1. Infers error_type from exception class if not provided
2. Updates status to "failure"
3. Sets error_type, error_message, completed_at
4. Broadcasts `run_updated` event

**Note:** `error_details` field set to None (TODO: Add stack trace)

---

### Background Worker Lifecycle

#### 15. `async startup() -> bool` (Lines 989-1009)
**Purpose:** Start background processing worker

**Implementation Status:** ✅ **COMPLETE**

**Process:**
1. Checks if worker_enabled (from environment)
2. Creates async task for `_continuous_processing_loop()`
3. Sets worker_running = True

**Returns:** `True` if started, `False` if disabled/already running

---

#### 16. `async shutdown(graceful: bool = True) -> bool` (Lines 1011-1055)
**Purpose:** Stop background worker

**Implementation Status:** ✅ **COMPLETE**

**Process:**
1. Sets worker_running = False
2. If graceful: Waits for current batch (with timeout)
3. If not graceful or timeout: Cancels worker_task
4. Calls `_reset_stuck_runs()` to clean up

**Returns:** `True` if stopped successfully

---

#### 17. `pause_worker() -> bool` (Lines 1057-1071)
**Purpose:** Pause worker (emergency stop without shutdown)

**Implementation Status:** ✅ **COMPLETE**

**Process:**
1. Sets worker_paused = True
2. Worker loop will skip processing but keep running

---

#### 18. `resume_worker() -> bool` (Lines 1073-1086)
**Purpose:** Resume worker from paused state

**Implementation Status:** ✅ **COMPLETE**

**Process:**
1. Sets worker_paused = False
2. Worker loop resumes processing

---

#### 19. `get_worker_status() -> Dict[str, Any]` (Lines 1088-1111)
**Purpose:** Get worker status and metrics

**Implementation Status:** ✅ **COMPLETE**

**Returns:**
```python
{
  "worker_enabled": bool,
  "worker_running": bool,
  "worker_paused": bool,
  "max_concurrent_runs": int,
  "polling_interval": int,
  "pending_runs_count": int,
  "currently_processing_count": int,
  "worker_task_active": bool
}
```

---

### Worker Polling Loop

#### 20. `async _continuous_processing_loop()` (Lines 1115-1143)
**Purpose:** Main worker loop - polls for pending runs

**Implementation Status:** ✅ **COMPLETE**

**Process:**
1. Runs while `worker_running == True`
2. Skips if `worker_paused == True`
3. Calls `_process_pending_runs_batch()`
4. Sleeps for `polling_interval` seconds
5. Handles `asyncio.CancelledError` for graceful shutdown
6. Doubles sleep interval on error to avoid tight loops

---

#### 21. `async _process_pending_runs_batch()` (Lines 1145-1185)
**Purpose:** Process batch of pending runs concurrently

**Implementation Status:** ✅ **COMPLETE**

**Process:**
1. Fetches up to `max_concurrent_runs` with status="not_started"
2. Creates async task for each run via `_process_run_async()`
3. Uses `asyncio.gather()` to run all concurrently
4. Logs batch results (successful vs failed)

**Concurrency:** Processes up to 10 runs simultaneously (configurable)

---

#### 22. `async _process_run_async(run_id: int) -> bool` (Lines 1187-1217)
**Purpose:** Async wrapper for processing single run

**Implementation Status:** ✅ **COMPLETE**

**Process:**
1. Adds run_id to `currently_processing_runs` set
2. Runs synchronous `process_run()` in thread pool via `loop.run_in_executor()`
3. Removes run_id from set in finally block

**Why Thread Pool:** `process_run()` is synchronous (uses sync repositories), so it runs in executor to avoid blocking event loop

---

#### 23. `async _reset_stuck_runs()` (Lines 1219-1248)
**Purpose:** Reset runs stuck in "processing" back to "not_started"

**Implementation Status:** ✅ **COMPLETE**

**When Called:** During worker shutdown

**Process:**
1. Finds all runs with status="processing"
2. Resets each to "not_started"
3. Clears processing_step and started_at

**Purpose:** Clean up orphaned runs if worker crashed

---

### Duplicate Methods (PROBLEMATIC)

#### 24. `reprocess_runs(run_ids: List[int]) -> None` (Lines 1252-1265)
**Status:** ❌ **DUPLICATE - RAISES NotImplementedError**

**Issue:** This is a DUPLICATE of the complete implementation at lines 323-403

---

#### 25. `skip_runs(run_ids: List[int]) -> None` (Lines 1267-1277)
**Status:** ❌ **DUPLICATE - RAISES NotImplementedError**

**Issue:** This is a DUPLICATE of the complete implementation at lines 405-461

---

#### 26. `delete_runs(run_ids: List[int]) -> None` (Lines 1279-1291)
**Status:** ❌ **DUPLICATE - RAISES NotImplementedError**

**Issue:** This is a DUPLICATE of the complete implementation at lines 463-534

---

## Problems Identified

### Critical Issues

#### 1. **Duplicate Method Definitions** (Lines 1252-1291)
**Severity:** 🔴 **CRITICAL**

**Problem:** Three methods have duplicate definitions:
- `reprocess_runs()` - Complete at 323-403, stub at 1252-1265
- `skip_runs()` - Complete at 405-461, stub at 1267-1277
- `delete_runs()` - Complete at 463-534, stub at 1279-1291

**Why This Happens:**
- Python allows method redefinition
- Second definition **OVERWRITES** the first
- The working implementations are **INACCESSIBLE**
- Calling these methods raises `NotImplementedError`

**Impact:**
- ❌ API endpoints for reprocess/skip/delete are **BROKEN**
- ❌ Cannot reprocess failed runs
- ❌ Cannot skip or delete runs

**Fix:** Delete lines 1250-1291 (the duplicate section under "Bulk Operations")

---

#### 2. **Incomplete `get_run_with_detail()` Method** (Lines 318-319)
**Severity:** 🔴 **CRITICAL**

**Problem:**
- Method is a stub with just `pass`
- Required by `GET /api/eto-runs/{id}` endpoint
- Endpoint will fail or return incomplete data

**Expected Implementation:**
```python
def get_run_with_detail(self, run_id: int) -> EtoRunDetailView:
    """Get complete run detail with all stage data."""
    from shared.database.repositories.pdf_template import PdfTemplateRepository
    from shared.database.repositories.pdf_template_version import PdfTemplateVersionRepository

    template_repo = PdfTemplateRepository(self.connection_manager)
    version_repo = PdfTemplateVersionRepository(self.connection_manager)

    detail = self.eto_run_repo.get_detail_with_stages(
        run_id=run_id,
        template_matching_repo=self.template_matching_repo,
        extraction_repo=self.extraction_repo,
        pipeline_execution_repo=self.pipeline_execution_repo,
        template_repo=template_repo,
        version_repo=version_repo
    )

    if not detail:
        raise ObjectNotFoundError(f"ETO run {run_id} not found")

    return detail
```

**Fix:** Implement method to call `eto_run_repo.get_detail_with_stages()`

---

### Medium Priority Issues

#### 3. **Fake Data in Extraction Stage** (Lines 776-843)
**Severity:** 🟡 **MEDIUM**

**Problem:**
- `_execute_data_extraction()` generates hardcoded fake data
- Not extracting real data from PDFs
- Prevents real end-to-end testing

**Current Fake Data:**
```python
fake_extracted_data = {
    "invoice_number": "FAKE-INV-12345",
    "invoice_date": "2025-10-29",
    "vendor_name": "Test Vendor Inc.",
    "total_amount": "1234.56",
    "line_items": [...]
}
```

**Expected Implementation:**
1. Get matched template version from template_matching stage
2. Get template's extraction_fields configuration
3. Call PDF extraction service with PDF objects + extraction_fields
4. Store real extracted data in JSON format

**Fix:** Implement real extraction using `pdf_template_service` or create new extraction service

---

#### 4. **Fake Data in Transformation Stage** (Lines 845-914)
**Severity:** 🟡 **MEDIUM**

**Problem:**
- `_execute_data_transformation()` generates hardcoded fake pipeline results
- Not executing real pipelines
- Prevents testing actual transformations

**Current Fake Data:**
```python
fake_executed_actions = {
    "steps_executed": [...],
    "total_steps": 3,
    "successful_steps": 3,
    "failed_steps": 0
}
```

**Expected Implementation:**
1. Get matched template version from template_matching stage
2. Get extracted data from extraction stage
3. Get template's pipeline definition
4. Call `pipeline_execution_service.execute_pipeline()` with extracted data
5. Store real execution results and step-by-step trace

**Fix:** Implement real pipeline execution using `pipeline_execution_service`

---

#### 5. **Missing Pipeline Execution Step Repository** (Lines 105, 138)
**Severity:** 🟡 **MEDIUM**

**Problem:**
- `pipeline_execution_step_repo` declared but commented out
- Needed for storing step-by-step execution trace
- Currently only storing summary in `pipeline_execution.executed_actions`

**TODO Comments:**
- Line 105: "TODO: Add remaining repositories when implemented"
- Line 138: "TODO: Initialize remaining repositories when implemented"

**Impact:**
- Cannot store detailed step-by-step execution logs
- Cannot debug pipeline failures at step level
- API cannot return execution trace

**Fix:**
1. Uncomment repository initialization
2. Update `_execute_data_transformation()` to create step records
3. Update `get_detail_with_stages()` to fetch steps if needed

---

#### 6. **Error Details Not Captured** (Line 969)
**Severity:** 🟡 **MEDIUM**

**Problem:**
- In `_mark_run_failure()`, `error_details` field set to `None`
- No stack trace or additional context captured

**Current Code:**
```python
error_details=None  # TODO: Add stack trace or additional context if needed
```

**Impact:**
- Hard to debug failures in production
- No context beyond error message

**Fix:**
```python
import traceback

error_details = traceback.format_exc()  # Capture full stack trace
```

---

### Low Priority Issues

#### 7. **Import Statement Duplication** (Line 17)
**Severity:** 🟢 **LOW**

**Problem:**
- `EtoRunPipelineExecutionRepository` imported twice (lines 14 and 17)

**Code:**
```python
from shared.database.repositories.eto_run_pipeline_execution import EtoRunPipelineExecutionRepository  # Line 14
from shared.database.repositories.eto_run_pipeline_execution import EtoRunPipelineExecutionRepository  # Line 17
```

**Fix:** Remove duplicate import

---

#### 8. **Commented-Out TODO Import** (Line 22)
**Severity:** 🟢 **LOW**

**Problem:**
- Line 22 has commented TODO that duplicates line 18

**Code:**
```python
from shared.database.repositories.eto_run_pipeline_execution_step import EtoRunPipelineExecutionStepRepository  # Line 18
# TODO: Import remaining repositories when implemented
# from shared.database.repositories.eto_run_pipeline_execution_step import EtoRunPipelineExecutionStepRepository  # Line 22
```

**Fix:** Delete commented line 22

---

#### 9. **Inconsistent Type Hints** (Line 107)
**Severity:** 🟢 **LOW**

**Problem:**
- `__init__` method has `-> None` return type annotation but some methods don't

**Not Critical:** All methods are properly typed in signatures, just inconsistent

---

#### 10. **Missing Error Detail in get_run()** (Line 315)
**Severity:** 🟢 **LOW**

**Problem:**
- Log message doesn't include `error_details` field (only logs status and processing_step)

**Line 315:**
```python
logger.debug(f"Retrieved ETO run {run_id}: status={run.status}, processing_step={run.processing_step}")
```

**Enhancement:** Add error info if status is "failure"

---

## Recommendations

### Immediate Actions (Must Fix)

1. **❗ Delete Duplicate Method Definitions** (Lines 1250-1291)
   - Remove entire "Bulk Operations" section at end of file
   - This immediately fixes broken reprocess/skip/delete endpoints

2. **❗ Implement `get_run_with_detail()`** (Lines 318-319)
   - Call `eto_run_repo.get_detail_with_stages()` we just built
   - Inject required repository dependencies
   - This fixes the detail endpoint

3. **❗ Remove Import Duplication** (Line 17)
   - Delete duplicate `EtoRunPipelineExecutionRepository` import
   - Remove commented TODO at line 22

---

### Short-Term Improvements

4. **Implement Real Data Extraction** (Lines 776-843)
   - Replace fake data with real extraction logic
   - Use matched template's extraction_fields configuration
   - Call extraction service/logic

5. **Implement Real Pipeline Execution** (Lines 845-914)
   - Replace fake data with real pipeline execution
   - Call `pipeline_execution_service.execute_pipeline()`
   - Store actual execution results and step trace

6. **Initialize Pipeline Execution Step Repository** (Lines 105, 138)
   - Uncomment repository initialization
   - Store step-by-step execution logs
   - Return steps in detail view

---

### Long-Term Enhancements

7. **Capture Error Details** (Line 969)
   - Store stack traces in `error_details` field
   - Helps with production debugging

8. **Enhanced Logging**
   - Add error_type/error_message to get_run() debug log
   - Add timing metrics for each stage
   - Add structured logging for monitoring

9. **Batch Operation Optimization**
   - Consider transaction wrapping for bulk operations
   - Add progress tracking for large batches
   - Add dry-run mode for validation

10. **Worker Metrics**
    - Track processing time per run
    - Track success/failure rates
    - Add health check endpoint

---

## Method Implementation Status Summary

| Method | Status | Line | Notes |
|--------|--------|------|-------|
| `create_run()` | ✅ Complete | 161-208 | Fully implemented |
| `list_runs()` | ✅ Complete | 210-247 | Fully implemented |
| `list_runs_with_relations()` | ✅ Complete | 249-290 | Fully implemented |
| `get_run()` | ✅ Complete | 292-316 | Fully implemented |
| `get_run_with_detail()` | ❌ Stub | 318-319 | **NEEDS IMPLEMENTATION** |
| `reprocess_runs()` | ⚠️ Broken | 323-403 | Overwritten by duplicate |
| `skip_runs()` | ⚠️ Broken | 405-461 | Overwritten by duplicate |
| `delete_runs()` | ⚠️ Broken | 463-534 | Overwritten by duplicate |
| `process_run()` | ✅ Complete | 538-635 | Fully implemented |
| `_execute_template_matching()` | ✅ Complete | 637-774 | Fully implemented |
| `_execute_data_extraction()` | ⚠️ Stub | 776-843 | Fake data |
| `_execute_data_transformation()` | ⚠️ Stub | 845-914 | Fake data |
| `_mark_run_success()` | ✅ Complete | 918-944 | Fully implemented |
| `_mark_run_failure()` | ✅ Complete | 946-985 | Fully implemented |
| `startup()` | ✅ Complete | 989-1009 | Fully implemented |
| `shutdown()` | ✅ Complete | 1011-1055 | Fully implemented |
| `pause_worker()` | ✅ Complete | 1057-1071 | Fully implemented |
| `resume_worker()` | ✅ Complete | 1073-1086 | Fully implemented |
| `get_worker_status()` | ✅ Complete | 1088-1111 | Fully implemented |
| `_continuous_processing_loop()` | ✅ Complete | 1115-1143 | Fully implemented |
| `_process_pending_runs_batch()` | ✅ Complete | 1145-1185 | Fully implemented |
| `_process_run_async()` | ✅ Complete | 1187-1217 | Fully implemented |
| `_reset_stuck_runs()` | ✅ Complete | 1219-1248 | Fully implemented |
| **DUPLICATE: `reprocess_runs()`** | ❌ Broken | 1252-1265 | **DELETE THIS** |
| **DUPLICATE: `skip_runs()`** | ❌ Broken | 1267-1277 | **DELETE THIS** |
| **DUPLICATE: `delete_runs()`** | ❌ Broken | 1279-1291 | **DELETE THIS** |

---

## Conclusion

The ETO Runs Service is **~85% complete** with a well-architected foundation:
- ✅ Worker lifecycle fully implemented
- ✅ Template matching stage complete
- ✅ Query operations complete
- ⚠️ 3 critical bugs preventing bulk operations
- ⚠️ 2 processing stages use fake data (intentional for testing)
- ❌ Detail view endpoint not implemented

**Priority:** Fix the 3 critical issues first (duplicate methods, implement get_run_with_detail), then tackle real extraction and transformation logic.
