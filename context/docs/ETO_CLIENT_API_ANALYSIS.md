# ETO Client API Analysis

## Overview
Analysis of client-side mock API to inform backend API schema design.

**Source Files:**
- `client/src/renderer/features/eto/types.ts` - Domain types
- `client/src/renderer/features/eto/api/types.ts` - API request/response types
- `client/src/renderer/features/eto/hooks/useMockEtoApi.ts` - Mock API implementation

---

## Key Findings

### 1. **Bulk Operations vs Single Operations**
**✅ RESOLVED:** Router updated to match client expectations

**Implementation (Bulk Only):**
- `POST /eto-runs/reprocess` with `{ run_ids: number[] }`
- `POST /eto-runs/skip` with `{ run_ids: number[] }`
- `DELETE /eto-runs` with `{ run_ids: number[] }`

**Design Decision:**
- Single operations send array with one ID: `{run_ids: [1]}`
- Reduces endpoint count, simplifies API surface
- All operations return 204 No Content

---

### 2. **Response Structure**

#### GET /eto-runs Response
**Client Expects:**
```typescript
{
  items: EtoRunListItem[];
  total: number;
  limit: number;
  offset: number;
}
```

**NOT just an array!** Must include pagination metadata.

---

### 3. **EtoRunListItem Structure**

```typescript
{
  id: number;
  status: EtoRunStatus;
  processing_step: EtoProcessingStep | null;
  started_at: string | null;          // ISO 8601
  completed_at: string | null;        // ISO 8601
  error_type: string | null;
  error_message: string | null;

  // Nested objects (not just IDs)
  pdf: {
    id: number;
    original_filename: string;
    file_size: number | null;
    page_count: number | null;        // Optional in list view
  };

  source: {
    type: 'manual' | 'email';
    // Email-specific (only if type='email')
    sender_email?: string;
    received_date?: string;           // ISO 8601
    subject?: string | null;
    folder_name?: string;
  };

  matched_template: {
    template_id: number;
    template_name: string;
    version_id: number;
    version_num: number;
  } | null;
}
```

**Key Points:**
- PDF info embedded (not just pdf_file_id)
- Source discriminated union (manual vs email)
- Matched template includes name and version info (not just IDs)

---

### 4. **EtoRunDetail Structure**

Extends `EtoRunListItem` with additional stage data:

```typescript
{
  ...EtoRunListItem,

  // PDF with required page_count
  pdf: {
    id: number;
    original_filename: string;
    file_size: number | null;
    page_count: number | null;        // Required in detail view
  };

  // Stage 1: Template Matching
  template_matching: {
    status: 'not_started' | 'success' | 'failure' | 'skipped';
    started_at: string | null;
    completed_at: string | null;
    error_message: string | null;
    matched_template: {
      template_id: number;
      template_name: string;
      version_id: number;
      version_num: number;
    } | null;
  };

  // Stage 2: Data Extraction
  data_extraction: {
    status: 'not_started' | 'success' | 'failure' | 'skipped';
    started_at: string | null;
    completed_at: string | null;
    error_message: string | null;
    extracted_data: Record<string, any> | null;
    extracted_fields_with_boxes?: ExtractedFieldWithBox[];  // For overlay
  };

  // Stage 3: Pipeline Execution
  pipeline_execution: {
    status: 'not_started' | 'success' | 'failure' | 'skipped';
    started_at: string | null;
    completed_at: string | null;
    error_message: string | null;
    pipeline_definition_id: number;
    executed_actions: Array<{
      action_module_name: string;
      inputs: Record<string, any>;
    }> | null;
    steps: EtoPipelineExecutionStep[];
  };
}
```

---

### 5. **ExtractedFieldWithBox** (For PDF Overlay)

```typescript
{
  field_id: string;
  label: string;
  value: string;
  page: number;
  bbox: [number, number, number, number];  // [x1, y1, x2, y2]
}
```

**Purpose:** Allows frontend to overlay extracted field bounding boxes on PDF viewer

---

### 6. **EtoPipelineExecutionStep**

```typescript
{
  id: number;
  step_number: number;
  module_instance_id: string;

  // Node IDs from pipeline definition (e.g., "i1", "i2", "o1")
  inputs: Record<string, {
    name: string;
    value: any;
    type: string;
  }> | null;

  outputs: Record<string, {
    name: string;
    value: any;
    type: string;
  }> | null;

  // Structured error
  error: {
    type: string;
    message: string;
    details?: any;
  } | null;
}
```

**Key Points:**
- Inputs/outputs keyed by node_id (not just arrays)
- Each input/output includes name, value, type
- Structured error object (not just string)

---

### 7. **POST /eto-runs Response**

```typescript
{
  id: number;
  pdf_file_id: number;
  status: 'not_started';
  processing_step: null;
  started_at: null;
  completed_at: null;
}
```

**Simpler than list item** - Just basic fields, no nested objects

---

## Backend Schema Requirements

### Must Include in Backend Schemas

1. **Pagination wrapper** for GET /eto-runs
   - `items`, `total`, `limit`, `offset`

2. **Embedded related data** (not just foreign keys)
   - PDF info (filename, size, page count)
   - Matched template (name, version number)
   - Source information (email vs manual)

3. **Stage-specific schemas**
   - Template matching stage
   - Data extraction stage
   - Pipeline execution stage

4. **ExtractedFieldWithBox** for overlay rendering
   - Include bounding box coordinates
   - Page number for multi-page PDFs

5. **Structured pipeline execution steps**
   - Node-id keyed inputs/outputs
   - Name, value, type for each
   - Structured error objects

---

## API Design Decisions

### 1. Bulk vs Single Operations ✅
**Decision:** Bulk only (Option B)
- `POST /reprocess` with `{run_ids: [...]}`
- `POST /skip` with `{run_ids: [...]}`
- `DELETE /eto-runs` with `{run_ids: [...]}`
- Single operations: send array with one ID

### 2. Source Field Population
**Question:** How to determine source type?
- If `email_id` present in database → type='email', fetch email details
- If `email_id` null → type='manual'

### 3. Matched Template Enrichment
**Question:** Should mapper fetch template name from database?
- Option A: Join in repository query (single query)
- Option B: Mapper fetches template details (multiple queries)
- Option C: Service layer enrichment

**Recommendation:** Option A (repository join)

---

## Mapper Complexity

**High complexity areas:**

1. **List item mapper** must:
   - Fetch PDF details (filename, size)
   - Determine source type (manual vs email)
   - Fetch email details if applicable
   - Fetch matched template name/version if applicable

2. **Detail mapper** must:
   - Everything from list mapper
   - Fetch all stage records
   - Transform extracted_data JSON to include bounding boxes
   - Fetch pipeline execution steps
   - Transform step inputs/outputs to node-keyed format

**Recommendation:**
- Repository layer handles joins
- Mapper layer handles domain → API conversion
- Service layer orchestrates multiple repository calls

---

## Backend Implementation Strategy

### Phase 1: Core Endpoints (MVP)
1. GET /eto-runs (with pagination wrapper)
2. GET /eto-runs/{id} (full detail with all stages)
3. POST /eto-runs (create from PDF upload)
4. POST /eto-runs/reprocess (bulk)
5. POST /eto-runs/skip (bulk)
6. DELETE /eto-runs (bulk)

### Phase 2: Enrichment & Optimization
1. Repository-level joins for related data
2. Caching for frequently accessed data
3. Pagination optimization

---

## Next Steps

1. **Create backend schemas** matching client types
2. **Create mappers** with proper data enrichment
3. **Update router** to use schemas
4. **Decide on bulk vs single operations**
5. **Test with real client**
