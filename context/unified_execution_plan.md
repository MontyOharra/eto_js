# Unified Execution Engine Spec (Dask with Node Metadata)

> Audience: **Claude Code**
> Purpose: Implement the **runtime executor** that runs compiled pipelines using **Dask** with full node metadata context.
> Inputs: Compiled steps cached in DB (`pipeline_steps`) keyed by `plan_checksum`, plus `entry_values`.
> Key Enhancement: **Node metadata preservation** for type-aware and name-aware module execution.

---

## 0) High-level Flow

1. Load the **latest plan** (list of `PipelineStepModel` rows) by `pipeline_id` and `plan_checksum`.
2. Build a **Dask delayed task** per module instance from those rows.
3. Wire each task's kwargs to the **upstream output pin producers** using `input_field_mappings`.
4. Pass **node metadata context** to each module handler for type/name awareness.
5. Seed **entry pins** as constant tasks.
6. **Compute only Action tasks** (sinks).
7. Return a **run report** (status, timings, action results, errors).

---

## 1) Data Contracts

### 1.1 Enhanced `PipelineStepModel` (with Node Metadata)

For each reachable module instance:

* `module_instance_id: str`
* `module_ref: str` (e.g., `"basic_text_cleaner:1.0.0"`)
* `module_kind: "transform"|"logic"|"action"`
* `module_config: JSON` (already validated)
* `input_field_mappings: JSON`
  ```json
  {
    "pin_123": { "source_module_id": "mX"|"entry", "source_field": "pin_456" },
    ...
  }
  ```
* **`node_metadata: JSON`** (NEW - preserves complete node context)
  ```json
  {
    "inputs": [
      {
        "node_id": "pin_123",
        "name": "customer_name",     // User-assigned name for placeholders
        "type": "str",                // Resolved type for conversions
        "group_index": 0,
        "group_label": "Text Inputs",
        "position_index": 0
      }
    ],
    "outputs": [
      {
        "node_id": "pin_456",
        "name": "cleaned_text",
        "type": "str",
        "group_index": 0,
        "group_label": "Results",
        "position_index": 0
      }
    ]
  }
  ```
* `step_number: int` (topological layer; optional for Dask)

### 1.2 ExecutionContext Class

```python
from dataclasses import dataclass
from typing import Dict, Any, List

@dataclass
class ExecutionContext:
    """Context passed to module handlers with node metadata and helpers"""
    node_metadata: Dict[str, Any]     # Full node context from PipelineStep
    module_instance_id: str            # For debugging/logging
    run_id: str                        # Execution run ID

    # Helper methods for modules
    def get_input_type(self, index: int = 0) -> str:
        """Get type of input at given index"""
        return self.node_metadata["inputs"][index]["type"]

    def get_output_type(self, index: int = 0) -> str:
        """Get type of output at given index"""
        return self.node_metadata["outputs"][index]["type"]

    def get_input_names(self) -> Dict[str, str]:
        """Get mapping of node_id to user-assigned names"""
        return {n["node_id"]: n["name"] for n in self.node_metadata["inputs"]}

    def get_output_names(self) -> Dict[str, str]:
        """Get mapping of node_id to user-assigned names"""
        return {n["node_id"]: n["name"] for n in self.node_metadata["outputs"]}

    def resolve_placeholders(self, template: str, inputs: Dict[str, Any]) -> str:
        """Replace {name} placeholders with actual values"""
        result = template
        # Replace input placeholders
        for node in self.node_metadata["inputs"]:
            placeholder = f"{{{node['name']}}}"
            value = inputs.get(node["node_id"], "")
            result = result.replace(placeholder, str(value))
        # Also support output placeholders for prompts
        for node in self.node_metadata["outputs"]:
            placeholder = f"{{{node['name']}}}"
            result = result.replace(placeholder, placeholder)  # Keep for LLM to fill
        return result

    def get_input_by_name(self, name: str, inputs: Dict[str, Any]) -> Any:
        """Get input value by user-assigned name"""
        for node in self.node_metadata["inputs"]:
            if node["name"] == name:
                return inputs.get(node["node_id"])
        raise KeyError(f"No input with name '{name}'")

    def get_input_groups(self) -> Dict[int, List[Dict]]:
        """Get inputs organized by group"""
        groups = {}
        for node in self.node_metadata["inputs"]:
            group_idx = node["group_index"]
            if group_idx not in groups:
                groups[group_idx] = []
            groups[group_idx].append(node)
        return groups
```

### 1.3 Updated Module Handler Interface

```python
class ModuleHandler(ABC):
    """Base class for all module handlers"""

    @abstractmethod
    def run(
        self,
        inputs: Dict[str, Any],        # pin_id -> value mapping
        config: Dict[str, Any],        # module configuration
        context: ExecutionContext      # NEW: execution context with metadata
    ) -> Dict[str, Any]:               # pin_id -> value mapping
        """Execute the module logic"""
        pass
```

### 1.4 Entry Values

* Dict `{ entry_pin_id: value }` provided at runtime
* Every **required** entry pin in the pruned plan **must** be present

---

## 2) Executor API

```python
class RunResult(TypedDict):
    status: Literal["success", "failed"]
    run_id: str
    started_at: str
    completed_at: str
    actions: List[Dict]         # action results (one per action module)
    errors: List[Dict]          # [{module_instance_id, code, message}]
    timings: Dict[str, float]   # per-module ms
    metadata: Dict[str, Any]    # execution metadata

def run_pipeline(
    pipeline_id: str,
    plan_checksum: str,
    entry_values: Dict[str, Any],
    *,
    scheduler: Literal["threads", "processes", "distributed"] = "threads",
    max_workers: int | None = None,
    fail_fast: bool = True,
) -> RunResult:
    """Execute a compiled pipeline with entry values"""
    ...
```

---

## 3) Building the Dask Graph with Node Metadata

### 3.1 Preload steps

```python
rows = fetch_pipeline_steps(pipeline_id, plan_checksum)  # ORDER BY step_number ASC
if not rows:
    raise NotFound("No compiled steps for checksum")

# Generate run ID for this execution
run_id = gen_run_id()
```

### 3.2 Seed entries as delayed tasks

```python
from dask import delayed
entry_tasks: Dict[str, Any] = {}

@delayed(pure=True)
def _entry_passthrough(v):
    return v

for eid, val in entry_values.items():
    entry_tasks[eid] = _entry_passthrough(val)
```

### 3.3 Maps maintained during graph build

```python
delayed_by_module: Dict[str, Any] = {}     # module_instance_id -> delayed task
producer_of_pin: Dict[str, Any] = {}       # output_pin_id -> delayed task
timing_meta: Dict[str, Dict] = {}          # capture per module timing
```

### 3.4 Creating a delayed task with context

```python
def make_task(row, run_id: str) -> Any:
    handler_cls = registry.resolve(row.module_ref)
    handler = handler_cls()
    cfg = parse_module_config(row.module_config)
    input_map = json.loads(row.input_field_mappings)

    # Parse node metadata (NEW)
    node_metadata = json.loads(row.node_metadata) if row.node_metadata else {
        "inputs": [],
        "outputs": []
    }

    # Prepare dependency kwargs
    deps: Dict[str, Any] = {}
    for in_pin, mapping in input_map.items():
        src_field = mapping["source_field"]
        if mapping["source_module_id"] == "entry":
            deps[src_field] = producer_of_pin[src_field]
        else:
            deps[src_field] = producer_of_pin[src_field]

    @delayed(pure=(row.module_kind != "action"))
    def _run_instance(**upstream_outputs):
        t0 = time.perf_counter()

        # Build inputs for handler
        inputs_for_handler = {
            in_pin: upstream_outputs[mapping["source_field"]]
            for in_pin, mapping in input_map.items()
        }

        # Create execution context with node metadata (NEW)
        context = ExecutionContext(
            node_metadata=node_metadata,
            module_instance_id=row.module_instance_id,
            run_id=run_id
        )

        try:
            # Call handler with context
            out = handler.run(inputs_for_handler, cfg, context)
            ok = True
            err = None
        except Exception as e:
            ok = False
            out = {}
            err = f"{e.__class__.__name__}: {e}"
            # Log with full context for debugging
            logger.error(f"Module {row.module_instance_id} failed: {err}")
            logger.debug(f"Node metadata: {node_metadata}")

        t1 = time.perf_counter()
        return {
            "__ok__": ok,
            "__err__": err,
            "__elapsed_ms__": (t1 - t0) * 1000.0,
            "__module_instance_id__": row.module_instance_id,
            "__module_kind__": row.module_kind,
            "outputs": out,
        }

    return _run_instance(**deps)
```

### 3.5 Build in topological order

```python
# Seed producer map with entries
producer_of_pin.update(entry_tasks)

for row in rows:
    task = make_task(row, run_id)
    delayed_by_module[row.module_instance_id] = task

    # Map output pins to task (extract from node_metadata)
    if row.node_metadata:
        metadata = json.loads(row.node_metadata)
        for out_node in metadata.get("outputs", []):
            producer_of_pin[out_node["node_id"]] = task
```

### 3.6 Compute only Action tasks

```python
action_tasks = [
    delayed_by_module[row.module_instance_id]
    for row in rows if row.module_kind == "action"
]
```

---

## 4) Execute and Collect Results

```python
from dask import compute
started = now_iso()

try:
    results = compute(*action_tasks, scheduler=scheduler)
except Exception as e:
    return {
        "status": "failed",
        "run_id": run_id,
        "started_at": started,
        "completed_at": now_iso(),
        "errors": [{"code": "DASK_RUNTIME", "message": str(e)}],
    }

# Process results
actions = []
errors = []
timings = {}

for env in results:
    mid = env["__module_instance_id__"]
    timings[mid] = env["__elapsed_ms__"]
    if not env["__ok__"]:
        errors.append({
            "module_instance_id": mid,
            "code": "RUNTIME_ERROR",
            "message": env["__err__"]
        })
    else:
        actions.append({
            "module_instance_id": mid,
            "result": env["outputs"]
        })

status = "failed" if errors else "success"
return {
    "status": status,
    "run_id": run_id,
    "started_at": started,
    "completed_at": now_iso(),
    "actions": actions,
    "errors": errors,
    "timings": timings,
}
```

---

## 5) Example Module Implementations

### Type Converter Module

```python
class TypeConverterHandler(ModuleHandler):
    def run(self, inputs: Dict[str, Any], config: Dict, context: ExecutionContext):
        # Use context to determine conversion
        input_type = context.get_input_type(0)
        output_type = context.get_output_type(0)

        input_pin = context.node_metadata["inputs"][0]["node_id"]
        output_pin = context.node_metadata["outputs"][0]["node_id"]

        value = inputs[input_pin]

        # Type conversion logic based on metadata
        if input_type == "str" and output_type == "int":
            converted = int(value)
        elif input_type == "int" and output_type == "str":
            converted = str(value)
        elif input_type == "str" and output_type == "float":
            converted = float(value)
        elif input_type == "float" and output_type == "str":
            converted = str(value)
        elif input_type == "str" and output_type == "bool":
            converted = value.lower() in ('true', '1', 'yes')
        else:
            raise ValueError(f"Unsupported conversion: {input_type} -> {output_type}")

        return {output_pin: converted}
```

### LLM Module with Named Placeholders

```python
class LLMHandler(ModuleHandler):
    def run(self, inputs: Dict[str, Any], config: Dict, context: ExecutionContext):
        # Use named placeholders in prompt
        prompt_template = config["prompt"]
        # e.g., "Analyze {customer_name} and extract {order_date} into {parsed_date}"

        # Replace placeholders with actual values using context
        prompt = context.resolve_placeholders(prompt_template, inputs)

        # Add system context about expected outputs
        output_names = context.get_output_names()
        system_prompt = f"Extract the following fields: {', '.join(output_names.values())}"

        # Execute LLM call
        response = call_llm(system_prompt, prompt)

        # Parse response and map to output pins
        # For simplicity, assume single output
        output_pin = context.node_metadata["outputs"][0]["node_id"]
        return {output_pin: response}
```

### Group-Aware Aggregator

```python
class AggregatorHandler(ModuleHandler):
    def run(self, inputs: Dict[str, Any], config: Dict, context: ExecutionContext):
        # Process inputs by group
        groups = context.get_input_groups()
        results = {}

        for group_idx, nodes in groups.items():
            group_values = []
            for node in nodes:
                value = inputs.get(node["node_id"])
                if value is not None:
                    group_values.append(value)

            # Aggregate based on config
            operation = config.get("operation", "concat")
            if operation == "concat":
                result = " ".join(str(v) for v in group_values)
            elif operation == "sum":
                result = sum(float(v) for v in group_values)
            elif operation == "count":
                result = len(group_values)
            else:
                raise ValueError(f"Unknown operation: {operation}")

            # Map to output for this group
            output_node = context.node_metadata["outputs"][group_idx]
            results[output_node["node_id"]] = result

        return results
```

---

## 6) Policies & Edge Cases

* **Missing entry values**: Validate before execution that all required entries are provided
* **Type safety**: Node metadata includes types for validation and conversion
* **Named references**: User-friendly names preserved for debugging and prompts
* **Group processing**: Modules can process pins by their group context
* **Backward compatibility**: Old modules can ignore context parameter (make optional)
* **Debug context**: Full metadata available in error messages for troubleshooting

---

## 7) Sequential Fallback (No Dask)

For debugging or simple execution:

```python
def run_pipeline_sequential(pipeline_id, plan_checksum, entry_values):
    rows = fetch_pipeline_steps(pipeline_id, plan_checksum)
    values_by_pin = dict(entry_values)
    run_id = gen_run_id()

    for row in rows:  # Already in topological order
        handler_cls = registry.resolve(row.module_ref)
        handler = handler_cls()
        cfg = parse_module_config(row.module_config)

        # Build inputs
        input_map = json.loads(row.input_field_mappings)
        inputs = {}
        for in_pin, mapping in input_map.items():
            src_pin = mapping["source_field"]
            inputs[in_pin] = values_by_pin[src_pin]

        # Create context
        node_metadata = json.loads(row.node_metadata) if row.node_metadata else {}
        context = ExecutionContext(
            node_metadata=node_metadata,
            module_instance_id=row.module_instance_id,
            run_id=run_id
        )

        # Execute
        outputs = handler.run(inputs, cfg, context)
        values_by_pin.update(outputs)

    return values_by_pin
```

---

## 8) Benefits of Unified Approach

1. **Type awareness**: Modules can make decisions based on actual types
2. **Named placeholders**: User-friendly names in prompts and configs
3. **Group context**: Modules understand their input/output organization
4. **Debugging**: Rich context in error messages
5. **Extensibility**: Context can be extended with more metadata as needed
6. **Performance**: Metadata stored once in DB, not reconstructed

---

## 9) Implementation Checklist

* [ ] Update PipelineStep model with node_metadata field
* [ ] Create ExecutionContext class with helper methods
* [ ] Update module handler base class interface
* [ ] Modify compilation to preserve node metadata
* [ ] Update Dask executor to pass context
* [ ] Migrate existing modules to use context (optional parameter)
* [ ] Add database migration for node_metadata column
* [ ] Write unit tests for context-aware execution
* [ ] Update example modules (type converter, LLM, etc.)

This unified spec provides full node context to modules while maintaining the efficient Dask-based execution model.