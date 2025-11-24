# ETO Multi-Template Refactoring Progress

**Date Started:** 2025-01-24
**Status:** In Progress

---

## Overview

Refactoring the ETO service from single-template processing to multi-template support. The key architectural change is moving processing logic from parent `eto_runs` to child `eto_sub_runs`.

**Old Flow:** Worker processes parent runs → Three stages (matching, extraction, pipeline) for entire PDF

**New Flow:** Template matching on creation → Worker processes sub-runs → Two stages (extraction, pipeline) per page set

---

## Completed Tasks ✅

### 1. Database Types & Repositories
- ✅ Created `eto_sub_runs` types and repository
- ✅ Created `eto_sub_run_extractions` types and repository
- ✅ Created `eto_sub_run_pipeline_executions` types and repository
- ✅ Created `eto_sub_run_pipeline_execution_steps` types and repository
- ✅ Removed `sequence` field from all sub-run types/repositories
- ✅ Updated `eto_runs` types (removed template matching, added sub-run aggregations)
- ✅ Updated `eto_run` repository (get_all_with_relations, get_detail_with_stages)

### 2. Service Layer - Infrastructure
- ✅ Updated imports (removed old single-template types, added sub-run types)
- ✅ Updated repository initialization (replaced old repos with sub-run repos)
- ✅ Updated worker callbacks:
  - `process_run_callback` → `process_sub_run`
  - `get_pending_runs_callback` → gets sub-runs with `status="not_started"`
  - `reset_run_callback` → `_reset_sub_run_to_not_started`

### 3. Service Layer - Core Methods
- ✅ Rewrote `create_run()`:
  - Creates parent run with `status="processing"`
  - Immediately runs multi-template matching
  - Creates sub-runs (matched with `status="not_started"`, unmatched with `status="needs_template"`)
  - Returns parent run
- ✅ Added `process_sub_run(sub_run_id)`:
  - Called by worker for sub-runs
  - Coordinates extraction + pipeline stages
  - Updates parent run status after completion

---

## In Progress 🚧

### Service Layer - Stage Processing Methods

**Location:** `server/src/features/eto_runs/service.py` after line 485

Need to add these methods after `process_sub_run()` and before bulk operations section:

1. **`_process_sub_run_extraction(sub_run_id)`** - Extract data from sub-run pages only
2. **`_process_sub_run_pipeline(sub_run_id, extracted_data)`** - Execute pipeline for sub-run
3. **`_extract_data_from_pdf_pages(pdf_file_id, extraction_fields, page_numbers)`** - Wrapper for page-filtered extraction

---

## Pending Tasks 📋

### 1. Service Layer - Helper Methods

Add to service.py after stage processing methods:

```python
def _mark_sub_run_success(self, sub_run_id: int) -> None:
    """Mark sub-run as successfully completed."""

def _mark_sub_run_failure(self, sub_run_id: int, error: Exception, error_type: Optional[str] = None) -> None:
    """Mark sub-run as failed and record error details."""

def _update_parent_run_status(self, run_id: int) -> None:
    """Update parent run status based on all sub-run statuses."""

def _reset_sub_run_to_not_started(self, sub_run_id: int) -> None:
    """Reset a sub-run back to not_started status (worker cleanup)."""
```

### 2. Extraction Utility - Page Filtering

**File:** `server/src/features/eto_runs/utils/extraction.py`

Add new function:
```python
def extract_data_from_pdf_pages(
    pdf_file_service,
    pdf_file_id: int,
    extraction_fields: list,
    page_numbers: list[int]
) -> list:
    """Extract data from PDF, filtered to specific pages only."""
```

This should call the existing `extract_data_from_pdf()` and filter results to only specified pages.

### 3. Remove Old Methods

Delete from service.py (currently at line ~704):
- `process_run(run_id)` - Replaced by `process_sub_run()`
- `_process_template_matching(run_id)` - Now done in `create_run()`
- `_process_data_extraction(run_id, version_id)` - Replaced by `_process_sub_run_extraction()`
- `_process_pipeline_execution(run_id, version_id, extracted_data)` - Replaced by `_process_sub_run_pipeline()`
- `_mark_run_success(run_id)` - Replaced by `_mark_sub_run_success()`
- `_mark_run_failure(run_id, error, error_type)` - Replaced by `_mark_sub_run_failure()`
- `_reset_run_to_not_started(run_id)` - Replaced by `_reset_sub_run_to_not_started()`
- `_extract_data_from_pdf(pdf_file_id, extraction_fields)` - Will be replaced by page-filtered version

### 4. Update __init__ Files

**File:** `server/src/shared/types/__init__.py`

Add exports:
```python
from .eto_sub_runs import (
    EtoSubRun,
    EtoSubRunCreate,
    EtoSubRunUpdate,
    EtoSubRunDetailView,
)
from .eto_sub_run_extractions import (
    EtoSubRunExtraction,
    EtoSubRunExtractionCreate,
    EtoSubRunExtractionUpdate,
)
from .eto_sub_run_pipeline_executions import (
    EtoSubRunPipelineExecution,
    EtoSubRunPipelineExecutionCreate,
    EtoSubRunPipelineExecutionUpdate,
)
from .eto_sub_run_pipeline_execution_steps import (
    EtoSubRunPipelineExecutionStep,
    EtoSubRunPipelineExecutionStepCreate,
    EtoSubRunPipelineExecutionStepUpdate,
)
```

**File:** `server/src/shared/database/repositories/__init__.py`

Add exports:
```python
from .eto_sub_run import EtoSubRunRepository
from .eto_sub_run_extraction import EtoSubRunExtractionRepository
from .eto_sub_run_pipeline_execution import EtoSubRunPipelineExecutionRepository
from .eto_sub_run_pipeline_execution_step import EtoSubRunPipelineExecutionStepRepository
```

### 5. Bulk Operations (DEFERRED)

**DO NOT IMPLEMENT YET** - Will build after main process works:
- `reprocess_runs(run_ids)` - Delete failed sub-runs, re-run template matching
- `skip_runs(run_ids)` - Mark failed/needs_template sub-runs as skipped
- `delete_runs(run_ids)` - Already works (cascade delete), just needs testing

---

## Testing Checklist (After Implementation)

1. ✅ Create run → template matching → sub-runs created
2. ⏳ Worker picks up sub-runs (not parent runs)
3. ⏳ Sub-run processes: extraction → pipeline → success
4. ⏳ Parent status updates when all sub-runs complete
5. ⏳ Multi-template PDF: Multiple sub-runs process independently
6. ⏳ Unmatched pages: sub-run with status="needs_template" created
7. ⏳ Error handling: Sub-run failures don't fail parent

---

## Key Architectural Decisions

1. **No `not_started` on parent runs** - Parent goes directly to `"processing"` on creation
2. **Template matching is synchronous** - Happens immediately in `create_run()`, not in worker
3. **Worker processes sub-runs only** - Worker no longer touches parent runs
4. **Parent status aggregation**:
   - `"processing"`: Has active sub-runs (not_started or processing)
   - `"success"`: All sub-runs completed (regardless of individual success/failure)
   - `"failure"`: Reserved for critical template matching errors only
5. **Removed `sequence` field** - Sub-runs sorted by first page number instead

---

## Important Notes

- Parent run `status="failure"` is ONLY for critical orchestration errors (template matching crashes)
- Individual sub-run failures do NOT cause parent failure
- Sub-runs with `status="needs_template"` are NOT picked up by worker
- Page filtering in extraction is critical - must only extract from sub-run's pages

---

## Files Modified

### Types
- `server/src/shared/types/eto_runs.py` - Updated for multi-template
- `server/src/shared/types/eto_sub_runs.py` - NEW
- `server/src/shared/types/eto_sub_run_extractions.py` - NEW
- `server/src/shared/types/eto_sub_run_pipeline_executions.py` - NEW
- `server/src/shared/types/eto_sub_run_pipeline_execution_steps.py` - NEW

### Repositories
- `server/src/shared/database/repositories/eto_run.py` - Updated for sub-runs
- `server/src/shared/database/repositories/eto_sub_run.py` - NEW
- `server/src/shared/database/repositories/eto_sub_run_extraction.py` - NEW
- `server/src/shared/database/repositories/eto_sub_run_pipeline_execution.py` - NEW
- `server/src/shared/database/repositories/eto_sub_run_pipeline_execution_step.py` - NEW

### Service
- `server/src/features/eto_runs/service.py` - MAJOR REFACTOR (in progress)

### Utils
- `server/src/features/eto_runs/utils/extraction.py` - Need to add page filtering (pending)

---

## Next Immediate Steps

1. Add `_process_sub_run_extraction()` method to service.py
2. Add `_process_sub_run_pipeline()` method to service.py
3. Add `_extract_data_from_pdf_pages()` wrapper method to service.py
4. Add page-filtered extraction function to utils/extraction.py
5. Add helper methods (_mark_sub_run_success, _mark_sub_run_failure, _update_parent_run_status, _reset_sub_run_to_not_started)
6. Remove old methods (process_run and all _process_* stage methods)
7. Update __init__ files
8. Test end-to-end flow
9. Build bulk operations (reprocess/skip) after main flow works
