# Backend Spec — Pipeline Validation, Compilation, and Execution (v1)

> Audience: Claude. Purpose: implement the backend that validates a pipeline, compiles it into executable steps, persists it, and runs it with entry values.
> Ground rules provided by the user:
>
> * **Handlers only need pin IDs** and values; they don’t need ordered views.
> * **Edge types must match exactly**. All type changes happen via an explicit **Type Converter** module.
> * **Only paths that reach an Action module** should be executed.
> * We can use **NetworkX** for graph checks/sorting and optionally **Dask** for parallel execution; Dask choice is a later discussion.

---

## 0) Canonical pipeline JSON (input to backend)

The builder sends **two JSON blobs**:

1. **`pipeline_json`** (execution model; lean, no UI-only fields)

   ```jsonc
   {
     "entry_points": [
       { "node_id": "entry_1", "name": "Entry 1", "type": "str" }
       // entry pins are always type "str"; they act like output pins
     ],
     "modules": [
       {
         "module_instance_id": "m_cleaner",
         "module_ref": "basic_text_cleaner:1.0.0",
         "config": { "strip_whitespace": true, "normalize_spaces": true, "remove_empty_lines": false, "to_lowercase": false },
         "inputs": [
           { "node_id": "m_cleaner:i0", "type": "str", "name": "Entry 1", "position_index": 0, "group_index": 0 }
         ],
         "outputs": [
           { "node_id": "m_cleaner:o0", "type": "str", "name": "output_1", "position_index": 0, "group_index": 0 }
         ]
       },
       {
         "module_instance_id": "m_action",
         "module_ref": "order_create:1.0.0",
         "config": { /*...*/ },
         "inputs": [ /* concrete pins with types */ ],
         "outputs": []   // Actions typically have zero outputs
       }
     ],
     "connections": [
       { "from_node_id": "entry_1",       "to_node_id": "m_cleaner:i0" },
       { "from_node_id": "m_cleaner:o0",  "to_node_id": "m_action:i1" }
     ]
   }
   ```

2. **`visual_json`** (layout only; ignored by executor; stored alongside the pipeline)

---

## 1) API surface

### 1.1 Validate as-you-edit (debounced from FE)

`POST /pipelines/validate`

* **Body:** `{ "pipeline_json": <above> }`
* **Returns:**

  ```json
  {
    "valid": true,
    "errors": []           // or, when invalid:
    // "errors": [{ code, message, where: { module_instance_id?, node_id?, connection? } }]
  }
  ```
* **FE behavior:** if `valid=false`, disable “Create Pipeline” and **console.log** each error for now (later: surface inline).

### 1.2 Create pipeline

`POST /pipelines`

* **Flow:**

  1. Re-run full validation (authoritative).
  2. If valid: **compile** to steps (see §3), **persist** pipeline + compiled plan.
  3. Return `pipeline_id` and compilation metadata (generations count, module count, action count).
* **Returns:** `{ "pipeline_id": "...", "compile": { "layers": N, "modules": M, "actions": A } }`

### 1.3 Run pipeline

`POST /pipelines/{pipeline_id}/run`

* **Body:** `{ "entry_values": { "<entry_node_id>": <value>, ... } }`
* **Flow:** Load compiled plan; execute only the subgraph that **reaches an Action** (see §4.3).
* **Returns:** execution report:

  ```json
  {
    "status": "success" | "failed",
    "started_at": "...", "completed_at": "...",
    "actions": [
      { "module_instance_id": "m_action", "result": { /* module-defined */ } }
    ],
    "errors": [
      { "module_instance_id": "mX", "code": "RUNTIME_ERROR", "message": "..." }
    ],
    "audit": { /* optional: per-module timing, selected outputs, etc. */ }
  }
  ```

---

## 2) Validation (server-side)

Perform layered checks; return **scoped** errors so the FE can attach them later.

### 2.1 Schema & presence

* Ensure `entry_points`, `modules`, `connections` arrays exist.
* For each module:

  * `module_instance_id`, `module_ref`, `config`, `inputs[]`, `outputs[]` present.
  * Each pin has `node_id`, `type ∈ {str|int|float|bool|datetime}`, `position_index`, `group_index`.
* Node IDs must be **globally unique** across entries and pins.

### 2.2 Build indices (used by all later phases)

* `pin_by_id[node_id] -> { node_id, type, module_instance_id? (absent for entry), direction }`
* `module_by_id[module_instance_id] -> module instance`
* `input_to_upstream[input_pin_id]` from `connections` (must resolve uniquely)
* `out_to_downstreams[output_pin_id] -> [input_pin_id...]`

### 2.3 Edge cardinality & types

* **Inputs must have exactly one upstream**. If 0 or >1, error on that `to_node_id`.
* **Type equality rule:** `type(from) == type(to)` for every edge.

  * **No coercions on edges**. All conversions must go through the **Type Converter** module.
* **Self-loop** disallowed (`from` == `to`).

### 2.4 DAG / cycles (NetworkX)

* Construct a **pin-level** directed graph `G`:

  * **Nodes**: all pin node_ids (including entry pins)
  * **Edges**: `from_node_id -> to_node_id` for each connection
* Assert `is_directed_acyclic_graph(G) == True`. If false, return cycle edges.

### 2.5 Module-level invariants

* Fetch the module template’s I/O definition (NodeGroups / IOShape).
* Verify for this **instance**:

  * Group cardinalities (`min_count ≤ count(group) ≤ max_count`).
  * **Typing rules:**

    * For pins with **fixed types** (or `allowed_types`), ensure the concrete `type` conforms.
    * For **type variables** (e.g., `T`), **unify** within the module instance: first occurrence binds `T`, other `T`-pins must match; check against domain.
* Validate `config` against the module’s Pydantic model (Pydantic errors → validation errors scoped to `module_instance_id`).

### 2.6 Reachability and action presence

* Identify **Action** modules (by `kind="action"` via the module registry).
* Error if **no actions present**.
* Compute the set `R` = pins (and their modules) that lie on **any path that reaches an Action input**:

  * Take all **Action input pins**, do a **reverse BFS/DFS** on `G` to collect upstream pins/modules.
* Optionally warn on **dead branches** (pins/modules not in `R`).

**Return value:** `{"valid": true}` if all checks pass; otherwise `{"valid": false, "errors": [...]}`.

---

## 3) Compilation to an executable plan

We compile **module instances** into a runnable plan. We do **not** expand to per-pin steps; handlers work with pin IDs/values.

### 3.1 Prune to action-reachable subgraph

* Using `R` from §2.6, discard modules/pins/edges **not** on a path to an Action.
* This ensures we won’t schedule work that can’t affect an Action.

### 3.2 Build a **module-level DAG**

* Collapse the pin graph to a module graph `H`:

  * **Nodes**: all module_instance_ids (entries can be represented as a virtual “ENTRY” source set).
  * **Edges**: `A -> B` if **any** output pin of A connects to **any** input pin of B.
* Compute **topological order** or **topological generations**:

  * `topological_generations(H)` gives **layers** (`[layer0, layer1, ...]`) that we can run in parallel later.

### 3.3 For each module instance, compute an **input map**

* `input_map[input_pin_id] = upstream_output_pin_id` using `input_to_upstream`.
* Store module config and `module_ref` (to resolve the handler at runtime).

### 3.4 Persist compiled plan (concept)

```jsonc
{
  "pipeline_id": "...",
  "compiled_at": "...",
  "layers": [
    ["mA","mB"],   // layer 0 (no upstreams except entries)
    ["mC"],        // layer 1
    ["mAction"]    // layer 2
  ],
  "instances": {
    "mA": { "module_ref": "basic_text_cleaner:1.0.0", "config": { ... }, "input_map": { "mA:i0": "entry_1" } },
    "mB": { "module_ref": "type_converter:1.0.0", "config": { ... }, "input_map": { "mB:i0": "mA:o0" } },
    "mAction": { "module_ref": "order_create:1.0.0", "config": { ... }, "input_map": { "mAction:i1": "mB:o0" } }
  },
  "pins": {
    // optional: static facts for fast validation at run-time
    "mA:o0": { "type": "str" }, "mB:i0": { "type": "str" }, ...
  }
}
```

> Note: we’re intentionally **not** prescribing table schemas here; store however your backend currently expects.

---

## 4) Execution

### 4.1 Inputs

* `entry_values` is a dict keyed by **entry pin IDs** (`node_id`) with concrete values. Missing required entries → error.

### 4.2 Runtime value store

* Maintain a `values_by_pin: Dict[node_id, Any]`.

  * Initialize with `entry_values`.
  * When a module finishes, write all returned `{output_pin_id: value}` to this store.

### 4.3 Schedule only action-reachable work

* From the compiled plan’s **layers**, run only the modules included in the pruned plan (already action-reachable).
* A module is **ready** if **all** its input pins’ upstream output pins have values in `values_by_pin`.

### 4.4 Execution mode (v1)

* **Sequential by layer** (simple, deterministic):

  * For `layer` in `layers`:

    * For each `module_instance_id` in `layer`:

      * Build `inputs_for_handler = { input_pin_id: values_by_pin[ upstream_of(input_pin_id) ] }`
      * Resolve handler from `module_ref` (registry).
      * Call `handler.run(inputs_for_handler, cfg)` → `{output_pin_id: value}`
      * Write outputs into `values_by_pin`.
* **Parallel** (later): two options

  * Thread/async pool per layer (no extra deps).
  * **Dask**: build a small delayed DAG:

    * For each module instance, create `delayed` task that consumes the `delayed` futures of upstream producers and returns output dict; compute only **Action** modules’ tasks as roots. Because we already pruned to Action-reachable nodes, this is naturally minimal.

### 4.5 Failure policy (v1)

* **Fail-fast**: if any module throws, stop the run, return `"status": "failed"` with the error scoped to `module_instance_id`.
* (Optional v2) **Isolate branches**: allow independent subtrees to finish; report partial results.

### 4.6 Returned report

* Include timing per module, counts (modules executed, actions executed), and the **Action results** (whatever each action returns).
* Optionally include a subset of transformed values for audit (e.g., selected output names), controlled by a debug flag.

---

## 5) Error payloads (for FE)

Use a consistent structure across validation & runtime:

```json
{
  "code": "EDGE_TYPE_MISMATCH" | "CYCLE" | "MISSING_UPSTREAM" | "GROUP_CARDINALITY" | "TYPEVAR_MISMATCH" | "NO_ACTIONS" | "RUNTIME_ERROR",
  "message": "Human-friendly explanation.",
  "where": {
    "module_instance_id": "m_cleaner",     // optional
    "node_id": "m_cleaner:i0",             // optional
    "from_node_id": "mA:o0",               // optional
    "to_node_id": "mB:i1"                  // optional
  }
}
```

For now the FE should:

* disable “Create Pipeline” when invalid,
* **console.log** errors (later: inline highlights).

---

## 6) Notes for module handlers

* Handlers are located via `module_ref` (e.g., `"modules.text.basic_text_cleaner:BasicTextCleaner@1.0.0"`).
* **Inputs to `run`**: `{ input_pin_id → value }` (pin IDs only; order not guaranteed).
* **Outputs from `run`**: `{ output_pin_id → value }`.
* Handlers must **not assume** missing inputs; the executor guarantees readiness before invocation.
* Type correctness at edges is guaranteed by validation (handlers may still validate their own config and input shapes if they wish).

---

## 7) NetworkX & Dask specifics

* **NetworkX usage**:

  * Build graph at **pin level** (`DiGraph`), edges = connections.
  * `nx.is_directed_acyclic_graph(G)` for cycles.
  * Reverse traversal from **Action inputs** to compute the **action-reachable** set.
  * Build **module-level** `DiGraph` `H` by contracting pins to modules for scheduling.
  * Use `nx.algorithms.dag_layers(H)` (or `topological_generations`) to compute **layers** for execution.

* **Dask (optional v2)**:

  * For each module instance `m`, create:

    ```python
    @dask.delayed
    def run_m(**upstream_outputs):
        inputs = {input_pin_id: upstream_outputs[ upstream_pin_id ]}
        return handler.run(inputs, cfg)  # -> {output_pin_id: value}
    ```
  * Wire dependencies with the upstream producers’ delayed objects.
  * Compute only delayed nodes for **Action** modules.
  * Merge the resulting dicts into `values_by_pin`.

---

## 8) End-to-end flow (FE ↔ BE)

1. **User edits** → FE sends `/pipelines/validate` (debounced).

   * If invalid → disable Create; console.log(errors).
   * If valid → enable Create.

2. **User clicks Create** → BE re-validates, compiles, persists plan.

3. **Run** → POST `/pipelines/{id}/run` with `entry_values`.

   * BE executes only action-reachable paths, returns report.

---

## 9) Open items (please confirm)

* **Ordering in handlers**: v1 passes pin-keyed dicts (no guaranteed order). If some handlers benefit from ordered groups, we can add an optional **ordered view** later.
* **Deduplication**: if the same pipeline is saved unchanged, do we recompile or reuse prior compiled plan? (Out of scope for v1.)
* **Action results contract**: standardize a small envelope (`{status, payload}`) so FE can render consistently.

---

If this spec looks right, I’ll produce:

* a validation module (NetworkX-based) with the staged checks above,
* a compiler that emits the `layers` and `instances` maps, and
* a simple executor (sequential-by-layer) with a clean seam to swap in Dask later.
