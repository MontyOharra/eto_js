Perfect—let’s wire the spec to your **`pipeline_steps`** cache. Below is a focused addendum you can hand to Claude. It explains **how we populate** `PipelineStepModel` during compile, **what each field means**, how **checksums** are computed/used, and **how execution** reads from this table.

---

# Addendum: Compiled Steps Cache (`pipeline_steps`) — Population & Use

## Purpose

`pipeline_steps` is a **compiled cache** for a specific pipeline definition. It stores one row **per module instance** that is reachable from any **Action** module. The cache lets us **run** without re-planning, and enables ordered or parallel execution by using `step_number`.

---

## When we write `pipeline_steps`

* **Trigger:** on `POST /pipelines` (create/update) after validation succeeds.
* **Scope:** we compile **only** the portion of the graph that **reaches an Action** (policy).
* **Idempotence:** we compute a **`plan_checksum`** of the compiled plan. If the same checksum already exists for the pipeline, we can skip re-insert or replace atomically.

---

## How we compile → rows

### 1) Prune to action-reachable subgraph (pin graph → module graph)

* From the pin-level graph:

  * Reverse-walk from **Action input pins** to find all **reachable pins and their owning module instances**.
* Drop everything else.
* Contract pins to **module-level graph** `H`:

  * nodes = `module_instance_id`
  * edge `A → B` if any output pin of `A` connects to any input pin of `B`.

### 2) Topological **layers** and step numbers

* Use NetworkX `topological_generations(H)` (or `dag_layers`) to get layers.
* Assign:

  * `step_number` = **layer index** (0,1,2,…)
  * All modules in the same layer can run in **parallel**.

### 3) Build `input_field_mappings` per module

For each module instance `m` in the pruned plan:

```json
{
  "m:<input_pin_id>" : "<upstream_output_pin_id>"
}
```

* One mapping per **input pin** of `m`.
* This is a **pin→pin** mapping (using global `node_id`s), so handlers only need the IDs to assemble their input dict at runtime.

### 4) Choose `output_display_names` (optional UX)

* Persist user-defined output pin names for audit/reporting:

```json
{
  "<output_pin_id>": "<user_friendly_name>"
}
```

If you don’t need it yet, store `{}` (or `NULL`).

---

## Mapping the compile result → `PipelineStepModel`

For each reachable **module instance**:

* **`pipeline_id`**: the owning pipeline definition id (FK).
* **`plan_checksum`**: see checksum section below.
* **`module_instance_id`**: instance id from builder JSON.
* **`module_ref`**: e.g., `"basic_text_cleaner:1.0.0"`.
* **`module_kind`**: `"transform" | "logic" | "action"`.
* **`module_config`**: **validated** config JSON (post-Pydantic).
* **`input_field_mappings`**: JSON map `{ input_pin_id → upstream_output_pin_id }`.
* **`output_display_names`**: JSON map `{ output_pin_id → label }` (optional).
* **`step_number`**: layer index (0-based) for scheduling.

### Example rows (JSON for clarity)

**Cleaner (step 0):**

```json
{
  "pipeline_id": "p_abc",
  "plan_checksum": "3d1a…",
  "module_instance_id": "m_cleaner",
  "module_ref": "basic_text_cleaner:1.0.0",
  "module_kind": "transform",
  "module_config": {"strip_whitespace":true,"normalize_spaces":true,"remove_empty_lines":false,"to_lowercase":false},
  "input_field_mappings": { "m_cleaner:i0": "entry_order_ref" },
  "output_display_names": { "m_cleaner:o0": "order_ref_clean" },
  "step_number": 0
}
```

**Type Converter (step 1):**

```json
{
  "pipeline_id": "p_abc",
  "plan_checksum": "3d1a…",
  "module_instance_id": "m_cast",
  "module_ref": "type_converter:1.0.0",
  "module_kind": "transform",
  "module_config": {"strict": false},
  "input_field_mappings": { "m_cast:i0": "m_cleaner:o0" },
  "output_display_names": {
    "m_cast:o0": "order_ref_str",
    "m_cast:o1": "order_ref_dt"
  },
  "step_number": 1
}
```

**Action (step 2):**

```json
{
  "pipeline_id": "p_abc",
  "plan_checksum": "3d1a…",
  "module_instance_id": "m_action",
  "module_ref": "order_create:1.0.0",
  "module_kind": "action",
  "module_config": {"apply_defaults": true},
  "input_field_mappings": {
    "m_action:i_ref": "m_cast:o0",
    "m_action:i_eta": "m_cast:o1"
  },
  "output_display_names": {},
  "step_number": 2
}
```

---

## `plan_checksum` — what we hash and why

We want a checksum that changes **only** when execution-relevant details change.

### Recommended checksum input (normalized JSON):

* The **pruned** action-reachable plan only:

  * Sorted list of **module instances** with:

    * `module_instance_id`
    * `module_ref`, `module_kind`
    * **validated** `module_config`
    * `inputs[]` and `outputs[]` **pin IDs and types** (names optional)
  * Sorted list of **connections** among those pins
* The computed **layer assignment** (array of layers with module ids)
* Optionally the pipeline definition id/version

Normalize (stable key order, no whitespace) and compute SHA-256 → `plan_checksum`.

**Why:** If UI-only changes occur (canvas coordinates, hidden labels), checksum remains stable. If config/types/wiring/layers change, checksum changes → we write new step rows (and can keep old rows for history).

---

## Validation recap (what we enforce before writing rows)

1. **Schema & presence**
2. **Pin uniqueness**; node ids globally unique.
3. **Edge cardinality**: every **input** pin has **exactly one** upstream.
4. **Type equality on edges** (no coercions).
5. **Acyclic** (pin graph).
6. **Module instance conformance** to its template:

   * NodeGroup cardinalities (min/max)
   * Typing: fixed types, `allowed_types`, and **type-var unification** within the instance
   * Config Pydantic validation
7. **At least one Action present**.
8. Compute action-reachable set; warn (or ignore) dead branches.

Only after all checks pass do we build layers and write rows.

---

## How execution reads from `pipeline_steps`

### Query

* Select rows by `pipeline_id` **and** the **latest** `plan_checksum` (or the one requested).
* Order by **`step_number ASC, id ASC`** (secondary sort is stable but doesn’t matter for correctness).

```sql
SELECT *
FROM pipeline_steps
WHERE pipeline_id = :pid AND plan_checksum = :checksum
ORDER BY step_number ASC, id ASC;
```

### Runtime value store

* Start with `values_by_pin = { **entry_pin_id → value** }` (from run request).
* For each row in order:

  * Build `inputs_for_handler`:

    ```python
    inputs = { in_id: values_by_pin[ upstream_id ]
               for in_id, upstream_id in input_field_mappings.items() }
    ```
  * Resolve handler by `module_ref`, call:

    ```python
    outputs = handler.run(inputs, cfg)  # returns { out_pin_id: value }
    ```
  * Write outputs into `values_by_pin`.

### Parallelism (optional)

* Group rows by `step_number`.
* Within a step, modules are independent → run them concurrently (thread/async pool).
* A Dask variant can be added later by producing delayed tasks per row and computing only **Action** roots.

### Pruning

Because we wrote rows only for **action-reachable** modules, the executor naturally runs the minimal necessary work.

### Failure policy

* **Fail-fast v1:** on any handler error, stop and return a failure report with `module_instance_id` and message.
* (Later: per-branch isolation or retry based on module kind.)

---

## Why this table design works well

* **Simple executor:** no graph rebuild at runtime; rows already encode dependency via `input_field_mappings` and `step_number`.
* **Deterministic & parallel-ready:** `step_number` gives layers; you can run per layer in parallel or strictly sequential.
* **Cache-friendly:** `plan_checksum` lets you quickly detect “no-op” compiles and keeps history if desired.
* **Handler simplicity:** handlers only need pin IDs and values; no ordering or naming logic required.

---

## Minimal pseudocode (compile)

```python
def compile_pipeline(pipeline_json) -> tuple[list[PipelineStepRow], str]:
    validate_or_raise(pipeline_json)
    pruned = prune_to_action_reachable(pipeline_json)           # pins/modules/edges
    H = module_graph(pruned)                                    # module nodes, edges
    layers = topo_layers(H)                                     # [[m1,m2], [m3], ...]
    rows = []
    for step_number, layer in enumerate(layers):
        for mid in layer:
            mod = pruned.module_by_id[mid]
            input_map = build_input_map(mod, pruned.connections)  # {in_pin → upstream_pin}
            row = PipelineStepRow(
                pipeline_id=pipeline_json["id"],
                module_instance_id=mid,
                module_ref=mod["module_ref"],
                module_kind=resolve_kind(mod["module_ref"]),
                module_config=validated_config_json(mod),
                input_field_mappings=json_dumps(input_map),
                output_display_names=json_dumps(get_output_names(mod)),
                step_number=step_number,
            )
            rows.append(row)
    checksum = compute_plan_checksum(pruned, layers)  # normalized JSON → sha256
    for r in rows: r.plan_checksum = checksum
    return rows, checksum
```

---

## Minimal pseudocode (run)

```python
def run_pipeline(pipeline_id, entry_values):
    rows = fetch_rows_for_latest_plan(pipeline_id)  # ORDER BY step_number, id
    values = dict(entry_values)
    report = {"actions": [], "errors": []}

    for step, group in groupby(rows, key=lambda r: r.step_number):
        for row in group:
            handler = registry.resolve(row.module_ref)
            cfg = json_loads(row.module_config)
            input_map = json_loads(row.input_field_mappings)

            inputs = { in_id: values[input_map[in_id]] for in_id in input_map }
            try:
                outputs = handler.run(inputs, cfg)
                values.update(outputs)
                if row.module_kind == "action":
                    report["actions"].append({
                        "module_instance_id": row.module_instance_id,
                        "result": outputs  # or handler-defined payload
                    })
            except Exception as e:
                report["errors"].append({
                    "module_instance_id": row.module_instance_id,
                    "code": "RUNTIME_ERROR",
                    "message": str(e)
                })
                return {"status": "failed", **report}

    return {"status": "success", **report}
```

---

If you want, I can produce a short unit-testable compiler stub that takes your current pipeline JSON and emits in-memory `PipelineStepRow` dicts exactly matching these fields.
