# Pipeline Connection Bug Analysis

## Problem Statement

When editing an existing template (version mode), connections cannot be created from pre-loaded modules. Connections can only be created from modules that are placed AFTER the initial template data loads.

## Reproduction

1. Open existing template for editing (version mode)
2. Template loads with existing modules and connections
3. Try to create new connection from a pre-loaded module → **FAILS**
4. Place a new module onto the canvas
5. Try to create connection from the newly-placed module → **WORKS**

## Root Cause Analysis

### How Connection Validation Works

**`isValidConnection` callback** (PipelineGraph.tsx line 558-587):
```typescript
const isValidConnection = useCallback(
  (connection: Connection) => {
    // ... validation logic using pipelineState and effectiveEntryPoints
    const result = validateConnection(
      tempPipelineState,
      effectiveEntryPoints,
      connection.source,
      connection.sourceHandle,
      connection.target,
      connection.targetHandle
    );
    return result.valid;
  },
  [pipelineState, effectiveEntryPoints]
);
```

**Dependencies**: `pipelineState`, `effectiveEntryPoints`

### Suspect 1: Stale Closure in isValidConnection

The `isValidConnection` callback is memoized with `useCallback` and has `pipelineState` and `effectiveEntryPoints` as dependencies. When the template loads initially:

1. PipelineState is set with existing modules/connections
2. `isValidConnection` is created with initial `pipelineState`
3. Callback is passed to React Flow

**Hypothesis**: The callback might not be updating properly when modules are already present, but does update when new modules are added.

### Suspect 2: Effective Types Cache Timing Issue

**Effect that recalculates types** (line 93-125):
```typescript
useEffect(() => {
  // Recalculate effective types for all pins
  const newCache = new Map<string, string[]>();

  pipelineState.modules.forEach((module) => {
    // Calculate types using getEffectiveAllowedTypes
    // which traverses connections via BFS
  });

  setEffectiveTypesCache(newCache);
}, [pipelineState, effectiveEntryPoints]);
```

**Issue**: `getEffectiveAllowedTypes` (typeSystem.ts line 88-175) traverses the connection graph to calculate type constraints. When modules are pre-loaded with connections, this creates a circular dependency:

1. Effect calculates types based on existing connections
2. Types might be over-constrained due to existing connections
3. When trying to add NEW connection, validation fails because types don't match

**When adding NEW module**:
1. Module has no connections yet
2. Types are calculated based only on template defaults
3. Validation succeeds because types are more flexible

### Suspect 3: React Flow Internal State Desynchronization

**Nodes initialization effect** (line 349-432) creates nodes and calls `setNodes(newNodes)`. This updates React Flow's internal node registry.

**Hypothesis**: When template loads initially, there might be a timing issue where:
1. Nodes are registered with React Flow
2. But handles aren't fully "connected" to React Flow's connection system
3. Only newly-placed modules get properly registered

### Suspect 4: Module Reference Check in findModule

**In typeSystem.ts** (line 38-64), `findModule` searches for modules in `pipelineState.modules`:
```typescript
function findModule(
  pipelineState: PipelineState,
  effectiveEntryPoints: EntryPoint[],
  moduleId: string
) {
  const module = pipelineState.modules.find((m) => m.module_instance_id === moduleId);
  // ...
}
```

**Hypothesis**: If `pipelineState` passed to validation is stale, it won't find pre-loaded modules, causing validation to fail.

## Debugging Strategy

### Step 1: Add Console Logging

Add logs to `isValidConnection` to see what's being validated:

```typescript
const isValidConnection = useCallback(
  (connection: Connection) => {
    console.log('[isValidConnection] Validating connection:', {
      source: connection.source,
      sourceHandle: connection.sourceHandle,
      target: connection.target,
      targetHandle: connection.targetHandle,
      modulesInState: pipelineState?.modules.map(m => m.module_instance_id),
      effectiveEntryPoints: effectiveEntryPoints.map(ep => ep.entry_point_id),
    });

    // ... rest of validation

    console.log('[isValidConnection] Result:', { valid: result.valid });
    return result.valid;
  },
  [pipelineState, effectiveEntryPoints]
);
```

### Step 2: Check if Module is Found

Add logs to `findModule` in typeSystem.ts:

```typescript
function findModule(...) {
  console.log('[findModule] Looking for module:', moduleId);
  console.log('[findModule] Available modules:', pipelineState.modules.map(m => m.module_instance_id));

  const module = pipelineState.modules.find((m) => m.module_instance_id === moduleId);
  console.log('[findModule] Found:', !!module);

  return module ? { module, isEntryPoint: false } : undefined;
}
```

### Step 3: Check Effective Types

Log what types are calculated:

```typescript
const sourceEffectiveTypes = getEffectiveAllowedTypes(...);
console.log('[validateConnection] Source effective types:', sourceEffectiveTypes);

const targetEffectiveTypes = getEffectiveAllowedTypes(...);
console.log('[validateConnection] Target effective types:', targetEffectiveTypes);

const typeIntersection = getTypeIntersection(...);
console.log('[validateConnection] Type intersection:', typeIntersection);
```

## Potential Solutions

### Solution 1: Force Callback Recreation

Ensure `isValidConnection` is always up-to-date by adding more dependencies:

```typescript
const isValidConnection = useCallback(
  (connection: Connection) => {
    // ... validation logic
  },
  [pipelineState, effectiveEntryPoints, effectiveTypesCache] // Add cache
);
```

### Solution 2: Use Ref for Latest State

Store pipelineState in a ref so validation always uses latest state:

```typescript
const pipelineStateRef = useRef(pipelineState);

useEffect(() => {
  pipelineStateRef.current = pipelineState;
}, [pipelineState]);

const isValidConnection = useCallback(
  (connection: Connection) => {
    // Use pipelineStateRef.current instead of pipelineState
    const result = validateConnection(
      pipelineStateRef.current,
      // ...
    );
  },
  [effectiveEntryPoints] // Remove pipelineState from deps
);
```

### Solution 3: Recalculate Types Without Existing Connections

When calculating effective types for validation, exclude existing connections to avoid over-constraining:

```typescript
const isValidConnection = useCallback(
  (connection: Connection) => {
    // Create temp state WITHOUT existing connections for validation
    const tempStateForValidation = {
      ...pipelineState,
      connections: [], // Empty connections for fresh type calculation
    };

    const result = validateConnection(
      tempStateForValidation,
      effectiveEntryPoints,
      // ...
    );
  },
  [pipelineState, effectiveEntryPoints]
);
```

### Solution 4: Force Node Re-registration

After loading initial state, force React Flow to re-register all nodes:

```typescript
useEffect(() => {
  if (pipelineState && isInitialLoad) {
    // Force re-registration by clearing and re-setting nodes
    setNodes([]);
    setTimeout(() => {
      // Recalculate nodes after brief delay
      // This gives React Flow time to clear its internal state
    }, 0);
  }
}, [pipelineState, isInitialLoad]);
```

### Solution 5: Check React Flow's Node Registration

Verify that nodes are properly registered with React Flow when loaded initially vs when placed new. The issue might be in how `NodeRow` handles are being set up.

## Recommended Approach

**Start with logging** (Debugging Steps 1-3) to confirm root cause, then apply Solution 2 (useRef) or Solution 3 (recalculate without connections) based on findings.

**Most likely fix**: Solution 3 - Recalculate types without existing connections during validation. This ensures that validation doesn't over-constrain types based on what's already connected.

## Testing Checklist

After applying fix:

- [ ] Load existing template with modules and connections
- [ ] Create new connection from pre-loaded module to another pre-loaded module
- [ ] Create new connection from pre-loaded module to newly-placed module
- [ ] Create new connection from newly-placed module to pre-loaded module
- [ ] Verify type validation still works correctly (incompatible types rejected)
- [ ] Verify type propagation still works after creating connection
