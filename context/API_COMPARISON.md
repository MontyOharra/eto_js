# Frontend vs Backend API Comparison

**Date**: 2025-10-20
**Frontend API Summary**: `context/client_redesign/API_SUMMARY.md` (38 endpoints)
**Backend Routers**: `server/src/api/routers/`

---

## Executive Summary

**Frontend expects**: 38 endpoints across 6 domains
**Backend implements**: ~40+ endpoints (many extra, some missing)

### Critical Issues:
1. **PDF Files API** - Entirely missing backend router (4 endpoints needed)
2. **Template simulate endpoint** - Missing (critical for template builder testing)
3. **Bulk operations** - Path/method mismatches (reprocess, skip, delete)
4. **Activation endpoints** - Different design (PATCH toggle vs separate POST activate/deactivate)

---

## 1. Templates API

**Frontend expects**: 10 endpoints
**Backend implements**: 6 endpoints

### ✅ Matches

| Endpoint | Method | Frontend | Backend |
|----------|--------|----------|---------|
| List templates | GET /pdf-templates | ✓ | ✓ |
| Get template | GET /pdf-templates/{id} | ✓ | ✓ |
| Create template | POST /pdf-templates | ✓ | ✓ |
| Get version detail | GET /pdf-templates/{id}/versions/{version_id} | ✓ | ✓ |

### ⚠️ Mismatches

| Frontend | Backend | Issue |
|----------|---------|-------|
| PUT /pdf-templates/{id} | PATCH /pdf-templates/{id} | **Different HTTP method** |

### ❌ Missing from Backend

| Endpoint | Frontend Spec | Priority |
|----------|---------------|----------|
| DELETE /pdf-templates/{id} | Delete template | HIGH |
| POST /pdf-templates/{id}/activate | Activate template | **CRITICAL** |
| POST /pdf-templates/{id}/deactivate | Deactivate template | **CRITICAL** |
| GET /pdf-templates/{id}/versions | List all versions | MEDIUM |
| POST /pdf-templates/simulate | **Simulate ETO without saving** | **CRITICAL** |

### ➕ Extra in Backend

| Endpoint | Purpose |
|----------|---------|
| POST /pdf-templates/{id}/versions | Create new version (frontend uses PUT /{id}) |
| GET /pdf-templates/status | Service health check |

### 🔥 Critical Issue

**POST /pdf-templates/simulate** is missing but essential for template builder Step 4 (testing). Frontend expects:
- Variant 1: `{ pdf_source: 'stored', pdf_file_id: number, ... }`
- Variant 2: `{ pdf_source: 'upload', pdf_file: File, ... }`
- Returns: template_matching + data_extraction + pipeline_execution results

---

## 2. ETO Runs API

**Frontend expects**: 7 endpoints
**Backend implements**: 15+ endpoints (many extra, some paths differ)

### ✅ Matches

| Endpoint | Method | Frontend | Backend |
|----------|--------|----------|---------|
| List runs | GET /eto-runs | ✓ | ✓ |
| Get run detail | GET /eto-runs/{id} | ✓ | ✓ |
| Skip single run | POST /eto-runs/{id}/skip | ✓ | PATCH /eto-runs/{id}/skip |
| Delete single run | DELETE /eto-runs/{id} | ✓ | DELETE /eto-runs/{id} ✓ |
| Reprocess single run | POST /eto-runs/{id}/reprocess | ✓ | PATCH /eto-runs/{id}/reprocess |

### ⚠️ Mismatches

| Frontend | Backend | Issue |
|----------|---------|-------|
| POST /eto-runs/{id}/skip | PATCH /eto-runs/{id}/skip | Different method |
| POST /eto-runs/{id}/reprocess | PATCH /eto-runs/{id}/reprocess | Different method |
| POST /eto-runs/upload | *Not found* | **Missing** |
| POST /eto-runs/reprocess (bulk) | PATCH /eto-runs/reprocess-bulk | Different path/method |
| POST /eto-runs/skip (bulk) | PATCH /eto-runs/bulk/skip | Different path/method |
| DELETE /eto-runs (bulk) | DELETE /eto-runs/{id} (single only) | **Bulk operation missing** |

### ❌ Missing from Backend

| Endpoint | Frontend Spec | Priority |
|----------|---------------|----------|
| POST /eto-runs/upload | Manual PDF upload creating new run | **CRITICAL** |
| POST /eto-runs/reprocess (bulk) | Body: `{ run_ids: number[] }` | HIGH |
| POST /eto-runs/skip (bulk) | Body: `{ run_ids: number[] }` | HIGH |
| DELETE /eto-runs (bulk) | Body: `{ run_ids: number[] }` | HIGH |

### ➕ Extra in Backend

| Endpoint | Purpose |
|----------|---------|
| GET /eto-runs/health | Service health check |
| POST /eto-runs/process-pdf/{pdf_file_id} | Alternative to upload endpoint |
| POST /eto-runs/worker/start | Worker control |
| POST /eto-runs/worker/stop | Worker control |
| POST /eto-runs/worker/pause | Worker control |
| POST /eto-runs/worker/resume | Worker control |
| GET /eto-runs/worker/status | Worker status |
| PATCH /eto-runs/reprocess-selected | Alternative bulk reprocess |
| POST /eto-runs/reprocess-failed | Reprocess all failed runs |
| GET /eto-runs/{id}/pdf-data | PDF metadata for run |
| GET /eto-runs/{id}/pdf-content | PDF binary content |

---

## 3. Email Configurations API

**Frontend expects**: 10 endpoints
**Backend implements**: 8 endpoints

### ✅ Matches

| Endpoint | Method | Frontend | Backend |
|----------|--------|----------|---------|
| Create config | POST /email-configs | ✓ | ✓ |
| List configs | GET /email-configs | ✓ | ✓ |
| Get config | GET /email-configs/{id} | ✓ | ✓ |
| Update config | PUT /email-configs/{id} | ✓ | ✓ |
| Discover accounts | GET /email-configs/discovery/accounts | ✓ | ✓ |
| Discover folders | GET /email-configs/discovery/folders | ✓ | ✓ |

### ⚠️ Mismatches

| Frontend | Backend | Issue |
|----------|---------|-------|
| POST /email-configs/{id}/activate | PATCH /email-configs/{id}/activate?activate=true | **Different design** |
| POST /email-configs/{id}/deactivate | PATCH /email-configs/{id}/activate?activate=false | **Different design** |

Frontend expects separate activate/deactivate endpoints. Backend uses single PATCH endpoint with boolean query param.

### ❌ Missing from Backend

| Endpoint | Frontend Spec | Priority |
|----------|---------------|----------|
| DELETE /email-configs/{id} | Delete email configuration | LOW (backend comment: "No deletion - configs are permanent") |
| POST /email-configs/validate | Validate email config before creation | MEDIUM |

### ➕ Extra in Backend

| Endpoint | Purpose |
|----------|---------|
| GET /email-configs/status | Service health check |

---

## 4. Modules API

**Frontend expects**: 2 endpoints
**Backend implements**: 3 endpoints

### ✅ Matches

| Endpoint | Method | Frontend | Backend |
|----------|--------|----------|---------|
| Get catalog | GET /modules | ✓ | ✓ |
| Execute module | POST /modules/execute | ✓ | ✓ |

### ➕ Extra in Backend

| Endpoint | Purpose |
|----------|---------|
| GET /modules/{module_id} | Get single module details |

**Note**: Frontend uses catalog filtering via query params. Backend provides dedicated endpoint for single module lookup.

---

## 5. Pipelines API

**Frontend expects**: 5 endpoints
**Backend implements**: 5 endpoints

### ✅ Matches

| Endpoint | Method | Frontend | Backend |
|----------|--------|----------|---------|
| List pipelines | GET /pipelines | ✓ | ✓ |
| Get pipeline | GET /pipelines/{id} | ✓ | ✓ |
| Validate pipeline | POST /pipelines/validate | ✓ | ✓ |

### ⚠️ Mismatches

| Frontend | Backend | Issue |
|----------|---------|-------|
| POST /pipelines | POST /pipelines/upload | **Different path** |

### ❌ Missing from Backend

| Endpoint | Frontend Spec | Priority |
|----------|---------------|----------|
| PUT /pipelines/{id} | Update existing pipeline | MEDIUM |
| DELETE /pipelines/{id} | Delete pipeline | MEDIUM |

### ➕ Extra in Backend

| Endpoint | Purpose |
|----------|---------|
| POST /pipelines/{id}/execute | Execute pipeline with entry values |

**Note**: Backend comment says upload endpoint "will eventually replace the main /pipelines endpoint."

---

## 6. PDF Files API

**Frontend expects**: 4 endpoints
**Backend implements**: **0 endpoints - NO ROUTER EXISTS**

### ❌ Missing from Backend - CRITICAL

| Endpoint | Frontend Spec | Priority |
|----------|---------------|----------|
| GET /pdf-files/{id} | Get PDF metadata | **CRITICAL** |
| GET /pdf-files/{id}/download | Download PDF as binary | **CRITICAL** |
| GET /pdf-files/{id}/objects | Get extracted PDF objects | **CRITICAL** |
| POST /pdf-files/process | Process uploaded PDF without storing | **CRITICAL** |

### 🔥 Critical Issue

**NO backend router for PDF files**. Frontend expects:
- PDF metadata (filename, size, page count)
- PDF download endpoint (returns binary with proper headers)
- PDF object extraction (text_words, graphics, images, tables)
- Temporary processing for template builder

These are essential for:
- Template builder (process uploaded PDF)
- ETO run detail modal (download and view PDFs)
- Template detail modal (view source PDF)

---

## 7. Health Check API

**Backend implements**: 1 endpoint
**Frontend does not expect**: Health endpoint not in API summary

### ➕ Backend Only

| Endpoint | Purpose |
|----------|---------|
| GET /health | System status and uptime |

**Note**: Not documented in frontend API summary but likely used by system monitoring.

---

## Summary of Critical Issues

### 🔴 Blockers (Must Fix Immediately)

1. **PDF Files Router Missing** - Create entire router with 4 endpoints
2. **POST /pdf-templates/simulate** - Template builder testing depends on this
3. **POST /eto-runs/upload** - Manual PDF upload functionality blocked

### 🟠 High Priority (Design Alignment)

4. **Bulk operations** - Align paths (reprocess/skip/delete)
   - Frontend: POST /eto-runs/reprocess, POST /eto-runs/skip, DELETE /eto-runs
   - Backend: PATCH /eto-runs/reprocess-bulk, PATCH /eto-runs/bulk/skip, no bulk delete
5. **Activation endpoints** - Choose pattern
   - Frontend: Separate POST activate/deactivate endpoints
   - Backend: Single PATCH toggle with query param
6. **Template/Config CRUD** - Add missing delete endpoints
7. **Pipeline CRUD** - Add PUT/DELETE endpoints

### 🟡 Medium Priority (Enhancements)

8. **GET /pdf-templates/{id}/versions** - Version history listing
9. **POST /email-configs/validate** - Pre-creation validation
10. **HTTP methods** - Standardize (POST vs PATCH, PUT vs PATCH)

### 🟢 Low Priority (Documentation)

11. **Extra backend endpoints** - Document or add to frontend API summary
12. **Query param differences** - Document filtering/sorting variations

---

## Recommendations

### Phase 1: Unblock Development (1-2 days)

1. **Create PDF Files router** with all 4 endpoints
2. **Add POST /pdf-templates/simulate** endpoint
3. **Add POST /eto-runs/upload** endpoint

### Phase 2: Align Core Operations (2-3 days)

4. **Standardize bulk operations** - Choose consistent pattern
5. **Unify activation pattern** - Pick one design for all resources
6. **Add missing CRUD endpoints** - Complete PUT/DELETE for templates, configs, pipelines

### Phase 3: Refinement (1 day)

7. **Document all extra endpoints** - Update frontend API summary or mark as internal
8. **Align HTTP methods** - Follow REST conventions consistently
9. **Add missing utility endpoints** - Version listing, validation, etc.

---

## Design Pattern Recommendations

### Activation/Deactivation

**Option A (Frontend preference)**:
```
POST /resource/{id}/activate
POST /resource/{id}/deactivate
```

**Option B (Backend current)**:
```
PATCH /resource/{id}/activate?activate=true
PATCH /resource/{id}/activate?activate=false
```

**Recommendation**: Use Option A for clarity and REST semantics.

### Bulk Operations

**Frontend pattern**:
```
POST /eto-runs/reprocess
POST /eto-runs/skip
DELETE /eto-runs
Body: { run_ids: number[] }
```

**Backend pattern**:
```
PATCH /eto-runs/reprocess-bulk
PATCH /eto-runs/bulk/skip
```

**Recommendation**: Use frontend pattern (cleaner, more RESTful). Body-based bulk operations are standard.

### HTTP Methods

**Current inconsistencies**:
- Template update: Frontend PUT, Backend PATCH
- Single operations: Frontend POST, Backend PATCH
- Pipeline create: Frontend POST, Backend POST /upload

**Recommendation**:
- POST: Create new resources
- PUT: Full replace/update
- PATCH: Partial update
- DELETE: Delete resources

---

## Next Steps

1. ✅ **Review this document** with team
2. ⬜ **Prioritize missing endpoints** based on frontend needs
3. ⬜ **Create PDF Files router** (critical blocker)
4. ⬜ **Add simulate endpoint** to pdf_templates.py
5. ⬜ **Align bulk operations** pattern
6. ⬜ **Update API documentation** on both sides
