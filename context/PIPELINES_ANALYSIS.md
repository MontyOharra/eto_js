# Pipelines Feature Analysis

## Purpose
This document tracks our analysis of all hooks and utility files in the `client/src/renderer/features/pipelines` directory to understand their purpose, identify issues, and plan refactoring.

---

## Hooks Analysis (`hooks/`)

### ✅ useConnectionManager.ts
**Status**: Analyzed and Approved (needs minor cleanup)

**Purpose**: Manages all connection (edge) operations in the pipeline graph - creation, deletion, and type propagation for connections between module pins.

**Key Functions**:
- `createConnection` - Create connection with type validation and propagation
- `deleteConnection` - Delete single connection by edge ID
- `deleteConnectionsForPin` - Delete all connections for a specific pin
- `deleteConnectionsForModule` - Delete all connections for a module

**Notes**:
- Good use of hook pattern since it depends on nodes/edges state
- Uses useCallback appropriately for memoization
- Needs import cleanup after reorganization

---

### ⏳ useModuleOperations.ts
**Status**: Pending Analysis

**Purpose**: TBD

---

### ⏳ useNodeUpdates.ts
**Status**: Pending Analysis

**Purpose**: TBD

---

### ⏳ usePipelineInitialization.ts
**Status**: Pending Analysis

**Purpose**: TBD

---

### ⏳ usePipelineValidation.ts
**Status**: Pending Analysis

**Purpose**: TBD

---

## Utils Analysis (`utils/`)

### ✅ autoLayout.ts
**Status**: DELETED

**Purpose**: Auto-layout utility for executed pipeline viewer (Sugiyama framework)

**Functions**:
- `calculateLayers` (private)
- `autoLayoutNodes` ❌ **DELETED**
- `applyAutoLayout` ❌ **DELETED**

**Reason for Deletion**: No references found in codebase. Replaced by `layeredLayout.ts`.

---

### ✅ edgeUtils.ts
**Status**: CLEANED UP

**Purpose**: Functions for edge creation, coloring, and management

**Functions**:
- `getTypeColor` ✅ Used (multiple locations)
- `getEdgeColor` ✅ Used (via updateEdgeColors)
- `updateEdgeColors` ✅ Used (useConnectionManager)
- `createStyledEdge` ✅ Used (useConnectionManager)
- `findConnectedEdges` ✅ Used (imported by useConnectionManager)
- `findEdgeBetweenPins` ❌ **DELETED**
- `removeModuleEdges` ❌ **DELETED**
- `removePinEdges` ✅ Used (useConnectionManager)
- `createEdgesFromConnections` ✅ Used (ExecutedPipelineGraph)

**Cleanup Complete**: Removed 2 unused functions

---

### ⏳ idGenerator.ts
**Status**: Partial Deletion Needed

**Purpose**: Generates short, readable IDs for pipeline elements

**Functions**:
- `generateRandomString` (private)
- `generateModuleId` ✅ Used (moduleFactory)
- `generateEntryPointId` ✅ Used (pages/dashboard/pipelines/create.tsx)
- `generateNodeId` ✅ Used (moduleFactory)

**Actions Needed**: Keep all functions - all are used

---

### ✅ layeredLayout.ts
**Status**: Keep All Functions

**Purpose**: Layered graph layout algorithm (Sugiyama-style) for pipeline visualization

**Functions**:
- `calculateLayers` (private)
- `groupByLayer` (private)
- `calculatePositions` (private)
- `applyLayeredLayout` ✅ Used (ExecutedPipelineViewer)

**Notes**: Primary layout algorithm, replaces autoLayout.ts

---

### ✅ moduleFactory.ts
**Status**: Keep All Functions

**Purpose**: Functions for creating and manipulating module instances

**Functions**:
- `getDefaultForType` (private)
- `initializeConfig` (private)
- `createPins` (private)
- `createModuleInstance` ✅ Used (useModuleOperations)
- `addPinToModule` ✅ Used (useModuleOperations)
- `removePinFromModule` ✅ Used (useModuleOperations)
- `updatePinInModule` ✅ Used (useNodeUpdates)
- `updateModuleConfig` ✅ Used (useModuleOperations)

**Notes**: Core module creation and manipulation logic

---

### ✅ moduleUtils.ts
**Status**: Keep All Functions

**Purpose**: Module utility functions and constants

**Functions**:
- `TYPE_COLORS` (constant) ✅ Used (multiple locations)
- `getTextColor` ✅ Used (ModuleHeader component)
- `groupNodesByIndex` ✅ Used (ModuleNodes component)

**Notes**: All functions actively used in rendering

---

### ✅ pipelineSerializer.ts
**Status**: CLEANED UP

**Purpose**: Serialization utilities for backend pipeline formats

**Functions**:
- `serializeNodePin` ❌ **DELETED** (inlined into serializePipelineData)
- `serializeModuleInstance` ❌ **DELETED** (inlined into serializePipelineData)
- `serializeEntryPoint` ❌ **DELETED** (inlined into serializePipelineData)
- `serializePipelineState` ❌ **DELETED** (inlined into serializePipelineData)
- `serializeVisualState` ❌ **DELETED** (inlined into serializePipelineData)
- `serializePipelineData` ✅ Used (pages/dashboard/pipelines/create.tsx)

**Cleanup Complete**: Consolidated all helper functions into single exported function, made internal types private

---

### ✅ serialization.ts
**Status**: Keep All Functions

**Purpose**: Convert between React Flow state and pipeline state format

**Functions**:
- `serializeToPipelineState` ✅ Used (PipelineGraph)
- `serializeToVisualState` ✅ Used (PipelineGraph)

**Notes**: Core serialization for PipelineGraph component

---

### ✅ typeSystem.ts
**Status**: CLEANED UP

**Purpose**: Type constraint validation and propagation

**Functions**:
- `getTypeIntersection` ✅ Used (internally)
- `getAllPins` ✅ **MADE PRIVATE** (only used internally by findPin)
- `findPin` ✅ Used (useConnectionManager, PipelineGraph)
- `getPinsWithTypeVar` ✅ Used (internally and useNodeUpdates)
- `getEffectiveAllowedTypes` ✅ Used (PipelineGraph)
- `validateConnection` ✅ Used (useConnectionManager)
- `calculateTypePropagation` ✅ Used (useConnectionManager, useNodeUpdates)
- `applyTypeUpdates` ✅ Used (useConnectionManager, useNodeUpdates)

**Cleanup Complete**: Made `getAllPins` a private function (removed export)

**Notes**: Core type system logic, heavily used by connection and node update hooks

---

## Summary Statistics

**Hooks**: 5 total
- ✅ Analyzed: 1
- ⏳ Pending: 4

**Utils**: 10 total (9 remaining after deletion)
- ✅ Cleaned and ready: 9
  - Deleted entirely: autoLayout.ts (1 file)
  - Cleaned up: edgeUtils.ts, pipelineSerializer.ts, typeSystem.ts (3 files)
  - Keep as-is: idGenerator.ts, layeredLayout.ts, moduleFactory.ts, moduleUtils.ts, serialization.ts (5 files)

**Total Cleanup Actions Completed**:
- ❌ 1 entire file deleted (autoLayout.ts)
- ❌ 9 unused functions removed
- 🔒 1 function made private
- ♻️ 5 helper functions inlined

**Remaining Analysis**: 4 hooks + detailed analysis of utils

---

---

## Type System Alignment (Backend vs Frontend)

### Purpose
Align frontend types with backend Pydantic schemas to eliminate unnecessary transformations and maintain single source of truth.

### Backend Ground Truth (Python/Pydantic)

**Node Structure** (`server/src/api/schemas/pipelines.py`):
```python
class Node(BaseModel):
    node_id: str
    type: str
    name: str
    position_index: int
    group_index: int
```

**EntryPoint Structure**:
```python
class EntryPoint(BaseModel):
    node_id: str
    name: str  # NO type field
```

**ModuleInstance Structure**:
```python
class ModuleInstance(BaseModel):
    module_instance_id: str
    module_ref: str  # e.g., "text_cleaner:1.0.0"
    config: Dict[str, Any]
    inputs: List[Node]
    outputs: List[Node]
    # NO module_kind field - parse from module_ref
```

**VisualState Structure**:
```python
VisualState: TypeAlias = Dict[str, Position]  # Flat structure
```

**Module Catalog Structure** (`server/src/api/schemas/modules.py`):
```python
class Module(BaseModel):
    id: str
    version: str
    name: str
    description: Optional[str]
    module_kind: str
    meta: Dict[str, Any]  # Contains io_shape
    config_schema: Dict[str, Any]
    color: str
    category: str
```

### Frontend Mismatches Found

1. **✅ NodePin Extra Fields** - CORRECT (UI enhancements)
   - Frontend adds: `direction`, `label`, `type_var`, `allowed_types`
   - These are UI-only fields reconstructed from module template
   - Backend sends minimal Node, frontend enriches for type system

2. **❌ ModuleInstance.module_kind** - WRONG (redundant)
   - Backend doesn't send this field
   - Can be parsed from `module_ref` (e.g., "text_cleaner:1.0.0" → "transform")
   - **Action**: Removed from ModuleInstance type

3. **✅ EntryPoint.type** - CORRECT (UI enhancement)
   - Backend EntryPoint has no type field
   - Frontend adds it for UI type system
   - Needed for connection validation

4. **❌ VisualStateDTO Structure** - WRONG
   - Frontend had: `{ positions: Record<string, Position> }`
   - Backend sends: `Record<string, Position>` (flat)
   - **Action**: Changed to flat structure

5. **❌ Module Meta Structure** - WRONG
   - Frontend tried to strongly type `meta.inputs` and `meta.outputs`
   - Backend sends `meta: Dict[str, Any]`
   - **Action**: Changed to `Record<string, any>`, frontend parses io_shape

6. **❌ Fake Transformations** - WRONG
   - Frontend had fake `visual_state.entry_points` transformation
   - This field doesn't exist in backend
   - **Action**: Removed all fake transformations from api/hooks.ts

### Changes Implemented

#### 1. `client/src/renderer/features/pipelines/types.ts`
- ❌ Removed `module_kind` field from ModuleInstance
- ❌ Removed `InstanceNodePin` type (used BackendNodePin in serializer)
- ❌ Removed `BackendEntryPoint` type (moved to serializer)

#### 2. `client/src/renderer/features/pipelines/api/types.ts`
- ✅ Fixed VisualStateDTO to be flat: `Record<string, PositionDTO>`
- ✅ Fixed ModuleDTO to have `meta: Record<string, any>`
- ✅ Removed strongly-typed ModuleCatalogItemDTO

#### 3. `client/src/renderer/features/pipelines/api/hooks.ts`
- ❌ Removed fake visual_state.entry_points transformation (4 locations):
  - `getPipeline` (lines 94-96)
  - `createPipeline` (lines 114-116)
  - `updatePipeline` (lines 135-137)
  - `validatePipeline` (lines 169-171)

#### 4. `client/src/renderer/features/pipelines/utils/pipelineSerializer.ts`
- ✅ Defined BackendNodePin, BackendEntryPoint, BackendModuleInstance locally
- ✅ Updated to serialize without module_kind field
- ✅ All helper functions already inlined (from previous cleanup)

#### 5. `client/src/renderer/features/pipelines/index.ts`
- ❌ Removed BackendEntryPoint from exports

### Strong Typing Approach for io_shape

**Goal**: Keep strongly typed io_shape while accepting Dict from backend

**Current Approach**:
- Backend sends `meta: Dict[str, Any]`
- Frontend has types: `IOShape`, `NodeGroup`, `IOSideShape`
- Frontend parses meta.io_shape into strongly typed structure
- Module templates contain fully typed io_shape for UI
- No runtime validation yet (optional future enhancement)

**Type Definitions** (`client/src/renderer/features/modules/types.ts`):
```typescript
export interface IOShape {
  inputs: IOSideShape;
  outputs: IOSideShape;
}

export interface IOSideShape {
  nodes: NodeGroup[];
  rules: NodeTypeRule[];
}

export interface NodeGroup {
  label: string;
  min_count: number;
  max_count: number | null;
  type_rules: NodeTypeRule[];
}
```

### Type System Philosophy

**Backend**: Sends minimal data, validates structure
**Frontend**: Enriches with UI state, reconstructs from templates
**Serialization**: Strips UI-only fields before sending to backend

**UI-Only Fields** (never sent to backend):
- NodePin: `direction`, `label`, `type_var`, `allowed_types`
- EntryPoint: `type`
- ModuleInstance: ~~`module_kind`~~ (removed)

**Reconstruction Flow**:
1. Backend sends Node with basic fields
2. Frontend looks up module template by module_ref
3. Frontend reconstructs NodePin with UI fields from template.io_shape
4. Type system uses reconstructed NodePin for validation

---

## Next Steps
1. Analyze utils files first (per user request)
2. Continue with remaining hooks
3. Identify refactoring opportunities
4. Document dependencies between files
