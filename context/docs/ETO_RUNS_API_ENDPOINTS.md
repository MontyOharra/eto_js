# ETO Runs API Endpoints Specification

## Overview
API endpoints for ETO (Email-to-Order) processing control and monitoring.

---

## Core Endpoints (MVP)

### 1. List ETO Runs
```
GET /api/eto-runs
```

**Query Parameters:**
- `status` (optional): Filter by status - `"not_started" | "processing" | "success" | "failure" | "needs_template" | "skipped"`
- `limit` (optional, default=50, max=200): Number of results
- `offset` (optional, default=0): Pagination offset
- `sort_by` (optional, default="started_at"): `"started_at" | "completed_at"`
- `sort_order` (optional, default="desc"): `"asc" | "desc"`

**Response:** Array of run list items
- `id`, `pdf_file_id`, `status`, `processing_step`
- `started_at`, `completed_at`
- `error_type`, `error_message` (if failure)

**Purpose:** Creates 6 separate views (one per status) for frontend tables

---

### 2. Get ETO Run Details
```
GET /api/eto-runs/{id}
```

**Response:** Complete run details including ALL stages
- Core run data (status, timestamps, errors)
- Stage 1: Template matching (status, matched template)
- Stage 2: Data extraction (status, extracted data JSON)
- Stage 3: Pipeline execution (status, executed actions, step-by-step trace)

**Different views by status:**
- **success**: All stages with full data
- **failure**: Partial stages, error details, which stage failed
- **needs_template**: Template matching results only

**Note:** All stage data returned in single response (no separate stage endpoints)

---

### 3. Create ETO Run
```
POST /api/eto-runs
```

**Request:** Multipart form-data
- `file`: PDF file to process

**Response:**
- `id`: Created run ID
- `status`: "not_started"
- `pdf_file_id`: Created PDF file ID

**Flow:**
1. Upload PDF and create `pdf_files` record
2. Create `eto_runs` record with status="not_started"
3. Background worker automatically picks up and processes

---

### 4. Reprocess ETO Runs (Bulk)
```
POST /api/eto-runs/reprocess
```

**Request Body:**
```json
{
  "run_ids": [1, 2, 3]
}
```

**For single run:** `{ "run_ids": [1] }`

**Flow (for each run):**
1. Verify status is "failure" or "skipped"
2. Delete all stage records (template_matching, extraction, pipeline_execution + steps)
3. Reset status to "not_started"
4. Clear error fields
5. Worker picks up and reprocesses from beginning

**Response:** 204 No Content

**Errors:**
- 404: One or more runs not found
- 400: One or more runs have invalid status (can only reprocess failure/skipped)

---

### 5. Skip ETO Runs (Bulk)
```
POST /api/eto-runs/skip
```

**Request Body:**
```json
{
  "run_ids": [1, 2, 3]
}
```

**For single run:** `{ "run_ids": [1] }`

**Flow (for each run):**
1. Verify status is "failure" or "needs_template"
2. Set status to "skipped"
3. Preserve all stage data

**Response:** 204 No Content

**Purpose:** Exclude from bulk reprocessing, indicate intentional decision

**Errors:**
- 404: One or more runs not found
- 400: One or more runs have invalid status (can only skip failure/needs_template)

---

### 6. Delete ETO Runs (Bulk)
```
DELETE /api/eto-runs
```

**Request Body:**
```json
{
  "run_ids": [1, 2, 3]
}
```

**For single run:** `{ "run_ids": [1] }`

**Flow (for each run):**
1. Verify status is "skipped"
2. Cascade delete all stage records
3. Delete run record
4. Optionally delete PDF file if not referenced elsewhere

**Response:** 204 No Content

**Restrictions:**
- Can only delete "skipped" runs
- Permanent deletion (no recovery)

**Errors:**
- 404: One or more runs not found
- 400: One or more runs have invalid status (can only delete skipped)

---

## Related Endpoints (Other Routers)

### PDF Viewing
```
GET /api/pdf-files/{pdf_file_id}
```
Used to view PDFs in run detail pages (uses existing pdf-files router)

---

## Status Transitions

```
not_started → processing → success
                         → failure
                         → needs_template

failure → not_started (reprocess)
        → skipped (skip)

needs_template → skipped (skip)

skipped → not_started (reprocess)
        → DELETED (permanent)
```

---

## Design Notes

1. **Bulk operations only** - All state-changing operations (reprocess/skip/delete) use bulk endpoints
   - Single operations send array with one ID: `{run_ids: [1]}`
   - Reduces endpoint count, simplifies API surface
2. **No separate stage endpoints** - All stage data in `GET /{id}`
3. **No statistics endpoint** - Future enhancement if needed
4. **PDF viewing** - Via existing `/api/pdf-files/{pdf_file_id}` endpoint
5. **Worker-driven** - All processing automatic via background worker
6. **Status-based views** - Frontend shows 6 separate tables (one per status)
7. **204 No Content** - Bulk operations return 204 (not updated run details)
