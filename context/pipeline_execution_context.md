# Transformation Pipeline System - Execution Context

## Overview
This document provides a comprehensive overview of the transformation pipeline system architecture, focusing on how pipelines are stored, structured, and prepared for execution. This is intended as context for implementing the backend execution engine.

---

## 1. PIPELINE DATA STRUCTURE

### 1.1 Pipeline Storage Format

Pipelines are stored with two primary JSON structures:

**`pipeline_json`** - The execution graph:
```python
class PipelineState(BaseModel):
    entry_points: List[EntryPoint] = Field(default_factory=list)
    modules: List[ModuleInstance] = Field(default_factory=list)
    connections: List[NodeConnection] = Field(default_factory=list)
```

**`visual_json`** - UI positioning (not needed for execution):
```python
class VisualState(BaseModel):
    modules: Dict[str, ModulePosition] = Field(default_factory=dict)
    entryPoints: Dict[str, ModulePosition] = Field(default_factory=dict)
```

### 1.2 Entry Points

Entry points are the starting nodes of the pipeline. They represent external inputs that will be provided at runtime.

```python
class EntryPoint(BaseModel):
    """Entry point for pipeline input"""
    node_id: str  # Unique ID for this output node
    name: str     # Human-readable name (e.g., "email_body", "subject_line")
```

**Key Characteristics:**
- Entry points have NO inputs
- Entry points have ONE output (the `node_id` field IS the output node ID)
- Entry points always output type `str` (hardcoded in frontend)
- Entry points are provided as runtime inputs when executing the pipeline
- Multiple entry points can exist in a single pipeline

**Example:**
```json
{
  "entry_points": [
    {
      "node_id": "ep-001",
      "name": "email_body"
    },
    {
      "node_id": "ep-002",
      "name": "subject_line"
    }
  ]
}
```

### 1.3 Module Instances

Module instances are nodes placed on the canvas representing transformations, actions, or logic operations.

```python
class ModuleInstance(BaseModel):
    """A module instance placed on the canvas"""
    module_instance_id: str  # Unique ID for this module instance
    module_ref: str          # Reference to template: "text_cleaner:1.0.0"
    module_kind: Literal["transform", "action", "logic"]
    config: Dict[str, Any]   # Module-specific configuration
    inputs: List[InstanceNodePin]   # Input pins
    outputs: List[InstanceNodePin]  # Output pins
```

**Module Reference Format:**
- Format: `"{module_id}:{version}"`
- Example: `"text_cleaner:1.0.0"`, `"if_selector:1.0.0"`

**Module Kinds:**
- `transform`: Pure functions, no side effects (e.g., text cleaning, data conversion)
- `action`: Side effects allowed (e.g., send email, write to database)
- `logic`: Control flow (e.g., if/else routing, boolean operations)

### 1.4 Node Pins (Inputs/Outputs)

Each module instance has explicit input and output pins. Pins are the connection points.

```python
class InstanceNodePin(BaseModel):
    """Runtime instance of a pin in a module instance"""
    node_id: str         # Unique ID for THIS pin (used in connections)
    type: str            # Selected scalar type: "str", "int", "float", "bool", "datetime"
    name: str            # User-editable name for this pin
    position_index: int  # Position within the group (for dynamic groups)
    group_index: int     # Which NodeGroup this belongs to (from template)
```

**Important Notes:**
- `node_id` is unique across ALL pins in the entire pipeline
- `node_id` is what connections reference (not module IDs)
- Pins are grouped by `group_index` (maps to template's NodeGroup array)
- Within a group, pins are ordered by `position_index`

**Example:**
```json
{
  "module_instance_id": "mod-001",
  "module_ref": "text_cleaner:1.0.0",
  "module_kind": "transform",
  "config": {},
  "inputs": [
    {
      "node_id": "pin-in-001",
      "type": "str",
      "name": "input_text",
      "position_index": 0,
      "group_index": 0
    }
  ],
  "outputs": [
    {
      "node_id": "pin-out-001",
      "type": "str",
      "name": "cleaned_text",
      "position_index": 0,
      "group_index": 0
    }
  ]
}
```

### 1.5 Connections

Connections define the data flow between nodes.

```python
class NodeConnection(BaseModel):
    """Connection between two nodes"""
    from_node_id: str  # Source pin's node_id (output pin or entry point)
    to_node_id: str    # Target pin's node_id (input pin)
```

**Key Points:**
- Connections reference `node_id` values directly
- `from_node_id` can be:
  - An output pin from a ModuleInstance
  - An EntryPoint's `node_id` (entry points act as sources)
- `to_node_id` is always an input pin of a ModuleInstance
- One output can connect to MULTIPLE inputs (fan-out)
- One input can connect to ONLY ONE output

**Example:**
```json
{
  "connections": [
    {
      "from_node_id": "ep-001",      // Entry point output
      "to_node_id": "pin-in-001"     // Module input
    },
    {
      "from_node_id": "pin-out-001",  // Module output
      "to_node_id": "pin-in-002"      // Another module input
    }
  ]
}
```

---

## 2. MODULE TEMPLATES (Type System)

Module templates define the structure and constraints for module instances.

### 2.1 Template Structure

```python
class ModuleMeta(BaseModel):
    """Metadata defining I/O constraints for a module"""
    io_shape: IOShape

class IOShape(BaseModel):
    inputs: IOSideShape
    outputs: IOSideShape
    type_params: Dict[str, List[Scalar]]  # TypeVar domains

class IOSideShape(BaseModel):
    nodes: List[NodeGroup]  # Ordered array of node groups

class NodeGroup(BaseModel):
    label: str           # Group label (e.g., "Input Text", "Items")
    min_count: int       # Minimum pins in this group
    max_count: Optional[int]  # Maximum pins (None = unlimited)
    typing: NodeTypeRule      # Type constraints
```

### 2.2 Node Groups Explained

Node groups define how many pins can exist and their type constraints.

**Static Groups** (Fixed Count):
- `min_count == max_count == 1`
- Always exactly one pin
- Example: Single "input_text" field

**Dynamic Groups** (Variable Count):
- `max_count > 1` or `max_count == None`
- User can add/remove pins within bounds
- Example: "Items to concatenate" (0 to unlimited)

### 2.3 Type System

There are two type constraint models:

**Per-Pin Whitelist** (`allowed_types`):
```python
class NodeTypeRule(BaseModel):
    allowed_types: Optional[List[Scalar]] = None
    type_var: Optional[str] = None

# Example:
NodeTypeRule(allowed_types=["str", "int", "float"])
```
- Each pin independently selects from allowed types
- No coordination between pins

**Type Variables** (`type_var`):
```python
NodeTypeRule(type_var="T")

# With domain:
type_params = {"T": ["str", "int", "float", "bool"]}
```
- All pins with same type_var MUST have the same type
- Enforces consistency across inputs/outputs
- Domain defined in `io_shape.type_params`

**Example Template:**
```json
{
  "id": "type_converter",
  "version": "1.0.0",
  "meta": {
    "io_shape": {
      "inputs": {
        "nodes": [
          {
            "label": "Input Value",
            "min_count": 1,
            "max_count": 1,
            "typing": {
              "allowed_types": ["str", "int", "float", "bool"]
            }
          }
        ]
      },
      "outputs": {
        "nodes": [
          {
            "label": "Output Value",
            "min_count": 1,
            "max_count": 1,
            "typing": {
              "allowed_types": ["str", "int", "float", "bool"]
            }
          }
        ]
      },
      "type_params": {}
    }
  }
}
```

---

## 3. COMPLETE PIPELINE EXAMPLE

Here's a full example of a saved pipeline:

```json
{
  "id": "pipeline-123",
  "name": "Email Content Extractor",
  "description": "Extracts and cleans email content",
  "pipeline_json": {
    "entry_points": [
      {
        "node_id": "entry-email-body",
        "name": "email_body"
      },
      {
        "node_id": "entry-subject",
        "name": "subject"
      }
    ],
    "modules": [
      {
        "module_instance_id": "cleaner-001",
        "module_ref": "text_cleaner:1.0.0",
        "module_kind": "transform",
        "config": {},
        "inputs": [
          {
            "node_id": "cleaner-in-1",
            "type": "str",
            "name": "input_text",
            "position_index": 0,
            "group_index": 0
          }
        ],
        "outputs": [
          {
            "node_id": "cleaner-out-1",
            "type": "str",
            "name": "cleaned_text",
            "position_index": 0,
            "group_index": 0
          }
        ]
      },
      {
        "module_instance_id": "splitter-001",
        "module_ref": "text_splitter:1.0.0",
        "module_kind": "transform",
        "config": {
          "delimiter": "\n",
          "max_parts": 10
        },
        "inputs": [
          {
            "node_id": "splitter-in-1",
            "type": "str",
            "name": "text",
            "position_index": 0,
            "group_index": 0
          }
        ],
        "outputs": [
          {
            "node_id": "splitter-out-1",
            "type": "str",
            "name": "part_1",
            "position_index": 0,
            "group_index": 0
          },
          {
            "node_id": "splitter-out-2",
            "type": "str",
            "name": "part_2",
            "position_index": 1,
            "group_index": 0
          }
        ]
      }
    ],
    "connections": [
      {
        "from_node_id": "entry-email-body",
        "to_node_id": "cleaner-in-1"
      },
      {
        "from_node_id": "cleaner-out-1",
        "to_node_id": "splitter-in-1"
      }
    ]
  },
  "visual_json": {
    "modules": {
      "cleaner-001": { "x": 400, "y": 100 },
      "splitter-001": { "x": 700, "y": 100 }
    },
    "entryPoints": {
      "entry-email-body": { "x": 100, "y": 100 },
      "entry-subject": { "x": 100, "y": 250 }
    }
  }
}
```

---

## 4. EXECUTION MODEL CONSIDERATIONS

### 4.1 Graph Topology

The pipeline forms a **Directed Acyclic Graph (DAG)**:
- **Nodes**: Entry points + Module instances
- **Edges**: Connections (data flow)
- **Sources**: Entry points (no incoming edges)
- **Sinks**: Modules with no outgoing connections

### 4.2 Execution Requirements

1. **Topological Ordering**: Modules must execute in dependency order
2. **Data Resolution**: Map `node_id` connections to actual data values
3. **Entry Point Injection**: Runtime values provided for entry points
4. **Type Safety**: Validate types match at connection boundaries
5. **Configuration Injection**: Pass module `config` to execution handlers

### 4.3 Pin-Level Execution

Important: Modules execute at the **pin level**, not module level.

**Input Mapping:**
```python
# Execution receives inputs keyed by node_id
inputs = {
    "cleaner-in-1": "Some email text...",  # node_id -> value
}

# Module receives this and must map to its logic
```

**Output Mapping:**
```python
# Module returns outputs keyed by node_id
outputs = {
    "cleaner-out-1": "Cleaned text...",  # node_id -> value
}
```

### 4.4 Entry Point Runtime Values

Entry points are provided as a dictionary at execution time:

```python
# Runtime input format:
entry_point_values = {
    "entry-email-body": "Dear customer, ...",  # node_id -> str value
    "entry-subject": "Order Confirmation"
}
```

These are injected as the starting values in the execution graph.

---

## 5. FRONTEND VS BACKEND SERIALIZATION

### 5.1 Frontend Representation

The frontend uses enriched `NodePin` objects with UI-only fields:

```typescript
interface NodePin {
  node_id: string;
  direction: 'in' | 'out';      // UI only
  type: string;
  name: string;
  label: string;                 // UI only - from template
  position_index: number;
  group_index: number;
  type_var?: string;             // UI only - for type coordination
  allowed_types?: string[];      // UI only - for type picker
}
```

### 5.2 Backend Representation

The backend receives stripped-down `InstanceNodePin`:

```python
class InstanceNodePin(BaseModel):
    node_id: str
    type: str
    name: str
    position_index: int
    group_index: int
```

### 5.3 Serialization Process

When saving, the frontend strips UI-only fields:

```typescript
// Frontend -> Backend transformation
function serializeNodePin(pin: NodePin): InstanceNodePin {
  return {
    node_id: pin.node_id,
    type: pin.type,
    name: pin.name,
    position_index: pin.position_index,
    group_index: pin.group_index
    // direction, label, type_var, allowed_types are removed
  };
}
```

---

## 6. KEY DESIGN PRINCIPLES

1. **Pin-Centric**: Connections reference individual pins (`node_id`), not modules
2. **Immutable Pipelines**: Once created, pipelines cannot be edited (create new version)
3. **Entry Points are Special**: They act as source nodes with only outputs
4. **Type Safety**: Types are enforced at connection time and validated at execution time
5. **Module Independence**: Modules know nothing about the pipeline structure
6. **Graph-Based**: Pipeline execution follows DAG topology
7. **Configuration Separation**: Module behavior controlled by `config` dict

---

## 7. EXECUTION PLANNING REQUIREMENTS

To execute a pipeline, you need to:

1. **Load Pipeline State**: Parse `pipeline_json` from database
2. **Load Module Templates**: Fetch templates for all `module_ref` values
3. **Build Execution Graph**:
   - Create nodes for entry points + modules
   - Create edges from connections
   - Validate graph is acyclic
4. **Topological Sort**: Determine execution order
5. **Resolve Dependencies**: For each module, identify which upstream outputs feed which inputs
6. **Map Entry Points**: Identify which entry points feed into which module inputs
7. **Generate Execution Plan**: Ordered list of module executions with input/output mappings
8. **Validate Types**: Ensure connected pins have compatible types
9. **Validate Configuration**: Parse and validate each module's `config` against its `config_schema`

---

## 8. DATA STRUCTURES SUMMARY

```python
# From database
Pipeline(
    id="pipeline-123",
    pipeline_json=PipelineState(
        entry_points=[EntryPoint(node_id="ep-1", name="input")],
        modules=[ModuleInstance(...)],
        connections=[NodeConnection(from_node_id="ep-1", to_node_id="pin-in-1")]
    ),
    visual_json=VisualState(...)  # Ignore for execution
)

# Module templates (loaded separately)
ModuleTemplate(
    id="text_cleaner",
    version="1.0.0",
    meta=ModuleMeta(
        io_shape=IOShape(
            inputs=IOSideShape(nodes=[NodeGroup(...)]),
            outputs=IOSideShape(nodes=[NodeGroup(...)]),
            type_params={}
        )
    ),
    config_schema={...}
)
```

---

## 9. IMPORTANT NOTES FOR EXECUTION ENGINE

- **Entry points have `node_id` as their output**: The `node_id` field in `EntryPoint` IS the output node that can be referenced in connections
- **Pin IDs are globally unique**: Every `node_id` in the pipeline is unique
- **Connections are directional**: `from_node_id` (output) -> `to_node_id` (input)
- **Module config is opaque**: The execution engine passes it through to modules without interpretation
- **Types are strings**: "str", "int", "float", "bool", "datetime"
- **Dynamic pins**: Modules can have variable numbers of inputs/outputs based on `NodeGroup` constraints
- **No cycles allowed**: Pipeline must be a DAG for execution

---

## 10. FILE LOCATIONS

**Frontend Types:**
- `client/src/renderer/types/moduleTypes.ts` - Module and pin type definitions
- `client/src/renderer/types/pipelineTypes.ts` - Pipeline state types
- `client/src/renderer/utils/pipelineSerializer.ts` - Serialization logic

**Backend Types:**
- `transformation_pipeline_server/src/shared/models/pipeline.py` - Pipeline data models
- `transformation_pipeline_server/src/features/modules/core/contracts.py` - Module type system

**Backend Module Definitions:**
- `transformation_pipeline_server/src/features/modules/transform/` - Transform modules
- `transformation_pipeline_server/src/features/modules/logic/` - Logic modules
- `transformation_pipeline_server/src/features/modules/action/` - Action modules

---

This document should provide complete context for implementing pipeline execution logic. The execution engine needs to take the stored `PipelineState`, build an execution plan, and orchestrate module execution in topological order while managing data flow between pins.
