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

### Endpoints Overview

| Method | Path | Description |
|--------|------|-------------|
| GET | `/email-configs` | List all configurations (summary) |
| GET | `/email-configs/{id}` | Get configuration details |
| POST | `/email-configs` | Create new configuration |
| PUT | `/email-configs/{id}` | Update configuration |
| DELETE | `/email-configs/{id}` | Delete configuration |
| POST | `/email-configs/{id}/activate` | Activate configuration |
| POST | `/email-configs/{id}/deactivate` | Deactivate configuration |
| GET | `/email-configs/discovery/accounts` | List available email accounts |
| GET | `/email-configs/discovery/folders` | List folders for account |
| POST | `/email-configs/validate` | Validate configuration |

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

### Endpoints Overview

| Method | Path | Description |
|--------|------|-------------|
| GET | `/eto-runs` | List runs with optional status filtering, sorting, and pagination |
| GET | `/eto-runs/{id}` | Get full run details including all stage results and execution logs |
| POST | `/eto-runs/upload` | Create new run via manual PDF upload |
| POST | `/eto-runs/reprocess` | Reprocess runs (bulk): reset to not_started, clear stage records |
| POST | `/eto-runs/skip` | Skip runs (bulk): set status to skipped |
| DELETE | `/eto-runs` | Delete runs (bulk): permanently remove (only if skipped) |

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

        // Step inputs: node name → { value, type }
        "inputs": {
          [node_name: string]: {
            "value": any,
            "type": string               // Type of the value (e.g., "string", "number", "object")
          }
        } | null,

        // Step outputs: node name → { value, type }
        "outputs": {
          [node_name: string]: {
            "value": any,
            "type": string               // Type of the value
          }
        } | null,

        "error": {
          [key: string]: any             // Error details if step failed
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
- `steps` are ordered by `step_number` (execution order)
- Steps do not have individual status/timestamps - error presence indicates failure
- **Response Size Warning:** This endpoint can return large payloads (>1MB) for runs with:
  - Large extracted_data (100+ fields from complex PDFs)
  - Long pipelines (20+ steps with detailed inputs/outputs)
  - Consider splitting into separate endpoints if performance issues arise

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

### Endpoints Overview

| Method | Path | Description |
|--------|------|-------------|
| GET | `/pdf-files/{id}` | Get PDF file metadata |
| GET | `/pdf-files/{id}/download` | Download/stream PDF file bytes |
| GET | `/pdf-files/{id}/objects` | Get extracted PDF objects (for template building) |

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
- Parsed from the `objects_json` field in the `pdf_files` table
- Coordinates are rounded to 3 decimal places for consistency
- Each array can be empty if no objects of that type were found
- Frontend should iterate through each object type separately

**Errors:**
- `404`: `{"detail": "PDF file not found"}`
- `500`: `{"detail": "Database error or invalid objects data"}`

---

## Router 4: `/pdf-templates` - PDF Template Management

> See `API_DESIGN.md` Domain 3 for business rules and requirements.

**To be continued...**

---
