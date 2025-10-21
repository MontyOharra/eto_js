# Server Redesign - Continuity Document

## Current Status

**Phase:** Backend Implementation - Router & Schema Setup

**Latest Work (2025-10-21):**
- ✅ All 7 router files created with endpoint definitions (pass bodies)
- ✅ All 7 schema files created with Pydantic models (~830 lines total)
- ✅ Import statements fixed and verified across all routers and schemas
- ✅ Router and schema package exports properly configured
- 📍 Ready for error handling implementation

**Router Implementation Details:**
1. **email_configs.py** - 10 endpoints (list, get, create, update, delete, activate, deactivate, discover accounts/folders, validate)
2. **eto.py** - 6 endpoints (list, get, upload, bulk reprocess/skip/delete)
3. **pdf_files.py** - 4 endpoints (metadata, download, objects, process-objects) - NEW FILE CREATED
4. **pdf_templates.py** - 9 endpoints (list, get, create, update, activate/deactivate, versions, simulate)
5. **modules.py** - 1 endpoint (list catalog)
6. **pipelines.py** - 5 endpoints (list, get, create, update, delete - dev/testing only)
7. **health.py** - 1 endpoint (health check)

**Schema Implementation Details:**
- Created comprehensive Pydantic models for all request/response types
- No type collation yet - duplicated types intentionally kept separate per design
- Key models: PipelineState, ExtractionField, SignatureObject, EtoRunDetail, etc.
- Fixed import structure: Updated `api/schemas/__init__.py` with all exports
- Added `pdf_files_router` to `api/routers/__init__.py`

**Next Immediate Task:**
Add error handling to all endpoint functions as specified in API_ENDPOINTS.md:
- 400 Bad Request (business logic errors)
- 404 Not Found (resource not found)
- 409 Conflict (state conflicts)
- 422 Unprocessable Entity (validation errors)
- 500 Internal Server Error (unexpected failures)

**Previous Work (2025-10-18):**
- ✅ Pipeline builder (step 3) integrated into template builder
- ✅ Entry points auto-generated from extraction fields
- ✅ Pipelines page created with mock API
- ⚠️ **CRITICAL DISCOVERY**: Pipeline types don't match backend schema

**Frontend Pipeline Types Issue:**

The pipelines feature was implemented with types based on assumptions that don't match the actual database:

**Incorrect Frontend Assumptions:**
- Pipelines have name, description, status fields
- Pipelines have versions and usage counts
- Pipelines are standalone manageable entities

**Actual Backend Structure (from models.py):**
- `pipeline_definitions`: id, pipeline_state (JSON), visual_state (JSON), compiled_plan_id, timestamps
- `pipeline_compiled_plans`: id, plan_checksum, compiled_at
- `pipeline_definition_steps`: execution plan steps
- Pipelines are PURE graph definitions, no metadata
- Templates own the name/description/status via `pdf_template_versions.pipeline_definition_id`

**Required Fixes:**
1. Remove name, description, status from pipeline types
2. Update PipelineListItem to match actual schema
3. Update mock API to return realistic data
4. Redesign PipelineCard for inspection view (show ID, timestamps, compiled plan info)
5. Update page to be "Pipeline Inspector" for dev/testing
6. Add template reference information to show which templates use each pipeline

**Backend Redesign Status:**
**Phase:** Phase 5 - Service Layer Design ✅ **COMPLETE**

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
- ✅ Phase 4: Schema Definitions **COMPLETE** (~125 Pydantic models in SCHEMAS.md)
- ✅ Phase 5: Service Layer Design **COMPLETE** (All 6 services designed - Email, PDF, ETO, Template, Pipeline & Module)

**Documents Created:**
- `context/server_redesign/INSTRUCTIONS.md` - Design methodology (front-end-first, top-down)
- `context/server_redesign/API_DESIGN.md` - Phase 2 requirements for all 6 domains
- `context/server_redesign/API_ENDPOINTS.md` - Phase 3 endpoint specifications (all 7 routers complete)
- `context/server_redesign/SCHEMAS.md` - Phase 4 Pydantic schemas (all 35 endpoints)
- `context/server_redesign/SERVICE_LAYER_DESIGN.md` - Phase 5 service architecture and patterns
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

## Phase 3 & 4 Complete! 🎉

**All 7 routers fully specified with 35 total endpoints:**
- ✅ Router 1: `/email-configs` - 10 endpoints
- ✅ Router 2: `/eto-runs` - 6 endpoints
- ✅ Router 3: `/pdf-files` - 3 endpoints
- ✅ Router 4: `/pdf-templates` - 10 endpoints
- ✅ Router 5: `/modules` - 1 endpoint
- ✅ Router 6: `/pipelines` - 5 endpoints (dev/testing)
- ✅ Router 7: `/health` - 1 endpoint

**~125 Pydantic schemas defined** (SCHEMAS.md)

---

## Phase 5: Service Layer Design 🚧

### Email Ingestion Service - Design Complete ✅

**Location**: `features/email_ingestion/service.py`

**Service Responsibilities**:
1. **Account/Folder Discovery**: discover_email_accounts(), discover_folders(), test_connection_for_new_config()
2. **Configuration Management**: create_config(), get_config(), update_config(), delete_config(), list_configs()
3. **Listener Lifecycle**: activate_config(), deactivate_config(), stop_config_listeners(), get_active_listeners()
4. **Email Processing**: process_email(), _process_pdf_attachment(), get_processed_emails()
5. **Service Lifecycle**: startup_recovery(), shutdown(), is_healthy()

**Key Design Decisions**:
- Listener threads manage email polling with filter rules
- Deactivation (user-initiated) vs shutdown (preserves config status for recovery)
- Cross-service orchestration with PDF and ETO services
- Transaction support for multi-repository operations
- DTOs for all internal service/repository data transfer
- Pydantic only at API boundary (routers)

**DTOs Required**:
- EmailConfigDTO, EmailConfigCreateDTO, EmailConfigUpdateDTO
- EmailFilterRuleDTO
- EmailDTO, EmailCreateDTO
- EmailConfigSummaryDTO, ListenerStatusDTO

**What Needs to Change**:
1. Create DTOs (frozen dataclasses) for persistence types
2. Update service method signatures to use DTOs
3. Update repositories to accept/return DTOs
4. Create mapper functions in routers (Pydantic ↔ DTO)
5. Add transaction context manager support

### PDF Processing Service - Design Complete ✅

**Location**: `features/pdf_processing/service.py`

**Service Responsibilities**:
1. **Storage & Extraction**: store_pdf() - validates, deduplicates, extracts objects, stores file
2. **Retrieval**: get_pdf(), get_pdf_content(), get_pdf_objects()
3. **Utilities**: check_duplicate(), is_healthy()

**Key Design Decisions**:
- Synchronous object extraction (7 types: TextWord, TextLine, GraphicRect, GraphicLine, GraphicCurve, Image, Table)
- SHA-256 hash-based deduplication
- Filesystem storage with date-based organization
- Objects stored as JSON in DB, converted to typed dataclasses on retrieval
- PDFs never deleted (persistent)
- Access by ID only (no generic query endpoints)

**Dataclasses Required** (in `shared/types/`):
- PdfFile, PdfFileCreate
- 7 PDF object types, PdfObject union type
- PdfExtractionResult

**What Needs to Change**:
1. Create dataclasses (frozen) in `shared/types/`
2. Update service to use dataclasses
3. Update repository for JSON ↔ dataclass conversion
4. Create mappers in routers
5. Add missing endpoint for PDF download

### Template Management Service - Design Complete ✅

**Location**: `features/template_management/service.py`

**Service Responsibilities**:
1. **Template CRUD**: create_template(), get_template(), update_template_metadata(), delete_template(), list_templates()
2. **Template Activation**: activate_template(), deactivate_template(), get_templates_for_matching()
3. **Version Management**: update_template_definition(), get_version(), list_versions(), get_current_version()
4. **Wizard Simulation**: simulate_template(), _extract_data()
5. **Template Discovery**: find_templates_needing_pdf(), get_template_usage_stats()
6. **Service Lifecycle**: is_healthy()

**Key Design Decisions**:
- Stateless wizard workflow (frontend maintains state, no draft versions during creation)
- Atomic template creation (template + version 1 in single transaction)
- Two update paths: metadata-only vs definition updates (creates new version)
- Template status flow: draft → active (one-way), active ↔ inactive (reversible)
- Only draft templates can be deleted
- All versions preserved for historical reference
- Simulation endpoint for testing without persistence
- Pipeline integration via Pipeline Service
- Extraction helper method shared between simulation and real ETO runs

**Dataclasses Required** (in `shared/types/`):
- PdfTemplate, PdfTemplateCreate, PdfTemplateUpdate
- PdfTemplateVersion, PdfTemplateVersionCreate
- SignatureObject, ExtractionField, BoundingBox
- PdfTemplateStatus (enum: DRAFT, ACTIVE, INACTIVE)
- PdfTemplateSummary, PdfTemplateWithVersion
- TemplateSimulationRequest, TemplateSimulationResult
- PipelineDefinition (from Pipeline Service types)

**What Needs to Change**:
1. Create dataclasses (frozen) in `shared/types/`
2. Update service method signatures to use dataclasses
3. Update repositories to accept/return dataclasses
4. Create mapper functions in routers (Pydantic ↔ dataclass)
5. Add transaction context manager support
6. Implement extraction helper method for bounding box text extraction

### Pipeline Service - Design Complete ✅

**Location**: `features/pipeline/service.py` (unified with `features/pipeline_execution/service.py`)

**Service Responsibilities**:
1. **Pipeline CRUD**: create_pipeline(), get_pipeline(), list_pipelines(), list_pipeline_summaries()
2. **Pipeline Validation**: 6-stage validation (schema, indexing, graph, edges, modules, reachability)
3. **Pipeline Compilation**: Pruning, topological sorting, checksum calculation, step building
4. **Pipeline Execution**: execute_pipeline() via Dask DAG with action barrier
5. **Simulation Mode**: execute_pipeline_simulation() for template wizard testing
6. **Service Lifecycle**: is_healthy()

**Key Design Decisions**:
- Unified service (merges validation/compilation + execution into single service)
- Checksum-based deduplication (pipelines with identical logic share compiled plans)
- 6-stage validation pipeline before compilation (fail fast on validation errors)
- Dask DAG execution with action module barrier (all non-actions complete before actions start)
- Module execution via ModuleRegistry with ModuleExecutionContext
- Execution auditing with step-by-step results (PipelineExecutionRun + PipelineExecutionStep)
- Two execution modes: persist_run=True (real runs) vs persist_run=False (simulation)
- Dev/testing endpoints for standalone pipelines (Router 6)

**Dataclasses Required** (in `shared/types/`):
- PipelineDefinition, PipelineDefinitionCreate, PipelineDefinitionSummary
- PipelineState, VisualState, EntryPoint, ModuleInstance, NodeInstance, NodeConnection, ModulePosition
- PipelineDefinitionStep, PipelineDefinitionStepCreate
- PipelineExecutionRun, PipelineExecutionRunCreate
- PipelineExecutionStep, PipelineExecutionStepCreate
- PipelineValidationResult, PipelineValidationError, PipelineValidationErrorCode
- PipelineIndices, PinInfo
- ModuleExecutionContext

**What Needs to Change**:
1. Unify two separate services (pipeline/ and pipeline_execution/) into single Pipeline Service
2. Create dataclasses (frozen) in `shared/types/`
3. Update service method signatures to use dataclasses
4. Update 4 repositories (definition, steps, runs, execution steps) to accept/return dataclasses
5. Create mapper functions in routers (Pydantic ↔ dataclass)
6. Add execute_pipeline_simulation() method for template wizard testing
7. Update module registry to use dataclasses

### Module Service - Design Complete ✅

**Location**: `features/modules/service.py`

**Service Responsibilities**:
1. **Module Catalog Discovery**: get_module_catalog(), get_module_info(), get_modules_by_kind()
2. **Module Registration**: register_module_from_class(), register_modules_from_registry(), sync_module_packages()
3. **Module Execution**: execute_module() (for testing), _get_module_class(), _execute_module_instance()
4. **Service Lifecycle**: _auto_discover_modules(), get_registry_stats(), is_healthy()

**Key Design Decisions**:
- Dual responsibility: Discovery (frontend API) + Registration (backend CLI)
- ModuleRegistry singleton for in-memory class cache and dynamic loading
- Module catalog database table with (id, version) composite key
- Security validation for handler_name before dynamic import
- CLI-driven sync process (sync_modules.py calls service methods)
- Auto-discovery at service startup populates registry from package paths
- Module execution context for pipeline integration (is_simulation flag for action modules)
- Caching via ModuleRegistry (LRU cache with 1-hour TTL for dynamically loaded modules)

**Dataclasses Required** (in `shared/types/`):
- ModuleCatalog, ModuleCatalogCreate, ModuleCatalogUpdate, ModuleCatalogSummary
- SyncResult, RegistryStats
- ModuleExecutionContext
- (Module types already exist: BaseModule, ModuleMeta, IOShape, NodeGroup)

**What Needs to Change**:
1. Convert Pydantic models to frozen dataclasses
2. Update service method signatures to use dataclasses
3. Update repository to accept/return dataclasses
4. Create mapper functions in routers (Pydantic ↔ dataclass)
5. Add registration methods to service (register_module_from_class, register_modules_from_registry, sync_module_packages)
6. Update CLI tools to call service instead of repository directly
7. Keep ModuleRegistry as-is (internal implementation detail)

---

## Phase 5 Complete! 🎉

**All 6 services fully designed:**
- ✅ Service 1: Email Ingestion Service - Discovery, configuration, listener lifecycle, email processing
- ✅ Service 2: PDF Processing Service - Storage, extraction, retrieval, deduplication
- ✅ Service 3: ETO Processing Service - Template matching, extraction, transformation, orchestration
- ✅ Service 4: Template Management Service - Template CRUD, activation, versioning, simulation
- ✅ Service 5: Pipeline Service - CRUD, validation, compilation, execution, simulation
- ✅ Service 6: Module Service - Catalog discovery, registration, execution

**Design patterns established:**
- Frozen dataclasses for all service/repository operations
- Pydantic only at API boundary (routers)
- Explicit mapping functions in routers
- Transaction support for multi-repository operations
- Error bubbling from repositories through services to API layer
- Universal dataclass return (including discovery methods)

---

## Recommended Next Actions

1. **Move to Phase 6**: Repository Layer Design
   - Define data access patterns for each repository
   - Plan query methods and optimizations
   - Design dataclass ↔ SQLAlchemy ORM conversion
   - Document transaction support patterns (session parameter)
   - Identify shared repository patterns and base classes

2. **Move to Phase 7**: Implementation Planning
   - Determine implementation order based on service dependencies
   - Plan migration strategy (gradual vs all-at-once)
   - Identify shared infrastructure needed (dataclass definitions, base classes)
   - Create implementation checklist for each service

3. **Implementation Execution** (when ready):
   - Start with shared types (create all frozen dataclasses in shared/types/)
   - Implement repositories (dataclass ↔ ORM conversion)
   - Update services (accept/return dataclasses)
   - Create router mappers (Pydantic ↔ dataclass)
   - Test each service integration
   - Suggested order: PDF → Module → Pipeline → Template → Email → ETO (dependency order)

---

## Notes

- Template creation is the most complex workflow in the system
- Versioning adds complexity but provides audit trail and allows safe editing
- Testing feature is optional but valuable for validation
- Pipeline compilation and deduplication happens transparently in backend
- Frontend drives all design decisions - wizard UX determines API structure
- Service layer uses DTOs exclusively; Pydantic only at API boundary
