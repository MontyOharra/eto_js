# Execution Engine Spec (Dask over Compiled Steps)

> Audience: **Claude Code**
> Purpose: implement the **runtime executor** that runs a compiled pipeline using **Dask**.
> Inputs: compiled steps cached in DB (`pipeline_steps`) keyed by `plan_checksum`, plus `entry_values`.
> Constraints (from product):
>
> * **Type changes happen only via modules** (edges must match types).
> * **Handlers accept pin‐id → value maps**; they don’t need ordered arrays.
> * **Execute only paths that reach an Action** (the compiler already prunes).
> * Steps are already **layered** (`step_number`) but Dask **doesn’t require** layer info to run.

---

## 0) High-level Flow

1. Load the **latest plan** (list of `PipelineStepModel` rows) by `pipeline_id` and `plan_checksum`.
2. Build a **Dask delayed task** per module instance from those rows.
3. Wire each task’s kwargs to the **upstream output pin producers** using `input_field_mappings`.
4. Seed **entry pins** as constant tasks.
5. **Compute only Action tasks** (sinks).
6. Return a **run report** (status, timings, action results, errors).

---

## 1) Data Contracts We Rely On

### 1.1 `PipelineStepModel` (already compiled)

For each reachable module instance:

* `module_instance_id: str`
* `module_ref: str` (e.g., `"basic_text_cleaner:1.0.0"`)
* `module_kind: "transform"|"logic"|"action"`
* `module_config: JSON` (already validated)
* `input_field_mappings: JSON`
  Shape (per your compiler):

  ```json
  {
    "this_input_pin_id": { "source_module_id": "mX"|"entry", "source_field": "upstream_output_pin_id_or_entry_pin_id" },
    ...
  }
  ```
* `output_display_names: JSON` (optional, for reporting)
* `step_number: int` (topological layer; optional for Dask)

> The compiler has already: validated DAG, pruned to **action-reachable**, and generated these rows.

### 1.2 Module Registry

* `registry.resolve(module_ref) -> handler_class`
  where `handler_class().run(inputs: dict[pin_id, Any], cfg: PydanticModel) -> dict[pin_id, Any]`.

### 1.3 Entry Values

* Dict `{ entry_pin_id: value }` provided at run time.
  Every **required** entry pin in the pruned plan **must** be present.

---

## 2) Executor API

```python
class RunResult(TypedDict, total=False):
    status: Literal["success","failed"]
    run_id: str
    started_at: str
    completed_at: str
    actions: list[dict]         # action results (one per action module)
    errors: list[dict]          # [{module_instance_id, code, message}]
    timings: dict[str, float]   # optional per-module ms

def run_pipeline(
    pipeline_id: str,
    plan_checksum: str,
    entry_values: dict[str, Any],
    *,
    scheduler: Literal["threads","processes","distributed"] = "threads",
    max_workers: int | None = None,
    fail_fast: bool = True,
) -> RunResult: ...
```

Notes:

* `scheduler` is passed to `dask.compute`.
* `max_workers` can be mapped to Dask’s config (threads/processes) or ignored if using a global client.
* `fail_fast=True`: stop at first failure (see §5).

---

## 3) Building the Dask Graph

We create **one delayed task per module instance**. Each task returns that module’s **output dict** `{ out_pin_id: value }`.

### 3.1 Preload steps

```python
rows = fetch_pipeline_steps(pipeline_id, plan_checksum)  # ORDER BY step_number ASC, id ASC
if not rows:
    raise NotFound("No compiled steps for checksum")
```

Optional: **verify entries** exist for all required input edges that point to `"entry"`.

### 3.2 Seed entries as delayed tasks

Two options (A recommended):

**A) Uniform entry tasks**

```python
from dask import delayed
entry_tasks: dict[str, Any] = {}

@delayed(pure=True)
def _entry_passthrough(v): return v

for eid, val in entry_values.items():
    entry_tasks[eid] = _entry_passthrough(val)
```

**B) Inline constants** – you can pass values directly as kwargs. (A is cleaner for debugging and graph introspection.)

### 3.3 Maps we maintain during graph build

```python
delayed_by_module: dict[str, Any] = {}     # module_instance_id -> delayed task
producer_of_pin:   dict[str, Any] = {}     # output_pin_id (or entry pin id) -> delayed task
timing_meta:       dict[str, dict] = {}    # capture per module timing/envelopes
```

### 3.4 Creating a delayed task for a row

```python
from dask import delayed
import json, time

def make_task(row) -> Any:
    handler_cls = registry.resolve(row.module_ref)
    handler = handler_cls()
    cfg = parse_module_config(row.module_config)  # Ideally Pydantic-validated already
    input_map = json.loads(row.input_field_mappings)  # {in_pin -> {source_module_id, source_field}}

    # Prepare dependency kwargs: { upstream_output_pin_id: producing_task }
    deps: dict[str, Any] = {}
    for in_pin, mapping in input_map.items():
        src_field = mapping["source_field"]
        if mapping["source_module_id"] == "entry":
            deps[src_field] = producer_of_pin[src_field]  # seeded in 3.2
        else:
            # src_field is an output pin id
            deps[src_field] = producer_of_pin[src_field]

    # Wrap handler.run with a small envelope for timing and fail-fast control
    @delayed(pure=(row.module_kind != "action"))
    def _run_instance(**upstream_outputs):
        t0 = time.perf_counter()
        # Build the pin-keyed dict the handler expects:
        inputs_for_handler = {
            in_pin: upstream_outputs[mapping["source_field"]]
            for in_pin, mapping in input_map.items()
        }
        try:
            out = handler.run(inputs_for_handler, cfg)  # -> {out_pin_id: value}
            ok = True
            err = None
        except Exception as e:
            ok = False
            out = {}
            err = f"{e.__class__.__name__}: {e}"
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

### 3.5 Build in topological order (already sorted by `step_number`)

```python
# Seed producer map with entries
producer_of_pin.update(entry_tasks)

for row in rows:
    task = make_task(row)
    delayed_by_module[row.module_instance_id] = task

    # Every output pin of this module is produced by the same task (map all to task)
    for out_pin in list_output_pins_for_instance(row.module_instance_id):
        producer_of_pin[out_pin.node_id] = task
```

> `list_output_pins_for_instance` can come from your compiled cache or read from the pipeline JSON. We only need **pin IDs**, not types, at runtime.

### 3.6 Compute **only Action tasks**

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
    results = compute(*action_tasks, scheduler=scheduler)  # results: tuple of envelopes
except Exception as e:
    # This triggers if Dask fails the cluster or a top-level task blows up.
    return {
        "status": "failed",
        "run_id": gen_run_id(),
        "started_at": started,
        "completed_at": now_iso(),
        "errors": [{"code":"DASK_RUNTIME", "message": str(e)}],
    }

# Flatten per-action envelopes; if fail_fast is desired, each envelope already has __ok__/__err__
actions = []
errors = []
timings = {}

for env in results:
    mid = env["__module_instance_id__"]
    timings[mid] = env["__elapsed_ms__"]
    if not env["__ok__"]:
        errors.append({"module_instance_id": mid, "code": "RUNTIME_ERROR", "message": env["__err__"]})
    else:
        actions.append({"module_instance_id": mid, "result": env["outputs"]})

status = "failed" if errors else "success"
return {
    "status": status,
    "run_id": gen_run_id(),
    "started_at": started,
    "completed_at": now_iso(),
    "actions": actions,
    "errors": errors,
    "timings": timings,
}
```

### Optional: **fail-fast** semantics

If `fail_fast=True`, you can raise on first error within `_run_instance` so the whole `compute` fails early. The current envelope approach instead **collects** errors and returns them; switch by replacing the `try/except` with a `raise`.

---

## 5) Policies & Edge Cases

* **Missing entry values**: before building tasks, verify that every `input_field_mappings` entry with `source_module_id=="entry"` has a provided `entry_values[src_field]`; else return an error.
* **Purity**: mark `@delayed(pure=True)` for transforms/logic (safe to cache inside a graph); `pure=False` for actions.
* **Parallelism**: start with `scheduler="threads"`. If CPU-bound steps appear, allow `"processes"`; for distributed, you’d rely on an existing Dask client.
* **Idempotence**: if Actions need at-least-once semantics, the handler should implement its own idempotency (e.g., run_id + business key).
* **Timing**: envelope returns elapsed ms per module; combine with `step_number` if you want layer timing (can be added by joining `rows` meta in the final report).
* **Selective compute**: we already **compute only actions**, which naturally executes just the required upstream steps thanks to Dask dependency resolution.

---

## 6) Minimal Unit Test Plan

1. **Single linear flow** (entry → transform → action): assert outputs, check timings present.
2. **Parallel fanout** (entry → two transforms → action depends on both): assert both run; scheduler parallelizes.
3. **Dead branch pruned by compiler**: steps contain only action-reachable modules; executor never sees dead modules.
4. **Handler error**: inject a transform that raises; verify `status="failed"` and scoped error.
5. **Missing entry**: validation error before execution.
6. **Multiple actions**: compute returns tuple for each action; ensure both are present.

---

## 7) What We **Don’t** Do Here

* We **don’t** rebuild the graph with NetworkX at runtime. That happened at compile time.
* We **don’t** use `step_number` to schedule; Dask doesn’t need it. (We still store it for UX/ops and sequential fallback.)
* We **don’t** coerce types at runtime—edge type safety was enforced earlier.

---

## 8) Optional Sequential Fallback (No Dask)

Same plan; just loop rows by `step_number` and run handlers directly while building a `values_by_pin` store. Keep this path for easier local debugging.

---

## 9) Ready-to-Implement Checklist

* [ ] DB accessor: `fetch_pipeline_steps(pipeline_id, plan_checksum)`
* [ ] Registry resolver: `registry.resolve(module_ref)`
* [ ] Output pins enumerator: `list_output_pins_for_instance(module_instance_id)`
* [ ] Executor function `run_pipeline(...)` (as above)
* [ ] Unit tests (6 cases)

This spec should be enough to implement the Dask-based executor that consumes your **compiled, pruned, cached** pipeline steps and executes only the branches that reach an Action.
