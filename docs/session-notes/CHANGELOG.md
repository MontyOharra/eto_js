# CHANGELOG

## [2025-12-06] — Pending Orders System Design & Frontend Scaffolding

### Spec / Intent
- Design a system for compiling order data from multiple ETO runs
- Handle the case where order information arrives across multiple forms/PDFs
- Ensure collision-free order number generation with existing VBA/Access system
- Build frontend infrastructure for order management

### Changes Made

#### Design Work:
- Created comprehensive design document: `docs/designs/pending-orders-system.md`
- Analyzed VBA order creation code (`NextOrderNo`, `PosttoLON`, `RemoveOIW`)
- Extracted Access database schemas for LON, OIW, and HAWB Values tables
- Designed collision-free order reservation using OIW unique constraint

#### Frontend Structure Created:
- `client/src/renderer/features/order-management/` - New feature module
  - `types.ts` - Domain types (PendingOrder, PendingUpdate, OrderHistory, etc.)
  - `api/hooks.ts` - TanStack Query hooks for all endpoints
  - `api/types.ts` - API request/response types
  - Components: PendingOrdersTable, PendingOrdersHeader, PendingOrderDetail,
    PendingUpdatesTable, PendingUpdatesHeader, OrderHistoryTimeline,
    OrderStatusBadge, FieldStatusBadge

- `client/src/renderer/pages/dashboard/orders/index.tsx` - Orders page with:
  - Toggle between Pending Orders and Pending Updates views
  - Detail views for order inspection and history timeline

- Modified `client/src/renderer/pages/dashboard/route.tsx`:
  - Added "Orders" tab between ETO and Templates
  - Shortened tab names for space (Pipelines, Configs)

### Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Order identifier | HAWB | Unique per shipment |
| Auto-create trigger | All required fields present | Simple, predictable |
| Update handling | Queue for user approval | Prevents outdated overwrites |
| Pre-creation conflicts | Last write wins + history | Don't block workflow |
| Output approach | Channels per field | Avoids module explosion |

### Architecture Overview

```
PDF → ETO Run → Pipeline → Output Channels
                                ↓
                    ┌───────────────────────┐
                    │ Order exists in HTC?  │
                    └───────────┬───────────┘
                         YES    │    NO
                          ↓     │     ↓
                    Queue for   │  Merge into
                    review      │  pending order
                                │     ↓
                                │  Complete?
                                │  YES → Create in HTC
                                │  NO  → Wait for more data
```

### Pending Work
- [ ] Add mock data to visualize components
- [ ] Rethink design (don't just copy ETO patterns)
- [ ] Backend database models
- [ ] API endpoints implementation
- [ ] Output channel modules
- [ ] Output execution service refactor

### Session Continuity
- Created: `docs/session-notes/continuity-2025-12-06-pending-orders.md`
- Contains guiding questions, next steps, and technical context

### Notes
- User noted that blindly copying ETO table design was wrong approach
- Need to think about what makes sense specifically for order management
- Mock data essential before further design decisions
- Backend implementation waiting on frontend design validation

---

## [2025-12-03] — Frontend Fixes & Thread-Safe Output Execution

### Spec / Intent
- Fix scrolling issues on ETO run detail page
- Fix status display in ETO list view (showing "-" instead of sub-run counts)
- Add thread safety to Access database operations for concurrent worker threads

### Changes Made

#### Frontend Fixes:

**Scrolling Fix:**
- `client/src/renderer/features/eto/components/EtoRunDetailView/EtoRunDetailViewWrapper.tsx`
  - Added `h-full overflow-auto` to container div
- `client/src/renderer/pages/dashboard/eto/$runId.tsx`
  - Added `overflow-auto` to container div

**Status Display Fix:**
- `client/src/renderer/features/eto/types.ts`
  - Changed `EtoSubRunsSummary` from multiple count fields to `status_counts: Record<string, number>`
- `client/src/renderer/features/eto/components/EtoRunsTable/EtoRunsTable.tsx`
  - Updated `StatusCell` to read from `summary.status_counts.success`, `.failure`, `.needs_template`
  - Updated `ActionsCell` to use new `statusCounts` structure

#### Backend Fixes:

**API Simplification:**
- `server/src/api/schemas/eto_runs.py`
  - Simplified `EtoSubRunsSummary` to single `status_counts: Dict[str, int]` field
- `server/src/api/mappers/eto_runs.py`
  - Updated mapper to populate `status_counts` dict

**Thread Safety:**
- `server/src/features/pipeline_results/helpers/orders.py`
  - Added `import threading`
  - Added class-level `_order_number_lock = threading.Lock()`
  - Wrapped `generate_next_order_number()` body with `with self._order_number_lock:`

### Key Technical Details

#### Thread Safety Issue:
- **Error:** `pyodbc.Error: ('HY010', '[HY010] [Microsoft][ODBC Driver Manager] Function sequence error')`
- **Cause:** pyodbc has threadsafety=1 (threads cannot share connections)
- **Solution:** Class-level lock serializes all order number generation across threads
- **Trade-off:** Slight reduction in parallelism, but order numbers must be unique anyway

#### Status Display Issue:
- **Problem:** Frontend tried to calculate page counts from `sub_runs` array (which was null)
- **Fallback logic bug:** Only worked when `failure_count === 0`
- **Solution:** API now returns simple `status_counts` dict, frontend reads directly

### Database Impact
- No schema changes
- Access database operations now serialized via threading lock

### Next Actions
- Implement real order output module (beyond test module)
- Add output execution details to sub-run detail view
- Monitor lock contention under load

---

## [2025-11-28] — PDF Source Tracking Refactor & List View State Preservation

### Spec / Intent
- Move PDF source tracking from `pdf_files` table to `eto_runs` table
- Enable multiple ETO runs for the same PDF with different sources
- Make PDFs pure storage entities (hash-based deduplication)
- Fix list view state preservation when navigating to/from detail page
- Fix "Received" column showing hyphens for manual uploads

### Changes Made

#### Files Created:
- `client/src/renderer/features/eto/components/EtoRunDetailView/EtoRunDetailViewWrapper.tsx` - Extracted detail view logic to enable state preservation

#### Files Modified:

**Database Layer:**
- `server/src/shared/database/models.py`:
  - Added `ETO_SOURCE_TYPE` enum ('email', 'manual')
  - Added `source_type` and `source_email_id` to `EtoRunModel`
  - Added `source_email` relationship to `EtoRunModel`
  - Removed `email_id` field from `PdfFileModel`
  - Removed `email` relationship from `PdfFileModel`
  - Removed `pdf_files` relationship from `EmailModel`

**Domain Types:**
- `server/src/shared/types/eto_runs.py`:
  - Added `source_type` and `source_email_id` to `EtoRunCreate`, `EtoRun`, `EtoRunListView`, `EtoRunDetailView`
- `server/src/shared/types/pdf_files.py`:
  - Removed `email_id` from `PdfFile` and `PdfFileCreate` dataclasses
  - Updated docstrings to note source tracking moved to ETO runs

**Repositories:**
- `server/src/shared/database/repositories/eto_run.py`:
  - Updated `_model_to_domain` to map new source fields
  - Updated `create` to accept `source_type` and `source_email_id`
  - Changed JOIN in `get_all_with_relations` from `PdfFileModel.email_id` to `EtoRunModel.source_email_id`
  - Updated row mapping to include source fields
  - Same changes for `get_detail_with_stages`
- `server/src/shared/database/repositories/pdf_file.py`:
  - Removed `email_id` from `_model_to_dataclass` and `create` methods

**Service Layer:**
- `server/src/features/pdf_files/service.py`:
  - Removed `email_id` parameter from `store_pdf` method
  - Updated docstring to note source tracking moved to ETO runs level

**API Layer:**
- `server/src/api/schemas/pdf_files.py`:
  - Removed `email_id` field from `PdfFile` Pydantic model
  - Updated docstring to note source tracking moved to eto_runs
- `server/src/api/mappers/pdf_files.py`:
  - Removed `email_id` mapping from `pdf_file_to_api` function
  - Updated docstring

**Frontend:**
- `client/src/renderer/pages/dashboard/eto/index.tsx`:
  - Added `selectedRunId` state for list/detail toggle
  - Removed `useNavigate` hook
  - Implemented conditional rendering (detail view vs list view)
  - Fixed import paths for templates
- `client/src/renderer/features/eto/components/EtoRunsTable/EtoRunsTable.tsx`:
  - Fixed `getSourceDate()` to use `source.received_at` instead of `source.received_date`
  - Return `source.created_at` for manual uploads instead of `null`
- `client/src/renderer/features/eto/components/EtoRunRow/EtoRunRow.tsx`:
  - Same `getSourceDate()` fix as EtoRunsTable
- `client/src/renderer/features/eto/components/EtoPageHeader/EtoPageHeader.tsx`:
  - Cleaned up sort dropdown options
  - Added TODO comments for PDF filename and received_at sorting

### Key Technical Changes

#### PDF Source Tracking Architecture:
**Before:**
- `pdf_files.email_id` tracked source
- Hash deduplication returned existing record with old `email_id`
- New email ingestion lost source information on duplicate PDFs

**After:**
- PDFs are pure storage entities (no `email_id`)
- Each `eto_run` has its own `source_type` ('email'|'manual') and `source_email_id`
- Hash deduplication returns existing PDF, but new ETO run gets correct source
- Same PDF can have multiple ETO runs with different sources

#### List View State Preservation:
**Approach:** Toggle visibility instead of routing
- Created `EtoRunDetailViewWrapper` that accepts `runId` prop and `onBack` callback
- List page maintains `selectedRunId` state
- Conditional rendering: show detail when `selectedRunId` is set, otherwise show list
- List component never unmounts, preserving filters, scroll position, and pagination

### Database Schema Impact

**`eto_runs` table - Added:**
- `source_type` VARCHAR (enum: 'email', 'manual') - NOT NULL
- `source_email_id` INTEGER - NULLABLE, FK to emails.id
- `source_email` relationship (ORM)

**`pdf_files` table - Removed:**
- `email_id` INTEGER field
- `email` relationship (ORM)

**`emails` table - Removed:**
- `pdf_files` relationship (ORM)

### Pending Work

**Next Steps to Complete Refactor:**
1. Update email ingestion service to pass `source_type='email'` and `source_email_id` when creating ETO runs
2. Update API endpoint for manual uploads to pass `source_type='manual'` and `source_email_id=None`
3. Update ETO runs API mapper to use `source_type` instead of checking `email_id` for discriminated union
4. Test the complete flow:
   - Manual PDF upload creates run with correct source
   - Email PDF (new) creates run with email source
   - Email PDF (duplicate hash) creates NEW run with correct email source
5. Add PDF filename sorting (backend + frontend)
6. Test list view state preservation with filters and pagination

### Migration Notes
- No data migration required (dev/test environment)
- Breaking change: Existing code that creates ETO runs needs updating
- API responses for PDF files no longer include `email_id`

### Next Actions
- Update `features/email_ingestion/service.py` to pass source fields when creating ETO runs
- Update `api/routers/eto_runs.py` manual upload endpoint to pass source fields
- Update `api/mappers/eto_runs.py` to use new source fields
- Test complete ingestion flow (manual + email, duplicate PDFs)
- Implement PDF filename sorting
- Test list view state preservation

### Notes
- This refactor enables the same PDF to be processed multiple times with different sources
- PDFs are now truly deduplicated storage entities
- Source tracking is now correctly scoped to each ETO run
- List view state preservation provides better UX for reviewing runs

---

## [2025-11-24] — Multi-Template Sub-Run System Refactoring

### Spec / Intent
- Migrate ETO runs from single-template to multi-template sub-run architecture
- Fix type errors throughout the codebase (Pylance/typing issues)
- Clean up deprecated code and unused repositories
- Implement custom logging with typed `monitor()` and `trace()` methods

### Changes Made

#### New Files Created:
- `server/src/shared/logging.py` - Custom MonitorLogger class with typed `trace()` and `monitor()` methods
- `server/src/shared/database/repositories/eto_sub_run_extraction.py` - Repository for sub-run extractions
- `server/src/shared/database/repositories/eto_sub_run_pipeline_execution.py` - Repository for sub-run pipeline executions
- `server/src/shared/database/repositories/eto_sub_run_pipeline_execution_step.py` - Repository for sub-run pipeline execution steps
- `server/src/shared/types/eto_sub_run_extractions.py` - Types for sub-run extractions
- `server/src/shared/types/eto_sub_run_pipeline_executions.py` - Types for sub-run pipeline executions
- `server/src/shared/types/eto_sub_run_pipeline_execution_steps.py` - Types for sub-run pipeline execution steps

#### Files Modified:
- `server/src/app.py` - Updated to use `setup_logger_class()` from shared.logging
- `server/src/features/eto_runs/service.py` - Major refactoring:
  - Updated to use custom logger with typed `monitor()` method
  - Rewrote `_process_sub_run_extraction` to use new sub-run tables
  - Rewrote `_process_sub_run_pipeline` for new pipeline execution flow
  - Fixed `_mark_sub_run_failure` (removed traceback reference, added error_type inference)
  - Removed ~486 lines of deprecated old processing methods
  - Removed duplicate worker lifecycle methods
- `server/src/features/eto_runs/utils/eto_worker.py` - Changed `EtoRun` to `EtoSubRun` type
- `server/src/features/pipeline_execution/service.py` - Removed unused old repositories
- `server/src/features/pipelines/utils/validation.py` - Added assertion for `validate_config` return type
- `server/src/api/routers/pipelines.py` - Added type ignore for steps parameter
- `server/src/features/email_ingestion/integrations/imap_integration.py` - Fixed type narrowing issues, made `mark_as_read` a no-op

#### Files Deleted (Old System):
- `server/src/shared/database/repositories/eto_run_extraction.py`
- `server/src/shared/database/repositories/eto_run_pipeline_execution.py`
- `server/src/shared/database/repositories/eto_run_pipeline_execution_step.py`
- `server/src/shared/database/repositories/eto_run_template_matching.py`
- `server/src/shared/types/eto_run_extractions.py`
- `server/src/shared/types/eto_run_pipeline_executions.py`
- `server/src/shared/types/eto_run_pipeline_execution_steps.py`
- `server/src/shared/types/eto_run_template_matchings.py`
- `server/src/shared/database/models-new.py`

### Key Technical Changes

#### Custom Logging System:
```python
# server/src/shared/logging.py
class MonitorLogger(logging.Logger):
    def trace(self, msg: str, *args, **kwargs) -> None:  # Level 5
    def monitor(self, msg: str, *args, **kwargs) -> None:  # Level 7
```
- TRACE level (5) - Very detailed tracing below DEBUG
- MONITOR level (7) - Periodic status messages between TRACE and DEBUG
- Eliminates need for `# type: ignore` on logger.monitor() calls

#### Sub-Run Processing Flow:
1. `process_sub_run(sub_run_id)` - Main entry point
2. `_process_sub_run_extraction()` - Extract data using template fields
3. `_process_sub_run_pipeline()` - Execute pipeline with extracted data
4. `_mark_sub_run_success/failure()` - Update sub-run status
5. `_update_parent_run_status()` - Aggregate sub-run statuses to parent

#### Type Fixes:
- `validate_config` return type: Added `assert isinstance(validation_errors, list)`
- IMAP `msg_id_str` type narrowing: Explicit if/else with `str()` conversion
- `email_body` assertion: `assert isinstance(email_body, bytes)`
- Pipeline steps: Added `# type: ignore[arg-type]` for `PipelineDefinitionStepCreate`

### Database Schema Changes
- Old tables (deprecated): `eto_run_template_matchings`, `eto_run_extractions`, `eto_run_pipeline_executions`, `eto_run_pipeline_execution_steps`
- New tables: `eto_sub_runs`, `eto_sub_run_extractions`, `eto_sub_run_pipeline_executions`, `eto_sub_run_pipeline_execution_steps`

### Pending Work
- `reprocess_runs()` and `skip_runs()` methods need updating for sub-run system
- `delete_runs()` method needs updating for sub-run system
- Frontend components in test feature need completion

### Next Actions
- Update bulk operations (reprocess, skip, delete) for sub-run architecture
- Complete frontend test components for ETO run display
- Add tests for new sub-run processing flow

---

## [2025-11-18] — Page-Segment Template Matching Design & Test Dashboard Prototype

### Spec / Intent
- Design new page-segment-based template matching system to handle multi-document PDFs
- Create comprehensive UI/UX design for displaying matched and unmatched page segments
- Prototype new unified ETO dashboard with table-based layout
- Document get_order_number module implementation

### Changes Made
- Files Created:
  - `docs/misc/page-segment-matching-design.md` - Complete design spec for segment-based matching (449 lines)
  - `docs/misc/create-order-module-spec.md` - Order creation module specification (392 lines)
  - `server/src/pipeline_modules/misc/get_order_number.py` - Module to check if order exists for HAWB
  - `client/src/renderer/features/test/` - New feature directory structure for dashboard prototyping
  - `client/src/renderer/pages/dashboard/test/index.tsx` - Test dashboard page with mock data

- Files Modified:
  - `client/src/renderer/pages/dashboard/route.tsx` - Added "Test" tab to navigation

### Page-Segment Matching System Design

**Problem Statement**:
- Current system: 1 PDF = 1 template match (fails for multi-document PDFs)
- Need: Match different page ranges to different templates within same PDF

**Solution Architecture**:
1. **New Database Table**: `eto_run_page_segments`
   - Represents contiguous page ranges (start_page, end_page)
   - Status: matched, unmatched, manually_assigned, ignored
   - Links to template_version_id and match_confidence

2. **Sliding Window Algorithm**:
   - Try all possible page ranges against all templates
   - Resolve overlaps by prioritizing confidence, coverage, position
   - Identify unmatched gaps between matched segments

3. **Updated Relationships**:
   - Extractions and pipeline executions link to page_segment_id (not eto_run_id)
   - Each segment processes independently through extraction/transformation

**UI/UX Design** (Option 2: Dedicated Detail Page):
- Main dashboard: Unified table showing all ETO runs
- Row columns: PDF filename, segments status, overall status, source, timestamps
- Click row → Full-page detail view with segment cards
- Each segment card shows: page range, template match, extraction results, actions
- Segment-level actions: Reprocess, Assign Template, Ignore
- Global actions: Rematch Entire PDF, Reprocess All Unmatched

**Key Components Designed**:
- `PageSegmentTimeline` - Visual timeline of page segments with color coding
- `UnmatchedSegmentActionPanel` - User actions for unmatched pages
- `SegmentExecutionList` - Per-segment processing status
- `SegmentStatusSummary` - At-a-glance match status (e.g., "10/15 pages matched")

**Selective Reprocessing**:
- Critical workflow: Only reprocess failed/unmatched segments
- Preserve successful segment results
- Support manual template assignment and segment ignore

### Test Dashboard Prototype

**Structure**:
- Created feature directory: `client/src/renderer/features/test/` with api/, components/, hooks/ subdirectories
- Created page route: `/dashboard/test/`
- Added navigation tab in dashboard layout

**Current Implementation**:
- Mock data: 5 items with name field (test1-test5)
- Table layout: Header row with "Name" column
- Data rows: Line-separated, no background, hover effect
- Clean, modern dashboard aesthetic

**Suggested Columns for Production** (from ETO run analysis):
1. **Core**: PDF Filename, Run ID
2. **Status**: Overall Status, Processing Step, **Segments Status** (NEW: "3/5 matched, 2 unmatched")
3. **Source**: Email/Manual, Received Date
4. **Templates**: Matched Templates (NEW: Single or "Multiple"), Match Confidence (NEW)
5. **Timing**: Started At, Completed At, Duration
6. **Metadata**: File Size, Page Count
7. **Results**: Fields Extracted (NEW: across all segments), Errors

### Module Development

**get_order_number Module**:
- Input: HAWB (str)
- Outputs: order_exists (bool), order_number (int)
- Searches `HTC300_G040_T010A Open Orders` table
- Config: database connection, on_multiple_orders (first/last/error)

**create_order Module** (specification only):
- 16 fixed inputs (customer, hawb, mawb, addresses, dates, times, notes, pieces, weight)
- 1 output (order_number)
- Internal operations: customer lookup, address lookup, order type determination, validation
- Database inserts: Orders, Dimensions, History, HAWB Values tables
- Complex order type logic (10 types based on pickup/delivery flags and ACI ranges)

### Architectural Decisions

**Why Option 2 (Dedicated Detail Page)**:
- Selective reprocessing: Each segment needs independent actions
- Segment cards with per-segment "Reprocess" buttons
- "Reprocess All Unmatched" vs "Rematch Entire PDF" distinction
- Better screen real estate for complex multi-segment PDFs
- Clear visual indication of segment status

**Migration Strategy**:
1. Create eto_run_page_segments table (backward compatible)
2. Migrate existing runs to single-segment model
3. Implement sliding window matching algorithm
4. Update frontend to show segment-based view
5. Cleanup: Drop eto_run_template_matchings table

### Next Actions
- Implement page-segment database schema
- Build sliding window matching algorithm
- Create segment detail page UI components
- Add more columns to test dashboard prototype
- Wire up test dashboard to real ETO runs data

### Notes
- Page-segment design solves multi-document PDF problem comprehensively
- Selective reprocessing is critical workflow requirement
- Test dashboard provides clean prototyping environment
- Design focuses on user clarity for partial matches (key UX challenge)
- Column suggestions based on current ETO run table analysis

---

## [2025-11-11] — VBA to Modern System Comparison Analysis

### Spec / Intent
- Analyze current TypeScript/Python codebase to understand ingestion and template matching functionality
- Compare with legacy VBA/MS Access system documented in VBA analysis
- Identify discrepancies and missing functionalities between systems
- Create comprehensive comparison document for migration planning

### Changes Made
- Files Created:
  - `docs/version_comparison/ingestion-and-templates.md` - Comprehensive VBA vs Modern system comparison (1029 lines)

### Analysis Completed

**Current System Analysis** (via Explore agent):
- Template system architecture (versioning, signature objects, extraction fields)
- Document ingestion/processing (pdfplumber, PDF object extraction)
- Template matching algorithm (fuzzy matching, ranked results, bbox-based)
- Data extraction (bbox-based, multiple strategies)
- Pipeline system (Dask execution, visual builder, module catalog)
- Complete ETO workflow (matching → extraction → pipeline execution)
- Database schema (PostgreSQL with JSONB)
- Frontend architecture (React, TypeScript, React Flow)
- Backend architecture (FastAPI, Pydantic, async workers)

**VBA System Analysis** (from existing documentation):
- HTC350C_1of2_Translation (1,653 lines) - main orchestrator
- Character-by-character pattern matching (14 hard-coded formats)
- Line/char position-based data extraction
- 10+ format-specific parser functions
- File system-based workflow
- Access forms for UI
- WhosLoggedIn session locking
- 31-day retention policy with file deletion

### Key Findings

#### ✅ Modern System Advantages:
1. **Version Control** - Immutable template versions, comparison, rollback
2. **Visual Pipeline Builder** - Drag-and-drop, live simulation, reusable modules
3. **Fuzzy Matching** - Confidence scores, OCR tolerance, ranked results
4. **Scalability** - Parallel workers, no hard limits (VBA had 1000 PDF max)
5. **Modern Architecture** - Service-based, API-first, Docker containers
6. **Multi-user Web UI** - Accessible anywhere, real-time collaboration
7. **Type Safety** - Pydantic/TypeScript validation throughout

#### ⚠️ Missing from Modern System:
1. **Pre-built Document Handlers** - VBA has 14 format parsers (SOS Routing, BOL variants, Alert, MAWB, etc.)
   - Modern system has generic template system but zero pre-built templates
   - **Action Required**: Create templates for each VBA format in template builder

2. **Multi-Delivery Alert Expansion** - VBA `prep_AllParsedPDFs()` expands Alerts with multiple delivery receipts
   - **Action Required**: Implement as custom pipeline module

3. **31-Day Retention Policy** - VBA auto-deletes old logs and files
   - **Action Required**: Add scheduled job for retention/archival

4. **Single-Process Enforcement** - VBA WhosLoggedIn table prevents concurrent runs
   - Modern system supports parallel processing (may or may not need single-process constraint)

#### Architectural Comparison:

| Feature | VBA | Modern | Winner |
|---------|-----|--------|--------|
| Pattern Matching | Exact sequential | Fuzzy bbox | Modern |
| Data Extraction | Line/char positions | Bbox coordinates | Modern |
| Configuration | Hard-coded in VBA | Database + UI | Modern |
| Scalability | Single-thread, max 1000 | Parallel, unlimited | Modern |
| Extensibility | Requires coding | Add modules | Modern |
| Format Support | 14 pre-built | 0 pre-built | VBA (temporary) |

### Recommendations

**Immediate Actions**:
1. Create modern templates for 14 VBA document formats using template builder
2. Implement multi-delivery alert expansion as pipeline module
3. Add retention policy scheduled job
4. Document migration path for each VBA format

**Migration Strategy**:
- Side-by-side testing (run both systems in parallel)
- Gradual rollout (migrate one format at a time)
- Comprehensive test suite with sample production PDFs
- One-time template creation effort, then modern system is superior

### Next Actions
- Begin creating templates for VBA formats (start with most common: SOS Routing, SOS BOL, SOS Alert)
- Implement custom pipeline modules for VBA-specific logic (alert expansion)
- Add retention/archival scheduled jobs
- Build test suite with sample PDFs from each format

### Notes
- Migration is feasible - modern system has equivalent or superior capabilities
- Key risk: Ensuring 14 VBA formats are correctly translated to templates
- Comprehensive comparison document ready for stakeholder review
- Modern system architecture is significantly more maintainable and scalable

---

## [2025-11-10 19:30] — Template Version Editing & VBA Migration Setup
### Spec / Intent
- Fix config editability in view mode for pipeline viewer
- Fix connection validation for initialized modules in template builder
- Preserve current step when switching template versions
- Set up VBA migration infrastructure and documentation

### Changes Made
- Files Modified:
  - `client/src/renderer/features/pipelines/components/PipelineGraph/ConfigSection.tsx`
  - `client/src/renderer/features/pipelines/components/PipelineGraph/ModuleConfig.tsx`
  - `client/src/renderer/features/pipelines/components/PipelineGraph/PipelineGraph.tsx`
  - `client/src/renderer/features/templates/components/TemplateDetail/TemplateDetailModal.tsx`

- Files Created:
  - `context/docs/CLAUDE_CODE_SLASH_COMMANDS.md` - Comprehensive guide to slash commands for VBA analysis
  - `vba-code/HTC_350C_Sub_1_of_2_translation.vba` - Original VBA code for migration
  - `vba-code/HTC_350C_Sub_2_of_2_createorders.vba` - Original VBA code for migration

### Summary of Fixes

#### 1. Config Editability in View Mode (commit: 6259021)
**Problem**: Config inputs were editable in view mode because ModuleConfig always passed a wrapper function to ConfigSection.
**Solution**: Made onConfigChange optional in ConfigSectionProps, conditionally pass undefined in view mode.

#### 2. Connection Validation for Initialized Modules (commit: 56a0703)
**Problem**: Connection validation used raw pipelineState lacking enriched metadata (allowed_types, direction, label, type_var), causing validation failures.
**Solution**: Updated all validation and type system operations to use enrichedPipelineState:
- `isValidConnection`: Uses enriched state for correct allowed_types
- `onConnect`: Validates with enriched state, persists to raw state
- `handleUpdateNode`: Calculates propagation with enriched state
- `effectiveTypesCache`: Computed from enriched state
Pattern: Read from enriched (for metadata), write to raw (for persistence).

#### 3. Template Version Step Preservation (commit: 6e5db09)
**Problem**: Switching template versions reset to signature-objects step, disrupting workflow.
**Solution**: Removed step reset from handleVersionChange to preserve current view.

### Next Actions
- Create `.claude/commands/` directory with VBA analysis slash commands
- Run `/vba-inventory` to analyze VBA codebase structure
- Begin systematic VBA to Python/TypeScript migration
- Define new pipeline module definitions for database writing

### Notes
- VBA migration is full rewrite of previous MS Access/VBA system
- VBA code stored in `vba-code/` directory for analysis
- Slash commands documented in `context/docs/CLAUDE_CODE_SLASH_COMMANDS.md`
- All recent commits ready to push to remote
