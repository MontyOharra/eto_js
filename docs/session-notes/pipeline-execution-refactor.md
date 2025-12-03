# Pipeline Execution Service Refactor Analysis

## Overview

This document analyzes the changes needed to `pipeline_execution/service.py` to:
1. Remove action module support
2. Add output module support
3. Move simulation logic to the ETO orchestration layer

---

## Current Architecture (Action-Based)

### Key Components

1. **ActionDataCollector** (removed by user already)
   - Collected action execution data during pipeline runs
   - Converted to `executed_actions` dict format
   - Thread-safe for parallel Dask execution

2. **Simulation vs Production Mode**
   - `execute_actions` flag controls behavior
   - Simulation: Actions don't execute, data is collected
   - Production: Actions execute with side effects

3. **Action Barrier Pattern**
   - All transforms/logic execute first
   - Barrier task ensures transforms complete before actions
   - Actions execute after barrier

4. **Action Module Execution** (lines 915-993)
   - **Simulation mode:** Collect data, generate mock outputs, no side effects
   - **Production mode:** Execute handler, collect results with `executed=True`
   - Uses `_convert_to_upstream_named_inputs()` for better UX

5. **Mock Output Generation** (lines 700-740)
   - Generates placeholder values when actions don't execute
   - Allows downstream modules to continue in simulation

---

## New Architecture (Output-Based)

### Core Principle: Separation of Concerns

**Pipeline Execution = Pure Data Transformation**
- No side effects
- No simulation mode
- Always executes the same way
- Output modules collect data (no execution)

**ETO Orchestrator = Workflow Control**
- Decides whether to execute outputs
- Calls OutputExecutionService when ready
- Handles simulation vs production decision

### Key Changes

#### 1. **Remove Simulation Mode Entirely**

**Current:**
```python
def simulate_pipeline(...) -> PipelineExecutionResult:
    return self._execute_pipeline_internal(..., execute_actions=False)

def execute_pipeline(...) -> PipelineExecutionResult:
    return self._execute_pipeline_internal(..., execute_actions=True)
```

**New:**
```python
def execute_pipeline(...) -> PipelineExecutionResult:
    """Execute pipeline and return output module data."""
    # No execute_actions parameter
    # No simulation mode
```

**Rationale:** Simulation is now the responsibility of the ETO orchestrator. It simply doesn't call OutputExecutionService.

---

#### 2. **Replace Action Detection with Output Detection**

**Current (lines 534-545):**
```python
for step in steps:
    module_id = step.module_ref.split(":")[0]
    handler = self.module_registry.get(module_id)
    if handler and handler.kind.value == 'action':
        action_steps.append(step)  # Separate action steps
    else:
        # Transform/logic modules
        task = self._make_step_task(step, ...)
        non_action_tasks.append(task)
```

**New:**
```python
for step in steps:
    module_id = step.module_ref.split(":")[0]
    handler = self.module_registry.get(module_id)

    # All modules (transform, logic, misc, output) execute in topological order
    task = self._make_step_task(step, ...)
    task_of_step[step.module_instance_id] = task
    self._publish_outputs_for_downstream(step, task, producer_of_pin)

    # Track output module for final return
    if handler and handler.kind.value == 'output':
        output_module_step = step  # Only one allowed by validation
```

**Rationale:** Output modules execute like any other module - they just collect their inputs and return empty dict.

---

#### 3. **Remove Action Barrier**

**Current (lines 547-561):**
```python
# Create action barrier
if non_action_tasks:
    barrier = delayed(lambda *args: True, pure=True)(*non_action_tasks)
else:
    barrier = delayed(lambda: True, pure=True)()

# Action tasks depend on barrier
for step in action_steps:
    task = self._make_step_task(step, ..., extra_dependencies=[barrier], ...)
```

**New:**
```python
# No barrier needed - output modules execute in topological order
# They have no special scheduling requirements
```

**Rationale:** Output modules don't need to wait for everything else - they're just regular nodes in the DAG.

---

#### 4. **Simplify Module Execution Logic**

**Current (lines 915-993):**
```python
if is_action:
    upstream_named_inputs = _convert_to_upstream_named_inputs(...)
    module_title = getattr(handler, 'title', module_id)

    if execute_actions:
        # Production: Execute action
        outputs_dict = handlerInstance.run(...)
        action_collector.add(ActionExecutionData(..., executed=True))
    else:
        # Simulation: Just collect
        action_collector.add(ActionExecutionData(..., executed=False))
        outputs_dict = self._generate_mock_outputs(ctx.outputs)
        return outputs_dict  # Early return, no step result
else:
    # Transform/Logic module
    outputs_dict = handlerInstance.run(...)
```

**New:**
```python
# No special casing - all modules execute the same way
try:
    config_instance = ConfigModel(**step.module_config)
    outputs_dict = handlerInstance.run(
        inputs=inputs_dict,
        cfg=config_instance,
        context=ctx,
        services=self.services
    )
    error = None
except Exception as e:
    outputs_dict = {}
    error = f"{type(e).__name__}: {e}"

# For output modules, outputs_dict will be empty (they return {})
# That's fine - we track their inputs separately for the return value
```

**Rationale:**
- Output modules have a `run()` method that returns `{}` (no outputs)
- No need for special execution logic
- All modules follow the same pattern

---

#### 5. **Return Output Module Information**

**Current Return:**
```python
return PipelineExecutionResult(
    status=status,
    steps=collected_steps,
    executed_actions=action_collector.to_executed_actions_dict(),  # Action data
    error=error
)
```

**New Return:**
```python
# After graph execution, extract output module data
output_module_id = None
output_module_inputs = {}

if output_module_step:  # Set during step iteration
    # Get the inputs that were passed to the output module
    # These are stored in the step result
    output_step_result = next(
        (s for s in collected_steps if s.module_instance_id == output_module_step.module_instance_id),
        None
    )
    if output_step_result:
        output_module_id = output_module_step.module_ref.split(":")[0]
        # Convert step result inputs to plain dict {name: value}
        output_module_inputs = {
            pin_data["name"]: pin_data["value"]
            for pin_data in output_step_result.inputs.values()
        }

return PipelineExecutionResult(
    status=status,
    steps=collected_steps,
    output_module_id=output_module_id,  # NEW: Which output module to execute
    output_module_inputs=output_module_inputs,  # NEW: Data for the output module
    error=error
)
```

**Rationale:**
- Pipeline returns structured data for the orchestrator
- Orchestrator decides whether to execute output
- Clean separation of concerns

---

#### 6. **Update PipelineExecutionResult Type**

**File:** `shared/types/pipeline_execution.py`

**Current:**
```python
@dataclass
class PipelineExecutionResult:
    status: str  # "success", "partial", "failed"
    steps: List[PipelineExecutionStepResult]
    executed_actions: Dict[str, Dict[str, Any]]  # Action data
    error: Optional[str]
```

**New:**
```python
@dataclass
class PipelineExecutionResult:
    status: str  # "success", "partial", "failed"
    steps: List[PipelineExecutionStepResult]
    output_module_id: Optional[str]  # Module ID to execute (e.g., "basic_order_output")
    output_module_inputs: Dict[str, Any]  # Input data for output module {name: value}
    error: Optional[str]
```

---

#### 7. **Remove Helper Functions**

Delete these functions (no longer needed):

1. **`_convert_to_named_inputs()`** (lines 234-258)
   - Was used to convert node IDs to names for actions
   - Not needed anymore

2. **`_convert_to_upstream_named_inputs()`** (lines 261-321)
   - Was used for action input name mapping
   - Not needed anymore

3. **`_generate_mock_outputs()`** (lines 700-740)
   - Was used in simulation mode
   - Not needed - no simulation mode

---

#### 8. **Simplify Imports**

**Current (lines 31-38):**
```python
from shared.types.pipeline_execution import (
    PipelineExecutionRun,
    PipelineExecutionRunCreate,
    PipelineExecutionStepCreate,
    # Simulation types
    PipelineExecutionStepResult,
    ActionExecutionData,  # REMOVE
    PipelineExecutionResult,
)
```

**New:**
```python
from shared.types.pipeline_execution import (
    PipelineExecutionStepResult,
    PipelineExecutionResult,
)
```

---

#### 9. **Update Method Signatures**

**Remove these parameters:**
- `execute_actions` from `_execute_pipeline_internal()`
- `execute_actions` from `_make_step_task()`
- `action_collector` from `_make_step_task()`
- `extra_dependencies` from `_make_step_task()` (no more barrier)

**Remove these variables:**
- `action_steps: List[PipelineDefinitionStep]`
- `non_action_tasks: List[Any]`
- `action_collector: ActionDataCollector`

---

#### 10. **Update Documentation**

**Current docstrings mention:**
- "Action modules"
- "Simulation mode"
- "execute_actions parameter"
- "Action barrier"

**Update to:**
- "Output modules"
- Remove simulation references
- "Pure data transformation"
- "Returns output module data for orchestrator"

---

## ETO Orchestrator Integration

### How ETO Orchestrator Uses New Pipeline Service

```python
# In eto_runs/service.py

def _process_sub_run_pipeline(self, sub_run_id: int):
    """Execute pipeline for a sub-run."""

    # 1. Get extraction data
    extraction = self.extraction_repo.get_by_sub_run_id(sub_run_id)
    extracted_data = extraction.extracted_data

    # 2. Execute pipeline (always the same, no simulation flag)
    result = self.pipeline_service.execute_pipeline(
        steps=pipeline_steps,
        entry_values_by_name=extracted_data,
        pipeline_state=template_version.pipeline_state
    )

    # 3. Check if pipeline succeeded
    if result.status != "success":
        # Handle failure
        return

    # 4. Create output execution record (THIS IS WHERE "SIMULATION" IS DECIDED)
    if result.output_module_id:
        # In PRODUCTION: Create output execution for OutputExecutionService to process
        output_execution = self.output_execution_repo.create(
            EtoSubRunOutputExecutionCreate(
                sub_run_id=sub_run_id,
                module_id=result.output_module_id,
                input_data=result.output_module_inputs
            )
        )

        # OutputExecutionService will pick this up and execute it
        # This is where order creation happens

    # In SIMULATION: Just don't create the output execution record
    # That's it - simulation is just "don't execute outputs"
```

---

## Summary of Changes

### Files to Modify

1. **`pipeline_execution/service.py`** (THIS FILE)
   - Remove `ActionDataCollector` class (done)
   - Remove `simulate_pipeline()` method
   - Remove `execute_actions` parameter throughout
   - Remove action barrier logic
   - Remove action-specific execution logic
   - Remove helper functions for action name mapping
   - Add output module data extraction
   - Update return type to include output module info
   - Simplify to single execution path

2. **`shared/types/pipeline_execution.py`**
   - Remove `ActionExecutionData` dataclass (done by user)
   - Update `PipelineExecutionResult`:
     - Remove `executed_actions: Dict[str, Dict[str, Any]]`
     - Add `output_module_id: Optional[str]`
     - Add `output_module_inputs: Dict[str, Any]`

3. **`features/eto_runs/service.py`**
   - Update pipeline execution calls (remove execute_actions)
   - Add logic to create output execution records
   - Implement simulation by NOT creating output executions

### Lines to Delete

- Lines 234-258: `_convert_to_named_inputs()`
- Lines 261-321: `_convert_to_upstream_named_inputs()`
- Lines 374-416: `simulate_pipeline()` method
- Lines 509: `action_collector = ActionDataCollector()`
- Lines 531-532: `non_action_tasks`, `action_steps` lists
- Lines 534-545: Action detection loop
- Lines 547-561: Action barrier creation
- Lines 604: `executed_actions=action_collector.to_executed_actions_dict()`
- Lines 700-740: `_generate_mock_outputs()`
- Lines 831-832: `is_action = (module_kind == "action")`
- Lines 915-993: Action-specific execution logic

### Net Result

**Before:**
- 1082 lines
- Complex action/simulation logic
- Two execution modes
- Special action scheduling

**After:**
- ~850 lines (estimate)
- Simple, single execution path
- Pure data transformation
- Output modules treated like any other module

---

## Migration Strategy

1. **Update types first** (`pipeline_execution.py`)
2. **Simplify service** (remove action logic)
3. **Update ETO orchestrator** (handle output execution)
4. **Test with simulation** (verify outputs aren't executed)
5. **Test with production** (verify outputs execute)

---

## Key Insight

The critical realization is that **simulation is not a pipeline execution concern** - it's an orchestration concern:

- **Pipeline service:** "Here's the data for the output module"
- **ETO orchestrator:** "Should I execute this output? In simulation: no. In production: yes."

This makes the pipeline service much simpler and more focused on its core responsibility: pure data transformation.
