# ETO System - Development Changelog

## Overview
This document tracks major development milestones and features implemented in the Email-to-Order (ETO) PDF processing system.

---

## [2025-11-06 15:30] — ExecutedPipelineViewer Component Implementation

### Spec / Intent
- Build new ExecutedPipelineViewer from scratch to visualize pipeline execution results
- Fix backend input pin name resolution to show upstream output pin names
- Create read-only pipeline visualization with execution data overlay
- Integrate with React Flow and dagre for automatic layout

### Changes Made

**Backend - Input Pin Name Resolution** (`server/src/features/pipeline_execution/service.py`):
- Created `_serialize_inputs_for_audit()` function (lines 185-250)
- Looks up upstream output pin names instead of using generic input group names
- Uses `input_field_mappings` to find upstream pin ID
- Uses `all_nodes_metadata` to find upstream pin name
- Updated `execute_pipeline()` to use new function for inputs (lines 974-980)
- Result: Input pins now show meaningful names like "hawb", "pu" instead of "text", "value"

**Frontend - ExecutedPipelineViewer Components** (`client/src/renderer/features/pipelines/components/ExecutedPipelineViewer/`):
- **ExecutedPipelineViewer.tsx** (287 lines):
  - Main orchestrator component with React Flow integration
  - Fetches modules using `useModules()` TanStack Query hook
  - Converts pipeline state + execution steps to React Flow nodes
  - Applies dagre layout (left-to-right, ranksep: 450, nodesep: 200)
  - **Critical Fix**: Always iterates pipeline state for structure, overlays execution data
  - This ensures all handles render even when execution data is incomplete
  - Maps connections to edges with proper handle IDs

- **ExecutedEntryPoint.tsx** (41 lines):
  - Wrapper component that reuses ExecutedModule with hardcoded values
  - Black header (#000000), "Entry Point" title
  - No inputs, single string output with entry point name
  - Uses `entry-${nodeId}` prefix for node IDs (critical for edge connections)

- **ExecutedModule.tsx** (74 lines):
  - Module node component composed of header + body
  - Border color based on execution status (red for failed, gray for executed)
  - Dynamic width based on content

- **ExecutedModuleHeader.tsx**:
  - Colored header bar with module name
  - Uses `getTextColor()` utility for proper text contrast

- **ExecutedModuleBody.tsx**:
  - Two-column layout (inputs left, outputs right)
  - Renders ExecutedModuleRow for each pin
  - Shows error message if execution failed

- **ExecutedModuleRow.tsx** (85 lines):
  - Individual pin row with React Flow Handle
  - Type-colored indicator badge (from TYPE_COLORS)
  - Mirrored layout: inputs show "name - type", outputs show "type - name"
  - Handle positioned on outer edge (-13px offset)

### Technical Details

**Critical Handle Rendering Fix**:
```typescript
// Always iterate through pipeline state for structure
moduleInstance.inputs.forEach((input) => {
  const executionData = executionStep?.inputs?.[input.node_id];
  inputs[input.node_id] = {
    name: executionData?.name || input.name,
    value: executionData?.value || "",
    type: executionData?.type || input.type,
  };
});
```

**Why This Matters**: Without this approach, React Flow throws "Couldn't create edge for source handle id" errors when execution data is incomplete. We iterate pipeline state (source of truth for structure) and overlay execution data (which may be incomplete).

**Entry Point ID Prefixing**:
```typescript
// Create entry point nodes with 'entry-' prefix
id: `entry-${entryPoint.node_id}`,

// Map in edge lookup
nodeIdToModuleId.set(ep.node_id, `entry-${ep.node_id}`);
```

**Dagre Layout Configuration**:
- Node dimensions: 220px × 180px
- Direction: Left-to-right (LR)
- Horizontal spacing (ranksep): 450px
- Vertical spacing (nodesep): 200px

### Errors Fixed

**Error 1: Input Pins Showing Generic Names**
- Before: Inputs showed "text", "value", "data" (group names)
- After: Inputs show "hawb", "pu", "due date text" (upstream output names)
- Fix: Created `_serialize_inputs_for_audit()` with upstream pin lookup

**Error 2: React Flow Handle Error**
- Error: `[React Flow]: Couldn't create edge for source handle id: "Na4y"`
- Root cause: Module "Ml2" had output "Na4y" in pipeline state but empty outputs in execution step
- Fix: Always iterate pipeline state for structure, overlay execution data for values
- Result: All handles render even when execution data is missing

**Error 3: Entry Point Edge Connections**
- Problem: Edges from entry points to modules weren't connecting
- Root cause: Entry point node IDs didn't match expected `entry-` prefix pattern
- Fix: Consistently use `entry-${nodeId}` prefix for all entry point nodes

### Architecture Decisions

**Why Reuse ExecutedModule for Entry Points?**
- Consistency: Same styling and structure as regular modules
- Simplicity: No duplicate component code
- Maintainability: Changes to module styling apply to entry points

**Why Iterate Pipeline State Instead of Execution Steps?**
- Completeness: Pipeline state is source of truth for structure
- Resilience: Handles missing execution data gracefully
- Edge Connections: Ensures all handles exist for React Flow

**Why Dagre Layout?**
- Hierarchical: Natural left-to-right flow from entry points to outputs
- Automatic: No manual positioning needed
- Consistent: Same layout algorithm as pipeline builder

### Next Actions
- Implement ExecutionEdge component with smooth step paths
- Add type-colored edges with value labels
- Add hover effects and value truncation
- Calculate offsets for parallel edges
- Test with various pipeline structures

### Notes
- All components are read-only (no editing functionality)
- Uses TanStack Query for module data fetching
- Replaces old executedViewer-old implementation
- Current state: Basic visualization working with straight-line edges
- Ready for ExecutionEdge implementation with enhanced styling
- Detailed continuity document created at `context/CONTINUITY.md`

---

## [2025-10-30 17:15] — ETO API Conversion to TanStack Query

### Spec / Intent
- Convert ETO API from imperative callbacks to declarative TanStack Query hooks
- Remove all mock data references and use real backend API
- Match the pattern established by PDF API (useQuery for GET, useMutation for POST/DELETE)
- Leverage TanStack Query's automatic caching, refetching, and state management

### Changes Made

**New ETO API Hooks (useEtoApi.ts):**
```typescript
// Query hooks (GET operations)
- useEtoRuns(params?) - List runs with filtering/pagination
- useEtoRunDetail(runId) - Get single run detail

// Mutation hooks (POST/DELETE operations)
- useCreateEtoRun() - Upload PDF and create ETO run (2-step)
- useReprocessRuns() - Bulk reprocess failed/skipped runs
- useSkipRuns() - Bulk skip runs
- useDeleteRuns() - Bulk delete skipped runs

// Utility
- getPdfDownloadUrl(pdfFileId) - Re-exported from PDF feature
```

**Deleted:**
- `useMockEtoApi.ts` - 384 lines of mock implementation
- `EtoRunsTable copy.tsx` - Duplicate file
- All references to `../mocks/data` imports

**RunDetailModal.tsx:**
- Before: Imperative `useMockEtoApi()` with manual state (`runDetail`, `error`, `isLoading`)
- After: Declarative `useEtoRunDetail(runId)` with automatic data fetching
- Removed `loadRunDetail()` function and manual error handling
- TanStack Query manages all loading and error states

**ETO Page (pages/dashboard/eto/index.tsx):**
- Before: Imperative `useEtoApi()` with callbacks (`getEtoRuns()`, `uploadPdf()`, etc.)
- After: Declarative hooks with automatic state management
  - `useEtoRuns()` for data fetching
  - `useCreateEtoRun()`, `useReprocessRuns()`, etc. for mutations
- Removed manual `runsByStatus` state - now derived via `useMemo` from query data
- Removed `loadRuns()` function - TanStack Query auto-refetches on mutations
- Updated all button handlers to use `mutation.mutateAsync()`
- Simplified SSE handlers - query invalidation handles cache updates

**Benefits Achieved:**
1. **Automatic caching** - Runs cached for 5 minutes, reducing API calls
2. **Request deduplication** - Multiple components requesting same data = 1 API call
3. **Automatic refetch** - Mutations auto-invalidate and refetch affected queries
4. **Built-in states** - No manual `isLoading`, `error` state management
5. **Consistent pattern** - ETO API now matches PDF API architecture
6. **Less code** - 592 lines removed (944 deleted, 352 added)

### Technical Details

**Before (Imperative):**
```typescript
const { getEtoRuns, uploadPdf, isLoading, error } = useEtoApi();

const loadRuns = async () => {
  const response = await getEtoRuns();
  setRunsByStatus(groupByStatus(response.items));
};

const handleUpload = async (file: File) => {
  await uploadPdf(file);
  await loadRuns(); // Manual refetch
};
```

**After (Declarative):**
```typescript
const { data, isLoading, error } = useEtoRuns();
const createEtoRun = useCreateEtoRun();

const runsByStatus = useMemo(() =>
  groupByStatus(data?.items), [data]
);

const handleUpload = async (file: File) => {
  await createEtoRun.mutateAsync(file);
  // TanStack Query auto-invalidates and refetches
};
```

**Query Configuration:**
- `useEtoRuns()`: staleTime 30s, gcTime 5min
- `useEtoRunDetail()`: staleTime 30s, gcTime 5min
- All mutations invalidate `['eto-runs']` and `['eto-run']` queries on success

### Next Actions
- Test real API integration with backend
- Add error toast notifications for better UX
- Consider implementing optimistic updates for instant feedback

### Notes
- TypeScript compilation: ✅ Zero errors
- 10 files changed: 352 insertions, 944 deletions
- SSE handlers simplified but still connected for real-time updates
- Backend API fully implemented and ready (all 7 endpoints)

---

## [2025-10-30 16:25] — Client Architecture Refactoring: Feature-First Organization

### Spec / Intent
- Establish feature-first architecture with shared/ as pure infrastructure only
- Move PDF feature from shared/ to features/pdf/ with consolidated API hooks
- Move moduleTypes and pipelineTypes from shared/types/ to respective feature directories
- Update all import statements across 15+ files to use new feature-relative paths
- Delete unused mock data (3.5 MB) and empty directories

### Changes Made

**Files Created:**
- `client/src/renderer/features/pdf/api/hooks.ts` - Consolidated all PDF API hooks into single file (usePdfData, usePdfMetadata, usePdfObjects, useUploadPdf, useProcessPdfObjects)
- `client/src/renderer/features/pdf/index.ts` - Unified export point for entire PDF feature
- `client/src/renderer/features/modules/types.ts` - Moved from shared/types/moduleTypes.ts
- `client/src/renderer/features/modules/index.ts` - Export file for modules feature
- `client/src/renderer/features/pipelines/types.ts` - Moved from shared/types/pipelineTypes.ts (imports and re-exports module types)
- `client/src/renderer/features/pipelines/index.ts` - Export file for pipelines feature

**PDF Feature Consolidation:**
- Moved PDF API, components, and hooks from shared/ to features/pdf/
- Consolidated separate hook files into single hooks.ts file (user preference)
- Updated 14 import statements across templates and eto features
- Moved PdfViewer components from shared/components/pdf/ to features/pdf/components/

**Type System Migration:**
- Moved moduleTypes.ts → features/modules/types.ts
- Moved pipelineTypes.ts → features/pipelines/types.ts (imports from modules, adds pipeline-specific types)
- Updated 15 files with new import paths using Edit tool
- Files updated: modules (2), pipelines (7), templates (6)

**Directories Deleted:**
- `client/src/renderer/features/pdf-files/` (entire feature with 3.5 MB mock data)
- `client/src/renderer/shared/api/pdf/`
- `client/src/renderer/shared/components/pdf/`
- `client/src/renderer/shared/components/` (empty after PDF move)
- `client/src/renderer/shared/types/` (empty after types migration)

### Technical Details

**Import Path Changes:**
```typescript
// Before: shared/types/moduleTypes
import { ModuleTemplate } from "../../../../shared/types/moduleTypes";

// After: features/modules/types
import { ModuleTemplate } from "../../../modules/types";

// Before: types/pipelineTypes
import { PipelineState } from '../../../types/pipelineTypes';

// After: features/pipelines/types
import { PipelineState } from '../../pipelines/types';
```

**Architecture Pattern Established:**
```
shared/
  api/ - Pure infrastructure (Axios client, config, interceptors)
  utils/ - Pure utilities

features/
  {feature-name}/
    api/ - Feature-specific API logic
    components/ - Feature-specific UI components
    hooks/ - Feature-specific React hooks
    types.ts - Feature-specific types
    index.ts - Unified exports
```

**74 Files Changed:**
- 410 insertions
- 196,317 deletions (mostly mock data)
- Zero TypeScript errors after all changes

### Next Actions
- Continue client directory cleanup (check for remaining shared/ issues)
- Consider moving other shared items to features if feature-specific
- Update documentation to reflect new architecture pattern

### Notes
- TypeScript compilation: ✅ Zero errors
- All imports updated systematically using Edit tool (not bulk sed commands)
- Followed "shared when needed, not by default" principle
- PDF hooks consolidated into single file per user preference
- Line ending warnings (CRLF) are normal Git behavior on Windows

---

## [2025-10-29 Current] — Template Builder Architecture Documentation

### Spec / Intent
- Document template builder architecture comprehensively for refactoring
- Identify root causes of entry point state management issues
- Catalog all design issues and intricacies that accumulated
- Create reference document for cleaning up "spaghetti code"
- Support user's planned refactoring based on new design principles

### Changes Made

**Architecture Documentation** (`context/docs/template-builder-architecture.md`):
- Created comprehensive 350+ line documentation of template builder architecture
- Documented component hierarchy: TemplateBuilderModal → PipelineBuilderStep → PipelineGraph
- Mapped all state management flows and data transformations
- Identified 4 major architectural issues:
  1. Entry point management split across components
  2. "Meaningful state" check creating unpredictability
  3. Visual state updates too broad (all onChange vs targeted drag/drop)
  4. Visual state structure unnecessarily nested (modules/entryPoints separation)
- Documented entry point positioning algorithm with code examples
- Mapped serialization functions and their purposes
- Catalogued all file locations with line numbers for refactoring
- Included type definitions (current and proposed)
- Created file reference map showing purpose of each component

**Key Sections**:
- Component Hierarchy (with visual tree)
- State Management (all 10+ state variables documented)
- Current Issues (4 major problems with root cause analysis)
- Entry Point Positioning Logic (algorithm walkthrough)
- Entry Point Representation (fake module structure)
- Serialization Functions (domain ↔ API conversion)
- Imperative API via Ref (useImperativeHandle methods)
- Mount/Unmount Pattern (current implementation and problems)
- Identified Root Causes (why entry points not saving, why infinite loops)
- File Reference Map (6 key files with purposes)
- Design Principles for Refactor (user's 4 requirements)
- Type Definitions (current and proposed structures)

### Design Principles Established (User Requirements)

1. **Entry point state in ExtractionFieldsStep**: Extraction field step should directly update entry_points in pipelineState when user adds/removes fields (not PipelineBuilderStep)
2. **Remove meaningful state check**: Always reconstruct pipeline graph predictably from parent state
3. **Target visual state to drag/drop**: Only update visual state on specific drag end events, not all onChange
4. **Flatten visual state**: Change from `{modules: {}, entryPoints: {}}` to `{"node_id": {x: int, y: int}}`

### Root Causes Identified

**Why Entry Point Positions Not Persisting**:
1. Dynamic entry point sync disabled (commented out to avoid infinite loops)
2. Initialization runs once via `hasInitializedRef` - doesn't re-run when entry points change
3. onChange timing - entry point additions don't reliably trigger onChange callback
4. Mount/unmount destroys React Flow state, reconstruction doesn't populate visual state

**Why Infinite Loops Occurred**:
1. useEffect triggered onChange after entry points synced
2. onChange updated parent state
3. Parent re-rendered PipelineBuilderStep
4. useEffect triggered again
5. Cycle repeated indefinitely

**Design Issues**:
- Too many layers of abstraction (TemplateBuilderModal → PipelineBuilderStep → PipelineGraph → usePipelineInitialization)
- Entry point conversion in wrong place (should be in ExtractionFieldsStep)
- Reactive updates crossing component boundaries without proper memoization
- Nested visual state structure adds complexity to serialization

### File Reference Map

| File | Lines | Purpose | Key Issues |
|------|-------|---------|------------|
| `TemplateBuilderModal.tsx` | 507-564 | Root state container, conditional rendering | Mount/unmount clears state |
| `PipelineBuilderStep.tsx` | 30-73 | Adapter, converts fields→entries | Entry point conversion in wrong layer |
| `PipelineGraph.tsx` | 107-302 | Visual editor, React Flow integration | Dynamic sync disabled, onChange timing |
| `usePipelineInitialization.ts` | 60-111 | Mount logic, positioning | Meaningful state check, one-time init |
| `serialization.ts` | 53-69 | State conversion | Nested structure complexity |
| `ExtractionFieldsStep.tsx` | - | Extraction field drawing | Should update entry points directly |

### Technical Details

**Entry Point Flow (Current - Problematic)**:
```
ExtractionFieldsStep (user creates fields)
  ↓ extractionFields passed as prop
PipelineBuilderStep (useMemo converts to entry points)
  ↓ entryPoints derived
PipelineGraph (renders as fake modules)
  ↓ onChange callback
Parent state updated
```

**Entry Point Flow (Proposed)**:
```
ExtractionFieldsStep (user creates fields)
  ↓ directly updates pipelineState.entry_points
  ↓ also updates extractionFields
TemplateBuilderModal (single source of truth)
  ↓ passes both to PipelineBuilderStep
PipelineGraph (renders from state, updates visual on drag only)
```

**Visual State Structure**:
```typescript
// Current (nested)
{
  modules: { "module-1": {x: 100, y: 100} },
  entryPoints: { "entry_field1": {x: 50, y: 50} }
}

// Proposed (flat)
{
  "module-1": {x: 100, y: 100},
  "entry_field1": {x: 50, y: 50}
}
```

### Next Actions

User plans to refactor based on documented architecture:
1. Move entry point state updates from PipelineBuilderStep to ExtractionFieldsStep
2. Remove `hasMeaningfulState()` function and `hasInitializedRef` guard
3. Change visual state updates from onChange to specific drag/drop event handlers
4. Flatten visual state structure to eliminate modules/entryPoints separation
5. Clean up unnecessary abstractions and intricacies

### Notes
- Documentation provides complete reference for refactoring
- All issues traced to root causes with code locations
- User will handle implementation of refactoring
- Document preserved in `context/docs/` for future sessions
- Previous session work: Entry point positioning fixes, validation, color fixes, coordinate transformations
- Infinite loop issue attempted fix but led to architectural rethink

---

## [2025-10-28 18:30] — Template Viewer UI Enhancement & Visibility Toggles

### Spec / Intent
- Update template viewer modal to match template builder UI structure
- Add object type visibility toggles for signature objects view
- Simplify stepper to show only step numbers (1, 2, 3) without testing section
- Enable users to selectively show/hide signature object types on PDF overlay
- Improve consistency between builder and viewer experiences

### Changes Made

**TemplateDetailModal UI Overhaul** (`client/src/renderer/features/templates/components/modals/TemplateDetailModal.tsx`):

**1. Sidebar Structure Update (lines 476-547)**:
- Changed from expandable grouped list to flat type count display
- Added "Template Information" section showing total signature object count
- Added "Object Visibility" section with "Show All" / "Hide All" buttons
- Converted static type displays to interactive toggle buttons
- Each button shows: color square, type label, count, and active/inactive state
- Buttons use same styling as builder: bright when visible, dim when hidden

**2. Visibility State Management (lines 446-471)**:
- Added `selectedTypes` state (Set<string>) initialized with all types visible
- Implemented `handleTypeToggle()` for individual type visibility control
- Implemented `handleShowAll()` to make all types visible at once
- Implemented `handleHideAll()` to hide all overlays
- State persists during user interaction within current version

**3. Signature Object Overlay Filtering (lines 364-403)**:
- Updated `SignatureObjectsOverlay` component to accept `selectedTypes` prop
- Modified flattening logic to only include objects of selected types
- Conditional assembly: checks `selectedTypes.has(type)` before adding to array
- Overlay now respects visibility toggles in real-time
- Performance optimized with useMemo dependency on selectedTypes

**4. Stepper Simplification (lines 28-72, 296)**:
- Created `TemplateViewerStepper` component (replaces TemplateBuilderStepper)
- Shows only numbers 1, 2, 3 (no checkmarks, no testing step)
- Three steps: Signature Objects, Extraction Fields, Pipeline
- Active step highlighted in blue (bg-blue-600), inactive in gray
- Removed all testing/validation UI elements from viewer
- Footer integration: replaced old stepper with new simplified version

### Technical Details

**Visibility Toggle Flow**:
1. User clicks object type button → `handleTypeToggle(type)` fires
2. State updates: `selectedTypes` Set adds or removes type
3. React re-renders with new selectedTypes
4. `SignatureObjectsOverlay` useMemo recalculates filtered objects
5. Only selected types appear on PDF canvas overlay

**State Initialization**:
- `selectedTypes` starts with all types that have count > 0
- Uses functional initialization: `useState(() => new Set(allTypes))`
- Prevents showing toggles for types with zero objects
- All visible by default for best initial user experience

**Button Styling**:
```typescript
// Active: bg-gray-700 text-white (bright, clearly selected)
// Inactive: bg-gray-800 text-gray-400 hover:bg-gray-700 (dim, can hover to activate)
```

**Overlay Performance**:
- useMemo with `[signatureObjects, currentPage, selectedTypes]` dependencies
- Only recalculates when types toggled or page changed
- Conditional forEach loops prevent unnecessary object processing
- No performance impact from visibility toggles

### Before/After Comparison

**Sidebar Structure**:
- Before: Expandable sections with all objects listed individually ❌
- After: Flat list with type counts and visibility toggles ✅

**Object Visibility Control**:
- Before: All signature objects always visible (no control) ❌
- After: Click to show/hide individual types, Show All / Hide All buttons ✅

**Stepper Display**:
- Before: Shows checkmarks, includes "Testing" step with validation status ❌
- After: Shows only numbers 1-2-3, no testing section (viewer is read-only) ✅

**UI Consistency**:
- Before: Viewer sidebar had different structure than builder ❌
- After: Viewer sidebar matches builder structure exactly ✅

### User Experience

**Visibility Control Benefits**:
- Users can focus on specific object types (e.g., only text_words for text analysis)
- Reduces visual clutter when many overlapping objects
- Quick toggle between "show all" and "show specific types"
- Helps identify which objects contribute to signature matching

**UI Improvements**:
- Consistent experience between building and viewing templates
- Simpler navigation (3 steps vs 4, no testing complexity)
- Clear visual feedback on active/inactive types
- Professional, polished appearance matching builder

### Next Actions (Planned for Next Session)

**Template Viewer Enhancements**:
1. **Version Navigation Improvements**:
   - Currently works but needs polish
   - Consider adding version comparison view
   - Show changelog between versions

2. **Pipeline Viewer Implementation**:
   - Currently shows placeholder "Coming Soon" message
   - Need to integrate PipelineGraph component in read-only mode
   - Display pipeline execution flow visualization
   - Show module connections and data flow

3. **Template Edit Functionality**:
   - Add "Edit Template" workflow
   - Create new version via PUT /api/pdf-templates/{id}
   - Allow updating: name, description, signature objects, extraction fields, pipeline
   - Version management: create new version vs update current
   - Handle version increment logic

4. **Version Comparison**:
   - Side-by-side diff of two versions
   - Highlight changes in signature objects, fields, pipeline
   - Help users understand what changed between versions

### Files Modified
- `client/src/renderer/features/templates/components/modals/TemplateDetailModal.tsx` (major updates)
  - Line 28-72: Created TemplateViewerStepper component
  - Line 296: Integrated new stepper in footer
  - Line 364-403: Updated SignatureObjectsOverlay with visibility filtering
  - Line 446-471: Added visibility state management
  - Line 476-547: Rebuilt sidebar with toggle buttons

### Notes
- All changes are frontend-only (no backend modifications)
- TypeScript compilation: ✅ Passed with 0 errors
- No breaking changes to existing functionality
- Viewer now provides same level of control as builder
- Ready for next phase: pipeline viewer and edit functionality
- User switching computers - this entry provides full context for continuation

---

## [2025-10-28 15:45] — Template Simulation API Refactoring (JSON + PDF Objects)

### Spec / Intent
- Fix 500 error in template simulation caused by bytes in validation error responses
- Update frontend template simulation to match backend API refactoring
- Backend now accepts JSON with pre-extracted pdf_objects (not FormData with PDF bytes)
- Eliminate repeated PDF file uploads (objects already extracted during PDF load)
- Improve error handling to prevent JSON serialization failures with binary data

### Changes Made

**Backend - Error Handler** (`server-new/src/app.py`, lines 364-394):
- Fixed RequestValidationError handler to sanitize bytes in error details
- Replaces bytes with string `"<binary data, X bytes>"` before JSON serialization
- Prevents 500 errors when validation fails on binary data
- Returns proper 422 validation errors instead of crashing

**Frontend - API Types** (`client/src/renderer/features/templates/api/types.ts`):
- Removed discriminated union (source_pdf_id vs pdf_file)
- Replaced with single `PostTemplateSimulateRequest` interface accepting `pdf_objects`
- Added `ExtractedFieldResult` interface matching backend format
- Added `ExecutionStepResult` interface for pipeline execution trace
- Updated `PostTemplateSimulateResponse` to match new backend format:
  - `extraction_results: ExtractedFieldResult[]` (field name, bbox, extracted_value)
  - `pipeline_status: string` (success/failed)
  - `pipeline_steps: ExecutionStepResult[]` (step-by-step execution trace)
  - `pipeline_actions: Record<string, Record<string, any>>` (action inputs)
  - `pipeline_error: string | null`

**Frontend - API Hook** (`client/src/renderer/features/templates/hooks/useTemplatesApi.ts`, lines 205-232):
- Removed FormData support from `simulateTemplate` function
- Always sends JSON with `Content-Type: application/json` header
- Accepts `PostTemplateSimulateRequest` (not FormData builder)

**Frontend - Template Builder Modal** (`client/src/renderer/features/templates/components/builder/TemplateBuilderModal.tsx`, lines 242-318):
- Updated `handleTest` to use pre-extracted `pdfObjects` from `activePdfData`
- Removed 32 lines of FormData construction code
- Now builds clean JSON request object:
  - `pdf_objects: pdfObjects` (already available from PDF load)
  - `extraction_fields: ExtractionField[]`
  - `pipeline_state: PipelineState`
- Updated response mapping to convert new backend format to internal `TemplateSimulationResult`:
  - Maps `extraction_results` array to `extracted_data` dict (field name → value)
  - Maps `pipeline_actions` dict to `simulated_actions` array
  - Maps `pipeline_steps` to execution trace format

### Technical Details

**Backend Error Flow (Before Fix)**:
1. Frontend sends FormData with PDF bytes
2. Pydantic raises `RequestValidationError` (correct)
3. Error handler tries to return error details
4. Error details include raw PDF bytes in `input` field
5. JSON encoder throws: "Object of type bytes is not JSON serializable"
6. 500 error crashes before CORS headers added → CORS error in browser

**Backend Error Flow (After Fix)**:
1. Frontend sends invalid request
2. Pydantic raises `RequestValidationError`
3. Error handler sanitizes bytes: `input` → `"<binary data, X bytes>"`
4. Returns proper 422 validation error with sanitized details ✅

**Frontend Simulation Flow (Before)**:
1. Build FormData with PDF file/id + JSON strings
2. Send multipart/form-data to backend
3. Backend extracts objects from PDF bytes every time

**Frontend Simulation Flow (After)**:
1. Use `pdfObjects` already available from `activePdfData` (extracted once during PDF load)
2. Build JSON request with `pdf_objects`, `extraction_fields`, `pipeline_state`
3. Send application/json to backend
4. Backend uses pre-extracted objects directly (no file processing)
5. Map new response format to internal format

**Key Insight**: PDF objects are already extracted and available in modal state at line 162 (`pdfObjects` from `activePdfData`). No need to send PDF file again - eliminates bandwidth waste and complexity.

### Before/After Comparison

**Error Handling**:
- Before: 500 Internal Server Error with CORS issues ❌
- After: 422 Validation Error with readable messages ✅

**Request Format**:
- Before: FormData with PDF bytes (multipart/form-data) ❌
- After: JSON with pdf_objects (application/json) ✅

**Bandwidth**:
- Before: Send entire PDF file on every test ❌
- After: Send only object references (already extracted) ✅

**Code Complexity**:
- Before: 32 lines of FormData construction ❌
- After: 10 lines of JSON object building ✅

### Next Actions
- Test template simulation in browser with uploaded PDFs
- Test with stored PDFs (from existing pdf_files)
- Verify extraction results display correctly in TestingStep component
- Verify pipeline execution trace shows proper step-by-step results
- Test error handling for various validation failures

### Notes
- Both backend and frontend changes committed in separate commits
- Backend commit: "fix: Sanitize bytes in validation error responses"
- Frontend commit: "refactor(client): Update template simulation to use JSON with pdf_objects"
- TypeScript compilation: ✅ Passed with 0 errors
- All changes maintain consistency with backend API specification
- User confirmed 422 errors now working correctly
- Implementation completed and ready for testing

---

## [2025-10-28] — PDF Template Router Refactoring

### Spec / Intent
- Simplify PDF template creation by separating PDF upload from template creation
- Remove Form-based request with JSON strings in favor of clean JSON request body
- Follow REST principles: one resource per endpoint (PDFs managed separately from templates)
- Reduce router code complexity (117 lines → 33 lines in create endpoint)
- Eliminate manual JSON parsing, validation, and conditional file upload logic
- Frontend updated to use dual-request pattern: upload PDF → create template

### Changes Made

**File 1: `api/routers/pdf_files.py`**
- Added `POST /pdf-files` endpoint for manual PDF uploads
- Accepts multipart file upload, validates PDF format
- Stores PDF with automatic object extraction and hash-based deduplication
- Returns complete `PdfFile` response with ID for use in template creation
- Note: `email_id` is not accepted (only set by email ingestion service)

**File 2: `api/schemas/pdf_templates.py`**
- Updated `CreatePdfTemplateRequest.source_pdf_id` from `Optional[int]` → `int` (required)
- Added comment: "Required - PDF must be uploaded first via POST /pdf-files"

**File 3: `api/routers/pdf_templates.py`**
- **Refactored `create_pdf_template` endpoint:**
  - Changed from Form fields → JSON request body (`CreatePdfTemplateRequest`)
  - Removed 82 lines of JSON parsing, validation, and conditional PDF upload logic
  - Reduced from 117 lines → 33 lines (72% reduction)
  - Now follows standard pattern: request → mapper → service → response
  - Removed dual-mode operation (stored vs upload)

- **Removed imports:**
  - Removed `Union` from typing imports (unused)

- **Kept imports needed for simulate endpoint:**
  - `json`, `File`, `UploadFile`, `Form`, `PdfFilesService` still required by `/simulate`

### Architecture Pattern

**Before (Single Request with Mixed Concerns):**
```
POST /pdf-templates (Form-data)
├── Parse JSON strings manually
├── Validate with Pydantic manually
├── Conditional: Upload PDF OR use existing
├── Build request object
└── Create template
```

**After (Two Clean Requests):**
```
1. POST /pdf-files (multipart)
   └── Returns: { id: 123, ... }

2. POST /pdf-templates (JSON)
   {
     source_pdf_id: 123,
     name: "...",
     signature_objects: { ... },
     extraction_fields: [ ... ],
     pipeline_state: { ... },
     visual_state: { ... }
   }
```

### Code Comparison

**create_pdf_template endpoint:**
- Before: 117 lines (Form fields, JSON parsing, conditional upload)
- After: 33 lines (JSON body, mapper delegation)
- Reduction: 72%

**Lines of business logic in router:**
- Before: ~80 lines (validation, PDF upload, request building)
- After: ~5 lines (mapper call, service call, response conversion)

### Benefits

**Architecture:**
- ✅ Clean separation: PDF management vs template management
- ✅ REST principles: one resource per endpoint
- ✅ Follows reference patterns (email_configs, modules)
- ✅ Single Responsibility Principle enforced

**Code Quality:**
- ✅ 72% code reduction in create endpoint
- ✅ No manual JSON parsing (FastAPI handles it)
- ✅ No conditional logic in router
- ✅ Proper request/response types

**Maintainability:**
- ✅ Easier to test (no file mocking in template tests)
- ✅ Better error messages (FastAPI validation)
- ✅ Standard JSON request/response contract

**API Design:**
- ✅ Clean OpenAPI documentation
- ✅ Consistent with other endpoints
- ✅ Frontend can show loading states across both calls

### Next Actions
- Frontend integration testing with dual-request flow
- Verify error handling (404 if pdf_id doesn't exist)
- Consider refactoring simulate endpoint (currently still uses Form-based approach)

### Notes
- Simulate endpoint intentionally kept with dual-mode (upload vs stored)
  - Used for preview/testing during template builder
  - Temporary PDFs for testing shouldn't be stored permanently
- All changes maintain backward compatibility in terms of API functionality
- No database schema changes required

---

## [2025-10-28] — PDF Files Domain Architecture Refactoring

### Spec / Intent
- Align pdf_files domain with email_configs and modules reference patterns
- Fix type naming inconsistencies (PdfMetadata → PdfFile, PdfCreate → PdfFileCreate)
- Remove duplicate/redundant schemas (GetPdfMetadataResponse)
- Standardize mapper naming convention (convert_pdf_metadata → pdf_file_to_api)
- Ensure API schemas match domain types exactly (no audit fields in responses)
- Maintain clean three-layer architecture: schemas → mappers → routers

### Changes Made

**File 1: `shared/types/pdf_files.py`**
- Renamed `PdfCreate` → `PdfFileCreate` for consistency with other domains

**File 2: `api/schemas/pdf_files.py`**
- Removed redundant `GetPdfMetadataResponse` class (use `PdfFile` instead)
- Updated `PdfFile` schema documentation to clarify it's API schema (not domain)
- Ensured schema doesn't include audit fields (created_at, updated_at)
- Changed field types to use `Optional[...]` for consistency

**File 3: `api/mappers/pdf_files.py`**
- Updated imports: `GetPdfMetadataResponse` → `PdfFile as PdfFilePydantic`
- Renamed `convert_pdf_metadata()` → `pdf_file_to_api()` (standard pattern)
- Updated return type to match `PdfFile` schema
- Fixed field mappings to use exact domain field names
- Added `stored_at.isoformat()` conversion for datetime field

**File 4: `api/routers/pdf_files.py`**
- Updated imports: `GetPdfMetadataResponse` → `PdfFile`, `convert_pdf_metadata` → `pdf_file_to_api`
- Changed `@router.get("/{id}")` response_model to `PdfFile`
- Renamed endpoint function: `get_pdf_metadata` → `get_pdf_file`
- Updated service calls: `get_pdf_metadata()` → `get_pdf_file()`
- Updated mapper calls: `convert_pdf_metadata()` → `pdf_file_to_api()`
- Fixed `get_pdf_objects` endpoint to call `get_pdf_file()` for page count

**File 5: `features/pdf_files/service.py`**
- Updated imports: `PdfMetadata` → `PdfFile`, `PdfCreate` → `PdfFileCreate`
- Renamed method: `get_pdf_metadata()` → `get_pdf_file()`
- Updated return types throughout: `PdfMetadata` → `PdfFile`
- Updated docstrings to use "file" terminology instead of "metadata"
- Updated `store_pdf()` to use `PdfFileCreate` and return `PdfFile`

**File 6: `shared/database/repositories/pdf_file.py`**
- Updated imports: `PdfMetadata` → `PdfFile`, `PdfCreate` → `PdfFileCreate`
- Updated `_model_to_dataclass()` return type: `PdfMetadata` → `PdfFile`
- Updated all method signatures to return `PdfFile` instead of `PdfMetadata`
- Updated `create()` method to accept `PdfFileCreate` parameter
- Updated docstrings for consistency

### Technical Details

**Naming Conventions Established:**
- Domain types: `PdfFile` (full record), `PdfFileCreate` (create data)
- API schemas: `PdfFile` (matches domain name exactly)
- Mapper functions: `{entity}_to_api()` pattern (e.g., `pdf_file_to_api()`)
- Service methods: `get_{entity}()` pattern (e.g., `get_pdf_file()`)

**Architecture Pattern:**
```
Router (HTTP) → Mapper (Conversion) → Service (Business Logic) → Repository (Data)
```

**Key Principles Applied:**
1. API schemas match domain types exactly (same field names)
2. Audit fields (created_at, updated_at) excluded from API responses
3. Single responsibility: routers handle HTTP, mappers handle conversion
4. Consistent naming across all layers
5. No duplicate type definitions between domain and API layers

### Before/After Comparison

**Type Names:**
- Before: `PdfMetadata`, `PdfCreate` ❌
- After: `PdfFile`, `PdfFileCreate` ✓

**API Schemas:**
- Before: `GetPdfMetadataResponse` (redundant), `PdfFile` (with audit fields) ❌
- After: `PdfFile` only (clean, matches domain) ✓

**Mapper Functions:**
- Before: `convert_pdf_metadata()` ❌
- After: `pdf_file_to_api()` ✓

**Service Methods:**
- Before: `get_pdf_metadata()` ❌
- After: `get_pdf_file()` ✓

### Testing Checklist
- [ ] Type checking passes (no PdfMetadata errors)
- [ ] GET /api/pdf-files/{id} returns PdfFile schema
- [ ] GET /api/pdf-files/{id}/objects works with updated service calls
- [ ] POST /api/pdf-files/process-objects still functions
- [ ] store_pdf() correctly uses PdfFileCreate

### Next Actions
- Test all pdf_files endpoints to ensure refactoring didn't break functionality
- Continue with pipelines.py refactoring (Phase 1 from previous analysis)
- Continue with pdf_templates.py refactoring (Phase 2 from previous analysis)

### Notes
- All changes maintain backward compatibility in terms of API contract
- No database schema changes required
- Changes align pdf_files with email_configs and modules patterns
- Ready for next phase: pipeline and template router refactoring

---

## [2025-10-27 14:45] — API Architecture Analysis & Refactoring Plan

### Spec / Intent
- Establish consistent API architecture pattern across all routers
- Use email_configs and modules as reference standard (three-layer: schemas → mappers → routers)
- Analyze pdf_files, pipelines, and pdf_templates for deviations
- Create detailed refactoring plan with specific line numbers and code examples
- Document all issues to enable seamless continuation in future sessions

### Changes Made
**No code changes** - Analysis and planning session only

**Created Comprehensive Planning Document** (`context/API_ARCHITECTURE_REFACTORING_PLAN.md`):
- Complete reference standard definition with examples
- Line-by-line analysis of all routers (pdf_files, pipelines, pdf_templates)
- Detailed issues with exact file paths and line numbers
- Before/after code examples for all required changes
- Phase-by-phase implementation plan with time estimates
- Testing checklist and success criteria
- Progress tracking section

### Analysis Results

**✅ pdf_files.py - COMPLIANT**
- Clean service injection pattern
- Consistent mapper usage throughout
- No business logic in router
- **No changes needed**

**⚠️ pipelines.py - 3 ISSUES IDENTIFIED**
1. **Direct Repository Access** (lines 221-231): Router accesses `PipelineDefinitionStepRepository` directly, bypassing service layer
2. **Inline DTO Construction** (lines 243-259): Building `ExecutionStepResultDTO` in router instead of using mapper
3. **Import Inside Function** (line 148): Import statement inside function instead of at top

**⚠️ pdf_templates.py - 5 ISSUES IDENTIFIED**
1. **JSON Parsing in Router** (lines 132-138, 311-316): Manual JSON parsing and validation logic in router
2. **Pydantic Validation in Router** (lines 141-147): Schema validation happening in router instead of automatic
3. **Complex Request Building** (lines 149-194): 45+ lines of business logic constructing requests
4. **Inline DTO Construction** (lines 361-381): Building DTOs directly in router for simulation results
5. **Form-Based Requests** (lines 98-109, 275-281): Mixed concerns with file uploads and JSON fields

### Reference Standard Pattern

**Key Principles Established:**
1. Router has NO business logic (HTTP concerns only)
2. Router does NO validation (Pydantic handles automatically)
3. Router does NO data transformation (mappers handle it)
4. Router does NO direct repository access (services handle it)
5. Mappers are separate functions in `api/mappers/`
6. Service layer returns domain types, not API schemas
7. Response type explicitly declared with `response_model`

**Standard Router Structure:**
```python
@router.post("", response_model=EntityAPI)
async def create_entity(
    request: CreateEntityRequest,
    service: EntityService = Depends(lambda: ServiceContainer.get_entity_service())
) -> EntityAPI:
    entity_create = create_request_to_domain(request)  # Mapper: API → Domain
    entity = service.create_entity(entity_create)       # Service: business logic
    return entity_to_api(entity)                        # Mapper: Domain → API
```

### Implementation Plan Created

**Phase 1: pipelines.py** (30-45 minutes)
- Add `get_compiled_steps()` method to `PipelineService`
- Create `convert_execution_result_to_api()` mapper function
- Update router to use service method and mapper
- Move import to top of file

**Phase 2: pdf_templates.py** (1.5-2 hours)
- Split create endpoint into `/from-stored` and `/from-upload`
- Create new schemas for clean JSON request body
- Move all parsing/validation logic to mappers
- Create `convert_simulation_result_to_api()` mapper
- Update frontend to use correct endpoints

**Phase 3: Documentation & Cleanup** (30 minutes)
- Update API documentation
- Remove unused imports
- Verify all routers follow standard pattern

### Technical Details

**Files Analyzed:**
- Reference: `api/routers/email_configs.py`, `api/routers/modules.py`
- Reference: `api/mappers/email_configs.py`, `api/mappers/modules.py`
- Reference: `api/schemas/email_configs.py`, `api/schemas/modules.py`
- Compare: `api/routers/pdf_files.py` (compliant)
- Compare: `api/routers/pipelines.py` (3 issues)
- Compare: `api/routers/pdf_templates.py` (5 issues)

**Architecture Layers:**
```
Router (HTTP) → Mapper (Conversion) → Service (Business) → Repository (Data)
```

**Separation of Concerns:**
- Router: HTTP concerns only (receive request, return response)
- Mapper: Type conversions (API schemas ↔ domain types)
- Service: Business logic (validation, orchestration)
- Repository: Data access (database operations)

### Recommended Endpoint Split for pdf_templates.py

**Current:** Single `POST /api/pdf-templates` with form fields
**Proposed:**
- `POST /api/pdf-templates/from-stored` - Clean JSON body for stored PDFs
- `POST /api/pdf-templates/from-upload` - Multipart form for file uploads

**Benefits:**
- Stored PDF endpoint uses clean Pydantic models
- Upload endpoint isolated to file handling only
- Better separation of concerns
- Easier to test and maintain

### Next Actions
1. Begin Phase 1: Refactor pipelines.py
2. Add service method for compiled steps
3. Create mapper for execution results
4. Test pipeline execution endpoint
5. Move to Phase 2: Refactor pdf_templates.py

### Notes
- Complete continuity document created in `context/API_ARCHITECTURE_REFACTORING_PLAN.md`
- All issues documented with exact line numbers
- Code examples provided for all changes
- Ready for immediate implementation pickup
- Estimated total time: 2.5-3 hours for all changes

---

## [2025-10-27 02:30] — Template Builder Pipeline State Persistence & Simulate Execution Integration

### Spec / Intent
- Fix pipeline state being cleared when navigating back to pipeline builder step
- Remove delete buttons from entry point modules (they depend on extraction fields)
- Integrate full pipeline execution into template simulate endpoint
- Follow dependency injection pattern for service dependencies
- Clean up debug logging in template builder

### Changes Made

**Pipeline State Persistence Fix** (`client/src/renderer/features/pipelines/hooks/usePipelineInitialization.ts`):
- Added `isInitialized` state to track when initialization completes
- Created `UsePipelineInitializationReturn` interface with `isInitialized: boolean`
- Set `isInitialized = true` only after nodes/edges are reconstructed or created
- Reset `isInitialized = false` in cleanup function
- Root cause: `onChange` was firing before reconstruction, wiping parent state

**Pipeline Graph Guard** (`client/src/renderer/features/pipelines/components/PipelineGraph.tsx`):
- Captured `isInitialized` from `usePipelineInitialization` hook
- Added guard to `onChange` effect: `if (!isInitialized) return;`
- Prevents premature state updates until reconstruction completes
- Added `isInitialized` to effect dependency array

**Entry Point Delete Button Removal**:
- Updated `Module.tsx` to accept and pass `isEntryPoint?: boolean` prop
- Updated `ModuleHeader.tsx` to conditionally hide delete button
- Changed condition to: `{!executionMode && !isEntryPoint && <delete button>}`
- Entry point nodes already have `isEntryPoint: true` in their data

**Pipeline Execution Integration** (`server-new/src/shared/services/service_container.py`):
- Added `PipelineExecutionService` to TYPE_CHECKING imports
- Added `pipeline_execution` service definition with args `[cls._connection_manager]`
- Updated `pdf_templates` service args to include `_service:pipeline_execution`
- Added `get_pipeline_execution_service()` convenience method

**PdfTemplateService Updates** (`server-new/src/features/pdf_templates/service.py`):
- Added imports: `PipelineExecutionService`, `PipelineExecutionResult`
- Added class attribute: `pipeline_execution_service: PipelineExecutionService`
- Updated `__init__` to accept `pipeline_execution_service` parameter
- Modified `simulate()` return type to `tuple[dict[str, str], PipelineExecutionResult]`
- Added Step 5: Execute pipeline with extracted data using injected service
- Added debug prints for execution results (status, steps, actions)

**API Router Updates** (`server-new/src/api/routers/pdf_templates.py`):
- Updated simulate endpoint to handle new return type from service
- Converted `execution_result.steps` to `PipelineStepSimulation` DTOs
- Converted `execution_result.executed_actions` to `SimulatedAction` DTOs
- Updated response to include actual execution results instead of empty arrays
- Response now shows: status, error_message, step trace, simulated actions

**Frontend Cleanup** (`client/src/renderer/features/templates/components/builder/TemplateBuilderModal.tsx`):
- Removed console.log debug wrappers from pipeline render
- Removed debug wrapper functions `handlePipelineStateChange` and `handleVisualStateChange`
- Changed to use `setPipelineState` and `setVisualState` directly
- Cleaner code without debugging artifacts

### Technical Details

**Pipeline State Persistence Flow**:
1. User navigates away from step 3 → PipelineGraph unmounts (state saved in parent)
2. User navigates back → PipelineGraph remounts with empty nodes/edges initially
3. `onChange` effect BLOCKED by `!isInitialized` guard (prevents wipe)
4. `usePipelineInitialization` reconstructs nodes/edges from saved state
5. Sets `isInitialized = true` after reconstruction completes
6. `onChange` effect now allowed to fire (state properly synchronized)

**Dependency Injection Pattern**:
- Services injected via constructor through ServiceContainer
- Never import services directly in methods
- ServiceContainer definitions map service names to classes and dependencies
- `_service:name` notation indicates dependency on another service
- ServiceProxy used for lazy resolution to prevent circular dependencies

**Execution Flow in Simulate Endpoint**:
1. Extract text from PDF bytes (using extraction_fields bounding boxes)
2. Validate pipeline structure (type checking, cycles, unconnected inputs)
3. Prune dead branches (remove unreachable modules)
4. Compile to execution steps (topological sort, step ordering)
5. **NEW**: Execute pipeline with Dask task graph
6. Return extracted_data + execution_result to endpoint
7. Convert domain objects to API DTOs
8. Return full simulation response with execution trace

**Entry Point Values to Pipeline Execution**:
- Extraction fields produce `extracted_data: dict[str, str]` (field name → text value)
- Pipeline entry points have names matching extraction field names
- `execute_pipeline(entry_values_by_name=extracted_data, ...)` - perfect mapping!
- Pipeline execution automatically wires entry values to entry point nodes

### Errors Fixed

**Error 1: Pipeline State Wiped on Navigation**
- Root cause: `onChange` fired before initialization, serialized empty arrays
- User evidence: Console logs showing 3 modules → 0 modules
- Fix: Added initialization guard to prevent premature state updates
- Result: Pipeline now correctly persists across navigation

**Error 2: Incorrect Dependency Injection**
- Root cause: Initially planned to import service directly in method
- User feedback: "do not import the service directly into the function"
- Fix: Followed ServiceContainer pattern with constructor injection
- Result: Proper separation of concerns, testable architecture

### Before/After Behavior

**Pipeline State Persistence**:
- Before: Navigating back wiped pipeline → had to rebuild from scratch ❌
- After: Pipeline fully restores with all modules and connections ✅

**Entry Point Deletion**:
- Before: Could delete entry points → broke connection to extraction fields ❌
- After: Entry points locked (no delete button shown) ✅

**Simulate Endpoint**:
- Before: Only extraction + compilation (no execution) ❌
- After: Full flow: extraction → compilation → execution ✅
- Returns step-by-step trace with inputs/outputs for debugging

### Next Actions
- Test full template simulation flow end-to-end
- Verify execution results display correctly in TestingStep component
- Test with various pipeline configurations and extraction fields
- Verify error handling for failed pipeline execution
- Consider adding execution time metrics

### Notes
- TypeScript compilation: ✅ Passed with 0 errors
- All changes follow established patterns in codebase
- Pipeline execution uses Dask for lazy evaluation and parallel execution
- Simulation mode: Actions collect data but don't execute (safe testing)
- User confirmed fix: "great that is working"

---

## [2025-10-26 17:15] — Add Auto-Validation to Template Builder Pipeline Step

### Spec / Intent
- Add real-time pipeline validation to template builder (same as pipeline create page)
- Block Test button when pipeline is invalid or validating
- Show validation error code and message in tooltip popup
- Provide immediate feedback as users build pipelines

### Changes Made

**Pipeline Validation Integration** (`client/src/renderer/features/templates/components/builder/TemplateBuilderModal.tsx`):
- Imported `usePipelineValidation` hook from pipelines features (line 12)
- Added validation hook call after state declarations (line 84):
  ```typescript
  const { isValid: isPipelineValid, error: pipelineValidationError, isValidating: isPipelineValidating } = usePipelineValidation(pipelineState);
  ```

**Updated canProceed Logic** (lines 173-188):
- Pipeline step now requires `isPipelineValid && !isPipelineValidating`
- Test button automatically disabled when pipeline invalid or validating
- Added validation state to useMemo dependencies

**Updated validationMessage Logic** (lines 190-217):
- Added case for `pipeline` step showing validation errors
- Shows "Validating pipeline..." while validation in progress
- Shows `[error_code] error_message` format when validation fails
- Error appears in tooltip popup above disabled Test button

### Technical Details

**Validation Flow**:
1. User modifies pipeline (adds module, creates connection, etc.)
2. PipelineBuilderStep calls `onPipelineStateChange` callback
3. TemplateBuilderModal updates `pipelineState`
4. `usePipelineValidation` hook detects change and starts 500ms debounce timer
5. After debounce, hook calls backend `POST /api/pipelines/validate` endpoint
6. Backend performs validation (type checking, cycle detection, unconnected inputs)
7. Hook updates `isPipelineValid` and `pipelineValidationError` state
8. UI updates: Test button enabled/disabled, tooltip shows error if any

**Validation Rules** (same as pipeline create page):
- ✅ All connections reference valid pins
- ✅ Type compatibility (str→str, int→int, etc.)
- ✅ No duplicate connections
- ✅ No cycles (DAG requirement)
- ✅ All module inputs connected

**Error Code Examples**:
- `[invalid_reference]` - Non-existent pins or modules
- `[type_mismatch]` - Incompatible connection types
- `[duplicate_connection]` - Duplicate connections
- `[cycle_detected]` - Circular dependencies
- `[unconnected_input]` - Missing required connections
- `[invalid_connection]` - Invalid pin directions

### User Experience

**Before**:
- Test button always enabled (except during testing)
- No validation until backend processes the test
- Invalid pipelines would fail during test with generic errors

**After**:
- Test button disabled while validating (shows "Validating pipeline...")
- Test button disabled if pipeline invalid (shows specific error with code)
- Hover over disabled button shows validation error tooltip
- Immediate feedback as pipeline is built (500ms debounce)
- Prevents testing invalid pipelines (saves time and API calls)

### Example Validation Messages

```
Validating pipeline...
[type_mismatch] Cannot connect int output to str input
[cycle_detected] Pipeline contains circular dependency
[unconnected_input] Module 'uppercase' has unconnected required input 'text'
Pipeline validation failed
```

### Next Actions
- Test validation with various invalid pipeline scenarios
- Verify error messages are clear and actionable
- Consider adding visual indicators on invalid connections (red edges)
- Continue with template simulate endpoint integration

### Notes
- TypeScript compilation: ✅ Passed with 0 errors
- Uses same validation hook as pipeline create page (consistent behavior)
- 500ms debounce prevents excessive API calls during rapid changes
- Empty pipelines (no modules) are considered valid (skip validation)

---

## [2025-10-26 16:45] — Fix Empty Type Array Handling in Pipeline Reconstruction

### Spec / Intent
- Fix template builder showing "no types allowed" for modules with empty type arrays
- Align type reconstruction behavior between pipeline create page and template builder
- Ensure empty type arrays are treated as "all types allowed" consistently
- Document comprehensive differences between the two pipeline builder implementations

### Changes Made

**Type Reconstruction Fix** (`client/src/renderer/features/pipelines/hooks/usePipelineInitialization.ts`):
- Added `ALL_TYPES` constant: `['str', 'int', 'float', 'bool', 'datetime']` (line 12)
- Updated `reconstructPins()` function (lines 119-130) to match `moduleFactory.ts` logic:
  ```typescript
  // Before: Empty arrays stayed empty
  const allowedTypes = typeVar
    ? template.meta.io_shape.type_params[typeVar] || []  // ❌
    : group.typing.allowed_types || [];  // ❌

  // After: Empty arrays become ALL_TYPES
  if (typeVar) {
    const typeParamTypes = template.meta.io_shape.type_params[typeVar] || [];
    allowedTypes = typeParamTypes.length === 0 ? ALL_TYPES : typeParamTypes;  // ✅
  } else {
    const directTypes = group.typing.allowed_types || [];
    allowedTypes = directTypes.length === 0 ? ALL_TYPES : directTypes;  // ✅
  }
  ```

**Comprehensive Analysis Document** (`context/PIPELINE_BUILDER_COMPARISON.md`):
- NEW FILE: Complete comparison of pipeline create page vs template builder
- Documented 9 key differences:
  1. Entry point creation (user-defined vs auto-generated)
  2. State storage location (local vs parent props)
  3. PipelineGraph props (no initial state vs with initial state)
  4. Pipeline state tracking (with validation vs without)
  5. Module loading (once vs with dependency)
  6. Entry point handling (automatic vs manual merge)
  7. Visual state capture (on-demand vs continuous)
  8. Reconstruction logic (never vs when returning to step)
  9. **Type reconstruction bug** (fixed in this session)
- Includes root cause analysis, summary table, recommendations, and testing checklist

### Technical Details

**Root Cause Analysis**:
- Pipeline create page uses `moduleFactory.createModuleInstance()` which has proper empty array handling
- Template builder uses `reconstructPins()` in `usePipelineInitialization.ts` which was missing the fallback
- Backend modules with `type_params: { T: [] }` or `allowed_types: []` mean "accept all types"
- Template builder was interpreting empty arrays literally (no types allowed)

**Behavior Before Fix**:
- Pipeline create page: `[]` → `['str', 'int', 'float', 'bool', 'datetime']` ✅
- Template builder: `[]` → `[]` (no connections possible) ❌

**Behavior After Fix**:
- Both pages now handle empty arrays consistently ✅
- Modules like data_duplicator now work in template builder ✅

### Comparison Summary

| Feature | Pipeline Create Page | Template Builder |
|---------|---------------------|------------------|
| Entry Points | User-defined via modal | Auto-generated from extraction fields |
| State Storage | Local component state | Parent component props |
| State Pattern | Pull (imperative via ref) | Push (reactive via callbacks) |
| Reconstruction | Never (always fresh) | Yes (from saved state) |
| Empty Type Arrays | Converts to ALL_TYPES ✅ | **NOW FIXED** ✅ |

### Next Actions
- Test module connections in template builder with generic modules (data_duplicator, etc.)
- Verify state persistence still works after type reconstruction
- Continue with template simulate endpoint integration (Phase 1 in CONTINUITY.md)
- Consider adding validation to template builder for consistency

### Notes
- TypeScript compilation: ✅ Passed with 0 errors
- No breaking changes to existing functionality
- Both pipeline implementations now have consistent type handling
- Comparison document serves as reference for future development

---

## [2025-10-26 14:30] — Template Builder Pipeline Integration & Schema Unification

### Spec / Intent
- Fix template builder pipeline integration with canonical type system
- Resolve schema duplication between templates and pipelines features
- Fix state persistence when navigating between template builder steps
- Improve module node UI (delete button spacing, output name initialization)

### Changes Made

**Schema Unification** (`client/src/renderer/features/templates/types.ts`):
- Removed duplicate `PipelineState` and `VisualState` interfaces (lines 53-83)
- Added comment directing to canonical location (`types/pipelineTypes.ts`)
- Eliminated schema mismatch issues:
  - Entry points: `id/label/field_reference` → `node_id/name/type` ✅
  - Modules: `instance_id/module_id` → `module_instance_id/module_ref` ✅
  - Pin types: `string[]` → `string` ✅

**Template Builder Type Updates**:
- `client/src/renderer/features/templates/api/types.ts` - Import from canonical location
- `client/src/renderer/features/templates/components/builder/TemplateBuilderModal.tsx` - Use canonical types
- `client/src/renderer/features/templates/components/builder/steps/PipelineBuilderStep.tsx` - Use canonical types
- `client/src/renderer/features/templates/components/builder/steps/ExtractionFieldsStep.tsx` - Use canonical types
- `client/src/renderer/features/templates/components/builder/steps/ExtractionFieldsStep/ExtractionFieldsSidebar.tsx` - Use canonical types

**State Persistence Fix** (`client/src/renderer/features/pipelines/hooks/usePipelineInitialization.ts`):
- Added `hasMeaningfulState()` function (lines 240-252) to distinguish empty vs populated state
- Checks for actual modules, connections, or visual positions (not just object existence)
- Fixed initialization logic to use meaningful state detection
- Added console logging for debugging initialization path

**Visual State Capture** (`client/src/renderer/features/templates/components/builder/steps/PipelineBuilderStep.tsx`):
- Updated `handlePipelineChange` callback (lines 52-68) to capture both states
- Added `pipelineGraphRef.current.getVisualState()` call after pipeline state update
- Now calls both `onPipelineStateChange` AND `onVisualStateChange`
- Ensures node positions persist when navigating between steps

**Module Node UI Improvements** (`client/src/renderer/features/pipelines/components/module/nodes/NodeRow.tsx`):
- Changed delete button from always-rendered-but-invisible to conditional rendering
- Delete button wrapper only renders when `canRemove && onRemove` (lines 126-138 for inputs, 167-179 for outputs)
- Label area now uses `flex-1` consistently and expands when delete button absent
- Removed complex conditional flex sizing (`flex-[2]` vs `flex-1`)

**Output Node Naming** (`client/src/renderer/features/pipelines/utils/moduleFactory.ts`):
- Updated `createPins()` to initialize output nodes with empty strings (lines 43-49)
- Input nodes still use group label (but display "Not Connected" until connected)
- Output nodes start empty for user to fill in meaningful names
- Prevents all outputs having same generic name like "Result"

### Technical Details

**Schema Migration Path**:
```typescript
// Before (templates/types.ts)
interface PipelineState {
  entry_points: Array<{ id: string; label: string; field_reference: string }>;
  modules: Array<{ instance_id: string; module_id: string; ... }>;
}

// After (types/pipelineTypes.ts) - CANONICAL
interface PipelineState {
  entry_points: EntryPoint[];  // {node_id, name, type}
  modules: ModuleInstance[];   // {module_instance_id, module_ref, ...}
  connections: NodeConnection[];
}
```

**State Persistence Flow**:
1. User builds pipeline in Step 3 → `onChange` fires → saves `pipelineState` + `visualState`
2. User navigates to Step 4 → PipelineBuilderStep unmounts (state still in parent)
3. User clicks "Back" → Step 3 remounts → `hasMeaningfulState()` returns true
4. PipelineGraph reconstructs from saved state → modules appear at exact positions

**Meaningful State Detection**:
```typescript
function hasMeaningfulState(pipelineState?, visualState?): boolean {
  return (pipelineState.modules.length > 0) ||
         (pipelineState.connections.length > 0) ||
         (Object.keys(visualState.modules).length > 0);
}
```

### Before/After Behavior

**Before**:
- Template builder used incompatible pipeline schemas
- Module drop failed due to schema mismatch
- Visual state never captured (modules lost positions)
- Delete buttons always took up space (even when hidden)
- Output nodes initialized with generic "Result" names

**After**:
- All features use canonical `types/pipelineTypes.ts` schemas ✅
- Modules can be dragged and dropped in template builder ✅
- State persists when navigating between steps ✅
- Delete buttons conditionally render (no wasted space) ✅
- Output nodes start empty (user fills in) ✅

### Errors Fixed

**Error 1: Schema Mismatch**
- Root cause: Duplicate `PipelineState` in `templates/types.ts` with wrong field names
- Fix: Removed duplicates, imported from canonical location
- Result: Module dropping now works, no type errors

**Error 2: State Not Persisting**
- Root cause: `hasMeaningfulState` checked object existence, not content
- Fix: Added proper checks for arrays/objects having data
- Result: Pipeline state properly restores when navigating back

**Error 3: Visual State Not Saved**
- Root cause: `onChange` callback only updated `pipelineState`
- Fix: Added `getVisualState()` call and `onVisualStateChange()`
- Result: Module positions now persist

**Error 4: Delete Button Space**
- Root cause: Wrapper rendered with `invisible` class (takes layout space)
- Fix: Conditional rendering (`canRemove && onRemove &&`)
- Result: Label expands to fill space when no delete button

### Next Actions
- Integrate pipeline execution into template simulate endpoint
- Test full template creation flow end-to-end
- Verify state persistence across all template builder steps
- Test with multiple extraction fields and complex pipelines

### Notes
- All TypeScript compilation successful (0 errors)
- No backend changes required (all frontend fixes)
- Template builder now fully integrated with pipeline system
- Ready for template simulate endpoint integration

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
