# Server Redesign - Continuity Document

## Current Status

**Phase:** Phase 3 - Endpoint Definitions ✅ **COMPLETE**

**Completed Work:**
- ✅ Phase 1: Domain & Router Segmentation (6 routers identified)
- ✅ Phase 2: Per-Domain Analysis (All 6 domains fully analyzed in API_DESIGN.md)
- ✅ Phase 3: Endpoint Definitions **COMPLETE** (35 total endpoints)
  - ✅ Router 1: `/email-configs` - Complete (10 endpoints)
  - ✅ Router 2: `/eto-runs` - Complete (6 endpoints)
  - ✅ Router 3: `/pdf-files` - Complete (3 endpoints)
  - ✅ Router 4: `/pdf-templates` - Complete (10 endpoints)
  - ✅ Router 5: `/modules` - Complete (1 endpoint)
  - ✅ Router 6: `/pipelines` - Complete (5 endpoints - dev/testing)
  - ✅ Router 7: `/health` - Complete (1 endpoint)

**Documents Created:**
- `context/server_redesign/INSTRUCTIONS.md` - Design methodology (front-end-first, top-down)
- `context/server_redesign/API_DESIGN.md` - Phase 2 requirements for all 6 domains
- `context/server_redesign/API_ENDPOINTS.md` - Phase 3 endpoint specifications (3 routers complete, 1 in progress)
- `context/ARCHITECTURE_REDESIGN.md` - Type system design (Pydantic for API, DTOs for service/repo layers)

---

## Router 4 Complete: `/pdf-templates` - Stateless Wizard with Simulation

### Final Design Summary

Router 4 is now complete with 10 endpoints using a **stateless wizard approach**:

#### Key Design Decisions

**1. No Draft Versions in Database**
- **Decision**: Frontend maintains wizard state, no DB persistence during creation/editing
- Wizard state is ephemeral (lives in frontend memory only)
- No `is_draft` field needed in database
- Simplified template versioning (only finalized versions exist)

**2. Stateless Simulation Endpoint**
- **Decision**: `POST /pdf-templates/simulate` for testing without DB persistence
- Runs full ETO process (extraction → transformation) without creating records
- Action modules simulate (no actual execution)
- Can be called repeatedly during wizard (modify and re-test)
- Pure computation, no side effects

**3. PDF Management Separation**
- **Decision**: Removed `POST /pdf-templates/from-upload` and `from-eto-run`
- PDF creation is separate concern (handled by `/pdf-files` endpoints)
- Template creation accepts `pdf_file_id` reference (no PDF upload)
- Frontend workflow:
  - Option A: Upload PDF via `/pdf-files` → Get `pdf_file_id` + objects → Use in wizard
  - Option B: Get `pdf_file_id` from existing ETO run → Get objects → Use in wizard

**4. Atomic Template Creation**
- **Decision**: `POST /pdf-templates` creates template + version 1 atomically
- All 3 wizard steps provided in single request (signature objects, extraction fields, pipeline)
- Template starts with `status = "draft"`
- Must call `POST /pdf-templates/{id}/activate` to use for matching
- No finalization endpoint needed (POST is the finalization)

**5. Version Management**
- **Decision**: `PUT /pdf-templates/{id}` creates new version (increments version_num)
- No draft versions stored between edits
- Frontend loads existing version, modifies in memory, saves new version
- Old versions preserved for historical ETO runs

#### Template Creation Flow

**New Template:**
1. Frontend gets PDF (upload or from ETO run)
2. Frontend gets objects via `GET /pdf-files/{id}/objects`
3. User completes 3-step wizard (frontend state only)
4. Optional: `POST /pdf-templates/simulate` (test repeatedly)
5. Final: `POST /pdf-templates` (creates template + version 1)
6. Activate: `POST /pdf-templates/{id}/activate`

**Editing Template:**
1. Frontend gets version data via `GET /pdf-templates/{id}/versions/{version_id}`
2. User modifies wizard steps (frontend state only)
3. Optional: `POST /pdf-templates/simulate` (test modifications)
4. Final: `PUT /pdf-templates/{id}` (creates new version)

**Cancellation:**
- Just discard frontend state (nothing in DB to clean up)

---

## Design Principles to Maintain

1. **Front-end-first design**: What does the frontend actually need?
2. **Direct responses**: No wrapper objects, HTTP status codes indicate success
3. **Type safety**: Prefer explicit structures over dynamic JSON where possible
4. **Atomic operations**: Bulk operations fail entirely if any validation fails
5. **Clear intent**: Endpoint names and payloads should be self-documenting
6. **Consistency**: Follow patterns established in completed routers

---

## Database Schema References

**Relevant Tables for Templates:**
- `pdf_templates`: Template metadata (name, description, source_pdf_id, status, current_version_id)
- `pdf_template_versions`: Version data (version_num, is_draft, signature_objects, extraction_fields, pipeline_definition_id, usage_count)
- `pdf_files`: Source PDFs (objects_json contains extracted PDF objects)
- `pipeline_definitions`: Pipeline state (pipeline_state, visual_state, compiled_plan_id)
- `pipeline_compiled_plans`: Compiled execution plans (shared across pipelines with same logic)

**Key Fields:**
- `pdf_templates.status`: `draft` | `active` | `inactive`
- `pdf_template_versions.version_num`: `0` for drafts, `1+` for finalized versions
- `pdf_template_versions.is_draft`: `true` for version_num = 0, `false` otherwise
- `pdf_templates.current_version_id`: Points to the active version used for template matching

---

## Template Versioning Rules

1. **New template creation**: Creates template with `status = draft` + version with `version_num = 0`, `is_draft = true`
2. **Editing existing template**: Creates new draft version (`version_num = 0`, `is_draft = true`), old versions preserved
3. **Finalization**: Draft version becomes `version_num = 1` (or next available), `is_draft = false`, template's `current_version_id` updated
4. **Cancellation**: Draft version deleted, if new template also delete template and PDF (if uploaded)
5. **Old versions**: Never deleted (historical reference for ETO runs that used them)

---

## Wizard Step Details

**Step 1: Signature Objects Selection**
- Frontend: Displays PDF with clickable objects (from GET /pdf-files/{id}/objects)
- User: Clicks objects to select/deselect as signature objects
- Data: Array of selected object identifiers/coordinates
- Storage: `pdf_template_versions.signature_objects` (JSON)

**Step 2: Extraction Fields Definition**
- Frontend: Drawing mode for bounding boxes
- User: Draws boxes, labels them, optionally adds validation regex and required flag
- Data: Array of extraction field definitions
- Storage: `pdf_template_versions.extraction_fields` (JSON)

**Step 3: Pipeline Building**
- Frontend: Visual graph builder with module catalog sidebar
- User: Drags modules, connects them, configures parameters
- Data: Pipeline state (logical structure) + visual state (node positions)
- Storage: Creates `pipeline_definitions` record, links via `pdf_template_versions.pipeline_definition_id`

**Step 4: Testing (Optional)**
- Frontend: "Test Template" button
- Backend: Simulates full ETO process without creating eto_run record, action modules don't execute
- Returns: Extracted data, transformation results
- Storage: No persistence (simulation only)

---

## Phase 3 Complete! 🎉

**All 7 routers fully specified with 35 total endpoints:**
- ✅ Router 1: `/email-configs` - 10 endpoints
- ✅ Router 2: `/eto-runs` - 6 endpoints
- ✅ Router 3: `/pdf-files` - 3 endpoints
- ✅ Router 4: `/pdf-templates` - 10 endpoints
- ✅ Router 5: `/modules` - 1 endpoint
- ✅ Router 6: `/pipelines` - 5 endpoints (dev/testing)
- ✅ Router 7: `/health` - 1 endpoint

## Recommended Next Actions

1. **Move to Phase 4**: Schema Definitions
   - Define detailed Pydantic request/response schemas
   - Create validation rules and constraints
   - Document all field types and formats
2. **Move to Phase 5**: Service Layer Design
   - Define service methods for business logic
   - Identify transaction boundaries
   - Plan cross-domain orchestration
3. **Move to Phase 6**: Repository Layer Design
   - Define data access patterns
   - Plan query methods and optimizations
   - Design JSON serialization strategies

---

## Notes

- Template creation is the most complex workflow in the system
- Versioning adds complexity but provides audit trail and allows safe editing
- Testing feature is optional but valuable for validation
- Pipeline compilation and deduplication happens transparently in backend
- Frontend drives all design decisions - wizard UX determines API structure
