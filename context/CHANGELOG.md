# ETO System - Development Changelog

## Overview
This document tracks major development milestones and features implemented in the Email-to-Order (ETO) PDF processing system.

---

## [2025-10-26 00:30] — Pipeline Execution & Checksum Fixes

### Spec / Intent
- Fix pipeline checksum to only capture logical graph structure (not IDs or labels)
- Implement backend pipeline execution endpoint for testing
- Create frontend execution modal for pipeline testing
- Fix entry point modal UX issues (input focus, event handling)

### Changes Made

**Backend - Pipeline Checksum** (`server-new/src/features/pipelines/service.py`):
- Completely rewrote `_calculate_checksum()` method for ID-agnostic hashing
- Implemented topology-based BFS traversal from entry points
- Excluded all instance-specific data: module_instance_id, node_id, entry point names
- Canonical representation uses: EP_0, M_0, M_1, M_2... for deterministic ordering
- Entry points sorted by downstream connections, only count/index included in hash
- Modules at same topology level sorted by (module_ref, config, pins)
- Connections mapped to canonical references: "M_0.out.0.0 → M_1.in.0.0"
- Two pipelines with identical logic now produce identical checksums regardless of IDs/names

**Backend - Execution Schemas** (`server-new/src/api/schemas/pipelines.py`):
- Added `ExecutePipelineRequest` - Entry values keyed by entry point name
- Added `ExecutionStepResultDTO` - Step execution result with inputs/outputs/error
- Added `ExecutePipelineResponse` - Status, steps, action data, error message

**Backend - Execution Endpoint** (`server-new/src/api/routers/pipelines.py`):
- Added `POST /api/pipelines/{id}/execute` endpoint (lines 170-261)
- Loads pipeline definition and validates it's compiled
- Loads compiled steps from database
- Calls `PipelineExecutionService.execute_pipeline()` with entry values
- Returns step-by-step execution trace with inputs/outputs
- Simulation mode: Actions collect data but don't execute (for testing)
- Detailed docstring with example request/response

**Frontend - Execution Modal** (`client/src/renderer/features/pipelines/components/modals/ExecutePipelineModal.tsx`):
- NEW FILE: Complete modal for pipeline execution testing
- Input fields for each entry point value (with validation)
- Execute button calls backend API
- Results display showing:
  - Success/failure status with visual indicators
  - Step-by-step execution trace with inputs/outputs
  - Action data (what would be executed in production)
  - Error messages for failed executions
- Modal z-index [60] to appear above PipelineViewerModal [50]

**Frontend - API Hook** (`client/src/renderer/features/pipelines/hooks/usePipelinesApi.ts`):
- Added `executePipeline()` method (lines 188-199)
- Posts to `/api/pipelines/{id}/execute` with entry_values
- Returns execution result with steps and action data
- Integrated with existing loading/error state management

**Frontend - Pipeline Viewer** (`client/src/renderer/features/pipelines/components/modals/PipelineViewerModal.tsx`):
- Added "Execute Pipeline" button to header (green, prominent)
- Integrated ExecutePipelineModal with state management
- Passes entry points from pipeline_state to execution modal
- Button only appears when pipeline is loaded

**Frontend - Entry Point Modal UX** (`client/src/renderer/features/pipelines/components/EntryPointModal.tsx`):
- Added autofocus to first input field (useRef + useEffect)
- Added event.stopPropagation() to prevent backdrop interference
- Added keyboard shortcuts:
  - Escape: Cancel modal
  - Ctrl+Enter: Confirm entry points
- Made backdrop clickable to close modal
- Fixed intermittent focus issues

### Technical Details

**Checksum Algorithm**:
1. Sort entry points by downstream connections (deterministic ordering)
2. Include only entry point count/index (not names/IDs)
3. BFS traversal from entry points to establish topology levels
4. Within each level, sort modules by (module_ref, config, pins)
5. Assign canonical IDs: EP_0, M_0, M_1, M_2...
6. Map connections to canonical references
7. SHA-256 hash of deterministic JSON representation

**Execution Flow**:
1. Frontend: User enters entry point values
2. Frontend: POST /api/pipelines/{id}/execute with entry_values
3. Backend: Load pipeline + compiled steps
4. Backend: PipelineExecutionService executes with Dask task graph
5. Backend: Return step results + action data (simulation mode)
6. Frontend: Display results with color-coded status

**Simulation Mode**:
- All transform/logic modules execute normally
- Action modules collect input data but don't execute
- Shows what would happen in production without side effects
- Perfect for testing pipeline logic

### Errors Fixed

**Error 1: Different checksums for identical pipelines**
- Root cause: Entry point names ("test" vs "asd") caused different hashes
- Fix: Excluded entry point names entirely, only count/index included

**Error 2: AttributeError in checksum calculation**
- Root cause: Tried to access non-existent PipelineIndices attributes
- Fix: Used pruned_pipeline.modules and pruned_pipeline.connections directly

**Error 3: Entry point modal input not focusable**
- Root cause: Event propagation and lack of autofocus
- Fix: Added autofocus, stopPropagation, keyboard shortcuts

### Next Actions
- Test pipeline execution with various entry point values
- Test checksum deduplication with identical pipelines
- Verify execution results match expected behavior
- Test error handling for invalid entry values

### Notes
- Checksum now truly captures only logical structure
- Execution modal ready for comprehensive pipeline testing
- All changes TypeScript compiled successfully (no errors)
- User will handle all testing

---

## [2025-10-24 21:45] — Pipeline Validation Endpoint Implementation

### Spec / Intent
- Create API endpoint for pipeline validation (`POST /api/pipelines/validate`)
- Expose existing validation logic in `PipelineService` for frontend use
- Enable "Validate Pipeline" button in pipeline builder to check structure before saving
- Provide structured error responses with error codes and messages

### Changes Made

**Backend - PipelineService** (`server-new/src/features/pipelines/service.py`):
- Added public `validate_pipeline()` method (lines 689-743)
- Wraps existing private `_validate_pipeline()` method
- Returns structured dict with `valid: bool` and `errors: list`
- Parses `ValidationError` messages to extract error codes:
  - `invalid_reference` - Non-existent pins or modules
  - `type_mismatch` - Incompatible connection types
  - `duplicate_connection` - Duplicate connections
  - `cycle_detected` - Circular dependencies
  - `unconnected_input` - Missing required connections
  - `invalid_connection` - Invalid pin directions
  - `internal_error` - Unexpected validation failures

**Backend - API Schemas** (`server-new/src/api/schemas/pipelines.py`):
- Added `ValidationErrorDTO` (lines 125-129): Error code, message, optional context
- Added `ValidatePipelineRequest` (lines 132-134): Accepts `pipeline_json` (PipelineStateDTO)
- Added `ValidatePipelineResponse` (lines 137-140): Returns `valid` flag and `errors` list

**Backend - Pipelines Router** (`server-new/src/api/routers/pipelines.py`):
- Added `POST /validate` endpoint (lines 123-163)
- Converts request DTO to domain `PipelineState` using existing mapper
- Calls `pipeline_service.validate_pipeline()`
- Returns structured validation response with detailed error information
- No database modifications (validation only)

**Frontend - API Types** (`client/src/renderer/features/pipelines/api/types.ts`):
- Added `ValidationErrorDTO` interface (lines 152-156)
- Added `ValidatePipelineRequestDTO` interface (lines 158-160)
- Added `ValidatePipelineResponseDTO` interface (lines 162-165)

**Frontend - Domain Types** (`client/src/renderer/features/pipelines/types.ts`):
- Added `ValidationError` interface (lines 164-168)
- Added `ValidatePipelineRequest` interface (lines 170-201)
- Added `ValidatePipelineResponse` interface (lines 203-206)

**Frontend - Pipelines Hook** (`client/src/renderer/features/pipelines/hooks/usePipelinesApi.ts`):
- Added `validatePipeline()` method (lines 137-152)
- Posts to `/api/pipelines/validate` endpoint
- Returns validation result with error details
- Uses same loading/error state management as other API methods

**Frontend - Pipeline Builder** (`client/src/renderer/pages/dashboard/pipelines/create.tsx`):
- Updated `handleValidate()` to use `validatePipeline()` from hook (lines 69-99)
- Replaced manual fetch with proper API call
- Maintains same UI feedback (alerts and console logging)
- Displays error count and details on validation failure

### Technical Details
- Validation checks performed (from `_validate_pipeline`):
  1. Module references exist in catalog (currently skipped - TODO)
  2. Connections reference valid pins
  3. Type compatibility (str→str, etc.)
  4. No duplicate connections
  5. No cycles (DAG requirement via DFS)
  6. All module inputs are connected
- Error parsing uses message pattern matching to determine error codes
- Frontend and backend type conversion handled by existing mappers
- No changes to database schema or repositories

### Before/After Behavior
**Before:**
- Validate button used manual fetch with hardcoded URL
- No proper error handling or type safety
- Direct coupling to backend URL

**After:**
- Validate button uses typed API hook
- Consistent error handling with other API operations
- Proper TypeScript types for request/response
- Reusable validation logic across frontend

### Next Actions
- Test validation endpoint with various pipeline configurations
- Enhance validation to check module catalog references (currently TODO)
- Consider adding validation warnings (non-blocking issues)

### Notes
- Validation is read-only - no database changes
- Module catalog check is skipped (line 161 in service.py) pending catalog implementation
- Error `where` field currently unused but available for future context enhancement

---

## [2025-10-24 20:20] — Fix Module Category Display in Selector Pane

### Spec / Intent
- Fix module categories not being used to display modules in separated sections
- Ensure category field is properly mapped from backend to frontend
- Enable ModuleSelectorPane to group modules by category correctly

### Changes Made

**ModuleTemplate Type** (`client/src/renderer/types/moduleTypes.ts`):
- Added `category: string` field to `ModuleTemplate` interface
- This field was missing, causing all modules to be grouped under "Uncategorized"

**Modules API Hook** (`client/src/renderer/features/modules/hooks/useModulesApi.ts`):
- Updated `convertModuleCatalogToTemplate()` to map `category` field from backend DTO
- Now includes `category: dto.category` in the conversion

### Technical Details
- Backend `ModuleCatalogDTO` always includes `category` field from database
- Frontend was not mapping this field during conversion
- ModuleSelectorPane already had category grouping logic (lines 32-62)
- Fix enables existing UI logic to work correctly

### Before/After
**Before:**
- All modules displayed under single "Uncategorized" section
- Category grouping code existed but had no category values to work with

**After:**
- Modules grouped by their actual categories (Text, Comparison, Logic, etc.)
- Proper section headers displayed for each category
- Modules sorted alphabetically within categories

### Notes
- Mock modules API already referenced category field (no changes needed)
- ModuleSelectorPane component already had correct grouping logic
- This was a data mapping issue, not a UI issue

---

## [2025-10-24 20:15] — Connect Pipeline Builder to Real Modules API

### Spec / Intent
- Replace mock modules API with real API integration in pipeline builder
- Fetch modules from GET /api/modules endpoint
- Enable pipeline builder to use live module catalog from database
- Maintain same interface for seamless transition from mock to real API

### Changes Made

**Modules API Hook** (`client/src/renderer/features/modules/hooks/useModulesApi.ts`):
- Created real API hook that fetches from `/api/modules` endpoint
- Converts backend `ModuleCatalogDTO` to frontend `ModuleTemplate` format
- Supports filtering by kind, category, and search (client-side filtering for category/search)
- Same interface as `useMockModulesApi` for drop-in replacement
- Methods: `getModules()`, `getModuleById()`, `getAvailableModuleIds()`, `getModulesByCategory()`, `getModulesByKind()`
- Returns loading state and error handling

**Modules Hooks Export** (`client/src/renderer/features/modules/hooks/index.ts`):
- Added export for `useModulesApi` alongside `useMockModulesApi`
- Allows gradual migration or environment-based switching

**Pipeline Builder** (`client/src/renderer/pages/dashboard/pipelines/create.tsx`):
- Replaced `useMockModulesApi` with `useModulesApi`
- Now fetches modules from live database via API
- Module selector pane displays real module catalog
- Updated comment to reflect API usage

### Technical Details
- Backend returns `ModulesListResponse` with `items: ModuleCatalogDTO[]`
- Frontend expects `ModuleCatalogResponse` with `modules: ModuleTemplate[]`
- Mapper converts between formats: `name` → `title`, `module_kind` → `kind`
- Backend filtering by `kind` via query param, frontend filters category/search client-side
- Uses `apiClient` from shared API layer for consistent HTTP handling

### Type Mapping
```typescript
// Backend (ModuleCatalogDTO)
{
  id, version, name, description, module_kind, meta,
  config_schema, handler_name, color, category, is_active,
  created_at, updated_at
}

// Frontend (ModuleTemplate)
{
  id, version, title, description, kind,
  color, meta, config_schema
}
```

### Next Actions
- Test module loading in pipeline builder
- Verify all 25 modules appear in module selector
- Test module filtering and search functionality
- Remove mock modules API dependency once fully tested

### Notes
- Mock API still available for offline development/testing
- Module catalog must be synced to database first (via CLI or admin endpoint)
- Pipeline builder now fully integrated with backend module system

---

## [2025-10-24 20:00] — Modules and Admin API Endpoints

### Spec / Intent
- Expose module sync functionality via API endpoint instead of CLI-only
- Create GET endpoint to retrieve module catalog for frontend use
- Enable web-based module synchronization for deployment automation
- Support filtering modules by kind (transform, action, logic, comparator)

### Changes Made

**Modules API Schemas** (`server-new/src/api/schemas/modules.py`):
- `ModuleCatalogDTO` - Module catalog entry with all metadata
- `ModulesListResponse` - Response for GET /api/modules
- `ModuleSyncResult` - Individual module sync result
- `SyncModulesResponse` - Response for POST /api/admin/sync-modules

**Modules API Mappers** (`server-new/src/api/mappers/modules.py`):
- `convert_module_catalog_to_dto()` - Domain → DTO conversion
- `convert_module_catalog_list()` - Batch conversion for list responses
- Handles JSON parsing for meta and config_schema fields

**Modules Router** (`server-new/src/api/routers/modules.py`):
- `GET /api/modules` - List all module catalog entries
  - Query param `kind` - Filter by module kind (optional)
  - Query param `only_active` - Filter active modules (default: true)
  - Returns ModulesListResponse with module DTOs

**Admin Router** (`server-new/src/api/routers/admin.py`):
- `POST /api/admin/sync-modules` - Sync modules from code to database
  - Query param `refresh` - Clear existing modules before sync (default: false)
  - Auto-discovers modules from known packages
  - Validates security for each module
  - Returns detailed sync results with success/error counts
  - Uses same logic as CLI tool but exposed via API

**Router Registration**:
- Updated `server-new/src/api/routers/__init__.py` to export modules and admin routers
- Registered both routers in `server-new/src/app.py` at `/api` prefix
- Updated info endpoint to document new endpoints

### Technical Details
- Uses `ServiceContainer.get_connection_manager()` for dependency injection
- Module repository created per-request with connection manager
- Admin endpoint clears Python module cache and registry before sync
- Supports refresh mode to clear catalog before syncing
- Returns structured response with per-module results

### API Endpoints

**GET /api/modules**
```
Query Parameters:
  - kind: string (optional) - "transform", "action", "logic", "comparator"
  - only_active: boolean (default: true)

Response: ModulesListResponse
  - items: ModuleCatalogDTO[]
  - total: number
```

**POST /api/admin/sync-modules**
```
Query Parameters:
  - refresh: boolean (default: false) - Clear before sync

Response: SyncModulesResponse
  - success: boolean
  - modules_discovered: number
  - modules_synced: number
  - modules_failed: number
  - results: ModuleSyncResult[]
  - message: string
```

### Next Actions
- Test GET /api/modules endpoint
- Test POST /api/admin/sync-modules endpoint
- Update frontend to fetch modules from /api/modules
- Add authentication/authorization to admin endpoints

### Notes
- Admin endpoint exposed without auth (add security before production)
- Module catalog now accessible via REST API
- Frontend can call sync endpoint during deployment/setup
- CLI tool still available for local development

---

## [2025-10-24 19:45] — Module Sync CLI Tool Implementation

### Spec / Intent
- Implement CLI tool to sync module definitions from code to database
- Enable module catalog management for the module/pipeline system
- Support module discovery, listing, and database synchronization
- Follow the pattern from old server but adapt for new architecture

### Changes Made

**CLI Tool** (`server-new/src/cli/sync_modules.py`):
- Created complete CLI tool with three commands:
  - `sync` - Auto-discover modules and sync to database (with optional `--refresh` flag)
  - `list` - List all discovered modules without touching database
  - `clear` - Clear all modules from database catalog
- Auto-discovers modules from package paths: transform, action, logic, comparator
- Validates module handler paths for security
- Uses module registry to convert modules to catalog format
- Uses `ModuleCatalogRepository` for database operations with proper UoW support
- Added `__init__.py` for CLI package

**Registry Fixes** (`server-new/src/shared/utils/registry.py`):
- Updated `to_catalog_format()` to keep `meta` as `ModuleMeta` object
- Let repository layer handle conversion to JSON (separation of concerns)
- Registry now returns catalog entries ready for `ModuleCatalogCreate` dataclass

### Technical Details
- Uses connection_manager.session() context manager (new server pattern)
- Module repository initialized with `connection_manager=connection_manager` kwarg
- Successfully synced 25 modules to database on first run
- Package paths use "features.modules.*" (no "src." prefix)
- Security validation prevents loading modules from unauthorized packages
- One module (llm_parser) skipped due to missing import dependency

### Usage
```bash
# List modules without database interaction
python src/cli/sync_modules.py list

# Sync modules to database
python src/cli/sync_modules.py sync

# Clear and re-sync modules
python src/cli/sync_modules.py sync --refresh

# Clear all modules
python src/cli/sync_modules.py clear
```

### Next Actions
- Set up modules GET endpoint in API router
- Connect frontend module selector to real API
- Fix llm_parser import issue if needed
- Document CLI tool usage in README

### Notes
- All 25 modules successfully synced to database
- CLI tool ready for use during development and deployment
- Module catalog now populated and ready for frontend consumption

---

## [2025-10-24 19:15] — Connect Pipeline Save Button to Backend API

### Spec / Intent
- Connect the "Save Pipeline" button in pipeline builder to the new POST /api/pipelines endpoint
- Replace manual fetch call with proper API hook usage
- Enable testing of full pipeline creation flow

### Changes Made

**Pipeline Create Page** (`client/src/renderer/pages/dashboard/pipelines/create.tsx`):
- Added `usePipelinesApi` hook import and initialization
- Updated `handleSave()` function to use `createPipeline()` from API hook instead of manual fetch
- Replaced hardcoded endpoint URL (`http://localhost:8090/api/pipelines/upload`) with proper API client
- Added loading state to Save Pipeline button (shows "Saving..." when active)
- Button now disabled during save operation to prevent duplicate submissions
- Improved success message to show both pipeline ID and compiled plan ID

### Technical Details
- Pipeline data serialization remains the same (using `serializePipelineData`)
- Error handling improved through API hook's built-in error management
- Uses proper API base URL from `API_CONFIG` instead of hardcoded URL
- Loading state (`isSaving`) prevents user interaction during save

### Next Actions
- Test pipeline creation flow end-to-end
- Verify compilation happens on backend
- Check that created pipelines appear in pipeline list
- Test error handling for invalid pipelines

### Notes
- Old fetch-based implementation removed in favor of consistent API hook usage
- Pipeline validation endpoint still uses manual fetch (can be migrated later)
- Backend compilation happens automatically during POST /api/pipelines

---

## [2025-10-24 19:00] — Pipeline Backend Router Implementation

### Spec / Intent
- Implement complete backend API router for pipeline definitions
- Create three-layer architecture: schemas → mappers → routers
- Support GET (list/detail) and POST (create) operations
- Register router in main FastAPI application

### Changes Made

**Pipeline API Schemas** (`server-new/src/api/schemas/pipelines.py`):
- Created comprehensive Pydantic models for pipeline API contract
- Key models: `NodeDTO`, `EntryPointDTO`, `ModuleInstanceDTO`, `NodeConnectionDTO`
- Separated logical structure (`PipelineStateDTO`) from visual layout (`VisualStateDTO`)
- Request/response models: `PipelinesListResponse`, `PipelineDetailDTO`, `CreatePipelineRequest`
- All models match frontend TypeScript types and backend API specification

**Pipeline API Mappers** (`server-new/src/api/mappers/pipelines.py`):
- Implemented bidirectional conversions between domain types and API DTOs
- Domain → API (response): `convert_pipeline_summary_list()`, `convert_pipeline_detail()`
- API → Domain (request): `convert_create_request()`, `convert_dto_to_pipeline_state()`
- Handles all nested structures (nodes, modules, connections, visual positions)

**Pipeline Router** (`server-new/src/api/routers/pipelines.py`):
- `GET /api/pipelines` - List pipelines with pagination (limit, offset) and sorting (sort_by, sort_order)
- `GET /api/pipelines/{id}` - Get full pipeline detail including pipeline_state and visual_state
- `POST /api/pipelines` - Create new pipeline (validates, compiles, persists)
- Uses dependency injection for `PipelineService` via `ServiceContainer`
- Marked as dev/testing endpoints (will be removed when standalone pipeline page is deprecated)

**Router Registration**:
- Updated `server-new/src/api/routers/__init__.py` to export `pipelines_router`
- Updated `server-new/src/app.py` to import and register pipelines router at `/api` prefix
- Updated info endpoint to include `/api/pipelines` in endpoints list

### Technical Details
- Pipeline service already existed with full functionality (validation, compilation, persistence)
- Compilation includes: structural validation, type checking, cycle detection, dead branch pruning, topological sorting
- Checksum-based deduplication: multiple pipeline definitions can share same compiled plan
- Pagination limit capped at 200 items per request
- All datetime values returned as ISO 8601 strings for API convenience

### Next Actions
- Test pipeline endpoints with frontend
- Verify list, detail, and create operations work correctly
- Implement remaining endpoints: PUT /api/pipelines/{id}, DELETE /api/pipelines/{id}
- Test full round-trip: create pipeline in frontend, compile, view details

### Notes
- Backend now fully supports GET (list/detail) and POST (create) for pipelines
- Frontend already connected to these endpoints via `usePipelinesApi` hook
- Following same three-layer pattern as email-configs: schemas → mappers → routers

---

## [2025-10-24 18:30] — Pipeline List API Integration

### Spec / Intent
- Connect frontend pipeline list to real backend API
- Replace mock data with actual API calls to `/api/pipelines`
- First step in migrating pipeline functionality from mocks to real backend

### Changes Made

**New API Hook** (`client/src/renderer/features/pipelines/hooks/usePipelinesApi.ts`):
- Created real API hook following same pattern as `useEmailConfigsApi`
- Implements all pipeline CRUD operations:
  - `getPipelines()` - GET /api/pipelines (with pagination/sorting)
  - `getPipeline(id)` - GET /api/pipelines/{id}
  - `createPipeline(data)` - POST /api/pipelines
  - `updatePipeline(id, data)` - PUT /api/pipelines/{id}
  - `deletePipeline(id)` - DELETE /api/pipelines/{id}
- Includes loading and error state management
- Uses existing `apiClient` and `API_CONFIG` from shared API layer

**Updated Pipelines Page** (`client/src/renderer/pages/dashboard/pipelines/index.tsx`):
- Replaced `useMockPipelinesApi` with `usePipelinesApi`
- Now fetches real pipeline data from backend
- Maintains same UI/UX - only data source changed

**Updated Hooks Export** (`client/src/renderer/features/pipelines/hooks/index.ts`):
- Added `usePipelinesApi` to centralized exports

### Technical Details
- Uses `PipelinesListResponse` type matching backend API spec
- API endpoint: `API_CONFIG.ENDPOINTS.PIPELINES` (`/api/pipelines`)
- Frontend types already match backend API structure from prior planning
- Mock API hook (`useMockPipelinesApi`) still exists for reference but is no longer used

### Next Actions
- Test pipeline list loading with real backend
- Connect pipeline detail view to API (GET /api/pipelines/{id})
- Connect pipeline create/edit operations to API
- Eventually remove mock hooks once all functionality is connected

### Notes
- This is first of several pipeline endpoints to be connected
- Backend pipeline router exists but needs implementation
- Following incremental replacement strategy: list → detail → create → edit → delete

---

## [2025-10-24 18:00] — Timezone-Aware Datetime Fix

### Spec / Intent
- Fix timezone-naive/aware datetime comparison errors throughout the application
- Convert all database datetime columns to timezone-aware storage
- Ensure consistency between Python datetime objects and database values

### Problem
Application was throwing `TypeError: can't subtract offset-naive and offset-aware datetimes` when comparing:
- Timezone-aware datetimes from Python code: `datetime.now(timezone.utc)`
- Timezone-naive datetimes from database (retrieved from `DATETIME2` columns)

### Solution
- Updated all SQLAlchemy model datetime columns to use `DateTime(timezone=True)`
- SQLAlchemy automatically maps this to SQL Server `DATETIMEOFFSET` type
- All datetime values retrieved from database are now timezone-aware Python objects
- All existing values interpreted as UTC (consistent with `func.getutcdate()` server defaults)

### Changes Made

**Database Models** (`server-new/src/shared/database/models.py`):
- Removed `DATETIME2` import and all references
- Updated ALL datetime column definitions across all tables:
  - `email_configs`: activated_at, last_check_time, last_error_at, created_at, updated_at
  - `emails`: received_date, processed_at, created_at, updated_at
  - `pdf_files`: created_at, updated_at
  - `pdf_templates`: created_at, updated_at
  - `pdf_template_versions`: last_used_at, created_at, updated_at
  - `module_catalog`: created_at, updated_at
  - `pipeline_compiled_plans`: compiled_at, created_at, updated_at
  - `pipeline_definitions`: created_at, updated_at
  - `pipeline_definition_steps`: created_at, updated_at
  - `eto_runs`: started_at, completed_at, created_at, updated_at
  - `eto_run_template_matchings`: started_at, completed_at, created_at, updated_at
  - `eto_run_extractions`: started_at, completed_at, created_at, updated_at
  - `eto_run_pipeline_executions`: started_at, completed_at, created_at, updated_at
  - `eto_run_pipeline_execution_steps`: created_at, updated_at

**Example Change**:
```python
# Before
from sqlalchemy.dialects.mssql import DATETIME2
activated_at: Mapped[Optional[datetime]] = mapped_column(DATETIME2)

# After
activated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
```

### Database Impact
**IMPORTANT**: Database schema must be updated - all `DATETIME2` columns must become `DATETIMEOFFSET`
- Option 1: Drop and recreate database (cleanest)
- Option 2: Manually alter columns if preserving data

### Technical Details
- `DateTime(timezone=True)` → SQL Server `DATETIMEOFFSET` type
- `DATETIMEOFFSET` stores timezone offset with the value
- SQLAlchemy automatically converts to/from Python timezone-aware datetime objects
- All UTC datetimes stored with `+00:00` offset
- Server defaults use `SYSUTCDATETIME()` (returns `DATETIMEOFFSET` in UTC)

### Next Actions
- Drop and recreate database to apply schema changes
- Test email ingestion with new timezone-aware datetimes
- Verify no more naive/aware datetime comparison errors

### Notes
- All existing data assumed to be UTC (consistent with previous `func.getutcdate()` usage)
- This is a breaking schema change - database must be updated

---
