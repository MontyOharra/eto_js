# ExecutedPipelineViewer Development - Session Continuity Document

## Session Overview
**Date**: 2025-11-06
**Status**: Viewer functional with basic visualization, ready for edge component implementation
**Primary Goal**: Build ExecutedPipelineViewer from scratch to visualize pipeline execution results

---

## What We Accomplished

### 1. Backend Fix - Input Pin Name Resolution
**Problem**: After pipeline execution, input pins showed generic group names ("text", "value") instead of meaningful upstream output pin names ("hawb", "pu").

**Root Cause**: The `_serialize_io_for_audit()` function used the current module's input pin names (group names), not the connected upstream output pin names.

**Solution**: Created new `_serialize_inputs_for_audit()` function in `server/src/features/pipeline_execution/service.py`:
- Looks up `input_field_mappings` to find upstream pin ID
- Uses `all_nodes_metadata` to find upstream pin name
- Falls back to input pin name if lookup fails

**File**: `server/src/features/pipeline_execution/service.py` (lines 185-250, 974-980)

**Code Reference**:
```python
def _serialize_inputs_for_audit(
    io_dict: Dict[str, Any],
    pins: List[NodeInstance],
    input_field_mappings: Dict[str, str],  # node_id -> upstream_node_id
    all_nodes_metadata: Dict[str, List[NodeInstance]],
    entry_points_lookup: Dict[str, str]
) -> Dict[str, Dict[str, Any]]:
    """Transform inputs to {node_id: {name, value, type}} using UPSTREAM pin names."""

    # Build lookup map of node_id -> name from all metadata
    node_id_to_name = {}
    for node_list in all_nodes_metadata.values():
        for node in node_list:
            node_id_to_name[node.node_id] = node.name

    node_id_to_name.update(entry_points_lookup)

    result = {}
    for pin in pins:
        if pin.node_id in io_dict:
            # Look up upstream pin ID from mapping
            upstream_pin_id = input_field_mappings.get(pin.node_id)
            if upstream_pin_id and upstream_pin_id in node_id_to_name:
                display_name = node_id_to_name[upstream_pin_id]
            else:
                display_name = pin.name

            result[pin.node_id] = {
                "name": display_name,
                "value": _serialize_value(raw_value, pin.type),
                "type": pin.type
            }
    return result
```

**Status**: ✅ Complete and verified working

---

### 2. ExecutedPipelineViewer Component Creation

#### Core Components Built

**A. ExecutedPipelineViewer.tsx** (Main orchestrator)
- File: `client/src/renderer/features/pipelines/components/ExecutedPipelineViewer/ExecutedPipelineViewer.tsx`
- Fetches modules using `useModules()` hook
- Converts pipeline state + execution steps to React Flow nodes
- Applies dagre layout (left-to-right, ranksep: 450, nodesep: 200)
- Creates edges from pipeline connections
- Renders read-only React Flow canvas

**Key Innovation - Handle Rendering Fix**:
The most critical fix ensures all handles render even when execution data is missing:

```typescript
// Build inputs/outputs from pipeline state structure with execution values
// This ensures all handles are rendered even if execution data is missing
const inputs: Record<string, { name: string; value: string; type: string }> = {};
const outputs: Record<string, { name: string; value: string; type: string }> = {};

// Populate inputs from pipeline state, overlay with execution data if available
moduleInstance.inputs.forEach((input) => {
  const executionData = executionStep?.inputs?.[input.node_id];
  inputs[input.node_id] = {
    name: executionData?.name || input.name,
    value: executionData?.value || "",
    type: executionData?.type || input.type,
  };
});

// Populate outputs from pipeline state, overlay with execution data if available
moduleInstance.outputs.forEach((output) => {
  const executionData = executionStep?.outputs?.[output.node_id];
  outputs[output.node_id] = {
    name: executionData?.name || output.name,
    value: executionData?.value || "",
    type: executionData?.type || output.type,
  };
});
```

**Why This Matters**: Without this approach, edges fail to connect because React Flow can't find the handle IDs. We iterate through pipeline state (source of truth for structure) and overlay execution data (which may be incomplete).

**B. ExecutedEntryPoint.tsx** (Entry point wrapper)
- File: `client/src/renderer/features/pipelines/components/ExecutedPipelineViewer/ExecutedEntryPoint.tsx`
- Simple wrapper that reuses ExecutedModule with hardcoded values
- Black header (`#000000`)
- "Entry Point" as module name
- No inputs, single string output with entry point name
- Uses `entry-${nodeId}` prefix for node IDs (critical for edge connections)

```typescript
export function ExecutedEntryPoint({ data }: ExecutedEntryPointProps) {
  const { name, nodeId } = data;

  const moduleData = {
    moduleName: "Entry Point",
    moduleColor: "#000000", // Black header
    inputs: {}, // No inputs for entry points
    outputs: {
      [nodeId]: {
        name: name,
        value: "", // No value to display
        type: "str", // Always string type
      },
    },
    status: "executed" as const,
  };

  return <ExecutedModule data={moduleData} />;
}
```

**C. ExecutedModule.tsx** (Module node component)
- File: `client/src/renderer/features/pipelines/components/ExecutedPipelineViewer/ExecutedModule.tsx`
- Composed of ExecutedModuleHeader + ExecutedModuleBody
- Border color based on execution status (red for failed, gray for executed)
- Supports hover handlers for future interactivity
- Dynamic width based on content

**D. ExecutedModuleHeader.tsx**
- File: `client/src/renderer/features/pipelines/components/ExecutedPipelineViewer/ExecutedModuleHeader.tsx`
- Colored header bar with module name
- Uses `getTextColor()` utility for proper text contrast
- Displays execution status icon (future enhancement)

**E. ExecutedModuleBody.tsx**
- File: `client/src/renderer/features/pipelines/components/ExecutedPipelineViewer/ExecutedModuleBody.tsx`
- Two-column layout (inputs left, outputs right)
- Renders ExecutedModuleRow for each pin
- Shows error message if execution failed
- Scrollable content if many pins

**F. ExecutedModuleRow.tsx**
- File: `client/src/renderer/features/pipelines/components/ExecutedPipelineViewer/ExecutedModuleRow.tsx`
- Individual pin row with React Flow Handle
- Type-colored indicator badge (from TYPE_COLORS)
- Mirrored layout: inputs show "name - type", outputs show "type - name"
- Handle positioned on outer edge (-13px offset)

---

### 3. Critical Bug Fixes

#### Bug 1: React Flow Handle Error
**Error Message**: `[React Flow]: Couldn't create edge for source handle id: "Na4y", edge id: edge-12`

**Root Cause**:
- Module "Ml2" had output "Na4y" in `pipelineState.modules`
- BUT execution step for "Ml2" had empty outputs object
- We were only rendering handles from execution step data
- So no Handle with id="Na4y" was rendered
- Edge connection referenced "Na4y" but couldn't find it

**User's Debugging**:
```
Pipeline State Modules:
  module_instance_id: "Ml2"
  outputs: Array(1)
    0: name: "due date text"
       node_id: "Na4y"

Execution Steps:
  module_instance_id: "Ml2"
  outputs: [[Prototype]]: Object  // EMPTY!
```

**Fix**: Always iterate through pipeline state for structure, overlay execution data for values (see Handle Rendering Fix above)

**Status**: ✅ Fixed and verified

#### Bug 2: Entry Point Edge Connections
**Problem**: Edges from entry points to modules weren't connecting

**Root Cause**: Entry point node IDs didn't match the expected `entry-` prefix pattern

**Fix** (in ExecutedPipelineViewer.tsx):
```typescript
// Create entry point nodes with 'entry-' prefix
pipelineState.entry_points.forEach((entryPoint) => {
  nodes.push({
    id: `entry-${entryPoint.node_id}`, // Critical prefix
    type: "executedEntryPoint",
    position: { x: 0, y: 0 },
    data: {
      name: entryPoint.name,
      nodeId: entryPoint.node_id,
    },
  });
});

// Map entry points in edge lookup - use 'entry-' prefixed ID
pipelineState.entry_points.forEach((ep) => {
  nodeIdToModuleId.set(ep.node_id, `entry-${ep.node_id}`);
});
```

**Status**: ✅ Fixed and verified

---

### 4. Dagre Layout Configuration

**Configuration** (ExecutedPipelineViewer.tsx lines 36-72):
```typescript
const nodeWidth = 220;
const nodeHeight = 180;

// Configure layout: LR (left-to-right), ranksep for horizontal spacing, nodesep for vertical
dagreGraph.setGraph({ rankdir: direction, ranksep: 450, nodesep: 200 });

nodes.forEach((node) => {
  dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight });
});

edges.forEach((edge) => {
  dagreGraph.setEdge(edge.source, edge.target);
});

dagre.layout(dagreGraph);

const layoutedNodes = nodes.map((node) => {
  const nodeWithPosition = dagreGraph.node(node.id);
  return {
    ...node,
    position: {
      x: nodeWithPosition.x - nodeWidth / 2,
      y: nodeWithPosition.y - nodeHeight / 2,
    },
  };
});
```

**Result**: Clean left-to-right hierarchical layout with proper spacing

---

### 5. Edge Creation and Debugging

**Edge Mapping Logic** (ExecutedPipelineViewer.tsx lines 182-229):
```typescript
// Build a lookup map: node_id -> module_instance_id (or entry point node_id)
const nodeIdToModuleId = new Map<string, string>();
pipelineState.modules.forEach((module) => {
  module.inputs.forEach((input) => {
    nodeIdToModuleId.set(input.node_id, module.module_instance_id);
  });
  module.outputs.forEach((output) => {
    nodeIdToModuleId.set(output.node_id, module.module_instance_id);
  });
});

// Map entry points - use 'entry-' prefixed ID as the node ID
pipelineState.entry_points.forEach((ep) => {
  nodeIdToModuleId.set(ep.node_id, `entry-${ep.node_id}`);
});

// Convert connections to edges
const edges = pipelineState.connections.map((connection, index) => {
  const sourceModuleId = nodeIdToModuleId.get(connection.from_node_id);
  const targetModuleId = nodeIdToModuleId.get(connection.to_node_id);

  // Debug: Log missing handles
  if (!sourceModuleId) {
    console.warn(`Missing source node for handle: ${connection.from_node_id}`);
  }
  if (!targetModuleId) {
    console.warn(`Missing target node for handle: ${connection.to_node_id}`);
  }

  return {
    id: `edge-${index}`,
    source: sourceModuleId || '',
    target: targetModuleId || '',
    sourceHandle: connection.from_node_id,
    targetHandle: connection.to_node_id,
    type: 'straight',
    style: { stroke: '#6B7280', strokeWidth: 2 },
  };
});

// Filter out edges with missing source or target
return edges.filter(edge => edge.source && edge.target);
```

**Current State**: Using basic straight-line edges (type: 'straight')

---

## What's Next: ExecutionEdge Implementation

### Analysis Complete
I analyzed the old `ExecutionEdge.tsx` component and documented how it works:

**File**: `client/src/renderer/features/pipelines/components/executedViewer-old/ExecutionEdge.tsx`

**Key Features**:
1. **Smooth Step Paths**: Uses `getSmoothStepPath` for orthogonal edges with 90-degree corners
2. **Custom Path Construction**: Adds horizontal offset for parallel edges to prevent overlapping
3. **Value Labels**: Positioned 80px right of source pin, shows execution values
4. **Hover Effects**: Glow effect (`drop-shadow`) when hovering over edge
5. **Type Coloring**: Edge stroke color from TYPE_COLORS based on data type
6. **EdgeLabelRenderer**: Proper label positioning that doesn't interfere with graph
7. **Invisible Wider Path**: 20px wide invisible path for easier hovering
8. **Value Truncation**: Truncates to 30 chars unless hovered

**Code Pattern**:
```typescript
const [edgePath, labelX, labelY] = getSmoothStepPath({
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
});

// Custom offset for parallel edges
const customPath = `M ${sourceX} ${sourceY} L ${sourceX + offset} ${sourceY} ${edgePath.substring(edgePath.indexOf('L'))}`;

// Label positioned near source
<EdgeLabelRenderer>
  <div style={{
    position: 'absolute',
    transform: `translate(-50%, -50%) translate(${sourceX + 80}px, ${sourceY}px)`,
  }}>
    {truncatedValue}
  </div>
</EdgeLabelRenderer>
```

---

## Pending Tasks (In Order)

### 1. Implement ExecutionEdge Component ⏳
**File to Create**: `client/src/renderer/features/pipelines/components/ExecutedPipelineViewer/ExecutionEdge.tsx`

**Requirements**:
- Use `getSmoothStepPath` for orthogonal paths
- Type-colored edges (from TYPE_COLORS)
- Value labels 80px right of source pin
- Hover effects with glow (drop-shadow)
- Support for parallel edges with horizontal offsets
- Invisible wider path (20px) for easier hovering
- Truncate values to 30 chars (show full on hover)

**Reference**: Old implementation at `executedViewer-old/ExecutionEdge.tsx`

### 2. Register Edge Type in ExecutedPipelineViewer
**File**: `ExecutedPipelineViewer.tsx`

**Changes Needed**:
- Import ExecutionEdge component
- Create `edgeTypes` constant: `{ executionEdge: ExecutionEdge }`
- Pass to ReactFlow component: `edgeTypes={edgeTypes}`
- Change edge creation: `type: 'executionEdge'` instead of `'straight'`

### 3. Extract Execution Values for Edge Labels
**File**: `ExecutedPipelineViewer.tsx`

**Logic Needed**:
- For each connection, find source module's execution step
- Look up output value from execution step using `connection.from_node_id`
- Attach value to edge data: `data: { value: executionValue }`
- ExecutionEdge will read from edge.data.value

**Code Pattern**:
```typescript
const edges = pipelineState.connections.map((connection, index) => {
  const sourceModuleId = nodeIdToModuleId.get(connection.from_node_id);
  const targetModuleId = nodeIdToModuleId.get(connection.to_node_id);

  // Find execution value for this connection
  const sourceExecution = executionSteps?.find(step =>
    step.module_instance_id === sourceModuleId
  );
  const outputValue = sourceExecution?.outputs?.[connection.from_node_id]?.value || "";

  return {
    id: `edge-${index}`,
    source: sourceModuleId || '',
    target: targetModuleId || '',
    sourceHandle: connection.from_node_id,
    targetHandle: connection.to_node_id,
    type: 'executionEdge',
    data: { value: outputValue },
    style: { stroke: '#6B7280', strokeWidth: 2 },
  };
});
```

### 4. Calculate Edge Offsets for Parallel Edges
**File**: `ExecutedPipelineViewer.tsx`

**Logic Needed**:
- Group edges by source-target pair
- For each group with multiple edges, assign incremental offsets
- Pass offset in edge data: `data: { value, offset }`
- ExecutionEdge uses offset to adjust horizontal position

### 5. Testing and Refinement
- Test with various pipeline structures
- Verify edge labels show correct values
- Test hover states and value truncation
- Verify parallel edges don't overlap
- Check type coloring matches data types

---

## Important Code Locations

### Frontend Files
```
client/src/renderer/features/pipelines/components/ExecutedPipelineViewer/
├── ExecutedPipelineViewer.tsx       [Main component, 287 lines]
├── ExecutedEntryPoint.tsx           [Entry point wrapper, 41 lines]
├── ExecutedModule.tsx               [Module node, 74 lines]
├── ExecutedModuleHeader.tsx         [Module header]
├── ExecutedModuleBody.tsx           [Module body with pins]
└── ExecutedModuleRow.tsx            [Individual pin row, 85 lines]

client/src/renderer/features/pipelines/components/executedViewer-old/
└── ExecutionEdge.tsx                [Reference implementation]
```

### Backend File
```
server/src/features/pipeline_execution/service.py
├── _serialize_inputs_for_audit()    [Lines 185-250]
└── execute_pipeline()               [Lines 974-980, calls serializer]
```

### Utility Files
```
client/src/renderer/features/pipelines/utils/moduleUtils.ts
├── TYPE_COLORS                      [Color mapping for data types]
└── getTextColor()                   [Text contrast calculation]
```

---

## Data Flow Summary

### Pipeline Execution Data Structure
```typescript
// From backend
interface ExecutionStepResult {
  module_instance_id: string;
  step_number: number;
  inputs: Record<string, { name: string; value: string; type: string }>;
  outputs: Record<string, { name: string; value: string; type: string }>;
  error: string | null;
}

// Pipeline state (structure)
interface PipelineState {
  entry_points: EntryPoint[];
  modules: ModuleInstance[];
  connections: NodeConnection[];
}

// Visual state (positions)
interface VisualState {
  modules: Record<string, { x: number; y: number }>;
  entryPoints: Record<string, { x: number; y: number }>;
}
```

### Component Props Flow
```
Parent Component (e.g., ETO Run Detail Modal)
  ↓ passes props
ExecutedPipelineViewer
  ↓ creates
[ExecutedEntryPoint nodes, ExecutedModule nodes]
  ↓ renders on
React Flow Canvas
  ↓ connected by
[ExecutionEdge components] ← TO BE IMPLEMENTED
```

---

## Known Issues and Considerations

### 1. Empty Execution Data
**Issue**: Some modules may have empty outputs in execution steps (e.g., module "Ml2" had no outputs).

**Solution**: We always iterate through pipeline state for structure, overlay execution data for values. Missing execution data results in empty value strings, but handles still render.

**Status**: ✅ Resolved

### 2. Entry Point ID Prefixing
**Issue**: Entry points need `entry-` prefix to avoid conflicts with module instance IDs.

**Solution**: All entry point node IDs use `entry-${nodeId}` pattern consistently.

**Status**: ✅ Resolved

### 3. Module Template Loading
**Issue**: Module templates must be loaded to get colors and titles.

**Solution**: Using `useModules()` hook with TanStack Query. Shows loading state while fetching.

**Status**: ✅ Working

### 4. Edge Type Coloring
**Issue**: Need to determine edge color based on connection's data type.

**Solution**: Look up type from source pin in pipeline state, use TYPE_COLORS mapping.

**Status**: ⏳ To be implemented in ExecutionEdge

---

## Testing Checklist

When implementing ExecutionEdge:

- [ ] Edges render with smooth step paths (orthogonal corners)
- [ ] Edge colors match data types (TYPE_COLORS)
- [ ] Value labels appear 80px right of source pins
- [ ] Values truncate to 30 chars, show full on hover
- [ ] Hover adds glow effect to edge
- [ ] Parallel edges have horizontal offsets (no overlapping)
- [ ] Invisible wider path makes hovering easier
- [ ] Entry point connections work correctly
- [ ] Multi-module pipelines layout cleanly
- [ ] Edge labels don't interfere with graph navigation

---

## Console Logs (For Debugging)

The viewer includes console logs that help debug data flow:

```typescript
console.log('Execution Steps:', executionSteps?.map((step, index) => ({
  index,
  module_instance_id: step.module_instance_id,
  step_number: step.step_number,
  inputs: step.inputs,
  outputs: step.outputs,
  error: step.error,
})));

console.log('Pipeline State Modules:', pipelineState?.modules.map(m => ({
  module_instance_id: m.module_instance_id,
  outputs: m.outputs.map(o => ({ node_id: o.node_id, name: o.name })),
  inputs: m.inputs.map(i => ({ node_id: i.node_id, name: i.name }))
})));

console.log('Pipeline Connections:', pipelineState?.connections);
```

These logs were crucial for identifying the missing handle bug.

---

## User Feedback History

1. **"Great that worked"** - Backend input name fix
2. **Black header for entry points** - Entry point styling
3. **"That is not what I wanted"** - Correction on ExecutedEntryPoint design (should reuse ExecutedModule)
4. **Handle ID error** - React Flow edge connection failure
5. **Console log expansion** - Debugging handle rendering
6. **"That worked"** - Confirming handle fix
7. **ExecutionEdge analysis request** - Current task

---

## Quick Start for Next Session

1. Read this document completely
2. Review ExecutionEdge reference: `executedViewer-old/ExecutionEdge.tsx`
3. Create new `ExecutionEdge.tsx` in ExecutedPipelineViewer directory
4. Register edge type in ExecutedPipelineViewer.tsx
5. Extract execution values and attach to edge data
6. Test with real pipeline execution data

---

## Additional Context

- User manages all testing and development servers
- Never run `npm run dev` or development servers
- Commit substantial changes with conventional commit messages
- Update CHANGELOG.md after session completion
- ExecutedPipelineViewer is read-only (no editing functionality)
- This replaces old executedViewer-old implementation

---

## Architecture Decisions

### Why Reuse ExecutedModule for Entry Points?
- **Consistency**: Same styling and structure as regular modules
- **Simplicity**: No duplicate component code
- **Maintainability**: Changes to module styling apply to entry points

### Why Iterate Pipeline State Instead of Execution Steps?
- **Completeness**: Pipeline state is the source of truth for structure
- **Resilience**: Handles missing execution data gracefully
- **Edge Connections**: Ensures all handles exist for React Flow

### Why Dagre Layout?
- **Hierarchical**: Natural left-to-right flow from entry points to outputs
- **Automatic**: No manual positioning needed
- **Consistent**: Same layout algorithm as pipeline builder

---

## End of Continuity Document

**Next Action**: Implement ExecutionEdge component following the pending tasks above.

**Success Criteria**:
- Edges display with smooth orthogonal paths
- Value labels show execution data
- Type-colored edges match data types
- Hover effects work properly
- All tests in Testing Checklist pass

**Estimated Time**: 1-2 hours for full ExecutionEdge implementation and testing
