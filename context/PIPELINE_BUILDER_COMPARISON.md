# Pipeline Builder Comparison: Create Page vs Template Builder

**Purpose**: Document all differences in how the pipeline builder works between the two implementations.

---

## Overview

**Pipeline Create Page**: `pages/dashboard/pipelines/create.tsx`
**Template Builder Pipeline Step**: `features/templates/components/builder/steps/PipelineBuilderStep.tsx`

Both use the same `PipelineGraph` component but with different initialization patterns and state management.

---

## Key Differences

### 1. **Entry Point Creation**

**Pipeline Create Page**:
```typescript
// Entry points created via modal (user defines names)
const handleEntryPointsConfirm = (points: Array<{ name: string }>) => {
  const newEntryPoints: EntryPoint[] = points.map((p) => ({
    node_id: generateEntryPointId(),
    name: p.name,
    type: 'str', // ✅ Always 'str'
  }));
  setEntryPoints(newEntryPoints);
};

// Entry points are user-defined and permanent
```

**Template Builder**:
```typescript
// Entry points derived from extraction fields (auto-generated)
const entryPoints: EntryPoint[] = useMemo(() => {
  return extractionFields.map((field) => ({
    node_id: `entry_${field.field_id}`,
    name: field.label,
    type: 'str', // ✅ Always 'str'
  }));
}, [extractionFields]);

// Entry points change when extraction fields change
```

**Impact**:
- Create page: Entry points are static after modal confirmation
- Template builder: Entry points are reactive to extraction fields

---

### 2. **State Storage Location**

**Pipeline Create Page**:
```typescript
// State stored in local component state
const [entryPoints, setEntryPoints] = useState<EntryPoint[]>([]);
const pipelineGraphRef = useRef<PipelineGraphRef>(null);

// Retrieved imperatively when needed
const handleSave = async () => {
  const pipelineState = pipelineGraphRef.current.getPipelineState();
  const visualState = pipelineGraphRef.current.getVisualState();
  // ...
};
```

**Template Builder**:
```typescript
// State stored in parent component (TemplateBuilderModal)
// Passed down as props
interface PipelineBuilderStepProps {
  pipelineState: PipelineState;
  visualState: VisualState;
  onPipelineStateChange: (state: PipelineState) => void;
  onVisualStateChange: (state: VisualState) => void;
}

// Updated reactively via callbacks
const handlePipelineChange = useCallback((state: PipelineState) => {
  const stateWithEntryPoints = { ...state, entry_points: entryPoints };
  onPipelineStateChange(stateWithEntryPoints);

  // Also capture visual state
  if (pipelineGraphRef.current) {
    const currentVisualState = pipelineGraphRef.current.getVisualState();
    onVisualStateChange(currentVisualState);
  }
}, [entryPoints, onPipelineStateChange, onVisualStateChange]);
```

**Impact**:
- Create page: Pull pattern (imperative retrieval via ref)
- Template builder: Push pattern (reactive updates via callbacks)

---

### 3. **PipelineGraph Props**

**Pipeline Create Page**:
```typescript
<PipelineGraph
  ref={pipelineGraphRef}
  moduleTemplates={moduleTemplates}
  selectedModuleId={selectedModuleId}
  onModulePlaced={handleModulePlaced}
  onChange={setCurrentPipelineState}  // ✅ For auto-validation only
  viewOnly={false}
  entryPoints={entryPoints}
  // ❌ NO initialPipelineState
  // ❌ NO initialVisualState
/>
```

**Template Builder**:
```typescript
<PipelineGraph
  ref={pipelineGraphRef}
  moduleTemplates={modules}
  selectedModuleId={selectedModuleId}
  onModulePlaced={handleModulePlaced}
  onChange={handlePipelineChange}  // ✅ Syncs to parent state
  initialPipelineState={pipelineState}  // ✅ For reconstruction
  initialVisualState={visualState}      // ✅ For reconstruction
  viewOnly={false}
  entryPoints={entryPoints}
/>
```

**Impact**:
- Create page: Always starts fresh (no reconstruction)
- Template builder: Can reconstruct from saved state

---

### 4. **Pipeline State Tracking**

**Pipeline Create Page**:
```typescript
// Tracks current state for validation only
const [currentPipelineState, setCurrentPipelineState] = useState<PipelineState | null>(null);

// Auto-validation hook
const { isValid, error: validationError, isValidating } = usePipelineValidation(currentPipelineState);

// Save button disabled based on validation
<button disabled={isSaving || !isValid || isValidating}>
  Save Pipeline
</button>
```

**Template Builder**:
```typescript
// State lives in parent, passed down via props
// No validation (yet) - user can proceed to next step regardless
// State persists when navigating between steps
```

**Impact**:
- Create page: Has auto-validation preventing invalid saves
- Template builder: No validation (can save invalid pipelines)

---

### 5. **Module Loading**

**Pipeline Create Page**:
```typescript
// Loads modules once on mount
useEffect(() => {
  async function loadModules() {
    try {
      const response = await getModules();
      setModuleTemplates(response.modules);
    } catch (err) {
      console.error('Failed to load module templates:', err);
    }
  }
  loadModules();
}, []); // ✅ Empty deps - runs once
```

**Template Builder**:
```typescript
// Loads modules on mount, but getModules is in deps
useEffect(() => {
  async function loadModules() {
    try {
      const response = await getModules();
      setModules(response.modules);
    } catch (error) {
      console.error('Failed to load modules:', error);
      setModules([]);
    }
  }
  loadModules();
}, [getModules]); // ⚠️ getModules is a dependency (could re-run)
```

**Impact**:
- Create page: Guaranteed single load
- Template builder: Could reload if `getModules` reference changes

---

### 6. **Entry Point Handling in State**

**Pipeline Create Page**:
```typescript
// Entry points passed separately to PipelineGraph
// Not included in change callback
<PipelineGraph
  entryPoints={entryPoints}
  onChange={setCurrentPipelineState}  // State doesn't include entry points
/>

// When saving, entry points are in graph state via serialization
const pipelineState = pipelineGraphRef.current.getPipelineState();
// pipelineState.entry_points is populated by graph
```

**Template Builder**:
```typescript
// Entry points manually merged into state in callback
const handlePipelineChange = useCallback((state: PipelineState) => {
  const stateWithEntryPoints: PipelineState = {
    ...state,
    entry_points: entryPoints,  // ✅ Explicitly merged
  };
  onPipelineStateChange(stateWithEntryPoints);
}, [entryPoints, onPipelineStateChange, onVisualStateChange]);
```

**Impact**:
- Create page: Entry points automatically included by graph serialization
- Template builder: Entry points manually merged in callback handler

---

### 7. **Visual State Capture**

**Pipeline Create Page**:
```typescript
// Visual state only retrieved when saving
const handleSave = async () => {
  const pipelineState = pipelineGraphRef.current.getPipelineState();
  const visualState = pipelineGraphRef.current.getVisualState();  // ✅ Retrieved once
  // ...
};
```

**Template Builder**:
```typescript
// Visual state captured on every pipeline change
const handlePipelineChange = useCallback((state: PipelineState) => {
  onPipelineStateChange(stateWithEntryPoints);

  // Capture visual state reactively
  if (pipelineGraphRef.current) {
    const currentVisualState = pipelineGraphRef.current.getVisualState();
    onVisualStateChange(currentVisualState);  // ✅ Captured on every change
  }
}, [entryPoints, onPipelineStateChange, onVisualStateChange]);
```

**Impact**:
- Create page: Visual state retrieved on-demand (when saving)
- Template builder: Visual state continuously synced to parent

---

### 8. **Reconstruction Logic (usePipelineInitialization)**

**Pipeline Create Page**:
```typescript
// Never reconstructs - always starts fresh
usePipelineInitialization({
  moduleTemplates,
  // initialPipelineState: undefined  ❌
  // initialVisualState: undefined     ❌
  entryPoints,
  setNodes,
  setEdges,
});

// Always takes the "create fresh" path
```

**Template Builder**:
```typescript
// Can reconstruct from saved state
usePipelineInitialization({
  moduleTemplates,
  initialPipelineState,  // ✅ May have saved state
  initialVisualState,    // ✅ May have saved state
  entryPoints,
  setNodes,
  setEdges,
});

// Takes "reconstruct" path if hasMeaningfulState() returns true
```

**Impact**:
- Create page: Always creates entry point nodes fresh
- Template builder: Reconstructs modules if returning from another step

---

### 9. **Type Reconstruction Bug** ⚠️

This is the bug you identified:

**In `moduleFactory.createModuleInstance()` (used by create page)**:
```typescript
// Lines 29-38 in moduleFactory.ts
let allowedTypes: string[];
if (typeVar && typeParams[typeVar]) {
  const typeParamTypes = typeParams[typeVar];
  allowedTypes = typeParamTypes.length === 0 ? ALL_TYPES : typeParamTypes;  // ✅
} else {
  const directTypes = nodeGroup.typing?.allowed_types || ['str'];
  allowedTypes = directTypes.length === 0 ? ALL_TYPES : directTypes;  // ✅
}
```

**In `reconstructPins()` (used by template builder)**:
```typescript
// Lines 117-120 in usePipelineInitialization.ts
const typeVar = group.typing.type_var;
const allowedTypes = typeVar
  ? template.meta.io_shape.type_params[typeVar] || []  // ❌ No fallback to ALL_TYPES
  : group.typing.allowed_types || [];  // ❌ No fallback to ALL_TYPES
```

**Result**:
- Create page: Empty arrays become `['str', 'int', 'float', 'bool', 'datetime']` ✅
- Template builder: Empty arrays stay `[]` (no types allowed) ❌

---

## Summary Table

| Feature | Pipeline Create Page | Template Builder |
|---------|---------------------|------------------|
| Entry Points | User-defined via modal | Auto-generated from extraction fields |
| State Storage | Local component state | Parent component props |
| State Pattern | Pull (imperative via ref) | Push (reactive via callbacks) |
| Reconstruction | Never (always fresh) | Yes (from saved state) |
| Validation | Auto-validation enabled | No validation |
| Visual State | Retrieved on-demand | Continuously synced |
| Module Loading | Once on mount | With getModules dependency |
| Empty Type Arrays | Converts to ALL_TYPES ✅ | Stays empty ❌ |
| Entry Point Merge | Automatic in graph | Manual in callback |
| Initial State Props | Not passed | Passed for reconstruction |

---

## Root Causes of Differences

1. **Different Use Cases**:
   - Create page: One-time pipeline creation with validation
   - Template builder: Multi-step wizard with state persistence

2. **State Ownership**:
   - Create page: Pipeline owns its own state
   - Template builder: Parent modal owns state (survives step navigation)

3. **Lifecycle Differences**:
   - Create page: Linear flow (create → validate → save → exit)
   - Template builder: Non-linear (step 1 → 2 → 3 → 4, can go back)

4. **Reconstruction Requirements**:
   - Create page: No reconstruction needed (never unmounts until save/cancel)
   - Template builder: Must reconstruct when returning to step 3 from step 4

---

## Recommendations

### 1. **Fix Type Reconstruction Bug**
Update `reconstructPins()` in `usePipelineInitialization.ts` to match `moduleFactory.ts` logic:

```typescript
const ALL_TYPES = ['str', 'int', 'float', 'bool', 'datetime'];

const typeVar = group.typing.type_var;
let allowedTypes: string[];

if (typeVar) {
  const typeParamTypes = template.meta.io_shape.type_params[typeVar] || [];
  allowedTypes = typeParamTypes.length === 0 ? ALL_TYPES : typeParamTypes;
} else {
  const directTypes = group.typing.allowed_types || [];
  allowedTypes = directTypes.length === 0 ? ALL_TYPES : directTypes;
}
```

### 2. **Standardize Module Loading**
Use empty dependency array in template builder to match create page:

```typescript
useEffect(() => {
  async function loadModules() {
    // ...
  }
  loadModules();
}, []); // Remove getModules from deps
```

### 3. **Add Validation to Template Builder** (Future)
Consider adding the same auto-validation to template builder for consistency.

### 4. **Document State Patterns**
The two different patterns (pull vs push) are both valid for their use cases, but should be clearly documented.

---

## Testing Checklist

When fixing the type reconstruction bug, test these scenarios in both pages:

- [ ] Module with empty `type_params: { T: [] }` shows all types
- [ ] Module with empty `allowed_types: []` shows all types
- [ ] Module with specific types like `['str', 'int']` shows only those types
- [ ] Entry points are created correctly
- [ ] Connections work between modules with empty type arrays
- [ ] State persists in template builder when navigating steps
- [ ] Pipeline create page validation still works

