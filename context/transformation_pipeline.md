# TRANSFORM_PIPELINE_PROPOSAL.md

> **Purpose**
> This document describes the proposed design for the **transformation pipeline** in the ETO system. It reflects our recent decisions around *modules vs. nodes*, *base scalar types only*, *dynamic I/O for base modules*, *fixed I/O for custom modules (for now)*, *template-version–scoped immutability*, and an **in-process DAG executor** (Dask) with a publish/compile step that emits a linearized execution plan.

---

## 0) Vocabulary & Ground Rules

* **Module** = an executable logic component (e.g., `text_clean`, `type_convert`, `llm_parser`, `sql_query`).
* **Node (pin)** = an input or output terminal on a module. Connections are **node_id → node_id**.
* **Base scalar types only**: `str | int | float | datetime | bool`.
* **Entry points** (pipeline inputs) are always `str` (extracted from PDF).
* **Type conversion** occurs via a dedicated `type_convert` module (special “style” module).
* **User-defined output names**: users name **output** nodes; **input** nodes inherit the upstream output’s name unless explicitly overridden.
* **Dynamic I/O**:

  * **Base modules** may declare `static` or `dynamic` node lists. Dynamic lists can have min/max/default counts and fixed or variable type rules.
  * **Custom modules (for now)**: **fixed** inputs/outputs with **defined counts and types** (no dynamic I/O for customs in this phase).
* **Immutability/versioning**: `PdfTemplateVersion` is the immutable unit that **pins** extraction settings **and** a pipeline snapshot.
* **Compiled plan**: at publish, we validate → expand → topo sort → materialize **compiled steps**; execution reads those steps.
* **Executor**: use **Dask (delayed)** for in-process DAG execution and parallel branches.

---

## 1) Data Model Additions (SQLAlchemy / SQL Server)

> We keep most of the current schema. The key is: pipeline JSON is stored on **`PdfTemplateVersionModel`**, and **compiled steps** are keyed to `template_version_id`. Runs copy the plan checksum for replay safety. Per-node artifacts are optional but recommended.

### 1.1 `PdfTemplateVersionModel` (add fields)

* `pipeline_definition: TEXT` — canonical JSON blob (see §2)
* `pipeline_plan_checksum: CHAR(64)` — hash of flattened plan (modules + versions + configs + wiring)
* `compiled_at: DATETIME2 NULL` — timestamp of last successful compile

> Keep your existing fields (`signature_objects`, `extraction_fields`, etc.).

### 1.2 `TransformationPipelineStepModel` (augment, cache of compiled plan)

Add:

* `template_version_id: INT FK → pdf_template_versions.id`
* (optional) `origin_module_instance_id: VARCHAR(100)` — which instance produced this step
* (optional) `origin_input_node_id` / `origin_output_node_id` — for traceability
* (optional) `execution_hints: TEXT` — JSON (retries, timeout)
* Ensure a composite index on `(template_version_id, step_number)`.

> Treat **steps** as **derived** cache. Safe to wipe & rebuild from `pipeline_definition`.

### 1.3 `transformation_artifacts` (new, optional but useful)

Per-node I/O snapshots for audit/replay:

* `id PK`
* `run_id FK → eto_runs.id`
* `template_version_id FK`
* `node_id VARCHAR(100)` — the **output** node_id this artifact represents
* `export_name VARCHAR(255) NULL` — user-visible name (if final output)
* `effective_type VARCHAR(16)` — concrete scalar type
* `value_json TEXT` — value serialized (e.g., stringified ISO date, numeric, bool)
* `content_hash CHAR(64) NULL`
* `created_at DATETIME2 DEFAULT getutcdate()`

### 1.4 `EtoRunModel` (augment)

* `template_version_id: INT NULL` — pin the exact template version used
* `pipeline_plan_checksum: CHAR(64) NULL` — copied from the template version at run start

---

## 2) Canonical Pipeline JSON (stored on `PdfTemplateVersionModel.pipeline_definition`)

> **Modules** live in `modules[]`. Each module declares **inputs** and **outputs** as lists of **nodes** with unique **node_id**. **Connections** are node-to-node. **Final outputs** list which **output node_ids** are exported as pipeline results. All entry points are `str`.

```jsonc
{
  "schema_version": "1.0",
  "name": "ACME v4 – Transform",
  "description": "Normalize PDF fields and assemble Order row.",

  "entry_points": [
    { "node_id": "in_order_no",  "name": "order_no",  "type": "str" },
    { "node_id": "in_ship_date", "name": "ship_date", "type": "str" },
    { "node_id": "in_address",   "name": "address",   "type": "str" },
    { "node_id": "in_qty",       "name": "qty",       "type": "str" }
  ],

  "modules": [
    {
      "module_instance_id": "m_clean",
      "module_ref": { "kind": "base", "id": "text_clean", "version": "1.2.0" },
      "config": { "strip": true, "collapse_space": true },

      "inputs": [
        { "node_id": "n_clean_in",  "direction": "in",  "type": "str", "position_index": 0 }
      ],
      "outputs": [
        { "node_id": "n_clean_out", "direction": "out", "type": "str", "name": "address_cleaned", "position_index": 0 }
      ],

      "io_layout": { "kind": "static" }
    },

    {
      "module_instance_id": "m_toint",
      "module_ref": { "kind": "base", "id": "type_convert", "version": "1.0.0" },
      "config": { "to_type": "int", "on_error": "null" },

      "inputs":  [ { "node_id": "n_toint_in",  "direction": "in",  "type": "str", "position_index": 0 } ],
      "outputs": [ { "node_id": "n_toint_out", "direction": "out", "type": "int", "name": "qty_int", "position_index": 0 } ],
      "io_layout": { "kind": "static" }
    },

    {
      "module_instance_id": "m_eta",
      "module_ref": { "kind": "base", "id": "llm_parser", "version": "2.1.0" },
      "config": {
        "model": "claude-3.5",
        "temperature": 0.1,
        "prompt": "Given ship date {ship_date} and address {address}, estimate delivery date.",
        "bindings": {
          "ship_date": { "source": "node", "node_id": "in_ship_date" },
          "address":   { "source": "node", "node_id": "n_clean_out" }
        }
      },

      "inputs": [
        { "node_id": "n_eta_date_in", "direction": "in", "type": { "mode": "variable", "allowed": ["str","datetime"] }, "position_index": 0 },
        { "node_id": "n_eta_addr_in", "direction": "in", "type": "str", "position_index": 1 }
      ],
      "outputs": [
        { "node_id": "n_eta_out",     "direction": "out", "type": "datetime", "name": "eta", "position_index": 0 }
      ],

      "io_layout": { "kind": "static" }
    }
  ],

  "connections": [
    { "from_node_id": "in_address",   "to_node_id": "n_clean_in"   },
    { "from_node_id": "in_qty",       "to_node_id": "n_toint_in"   },
    { "from_node_id": "in_ship_date", "to_node_id": "n_eta_date_in"},
    { "from_node_id": "n_clean_out",  "to_node_id": "n_eta_addr_in"}
  ],

  "final_outputs": [
    { "node_id": "n_eta_out",   "export_name": "eta"      },
    { "node_id": "n_toint_out", "export_name": "quantity" }
  ]
}
```

### Notes

* **Module inputs/outputs** are explicit lists of **nodes** with stable `node_id` and `position_index`.
* **Output names** (`name`) are user-defined and propagate for audit. Inputs may omit names; downstream the compiler can attach an `effective_name` (from upstream).
* **Variable type** → `{ "mode": "variable", "allowed": [...] }`.
* **Dynamic I/O (base modules only)**: set `io_layout.kind = "dynamic"` and include rules (min/max/default, auto-naming). *(Not shown above; see §3.3 for schema.)*
* **Custom modules (current phase)**: allowed, but **must** declare *fixed* input/output nodes with *fixed types*. The compiler will expand them to base steps at publish.

---

## 3) JSON Shape (formalized sketch)

> Strongly typed JSON helps publishing/validation and IDE hints. Below are the minimal Pydantic-style models Claude can mirror mentally (no code changes yet).

### 3.1 Types

* **Fixed**: `"type": "str"`
* **Variable**:

  ```json
  { "type": { "mode": "variable", "allowed": ["str","int","float","datetime","bool"] } }
  ```

### 3.2 Node Pin

```jsonc
{
  "node_id": "n_eta_out",
  "direction": "out",               // "in" | "out"
  "type": "datetime",               // fixed OR variable declaration
  "name": "eta",                    // user-defined for outputs; optional for inputs
  "position_index": 0
}
```

### 3.3 IO Layout (static vs. dynamic, base modules only)

```jsonc
{
  "io_layout": {
    "kind": "dynamic",
    "outputs": {
      "type_mode": { "mode": "fixed", "type": "str" },  // or variable {mode:"variable",allowed:[...]}
      "default_count": 2,
      "min": 1,
      "max": 10,
      "name_rule": { "pattern": "line_{i+1}" }          // auto-name suggestion
    }
  }
}
```

### 3.4 Module Reference

```jsonc
// Base module
{ "kind": "base", "id": "text_clean", "version": "1.2.0" }

// Custom module (fixed I/O only in this phase)
{ "kind": "custom", "id": "NormalizeAddress", "version": 3 }
```

> At publish, **custom** modules are **expanded** (namespaced inner node_ids) to base steps. Execution never needs to know about customs.

---

## 4) Publish / Compile (Validation → Plan → Steps)

**When a template version is published or activated**, run a **compiler**:

1. **Validate**:

   * Unique `module_instance_id` and `node_id` ecosystem-wide.
   * Acyclic graph (build graph over `node_id`s).
   * Every `connection.from_node_id` and `to_node_id` exists and is `out → in`.
   * **Type compatibility** per edge:

     * fixed → fixed must match exactly;
     * fixed → variable must be within `allowed`;
     * variable → variable OK iff `intersection(allowed)` non-empty (prefer prior fixed to concretize; otherwise require a `type_convert` step).
   * **Custom modules**: confirm fixed I/O and types; expand to base modules with namespaced node_ids.
   * Module config validation (per module’s schema).

2. **Inline expansion (customs)** → flatten to base modules.

3. **Topological sort** and compute **parallel groups**.

4. **Compute `pipeline_plan_checksum`** — hash of flattened modules+versions+configs+wiring.

5. **Persist compiled steps** into `TransformationPipelineStepModel` keyed by `template_version_id`.

6. Update `PdfTemplateVersionModel.pipeline_plan_checksum` and `compiled_at`.

> **Important**: `TransformationPipelineStepModel` is **derived cache**, not the source of truth. The JSON on `PdfTemplateVersionModel` is canonical.

---

## 5) Execution (Dask)

> The executor reads compiled steps for a `template_version_id`, binds node inputs from entry points and upstream outputs, and runs each base module function. Use **Dask Delayed** to parallelize independent groups and then **barrier** between groups.

**Conceptual flow (pseudocode):**

```python
# Load compiled steps for template_version_id
steps = load_steps_ordered(template_version_id)

values = {}  # node_id -> delayed/result

for parallel_group in group_by_parallel_id(steps):
    delayed_tasks = []
    for step in parallel_group:
        module_spec = REGISTRY[(step.module_id, step.module_version)]
        cfg = module_spec.Config.parse_raw(step.module_config_json)

        # Resolve inputs (they are node_ids from entry_points or prior outputs)
        kwargs = { pin_name: values[src_node_id] for pin_name, src_node_id in step.input_bindings.items() }

        task = dask.delayed(module_spec.run)(kwargs, cfg)
        for out_node_id in step.output_node_ids:
            values[out_node_id] = dask.delayed(lambda d, nid=out_node_id: d[nid])(task)

        delayed_tasks.append(task)

    dask.compute(*delayed_tasks)  # barrier per parallel group

# Export final outputs by node_id mapping
result = { fo.export_name: values[fo.node_id] for fo in final_outputs }
```

* **Retries/timeouts**: wrap `module_spec.run` with retry policies per step; LLM/SQL-heavy steps should have jittered retry and timeouts.
* **Idempotency**: hash `(template_version_id, node_id, inputs)` to optionally short-circuit repeats.
* **Artifacts**: persist per-node output (typed) for audit in `transformation_artifacts`.

> **Why Dask?**: It’s a lightweight, embeddable DAG executor with delayed/lazy computation and parallelism—fits our “library inside app” requirement and avoids heavy external schedulers. Perfect for parsing and executing complex pipelines in-process.

---

## 6) Module Registry (runtime)

> Each base module is registered with (a) its config model, (b) pin rules, (c) `run(inputs, cfg) -> dict[node_id -> value]`. The runtime binds by **node_id**, so dynamic output nodes are just more entries in the dict.

**Skeleton:**

```python
class ModuleSpec:
    id: str
    version: str
    Config: type
    input_rules: ...
    output_rules: ...
    def run(inputs: dict[str, Any], cfg) -> dict[str, Any]: ...

REGISTRY: dict[tuple[str,str], ModuleSpec] = {}

def register(spec: ModuleSpec): REGISTRY[(spec.id, spec.version)] = spec
```

* `type_convert` guarantees `output.type == cfg.to_type`.
* `text_clean` returns one or many outputs (depending on dynamic config), keyed by **output node_id**.
* `llm_parser` uses `config.bindings` to build prompts at runtime and emits outputs keyed by node_id.

---

## 7) Migration Sketch

1. **Add columns** to `pdf_template_versions`:

   * `pipeline_definition NVARCHAR(MAX)`
   * `pipeline_plan_checksum CHAR(64)`
   * `compiled_at DATETIME2 NULL`

2. **Augment** `transformation_pipeline_steps`:

   * `template_version_id INT NOT NULL` (+ index)
   * Optional trace fields

3. **Optional**: create `transformation_artifacts`.

4. **Backfill**: existing templates can get an initial pipeline JSON (even empty) and compile to zero steps.

---

## 8) Examples (compact)

### 8.1 Simple type conversion chain

* Entry `qty:str` → `type_convert(to=int)` → `qty_int:int` (final)

```jsonc
"modules": [
  {
    "module_instance_id": "m_toint",
    "module_ref": { "kind": "base", "id": "type_convert", "version": "1.0.0" },
    "config": { "to_type": "int", "on_error": "null" },
    "inputs":  [{ "node_id": "n_toint_in",  "direction":"in",  "type":"str", "position_index":0 }],
    "outputs": [{ "node_id": "n_toint_out", "direction":"out", "type":"int", "name":"qty_int", "position_index":0 }],
    "io_layout": { "kind": "static" }
  }
],
"connections": [
  { "from_node_id": "in_qty", "to_node_id": "n_toint_in" }
],
"final_outputs": [
  { "node_id": "n_toint_out", "export_name": "quantity" }
]
```

### 8.2 Base module with dynamic outputs (lines)

```jsonc
"io_layout": {
  "kind": "dynamic",
  "outputs": {
    "type_mode": { "mode": "fixed", "type": "str" },
    "default_count": 2, "min": 1, "max": 10, "name_rule": { "pattern": "line_{i+1}" }
  }
}
```

---

## 9) Why this matches our constraints

* **Modules vs Nodes**: aligned (modules = logic, nodes = pins).
* **Scalar types only**: all ports restricted to base scalars; complex structures are *user-composed* and/or serialized strings.
* **Dynamic I/O where needed**: dynamic lists on base modules only; customs are fixed for now.
* **User-defined output names**: carried on outputs and propagated to inputs for auditability.
* **Entry points are `str`**: explicit.
* **Dask**: used to parse/execute complex DAGs in-process with parallel branches.
* **Template-version immutability**: pipelines live on `PdfTemplateVersion`, compiled steps cache on `template_version_id`.

---

## 10) Instructions for Claude (how to use this file)

> **Read carefully—do not make code changes.**

1. **Goal**: Analyze this proposal against the current state of the project’s transformation pipeline.
2. **Scope**:

   * Compare the **current** SQLAlchemy models and execution code with the **proposed** storage model (pipeline JSON on `PdfTemplateVersion`, compiled steps on `template_version_id`, optional artifacts), the **JSON shapes**, and the **Dask-based execution plan**.
   * Identify **what would need to change** (data models, compile step, executor, registry).
3. **Constraints to honor**:

   * Modules vs nodes semantics exactly as defined here.
   * Base scalar types only; entry points are `str`.
   * Base modules may have **dynamic I/O**; **custom modules are fixed I/O** for now.
   * Steps are a **derived cache**; the JSON on `PdfTemplateVersion` is canonical.
   * Use **Dask** for in-process execution/parallelism; no heavy external orchestrator.
4. **Deliverables (from you, Claude)**:

   * A written **gap analysis** (no edits to code): what differs between current implementation and this proposal.
   * A **migration plan** outline (DB changes, publish/compile implementation, executor adjustments).
   * **Risk & trade-off notes** (e.g., type coercion edge cases, dynamic I/O UX implications, LLM retry/idempotency).
   * **Concrete recommendations** where appropriate.
   * **Questions** to clarify any ambiguous points (be critical and honest; don’t rubber-stamp).
5. **Do not**:

   * Do **not** modify code.
   * Do **not** praise or critique for its own sake—focus on actionable insight and legitimate concerns.

> After your analysis, we’ll iterate on open questions (especially dynamic I/O UX and validation rules) and then implement the publisher and minimal Dask executor.

---

*End of document.*
