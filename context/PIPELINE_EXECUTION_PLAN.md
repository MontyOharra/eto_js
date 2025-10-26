# Pipeline Execution Implementation Plan

## Overview

This document outlines the step-by-step implementation plan for pipeline execution in the new server (`server-new/`), based on the old server's Dask-based execution architecture.

**Goal**: Execute compiled pipeline definitions using Dask's lazy task graph with full audit trail persistence and fail-fast error handling.

---

## Architecture Summary

### Core Concepts

1. **Lazy Evaluation**: All modules wrapped in Dask `delayed()` - nothing executes until `compute()`
2. **Dependency Tracking**: `producer_of_pin` dict maps each pin ID to its delayed producer value
3. **Action Barrier**: Enforces transform→action ordering (all transforms must complete before any actions run)
4. **Fail Fast**: First module error stops entire run (Dask raises on first failure)
5. **Audit Trail**: Every module execution persisted with inputs/outputs/errors
6. **Pin-Level Granularity**: Module outputs split per-pin for precise dependency tracking

### Execution Flow

```
1. Load pipeline definition + compiled steps
2. Create execution run record (status: "processing")
3. Validate entry point values (fail if missing required)
4. Seed producer_of_pin with entry values (wrapped in delayed)
5. For each Transform/Logic module:
   - Create delayed task (waits for upstream producers)
   - Task executes: module.run() → {output_pin_id: value}
   - Split outputs into per-pin delayed futures
   - Update producer_of_pin for downstream dependencies
6. Create action barrier (delayed task that waits for all non-actions)
7. For each Action module:
   - Same as transform, but depends on barrier + upstreams
8. Execute: compute(*all_tasks)
9. Update run status (success/failed)
10. Return execution run record
```

---

## Implementation Checklist

### Phase 1: Foundation (Data Layer)

#### ✅ Step 1: Create Domain Types
**File**: `server-new/src/shared/types/pipeline_execution.py` (NEW)

**Types to create**:

```python
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime

class InstanceNodePin(BaseModel):
    """Pin metadata for module execution context"""
    node_id: str
    direction: str  # 'in' | 'out'
    type: str
    name: str
    label: str
    position_index: int
    group_index: int
    type_var: Optional[str] = None
    allowed_types: List[str] = []
    module_instance_id: Optional[str] = None  # For lookups

class ModuleExecutionContext(BaseModel):
    """Context passed to module handlers during execution"""
    module_instance_id: str
    inputs: List[InstanceNodePin]
    outputs: List[InstanceNodePin]
    services: Any = None  # ServiceContainer reference

class PipelineExecutionRunCreate(BaseModel):
    """Create new pipeline execution run"""
    eto_run_id: int
    status: str = "processing"  # 'processing' | 'success' | 'failed'
    executed_actions: Optional[str] = None
    started_at: Optional[datetime] = None

class PipelineExecutionRun(BaseModel):
    """Domain model for pipeline execution run"""
    id: int
    eto_run_id: int
    status: str
    executed_actions: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

class PipelineExecutionStepCreate(BaseModel):
    """Create new execution step audit record"""
    run_id: int
    module_instance_id: str
    step_number: int
    inputs: Dict[str, Dict[str, Any]]  # {node_name: {value, type}}
    outputs: Dict[str, Dict[str, Any]]  # {node_name: {value, type}}
    error: Optional[str] = None

class PipelineExecutionStep(BaseModel):
    """Domain model for execution step"""
    id: int
    run_id: int
    module_instance_id: str
    step_number: int
    inputs: Dict[str, Dict[str, Any]]
    outputs: Dict[str, Dict[str, Any]]
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
```

**Why first?** All other components depend on these types.

**Test criteria**: Types can be imported and instantiated successfully.

---

#### ✅ Step 2: Create Execution Repositories

**File 1**: `server-new/src/shared/database/repositories/eto_run_pipeline_execution.py` (NEW)

```python
from shared.database.repositories.base import BaseRepository
from shared.database.models import EtoRunPipelineExecutionModel
from shared.types.pipeline_execution import PipelineExecutionRun, PipelineExecutionRunCreate

class EtoRunPipelineExecutionRepository(BaseRepository[EtoRunPipelineExecutionModel]):
    def __init__(self, connection_manager):
        super().__init__(EtoRunPipelineExecutionModel, connection_manager)

    def create(self, data: PipelineExecutionRunCreate) -> PipelineExecutionRun:
        """Create new execution run"""
        # TODO: implement
        pass

    def get_by_id(self, run_id: int) -> Optional[PipelineExecutionRun]:
        """Get execution run by ID"""
        # TODO: implement
        pass

    def update_status(self, run_id: int, status: str, completed_at: Optional[datetime] = None) -> PipelineExecutionRun:
        """Update execution run status"""
        # TODO: implement
        pass
```

**File 2**: `server-new/src/shared/database/repositories/eto_run_pipeline_execution_step.py` (NEW)

```python
from shared.database.repositories.base import BaseRepository
from shared.database.models import EtoRunPipelineExecutionStepModel
from shared.types.pipeline_execution import PipelineExecutionStep, PipelineExecutionStepCreate

class EtoRunPipelineExecutionStepRepository(BaseRepository[EtoRunPipelineExecutionStepModel]):
    def __init__(self, connection_manager):
        super().__init__(EtoRunPipelineExecutionStepModel, connection_manager)

    def create(self, data: PipelineExecutionStepCreate) -> PipelineExecutionStep:
        """Create execution step audit record"""
        # TODO: implement
        pass

    def get_steps_by_run_id(self, run_id: int) -> List[PipelineExecutionStep]:
        """Get all steps for an execution run, ordered by step_number"""
        # TODO: implement
        pass
```

**Update**: `server-new/src/shared/database/repositories/__init__.py`
- Add imports for new repositories

**Why second?** Service needs these to persist data. Can unit test repositories independently.

**Test criteria**:
- Can create execution run record
- Can update run status
- Can create execution step records
- Can retrieve steps by run ID

---

### Phase 2: Service Foundation

#### ✅ Step 3: Create PipelineExecutionService Skeleton

**File**: `server-new/src/features/pipelines/service_execution.py` (NEW)

```python
"""
Pipeline Execution Service
Builds a Dask task graph from compiled steps and executes with auditing.

Usage:
    service = PipelineExecutionService(cm, services)
    run = service.execute_pipeline(
        pipeline_definition_id=123,
        eto_run_id=456,
        entry_values={"origin": "SFO", "destination": "LAX"}
    )
"""

from typing import Dict, Any, List, Tuple, Optional
import logging
from datetime import datetime
from dask.delayed import delayed
from dask.base import compute

from shared.database.repositories import (
    PipelineDefinitionRepository,
    PipelineDefinitionStepRepository,
    EtoRunPipelineExecutionRepository,
    EtoRunPipelineExecutionStepRepository,
)
from shared.utils.registry import ModuleRegistry
from shared.types.pipelines import PipelineDefinition, PipelineDefinitionStep
from shared.types.pipeline_execution import (
    PipelineExecutionRun,
    PipelineExecutionRunCreate,
    PipelineExecutionStepCreate,
    ModuleExecutionContext,
    InstanceNodePin,
)

logger = logging.getLogger(__name__)


class PipelineExecutionService:
    """Executes compiled pipelines using Dask task graphs"""

    def __init__(self, connection_manager, services=None):
        """
        Args:
            connection_manager: Database connection manager
            services: ServiceContainer for accessing other services (optional)
        """
        if not connection_manager:
            raise RuntimeError("Database connection manager is required")

        self.connection_manager = connection_manager
        self.module_registry = ModuleRegistry()
        self.services = services

        # Repositories
        self.pipeline_repo = PipelineDefinitionRepository(connection_manager)
        self.step_repo = PipelineDefinitionStepRepository(connection_manager)
        self.run_repo = EtoRunPipelineExecutionRepository(connection_manager)
        self.exec_step_repo = EtoRunPipelineExecutionStepRepository(connection_manager)

        logger.info("PipelineExecutionService initialized")

    # ==================== Public API ====================

    def execute_pipeline(
        self,
        pipeline_definition_id: int,
        eto_run_id: int,
        entry_values_by_name: Dict[str, Any],
    ) -> PipelineExecutionRun:
        """
        Execute a compiled pipeline with the provided entry values.

        Policy:
          - Fail fast on missing required entry names
          - Extra entry names are ignored (logged)
          - All Action modules run only after all Transform/Logic modules succeed
          - On any module error, the whole run is marked failed

        Args:
            pipeline_definition_id: ID of compiled pipeline to execute
            eto_run_id: Parent ETO run ID
            entry_values_by_name: Entry point values keyed by entry point name

        Returns:
            PipelineExecutionRun with final status

        Raises:
            ValueError: Missing required entry values
            RuntimeError: Pipeline not compiled or module not found
        """
        # TODO: Implement phases
        raise NotImplementedError("Pipeline execution not yet implemented")

    # ==================== Helper Methods (to be implemented) ====================

    def _require_pipeline(self, pipeline_definition_id: int) -> PipelineDefinition:
        """Load pipeline and verify it's compiled"""
        # TODO: Step 4
        pass

    def _require_compiled_steps(self, pipeline: PipelineDefinition) -> List[PipelineDefinitionStep]:
        """Load compiled steps by checksum"""
        # TODO: Step 4
        pass

    def _map_entry_names_to_pin_ids(self, pipeline: PipelineDefinition) -> Dict[str, List[str]]:
        """Build {entry_name -> [pin_id, ...]} from pipeline_state.entry_points"""
        # TODO: Step 4
        pass

    def _seed_entry_values(
        self,
        entry_values_by_name: Dict[str, Any],
        entry_name_to_ids: Dict[str, List[str]],
    ) -> Tuple[Dict[str, Any], List[str], List[str]]:
        """Seed producer_of_pin with entry values"""
        # TODO: Step 5
        pass

    def _make_step_task(
        self,
        step: PipelineDefinitionStep,
        producer_of_pin: Dict[str, Any],
        run_id: int,
        extra_dependencies: Optional[List[Any]] = None,
    ):
        """Create delayed task for a module"""
        # TODO: Step 6
        pass

    def _publish_outputs_for_downstream(
        self,
        step: PipelineDefinitionStep,
        task,
        producer_of_pin: Dict[str, Any],
    ) -> None:
        """Split module outputs into per-pin delayed futures"""
        # TODO: Step 7
        pass
```

**Why?** Establishes structure, can be imported and tested incrementally.

**Test criteria**: Service can be instantiated and imported without errors.

---

### Phase 3: Core Execution Logic (Incremental Implementation)

#### ✅ Step 4: Implement Entry Point Loading & Validation

**Methods to implement**:
- `_require_pipeline()` - Load pipeline from DB, verify compiled
- `_require_compiled_steps()` - Load steps by checksum, ordered by step_number
- `_map_entry_names_to_pin_ids()` - Build entry name→pin IDs map from `pipeline_state.entry_points`

**Update `execute_pipeline` to**:
1. Load pipeline and steps
2. Create execution run record (status: "processing")
3. Build entry name→pin ID map
4. Return run for now (don't execute yet)

**Reference**: Old server lines 108-120

**Test criteria**:
- Can load compiled pipeline
- Raises error if pipeline not compiled
- Creates execution run record
- Maps entry point names to pin IDs correctly

---

#### ✅ Step 5: Implement Entry Value Seeding

**Method to implement**: `_seed_entry_values()`

**Logic**:
```python
def _seed_entry_values(
    self,
    entry_values_by_name: Dict[str, Any],
    entry_name_to_ids: Dict[str, List[str]],
) -> Tuple[Dict[str, Any], List[str], List[str]]:
    """
    Returns:
        producer_of_pin: {pin_id -> delayed(value)}
        missing_names: required but not provided
        extra_names: provided but not used
    """
    expected = set(entry_name_to_ids.keys())
    provided = set(entry_values_by_name.keys())
    missing = sorted(expected - provided)
    extras = sorted(provided - expected)

    @delayed(pure=True)
    def _const(v):
        return v

    producer_of_pin: Dict[str, Any] = {}
    for name, node_ids in entry_name_to_ids.items():
        if name in entry_values_by_name:
            v = entry_values_by_name[name]
            for pin_id in node_ids:
                producer_of_pin[pin_id] = _const(v)

    return producer_of_pin, missing, extras
```

**Update `execute_pipeline`**:
- Call `_seed_entry_values()`
- Raise `ValueError` if missing required entries
- Log warning if extra entries provided

**Reference**: Old server lines 213-239

**Test criteria**:
- `producer_of_pin` contains delayed values for all entry point pins
- Detects missing required entries
- Detects extra provided entries

---

#### ✅ Step 6: Implement Module Task Creation

**Method to implement**: `_make_step_task()`

**Logic**:
```python
def _make_step_task(
    self,
    step: PipelineDefinitionStep,
    producer_of_pin: Dict[str, Any],
    run_id: int,
    extra_dependencies: Optional[List[Any]] = None,
):
    # 1. Resolve handler
    module_id = step.module_ref.split(":")[0] if ":" in step.module_ref else step.module_ref
    handler = self.module_registry.get(module_id)
    if not handler:
        raise RuntimeError(f"Module handler not found for {step.module_ref}")

    ConfigModel = handler.config_class()
    handlerInstance = handler()

    # 2. Build context
    inputs = step.node_metadata.get("inputs") or []
    outputs = step.node_metadata.get("outputs") or []
    ctx = ModuleExecutionContext(
        module_instance_id=step.module_instance_id,
        inputs=inputs,
        outputs=outputs,
        services=self.services,
    )

    # 3. Gather upstream producers
    input_ids = list(step.input_field_mappings.keys())
    upstream_ids = [step.input_field_mappings[iid] for iid in input_ids]
    upstream_tasks = [producer_of_pin[uid] for uid in upstream_ids]

    if extra_dependencies:
        upstream_tasks = upstream_tasks + list(extra_dependencies)

    # 4. Create delayed task
    @delayed(pure=False)
    def _run_module(*resolved):
        # Build {input_pin_id: value}
        values = resolved[:len(input_ids)]
        inputs = {inp_id: val for inp_id, val in zip(input_ids, values)}

        # Run handler
        try:
            outputs = handlerInstance.run(inputs=inputs, cfg=ConfigModel(**step.module_config), context=ctx)
            error = None
        except Exception as e:
            outputs = {}
            error = f"{type(e).__name__}: {e}"
            logger.exception("Module %s failed: %s", step.module_instance_id, e)

        # TODO: Persist audit row (Step 10)

        # Fail fast
        if error:
            raise RuntimeError(error)

        return outputs  # {output_pin_id: value}

    return _run_module(*upstream_tasks)
```

**Reference**: Old server lines 241-336

**Test criteria**: Can create delayed task for a single module (doesn't execute yet).

---

#### ✅ Step 7: Implement Output Publishing

**Method to implement**: `_publish_outputs_for_downstream()`

**Logic**:
```python
def _publish_outputs_for_downstream(
    self,
    step: PipelineDefinitionStep,
    task,
    producer_of_pin: Dict[str, Any],
) -> None:
    """
    Split module output dict into per-pin delayed futures.

    task produces: {output_pin_id -> value}
    We create: delayed futures for each output pin individually
    """
    output_pins: List[InstanceNodePin] = step.node_metadata.get("outputs") or []

    for pin in output_pins:
        node_id = pin.node_id

        @delayed(pure=True)
        def _select(outputs: Dict[str, Any], key: str):
            return outputs.get(key)

        producer_of_pin[node_id] = _select(task, node_id)
```

**Reference**: Old server lines 338-356

**Test criteria**: Output pins are available as delayed values for downstream modules.

---

#### ✅ Step 8: Implement Dask Graph Building (Transforms/Logic)

**Update `execute_pipeline`** to build graph:

```python
# After seeding entry values...

# Build Dask graph
task_of_step: Dict[str, Any] = {}
non_action_tasks: List[Any] = []
action_steps: List[PipelineDefinitionStep] = []

for step in steps:
    if step.module_kind == 'action':
        action_steps.append(step)
        continue

    task = self._make_step_task(step, producer_of_pin, run_id)
    task_of_step[step.module_instance_id] = task
    self._publish_outputs_for_downstream(step, task, producer_of_pin)
    non_action_tasks.append(task)
```

**Reference**: Old server lines 136-149

**Test criteria**: Can build graph for pipeline with only transform/logic modules.

---

#### ✅ Step 9: Implement Action Barrier & Action Execution

**Update `execute_pipeline`** to add action handling:

```python
# After building transform/logic tasks...

# Create action barrier
barrier = delayed(lambda *args: True, pure=True)(*non_action_tasks) if non_action_tasks else delayed(lambda: True, pure=True)()

# Build action tasks
for step in action_steps:
    task = self._make_step_task(step, producer_of_pin, run_id, extra_dependencies=[barrier])
    task_of_step[step.module_instance_id] = task
    self._publish_outputs_for_downstream(step, task, producer_of_pin)
```

**Reference**: Old server lines 152-157

**Test criteria**: Actions execute after all transforms complete.

---

#### ✅ Step 10: Implement Audit Trail Serialization

**Helper functions to add** (at module level):

```python
def _serialize_value(value: Any, type_hint: str) -> Any:
    """Serialize value to JSON-compatible format"""
    if type_hint == "datetime":
        if isinstance(value, (datetime, date)):
            return value.isoformat()
    return value

def _serialize_io_for_audit(
    io_dict: Dict[str, Any],
    pins: List[InstanceNodePin]
) -> Dict[str, Dict[str, Any]]:
    """
    Transform {node_id: value} to {node_name: {value, type}}
    """
    result = {}
    for pin in pins:
        if pin.node_id in io_dict:
            raw_value = io_dict[pin.node_id]
            result[pin.name] = {
                "value": _serialize_value(raw_value, pin.type),
                "type": pin.type
            }
    return result
```

**Update `_run_module` inside `_make_step_task`**:

```python
# After running handler...

# Persist audit row
if run_id is not None:
    try:
        audit_inputs = _serialize_io_for_audit(inputs, ctx.inputs)
        audit_outputs = _serialize_io_for_audit(outputs, ctx.outputs) if outputs else {}

        self.exec_step_repo.create(
            PipelineExecutionStepCreate(
                run_id=run_id,
                module_instance_id=step.module_instance_id,
                step_number=step.step_number,
                inputs=audit_inputs,
                outputs=audit_outputs,
                error=error,
            )
        )
    except Exception as pe:
        logger.exception("Failed to persist execution step for %s: %s", step.module_instance_id, pe)

# Then fail fast if error...
```

**Reference**: Old server lines 36-64, 308-326

**Test criteria**: Execution steps are persisted with inputs/outputs in `{node_name: {value, type}}` format.

---

#### ✅ Step 11: Implement Error Handling & Status Updates

**Update `execute_pipeline`** final phase:

```python
# After building all tasks...

# Execute
try:
    leaves = [t for t in task_of_step.values()] or list(producer_of_pin.values())
    if leaves:
        compute(*leaves)  # raises on first failure

    # Mark success
    self.run_repo.update_status(run_id, "success", completed_at=datetime.utcnow())
except Exception as e:
    logger.exception("Pipeline execution failed: %s", e)
    self.run_repo.update_status(run_id, "failed", completed_at=datetime.utcnow())
    raise

# Return final run
run_fresh = self.run_repo.get_by_id(run_id)
return run_fresh
```

**Reference**: Old server lines 160-177

**Test criteria**:
- Failed modules mark run as "failed" and stop execution
- Successful runs mark as "success"
- Completed timestamp set

---

### Phase 4: Integration & Testing

#### ✅ Step 12: End-to-End Testing

**Test pipeline structure**:
```
Entry Points: origin (str), destination (str)
  ↓
Transform: concatenate (inputs: origin, destination → output: route)
  ↓
Logic: uppercase (input: route → output: route_upper)
  ↓
Action: test_action (input: route_upper)
```

**Test cases**:
1. **Happy path**: All modules succeed
   - Verify all steps persisted
   - Verify correct layer ordering
   - Verify action runs last
   - Verify run status = "success"
   - Verify audit trail has correct inputs/outputs

2. **Missing entry point**: Omit "destination"
   - Verify raises `ValueError`
   - Verify run status = "failed"

3. **Module failure**: Make transform module raise error
   - Verify execution stops at failing module
   - Verify downstream modules don't execute
   - Verify error captured in step audit
   - Verify run status = "failed"

4. **Extra entry point**: Provide "extra_field"
   - Verify logged as warning
   - Verify execution succeeds

---

## Key Design Decisions

### 1. Separate Service File
**Decision**: Create `service_execution.py` instead of adding to `service.py`

**Rationale**:
- Separation of concerns (definition management vs. execution)
- Execution logic is complex enough to warrant its own file
- Easier to test independently

### 2. Module Registry
**Decision**: Reuse existing `ModuleRegistry` singleton

**Rationale**: All modules should already be registered at startup via `@register` decorator

### 3. Services Container
**Decision**: Pass `services` to execution context

**Rationale**: Modules need access to other services (email, PDF, database) to perform actions

### 4. Step Number = Layer
**Decision**: Step numbers represent execution layers, not sequential order

**Rationale**:
- Enables parallel execution within a layer
- Matches compilation output
- Dask can optimize execution graph

### 5. Fail Fast
**Decision**: First error stops entire run

**Rationale**:
- Prevents cascading errors
- Matches old server behavior
- Simpler error handling (no partial state)

### 6. Audit Trail Format
**Decision**: Store as `{node_name: {value, type}}` not `{node_id: value}`

**Rationale**:
- Human-readable for debugging
- Type information preserved
- Matches old server format

---

## Dependencies

### Python Packages (already in requirements)
- `dask` - Lazy task graph execution
- `pydantic` - Type validation
- `sqlalchemy` - Database ORM

### Internal Dependencies
- ✅ `ModuleRegistry` - Module handler resolution
- ✅ Database models - `EtoRunPipelineExecutionModel`, `EtoRunPipelineExecutionStepModel`
- ✅ Pipeline definition models and repositories
- ❌ Execution domain types (Step 1)
- ❌ Execution repositories (Step 2)

---

## Testing Strategy

### Unit Tests
- Repository methods (create, get, update)
- Entry value seeding logic
- Audit trail serialization
- Entry point name mapping

### Integration Tests
- Service initialization
- Pipeline loading and validation
- Graph building for simple pipeline
- Error handling and status updates

### End-to-End Tests
- Multi-module pipeline execution
- Action barrier enforcement
- Audit trail persistence
- Error propagation

---

## References

### Old Server Files
- `server/src/features/pipeline_execution/service.py` - Main execution logic
- `server/src/shared/database/repositories/` - Repository patterns

### New Server Files (to create/modify)
- `server-new/src/shared/types/pipeline_execution.py` - Domain types (NEW)
- `server-new/src/shared/database/repositories/eto_run_pipeline_execution.py` - Run repository (NEW)
- `server-new/src/shared/database/repositories/eto_run_pipeline_execution_step.py` - Step repository (NEW)
- `server-new/src/features/pipelines/service_execution.py` - Execution service (NEW)

### Existing Infrastructure
- `server-new/src/shared/database/models.py` (lines 488-549) - Execution models
- `server-new/src/shared/utils/registry.py` - Module registry
- `server-new/src/features/pipelines/utils/compilation.py` - Layer-based compilation

---

## Next Steps

After completing this implementation:

1. **API Endpoint**: Create POST `/pipelines/{id}/execute` endpoint
2. **ETO Integration**: Wire up pipeline execution in ETO run lifecycle
3. **Monitoring**: Add execution metrics and logging
4. **Performance**: Optimize Dask scheduler settings for workload
5. **Error Reporting**: Enhanced error messages with context

---

## Notes

- All module handlers must implement `.run(inputs, cfg, context)` interface
- Module registry must be populated before execution service starts
- Database connection pool must support concurrent transactions (Dask parallelization)
- Consider adding execution timeout mechanism for long-running pipelines
- Future: Add retry mechanism for transient failures
- Future: Add execution history/replay capability
