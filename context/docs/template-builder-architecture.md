# Template Builder Architecture Documentation

## Overview

The template builder modal is a multi-step wizard for creating extraction templates. It manages PDF signature object identification, extraction field definition, and pipeline construction for data transformation.

## Component Hierarchy

```
TemplateBuilderModal (Root - State Container)
├── SignatureObjectsStep (Step 1: PDF object identification)
├── ExtractionFieldsStep (Step 2: Draw extraction boxes)
├── PipelineBuilderStep (Step 3: Build transformation pipeline)
│   └── PipelineGraph (Visual pipeline editor)
│       └── usePipelineInitialization (Mount logic)
└── TestingStep (Step 4: Test template)
```

## State Management

### TemplateBuilderModal State (client/src/renderer/features/templates/components/builder/TemplateBuilderModal.tsx)

**Source of Truth**: This component holds all persistent state across step navigation.

```typescript
// Template metadata
const [templateName, setTemplateName] = useState<string>('');
const [templateDescription, setTemplateDescription] = useState<string>('');

// PDF state
const [pdfFile, setPdfFile] = useState<File | null>(null);
const [pdfFileId, setPdfFileId] = useState<number | null>(null);
const [pdfUrl, setPdfUrl] = useState<string>('');
const [pdfObjects, setPdfObjects] = useState<any>(null);

// Signature objects (identified PDF elements)
const [signatureObjects, setSignatureObjects] = useState<{
  text_words: any[];
  text_lines: any[];
  graphic_rects: any[];
  graphic_lines: any[];
  graphic_curves: any[];
  images: any[];
  tables: any[];
}>({...});

// Extraction fields (user-drawn boxes)
const [extractionFields, setExtractionFields] = useState<ExtractionField[]>([]);

// Pipeline state (logical structure)
const [pipelineState, setPipelineState] = useState<PipelineState>({
  entry_points: [],
  modules: [],
  connections: [],
});

// Visual state (UI positions)
const [visualState, setVisualState] = useState<VisualState>({
  modules: {},
  entryPoints: {},
});

// PDF viewer state
const [pdfScale, setPdfScale] = useState<number>(1.0);
const [pdfCurrentPage, setPdfCurrentPage] = useState<number>(1);

// Navigation
const [currentStep, setCurrentStep] = useState<'signature-objects' | 'extraction-fields' | 'pipeline' | 'testing'>('signature-objects');
```

### Data Flow on Save

```
User clicks "Create Template"
  ↓
TemplateBuilderModal.handleCreateTemplate()
  ↓
Sends to backend:
  - templateName
  - templateDescription
  - pdfFileId
  - extractionFields
  - signatureObjects
  - pipelineState (includes entry_points, modules, connections)
  - visualState (includes modules positions, entryPoints positions)
  ↓
Backend stores in database
```

## Current Issues

### Issue 1: Entry Point Management Split Across Components

**Current Flow**:
```
ExtractionFieldsStep (user creates extraction fields)
  ↓ extractionFields prop passed down
PipelineBuilderStep (converts fields → entry points via useMemo)
  ↓ entryPoints derived
PipelineGraph (renders entry points as fake modules)
  ↓ onChange callback
Parent state updated
```

**Problem**: Entry point creation is reactive in PipelineBuilderStep, but entry point state updates happen through PipelineGraph onChange. This creates timing issues and multiple sources of truth.

**Code Location**: `PipelineBuilderStep.tsx:30-36`
```typescript
const entryPoints: EntryPoint[] = useMemo(() => {
  return extractionFields.map((field) => ({
    node_id: `entry_${field.name}`,
    name: field.name,
    type: 'str',
  }));
}, [extractionFields]);
```

### Issue 2: "Meaningful State" Check Creates Unpredictability

**Current Logic**: `usePipelineInitialization.ts:60-68`
```typescript
function hasMeaningfulState(pipelineState?: PipelineState): boolean {
  if (!pipelineState) return false;
  return (
    (pipelineState.modules && pipelineState.modules.length > 0) ||
    (pipelineState.connections && pipelineState.connections.length > 0) ||
    (pipelineState.entry_points && pipelineState.entry_points.length > 0)
  );
}
```

**Problem**: When entry points exist but no modules, this returns `true`, but when only entry points change, `hasMeaningfulState()` doesn't re-evaluate because it's not reactive. The initialization hook has a `hasInitializedRef` that prevents re-initialization, so entry point changes don't trigger state reconstruction.

**Code Location**: `usePipelineInitialization.ts:94-111`
```typescript
useEffect(() => {
  if (hasInitializedRef.current) {
    console.log('[usePipelineInitialization] Already initialized, skipping');
    return;
  }

  if (hasMeaningfulState(initialPipelineState) && initialVisualState) {
    console.log('[usePipelineInitialization] Reconstructing from saved state');
    const reconstructed = reconstructPipeline(...);
    setNodes(reconstructed.nodes);
    setEdges(reconstructed.edges);
  } else {
    console.log('[usePipelineInitialization] Creating fresh entry points');
    const entryNodes = createEntryPointNodes(entryPoints, initialVisualState);
    setNodes(entryNodes);
    setEdges([]);
  }

  hasInitializedRef.current = true;
}, []);
```

### Issue 3: Visual State Updates Too Broad

**Current Implementation**: Every pipeline change triggers full serialization via onChange callback.

**Code Location**: `PipelineGraph.tsx:518-530`
```typescript
const handleNodesChange = useCallback(
  (changes: NodeChange[]) => {
    setNodes((nds) => {
      const updatedNodes = applyNodeChanges(changes, nds);

      // Trigger onChange with full pipeline state
      if (onChange) {
        onChange(serializeToPipelineState(updatedNodes, edges));
      }

      return updatedNodes;
    });
  },
  [edges, onChange]
);
```

**Problem**: Node drag, node add, node delete ALL trigger the same onChange. Visual state (positions) should only update on drag/drop, not on structural changes.

### Issue 4: Visual State Structure Nested

**Current Structure**:
```typescript
type VisualState = {
  modules: Record<string, { x: number; y: number }>;
  entryPoints: Record<string, { x: number; y: number }>;
};
```

**Problem**: Separating modules and entry points creates complexity in serialization logic and lookup.

**Code Location**: `serialization.ts:53-69`
```typescript
export function serializeToVisualState(nodes: Node[]): VisualState {
  const modules: Record<string, { x: number; y: number }> = {};
  const entryPoints: Record<string, { x: number; y: number }> = {};

  nodes.forEach((node) => {
    if (node.type === 'module' && !node.data.isEntryPoint) {
      modules[node.id] = { x: node.position.x, y: node.position.y };
    } else if (node.data.isEntryPoint && node.data.entryPoint) {
      const entryPoint = node.data.entryPoint as EntryPoint;
      entryPoints[entryPoint.node_id] = { x: node.position.x, y: node.position.y };
    }
  });

  return { modules, entryPoints };
}
```

## Entry Point Positioning Logic

**Current Algorithm**: `PipelineGraph.tsx:180-208`

Entry points are positioned to the LEFT of the leftmost element (modules or other entry points):

1. Collect all existing positions from visualState (modules + entry points)
2. Find leftmost X coordinate
3. Place new entry points 250px to the left
4. Space multiple entry points horizontally by 200px

**Code**:
```typescript
// Collect all positions
const allPositions: { x: number; y: number }[] = [];
if (initialVisualState?.modules) {
  Object.values(initialVisualState.modules).forEach(pos => allPositions.push(pos));
}
if (initialVisualState?.entryPoints) {
  Object.values(initialVisualState.entryPoints).forEach(pos => allPositions.push(pos));
}

// Calculate starting position
let startX = 50;
let startY = 50;

if (allPositions.length > 0) {
  const leftmostX = Math.min(...allPositions.map((p) => p.x));
  const leftmostElement = allPositions.find((p) => p.x === leftmostX);
  const leftmostY = leftmostElement ? leftmostElement.y : 50;

  startX = leftmostX - 250;
  startY = leftmostY;
}

// Create entry point nodes
const existingEntryPointCount = updatedNodes.filter(
  (n) => n.data.moduleInstance?.module_ref === 'entry_point:1.0.0'
).length;

const newNodes = entriesAdded.map((ep, index) => {
  const posX = startX + (existingEntryPointCount + index) * 200;
  const posY = startY;
  // ...
});
```

## Entry Point Representation

Entry points are rendered as fake module nodes:

**Code Location**: `PipelineGraph.tsx:209-265`

```typescript
const fakeModuleInstance: ModuleInstance = {
  node_id: ep.node_id,
  module_ref: 'entry_point:1.0.0', // Special identifier
  params: {},
};

const fakeTemplate: ModuleTemplate = {
  module_ref: 'entry_point:1.0.0',
  title: ep.name,
  description: `Entry point for ${ep.name}`,
  color: '#9333ea', // Purple
  // ... rest of module template structure
};

const newNode: Node = {
  id: ep.node_id,
  type: 'module',
  position: { x: posX, y: posY },
  data: {
    moduleInstance: fakeModuleInstance,
    template: fakeTemplate,
    isEntryPoint: true,  // Flag for serialization
    entryPoint: ep,      // Original entry point data
  },
};
```

## Serialization Functions

### serializeToPipelineState (client/src/renderer/types/pipelineUtils/serialization.ts:11-51)

Extracts logical pipeline structure from React Flow nodes/edges.

```typescript
export function serializeToPipelineState(nodes: Node[], edges: Edge[]): PipelineState {
  const modules: ModuleInstance[] = [];
  const entry_points: EntryPoint[] = [];

  nodes.forEach((node) => {
    if (node.type === 'module') {
      const moduleInstance = node.data.moduleInstance as ModuleInstance;

      if (moduleInstance.module_ref === 'entry_point:1.0.0') {
        // Extract entry point
        const entryPoint = node.data.entryPoint as EntryPoint;
        entry_points.push(entryPoint);
      } else {
        // Regular module
        modules.push(moduleInstance);
      }
    }
  });

  // Convert edges to connections
  const connections: Connection[] = edges.map((edge) => ({
    source_node_id: edge.source,
    source_param: edge.sourceHandle || '',
    target_node_id: edge.target,
    target_param: edge.targetHandle || '',
  }));

  return { entry_points, modules, connections };
}
```

### serializeToVisualState (client/src/renderer/types/pipelineUtils/serialization.ts:53-69)

Extracts UI positions from React Flow nodes.

```typescript
export function serializeToVisualState(nodes: Node[]): VisualState {
  const modules: Record<string, { x: number; y: number }> = {};
  const entryPoints: Record<string, { x: number; y: number }> = {};

  nodes.forEach((node) => {
    if (node.type === 'module' && !node.data.isEntryPoint) {
      modules[node.id] = { x: node.position.x, y: node.position.y };
    } else if (node.data.isEntryPoint && node.data.entryPoint) {
      const entryPoint = node.data.entryPoint as EntryPoint;
      entryPoints[entryPoint.node_id] = { x: node.position.x, y: node.position.y };
    }
  });

  return { modules, entryPoints };
}
```

## Imperative API via Ref

PipelineGraph exposes methods via `useImperativeHandle`:

**Code Location**: `PipelineGraph.tsx:107-125`

```typescript
useImperativeHandle(ref, () => ({
  getPipelineState: () => {
    return serializeToPipelineState(nodes, edges);
  },
  getVisualState: () => {
    return serializeToVisualState(nodes);
  },
  getNodes: () => nodes,
  getEdges: () => edges,
  setNodes: (newNodes: Node[]) => {
    setNodes(newNodes);
  },
  setEdges: (newEdges: Edge[]) => {
    setEdges(newEdges);
  },
}), [nodes, edges]);
```

## Mount/Unmount Pattern

**Current Implementation**: `TemplateBuilderModal.tsx:507-564`

Steps are conditionally rendered (mount/unmount on navigation):

```typescript
{currentStep === 'signature-objects' && (
  <div style={{ height: '100%' }}>
    <SignatureObjectsStep ... />
  </div>
)}
{currentStep === 'extraction-fields' && (
  <div style={{ height: '100%' }}>
    <ExtractionFieldsStep ... />
  </div>
)}
{currentStep === 'pipeline' && (
  <div style={{ height: '100%' }}>
    <PipelineBuilderStep ... />
  </div>
)}
```

**Problem**: When PipelineBuilderStep unmounts, PipelineGraph's React Flow internal state is destroyed. On re-mount, initialization must reconstruct from parent state, but timing issues prevent entry points from being captured in visual state.

## Identified Root Causes

### Why Entry Points Not Saving Positions:

1. **Dynamic sync disabled**: Entry point sync logic (lines 112-302 in PipelineGraph.tsx) is commented out to avoid infinite loops
2. **Initialization runs once**: `hasInitializedRef` prevents re-initialization when entry points change
3. **onChange timing**: Parent state updated via onChange callback, but entry point additions don't reliably trigger onChange
4. **Mount/unmount**: Navigating away destroys React Flow state, navigating back reconstructs but visual state isn't populated

### Why Infinite Loops Occurred:

1. **Attempted fix**: Added useEffect to trigger onChange after entry points synced (PipelineGraph.tsx:298-316, now removed)
2. **Loop mechanism**: onChange → parent updates → re-render → useEffect triggers → onChange → repeat
3. **Root issue**: Reactive updates across component boundaries without proper memoization/equality checks

## File Reference Map

| File | Purpose | Key Functions/Hooks |
|------|---------|---------------------|
| `TemplateBuilderModal.tsx` | Root state container | State management, step navigation, save handler |
| `PipelineBuilderStep.tsx` | Adapter layer | Converts extractionFields → entryPoints, wraps PipelineGraph |
| `PipelineGraph.tsx` | Visual editor | React Flow integration, node/edge management, ref API |
| `usePipelineInitialization.ts` | Mount logic | Decides between reconstructing state vs creating fresh, positioning algorithm |
| `serialization.ts` | State conversion | serializeToPipelineState, serializeToVisualState |
| `ExtractionFieldsStep.tsx` | Extraction field drawing | User draws boxes on PDF, manages extraction fields array |
| `ModuleHeader.tsx` | Module UI component | Renders module title bar, hides delete button for entry points |

## Design Principles for Refactor

Based on user requirements:

1. **Entry point state updates in ExtractionFieldsStep**: When user adds/removes extraction field, immediately update entry_points in pipelineState
2. **Remove meaningful state check**: Always reconstruct from parent state predictably
3. **Target visual state updates to drag/drop**: Only update visual state on specific drag end events, not all changes
4. **Flatten visual state structure**: Change to `{"node_id": {x: int, y: int}}` for both modules and entry points

## Type Definitions

### ExtractionField
```typescript
interface ExtractionField {
  name: string;
  description: string | null;
  page: number;
  bbox: [number, number, number, number];
}
```

### EntryPoint
```typescript
interface EntryPoint {
  node_id: string;
  name: string;
  type: string;
}
```

### PipelineState
```typescript
interface PipelineState {
  entry_points: EntryPoint[];
  modules: ModuleInstance[];
  connections: Connection[];
}
```

### VisualState (Current)
```typescript
interface VisualState {
  modules: Record<string, { x: number; y: number }>;
  entryPoints: Record<string, { x: number; y: number }>;
}
```

### VisualState (Proposed)
```typescript
type VisualState = Record<string, { x: number; y: number }>;
```
