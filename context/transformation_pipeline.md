# TRANSFORMATION PIPELINE — CONSOLIDATED DESIGN BRIEF (UPDATED)

> **Audience:** Me (to review) → then **Claude** (to analyze only; **do not** make code changes).
> **Scope:** Self-contained transformation service (own server/port). No assumptions about upstream systems. The runner accepts a dict of **entry values** and executes a compiled pipeline.

---

## 0) What changed in this update

* **Dynamic I/O is first-class now**: every module has **one list of inputs** and **one list of outputs**; each side may be **variable length** within min/max.
* **Random `node_id`s** are used for pins; **ordering** is conveyed by `position_index` (0..N-1) **per side**. No `group_id`.
* **Config references inputs by position** (e.g., `{input1}`, `{input2}`) when helpful (LLM example).
* **UI hints** are included next to `config_schema` to improve form UX (placeholders, widget choices, field ordering).
* We keep the previously agreed: module kinds (Transform/Action/Logic), Python-first modules + registry, dev “sync” to SQL catalog, compiler/validator, Dask executor, checksum, visual metadata separate from execution.

---

## 1) Goals & Principles

* **Single source of truth:** a **canonical pipeline JSON** (modules, pins, connections, configs).
* **Validate → Compile → Execute:** server validates and compiles JSON into compact **compiled rows**; **Dask** derives order/parallelism from dependencies.
* **Static DAG at runtime:** no graph mutation; “conditionals” are logic modules that forward values.
* **Wire by `node_id`, label by `name`:** execution uses IDs; names are for audits/UI.
* **Kinds:** separate base classes for **Transform**, **Action**, **Logic** with clear contracts.
* **Visual metadata is separate** (positions, canvas state only).
* **Immutability via versioning:** pipelines reference **module versions** (`name:semver`).
* **Checksum** ties compiled plan to what’s executed.

---

## 2) Data Model (service-local SQL)

> Names below are suggestions—use your existing models or adjust naming. Keep execution and visual concerns separate.

### `pipeline_definitions`

* `id` (PK)
* `name`, `description`
* `pipeline_json` (TEXT JSON) — canonical pipeline JSON (see §4)
* `plan_checksum` (CHAR(64)) — SHA-256 of compiled rows + entry list (canonicalized)
* `compiled_at` (DATETIME)
* `created_at`, `updated_at`

### `pipeline_steps` (compiled cache; read at run time)

* `id` (PK)
* `pipeline_id` (FK → pipeline_definitions.id)
* `plan_checksum` (CHAR(64))  — to ensure step rows match the exact plan
* `module_instance_id` (str)
* `module_ref` (str; `"name:version"`)
* `module_kind` (`"transform"|"action"|"logic"`)
* `module_config` (TEXT JSON) — validated config
* `input_field_mappings` (TEXT JSON: `{ this_input_node_id: upstream_node_id }`)
* Optional: `output_display_names` (JSON), `step_number` (int, optional)
* Index: `(pipeline_id, plan_checksum)`

### `module_catalog` (dev “sync” populates this for builder + validator)

* `id` (module name)
* `version` (semver)
* `name`, `description`, `color`, `category`
* `module_kind` (`transform|action|logic`)
* `meta` (JSON) — dynamic side rules (see §3)
* `config_schema` (JSON) — Pydantic JSON Schema
* `ui_hints` (JSON) — optional (placeholders, widget kinds, field order)
* `handler_name` (`"python.module.path:ClassName"`)
* `is_active` (bool), timestamps

### `pipeline_visual_state` (optional table/column)

* `pipeline_id` (FK)
* `visual_json` (TEXT JSON) — module positions, canvas pan/zoom, etc.
* `updated_at`, `updated_by`

---

## 3) Module system (Python-first)

We separate base classes by **kind** and keep a thin shared core.

### Shared contracts

```python
# modules/core/contracts.py
from typing import Optional, Literal, Dict, Any, List, Union
from pydantic import BaseModel, Field

Scalar = Literal["str","int","float","datetime","bool"]
VarType = Dict[str, Any]  # e.g. {"mode":"variable","allowed":["str","datetime"]}

class DynamicSide(BaseModel):
    allow: bool = True
    min_count: int = 0
    max_count: Optional[int] = None  # None = unbounded
    type: Union[Scalar, VarType] = "str"  # rule for all pins on this side

class ModuleMeta(BaseModel):
    inputs: DynamicSide = DynamicSide()   # one dynamic list per side
    outputs: DynamicSide = DynamicSide()  # one dynamic list per side

class CommonCore:
    id: str
    version: str
    title: str
    description: str
    kind: Literal["transform","action","logic"] = "transform"

    class ConfigModel(BaseModel): ...
    @classmethod
    def meta(cls) -> ModuleMeta: return ModuleMeta()

    # Optional UI hints to improve forms
    @classmethod
    def ui_hints(cls) -> Dict[str, Any]: return {}

    # Optional wiring validation hook (module-specific rules)
    @classmethod
    def validate_wiring(cls, module_instance_id: str, config: Dict[str, Any],
                        instance_inputs: List[Dict[str,Any]],
                        instance_outputs: List[Dict[str,Any]],
                        upstream_of_input: Dict[str,str]) -> List[Dict[str,Any]]:
        return []

    def run(self, inputs: Dict[str, Any], cfg: BaseModel, context: Any|None = None) -> Dict[str, Any]:
        raise NotImplementedError
```

```python
# Concrete bases by kind
class TransformModule(CommonCore): kind = "transform"
class ActionModule(CommonCore):    kind = "action"
class LogicModule(CommonCore):     kind = "logic"
```

### Registry & dev “sync”

* **Registry** (in memory): `module_ref ("name:version") → class`.
* **Dev sync** script reflects Python class metadata to `module_catalog` (I/O meta, `config_schema`, `ui_hints`, name, color, handler_name, kind).
* **Immutability:** changing behavior → bump `version`, re-sync. Old pipelines still reference old versions.

### Examples

**LLM Parser (Transform): variable inputs (str), exactly 1 output (str)**

```python
from modules.core.contracts import TransformModule, ModuleMeta, DynamicSide
from pydantic import Field, BaseModel

class LlmConfig(TransformModule.ConfigModel):
    model: str = Field(...)
    temperature: float = Field(0.1, ge=0.0, le=1.0)
    prompt: str = Field(..., description="Use {input1}, {input2}, ... to reference inputs by index (1-based).")

class LlmParser(TransformModule):
    id="llm_parser"; version="2.2.0"
    title="LLM Parser"; description="Parse fields from multiple text inputs with a prompt."

    @classmethod
    def meta(cls) -> ModuleMeta:
        return ModuleMeta(
            inputs=DynamicSide(allow=True, min_count=1, max_count=None, type="str"),
            outputs=DynamicSide(allow=True, min_count=1, max_count=1, type="str")
        )

    @classmethod
    def ui_hints(cls) -> dict:
        return {
            "order": ["model","temperature","prompt"],
            "widgets": {"temperature": "slider", "prompt": "textarea"},
            "placeholders": {"prompt": "Find date in {input1} and time in {input2}, return unified datetime."}
        }

    def run(self, inputs: Dict[str, Any], cfg: LlmConfig, context=None) -> Dict[str, Any]:
        # `context.instance_ordered_inputs` and `context.instance_ordered_outputs` are provided by the executor
        ordered_ins  = context.instance_ordered_inputs   # [(node_id, value), ...] in position_index order
        ordered_outs = context.instance_ordered_outputs  # [{"node_id": ...}, ...]
        # build prompt by substituting {input1}, {input2}, ...
        prompt = cfg.prompt
        for i, (_, val) in enumerate(ordered_ins, start=1):
            prompt = prompt.replace(f"{{input{i}}}", str(val))
        # call model (omitted), get result_text
        result_text = "...unified-datetime..."
        return { ordered_outs[0]["node_id"]: result_text }
```

**SQL Query (Transform): variable inputs (params), variable outputs (columns)**

```python
from modules.core.contracts import TransformModule, ModuleMeta, DynamicSide
from pydantic import BaseModel, Field
from typing import Dict, Any, List

class SqlQueryConfig(TransformModule.ConfigModel):
    conn: Dict[str,str]
    sql: str
    params_order: List[str] = []     # binds inputs by index to :named params
    columns: List[Dict[str,str]] = []  # [{"name":"eta","type":"datetime"}, ...]

class SqlQuery(TransformModule):
    id="sql_query"; version="1.0.0"
    title="SQL Query"; description="Run a parameterized SELECT and return columns."

    @classmethod
    def meta(cls) -> ModuleMeta:
        # both sides variable; both allow base scalar types
        any_scalar = {"mode":"variable", "allowed":["str","int","float","datetime","bool"]}
        return ModuleMeta(
            inputs = DynamicSide(allow=True, min_count=0, max_count=None, type=any_scalar),
            outputs= DynamicSide(allow=True, min_count=1, max_count=None, type=any_scalar)
        )

    def run(self, inputs: Dict[str, Any], cfg: SqlQueryConfig, context=None) -> Dict[str, Any]:
        ins  = [v for _, v in context.instance_ordered_inputs]
        outs = context.instance_ordered_outputs
        named = dict(zip(cfg.params_order, ins))
        row = (context.db.query_one(cfg.sql, named) if context and getattr(context,"db",None) else {}) or {}
        return { outs[i]["node_id"]: row.get(spec["name"]) for i, spec in enumerate(cfg.columns) }
```

**Action example** (`order_create`) remains the same pattern; the runner will mark actions `pure=False` and apply retries/idempotency.

---

## 4) Canonical Pipeline JSON (source of truth)

* **Pins** use random `node_id`s.
* **Order** is established by `position_index` per side.
* **Connections** always go **from entry/output → input**.

```jsonc
{
  "schema_version": "1.3",
  "name": "ACME — Normalize + ETA + Create Order",
  "description": "Example with LLM + SQL + Action.",
  "entry_points": [
    { "node_id": "in_order_no",  "name": "order_no",  "type": "str" },
    { "node_id": "in_date_text", "name": "date_text", "type": "str" },
    { "node_id": "in_time_text", "name": "time_text", "type": "str" },
    { "node_id": "in_address",   "name": "address",   "type": "str" }
  ],
  "modules": [
    {
      "module_instance_id": "m_llm",
      "module_ref": "llm_parser:2.2.0",
      "module_kind": "transform",
      "config": {
        "model": "claude-3.5",
        "temperature": 0.0,
        "prompt": "Please find the date from {input1} and the time from {input2} and combine them into a single unified datetime string."
      },
      "inputs": [
        { "node_id": "A1", "direction": "in",  "type": "str", "name":"date_part", "position_index": 0 },
        { "node_id": "B2", "direction": "in",  "type": "str", "name":"time_part", "position_index": 1 }
      ],
      "outputs": [
        { "node_id": "C3", "direction": "out", "type": "str", "name":"unified_dt", "position_index": 0 }
      ]
    },
    {
      "module_instance_id": "m_order_create",
      "module_ref": "order_create:0.5.0",
      "module_kind": "action",
      "config": {
        "conn": { "secret": "SQL_ORDERS_RW" },
        "table": "orders",
        "idempotency": { "key_template": "ORD-{{order_no}}" }
      },
      "inputs": [
        { "node_id":"D4","direction":"in","type":"str","name":"order_no","position_index":0 },
        { "node_id":"E5","direction":"in","type":"str","name":"eta_text","position_index":1 },
        { "node_id":"F6","direction":"in","type":"str","name":"address","position_index":2 }
      ],
      "outputs": [
        { "node_id":"G7","direction":"out","type":"int","name":"order_id","position_index":0 }
      ]
    }
  ],
  "connections": [
    { "from_node_id": "in_date_text", "to_node_id": "A1" },
    { "from_node_id": "in_time_text", "to_node_id": "B2" },
    { "from_node_id": "C3",           "to_node_id": "E5" },
    { "from_node_id": "in_order_no",  "to_node_id": "D4" },
    { "from_node_id": "in_address",   "to_node_id": "F6" }
  ]
}
```

---

## 5) Visual metadata (separate)

Only **module positions** and **canvas state**:

```jsonc
{
  "schema_version": "1.0",
  "canvas": { "pan": { "x": 120, "y": 80 }, "zoom": 0.9, "gridSize": 12, "snap": true },
  "modules": {
    "m_llm":          { "x": 380, "y": 200, "collapsed": false, "z": 1 },
    "m_order_create": { "x": 760, "y": 240, "collapsed": false, "z": 1 }
  }
}
```

Ports are placed at render time using **module box + ordered pins** (by `position_index`). Do **not** include this visual JSON in the plan checksum.

---

## 6) Validation (server)

**Structural graph checks**

* Unique IDs (modules & pins).
* Direction (entry/output → input).
* **Cardinality**: each input has **exactly 1** upstream.
* **Type compatibility** across edges (source type can feed target type; apply your rules).
* **DAG** (no cycles).
* **Reachability**: each non-entry input reachable from at least one entry.
* **Terminality**: at least one Action exists; transform-only branches end in Actions (policy-based).

**Module-instance checks**

* `module_ref` exists in registry (and optional catalog).
* **Side constraints** (per side):

  * Length in `[min_count, max_count or ∞]`
  * All pins have correct `direction`
  * Each pin’s **`type`** satisfies the side rule (fixed or variable allowed set)
  * **`position_index`** values are integers, unique, and contiguous from `0..N-1`
* **Config schema** validated via Pydantic.
* **Optional `validate_wiring`**: module-specific rules (e.g., ensure LLM prompt references ≤ `len(inputs)`).

**Failure response**

```jsonc
{
  "ok": false,
  "errors": [
    { "code":"INPUT_CARDINALITY", "where":{"module_instance_id":"m_llm","node_id":"A1"}, "message":"Input has 0 sources; exactly 1 required." },
    { "code":"TYPE_MISMATCH", "edge":{"from_node_id":"C3","to_node_id":"E5"}, "message":"Cannot connect 'str' to 'datetime'." }
  ]
}
```

**Success**

* Emit compiled rows; compute `plan_checksum`; persist steps keyed by `(pipeline_id, plan_checksum)`; return:

```jsonc
{ "ok": true, "compiled": { "plan_checksum": "a1c3...", "steps_count": 4 } }
```

---

## 7) Compilation (JSON → compiled rows)

* Build a node-level DAG (pins = nodes; edges = connections).
* For each module instance, emit a **compiled row**:

  * `module_instance_id`, `module_ref`, `module_kind`, **validated** `module_config`
  * **`input_field_mappings`**: `{ this_input_node_id: upstream_node_id }` (uses concrete random IDs)
  * (Optional) copy `outputs[*].name` into `output_display_names` for audit readability
* Compute **checksum** over canonicalized compiled rows + entry list, store with rows and the pipeline definition.

---

## 8) Execution (Dask)

Inputs:

* `rows` = compiled rows (by `pipeline_id`, `plan_checksum`)
* `entry_values` = `{ entry_node_id: str }` (caller passes these)
* `registry` = map `module_ref → class`
* `context` = runtime handles (DB client, idempotency, secrets); **executor** also injects **instance pin order**:

  * `context.instance_ordered_inputs  = sorted(instance.inputs,  key=position_index)`
  * `context.instance_ordered_outputs = sorted(instance.outputs, key=position_index)`

Execution sketch:

```python
from dask import delayed, compute

def execute(rows, entry_values, registry, instance_metas, context):
    # delayed constants for entries
    values = {nid: delayed(lambda x=x: x)() for nid, x in entry_values.items()}
    sinks = []

    for step in rows:
        spec_cls = registry[step["module_ref"]]; spec = spec_cls()
        cfg = spec_cls.ConfigModel.model_validate(step["module_config"])
        meta = instance_metas[step["module_instance_id"]]  # { "inputs":[...], "outputs":[...] }

        bound_inputs = {in_id: values[src_id] for in_id, src_id in step["input_field_mappings"].items()}
        ctxt = context.fork() if hasattr(context, "fork") else context
        setattr(ctxt, "instance_ordered_inputs",  [(p["node_id"], bound_inputs[p["node_id"]]) for p in sorted(meta["inputs"],  key=lambda x: x["position_index"])])
        setattr(ctxt, "instance_ordered_outputs", [p for p in sorted(meta["outputs"], key=lambda x: x["position_index"])])

        pure = (spec_cls.kind != "action")
        task = delayed(spec.run, pure=pure)(bound_inputs, cfg, ctxt)

        # fan-out outputs
        for p in meta["outputs"]:
            values[p["node_id"]] = delayed(lambda d, nid=p["node_id"]: d[nid])(task)

        if spec_cls.kind == "action":
            sinks.append(task)

    compute(*(sinks or list(values.values())))
    return values
```

* **Parallelism** comes from Dask inferring independent tasks.
* **Actions** are `pure=False` and should be wrapped with retry/timeout/idempotency as needed.
* **Audits**: capture timings/values (as needed) for step logs.

---

## 9) API surface (minimal)

* `GET /modules` → catalog rows (for builder): `module_ref`, `module_kind`, `meta` (dynamic side rules), `config_schema`, `ui_hints`, name/color/category.
* `POST /pipelines/validate-and-compile`

  * Body: canonical pipeline JSON
  * Returns: `{ok:false, errors[]}` OR `{ok:true, compiled:{plan_checksum, steps_count}}`
* `POST /pipelines/{id}/execute`

  * Body: `{ "plan_checksum":"...", "entry_values": { "<entry_node_id>": "<string>" } }`
  * Loads compiled rows by `(id, plan_checksum)` and runs once.

---

## 10) Testing & Observability

* **Unit**: Pydantic config validation; module `run()` happy paths; wiring validator hooks.
* **Validation**: cycles, type mismatches, cardinality, side constraints, reachability, terminality.
* **Integration**: compile sample pipeline → snapshot compiled rows & checksum; execute with a local Dask scheduler; assert parallel sections overlap in timing.
* **Graph viz** (optional): export Dask graph for debugging.

---

## 11) For Claude — what to analyze (do not change code)

* Compare this design to the current code & DB around transformation pipelines.
* Identify **gaps** (models, compiler, executor, registry, endpoints, tests).
* Propose a **migration/implementation plan** (DB deltas, services, sequencing).
* Call out **risks/trade-offs** (dynamic I/O edge cases, type coercion, long-running actions, LLM variability, idempotency).
* Provide **specific recommendations** and **clarifying questions**.
* Be **direct and critical** where warranted; avoid unearned praise or nitpicks.

---

### TL;DR

* Modules have **one dynamic list of inputs** and **one dynamic list of outputs**; pins use **random IDs** and `position_index` for order.
* **UI hints** travel with `config_schema` to render better forms.
* The compiler emits **`input_field_mappings`** over concrete IDs; **Dask** handles ordering/parallelism.
* **Transform/Action/Logic** bases keep validation and runtime behavior clean.
* **Visual metadata** is UI-only.
* **Checksum** locks runs to the compiled plan.
