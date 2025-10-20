# Pipeline Visualization Architecture

## Design Decision: Lazy-Loading with Shared Pipeline Component

**Date:** 2025-10-18
**Status:** Approved

---

## Overview

The pipeline visualization system uses a **lazy-loading architecture** with a **single reusable component** for displaying transformation pipelines across multiple contexts.

---

## Core Principle

**One Pipeline Viewer, Multiple Contexts:**
- Template Editor → shows pipeline being built/edited
- Template Viewer → shows finalized template pipeline
- ETO Run Detail → shows executed pipeline with runtime data
- Standalone Pipeline Testing → shows test pipelines

All use the **same underlying pipeline visualization component**.

---

## API Design: Pipeline Reference Pattern

### Problem Solved

Previously, to display an executed pipeline in the ETO run detail view, the frontend would need:

1. `GET /eto-runs/{id}` → Get template_id and version_id
2. `GET /pdf-templates/{id}/versions/{version_id}` → Get pipeline_definition_id
3. `GET /pipelines/{pipeline_definition_id}` → Get pipeline graph structure

**3 sequential API calls before rendering!**

### Solution: Include Pipeline Reference Directly

The `pipeline_execution` object in the ETO run detail response now includes `pipeline_definition_id`:

```typescript
// GET /eto-runs/{id} response:
{
  "id": 123,
  "status": "success",
  // ... other run fields ...

  "pipeline_execution": {
    "status": "success",
    "started_at": "2024-01-15T10:30:00Z",
    "completed_at": "2024-01-15T10:30:05Z",
    "error_message": null,

    // ✅ ADD THIS FIELD
    "pipeline_definition_id": 456,  // Direct reference to pipeline

    "executed_actions": [...],
    "steps": [...]
  }
}
```

---

## Lazy Loading Architecture

### Initial Load (Summary View)

When user opens ETO run detail modal:

```typescript
// Step 1: Load run details
const runDetail = await getEtoRunDetail(runId);

// runDetail.pipeline_execution.pipeline_definition_id is now available
// BUT we don't fetch the full pipeline yet - user might not switch to Detail view
```

**Result:** Fast initial load, only ~100KB response

### On-Demand Load (Detail View)

When user switches to "Detail" tab:

```typescript
// Step 2: Load pipeline graph (only when needed)
const pipelineDefinitionId = runDetail.pipeline_execution.pipeline_definition_id;
const pipeline = await getPipeline(pipelineDefinitionId);

// pipeline.pipeline_state contains full graph structure
// pipeline.visual_state contains node positions
```

**Result:** Additional ~50KB only when user actually needs it

---

## Component Reusability

### Single Source of Truth: `ExecutedPipelineViewer`

```typescript
// Component signature:
interface ExecutedPipelineViewerProps {
  pipelineDefinitionId: number;
  executionData?: PipelineExecutionData;  // Optional: for showing runtime values
  mode: 'readonly' | 'editable';
}
```

### Usage Contexts

#### 1. ETO Run Detail (Read-Only with Execution Data)

```typescript
<ExecutedPipelineViewer
  pipelineDefinitionId={runDetail.pipeline_execution.pipeline_definition_id}
  executionData={{
    steps: runDetail.pipeline_execution.steps,
    executedActions: runDetail.pipeline_execution.executed_actions
  }}
  mode="readonly"
/>
```

**Features:**
- Shows pipeline graph structure
- Overlays execution data (input/output values) on nodes
- Highlights executed paths
- Shows errors on failed modules

#### 2. Template Viewer (Read-Only, No Execution Data)

```typescript
<ExecutedPipelineViewer
  pipelineDefinitionId={templateVersion.pipeline_definition_id}
  mode="readonly"
/>
```

**Features:**
- Shows pipeline graph structure
- No execution data overlay
- Just displays the designed pipeline

#### 3. Template Editor (Editable)

```typescript
<ExecutedPipelineViewer
  pipelineDefinitionId={templateVersion.pipeline_definition_id}
  mode="editable"
/>
```

**Features:**
- Full pipeline builder functionality
- Same component as `/dashboard/pipelines/create`
- Saves updates back to template

#### 4. Standalone Pipeline Testing

```typescript
<ExecutedPipelineViewer
  pipelineDefinitionId={pipelineId}
  mode="editable"
/>
```

**Features:**
- Dev/testing environment
- Create and test pipelines without templates

---

## Data Flow

### Fetching Pipeline Definition

```typescript
// Single endpoint for all contexts:
GET /pipelines/{pipeline_definition_id}

Response:
{
  "id": 456,
  "compiled_plan_id": 789,
  "pipeline_state": {
    "entry_points": [
      {
        "id": "entry_hawb",
        "label": "hawb",
        "field_reference": "hawb"
      }
    ],
    "modules": [
      {
        "instance_id": "mod_uppercase",
        "module_id": "string_uppercase:1.0.0",
        "config": {},
        "inputs": [
          {
            "node_id": "input_text",
            "name": "text",
            "type": ["str"]
          }
        ],
        "outputs": [
          {
            "node_id": "output_result",
            "name": "result",
            "type": ["str"]
          }
        ]
      }
    ],
    "connections": [
      {
        "from_node_id": "entry_hawb",
        "to_node_id": "input_text"
      }
    ]
  },
  "visual_state": {
    "positions": {
      "entry_hawb": { "x": 100, "y": 100 },
      "mod_uppercase": { "x": 400, "y": 100 }
    }
  }
}
```

### Merging Execution Data (ETO Run Context Only)

```typescript
// Client-side merging in ExecutedPipelineViewer:
function mergeExecutionData(
  pipelineState: PipelineState,
  executionSteps: ExecutionStep[]
): EnrichedPipelineState {
  // Map execution steps to module instances
  const stepsByModuleId = new Map();
  executionSteps.forEach(step => {
    stepsByModuleId.set(step.module_instance_id, step);
  });

  // Enrich modules with execution data
  return {
    ...pipelineState,
    modules: pipelineState.modules.map(module => ({
      ...module,
      executed: stepsByModuleId.has(module.instance_id),
      executionData: stepsByModuleId.get(module.instance_id) || null
    }))
  };
}
```

---

## Mock Data Strategy

### Single Pipeline Mock for All Contexts

Create one comprehensive pipeline mock that can be used everywhere:

```typescript
// features/pipelines/mocks/executedPipelineMock.ts
export const mockPipelineDefinition = {
  id: 1,
  compiled_plan_id: 1,
  pipeline_state: {
    entry_points: [...],
    modules: [...],
    connections: [...]
  },
  visual_state: {
    positions: {...}
  }
};

// Separate execution data for ETO run context
export const mockExecutionData = {
  steps: [
    {
      step_number: 1,
      module_instance_id: "mod_uppercase",
      inputs: { text: { value: "HAWB-2024-12345", type: "str" } },
      outputs: { result: { value: "HAWB-2024-12345", type: "str" } },
      error: null
    }
  ],
  executed_actions: [...]
};
```

### Usage in Components

```typescript
// ETO Run Detail Modal
const mockRunDetail = {
  // ... other fields ...
  pipeline_execution: {
    pipeline_definition_id: 1,  // References mockPipelineDefinition
    steps: mockExecutionData.steps,
    executed_actions: mockExecutionData.executed_actions
  }
};

// Template Viewer
const mockTemplateVersion = {
  // ... other fields ...
  pipeline_definition_id: 1  // Same pipeline, different context
};

// Standalone Testing
const mockPipelineList = [
  {
    id: 1,  // Can fetch mockPipelineDefinition with this ID
    compiled_plan_id: 1,
    created_at: "2024-01-15T10:00:00Z",
    updated_at: "2024-01-15T10:00:00Z"
  }
];
```

---

## Implementation Benefits

### 1. Performance
- Lazy loading reduces initial page load
- Only fetch pipeline data when user needs it
- Cache pipeline definitions (same pipeline used across multiple runs)

### 2. Code Reuse
- Single visualization component
- Shared mock data
- Consistent UX across all pipeline views

### 3. Maintainability
- One component to update for UI improvements
- Single API endpoint for pipeline data
- Clear separation between structure (pipeline_state) and execution (steps)

### 4. Scalability
- Can add new contexts (e.g., pipeline history comparison) easily
- Cache pipeline definitions to avoid refetching
- Support large pipelines (20+ modules) without bloating ETO run response

---

## API Change Summary

### Required Backend Change

**Endpoint:** `GET /eto-runs/{id}`

**Add to `pipeline_execution` object:**
```typescript
"pipeline_execution": {
  "status": "...",
  "started_at": "...",
  "completed_at": "...",
  "error_message": null,

  // ✅ ADD THIS FIELD
  "pipeline_definition_id": number,  // From matched template version

  "executed_actions": [...],
  "steps": [...]
}
```

**How to populate:**
1. ETO run has `matched_template_version_id`
2. Template version has `pipeline_definition_id`
3. Include this ID in the pipeline_execution response

**SQL pseudocode:**
```sql
SELECT
  pe.pipeline_definition_id
FROM eto_run_pipeline_executions pe
JOIN eto_runs er ON er.id = pe.eto_run_id
WHERE er.id = :run_id
```

---

## Frontend Implementation Plan

### Phase 1: Create Base Pipeline Viewer Component
- [ ] Create `ExecutedPipelineViewer.tsx` component
- [ ] Support fetching pipeline by ID
- [ ] Display pipeline graph (read-only mode)
- [ ] Use existing React Flow components from pipeline builder

### Phase 2: Add Execution Data Overlay
- [ ] Merge execution steps with pipeline structure
- [ ] Show input/output values on hover
- [ ] Highlight executed paths
- [ ] Show error states on failed modules

### Phase 3: Integrate into ETO Run Detail Modal
- [ ] Add conditional fetch when switching to Detail tab
- [ ] Show loading state while fetching pipeline
- [ ] Display merged pipeline + execution data

### Phase 4: Reuse in Other Contexts
- [ ] Template viewer
- [ ] Template editor (editable mode)
- [ ] Standalone pipeline testing page

---

## Testing Strategy

### Mock API Responses

```typescript
// Mock pipelines API
export const useMockPipelinesApi = () => {
  const getPipeline = async (id: number) => {
    if (id === 1) return mockPipelineDefinition;
    throw new Error('Pipeline not found');
  };

  return { getPipeline };
};
```

### Test Button Flow

```typescript
// On pipelines index page:
<button onClick={() => {
  // Open modal/page showing executed pipeline
  showExecutedPipelineViewer({
    pipelineDefinitionId: 1,
    executionData: mockExecutionData
  });
}}>
  Test Executed Pipeline View
</button>
```

---

## Future Enhancements

### Potential Additions
1. **Module Metadata in Steps:** Include module name/color in execution steps to avoid fetching module catalog
2. **Extraction Field Overlay:** Include extracted_fields_with_boxes in data_extraction stage
3. **Pipeline Comparison:** Compare two pipeline versions side-by-side
4. **Execution Replay:** Step-by-step animation of pipeline execution
5. **Performance Metrics:** Show execution time per module

---

## Conclusion

This architecture provides:
- ✅ Clean separation of concerns (structure vs execution)
- ✅ Optimal performance (lazy loading)
- ✅ Maximum code reuse (single component)
- ✅ Scalable design (works for complex pipelines)
- ✅ Simple testing (single mock data source)

**Next Step:** Update API_ENDPOINTS.md with the pipeline_definition_id addition.
