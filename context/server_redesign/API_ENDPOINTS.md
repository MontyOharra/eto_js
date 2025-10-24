# API Endpoints Specification

## Status: In Progress

**Current Phase:** Phase 3 - Endpoint Definitions

---

## Overview

This document defines the complete HTTP API specification for the ETO backend server. For business logic and requirements, see `API_DESIGN.md`.

### Design Principles

- **RESTful conventions** where appropriate
- **Direct responses** (no wrapper objects - FastAPI style)
- **HTTP status codes indicate success/failure**
- **Clear status codes** (200, 201, 400, 404, 409, 500)
- **No `created_at`/`updated_at`** in responses (audit-only fields)
- **Validation at API boundary** (Pydantic schemas)

---

## Response Conventions

### Success Responses

Return data directly (no `success` wrapper):

**Single Resource:**
```typescript
{
  "id": number,
  "name": string,
  // ... actual data fields
}
```

**List/Collection:**
```typescript
[
  {"id": 1, "name": "Item 1"},
  {"id": 2, "name": "Item 2"}
]
```

**List with Pagination:**
```typescript
{
  "items": [...],
  "total": number,
  "page": number,
  "limit": number
}
```

---

### Error Responses

**Standard Error (FastAPI Default):**
```typescript
{
  "detail": string | object
}
```

**Validation Error (422 - FastAPI automatic):**
```typescript
{
  "detail": [
    {
      "loc": ["body", "field_name"],
      "msg": "error message",
      "type": "error_type"
    }
  ]
}
```

---

### Common HTTP Status Codes

- **200 OK**: Successful GET, PUT, PATCH, POST (non-creation)
- **201 Created**: Successful POST (resource created)
- **204 No Content**: Successful DELETE with no response body
- **400 Bad Request**: Business logic error, invalid operation
- **404 Not Found**: Resource does not exist
- **409 Conflict**: State conflict (e.g., cannot delete active config)
- **422 Unprocessable Entity**: Validation error (Pydantic automatic)
- **500 Internal Server Error**: Unexpected server error

---

## Router 1: `/email-configs` - Email Ingestion Configuration

> See `API_DESIGN.md` Domain 1 for business rules and requirements.

**Router Status**: ✅ Reviewed

### Endpoints Overview

| Method | Path | Description | Reviewed |
|--------|------|-------------|----------|
| GET | `/email-configs` | List all configurations (summary) | ✅ |
| GET | `/email-configs/{id}` | Get configuration details | ✅ |
| POST | `/email-configs` | Create new configuration | ✅ |
| PUT | `/email-configs/{id}` | Update configuration | ✅ |
| DELETE | `/email-configs/{id}` | Delete configuration | ✅ |
| POST | `/email-configs/{id}/activate` | Activate configuration | ✅ |
| POST | `/email-configs/{id}/deactivate` | Deactivate configuration | ✅ |
| GET | `/email-configs/discovery/accounts` | List available email accounts | ✅ |
| GET | `/email-configs/discovery/folders` | List folders for account | ✅ |
| POST | `/email-configs/validate` | Validate configuration | ✅ |

---

### `GET /email-configs`

**Description:** List all email configurations with summary information.

**Query Parameters:**
- `order_by` (optional): `name` | `is_active` | `last_check_time` (default: `name`)
- `desc` (optional): `true` | `false` (default: `false`)

**Response:** `200 OK`
```typescript
[
  {
    "id": number,
    "name": string,
    "is_active": boolean,
    "last_check_time": string | null // ISO 8601 datetime
  }
]
```

**Errors:**
- `500`: `{"detail": "Database error"}`

---

### `GET /email-configs/{id}`

**Description:** Get full configuration details by ID.

**Path Parameters:**
- `id`: Configuration ID (integer)

**Response:** `200 OK`
```typescript
{
  "id": number,
  "name": string,
  "description": string | null,
  "email_address": string,
  "folder_name": string,
  "filter_rules": [
    {
      "field": "sender_email" | "subject" | "has_attachments" | "attachment_types",
      "operation": "contains" | "equals" | "starts_with" | "ends_with",
      "value": string,
      "case_sensitive": boolean
    }
  ],
  "poll_interval_seconds": number,
  "max_backlog_hours": number,
  "error_retry_attempts": number,
  "is_active": boolean,
  "activated_at": string | null,
  "is_running": boolean,
  "last_check_time": string | null,
  "last_error_message": string | null,
  "last_error_at": string | null
}
```

**Errors:**
- `404`: `{"detail": "Configuration not found"}`
- `500`: `{"detail": "Database error"}`

---

### `POST /email-configs`

**Description:** Create new email configuration.

**Request Body:**
```typescript
{
  "name": string, // required, 1-255 chars
  "description"?: string, // optional, max 1000 chars
  "email_address": string, // required, valid email
  "folder_name": string, // required, min 1 char
  "filter_rules"?: [
    {
      "field": "sender_email" | "subject" | "has_attachments" | "attachment_types",
      "operation": "contains" | "equals" | "starts_with" | "ends_with",
      "value": string,
      "case_sensitive"?: boolean // default: false
    }
  ], // optional, default: []
  "poll_interval_seconds"?: number, // optional, min: 5, default: 5
  "max_backlog_hours"?: number, // optional, min: 1, default: 24
  "error_retry_attempts"?: number // optional, min: 1, max: 10, default: 3
}
```

**Response:** `201 Created`
```typescript
{
  // Same structure as GET /email-configs/{id}
  "id": number,
  "name": string,
  // ... all fields
}
```

**Errors:**
- `422`: Pydantic validation error (invalid fields, constraints violated)
- `500`: `{"detail": "Database error"}`

---

### `PUT /email-configs/{id}`

**Description:** Update existing configuration. **Must be deactivated first.**

**Path Parameters:**
- `id`: Configuration ID (integer)

**Request Body:**
```typescript
{
  "description"?: string | null,
  "filter_rules"?: [...], // same structure as POST
  "poll_interval_seconds"?: number, // min: 5
  "max_backlog_hours"?: number, // min: 1
  "error_retry_attempts"?: number // min: 1, max: 10
}
```
*Note: All fields optional. Only provided fields are updated.*

**Response:** `200 OK`
```typescript
{
  // Same structure as GET /email-configs/{id}
}
```

**Errors:**
- `404`: `{"detail": "Configuration not found"}`
- `409`: `{"detail": "Cannot update active configuration. Deactivate first."}`
- `422`: Pydantic validation error
- `500`: `{"detail": "Database error"}`

---

### `DELETE /email-configs/{id}`

**Description:** Delete configuration. **Must be deactivated first.**

**Path Parameters:**
- `id`: Configuration ID (integer)

**Response:** `204 No Content`

*(No response body)*

**Errors:**
- `404`: `{"detail": "Configuration not found"}`
- `409`: `{"detail": "Cannot delete active configuration. Deactivate first."}`
- `500`: `{"detail": "Database error"}`

---

### `POST /email-configs/{id}/activate`

**Description:** Activate configuration (starts email monitoring).

**Path Parameters:**
- `id`: Configuration ID (integer)

**Response:** `200 OK`
```typescript
{
  // Updated configuration with is_active: true, activated_at set
  "id": number,
  "is_active": true,
  "activated_at": string,
  // ... all other fields
}
```

**Errors:**
- `404`: `{"detail": "Configuration not found"}`
- `500`: `{"detail": "Failed to activate configuration"}` (service startup error)

---

### `POST /email-configs/{id}/deactivate`

**Description:** Deactivate configuration (stops email monitoring).

**Path Parameters:**
- `id`: Configuration ID (integer)

**Response:** `200 OK`
```typescript
{
  // Updated configuration with is_active: false
  "id": number,
  "is_active": false,
  // ... all other fields
}
```

**Errors:**
- `404`: `{"detail": "Configuration not found"}`
- `500`: `{"detail": "Failed to deactivate configuration"}` (service shutdown error)

---

### `GET /email-configs/discovery/accounts`

**Description:** List available email accounts for configuration wizard Step 1. Only returns accounts that are accessible by the server.

**Response:** `200 OK`
```typescript
[
  {
    "email_address": string,
    "display_name": string | null
  }
]
```

**Errors:**
- `500`: `{"detail": "Email service connection error"}`

---

### `GET /email-configs/discovery/folders`

**Description:** List available folders for selected email account (wizard Step 2).

**Query Parameters:**
- `email_address` (required): Email account to query

**Response:** `200 OK`
```typescript
[
  {
    "folder_name": string,
    "folder_path": string // full path
  }
]
```

**Errors:**
- `400`: `{"detail": "Missing or invalid email_address parameter"}`
- `404`: `{"detail": "Email account not found or inaccessible"}`
- `500`: `{"detail": "Email service connection error"}`

---

### `POST /email-configs/validate`

**Description:** Validate configuration before creation (wizard Step 4). Tests connection only. Returns 200 if valid, 400 if invalid.

**Request Body:**
```typescript
{
  "email_address": string,
  "folder_name": string
  // Other config fields not needed for validation
}
```

**Response:** `200 OK` (Configuration is valid)
```typescript
{
  "email_address": string,
  "folder_name": string,
  "message": "Configuration is valid"
}
```

**Errors:**
- `400`: Configuration is invalid
  - `{"detail": "Cannot connect to email account"}`
  - `{"detail": "Folder does not exist or is not accessible"}`
  - `{"detail": "Invalid email address format"}`
- `422`: Pydantic validation error (missing fields)
- `500`: `{"detail": "Email service error"}`

---

## Router 2: `/eto-runs` - ETO Processing Control

> See `API_DESIGN.md` Domain 2 for business rules and requirements.

**Router Status**: ✅ Reviewed

### Endpoints Overview

| Method | Path | Description | Reviewed |
|--------|------|-------------|----------|
| GET | `/eto-runs` | List runs with optional status filtering, sorting, and pagination | ✅ |
| GET | `/eto-runs/{id}` | Get full run details including all stage results and execution logs | ✅ |
| POST | `/eto-runs/upload` | Create new run via manual PDF upload | ✅ |
| POST | `/eto-runs/reprocess` | Reprocess runs (bulk): reset to not_started, clear stage records | ✅ |
| POST | `/eto-runs/skip` | Skip runs (bulk): set status to skipped | ✅ |
| DELETE | `/eto-runs` | Delete runs (bulk): permanently remove (only if skipped) | ✅ |

---

### `GET /eto-runs`

**Description:** List ETO runs with summary information including PDF details, source info, and matched template summary.

**Query Parameters:**
- `status` (optional): `not_started` | `processing` | `success` | `failure` | `needs_template` | `skipped` (default: all)
- `sort_by` (optional): `created_at` | `started_at` | `completed_at` | `status` (default: `started_at`)
- `sort_order` (optional): `asc` | `desc` (default: `desc`)
- `limit` (optional): number (default: 50, max: 200)
- `offset` (optional): number (default: 0)

**Response:** `200 OK`
```typescript
{
  "items": [
    {
      // Core run info
      "id": number,
      "status": "not_started" | "processing" | "success" | "failure" | "needs_template" | "skipped",
      "processing_step": "template_matching" | "data_extraction" | "data_transformation" | null,
      "started_at": string | null,        // ISO 8601
      "completed_at": string | null,      // ISO 8601
      "error_type": string | null,
      "error_message": string | null,

      // PDF information
      "pdf": {
        "id": number,
        "original_filename": string,
        "file_size": number | null
      },

      // Source information
      "source": {
        "type": "manual" | "email",

        // Email-specific fields (only present when type = "email")
        "sender_email"?: string,
        "received_date"?: string,          // ISO 8601
        "subject"?: string | null,
        "folder_name"?: string
      },

      // Matched template summary (null if no template found)
      "matched_template": {
        "template_id": number,
        "template_name": string,
        "version_id": number,
        "version_num": number
      } | null
    }
  ],
  "total": number,
  "limit": number,
  "offset": number
}
```

**Notes:**
- List view includes brief matched template summary for navigation
- `matched_template` is null if no template was found during processing
- Does NOT include full stage objects (template_matching, data_extraction, pipeline_execution) - those are detail-view only
- Does NOT include `page_count` in PDF info (list view optimization)

**Errors:**
- `400`: `{"detail": "Invalid query parameters"}`
- `500`: `{"detail": "Database error"}`

---

### `GET /eto-runs/{id}`

**Description:** Get full ETO run details including PDF info, source info, and all processing stage results.

**Path Parameters:**
- `id`: Run ID (integer)

**Response:** `200 OK`
```typescript
{
  // Core run info
  "id": number,
  "status": "not_started" | "processing" | "success" | "failure" | "needs_template" | "skipped",
  "processing_step": "template_matching" | "data_extraction" | "data_transformation" | null,
  "started_at": string | null,        // ISO 8601
  "completed_at": string | null,      // ISO 8601
  "error_type": string | null,
  "error_message": string | null,

  // PDF information (enriched with page_count for detail view)
  "pdf": {
    "id": number,
    "original_filename": string,
    "file_size": number | null,
    "page_count": number | null       // Included in detail view
  },

  // Source information
  "source": {
    "type": "manual" | "email",

    // Email-specific fields (only present when type = "email")
    "sender_email"?: string,
    "received_date"?: string,          // ISO 8601
    "subject"?: string | null,
    "folder_name"?: string
  },

  // Stage 1: Template Matching
  "template_matching": {
    "status": "not_started" | "success" | "failure" | "skipped",
    "started_at": string | null,
    "completed_at": string | null,
    "error_message": string | null,
    "matched_template": {
      "template_id": number,
      "template_name": string,
      "version_id": number,
      "version_num": number
    } | null
  },

  // Stage 2: Data Extraction
  "data_extraction": {
    "status": "not_started" | "success" | "failure" | "skipped",
    "started_at": string | null,
    "completed_at": string | null,
    "error_message": string | null,
    "extracted_data": {
      // JSON object - structure varies by template
      // Key-value pairs of extracted field names and values
      [key: string]: any
    } | null
  },

  // Stage 3: Pipeline Execution
  "pipeline_execution": {
    "status": "not_started" | "success" | "failure" | "skipped",
    "started_at": string | null,
    "completed_at": string | null,
    "error_message": string | null,

    // Pipeline definition reference (from matched template version)
    // Enables lazy-loading full pipeline graph via GET /pipelines/{id}
    "pipeline_definition_id": number,

    // Pipeline-level summary of executed actions (JSON from eto_run_pipeline_executions.executed_actions)
    // List of action modules executed with their input data
    "executed_actions": [
      {
        "action_module_name": string,    // Name of the action module (e.g., "Send Email", "Create File")
        "inputs": {
          [input_name: string]: any      // Input name → value passed to the action
        }
      }
    ] | null,

    // Individual pipeline steps (from eto_run_pipeline_execution_steps table)
    "steps": [
      {
        "id": number,                    // Step record ID
        "step_number": number,           // Execution order (1-based)
        "module_instance_id": string,    // Module instance identifier

        // Step inputs: node_id → { name, value, type }
        // Keys are node_ids from pipeline definition (e.g., "i1", "i2")
        // Enables frontend to map values to specific pins on graph visualization
        "inputs": {
          [node_id: string]: {
            "name": string,              // Pin name (e.g., "text", "separator")
            "value": any,                // Actual value passed to this input pin
            "type": string               // Runtime type (e.g., "str", "int", "bool")
          }
        } | null,

        // Step outputs: node_id → { name, value, type }
        // Keys are node_ids from pipeline definition (e.g., "o1", "o2")
        "outputs": {
          [node_id: string]: {
            "name": string,              // Pin name (e.g., "result", "success")
            "value": any,                // Actual value produced by this output pin
            "type": string               // Runtime type
          }
        } | null,

        // Structured error object (only present if step failed)
        "error": {
          "type": string,                // Error class name (e.g., "ValidationError", "TypeError")
          "message": string,             // Human-readable error message
          "details"?: any                // Optional structured error details
        } | null
      }
    ]
  }
}
```

**Notes:**
- Detail view includes `page_count` in PDF info (list view does not)
- Each stage has consistent structure: status, timestamps, error_message
- `matched_template` is null if no template was found during template matching
- `extracted_data` structure varies by template - frontend must handle dynamic keys
- `executed_actions` is the JSON field from `eto_run_pipeline_executions` table - duplicates step information as a summary
- `steps` array corresponds to `eto_run_pipeline_execution_steps` table records
- `steps` array is empty if pipeline execution hasn't started or was skipped
- `steps` are ordered by `step_number` (execution order determined by Dask DAG)
- Steps do not have individual status/timestamps - error presence indicates failure
- **Step Input/Output Structure:**
  - Uses `node_id` as dictionary key (matches pipeline definition node IDs)
  - Each entry includes `name` (pin label), `value` (actual data), and `type` (runtime type)
  - Enables frontend to map execution data directly to pins on graph visualization
  - When execution fails at module M: inputs are recorded, outputs are null, error is present
  - All subsequent modules after failure are NOT recorded (execution stops)
- **Pipeline Visualization:** `pipeline_definition_id` enables lazy-loading of full pipeline graph:
  - Initial load: Get run details (~100KB) with pipeline reference
  - On-demand: Fetch `GET /pipelines/{pipeline_definition_id}` only when user views Detail tab (~50KB)
  - Avoids embedding full pipeline_state in every ETO run response
  - Same pipeline definition can be cached and reused across multiple runs
- **Response Size Warning:** This endpoint can return large payloads (>1MB) for runs with:
  - Large extracted_data (100+ fields from complex PDFs)
  - Long pipelines (20+ steps with detailed inputs/outputs)
  - Lazy-loading architecture helps mitigate this issue

**Errors:**
- `404`: `{"detail": "Run not found"}`
- `500`: `{"detail": "Database error"}`

---

### `POST /eto-runs/upload`

**Description:** Create new ETO run via manual PDF upload.

**Request:** `multipart/form-data`
- `pdf_file`: File (required, PDF only)

**Response:** `201 Created`
```typescript
{
  "id": number,
  "pdf_file_id": number,
  "status": "not_started",
  "processing_step": null,
  "started_at": null,
  "completed_at": null
}
```

**Errors:**
- `400`: `{"detail": "Missing PDF file or invalid file type"}`
- `500`: `{"detail": "File storage error or database error"}`

---

### `POST /eto-runs/reprocess`

**Description:** Reprocess runs (bulk operation). Resets runs to `not_started` and clears all stage records. Validates each run before processing. **Atomic operation** - fails entirely if any validation fails.

**Request Body:**
```typescript
{
  "run_ids": number[] // array of run IDs to reprocess
}
```

**Validation Rules:**
- Run must exist
- Run status must NOT be `processing`
- Run status must NOT be `success` (cannot reprocess successful runs)

**Response:** `204 No Content`

*(No response body)*

**Errors:**
- `400`: Validation failed for one or more runs
  - `{"detail": "Run 123 is currently processing"}`
  - `{"detail": "Run 456 has already succeeded"}`
  - `{"detail": "Cannot reprocess successful runs: [123, 456]"}`
- `404`: `{"detail": "One or more runs not found: [123, 456]"}`
- `422`: Pydantic validation error (invalid request body)
- `500`: `{"detail": "Database error"}`

---

### `POST /eto-runs/skip`

**Description:** Skip runs (bulk operation). Sets run status to `skipped`. Validates each run before processing. **Atomic operation** - fails entirely if any validation fails.

**Request Body:**
```typescript
{
  "run_ids": number[] // array of run IDs to skip
}
```

**Validation Rules:**
- Run must exist
- Run status must NOT be `processing`
- Run status must NOT be `success` (cannot skip successful runs)

**Response:** `204 No Content`

*(No response body)*

**Errors:**
- `400`: Validation failed for one or more runs
  - `{"detail": "Run 123 is currently processing"}`
  - `{"detail": "Run 456 has already succeeded"}`
  - `{"detail": "Cannot skip successful runs: [123, 456]"}`
- `404`: `{"detail": "One or more runs not found: [123, 456]"}`
- `422`: Pydantic validation error (invalid request body)
- `500`: `{"detail": "Database error"}`

---

### `DELETE /eto-runs`

**Description:** Delete runs (bulk operation). Permanently removes runs from database. **Only allowed if all runs have `skipped` status.** **Atomic operation** - fails entirely if any validation fails.

**Request Body:**
```typescript
{
  "run_ids": number[] // array of run IDs to delete
}
```

**Validation Rules:**
- Run must exist
- Run status MUST be `skipped` (can only delete skipped runs)

**Response:** `204 No Content`

*(No response body)*

**Errors:**
- `400`: Validation failed for one or more runs
  - `{"detail": "Run 123 status is not skipped"}`
  - `{"detail": "Can only delete skipped runs. Invalid runs: [123, 456]"}`
- `404`: `{"detail": "One or more runs not found: [123, 456]"}`
- `422`: Pydantic validation error (invalid request body)
- `500`: `{"detail": "Database error"}`

---

## Router 3: `/pdf-files` - PDF File Access

**Router Status**: ✅ Reviewed

**Implementation Note**: PDF objects are stored as JSON in the `extracted_objects` field of the `pdf_files` table. There is no separate `pdf_objects` table. Objects are extracted using pdfplumber and stored in a grouped dict structure that matches the API response format.

### Endpoints Overview

| Method | Path | Description | Reviewed |
|--------|------|-------------|----------|
| GET | `/pdf-files/{id}` | Get PDF file metadata | ✅ |
| GET | `/pdf-files/{id}/download` | Download/stream PDF file bytes | ✅ |
| GET | `/pdf-files/{id}/objects` | Get extracted PDF objects (for template building) | ✅ |
| POST | `/pdf-files/process-objects` | Process uploaded PDF and extract objects (no persistence) | ✅ |

---

### `GET /pdf-files/{id}`

**Description:** Get PDF file metadata (filename, size, page count, etc.).

**Path Parameters:**
- `id`: PDF file ID (integer)

**Response:** `200 OK`
```typescript
{
  "id": number,
  "email_id": number | null,
  "filename": string,
  "original_filename": string,
  "relative_path": string,
  "file_size": number | null, // bytes
  "file_hash": string | null,
  "page_count": number | null
}
```

**Errors:**
- `404`: `{"detail": "PDF file not found"}`
- `500`: `{"detail": "Database error"}`

---

### `GET /pdf-files/{id}/download`

**Description:** Download or stream PDF file bytes for viewing. Returns raw PDF bytes with appropriate headers for browser rendering.

**Path Parameters:**
- `id`: PDF file ID (integer)

**Response:** `200 OK`
- **Content-Type:** `application/pdf`
- **Content-Disposition:** `inline; filename="<original_filename>"`
- **Body:** Raw PDF bytes (streamed)

**Usage:**
- Embed in iframe: `<iframe src="/pdf-files/123/download" />`
- Fetch and create blob URL for PDF.js viewer

**Errors:**
- `404`: `{"detail": "PDF file not found"}`
- `500`: `{"detail": "File system error or file not accessible"}`

---

### `GET /pdf-files/{id}/objects`

**Description:** Get extracted PDF objects for template building. Returns all objects extracted during PDF processing (used in template wizard Step 1 for signature object selection). Objects are grouped by type for easier frontend consumption.

**Path Parameters:**
- `id`: PDF file ID (integer)

**Response:** `200 OK`
```typescript
{
  "pdf_file_id": number,
  "page_count": number,
  "objects": {
    "text_words": [
      {
        "page": number,
        "bbox": [number, number, number, number], // [x0, y0, x1, y1]
        "text": string,
        "fontname": string,
        "fontsize": number
      }
    ],
    "text_lines": [
      {
        "page": number,
        "bbox": [number, number, number, number]  // [x0, y0, x1, y1]
      }
    ],
    "graphic_rects": [
      {
        "page": number,
        "bbox": [number, number, number, number], // [x0, y0, x1, y1]
        "linewidth": number
      }
    ],
    "graphic_lines": [
      {
        "page": number,
        "bbox": [number, number, number, number], // [x0, y0, x1, y1]
        "linewidth": number
      }
    ],
    "graphic_curves": [
      {
        "page": number,
        "bbox": [number, number, number, number], // [x0, y0, x1, y1]
        "points": [[number, number], [number, number], ...], // Array of [x, y] coordinate pairs
        "linewidth": number
      }
    ],
    "images": [
      {
        "page": number,
        "bbox": [number, number, number, number], // [x0, y0, x1, y1]
        "format": string,      // e.g., "JPEG", "PNG"
        "colorspace": string,  // e.g., "RGB", "CMYK"
        "bits": number         // Bit depth
      }
    ],
    "tables": [
      {
        "page": number,
        "bbox": [number, number, number, number], // [x0, y0, x1, y1]
        "rows": number,
        "cols": number
      }
    ]
  }
}
```

**Notes:**
- Objects are grouped by type (7 types total)
- Retrieved from the `extracted_objects` JSON field in the `pdf_files` table
- Objects extracted using pdfplumber during PDF storage
- Coordinates are rounded to 3 decimal places for consistency
- Each array can be empty if no objects of that type were found
- Frontend should iterate through each object type separately

**Errors:**
- `404`: `{"detail": "PDF file not found"}`
- `500`: `{"detail": "Database error or invalid objects data"}`

---

### `POST /pdf-files/process-objects`

**Description:** Process uploaded PDF file and extract objects without database persistence. Used during template creation with manual PDF upload. Returns same object structure as `GET /pdf-files/{id}/objects` but for temporary files.

**Request:** `multipart/form-data`
- `pdf_file`: File (required, PDF only)

**Response:** `200 OK`
```typescript
{
  "page_count": number,
  "objects": {
    "text_words": [
      {
        "page": number,
        "bbox": [number, number, number, number], // [x0, y0, x1, y1]
        "text": string,
        "fontname": string,
        "fontsize": number
      }
    ],
    "text_lines": [
      {
        "page": number,
        "bbox": [number, number, number, number]  // [x0, y0, x1, y1]
      }
    ],
    "graphic_rects": [
      {
        "page": number,
        "bbox": [number, number, number, number], // [x0, y0, x1, y1]
        "linewidth": number
      }
    ],
    "graphic_lines": [
      {
        "page": number,
        "bbox": [number, number, number, number], // [x0, y0, x1, y1]
        "linewidth": number
      }
    ],
    "graphic_curves": [
      {
        "page": number,
        "bbox": [number, number, number, number], // [x0, y0, x1, y1]
        "points": [[number, number], [number, number], ...], // Array of [x, y] coordinate pairs
        "linewidth": number
      }
    ],
    "images": [
      {
        "page": number,
        "bbox": [number, number, number, number], // [x0, y0, x1, y1]
        "format": string,      // e.g., "JPEG", "PNG"
        "colorspace": string,  // e.g., "RGB", "CMYK"
        "bits": number         // Bit depth
      }
    ],
    "tables": [
      {
        "page": number,
        "bbox": [number, number, number, number], // [x0, y0, x1, y1]
        "rows": number,
        "cols": number
      }
    ]
  }
}
```

**Notes:**
- **No database persistence** - Pure PDF processing operation
- PDF is not stored on server - processed in-memory and discarded
- Used when creating templates from manually uploaded PDFs
- Returns same object structure as `GET /pdf-files/{id}/objects` for consistency
- Objects grouped by type (7 types total)
- Coordinates are rounded to 3 decimal places
- Each array can be empty if no objects of that type were found

**Usage Flow:**
1. User uploads PDF in template builder
2. Frontend calls this endpoint to extract objects
3. Objects displayed in signature object step
4. PDF and objects kept in browser until template save
5. On save, PDF uploaded again (via POST /pdf-templates with multipart)

**Errors:**
- `400`: `{"detail": "Missing PDF file or invalid file type"}`
- `422`: `{"detail": "Invalid PDF file - corrupted or unreadable"}`
- `500`: `{"detail": "PDF processing error: [specific error]"}`

---

## Router 4: `/pdf-templates` - PDF Template Management

> See `API_DESIGN.md` Domain 3 for business rules and requirements.

**Router Status**: ✅ Reviewed

### Endpoints Overview

| Method | Path | Description | Reviewed |
|--------|------|-------------|----------|
| GET | `/pdf-templates` | List all templates (summary with pagination) | ✅ |
| GET | `/pdf-templates/{id}` | Get full template details (with current version data and version list) | ✅ |
| POST | `/pdf-templates` | Create new template (accepts pdf_file_id + wizard data) | ✅ |
| PUT | `/pdf-templates/{id}` | Update template (creates new version from wizard data) | ✅ |
| POST | `/pdf-templates/{id}/activate` | Set template status to active | ✅ |
| POST | `/pdf-templates/{id}/deactivate` | Set template status to inactive | ✅ |
| GET | `/pdf-templates/{id}/versions/{version_id}` | Get specific version details | ✅ |
| POST | `/pdf-templates/simulate` | Simulate full ETO process without DB persistence | ✅ |

---

### `GET /pdf-templates`

**Description:** List all templates with summary information including version counts and usage statistics.

**Query Parameters:**
- `status` (optional): `active` | `inactive` (default: all statuses)
- `sort_by` (optional): `name` | `status` | `usage_count` (default: `name`)
- `sort_order` (optional): `asc` | `desc` (default: `asc`)
- `limit` (optional): number (default: 50, max: 200)
- `offset` (optional): number (default: 0)

**Response:** `200 OK`
```typescript
{
  "items": [
    {
      "id": number,
      "name": string,
      "description": string | null,
      "status": "active" | "inactive",
      "source_pdf_id": number,

      // Current version summary
      "current_version": {
        "version_id": number,
        "version_num": number,
        "usage_count": number  // ETO runs that used this version
      },

      "total_versions": number  // Count of all versions for this template
    }
  ],
  "total": number,
  "limit": number,
  "offset": number
}
```

**Notes:**
- `status` is `inactive` during initial creation (after POST /pdf-templates), becomes `active` after activation
- `current_version` represents the version currently used for template matching
- `total_versions` includes all finalized versions

**Errors:**
- `400`: `{"detail": "Invalid query parameters"}`
- `500`: `{"detail": "Database error"}`

---

### `GET /pdf-templates/{id}`

**Description:** Get full template details including current version's signature objects, extraction fields, and pipeline reference, plus list of all available versions.

**Path Parameters:**
- `id`: Template ID (integer)

**Response:** `200 OK`
```typescript
{
  // Template metadata
  "id": number,
  "name": string,
  "description": string | null,
  "source_pdf_id": number,
  "status": "active" | "inactive",
  "current_version_id": number,

  // Current version details (denormalized for convenience)
  "current_version": {
    "version_id": number,
    "version_num": number,
    "usage_count": number,
    "last_used_at": string | null,  // ISO 8601

    // Signature objects (from Step 1 of wizard)
    "signature_objects": [
      {
        "object_type": "text_word" | "text_line" | "graphic_rect" | "graphic_line" | "graphic_curve" | "image" | "table",
        "page": number,
        "bbox": [number, number, number, number],  // [x0, y0, x1, y1]
        // Additional properties vary by object_type (matching /pdf-files/{id}/objects structure)
      }
    ],

    // Extraction fields (from Step 2 of wizard)
    "extraction_fields": [
      {
        "name": string,
        "description": string,
        "bbox": [number, number, number, number],  // [x0, y0, x1, y1]
        "page": number
      }
    ],

    // Pipeline reference (from Step 3 of wizard)
    "pipeline_definition_id": number
  },

  // Version history summary
  "total_versions": number,

  // All available versions (for version selection dropdown)
  "available_versions": [
    {
      "version_id": number,
      "version_num": number,
      "created_at": string  // ISO 8601
    }
  ]
}
```

**Notes:**
- Current version data is denormalized into response for convenience
- `available_versions` list enables frontend version selection without separate API call
- To view full details of different version, use `GET /pdf-templates/{id}/versions/{version_id}`
- Pipeline details retrieved via pipelines endpoints (if needed)

**Errors:**
- `404`: `{"detail": "Template not found"}`
- `500`: `{"detail": "Database error"}`

---

### `POST /pdf-templates`

**Description:** Create new template from wizard data (final save). Creates template + version 1 atomically. Sets status to `inactive` initially (user must activate).

**Request:** `multipart/form-data`
```typescript
{
  "name": string,                    // required, 1-255 chars
  "description"?: string,             // optional, max 1000 chars
  "source_pdf_id"?: number | null,   // optional - for existing PDFs
  // pdf_file: File (if source_pdf_id is null - multipart form field)

  // Step 1: Signature objects
  "signature_objects": [
    {
      "object_type": "text_word" | "text_line" | "graphic_rect" | "graphic_line" | "graphic_curve" | "image" | "table",
      "page": number,
      "bbox": [number, number, number, number],
      // Additional properties matching object type from PDF extraction
    }
  ],  // required, min: 1 object

  // Step 2: Extraction fields
  "extraction_fields": [
    {
      "name": string,
      "description": string,
      "bbox": [number, number, number, number],  // [x0, y0, x1, y1]
      "page": number
    }
  ],  // required, min: 1 field

  // Step 3: Pipeline definition
  "pipeline_state": {
    "entry_points": [...],   // See pipeline structure in API_DESIGN.md Domain 5
    "modules": [...],
    "connections": [...]
  },
  "visual_state": {
    "positions": {...}
  }
}
```

**Response:** `201 Created`
```typescript
{
  "id": number,                       // Created template ID
  "name": string,
  "status": "inactive",               // Always starts as inactive
  "current_version_id": number,       // Version 1 ID
  "current_version_num": 1,
  "pipeline_definition_id": number    // Created pipeline ID
}
```

**Notes:**
- Creates template + version 1 + pipeline definition atomically
- Template starts with `status = "inactive"` (must call activate to use for matching)
- Pipeline compilation happens during this operation (transparent to frontend)
- Backend may deduplicate compiled plan if identical pipeline already exists
- PDF can be provided via `source_pdf_id` (existing PDF) OR `pdf_file` (upload new PDF)
- If `pdf_file` provided, PDF is stored and `source_pdf_id` is generated automatically

**Errors:**
- `400`: Business logic errors
  - `{"detail": "Source PDF not found or not accessible"}`
  - `{"detail": "Signature objects must reference valid PDF objects"}`
  - `{"detail": "Extraction field bboxes must be within PDF page bounds"}`
  - `{"detail": "Pipeline validation failed: [specific error]"}`
- `422`: Pydantic validation error (missing/invalid fields)
- `500`: `{"detail": "Database error or pipeline compilation error"}`

---

### `PUT /pdf-templates/{id}`

**Description:** Update template by creating new version. Increments version number, updates current_version_id. Template can be active or inactive during update.

**Path Parameters:**
- `id`: Template ID (integer)

**Request Body:**
```typescript
{
  // Optional: Update template metadata
  "name"?: string,                    // optional, 1-255 chars
  "description"?: string,             // optional, max 1000 chars

  // Required: New version data (all 3 wizard steps)
  "signature_objects": [
    {
      "object_type": "text_word" | "text_line" | "graphic_rect" | "graphic_line" | "graphic_curve" | "image" | "table",
      "page": number,
      "bbox": [number, number, number, number],
      // Additional properties matching object type
    }
  ],  // required, min: 1 object

  "extraction_fields": [
    {
      "name": string,
      "description": string,
      "bbox": [number, number, number, number],  // [x0, y0, x1, y1]
      "page": number
    }
  ],  // required, min: 1 field

  "pipeline_state": {
    "entry_points": [...],
    "modules": [...],
    "connections": [...]
  },
  "visual_state": {
    "positions": {...}
  }
}
```

**Response:** `200 OK`
```typescript
{
  "id": number,
  "name": string,
  "status": "active" | "inactive",            // Status unchanged
  "current_version_id": number,               // Updated to new version ID
  "current_version_num": number,              // Incremented version number
  "pipeline_definition_id": number            // New pipeline ID
}
```

**Notes:**
- Creates new version with incremented version_num (e.g., 1 → 2)
- Updates template's current_version_id to new version
- Old version preserved for historical ETO runs
- Template status unchanged (active templates remain active)
- Pipeline compilation happens during update

**Errors:**
- `404`: `{"detail": "Template not found"}`
- `400`: Business logic errors (same as POST /pdf-templates)
- `422`: Pydantic validation error
- `500`: `{"detail": "Database error or pipeline compilation error"}`

---

### `POST /pdf-templates/{id}/activate`

**Description:** Set template status to `active`. Makes template available for ETO run template matching.

**Path Parameters:**
- `id`: Template ID (integer)

**Response:** `200 OK`
```typescript
{
  "id": number,
  "status": "active",
  "current_version_id": number
}
```

**Notes:**
- Template must have at least one finalized version
- Only active templates are considered during ETO template matching

**Errors:**
- `404`: `{"detail": "Template not found"}`
- `400`: `{"detail": "Template has no finalized versions"}`
- `500`: `{"detail": "Database error"}`

---

### `POST /pdf-templates/{id}/deactivate`

**Description:** Set template status to `inactive`. Removes template from ETO run template matching (archived).

**Path Parameters:**
- `id`: Template ID (integer)

**Response:** `200 OK`
```typescript
{
  "id": number,
  "status": "inactive",
  "current_version_id": number
}
```

**Notes:**
- Inactive templates are not considered during template matching
- Historical ETO runs that used this template are unaffected
- Can be reactivated at any time

**Errors:**
- `404`: `{"detail": "Template not found"}`
- `500`: `{"detail": "Database error"}`

---

### `GET /pdf-templates/{id}/versions/{version_id}`

**Description:** Get full details for a specific template version including signature objects, extraction fields, and pipeline definition.

**Path Parameters:**
- `id`: Template ID (integer)
- `version_id`: Version ID (integer)

**Response:** `200 OK`
```typescript
{
  "version_id": number,
  "template_id": number,
  "version_num": number,
  "usage_count": number,
  "last_used_at": string | null,  // ISO 8601
  "is_current": boolean,          // true if this is template's current_version_id

  // Full version data (all 3 wizard steps)
  "signature_objects": [
    {
      "object_type": "text_word" | "text_line" | "graphic_rect" | "graphic_line" | "graphic_curve" | "image" | "table",
      "page": number,
      "bbox": [number, number, number, number],
      // Additional properties matching object type
    }
  ],

  "extraction_fields": [
    {
      "name": string,
      "description": string,
      "bbox": [number, number, number, number],  // [x0, y0, x1, y1]
      "page": number
    }
  ],

  "pipeline_definition_id": number
}
```

**Notes:**
- Returns complete version data for viewing or editing
- Frontend can use this to populate wizard when editing from specific version
- Pipeline details retrieved separately via pipelines router if needed

**Errors:**
- `404`: `{"detail": "Template or version not found"}`
- `500`: `{"detail": "Database error"}`

---

### `POST /pdf-templates/simulate`

**Description:** Simulate full ETO process (template matching → data extraction → pipeline execution) without database persistence. Used for testing during template creation/editing. Action modules simulate only (no actual execution).

**Request:** `multipart/form-data` (discriminated union)

**Variant 1 - Stored PDF:**
```typescript
{
  "pdf_source": "stored",
  "pdf_file_id": number,              // required when pdf_source = "stored"

  // Template definition to test (all 3 wizard steps)
  "signature_objects": [
    {
      "object_type": string,
      "page": number,
      "bbox": [number, number, number, number],
      // Additional properties
    }
  ],

  "extraction_fields": [
    {
      "name": string,
      "description": string,
      "bbox": [number, number, number, number],  // [x0, y0, x1, y1]
      "page": number
    }
  ],

  "pipeline_state": {
    "entry_points": [...],
    "modules": [...],
    "connections": [...]
  }
}
```

**Variant 2 - Uploaded PDF:**
```typescript
{
  "pdf_source": "upload",
  // pdf_file: File (multipart form field)

  // Template definition to test (all 3 wizard steps)
  "signature_objects": [
    {
      "object_type": string,
      "page": number,
      "bbox": [number, number, number, number],
      // Additional properties
    }
  ],

  "extraction_fields": [
    {
      "name": string,
      "description": string,
      "bbox": [number, number, number, number],  // [x0, y0, x1, y1]
      "page": number
    }
  ],

  "pipeline_state": {
    "entry_points": [...],
    "modules": [...],
    "connections": [...]
  }
}
```

**Response:** `200 OK`
```typescript
{
  // Stage 1: Template Matching (always succeeds in simulation)
  "template_matching": {
    "status": "success",
    "message": "Simulation mode - template matching skipped"
  },

  // Stage 2: Data Extraction
  "data_extraction": {
    "status": "success" | "failure",
    "extracted_data": {
      // Key-value pairs matching extraction field labels
      [field_label: string]: string  // Extracted text from bounding boxes
    } | null,
    "error_message": string | null,
    "validation_results": [
      {
        "field_label": string,
        "required": boolean,
        "has_value": boolean,
        "regex_valid": boolean | null,  // null if no regex
        "error": string | null
      }
    ]
  },

  // Stage 3: Pipeline Execution
  "pipeline_execution": {
    "status": "success" | "failure",
    "error_message": string | null,

    // Transformation steps with data flow
    "steps": [
      {
        "step_number": number,
        "module_instance_id": string,
        "module_name": string,          // Human-readable module name
        "inputs": {
          [node_name: string]: {
            "value": any,
            "type": string
          }
        },
        "outputs": {
          [node_name: string]: {
            "value": any,
            "type": string
          }
        },
        "error": object | null
      }
    ],

    // Simulated actions (not actually executed)
    "simulated_actions": [
      {
        "action_module_name": string,
        "inputs": {
          [input_name: string]: any
        },
        "simulation_note": "Action not executed - simulation mode"
      }
    ]
  }
}
```

**Notes:**
- **No database persistence** - pure computation
- Template matching always succeeds (testing extraction/transformation only)
- Extraction validation runs (required fields, regex patterns)
- Pipeline executes with actual transformation logic
- Action modules simulate (return what would be executed, but don't execute)
- Can be called repeatedly during wizard (modify and re-test)
- Pipeline compilation happens in-memory (not saved)

**Errors:**
- `404`: `{"detail": "PDF file not found"}`
- `400`: Validation errors
  - `{"detail": "Signature objects must reference valid PDF objects"}`
  - `{"detail": "Extraction field bboxes must be within PDF page bounds"}`
  - `{"detail": "Pipeline validation failed: [specific error]"}`
- `422`: Pydantic validation error
- `500`: `{"detail": "Simulation error: [specific error]"}`

---

## Router 5: `/modules` - Module Catalog Viewing

> See `API_DESIGN.md` Domain 4 for business rules and requirements.

**Router Status**: ✅ Reviewed

### Endpoints Overview

| Method | Path | Description | Reviewed |
|--------|------|-------------|----------|
| GET | `/modules` | List all active modules (complete catalog for pipeline builder) | ✅ |

---

### `GET /modules`

**Description:** List all active modules for pipeline builder. Returns complete module catalog with metadata, I/O definitions, and configuration schemas. No pagination - returns all active modules in single request for frontend caching.

**Query Parameters:**
- `module_kind` (optional): `transform` | `action` | `logic` | `entry_point` (default: all kinds)
- `category` (optional): string - Filter by category (e.g., "Text Processing", "Data Validation")
- `search` (optional): string - Text search on name and description

**Response:** `200 OK`
```typescript
[
  {
    "id": string,                     // Module identifier
    "version": string,                // Module version (e.g., "1.0.0")
    "name": string,                   // Display name
    "description": string,            // User-facing description
    "color": string,                  // UI display color (hex code)
    "category": string,               // e.g., "Text Processing", "Actions", "Logic"
    "module_kind": "transform" | "action" | "logic" | "entry_point",

    // I/O node definitions and metadata
    "meta": {
      "inputs": [
        {
          "id": string,
          "name": string,
          "type": string[],           // Allowed types (e.g., ["string", "number"])
          "required": boolean,
          "description": string
        }
      ],
      "outputs": [
        {
          "id": string,
          "name": string,
          "type": string[],           // Output types
          "description": string
        }
      ]
      // Future: additional metadata fields
    },

    // JSON Schema for configuration UI (dynamic form generation)
    "config_schema": {
      "type": "object",
      "properties": {
        // JSON Schema definition
      }
    }
  }
]
```

**Notes:**
- Returns **all active modules** (`is_active = true`) in single request
- Frontend caches for offline pipeline building
- No pagination needed (catalog size: ~20-50 modules)
- Frontend groups/sorts by `module_kind` and `category`
- Excludes: `handler_name` (backend execution only), `created_at`, `updated_at` (audit only)
- Filtering/search applied server-side to reduce payload if needed

**Errors:**
- `500`: `{"detail": "Database error"}`

---

## Router 6: `/pipelines` - Pipeline Management (Development/Testing)

> See `API_DESIGN.md` Domain 5 for business rules and requirements.

**Router Status**: ✅ Reviewed

**Note:** This router is primarily for standalone pipeline testing during development. Pipelines are typically accessed via templates in production. Pipelines are immutable once created (append-only architecture).

### Endpoints Overview

| Method | Path | Description | Reviewed |
|--------|------|-------------|----------|
| GET | `/pipelines` | List all pipelines (with pagination) | ✅ |
| GET | `/pipelines/{id}` | Get pipeline definition (pipeline_state, visual_state) | ✅ |
| POST | `/pipelines` | Create standalone pipeline | ✅ |

---

### `GET /pipelines`

**Description:** List all pipeline definitions with summary information. Useful for managing standalone test pipelines.

**Query Parameters:**
- `sort_by` (optional): `id` | `created_at` (default: `created_at`)
- `sort_order` (optional): `asc` | `desc` (default: `desc`)
- `limit` (optional): number (default: 50, max: 200)
- `offset` (optional): number (default: 0)

**Response:** `200 OK`
```typescript
{
  "items": [
    {
      "id": number,
      "compiled_plan_id": number | null,  // null if not yet compiled
      "created_at": string,                // ISO 8601 (included for dev convenience)
      "updated_at": string                 // ISO 8601 (included for dev convenience)
    }
  ],
  "total": number,
  "limit": number,
  "offset": number
}
```

**Notes:**
- **Dev/Testing only** - This endpoint is for standalone pipeline testing
- Will be removed when standalone pipeline page is removed from production
- Includes `created_at`/`updated_at` for dev convenience (normally excluded)
- Minimal data - just IDs and timestamps for browsing

**Errors:**
- `400`: `{"detail": "Invalid query parameters"}`
- `500`: `{"detail": "Database error"}`

---

### `GET /pipelines/{id}`

**Description:** Get complete pipeline definition including pipeline_state (logical structure) and visual_state (UI layout).

**Path Parameters:**
- `id`: Pipeline definition ID (integer)

**Response:** `200 OK`
```typescript
{
  "id": number,
  "compiled_plan_id": number | null,  // Reference to compiled execution plan (if compiled)

  // Logical pipeline structure
  "pipeline_state": {
    "entry_points": [
      {
        "id": string,
        "label": string,
        "field_reference": string  // For templates, references extraction field label
      }
    ],
    "modules": [
      {
        "instance_id": string,
        "module_id": string,          // Reference to module_catalog
        "config": object,             // Module-specific configuration
        "inputs": [
          {
            "node_id": string,
            "name": string,
            "type": string[]
          }
        ],
        "outputs": [
          {
            "node_id": string,
            "name": string,
            "type": string[]
          }
        ]
      }
    ],
    "connections": [
      {
        "from_node_id": string,      // Entry point or module output node
        "to_node_id": string         // Module input node
      }
    ]
  },

  // Visual layout for graph builder
  "visual_state": {
    "positions": {
      // entry_point_id or module_instance_id → position
      [key: string]: {
        "x": number,
        "y": number
      }
    }
  }
}
```

**Notes:**
- Returns complete pipeline data for visualization/editing
- `compiled_plan_id` is null for new pipelines (compilation happens on first use)
- Frontend uses this to reconstruct visual graph builder
- Entry points may reference extraction fields (for template pipelines) or be standalone (for test pipelines)

**Errors:**
- `404`: `{"detail": "Pipeline not found"}`
- `500`: `{"detail": "Database error"}`

---

### `POST /pipelines`

**Description:** Create new standalone pipeline for testing. Creates pipeline definition without template association.

**Request Body:**
```typescript
{
  "pipeline_state": {
    "entry_points": [
      {
        "id": string,
        "label": string,
        "field_reference": string  // Can be arbitrary for standalone testing
      }
    ],
    "modules": [
      {
        "instance_id": string,
        "module_id": string,
        "config": object,
        "inputs": [
          {
            "node_id": string,
            "name": string,
            "type": string[]
          }
        ],
        "outputs": [
          {
            "node_id": string,
            "name": string,
            "type": string[]
          }
        ]
      }
    ],
    "connections": [
      {
        "from_node_id": string,
        "to_node_id": string
      }
    ]
  },
  "visual_state": {
    "positions": {
      [key: string]: {
        "x": number,
        "y": number
      }
    }
  }
}
```

**Response:** `201 Created`
```typescript
{
  "id": number,                    // Created pipeline ID
  "compiled_plan_id": number | null  // null initially, set on first compilation
}
```

**Notes:**
- **Dev/Testing only** - Creates pipeline without template
- **Will be removed** - This endpoint will be removed once pipeline system testing is complete
- Pipeline compilation may happen during creation (validation)
- Backend may deduplicate compiled plan if identical pipeline exists
- No template association - standalone pipeline

**Errors:**
- `400`: Business logic errors
  - `{"detail": "Pipeline validation failed: [specific error]"}`
  - `{"detail": "Invalid module references: [module IDs]"}`
  - `{"detail": "Invalid connections: [connection details]"}`
- `422`: Pydantic validation error (missing/invalid fields)
- `500`: `{"detail": "Database error or pipeline compilation error"}`

---

### `PUT /pipelines/{id}`

**Description:** Update existing pipeline definition. Replaces pipeline_state and visual_state.

**Path Parameters:**
- `id`: Pipeline definition ID (integer)

**Request Body:**
```typescript
{
  "pipeline_state": {
    "entry_points": [...],
    "modules": [...],
    "connections": [...]
  },
  "visual_state": {
    "positions": {...}
  }
}
```

**Response:** `200 OK`
```typescript
{
  "id": number,
  "compiled_plan_id": number | null  // May change if pipeline logic changed
}
```

**Notes:**
- **Will be removed** - This endpoint will be removed once pipeline system testing is complete
- Replaces entire pipeline definition
- Recompilation may occur if pipeline logic changed
- `compiled_plan_id` may update to point to different compiled plan
- Cannot update pipelines associated with finalized template versions (returns 409)

**Errors:**
- `404`: `{"detail": "Pipeline not found"}`
- `400`: Business logic errors (same as POST)
- `409`: `{"detail": "Cannot update pipeline associated with finalized template version"}`
- `422`: Pydantic validation error
- `500`: `{"detail": "Database error or pipeline compilation error"}`

---

### `DELETE /pipelines/{id}`

**Description:** Delete pipeline definition. **Only allowed for standalone pipelines** (not associated with any template version).

**Path Parameters:**
- `id`: Pipeline definition ID (integer)

**Response:** `204 No Content`

*(No response body)*

**Notes:**
- **Will be removed** - This endpoint will be removed once pipeline system testing is complete

**Deletion Rules:**
- Can delete: Standalone pipelines (not referenced by any template version)
- Cannot delete: Pipelines referenced by template versions (historical integrity)

**Errors:**
- `404`: `{"detail": "Pipeline not found"}`
- `409`: `{"detail": "Cannot delete pipeline associated with template versions"}`
- `500`: `{"detail": "Database error"}`

---

## Router 7: `/health` - System Health Monitoring

> See `API_DESIGN.md` Domain 6 for business rules and requirements.

**Router Status**: ✅ Reviewed

### Endpoints Overview

| Method | Path | Description | Reviewed |
|--------|------|-------------|----------|
| GET | `/health` | Get system health status (server + all services) | ✅ |

---

### `GET /health`

**Description:** Get overall system health and individual service statuses. Used by frontend for pre-load health checks and periodic monitoring. No authentication required.

**Response:** `200 OK`
```typescript
{
  "status": "healthy" | "degraded" | "unhealthy",

  "server": {
    "status": "up"  // If server responds, always "up"
  },

  "services": {
    "email_ingestion": {
      "status": "healthy" | "unhealthy",
      "message"?: string  // Optional error message if unhealthy
    },
    "eto_processing": {
      "status": "healthy" | "unhealthy",
      "message"?: string
    },
    "pdf_processing": {
      "status": "healthy" | "unhealthy",
      "message"?: string
    },
    "database": {
      "status": "healthy" | "unhealthy",
      "message"?: string
    }
    // Additional services from service container
  }
}
```

**Overall Status Logic:**
- `healthy`: All services are healthy
- `degraded`: One or more services unhealthy, but server is functional
- `unhealthy`: Server down or critical services down (rare - server won't respond)

**Notes:**
- **No authentication required** - Public health check endpoint
- Used by frontend before application load (blocks if server down)
- Used for periodic polling to detect service failures
- If server is completely down, browser shows native connection error (no 200 response)
- Individual service failures return 200 with `degraded` status
- Services checked: All services registered in service container
- Lightweight operation - simple boolean checks, no detailed diagnostics
- Detailed diagnostics available in server logs (not exposed via API)
- **TODO**: Response structure is preliminary. Service names and structure will be updated once service layer architecture is finalized

**Errors:**
- No error responses - if server can respond, returns 200 with status
- If server cannot respond, browser handles connection error

---

## Phase 3 Complete! 🎉

All 7 routers have been fully specified with **36 total endpoints**:

- ✅ Router 1: `/email-configs` - 10 endpoints
- ✅ Router 2: `/eto-runs` - 6 endpoints
- ✅ Router 3: `/pdf-files` - 4 endpoints
- ✅ Router 4: `/pdf-templates` - 8 endpoints
- ✅ Router 5: `/modules` - 1 endpoint
- ✅ Router 6: `/pipelines` - 5 endpoints (dev/testing)
- ✅ Router 7: `/health` - 1 endpoint

**Next Phase:** Phase 4 - Schema Definitions (detailed request/response types with Pydantic)

---
