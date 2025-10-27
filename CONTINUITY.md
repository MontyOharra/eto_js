# Template Builder Pipeline Integration - Continuity Document

**Date**: 2025-10-26
**Branch**: server_unification
**Session Context**: Fixed template builder pipeline integration with canonical type system and state persistence

---

## Current State ✅

### What Works Now

1. **Template Builder Pipeline Integration** - Fully functional
   - Step 3 (Pipeline Builder) uses canonical pipeline types from `types/pipelineTypes.ts`
   - Entry points auto-generated from extraction fields (Step 2)
   - Entry points are NOT deletable (by design - extraction fields define them)
   - Modules can be dragged and dropped from module selector
   - State persists when navigating between steps (Step 3 → Step 4 → back to Step 3)
   - **Location**: `client/src/renderer/features/templates/components/builder/steps/PipelineBuilderStep.tsx`

2. **Pipeline State Persistence** - Working
   - Both `pipelineState` and `visualState` stored in TemplateBuilderModal parent component
   - PipelineGraph uses `onChange` callback to update parent state reactively
   - Visual state (node positions) captured via ref and updated alongside logical state
   - `usePipelineInitialization` hook checks for meaningful state vs empty structures
   - **Location**: `client/src/renderer/features/pipelines/hooks/usePipelineInitialization.ts`

3. **Schema Unification** - Complete
   - Removed duplicate `PipelineState` and `VisualState` from `features/templates/types.ts`
   - All template builder components now import from canonical `types/pipelineTypes.ts`
   - Entry points use standard `{node_id, name, type}` structure
   - Module instances use full `ModuleInstance` type with proper pin metadata
   - No more schema mismatches between features

4. **Module Node UI Improvements** - Complete
   - Delete button only renders when node is removable (`canRemove && onRemove`)
   - Label area expands to fill space when delete button is absent
   - Output nodes initialize with empty strings (user fills in names)
   - Input nodes show connected output name or "Not Connected"

5. **Pipeline Execution** - Fully functional (unchanged)
   - Standalone pipeline execution works via ExecutePipelineModal
   - Compilation, validation, execution all working
   - **Location**: `server-new/src/features/pipelines/service_execution.py`

6. **PDF Text Extraction** - Fully functional (unchanged)
   - Works in ExtractionFieldsStep with "Simulate" button
   - **Location**: `server-new/src/features/pdf_templates/service.py`

---

## What Was Fixed This Session

### 1. Schema Duplication Issue ❌ → ✅

**Problem**: Template builder had its own incompatible pipeline schemas
- `features/templates/types.ts` defined `PipelineState` with wrong field names
- Entry points had `id/label/field_reference` instead of `node_id/name/type`
- Module instances had `instance_id/module_id` instead of `module_instance_id/module_ref`
- Pin types were `string[]` instead of `string`

**Solution**:
- Removed duplicate schemas from `features/templates/types.ts`
- Updated all template imports to use `types/pipelineTypes.ts`
- Added comment directing future developers to canonical location

**Files Changed**:
- `client/src/renderer/features/templates/types.ts` - Removed duplicates
- `client/src/renderer/features/templates/api/types.ts` - Updated imports
- `client/src/renderer/features/templates/components/builder/steps/ExtractionFieldsStep.tsx` - Updated imports
- `client/src/renderer/features/templates/components/builder/steps/ExtractionFieldsStep/ExtractionFieldsSidebar.tsx` - Updated imports
- `client/src/renderer/features/templates/components/builder/TemplateBuilderModal.tsx` - Updated imports

### 2. State Persistence Issue ❌ → ✅

**Problem**: Pipeline builder couldn't drop modules and didn't persist state
- PipelineGraph initialization treated empty state objects as "has saved state"
- Visual state was never captured from graph (only pipeline state)
- Navigation between steps lost module positions

**Solution**:

**Part A - Initialization Logic** (`usePipelineInitialization.ts`):
```typescript
// Added hasMeaningfulState() function
function hasMeaningfulState(pipelineState?, visualState?): boolean {
  if (!pipelineState || !visualState) return false;

  const hasModules = pipelineState.modules.length > 0;
  const hasConnections = pipelineState.connections.length > 0;
  const hasVisualPositions = Object.keys(visualState.modules).length > 0;

  return hasModules || hasConnections || hasVisualPositions;
}
```

**Part B - Visual State Capture** (`PipelineBuilderStep.tsx`):
```typescript
const handlePipelineChange = useCallback((state: PipelineState) => {
  // Save logical state
  const stateWithEntryPoints: PipelineState = {
    ...state,
    entry_points: entryPoints,
  };
  onPipelineStateChange(stateWithEntryPoints);

  // Also save visual state using ref
  if (pipelineGraphRef.current) {
    const currentVisualState = pipelineGraphRef.current.getVisualState();
    onVisualStateChange(currentVisualState);  // ✅ NOW CAPTURED
  }
}, [entryPoints, onPipelineStateChange, onVisualStateChange]);
```

**Result**:
- First visit: Empty state → creates entry points → can drop modules
- Return visit: Has modules → reconstructs saved state → preserves positions

### 3. Module Node UI Spacing ❌ → ✅

**Problem**: Delete button wrapper always rendered with `invisible` class
- Wrapper had `flex-shrink-0` so it reserved space even when hidden
- Label couldn't expand into the empty space

**Solution**: Conditional rendering instead of hiding
```typescript
// Before
{!executionMode && (
  <div className="flex-shrink-0">  // Always rendered
    <button className={canRemove ? 'visible' : 'invisible'}> // Hidden but takes space

// After
{!executionMode && canRemove && onRemove && (  // Only renders when removable
  <div className="flex-shrink-0">
    <button onClick={onRemove}>
```

**Files Changed**:
- `client/src/renderer/features/pipelines/components/module/nodes/NodeRow.tsx`

### 4. Output Node Naming ❌ → ✅

**Problem**: Output nodes initialized with group label names
- Made all outputs have same generic names like "Result"
- User had to delete and retype for meaningful names

**Solution**: Initialize outputs with empty strings
```typescript
// moduleFactory.ts - createPins()
const defaultName = direction === 'out'
  ? ''  // Outputs start empty (user fills in)
  : (nodeGroup.min_count > 1 ? `${nodeGroup.label}_${i}` : nodeGroup.label);
```

**Files Changed**:
- `client/src/renderer/features/pipelines/utils/moduleFactory.ts`

---

## Architecture Overview

### State Flow in Template Builder

```
TemplateBuilderModal (parent)
  ├── State Storage:
  │   ├── pipelineState: PipelineState (logical structure)
  │   ├── visualState: VisualState (node positions)
  │   └── extractionFields: ExtractionField[] (from step 2)
  │
  └── Step 3: PipelineBuilderStep
      ├── Derives entry points from extractionFields
      ├── Passes to PipelineGraph via props
      │   ├── initialPipelineState (for reconstruction)
      │   ├── initialVisualState (for positions)
      │   └── entryPoints (for fresh creation)
      │
      └── Updates parent via callbacks:
          ├── onChange → updates pipelineState
          └── ref.getVisualState() → updates visualState
```

### Type System Hierarchy

```
Canonical Location: types/pipelineTypes.ts
  ├── PipelineState { entry_points, modules, connections }
  ├── VisualState { modules: {}, entryPoints: {} }
  ├── EntryPoint { node_id, name, type }
  ├── ModuleInstance (from moduleTypes.ts)
  └── NodeConnection { from_node_id, to_node_id }

Used By:
  ✅ features/pipelines/* (always used this)
  ✅ features/templates/* (NOW uses this, was using duplicates)
  ✅ pages/dashboard/pipelines/* (always used this)
```

---

## Design Principles Applied

1. **Single Source of Truth for Types**
   - One `PipelineState` definition in `types/pipelineTypes.ts`
   - All features import from this canonical location
   - No duplicates, no divergence

2. **State Ownership at Parent Level**
   - TemplateBuilderModal owns state (survives step navigation)
   - PipelineGraph is stateless from parent perspective
   - Updates flow up via `onChange` callback

3. **Meaningful State Detection**
   - Don't just check if objects exist
   - Check if they contain actual data
   - Enables proper fresh vs restore behavior

4. **Reactive Updates + Imperative Queries**
   - `onChange` for logical structure (reactive)
   - `ref.getVisualState()` for positions (imperative)
   - Both captured together for full state

5. **Conditional Rendering Over Hiding**
   - Don't render with `invisible` class
   - Use conditional rendering to remove from DOM
   - Prevents layout space reservation

---

## Files Changed This Session

### Backend
- None (all changes were frontend)

### Frontend

**Type Definitions**:
- `client/src/renderer/features/templates/types.ts` - Removed duplicate PipelineState/VisualState
- `client/src/renderer/features/templates/api/types.ts` - Import from canonical location

**Template Builder Components**:
- `client/src/renderer/features/templates/components/builder/TemplateBuilderModal.tsx` - Use canonical types
- `client/src/renderer/features/templates/components/builder/steps/PipelineBuilderStep.tsx` - Reactive updates + visual state capture
- `client/src/renderer/features/templates/components/builder/steps/ExtractionFieldsStep.tsx` - Import canonical types
- `client/src/renderer/features/templates/components/builder/steps/ExtractionFieldsStep/ExtractionFieldsSidebar.tsx` - Import canonical types

**Pipeline System**:
- `client/src/renderer/features/pipelines/hooks/usePipelineInitialization.ts` - Meaningful state detection
- `client/src/renderer/features/pipelines/components/module/nodes/NodeRow.tsx` - Conditional delete button rendering
- `client/src/renderer/features/pipelines/utils/moduleFactory.ts` - Empty output node names

---

## Testing Checklist

- [x] Template builder step 3 loads without errors
- [x] Entry points appear from extraction fields
- [x] Modules can be dragged and dropped
- [x] Modules can be connected
- [x] Navigation to step 4 and back preserves pipeline
- [x] Node positions are preserved
- [x] Delete buttons only show when removable
- [x] Labels extend when delete button absent
- [x] Output nodes start with empty names
- [x] TypeScript compilation successful (0 errors)

---

## Next Steps (Template Simulate Integration)

The template builder now works correctly with proper state management. The next phase is to integrate the full simulation flow:

### Phase 1: Design Template Testing Flow

**Questions to Answer**:
1. Should "Test Template" button:
   - Call extraction only (current behavior)
   - Call extraction + pipeline execution together
   - Keep them separate with two API calls

2. Endpoint design:
   - New endpoint `/api/pdf-templates/test`?
   - Expand existing `/simulate`?
   - Keep separate, call both from frontend?

3. Entry point value mapping:
   - Extraction returns: `{field_label: "extracted_text"}`
   - Pipeline expects: `{entry_point_name: "value"}`
   - Entry points use `field.label` as name
   - Should work automatically if extraction uses label as key

### Phase 2: Implement Clean Integration

**Backend** (`server-new/src/features/pdf_templates/service.py`):
```python
def simulate_with_pipeline(
    self,
    pdf_bytes: bytes,
    extraction_fields: List[ExtractionField],
    pipeline_state: PipelineState
) -> TemplateSimulationResult:
    # 1. Extract data from PDF
    extracted_data = self.simulate_extraction(...)

    # 2. Compile pipeline (in-memory, no DB)
    compiled_steps, pruned_pipeline = self.pipeline_service.compile_for_simulation(
        pipeline_state
    )

    # 3. Execute with extracted data as entry values
    execution_result = self.pipeline_execution_service.execute_pipeline(
        steps=compiled_steps,
        entry_values_by_name=extracted_data,
        pipeline_state=pruned_pipeline
    )

    # 4. Return combined results
    return TemplateSimulationResult(
        extraction=extracted_data,
        execution=execution_result
    )
```

**Frontend** (`TemplateBuilderModal.tsx::handleTest()`):
```typescript
// Use existing serializePipelineData() to prepare pipeline state
const serialized = serializePipelineData(pipelineState, visualState);

// Convert extraction fields (handle page number 0→1 indexing)
const fields = extractionFields.map(f => ({
  name: f.label,
  bbox: f.bbox,
  page: f.page + 1,  // Convert to 1-indexed
}));

// Call combined endpoint
const result = await simulateTemplate({
  pdfSource: pdfFile ? 'upload' : 'stored',
  pdfFileId,
  pdfFile,
  extractionFields: fields,
  pipelineState: serialized.pipeline_state
});

// Display in TestingStep
setTestResults(result);
```

---

## Git Status

**Branch**: server_unification
**Working Tree**: Modified files ready for commit
**Changes**:
- Schema unification (removed duplicates)
- State persistence fixes
- UI improvements (delete button, output names)

---

## Commands Reference

**Start Backend**:
```bash
cd server-new
python main.py
```

**Start Frontend**:
```bash
cd client
npm run dev
```

**Test Template Builder**:
1. Navigate to PDF Templates
2. Click "Create Template" or select PDF
3. Complete Step 1 (Signature Objects)
4. Complete Step 2 (Extraction Fields)
5. Build pipeline in Step 3
6. Verify modules can be dropped
7. Navigate to Step 4 and back
8. Verify pipeline state persists
