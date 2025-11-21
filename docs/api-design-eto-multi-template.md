# ETO API Design - Multi-Template Architecture

> **Purpose**: Design document for the new ETO API endpoints that support the parent-child run structure with multiple template matches per PDF.

---

## Overview

### Context
The new database schema (`models.py`) introduces a parent-child structure:
- **Parent (`eto_runs`)**: Orchestration-level tracking for the entire PDF processing
- **Child (`eto_sub_runs`)**: Business logic level for each page-set/template match

This design replaces the old single-template-per-PDF approach with support for:
- Multiple templates matched to different page sets in a single PDF
- Unmatched pages tracked separately
- Independent processing status per page-set
- Granular error handling and reprocessing

### Design Goals
1. **Frontend-Driven**: API should serve the test feature mockups directly
2. **Backward Compatible**: Minimize breaking changes where possible
3. **Performance**: Efficient queries with proper joins and aggregations
4. **RESTful**: Follow established patterns from `pdf_templates` and existing `eto_runs` routers
5. **Type Safety**: Maintain the schema → mapper → types → service pattern

---

## Architecture Layers

### Current Pattern (Reference)
```
┌─────────────────────────────────────────────────┐
│ Router (api/routers/*.py)                       │
│ - FastAPI endpoints                             │
│ - Request validation                            │
│ - Response serialization                        │
└──────────────────┬──────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────┐
│ Schemas (api/schemas/*.py)                      │
│ - Pydantic request/response models              │
│ - OpenAPI documentation                         │
└──────────────────┬──────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────┐
│ Mappers (api/mappers/*.py)                      │
│ - Convert domain ↔ API schemas                  │
│ - DateTime formatting                           │
│ - Nested model construction                     │
└──────────────────┬──────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────┐
│ Types (shared/types/*.py)                       │
│ - Domain dataclasses                            │
│ - Business logic types                          │
└──────────────────┬──────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────┐
│ Services (features/*/service.py)                │
│ - Business logic                                │
│ - Repository orchestration                      │
│ - Transaction management                        │
└──────────────────┬──────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────┐
│ Repositories (shared/database/repositories/*.py)│
│ - Database access                               │
│ - SQL queries                                   │
└─────────────────────────────────────────────────┘
```

---

## Endpoint Categories

### 1. Parent-Level Operations (ETO Runs)
Operations on the entire PDF processing run.

**Endpoints to Design:**
- [ ] `GET /api/eto-runs` - List all parent runs with aggregated sub-run data
- [ ] `GET /api/eto-runs/{id}` - Get detailed parent run with all sub-runs
- [ ] `POST /api/eto-runs` - Create new parent run from uploaded PDF
- [ ] `POST /api/eto-runs/reprocess` - Reprocess entire parent run(s)
- [ ] `POST /api/eto-runs/skip` - Skip entire parent run(s)
- [ ] `DELETE /api/eto-runs` - Delete entire parent run(s)
- [ ] `GET /api/eto-runs/events` - SSE stream for real-time updates

### 2. Child-Level Operations (Sub-Runs)
Operations on individual page-set template matches.

**Endpoints to Design:**
- [ ] `GET /api/eto-runs/{run_id}/sub-runs/{sub_run_id}` - Get detailed sub-run
- [ ] `POST /api/eto-runs/{run_id}/sub-runs/{sub_run_id}/reprocess` - Reprocess single sub-run
- [ ] `POST /api/eto-runs/{run_id}/sub-runs/{sub_run_id}/skip` - Skip single sub-run
- [ ] `DELETE /api/eto-runs/{run_id}/sub-runs/{sub_run_id}` - Delete single sub-run
- [ ] `PATCH /api/eto-runs/{run_id}/sub-runs/{sub_run_id}/template` - Assign/change template

### 3. Batch Operations
Bulk operations across multiple runs or sub-runs.

**Endpoints to Design:**
- [ ] `POST /api/eto-runs/batch/reprocess` - Reprocess multiple runs
- [ ] `POST /api/eto-runs/batch/skip` - Skip multiple runs
- [ ] `DELETE /api/eto-runs/batch` - Delete multiple runs
- [ ] `POST /api/eto-runs/{run_id}/sub-runs/batch/reprocess` - Reprocess multiple sub-runs
- [ ] `POST /api/eto-runs/{run_id}/sub-runs/batch/skip` - Skip multiple sub-runs

---

## Data Models Structure

### Parent Run Models
```
EtoRunListItem (List View)
├── Core fields: id, status, processing_step, timestamps
├── PDF info: filename, size, page_count
├── Source: manual upload OR email details
└── Aggregations:
    ├── total_sub_runs
    ├── sub_runs_by_status: {success: N, failure: M, needs_template: X}
    ├── pages_matched
    ├── pages_unmatched
    └── templates_matched (count of unique templates)

EtoRunDetail (Detail View)
├── All fields from EtoRunListItem
├── Error details: error_type, error_message, error_details
└── sub_runs: [EtoSubRunDetail]
```

### Sub-Run Models
```
EtoSubRunDetail
├── Core fields: id, status, sequence
├── Pages: matched_pages (array of page numbers)
├── Template: matched_template (id, name, version)
├── Extraction:
│   ├── status
│   ├── extracted_data: [ExtractedFieldResult]
│   └── timestamps
└── Pipeline Execution:
    ├── status
    ├── executed_actions
    ├── steps: [ExecutionStepResult]
    └── timestamps
```

---

## Design Decisions

### Questions to Resolve
1. **Endpoint Granularity**: Should sub-run operations be nested under parent (`/eto-runs/{id}/sub-runs/{sub_id}`) or flat (`/eto-sub-runs/{id}`)?
2. **Pagination**: Should sub-runs within a parent be paginated for large PDFs?
3. **Filtering**: What filters are needed for list view? (status, date range, source type, template)
4. **Aggregations**: Should aggregations be pre-calculated or computed on-the-fly?
5. **SSE Events**: Should SSE events include sub-run updates or only parent-level changes?
6. **Bulk Operations**: Should bulk operations support cross-parent sub-run operations?

### Design Principles
- **Progressive Enhancement**: Start with parent-level operations, add sub-run operations as needed
- **Explicit Over Implicit**: Clear endpoint names and request/response structures
- **Fail Fast**: Validate requests early, return clear error messages
- **Idempotent Operations**: Reprocess/skip operations should be safely retriable

---

## Implementation Phases

### Phase 1: Core Parent Operations
- [ ] Update schemas for parent run list/detail with sub-run aggregations
- [ ] Update domain types for parent-child structure
- [ ] Update mappers for new structure
- [ ] Update service methods for parent operations
- [ ] Update router endpoints for parent operations

### Phase 2: Sub-Run Operations
- [ ] Add sub-run specific schemas
- [ ] Add sub-run domain types
- [ ] Add sub-run mappers
- [ ] Add sub-run service methods
- [ ] Add sub-run router endpoints

### Phase 3: Batch Operations & Optimization
- [ ] Implement batch operations
- [ ] Optimize queries with proper joins
- [ ] Add caching where appropriate
- [ ] Performance testing

---

## Endpoint: GET /api/eto-runs (List View)

### **Query Parameters**

```typescript
GET /api/eto-runs?{query_params}

Query Parameters:
{
  // Pagination
  limit: number = 50;              // Items per page (25, 50, 100, 200)
  offset: number = 0;              // Skip N items

  // Search
  search?: string;                 // Search query text (case-insensitive partial match)
  search_scope?: string;           // Where to search
                                   // Values: 'filename' | 'email' | 'all'
                                   // Default: 'filename'
                                   // - 'filename': Search pdf_files.original_filename
                                   // - 'email': Search emails.sender_email and emails.subject
                                   // - 'all': Search all above fields

  // Core Filters
  status?: string;                 // Parent run status filter
                                   // Values: 'success' | 'processing' | 'failure' |
                                   //         'needs_template' | 'not_started' | 'skipped'
                                   // Maps to: eto_runs.status (ETO_MASTER_STATUS enum)

  is_read?: boolean;               // Read/unread filter
                                   // true = show only read runs
                                   // false = show only unread runs
                                   // undefined/null = show all
                                   // Maps to: eto_runs.is_read

  date_from?: string;              // Filter runs created on or after this date (ISO 8601)
  date_to?: string;                // Filter runs created on or before this date (ISO 8601)
                                   // Maps to: eto_runs.created_at

  // Sorting
  sort_by?: string;                // Field to sort by
                                   // Values: 'updated_at' | 'created_at' | 'filename' | 'status'
                                   // Default: 'updated_at'
  sort_order?: string;             // Sort direction
                                   // Values: 'asc' | 'desc'
                                   // Default: 'desc'
}
```

### **Response Structure**

```typescript
Response: {
  items: EtoRunListItem[];         // Array of run items

  // Pagination metadata
  pagination: {
    total: number;                 // Total matching runs (for "Showing X of Y")
    limit: number;                 // Items per page (echoed from request)
    offset: number;                // Current offset (echoed from request)
    page: number;                  // Current page number (computed: offset / limit + 1)
    total_pages: number;           // Total pages (computed: ceil(total / limit))
    has_next: boolean;             // Whether there's a next page
    has_previous: boolean;         // Whether there's a previous page
  };
}
```

### **EtoRunListItem Schema**

```typescript
interface EtoRunListItem {
  // === Core Parent Run Fields ===
  id: number;                          // From: eto_runs.id
  status: string;                      // From: eto_runs.status
                                       // Values: 'success' | 'processing' | 'failure' |
                                       //         'needs_template' | 'not_started' | 'skipped'
  processing_step: string | null;      // From: eto_runs.processing_step
                                       // Values: 'template_matching' | 'sub_runs' | null
  is_read: boolean;                    // From: eto_runs.is_read

  // === Timestamps (ISO 8601 strings) ===
  created_at: string;                  // From: eto_runs.created_at
  updated_at: string;                  // From: eto_runs.updated_at (displayed as "Last Updated")
  started_at: string | null;           // From: eto_runs.started_at
  completed_at: string | null;         // From: eto_runs.completed_at

  // === PDF File Info (nested object) ===
  pdf: {
    id: number;                        // From: pdf_files.id
    filename: string;                  // From: pdf_files.original_filename
    page_count: number | null;         // From: pdf_files.page_count
    file_size: number | null;          // From: pdf_files.file_size (bytes)
  };

  // === Source (discriminated union) ===
  source: {
    type: "manual";
  } | {
    type: "email";
    sender_email: string;              // From: emails.sender_email
    received_date: string;             // From: emails.received_date (ISO 8601)
    subject: string | null;            // From: emails.subject
    folder_name: string;               // From: emails.folder_name
  };

  // === Sub-Run Aggregations (computed) ===
  aggregations: {
    total_sub_runs: number;            // COUNT(eto_sub_runs.id)

    // Status breakdown for indicator color logic
    sub_runs_by_status: {
      success: number;                 // COUNT WHERE eto_sub_runs.status='success'
      failure: number;                 // COUNT WHERE eto_sub_runs.status='failure'
      needs_template: number;          // COUNT WHERE eto_sub_runs.status='needs_template'
      processing: number;              // COUNT WHERE eto_sub_runs.status='processing'
      not_started: number;             // COUNT WHERE eto_sub_runs.status='not_started'
      skipped: number;                 // COUNT WHERE eto_sub_runs.status='skipped'
    };

    // Template matching metrics
    templates_matched: number;         // COUNT(DISTINCT template_version_id) WHERE NOT NULL

    // Page distribution
    pages_matched: number;             // SUM(page count) WHERE template_version_id IS NOT NULL
    pages_unmatched: number;           // SUM(page count) WHERE is_unmatched_group=true
  };

}
```

### **Frontend Visual Styling for Read/Unread**

Read runs have the following visual differences:
- **Entire row**: 60% opacity
- **Filename**: Gray color (`text-gray-400`) instead of white (`text-gray-200`)
- **Filename**: No font-weight (medium removed for read items)
- **Indicator dots**: Hidden for read items

Unread runs:
- **Full opacity**
- **Filename**: Brighter color and medium font-weight
- **Indicator dots**: Multiple animated pulsing dots showing sub-run statuses (see below)

### **Status Indicator Logic**

The indicators on the left of each row represent **sub-run statuses**, not parent status:

**When indicators are shown:**
- When sub-runs exist (at least one sub-run with success/failure/needs_template)
- Shown for both read AND unread items (with different styling)

**Which indicators appear (can show multiple simultaneously):**
- 🟢 **Green dot**: If `sub_runs_by_status.success > 0` (at least one sub-run succeeded)
- 🟡 **Yellow dot**: If `sub_runs_by_status.needs_template > 0` (at least one sub-run needs a template)
- 🔴 **Red dot**: If `sub_runs_by_status.failure > 0` (at least one sub-run failed)

**Visual differences based on read status:**
- **Unread items** (`is_read = false`):
  - Full opacity colored dots
  - Animated pulsing effect on all dots
  - Demands user attention

- **Read items** (`is_read = true`):
  - Dimmed dots (40% opacity)
  - NO pulsing animation
  - Subtle presence, doesn't demand attention

**When NO indicators are shown:**
- Parent-level failures (`masterStatus = 'failure'`) - no sub-runs were created
- Not started (`masterStatus = 'not_started'`) - no sub-runs yet
- Processing (`masterStatus = 'processing'`) - sub-runs not yet created
- Skipped (`masterStatus = 'skipped'`) - intentionally skipped

**Examples:**
- All successful sub-runs (unread): 🟢 with pulsing (green only)
- All successful sub-runs (read): 🟢 dimmed, no pulse (green only)
- Mix of success + needs template (unread): 🟢🟡 with pulsing
- Mix of success + needs template (read): 🟢🟡 dimmed, no pulse
- All three statuses (unread): 🟢🟡🔴 with pulsing - like insurance_claims.pdf
- All three statuses (read): 🟢🟡🔴 dimmed, no pulse
- Parent failure: (no dots, status column shows "failure")

### **Database Query Notes**

```sql
-- Base query with all required joins and aggregations
SELECT
  -- Core eto_runs fields
  er.id, er.status, er.processing_step, er.is_read,
  er.created_at, er.updated_at, er.started_at, er.completed_at,

  -- PDF file info
  pf.id as pdf_id, pf.original_filename, pf.page_count, pf.file_size,

  -- Email source (NULL if manual upload)
  e.id as email_id, e.sender_email, e.received_date, e.subject, e.folder_name,

  -- Sub-run aggregations (computed in subquery or window functions)
  COUNT(esr.id) as total_sub_runs,
  COUNT(DISTINCT esr.template_version_id) FILTER (WHERE esr.template_version_id IS NOT NULL) as templates_matched,
  COUNT(*) FILTER (WHERE esr.status = 'success') as success_count,
  COUNT(*) FILTER (WHERE esr.status = 'failure') as failure_count,
  COUNT(*) FILTER (WHERE esr.status = 'needs_template') as needs_template_count,
  -- ... more aggregations

FROM eto_runs er
INNER JOIN pdf_files pf ON er.pdf_file_id = pf.id
LEFT JOIN emails e ON pf.email_id = e.id
LEFT JOIN eto_sub_runs esr ON er.id = esr.eto_run_id
WHERE
  -- Apply filters from query params
  (? IS NULL OR er.status = ?)
  AND (? IS NULL OR er.is_read = ?)
  AND (? IS NULL OR er.created_at >= ?)
  AND (? IS NULL OR er.created_at <= ?)
  -- Search filters
  AND (
    ? IS NULL OR (
      CASE ?
        WHEN 'filename' THEN pf.original_filename ILIKE ?
        WHEN 'email' THEN (e.sender_email ILIKE ? OR e.subject ILIKE ?)
        WHEN 'all' THEN (pf.original_filename ILIKE ? OR e.sender_email ILIKE ? OR e.subject ILIKE ?)
      END
    )
  )
GROUP BY er.id, pf.id, e.id
ORDER BY
  CASE ?
    WHEN 'updated_at' THEN er.updated_at
    WHEN 'created_at' THEN er.created_at
    WHEN 'filename' THEN pf.original_filename
    WHEN 'status' THEN er.status
  END
LIMIT ? OFFSET ?
```

### **Performance Considerations**

1. **Indexes needed**:
   - `eto_runs.status` (existing)
   - `eto_runs.is_read` (add if not exists)
   - `eto_runs.created_at` (add for date filtering)
   - `pdf_files.original_filename` (consider GIN index for ILIKE)
   - `emails.sender_email` (consider GIN index for ILIKE)

2. **Aggregation optimization**:
   - Sub-run aggregations happen on every query
   - For very large datasets, consider:
     - Materialized view with aggregations
     - Denormalized counts on `eto_runs` table
     - Caching layer

3. **Pagination**:
   - Total count query runs separately from items query
   - For very large datasets, consider approximate counts or cursor pagination

---

## Next Steps

1. ✅ **Define GET /api/eto-runs Query Parameters** - Complete
2. ✅ **Define GET /api/eto-runs Response Schema** - Complete
3. **Define GET /api/eto-runs/{id} Detail View** - Next
4. **Design Request/Response Schemas**: Document exact JSON structures
5. **Map to Database Schema**: Ensure queries can efficiently fetch required data
6. **Identify Breaking Changes**: Document any changes to existing endpoints
7. **Implementation Plan**: Create ordered task list for building endpoints

---

## Appendix

### Related Files
- Database Models: `server/src/shared/database/models.py`
- Old ETO Router: `server/src/api/routers/eto_runs.py`
- Old ETO Schemas: `server/src/api/schemas/eto_runs.py`
- Old ETO Types: `server/src/shared/types/eto_runs.py`
- Frontend Test Pages:
  - List: `client/src/renderer/pages/dashboard/test/index.tsx`
  - Detail: `client/src/renderer/pages/dashboard/test/$runId.tsx`

### References
- [Database Redesign Doc](./database-redesign-multi-template-matching.md)
- [Full Database Design](./new-full-database-design.md)
