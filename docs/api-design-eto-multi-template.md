# ETO API Design - Multi-Template Architecture

> **Router**: `server/src/api/routers/eto_runs.py`

---

## Overview

This document defines the API endpoints for the ETO (Email-to-Order) system with multi-template support. The new architecture supports a parent-child structure where a single PDF can match multiple templates across different page sets.

**Key Concepts:**
- **Parent Run (`eto_runs`)**: Orchestration-level tracking for entire PDF processing
- **Sub-Run (`eto_sub_runs`)**: Business logic level for each page-set/template match
- **Multi-template matching**: Single PDF can have multiple sub-runs, each matching different templates

---

## Endpoints

### GET /api/eto-runs - List View

**Description:** Retrieve a paginated list of ETO runs with aggregated sub-run data. Powers the main list view UI with search, filtering, and sorting capabilities.

**Query Parameters:**
```typescript
{
  // Pagination
  page?: number;              // Default: 1
  per_page?: number;          // Default: 20, Options: [20, 50, 100, 200]

  // Search
  search?: string;            // Search text (case-insensitive partial match)
  search_scope?: "filename" | "email" | "all";
                              // Default: "all"

  // Filters
  status?: "success" | "failure" | "processing" | "skipped";
  is_read?: boolean;
  date_from?: string;         // ISO 8601 date
  date_to?: string;           // ISO 8601 date

  // Sorting
  sort_by?: "updated_desc" | "updated_asc" | "created_desc" | "created_asc" |
            "filename_asc" | "filename_desc" | "status";
                              // Default: "updated_desc"
}
```

**Response:**
```typescript
{
  items: EtoRunListItem[];
  pagination: {
    page: number;
    per_page: number;
    total_items: number;
    total_pages: number;
  };
}

interface EtoRunListItem {
  // Identity
  id: number;

  // Status & State
  status: "success" | "failure" | "processing" | "skipped";
  is_read: boolean;

  // PDF Information
  pdf: {
    id: number;
    filename: string;
    page_count: number;
  };

  // Source (Discriminated Union)
  source: {
    type: "manual";
    uploaded_at: string;      // ISO 8601
  } | {
    type: "email";
    sender_email: string;
    received_at: string;      // ISO 8601
    subject: string | null;
  };

  // Sub-Run Aggregations
  sub_runs: {
    success: number;
    failure: number;
    needs_template: number;
    skipped: number;
  };

  // Page Breakdown
  pages: {
    matched: number[];        // Array of page numbers
    unmatched: number[];
    skipped: number[];
  };

  // Timestamps
  updated_at: string;         // ISO 8601
}
```

---

### GET /api/eto-runs/{id} - Detail View

**Description:** Retrieve detailed information for a single ETO run, including all sub-runs, extracted data, and processing history.

**Path Parameters:**
```typescript
{
  id: number;  // ETO run ID
}
```

**Response:**
```typescript
{
  // Core Run Information
  id: number;
  pdfFilename: string;
  masterStatus: "success" | "failure" | "processing" | "skipped";
  totalPages: number;
  source: string;              // Display string: "Manual Upload" or sender email
  sourceDate: string;          // ISO 8601
  createdAt: string;           // ISO 8601
  lastUpdated: string;         // ISO 8601
  processingStep: string;      // Current processing stage

  // PDF File Details
  pdfFile: {
    id: number;
    storagePath: string;
    fileSize: string;          // Human-readable format (e.g., "3.8 MB")
  };

  // Email Details (optional)
  emailDetails: null | {
    // TBD - populated if source is email
  };

  // Matched Sub-Runs (with template matches)
  matchedSubRuns: Array<{
    id: number;
    pages: number[];           // Array of page numbers
    status: "success" | "failure";
    template: {
      id: number;
      name: string;
    };
    extractedData: Record<string, any> | null;  // Dynamic fields, null if failed
    errorMessage: string | null;                // Only for failures
  }>;

  // Needs Template Sub-Runs (no template match)
  needsTemplateSubRuns: Array<{
    id: number;
    pages: number[];           // Array of page numbers
    status: "needs_template";
  }>;

  // Skipped Sub-Runs (user-skipped pages)
  skippedSubRuns: Array<{
    id: number;
    pages: number[];           // Array of page numbers
    status: "skipped";
  }>;
}
```

---

### PATCH /api/eto-runs/{id}/mark-read

**Description:** Mark an ETO run as read or unread. Used for visual tracking in the list view.

**Path Parameters:**
```typescript
{
  id: number;  // ETO run ID
}
```

**Request Body:**
```typescript
{
  is_read: boolean;  // true = mark as read, false = mark as unread
}
```

**Response:**
```typescript
{
  is_read: boolean;  // Confirmed read state
}
```

---

### POST /api/eto-runs/{id}/skip

**Description:** Skip all failed/needs_template sub-runs by consolidating them into one skipped sub-run. Deletes the problematic sub-runs and creates/updates a consolidated skipped sub-run containing all affected pages.

**Path Parameters:**
```typescript
{
  id: number;  // ETO run ID
}
```

**Request Body:**
None

**Response:**
```
204 No Content
```

---

### POST /api/eto-runs/{id}/reprocess

**Description:** Reprocess all failed/needs_template sub-runs. Deletes these sub-runs and re-runs template matching from scratch. Ignores skipped sub-runs.

**Path Parameters:**
```typescript
{
  id: number;  // ETO run ID
}
```

**Request Body:**
None

**Response:**
```
204 No Content
```

---

### DELETE /api/eto-runs/{id}

**Description:** Delete an ETO run and all associated sub-runs. Used when the user wants to completely remove a run from the system. Cascade deletes all child records including matched sub-runs, needs_template sub-runs, skipped sub-runs, and any other related data.

**Path Parameters:**
```typescript
{
  id: number;  // ETO run ID
}
```

**Request Body:**
None

**Response:**
```
204 No Content
```

---

### GET /api/eto-runs/{id}/sub-runs/{sub_id}

**Description:** Retrieve detailed information for a single sub-run, including extracted data, template information, and processing status. Returns the same detailed view structure as the old single-template system, but scoped to the specific pages that matched this template.

**Path Parameters:**
```typescript
{
  id: number;      // ETO run ID
  sub_id: number;  // Sub-run ID
}
```

**Response:**
```typescript
{
  // Sub-run core data
  id: number;
  pages: number[];  // Array of page numbers this sub-run covers
  status: "success" | "failure";

  // Template that was matched
  template: {
    id: number;
    name: string;
    version_id: number;
    version_number: number;
  };

  // PDF info (for the viewer)
  pdf: {
    id: number;
    original_filename: string;
    file_size: number | null;
    page_count: number | null;
  };

  // Extraction stage (same structure as old system)
  stage_data_extraction: {
    status: "processing" | "success" | "failure";
    extraction_results: Array<ExtractedFieldResult> | null;  // Filtered to sub-run pages only
    started_at: string | null;  // ISO 8601
    completed_at: string | null;  // ISO 8601
  } | null;

  // Pipeline execution stage (same structure as old system)
  stage_pipeline_execution: {
    status: "processing" | "success" | "failure";
    executed_actions: Record<string, any> | null;
    started_at: string | null;  // ISO 8601
    completed_at: string | null;  // ISO 8601
    pipeline_definition_id: number | null;
    steps: Array<{
      id: number;
      step_number: number;
      module_instance_id: string;
      inputs: Record<string, Record<string, any>> | null;
      outputs: Record<string, Record<string, any>> | null;
      error: Record<string, any> | null;
    }> | null;
  } | null;

  // Error details (if failed)
  error_message: string | null;
  error_details: string | null;
}
```

**Note:** The `ExtractedFieldResult` type includes bbox coordinates, page numbers, field values, and confidence scores for displaying overlays on the PDF viewer.

---

### POST /api/eto-runs/{id}/sub-runs/{sub_id}/skip

**Description:** Skip a specific sub-run. Marks the sub-run as skipped without deleting it.

**Path Parameters:**
```typescript
{
  id: number;      // ETO run ID
  sub_id: number;  // Sub-run ID
}
```

**Request Body:**
None

**Response:**
```
204 No Content
```

---

### POST /api/eto-runs/{id}/sub-runs/{sub_id}/reprocess

**Description:** Reprocess a specific sub-run (including skipped ones). Deletes the sub-run and re-runs template matching for those specific pages.

**Path Parameters:**
```typescript
{
  id: number;      // ETO run ID
  sub_id: number;  // Sub-run ID
}
```

**Request Body:**
None

**Response:**
```
204 No Content
```

---

## Related Files

- Database Models: `server/src/shared/database/models.py`
- Frontend List View: `client/src/renderer/pages/dashboard/test/index.tsx`
- Frontend Detail View: `client/src/renderer/pages/dashboard/test/$runId.tsx`
- Database Design: `docs/new-full-database-design.md`
