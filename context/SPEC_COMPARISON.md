# API Specification Comparison: Frontend vs Backend

**Date**: 2025-10-20
**Purpose**: Compare frontend API expectations with backend API specification to ensure alignment before building the new backend

**Documents Compared**:
- Frontend: `context/client_redesign/API_SUMMARY.md` (38 endpoints)
- Backend: `context/server_redesign/API_ENDPOINTS.md` (36 endpoints)

---

## Executive Summary

**Overall Alignment**: 🟡 **Good with Minor Mismatches**

The frontend and backend specs are mostly aligned, with only a few discrepancies that need resolution before backend implementation begins.

### Critical Mismatches Found:
1. **Modules API** - Frontend expects `POST /modules/execute`, backend spec omits it
2. **ETO Runs API** - Frontend has single-run reprocess endpoint, backend only has bulk
3. **Templates Simulate** - Frontend expects two variants (stored/upload), backend only stored
4. **Templates Create** - Frontend expects PDF upload support, backend spec doesn't mention it

### Statistics:
- ✅ **Fully Aligned**: 4 domains (Email Configs, PDF Files, Pipelines, Health)
- 🟡 **Minor Issues**: 2 domains (ETO Runs, Templates)
- 🔴 **Missing Functionality**: 1 domain (Modules - missing execute endpoint)

---

## 1. Email Configurations API ✅

**Endpoint Count**: 10 (both specs match)

| Endpoint | Backend Spec | Frontend Spec | Status |
|----------|--------------|---------------|--------|
| GET /email-configs | ✓ | ✓ | ✅ Match |
| GET /email-configs/{id} | ✓ | ✓ | ✅ Match |
| POST /email-configs | ✓ | ✓ | ✅ Match |
| PUT /email-configs/{id} | ✓ | ✓ | ✅ Match |
| DELETE /email-configs/{id} | ✓ | ✓ | ✅ Match |
| POST /email-configs/{id}/activate | ✓ | ✓ | ✅ Match |
| POST /email-configs/{id}/deactivate | ✓ | ✓ | ✅ Match |
| GET /email-configs/discovery/accounts | ✓ | ✓ | ✅ Match |
| GET /email-configs/discovery/folders | ✓ | ✓ | ✅ Match |
| POST /email-configs/validate | ✓ | ✓ | ✅ Match |

### Response Structure Comparison

**GET /email-configs** (List):
- Backend: Array of `{id, name, is_active, last_check_time}`
- Frontend: Same structure
- ✅ **Perfect match**

**GET /email-configs/{id}** (Detail):
- Backend: Full config with all fields
- Frontend: Identical structure with `EmailConfigDetailDTO`
- ✅ **Perfect match**

**Query Parameters**:
- Backend: `order_by`, `desc`
- Frontend: Same naming
- ✅ **Perfect match**

### Verdict: ✅ **Fully Aligned**

No changes needed. Backend spec and frontend expectations are identical.

---

## 2. ETO Runs API 🟡

**Endpoint Count**: Backend 6, Frontend 7

| Endpoint | Backend Spec | Frontend Spec | Status |
|----------|--------------|---------------|--------|
| GET /eto-runs | ✓ | ✓ | ✅ Match |
| GET /eto-runs/{id} | ✓ | ✓ | ✅ Match |
| POST /eto-runs/upload | ✓ | ✓ | ✅ Match |
| POST /eto-runs/reprocess (bulk) | ✓ | ✓ | ✅ Match |
| POST /eto-runs/skip (bulk) | ✓ | ✓ | ✅ Match |
| DELETE /eto-runs (bulk) | ✓ | ✓ | ✅ Match |
| POST /eto-runs/{id}/reprocess | ❌ | ✓ | 🔴 **Missing from backend** |

### Issue 1: Single-Run Reprocess Endpoint

**Frontend Expects**:
```
POST /eto-runs/{id}/reprocess
Description: "Reprocess single run (alternative to bulk endpoint)"
Request: No body
Response: 204 No Content
```

**Backend Spec**: Does not include this endpoint. Only provides bulk operation:
```
POST /eto-runs/reprocess
Body: { "run_ids": number[] }
```

**Impact**: Frontend has convenience method for single-run reprocessing. Backend would require frontend to wrap single ID in array for bulk endpoint.

**Resolution Options**:
- **Option A**: Add `POST /eto-runs/{id}/reprocess` to backend spec (consistency with skip/delete patterns)
- **Option B**: Remove from frontend, use bulk endpoint with single-item array
- **Recommendation**: Option A - single-run endpoints are more ergonomic

### Response Structure Comparison

**GET /eto-runs** (List):
- Backend: `{items: [...], total, limit, offset}`
- Frontend: Same pagination structure with `GetEtoRunsResponse`
- ✅ **Perfect match**

**GET /eto-runs/{id}** (Detail):
- Backend: Full run with template_matching, data_extraction, pipeline_execution
- Frontend: Identical structure with EtoRunDetail
- ✅ **Perfect match**

**Step Input/Output Structure**:
- Backend: Uses `node_id` as key (matches graph visualization needs)
- Frontend: Expects same structure
- ✅ **Perfect match**

### Verdict: 🟡 **Minor Mismatch**

**Action Required**: Decide whether to add single-run reprocess endpoint to backend spec.

---

## 3. PDF Files API ✅

**Endpoint Count**: 4 (both specs match)

| Endpoint | Backend Spec | Frontend Spec | Status |
|----------|--------------|---------------|--------|
| GET /pdf-files/{id} | ✓ | ✓ | ✅ Match |
| GET /pdf-files/{id}/download | ✓ | ✓ | ✅ Match |
| GET /pdf-files/{id}/objects | ✓ | ✓ | ✓ | ✅ Match |
| POST /pdf-files/process | ✓ | ✓ | ✅ Match |

### Response Structure Comparison

**GET /pdf-files/{id}** (Metadata):
- Backend: `{id, email_id, filename, original_filename, relative_path, file_size, file_hash, page_count}`
- Frontend: Identical structure with `PdfFileMetadataDTO`
- ✅ **Perfect match**

**GET /pdf-files/{id}/objects** (Extracted objects):
- Backend: Grouped by type (text_words, text_lines, graphic_rects, etc.)
- Frontend: Same grouping structure
- ✅ **Perfect match**

**POST /pdf-files/process** (Process without storage):
- Backend: Returns `{page_count, objects: {...}}`
- Frontend: Expects same structure
- ✅ **Perfect match**

### Verdict: ✅ **Fully Aligned**

No changes needed. Perfect alignment between specs.

---

## 4. PDF Templates API 🟡

**Endpoint Count**: 10 (both specs match count, but differ in details)

| Endpoint | Backend Spec | Frontend Spec | Status |
|----------|--------------|---------------|--------|
| GET /pdf-templates | ✓ | ✓ | ✅ Match |
| GET /pdf-templates/{id} | ✓ | ✓ | ✅ Match |
| POST /pdf-templates | ✓ | ✓ | 🟡 **Partial** |
| PUT /pdf-templates/{id} | ✓ | ✓ | ✅ Match |
| DELETE /pdf-templates/{id} | ✓ | ✓ | ✅ Match |
| POST /pdf-templates/{id}/activate | ✓ | ✓ | ✅ Match |
| POST /pdf-templates/{id}/deactivate | ✓ | ✓ | ✅ Match |
| GET /pdf-templates/{id}/versions | ✓ | ✓ | ✅ Match |
| GET /pdf-templates/{id}/versions/{version_id} | ✓ | ✓ | ✅ Match |
| POST /pdf-templates/simulate | ✓ | ✓ | 🔴 **Mismatch** |

### Issue 1: Create Template - PDF Upload Support

**Frontend Expects** (multipart/form-data):
```typescript
{
  name: string;
  description?: string;
  source_pdf_id?: number | null;  // optional - for existing PDFs
  signature_objects: [...];
  extraction_fields: [...];
  pipeline_state: {...};
  visual_state: {...};
  // pdf_file: File (if source_pdf_id is null)
}
```

**Backend Spec**:
```typescript
{
  "name": string,
  "description"?: string,
  "source_pdf_id": number,  // required, no upload option
  "signature_objects": [...],
  "extraction_fields": [...],
  "pipeline_state": {...},
  "visual_state": {...}
}
```

**Impact**: Frontend expects to create templates by either:
1. Referencing existing PDF (source_pdf_id)
2. Uploading new PDF (pdf_file)

Backend spec only supports option 1.

**Resolution**: Backend spec should support both patterns. Request should be multipart when pdf_file provided.

### Issue 2: Simulate Endpoint - Upload Variant Missing

**Frontend Expects** (discriminated union):

**Variant 1 - Stored PDF**:
```typescript
{
  pdf_source: 'stored';
  pdf_file_id: number;
  signature_objects: [...];
  extraction_fields: [...];
  pipeline_state: {...};
}
```

**Variant 2 - Uploaded PDF**:
```typescript
{
  pdf_source: 'upload';
  // pdf_file: File (multipart)
  signature_objects: [...];
  extraction_fields: [...];
  pipeline_state: {...};
}
```

**Backend Spec** (only one variant):
```typescript
{
  "pdf_file_id": number,  // always required
  "signature_objects": [...],
  "extraction_fields": [...],
  "pipeline_state": {...}
}
```

**Impact**: Frontend template wizard needs to simulate with uploaded PDFs during template creation (before PDF is stored). Backend spec only supports stored PDFs.

**Resolution**: Backend spec should add discriminated union with `pdf_source` field:
- `'stored'` → requires `pdf_file_id`
- `'upload'` → requires `pdf_file` (multipart)

### Response Structure Comparison

**GET /pdf-templates** (List):
- Backend: `{items: [...], total, limit, offset}` with current_version nested
- Frontend: Same structure
- ✅ **Perfect match**

**GET /pdf-templates/{id}** (Detail):
- Backend: Template + current_version with signature_objects, extraction_fields, pipeline_definition_id
- Frontend: Identical structure
- ✅ **Perfect match**

### Verdict: 🟡 **Minor Mismatches**

**Action Required**:
1. Add PDF upload support to `POST /pdf-templates` (make source_pdf_id optional, add pdf_file field)
2. Add upload variant to `POST /pdf-templates/simulate` (discriminated union)

---

## 5. Modules API 🔴

**Endpoint Count**: Backend 1, Frontend 2

| Endpoint | Backend Spec | Frontend Spec | Status |
|----------|--------------|---------------|--------|
| GET /modules | ✓ | ✓ | ✅ Match |
| POST /modules/execute | ❌ | ✓ | 🔴 **Missing from backend** |

### Issue: Missing Execute Endpoint

**Frontend Expects**:
```
POST /modules/execute
Request: {
  module_id: string,
  inputs: Record<string, any>,
  config: Record<string, any>,
  use_cache?: boolean
}
Response: {
  success: boolean,
  module_id: string,
  outputs: Record<string, any>,
  error: string | null,
  performance_ms: number,
  cache_used: boolean
}
```

**Backend Spec**: Does not include this endpoint.

**Impact**: Frontend needs to test modules during pipeline building. This is a critical feature for the pipeline builder.

**Resolution**: Add `POST /modules/execute` to backend spec.

### Response Structure Comparison

**GET /modules** (Catalog):
- Backend: Array of modules with `{id, version, name, description, color, category, module_kind, meta, config_schema}`
- Frontend: Expects `ModuleCatalogResponse` with same structure
- ✅ **Perfect match**

### Verdict: 🔴 **Critical Missing Endpoint**

**Action Required**: Add `POST /modules/execute` endpoint to backend spec.

---

## 6. Pipelines API ✅

**Endpoint Count**: 5 (both specs match)

| Endpoint | Backend Spec | Frontend Spec | Status |
|----------|--------------|---------------|--------|
| GET /pipelines | ✓ | ✓ | ✅ Match |
| GET /pipelines/{id} | ✓ | ✓ | ✅ Match |
| POST /pipelines | ✓ | ✓ | ✅ Match |
| PUT /pipelines/{id} | ✓ | ✓ | ✅ Match |
| DELETE /pipelines/{id} | ✓ | ✓ | ✅ Match |

### Response Structure Comparison

**GET /pipelines** (List):
- Backend: `{items: [...], total, limit, offset}` with id, compiled_plan_id, created_at, updated_at
- Frontend: Same structure with `PipelinesListResponseDTO`
- ✅ **Perfect match**

**GET /pipelines/{id}** (Detail):
- Backend: `{id, compiled_plan_id, pipeline_state, visual_state}`
- Frontend: Identical structure
- ✅ **Perfect match**

**Pipeline State Structure**:
- Backend: entry_points, modules, connections
- Frontend: Same structure
- ✅ **Perfect match**

### Verdict: ✅ **Fully Aligned**

No changes needed. Perfect alignment between specs.

---

## 7. Health API ✅

**Endpoint Count**: Backend 1, Frontend 0 (not documented)

| Endpoint | Backend Spec | Frontend Spec | Status |
|----------|--------------|---------------|--------|
| GET /health | ✓ | (not documented) | ✅ OK |

**Note**: Health endpoint is system-level monitoring, not a feature API. Frontend doesn't document it in API_SUMMARY but will use it for system health checks.

### Verdict: ✅ **OK as-is**

Health endpoint is backend-provided infrastructure. No frontend spec needed.

---

## Summary of Required Changes

### 🔴 Critical (Must Fix)

**1. Modules API - Add Execute Endpoint**
```
Endpoint: POST /modules/execute
Location: Backend spec section 5
Action: Add complete endpoint specification with request/response schemas
Priority: CRITICAL - Pipeline builder depends on this
```

### 🟡 High Priority (Should Fix)

**2. Templates Simulate - Add Upload Variant**
```
Endpoint: POST /pdf-templates/simulate
Location: Backend spec section 4
Action: Change to discriminated union with pdf_source field
  - pdf_source: 'stored' → pdf_file_id required
  - pdf_source: 'upload' → pdf_file (multipart) required
Priority: HIGH - Template wizard testing depends on this
```

**3. Templates Create - Add PDF Upload Support**
```
Endpoint: POST /pdf-templates
Location: Backend spec section 4
Action: Make source_pdf_id optional, add pdf_file field (multipart)
  - If source_pdf_id provided → use existing PDF
  - If pdf_file provided → upload and store new PDF
Priority: HIGH - Template creation flexibility
```

**4. ETO Runs - Add Single Reprocess Endpoint**
```
Endpoint: POST /eto-runs/{id}/reprocess
Location: Backend spec section 2
Action: Add single-run reprocess endpoint (mirrors pattern of skip/delete)
Priority: MEDIUM - Convenience endpoint, bulk can substitute
```

---

## Alignment Summary by Domain

| Domain | Status | Endpoints Match | Schemas Match | Action Needed |
|--------|--------|----------------|---------------|---------------|
| Email Configurations | ✅ Perfect | 10/10 | ✅ | None |
| PDF Files | ✅ Perfect | 4/4 | ✅ | None |
| Pipelines | ✅ Perfect | 5/5 | ✅ | None |
| Health | ✅ OK | 1/0 | ✅ | None |
| ETO Runs | 🟡 Good | 6/7 | ✅ | Add single reprocess |
| Templates | 🟡 Good | 10/10 | 🟡 | Fix simulate & create |
| Modules | 🔴 Issue | 1/2 | ✅ | Add execute endpoint |

---

## Recommendation: Update Backend Spec Before Implementation

**Phase 1: Critical Fixes** (Must do before backend build)
1. Add `POST /modules/execute` to backend spec
2. Update `POST /pdf-templates/simulate` to support both stored and uploaded PDFs
3. Update `POST /pdf-templates` to support PDF uploads

**Phase 2: Consistency Improvements** (Should do)
4. Add `POST /eto-runs/{id}/reprocess` for consistency with other single-run operations

**After Changes**: Backend spec and frontend spec will be **100% aligned** and ready for implementation.

---

## Next Steps

1. ✅ **Review this comparison** with team
2. ⬜ **Update backend spec** (API_ENDPOINTS.md) with missing endpoints
3. ⬜ **Validate changes** with frontend team
4. ⬜ **Proceed to Phase 4** (Schema Definitions) with aligned spec
5. ⬜ **Begin backend implementation** with confidence

