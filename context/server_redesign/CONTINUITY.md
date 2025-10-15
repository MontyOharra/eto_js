# Server Redesign - Continuity Document

## Current Status

**Phase:** Phase 3 - Endpoint Definitions (In Progress)

**Completed Work:**
- ✅ Phase 1: Domain & Router Segmentation (6 routers identified)
- ✅ Phase 2: Per-Domain Analysis (All 6 domains fully analyzed in API_DESIGN.md)
- ✅ Phase 3: Endpoint Definitions (Partial)
  - ✅ Router 1: `/email-configs` - Complete (10 endpoints)
  - ✅ Router 2: `/eto-runs` - Complete (6 endpoints)
  - ✅ Router 3: `/pdf-files` - Complete (3 endpoints)
  - 🚧 Router 4: `/pdf-templates` - **IN PROGRESS**
  - ⏳ Router 5: `/modules` - Not started
  - ⏳ Router 6: `/pipelines` - Not started (accessed via templates, may not need dedicated router)
  - ⏳ Router 7: `/health` - Not started

**Documents Created:**
- `context/server_redesign/INSTRUCTIONS.md` - Design methodology (front-end-first, top-down)
- `context/server_redesign/API_DESIGN.md` - Phase 2 requirements for all 6 domains
- `context/server_redesign/API_ENDPOINTS.md` - Phase 3 endpoint specifications (3 routers complete, 1 in progress)
- `context/ARCHITECTURE_REDESIGN.md` - Type system design (Pydantic for API, DTOs for service/repo layers)

---

## Current Work: Router 4 - `/pdf-templates` Endpoint Design

### Context

We are designing the PDF Templates router endpoints. This is the most complex router involving:
- Template creation wizard (3 steps: signature objects, extraction fields, pipeline building)
- Template versioning system (draft versions, numbered versions, current_version_id)
- Optional testing (simulate ETO run without creating records)
- Template activation/deactivation
- Version history viewing

### Key Design Decisions Made

#### 1. Response Format
- **Decision**: Use direct responses (no wrapper objects) - FastAPI style
- All successful operations return data directly
- HTTP status codes indicate success/failure
- Pagination uses `{items: [], total, limit, offset}` format

#### 2. Bulk Operations (ETO Runs)
- **Decision**: Use `204 No Content` for mutation operations that trigger frontend table refresh
- Examples: POST /eto-runs/reprocess, POST /eto-runs/skip, DELETE /eto-runs
- Frontend refreshes all tables on success, so returning data is redundant

#### 3. PDF Objects Response Type
- **Decision**: Use grouped/typed structure (not raw JSON array)
- Return objects grouped by type for type safety and easier frontend consumption
- 7 object types: text_words, text_lines, graphic_rects, graphic_lines, graphic_curves, images, tables
- Trade-off: 5-200ms overhead for grouping vs better DX and type safety
- Acceptable because this is infrequent operation (template wizard initialization)

#### 4. Template Creation Entry Points
- **Decision**: Two separate endpoints for clarity and type safety
  - `POST /pdf-templates/from-upload` - Create from new PDF upload
  - `POST /pdf-templates/from-eto-run` - Create from existing ETO run's PDF

**Reasoning:**
- Frontend knows context (template page vs ETO run page)
- Type-safe payloads (can't send wrong data)
- Avoids multipart/form-data complexity with discriminated unions
- Clearer error messages per endpoint

**Endpoint Specifications:**

```
POST /pdf-templates/from-upload
Content-Type: multipart/form-data

Request:
- name: string (required)
- description: string (optional)
- pdf_file: File (required, PDF only)

Response: 201 Created
{
  "template_id": number,
  "draft_version_id": number,
  "pdf_file_id": number,
  "name": string,
  "status": "draft"
}
```

```
POST /pdf-templates/from-eto-run
Content-Type: application/json

Request:
{
  "name": string,
  "description"?: string,
  "eto_run_id": number
}

Response: 201 Created
{
  "template_id": number,
  "draft_version_id": number,
  "pdf_file_id": number,
  "name": string,
  "status": "draft"
}
```

**Backend Logic:**
- `from-upload`: Creates PDF record, extracts objects, creates template + draft version
- `from-eto-run`: Looks up ETO run, gets existing pdf_file_id (objects already extracted), creates template + draft version

**Both return same response structure** - frontend proceeds to wizard using template_id and draft_version_id.

---

## Next Steps - Questions to Answer

### 1. Progressive Saving vs Single Save
**Question:** Should the wizard save after each step, or only at the end?

**Options:**
- **Progressive**: `PUT /pdf-templates/{id}/versions/{version_id}/signature`, `PUT .../extraction`, `PUT .../pipeline`
  - Pros: User can close browser and resume, data persisted incrementally
  - Cons: More API calls, partial state possible
- **Single Save**: All 3 steps saved at once when user clicks "Finalize"
  - Pros: Atomic operation, simpler state management
  - Cons: Lost progress if browser closes, larger payload

**User's question to address:** Do we want state persistence across browser sessions?

### 2. Draft Version Lifecycle
**Question:** When is the draft version created?

**Options:**
- Immediately when `POST /pdf-templates/from-*` is called (template + draft created together)
- After Step 1 completion
- Only when user saves

**Recommendation:** Create draft immediately when template is created (during POST /pdf-templates/from-*), so user always has a draft to work with.

### 3. Pipeline Compilation Timing
**Question:** When does pipeline compilation happen?

**Options:**
- During Step 3 save (immediate validation)
- During testing (lazy compilation)
- During final save/finalization (latest possible)

**Consideration:** Compilation includes deduplication (checking if compiled plan already exists), which affects pipeline_definition_id.

### 4. Finalization Process
**Question:** How does the user finalize the template?

**Likely approach:**
- User completes Steps 1-3 (optionally tests)
- User clicks "Save Template"
- Backend:
  - Converts draft version: `version_num = 0 → 1`, `is_draft = true → false`
  - Updates template: `current_version_id = draft_version_id`, `status = draft → active`
  - Returns finalized template

**API:** `POST /pdf-templates/{id}/finalize` or similar?

### 5. Cancellation Process
**Question:** How does user cancel template creation?

**Likely approach:**
- User clicks "Cancel" in wizard
- Backend:
  - If new template: Delete template + draft version + PDF (if uploaded)
  - If editing: Delete draft version only
  - Returns success

**API:** `DELETE /pdf-templates/{id}` (if new) or `DELETE /pdf-templates/{id}/versions/{draft_id}` (if editing)?

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

## Open Questions for Next Session

1. Should we use progressive saving (PUT after each step) or single save at end?
2. When exactly should pipeline compilation happen?
3. What should the finalization endpoint look like?
4. How should cancellation be handled (one endpoint or two)?
5. Should we allow editing active templates, or require deactivation first?
6. What endpoints are needed for version history viewing?

---

## Recommended Next Actions

1. **Answer open questions** about template creation workflow
2. **Design remaining template endpoints**:
   - Template finalization
   - Template cancellation
   - Template version management (create new version for editing)
   - Template activation/deactivation
   - Template deletion (draft only)
   - Version history viewing
3. **Continue with Router 5**: `/modules` (simple read-only catalog)
4. **Design Router 7**: `/health` (single endpoint)
5. **Complete Phase 3** endpoint definitions
6. **Move to Phase 4**: Schema definitions (detailed request/response types)

---

## Notes

- Template creation is the most complex workflow in the system
- Versioning adds complexity but provides audit trail and allows safe editing
- Testing feature is optional but valuable for validation
- Pipeline compilation and deduplication happens transparently in backend
- Frontend drives all design decisions - wizard UX determines API structure
