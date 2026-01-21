# Feature: Conditional Error/Halt Module

## Overview

New pipeline module that conditionally throws an error to halt sub-run processing. Acts as a guard to prevent data from being sent out when something is wrong.

## Module Specification

### Metadata

```python
identifier = "conditional_error"
version = "1.0.0"
title = "Conditional Error"
description = "Throws an error to halt processing if condition is true"
kind = "logic"  # or "misc"
category = "Logic"
color = "#EF4444"  # Red - indicates danger/halt
```

### I/O Shape

```python
inputs = IOSideShape(
    nodes=[
        NodeGroup(
            label="condition",
            typing=NodeTypeRule(allowed_types=["bool"]),
            min_count=1,
            max_count=1
        )
    ]
)

outputs = IOSideShape(
    nodes=[]  # No outputs - this is a terminal node
)
```

### Config

```python
class ConditionalErrorConfig(BaseModel):
    error_message: str = Field(
        ...,
        description="Error message to throw. Supports ${variable} injection from inputs."
    )
    invert_condition: bool = Field(
        default=False,
        description="If true, throws error when condition is FALSE instead of TRUE"
    )
```

### Execution Logic

```python
def run(self, inputs, cfg: ConditionalErrorConfig, context, access_conn_manager=None):
    condition = inputs[context.inputs[0].node_id]

    # Apply inversion if configured
    should_throw = not condition if cfg.invert_condition else condition

    if should_throw:
        # Variable injection in error message
        message = cfg.error_message
        # Could inject other values if we add more inputs later
        raise PipelineExecutionError(message)

    # No outputs to return
    return {}
```

## Pipeline Compilation Changes

### Current Behavior

```
1. Find all output channel nodes (considered "end nodes")
2. Traverse backwards from end nodes
3. Build execution order based on dependencies
```

### Problem

Modules with no output connections (like conditional_error) are never reached during backwards traversal from output channels.

### Solution

Update end-node detection to include:
1. Output channel nodes (existing)
2. Any module node with no outgoing connections (new)

### Implementation

**File:** `server/src/features/pipeline_execution/` (or wherever compilation occurs)

```python
def find_end_nodes(pipeline_state):
    end_nodes = []

    # 1. All output channel nodes are end nodes
    for node in pipeline_state.nodes:
        if is_output_channel(node):
            end_nodes.append(node)

    # 2. Any module with no outgoing edges is also an end node
    nodes_with_outgoing = set()
    for edge in pipeline_state.edges:
        nodes_with_outgoing.add(edge.source_node_id)

    for node in pipeline_state.nodes:
        if node.id not in nodes_with_outgoing and not is_output_channel(node):
            # This node has no outgoing connections - it's a terminal
            end_nodes.append(node)

    return end_nodes
```

### Edge Cases

1. **Disconnected nodes**: Nodes with no connections at all should probably be excluded (validation error?)
2. **Multiple terminal branches**: Pipeline can have multiple independent end points - all should execute
3. **Generator → Error direct connection**: Should work fine, generator feeds into error module

## Variable Injection

Support `${variable}` syntax in error message, similar to LLM module.

For this module, the only input is the boolean condition, which isn't very useful to inject. However, designing for variable injection now allows future flexibility if we add more inputs (e.g., a "value" input to include in error message).

```python
# Future possibility: add optional value input for richer error messages
error_message = "Validation failed: value was ${value}, expected positive number"
```

For MVP, just support the basic static message.

## Checklist

### Module Implementation
- [ ] Create `server/src/features/modules/definitions/logic/conditional_error.py`
- [ ] Define ConditionalErrorConfig with error_message and invert_condition
- [ ] Define meta() with single bool input, no outputs
- [ ] Implement run() to throw error when condition met
- [ ] Register module with @register decorator

### Pipeline Compilation Update
- [ ] Identify pipeline compilation code (find_end_nodes or equivalent)
- [ ] Update to include no-output modules as end nodes
- [ ] Test that disconnected nodes are handled appropriately
- [ ] Verify execution order is correct with multiple terminal branches

### Testing
- [ ] Test error thrown when condition is true
- [ ] Test no error when condition is false
- [ ] Test invert_condition flag
- [ ] Test pipeline with error module compiles correctly
- [ ] Test error propagates and fails sub-run
- [ ] Test pipeline with multiple branches (some ending in output, some in error)
