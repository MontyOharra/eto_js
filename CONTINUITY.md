# CONTINUITY DOCUMENT
**Last Updated**: 2025-10-27
**Session Summary**: Implemented pipeline compilation in simulate endpoint and wired up template builder test functionality

---

## What Was Accomplished This Session

### 1. Pipeline Compilation in Simulate Endpoint ✅

**Goal**: Add pipeline compilation alongside PDF extraction in the simulate endpoint, with printed output of compiled steps.

**Backend Changes:**

1. **Service Layer** (`server-new/src/features/pdf_templates/service.py`):
   - Replaced `simulate_extraction()` method with new `simulate()` method
   - New method signature: `simulate(pdf_bytes, extraction_fields, pipeline_state) -> tuple[dict, list]`
   - Added imports: `ExtractionFieldDomain`, `PipelineStateDomain`, `PipelineDefinitionStepCreate`
   - Method now performs:
     - PDF text extraction via PDF files service
     - Pipeline validation via `pipeline_service._validate_pipeline()`
     - Dead branch pruning via `pipeline_service._prune_dead_branches()`
     - Pipeline compilation via `pipeline_service._compile_pipeline()`
     - Prints extracted data and compiled steps to console
   - Returns tuple of `(extracted_data, compiled_steps)`

2. **Endpoint** (`server-new/src/api/routers/pdf_templates.py`):
   - Added imports: `convert_extraction_fields_to_domain`, `convert_dto_to_pipeline_state`, `PipelineStateDTO`
   - Updated `simulate_template()` endpoint to:
     - Convert Pydantic `ExtractionField` schemas to domain types using mapper
     - Convert `pipeline_state` dict to `PipelineStateDTO` then to domain type
     - Call new `simulate()` service method with domain types
     - Handle tuple return value `(extracted_data, compiled_steps)`
     - Updated response to show compilation success (no execution yet)

**Frontend Changes:**

1. **TemplateBuilderModal** (`client/src/renderer/features/templates/components/builder/TemplateBuilderModal.tsx`):
   - Added import: `useTemplatesApi` hook
   - Replaced mock test implementation in `handleTest()` with real API call
   - Builds FormData with:
     - `pdf_source`: "stored" or "upload"
     - `pdf_file_id` or `pdf_file`: PDF source
     - `extraction_fields`: JSON string (transforms `label` → `name` for backend)
     - `pipeline_state`: JSON string
   - Maps API response back to frontend format:
     - Backend returns data keyed by field name
     - Frontend needs data keyed by field_id
     - Transforms extraction field names back to field_ids
   - Shows error alert on failure

**Key Architecture:**
- Endpoint handles Pydantic validation and converts to domain types
- Service works only with domain types (no Pydantic or dict conversions)
- Compilation happens but execution steps remain empty (simulation mode)
- No persistence - everything runs in memory

---

### 2. Pipeline State Persistence Issue 🚧 (IN PROGRESS)

**Problem**: When user navigates away from pipeline step (step 3) and returns, the pipeline is cleared instead of being restored from saved state.

**Root Cause**: The `usePipelineInitialization` hook was not properly preserving state on component remount.

**Attempted Fixes**:

1. **First Attempt**: Split into two effects with computed `hasSavedState` - didn't work
2. **Second Attempt**: Combined into single effect with `useRef` to track initialization

**Current State** (`client/src/renderer/features/pipelines/hooks/usePipelineInitialization.ts`):
- Uses `hasInitializedRef` to prevent re-initialization
- Single effect with proper dependency array
- Waits for modules to load before initializing
- Checks `hasMeaningfulState()` to determine reconstruction vs fresh entry points
- Should reconstruct from `initialPipelineState` and `initialVisualState` when present

**Status**: User reports it's still not working - pipeline loads empty on return to step 3

**Next Steps to Debug**:
1. Check browser console logs when navigating to step 3:
   - Look for: `[usePipelineInitialization] Reconstructing from saved state:`
   - Look for: `[usePipelineInitialization] Waiting for modules to load...`
   - Look for: `[usePipelineInitialization] Creating fresh entry points:`
2. Add temporary logging in `TemplateBuilderModal` to verify `pipelineState` and `visualState` are being preserved
3. Check if `hasMeaningfulState()` is correctly detecting saved state
4. Verify `moduleTemplates` are loaded before initialization runs

---

## Files Modified This Session

### Backend Files

1. **`server-new/src/features/pdf_templates/service.py`**
   - Lines 14-24: Added imports for domain types
   - Lines 430-490: Replaced `simulate_extraction()` with `simulate()` method

2. **`server-new/src/api/routers/pdf_templates.py`**
   - Lines 23-33: Added imports for mappers and schemas
   - Lines 244-275: Updated simulate endpoint to convert types and call new service method

### Frontend Files

1. **`client/src/renderer/features/templates/components/builder/TemplateBuilderModal.tsx`**
   - Line 12: Added `useTemplatesApi` import
   - Line 83: Added `simulateTemplate` hook initialization
   - Lines 242-311: Completely rewrote `handleTest()` to call real API

2. **`client/src/renderer/features/pipelines/hooks/usePipelineInitialization.ts`**
   - Line 6: Added `useRef` import
   - Lines 264-323: Rewrote hook to use ref-based initialization tracking

---

## Current System State

### What's Working ✅
- Template builder test button calls real simulate endpoint
- PDF extraction works for both stored and uploaded PDFs
- Pipeline compilation runs successfully alongside extraction
- Compiled steps are printed to console for verification
- Frontend receives and displays extraction results
- TypeScript compiles without errors

### What's Not Working 🚧
- Pipeline state not restoring when navigating back to step 3
- User builds a pipeline, navigates away, comes back → pipeline is empty
- `pipelineState` and `visualState` should be preserved by parent component
- Initialization hook should reconstruct from these states but isn't

---

## Technical Context

### Pipeline Initialization Flow
1. User enters step 3 (`currentStep = 'pipeline'`)
2. `PipelineBuilderStep` component mounts
3. Passes `pipelineState` and `visualState` props to `PipelineGraph`
4. `PipelineGraph` passes to `usePipelineInitialization` as `initialPipelineState` and `initialVisualState`
5. Hook should detect meaningful state and reconstruct pipeline
6. Currently detecting empty state instead

### Expected Behavior
- `TemplateBuilderModal` maintains `pipelineState` and `visualState` in useState
- These states are updated via callbacks as user builds pipeline
- When user navigates away and back, these states should still contain pipeline data
- `usePipelineInitialization` should reconstruct pipeline from these states

### hasMeaningfulState Function
```typescript
function hasMeaningfulState(
  pipelineState?: PipelineState,
  visualState?: VisualState
): boolean {
  if (!pipelineState || !visualState) return false;

  const hasModules = pipelineState.modules.length > 0;
  const hasConnections = pipelineState.connections.length > 0;
  const hasVisualPositions = Object.keys(visualState.modules).length > 0;

  return hasModules || hasConnections || hasVisualPositions;
}
```

---

## Next Session TODO

### Immediate Priority: Fix Pipeline State Persistence

**Debug Steps**:
1. Add console.log in `TemplateBuilderModal` before rendering `PipelineBuilderStep`:
   ```typescript
   console.log('[TemplateBuilderModal] Rendering pipeline step with state:', {
     pipelineState,
     visualState,
     hasModules: pipelineState.modules.length,
     hasVisualPositions: Object.keys(visualState.modules).length,
   });
   ```

2. Check if states are actually being preserved in parent or getting reset

3. Verify `usePipelineInitialization` logs show correct detection

**Potential Issues**:
- Parent component might be resetting states when step changes
- `useRef` might not be resetting properly on unmount
- `moduleTemplates` might not be ready when effect runs
- Prop references might be changing causing re-initialization

**Possible Solutions**:
- Add key prop to `PipelineBuilderStep` based on `currentStep` to force remount
- Store pipeline state in parent's ref instead of state
- Use `useEffect` cleanup to reset `hasInitializedRef`
- Add more defensive checks in initialization hook

### After Pipeline Persistence is Fixed

**Next Feature: Pipeline Execution**
- Currently only compilation happens in simulate endpoint
- Need to add actual pipeline execution using compiled steps
- Execute each step in order using entry values from extracted data
- Collect outputs and action data
- Return execution results in response

---

## Important Notes

- **Do not create MD files unless user specifies**
- **Do not push to remote unless user specifies**
- **No imports inside functions** - all imports at top level
- **Config validation should happen in existing module validation functions**
- **Never run `npm run dev`** - user handles testing and server execution

---

## Git Status Before Commit

**Modified Files:**
- `server-new/src/features/pdf_templates/service.py`
- `server-new/src/api/routers/pdf_templates.py`
- `client/src/renderer/features/templates/components/builder/TemplateBuilderModal.tsx`
- `client/src/renderer/features/pipelines/hooks/usePipelineInitialization.ts`

**Branch**: `server_unification`

**Main Branch**: `master`

---

## Environment

- Working Directory: `C:\Users\Owner\Software_Projects\eto_js`
- Platform: Windows (MINGW64_NT-10.0-26100)
- Date: 2025-10-27
- Backend: Python FastAPI
- Frontend: React + TypeScript + React Flow
- Database: PostgreSQL (via connection manager)
