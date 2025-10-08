# Implementation Tasks for Unified Execution with Node Metadata

## 🔄 IMPLEMENTATION PROTOCOL - MUST READ BEFORE EACH PHASE
**IMPORTANT: Read these instructions at the start of each phase and after completing each phase**

### Step-by-Step Implementation Process:
1. **PLAN**: Present a detailed plan for the current phase including:
   - Exact files to be created/modified
   - Specific code/functions to be written
   - Location of each change
   - Dependencies and imports needed

2. **WAIT**: Wait for user confirmation before proceeding ("ok", "proceed", "go ahead", etc.)

3. **CHECK**: After confirmation, read/check existing code that will be modified

4. **IMPLEMENT**: Write the code according to the plan

5. **TEST**: If testable, write and run unit tests for the new functionality

6. **E2E READY**: Announce readiness for end-to-end testing by user

7. **CONFIRM**: Wait for user's test results and final confirmation

8. **UPDATE CHECKBOXES**: Mark completed items with [x] in the implementation tasks

9. **NEXT**: Move to next phase and **RE-READ THESE INSTRUCTIONS**

### Testing Priority:
- Unit test individual functions where possible
- Focus on domain model conversions
- Test error cases and edge conditions
- Repository methods can be tested with mock sessions

### Recursive Instruction:
**After completing each phase, return to read these implementation instructions again before starting the next phase.**

---

> This document outlines all changes and additions needed to implement the unified execution plan with node metadata support.

## 📊 Implementation Progress

### Phase Overview:
- ✅ **Phase 1: Data Model Updates** - COMPLETE
  - [x] 1.1 Update PipelineStep Model
  - [x] 1.2 Update SQLAlchemy Model
  - [x] 1.3 Update Repository
- ✅ **Phase 2: Compilation Process Updates** - COMPLETE
  - [x] 2.1 Update Compiler to Preserve Node Metadata
- ✅ **Phase 3: Execution Context Implementation** - COMPLETE
  - [x] 3.1 Create ExecutionContext Class
  - [x] 3.2 Update Module Handler Base Class
- ✅ **Phase 4: Dask Executor Implementation** - COMPLETE
  - [x] 4.1 Add Execution Audit Trail (Database Persistence)
  - [x] 4.2 Create Pipeline Executor
  - [x] 4.3 Create Execution Models
  - [x] 4.4 Sequential Fallback Executor (skipped - optional)
- ✅ **Phase 5: API Endpoints** - COMPLETE
  - [x] 5.1 Create Execution Endpoint
- ⏳ **Phase 6: Frontend Updates** - NOT STARTED
  - [ ] 6.1 Add Execution UI

---

## Phase 1: Data Model Updates

- [x] **1.1 Update PipelineStep Model**
**File**: `transformation_pipeline_server/src/shared/models/pipeline_step.py`

Add the following to `PipelineStepBase` class after the existing fields, and remove redundant field:
```python
from typing import Dict, List, Optional
from shared.models.pipeline import InstanceNodePin

class PipelineStepBase(BaseModel):
    # Existing fields...
    input_field_mappings: Dict[str, Dict[str, str]]

    # REMOVE: This field is now redundant with node_metadata
    # output_display_names: Dict[str, str] = Field(default_factory=dict)  # DELETE THIS LINE

    # NEW: Node metadata for execution context (replaces output_display_names)
    # Dict with "inputs" and "outputs" keys, each containing List[InstanceNodePin]
    node_metadata: Optional[Dict[str, List[InstanceNodePin]]] = Field(
        default_factory=dict,
        description="Node pins metadata with inputs and outputs lists (replaces output_display_names)"
    )
```

Update `PipelineStepCreate.model_dump_for_db()`:
```python
def model_dump_for_db(self) -> dict:
    data = self.model_dump()
    data['input_field_mappings'] = json.dumps(self.input_field_mappings)
    # Convert InstanceNodePin objects to dicts for JSON serialization
    if self.node_metadata:
        metadata_dict = {
            "inputs": [pin.model_dump() for pin in self.node_metadata.get("inputs", [])],
            "outputs": [pin.model_dump() for pin in self.node_metadata.get("outputs", [])]
        }
        data['node_metadata'] = json.dumps(metadata_dict)
    else:
        data['node_metadata'] = '{}'
    return data
```

- [x] **1.2 Update SQLAlchemy Model**
**File**: `transformation_pipeline_server/src/shared/database/models.py`

Update `PipelineStepModel` class to add new column and remove redundant one:
```python
class PipelineStepModel(Base):
    # Existing columns...
    input_field_mappings = Column(String, nullable=False)

    # REMOVE: This column is redundant with node_metadata
    # output_display_names = Column(String, nullable=True)  # DELETE THIS LINE

    # NEW: Add node metadata column
    node_metadata = Column(String, nullable=True, default='{}')  # JSON string storage
```

- [x] **1.3 Update Repository** Layer
**File**: `transformation_pipeline_server/src/shared/database/repositories/pipeline_step.py`

In `PipelineStepRepository.create_steps()` method, ensure the node_metadata is included:
```python
def create_steps(self, db: Session, steps: List[PipelineStepCreate]) -> List[PipelineStepModel]:
    db_steps = []
    for step in steps:
        step_data = step.model_dump_for_db()  # This now includes node_metadata
        db_step = PipelineStepModel(**step_data)
        db_steps.append(db_step)

    db.add_all(db_steps)
    db.commit()
    return db_steps
```

In `get_steps_by_checksum()`, the node_metadata will be automatically retrieved since it's a model field. Update the method to parse it:
```python
from shared.models.pipeline import InstanceNodePin

def get_steps_by_checksum(self, db: Session, checksum: str) -> List[PipelineStep]:
    steps = db.query(PipelineStepModel).filter(
        PipelineStepModel.plan_checksum == checksum
    ).order_by(PipelineStepModel.step_number).all()

    # Convert to Pydantic models, parsing JSON fields
    result = []
    for step in steps:
        step_dict = step.__dict__.copy()
        step_dict['input_field_mappings'] = json.loads(step.input_field_mappings)

        # Parse node_metadata and convert back to InstanceNodePin objects
        metadata_json = json.loads(step.node_metadata or '{}')
        if metadata_json:
            step_dict['node_metadata'] = {
                "inputs": [InstanceNodePin(**pin) for pin in metadata_json.get("inputs", [])],
                "outputs": [InstanceNodePin(**pin) for pin in metadata_json.get("outputs", [])]
            }
        else:
            step_dict['node_metadata'] = {}

        result.append(PipelineStep(**step_dict))

    return result
```

## Phase 2: Compilation Process Updates

- [x] **2.1 Update Compiler to Preserve Node Metadata**
**File**: `transformation_pipeline_server/src/features/pipeline/compilation/compiler.py`

Modify the `_build_steps()` static method to extract and include node metadata when creating PipelineStepCreate objects. Update lines 114-124:

```python
@staticmethod
def _build_steps(
    pipeline: PipelineState,
    layers: List[List[str]],
    checksum: str
) -> List[PipelineStepCreate]:
    """Build PipelineStepCreate domain objects from topological layers"""

    # Build lookups for fast access
    pin_to_module = PipelineCompiler._build_pin_to_module_lookup(pipeline)
    module_lookup = {m.module_instance_id: m for m in pipeline.modules}

    # Flatten layers into steps with step_number
    steps = []
    step_number = 0

    for layer in layers:
        for module_id in layer:
            module = module_lookup[module_id]

            # Build input mappings for this module
            input_mappings = PipelineCompiler._build_input_mappings(
                module,
                pipeline.connections,
                pin_to_module
            )

            # REMOVE: No longer need output_names since node_metadata contains this info
            # output_names = PipelineCompiler._build_output_names(module)  # DELETE THIS LINE

            # NEW: Extract node metadata for execution context
            # The module.inputs and module.outputs are already InstanceNodePin objects
            # This replaces the need for output_display_names
            node_metadata = {
                "inputs": module.inputs,   # List[InstanceNodePin]
                "outputs": module.outputs  # List[InstanceNodePin]
            }

            # Create PipelineStepCreate domain object
            step = PipelineStepCreate(
                plan_checksum=checksum,
                module_instance_id=module.module_instance_id,
                module_ref=module.module_ref,
                module_kind=module.module_kind,
                module_config=module.config,
                input_field_mappings=input_mappings,
                # REMOVE: output_display_names=output_names,  # DELETE THIS LINE
                node_metadata=node_metadata,  # NEW - replaces output_display_names
                step_number=step_number
            )
            steps.append(step)
            step_number += 1

    return steps
```

The key changes are:
1. Adding the `node_metadata` extraction
2. Removing the `output_names` variable and `_build_output_names()` call (lines to delete)
3. Removing `output_display_names` from the PipelineStepCreate constructor
4. The node_metadata now serves as the single source of truth for all pin information

### 2.2 Cleanup - Remove Unused Method
**File**: `transformation_pipeline_server/src/features/pipeline/compilation/compiler.py`

Since we no longer need output display names, remove the unused method:
```python
# DELETE THIS ENTIRE METHOD (lines ~207-234):
@staticmethod
def _build_output_names(module: ModuleInstance) -> Dict[str, str]:
    """
    Build output display names for a module
    [DELETE - No longer needed as node_metadata contains names]
    """
    # ... entire method body ...
```

### 2.3 Update Topological Sorter
**File**: `transformation_pipeline_server/src/features/pipeline/compilation/topological_sorter.py`

The topological sorter already works with ModuleInstance objects and doesn't create PipelineSteps directly. No code changes needed - the sorter returns ordered ModuleInstances which already contain all pin information.

## Phase 3: Execution Context Implementation

- [x] **3.1 Create ExecutionContext Class**
**File**: New file `transformation_pipeline_server/src/shared/models/execution_context.py`

```python
from pydantic import BaseModel
from typing import Dict, Any, List
from shared.models.pipeline import InstanceNodePin

class ExecutionContext(BaseModel):
    """Context passed to module handlers with node metadata and helpers"""
    inputs: List[InstanceNodePin]      # Input pins metadata
    outputs: List[InstanceNodePin]     # Output pins metadata
    module_instance_id: str             # For debugging/logging
    run_id: str                         # Execution run ID

    def get_input_type(self, index: int = 0) -> str:
        """Get type of input at given index"""
        if not self.inputs:
            raise IndexError("No inputs in context")
        if index >= len(self.inputs):
            raise IndexError(f"Input index {index} out of range")
        return self.inputs[index].type

    def get_output_type(self, index: int = 0) -> str:
        """Get type of output at given index"""
        if not self.outputs:
            raise IndexError("No outputs in context")
        if index >= len(self.outputs):
            raise IndexError(f"Output index {index} out of range")
        return self.outputs[index].type

    def get_input_names(self) -> Dict[str, str]:
        """Get mapping of node_id to user-assigned names"""
        return {pin.node_id: pin.name for pin in self.inputs}

    def get_output_names(self) -> Dict[str, str]:
        """Get mapping of node_id to user-assigned names"""
        return {pin.node_id: pin.name for pin in self.outputs}

    def resolve_placeholders(self, template: str, inputs: Dict[str, Any]) -> str:
        """Replace {name} placeholders with actual values"""
        result = template
        # Replace input placeholders
        for pin in self.inputs:
            placeholder = f"{{{pin.name}}}"
            value = inputs.get(pin.node_id, "")
            result = result.replace(placeholder, str(value))
        # Also support output placeholders for prompts
        for pin in self.outputs:
            placeholder = f"{{{pin.name}}}"
            # Keep output placeholders as-is for LLM to understand
            result = result.replace(placeholder, f"[{pin.name}]")
        return result

    def get_input_by_name(self, name: str, inputs: Dict[str, Any]) -> Any:
        """Get input value by user-assigned name"""
        for pin in self.inputs:
            if pin.name == name:
                return inputs.get(pin.node_id)
        raise KeyError(f"No input with name '{name}'")

    def get_input_groups(self) -> Dict[int, List[InstanceNodePin]]:
        """Get inputs organized by group"""
        groups: Dict[int, List[InstanceNodePin]] = {}
        for pin in self.inputs:
            if pin.group_index not in groups:
                groups[pin.group_index] = []
            groups[pin.group_index].append(pin)
        return groups

    def get_output_groups(self) -> Dict[int, List[InstanceNodePin]]:
        """Get outputs organized by group"""
        groups: Dict[int, List[InstanceNodePin]] = {}
        for pin in self.outputs:
            if pin.group_index not in groups:
                groups[pin.group_index] = []
            groups[pin.group_index].append(pin)
        return groups
```

- [x] **3.2 Update Module Handler Base Class**
**File**: `transformation_pipeline_server/src/features/modules/core/base.py`

Add context parameter to the base class:
```python
from typing import Dict, Any
from shared.models.execution_context import ExecutionContext

class BaseModule(ABC):
    """Base class for all module handlers"""

    @abstractmethod
    def run(
        self,
        inputs: Dict[str, Any],
        config: Dict[str, Any],
        context: ExecutionContext # NEW 
    ) -> Dict[str, Any]:
        """Execute the module logic"""
        pass
```

## Phase 4: Dask Executor Implementation

- [x] **4.1 Add Execution Audit Trail (Database Persistence)**
**File**: `transformation_pipeline_server/src/shared/database/models.py` (add to existing file)

Add execution tracking models:
```python
class ExecutionRunModel(Base):
    __tablename__ = "execution_runs"

    run_id = Column(String, primary_key=True)
    pipeline_id = Column(String, ForeignKey("pipeline_definitions.id"))
    status = Column(String, nullable=False)  # "running", "success", "failed"
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    entry_values = Column(Text)  # JSON - serialized entry values
    created_at = Column(DateTime, default=datetime.utcnow)

class ExecutionStepModel(Base):
    __tablename__ = "execution_steps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String, ForeignKey("execution_runs.run_id"))
    module_instance_id = Column(String, nullable=False)
    step_number = Column(Integer, nullable=False)
    inputs = Column(Text)  # JSON - serialized inputs
    outputs = Column(Text)  # JSON - serialized outputs
    elapsed_ms = Column(Float, nullable=False)
    error = Column(Text, nullable=True)
    executed_at = Column(DateTime, nullable=False)
```

**File**: New file `transformation_pipeline_server/src/shared/models/execution.py`

Create domain models for execution history:
```python
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class ExecutionRun(BaseModel):
    """Domain model for execution run"""
    run_id: str
    pipeline_id: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    entry_values: Dict[str, Any]
    created_at: datetime

    @classmethod
    def from_db_model(cls, db_model) -> "ExecutionRun":
        """Convert from SQLAlchemy model"""
        return cls(
            run_id=db_model.run_id,
            pipeline_id=db_model.pipeline_id,
            status=db_model.status,
            started_at=db_model.started_at,
            completed_at=db_model.completed_at,
            entry_values=json.loads(db_model.entry_values) if db_model.entry_values else {},
            created_at=db_model.created_at
        )

class ExecutionStep(BaseModel):
    """Domain model for execution step"""
    id: int
    run_id: str
    module_instance_id: str
    step_number: int
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    elapsed_ms: float
    error: Optional[str] = None
    executed_at: datetime

    @classmethod
    def from_db_model(cls, db_model) -> "ExecutionStep":
        """Convert from SQLAlchemy model"""
        return cls(
            id=db_model.id,
            run_id=db_model.run_id,
            module_instance_id=db_model.module_instance_id,
            step_number=db_model.step_number,
            inputs=json.loads(db_model.inputs) if db_model.inputs else {},
            outputs=json.loads(db_model.outputs) if db_model.outputs else {},
            elapsed_ms=db_model.elapsed_ms,
            error=db_model.error,
            executed_at=db_model.executed_at
        )

class ExecutionRunCreate(BaseModel):
    """Model for creating execution run"""
    run_id: str
    pipeline_id: str
    status: str = "running"
    started_at: datetime
    entry_values: Dict[str, Any]

    def model_dump_for_db(self) -> dict:
        """Convert to database format"""
        data = self.model_dump()
        data['entry_values'] = json.dumps(data['entry_values'])
        return data

class ExecutionStepCreate(BaseModel):
    """Model for creating execution step"""
    run_id: str
    module_instance_id: str
    step_number: int
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    elapsed_ms: float
    error: Optional[str] = None
    executed_at: datetime

    def model_dump_for_db(self) -> dict:
        """Convert to database format"""
        data = self.model_dump()
        data['inputs'] = json.dumps(data['inputs'])
        data['outputs'] = json.dumps(data['outputs'])
        return data
```

**File**: New file `transformation_pipeline_server/src/shared/database/repositories/execution_run.py`

Create ExecutionRunRepository following current patterns:
```python
import logging
import json
from typing import List, Optional
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError

from .base import BaseRepository
from shared.database.models import ExecutionRunModel, ExecutionStepModel
from shared.models.execution import (
    ExecutionRun, ExecutionRunCreate,
    ExecutionStep, ExecutionStepCreate
)
from shared.exceptions import RepositoryError, ObjectNotFoundError

logger = logging.getLogger(__name__)

class ExecutionRunRepository(BaseRepository[ExecutionRunModel]):
    """Repository for execution run operations"""

    @property
    def model_class(self):
        return ExecutionRunModel

    def _convert_to_domain_object(self, db_model: ExecutionRunModel) -> ExecutionRun:
        """Convert SQLAlchemy model to domain object"""
        return ExecutionRun.from_db_model(db_model)

    def create_run(self, run_create: ExecutionRunCreate) -> ExecutionRun:
        """Create a new execution run"""
        try:
            with self.connection_manager.session_scope() as session:
                data = run_create.model_dump_for_db()
                model = self.model_class(**data)
                session.add(model)
                session.flush()
                session.refresh(model)

                logger.info(f"Created execution run: {run_create.run_id}")
                return self._convert_to_domain_object(model)

        except SQLAlchemyError as e:
            logger.error(f"Error creating execution run: {e}")
            raise RepositoryError(f"Failed to create execution run: {e}") from e

    def update_run_status(self, run_id: str, status: str, completed_at: datetime) -> Optional[ExecutionRun]:
        """Update run status on completion"""
        try:
            with self.connection_manager.session_scope() as session:
                model = session.query(self.model_class).filter_by(run_id=run_id).first()

                if not model:
                    logger.warning(f"Execution run not found: {run_id}")
                    return None

                model.status = status
                model.completed_at = completed_at
                session.flush()
                session.refresh(model)

                logger.info(f"Updated execution run status: {run_id} -> {status}")
                return self._convert_to_domain_object(model)

        except SQLAlchemyError as e:
            logger.error(f"Error updating execution run {run_id}: {e}")
            raise RepositoryError(f"Failed to update execution run: {e}") from e

    def get_run_by_id(self, run_id: str) -> Optional[ExecutionRun]:
        """Get execution run by ID"""
        try:
            with self.connection_manager.session_scope() as session:
                model = session.query(self.model_class).filter_by(run_id=run_id).first()

                if not model:
                    return None

                return self._convert_to_domain_object(model)

        except SQLAlchemyError as e:
            logger.error(f"Error getting execution run {run_id}: {e}")
            raise RepositoryError(f"Failed to get execution run: {e}") from e

    def get_runs_by_pipeline(self, pipeline_id: str, limit: int = 10) -> List[ExecutionRun]:
        """Get recent execution runs for a pipeline"""
        try:
            with self.connection_manager.session_scope() as session:
                models = session.query(self.model_class).filter_by(
                    pipeline_id=pipeline_id
                ).order_by(
                    self.model_class.started_at.desc()
                ).limit(limit).all()

                return [self._convert_to_domain_object(m) for m in models]

        except SQLAlchemyError as e:
            logger.error(f"Error getting runs for pipeline {pipeline_id}: {e}")
            raise RepositoryError(f"Failed to get execution runs: {e}") from e

```

**File**: New file `transformation_pipeline_server/src/shared/database/repositories/execution_step.py`

Create ExecutionStepRepository in separate file:
```python
import logging
import json
from typing import List, Optional
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError

from .base import BaseRepository
from shared.database.models import ExecutionStepModel
from shared.models.execution import ExecutionStep, ExecutionStepCreate
from shared.exceptions import RepositoryError

logger = logging.getLogger(__name__)

class ExecutionStepRepository(BaseRepository[ExecutionStepModel]):
    """Repository for execution step operations"""

    @property
    def model_class(self):
        return ExecutionStepModel

    def _convert_to_domain_object(self, db_model: ExecutionStepModel) -> ExecutionStep:
        """Convert SQLAlchemy model to domain object"""
        return ExecutionStep.from_db_model(db_model)

    def create_step(self, step_create: ExecutionStepCreate) -> ExecutionStep:
        """Add an execution step to the history"""
        try:
            with self.connection_manager.session_scope() as session:
                data = step_create.model_dump_for_db()
                model = self.model_class(**data)
                session.add(model)
                session.flush()
                session.refresh(model)

                logger.debug(f"Created execution step for run: {step_create.run_id}")
                return self._convert_to_domain_object(model)

        except SQLAlchemyError as e:
            logger.error(f"Error creating execution step: {e}")
            raise RepositoryError(f"Failed to create execution step: {e}") from e

    def get_steps_by_run(self, run_id: str) -> List[ExecutionStep]:
        """Get all steps for an execution run"""
        try:
            with self.connection_manager.session_scope() as session:
                models = session.query(self.model_class).filter_by(
                    run_id=run_id
                ).order_by(self.model_class.step_number).all()

                return [self._convert_to_domain_object(m) for m in models]

        except SQLAlchemyError as e:
            logger.error(f"Error getting steps for run {run_id}: {e}")
            raise RepositoryError(f"Failed to get execution steps: {e}") from e
```

- [x] **4.2 Create Pipeline Executor**
**File**: New file `transformation_pipeline_server/src/features/pipeline/execution/executor.py`

Create pipeline executor that works with domain objects:
```python
import time
from datetime import datetime
from typing import Dict, Any, List, Literal, Optional, Tuple
from dask import delayed, compute
import logging

from shared.models.execution_result import RunResult, ExecutionError
from shared.models.execution_context import ExecutionContext
from shared.models.execution import ExecutionRunCreate, ExecutionStepCreate
from shared.models.pipeline_step import PipelineStep
from shared.models.pipeline import InstanceNodePin
from features.modules.core.registry import ModuleRegistry

logger = logging.getLogger(__name__)

class PipelineExecutor:
    """Executes compiled pipelines using Dask for parallel processing"""

    def __init__(self):
        # Only module registry needed, no repositories
        self.registry = ModuleRegistry()

    def run_pipeline(
        self,
        pipeline_id: str,
        run_id: str,  # Generated by service layer
        steps: List[PipelineStep],  # Domain objects from shared.models
        entry_values: Dict[str, Any],
        *,
        scheduler: Literal["threads", "processes", "distributed"] = "threads",
        max_workers: Optional[int] = None,
        fail_fast: bool = True
    ) -> Tuple[ExecutionRunCreate, List[ExecutionStepCreate], RunResult]:
        """
        Execute a compiled pipeline with entry values.

        Args:
            pipeline_id: ID of the pipeline being executed
            run_id: Pre-generated execution run ID
            steps: List of PipelineStep domain objects
            entry_values: Entry point values
            scheduler: Dask scheduler type
            max_workers: Maximum number of workers for parallel execution
            fail_fast: Whether to stop on first error

        Returns:
            Tuple of:
            - ExecutionRunCreate: For creating/updating the run record
            - List[ExecutionStepCreate]: For creating step records
            - RunResult: The execution result for API response
        """
        started_at = datetime.utcnow()

        try:
            # 1. Validate entry values
            required_entries = self._get_required_entries(steps)
            missing = set(required_entries) - set(entry_values.keys())
            if missing:
                raise ValueError(f"Missing required entry values: {missing}")

            # 2. Build Dask graph
            delayed_tasks, action_tasks = self._build_dask_graph(steps, entry_values, run_id)

            # 3. Execute only action tasks
            logger.info(f"Executing {len(action_tasks)} action tasks for run {run_id}")
            results = compute(*action_tasks, scheduler=scheduler)

            # 4. Process results into domain objects
            step_creates, actions, errors, timings = self._process_results(results)

            completed_at = datetime.utcnow()
            status = "failed" if errors else "success"

            # 5. Create domain objects for return
            run_create = ExecutionRunCreate(
                run_id=run_id,
                pipeline_id=pipeline_id,
                status=status,
                started_at=started_at,
                entry_values=entry_values
                # completed_at will be set by service when persisting
            )

            run_result = RunResult(
                status=status,
                run_id=run_id,
                started_at=started_at.isoformat(),
                completed_at=completed_at.isoformat(),
                actions=actions,
                errors=errors,
                timings=timings
            )

            return run_create, step_creates, run_result

        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}")

            # Create minimal domain objects for failed execution
            completed_at = datetime.utcnow()

            run_create = ExecutionRunCreate(
                run_id=run_id,
                pipeline_id=pipeline_id,
                status="failed",
                started_at=started_at,
                entry_values=entry_values
                # completed_at will be set by service when persisting
            )

            run_result = RunResult(
                status="failed",
                run_id=run_id,
                started_at=started_at.isoformat(),
                completed_at=completed_at.isoformat(),
                errors=[ExecutionError(
                    code="EXECUTION_FAILED",
                    message=str(e),
                    module_instance_id=None
                )],
                actions=[],
                timings={}
            )

            return run_create, [], run_result

    def _build_dask_graph(self, steps, entry_values, run_id):
        """Build the Dask delayed task graph"""

        # Maps for tracking tasks
        delayed_by_module = {}
        producer_of_pin = {}

        # Create entry tasks
        @delayed(pure=True)
        def _entry_passthrough(v):
            return v

        for entry_id, value in entry_values.items():
            producer_of_pin[entry_id] = _entry_passthrough(value)

        # Create task for each step
        action_tasks = []
        for step in steps:
            task = self._make_task(step, producer_of_pin, run_id)
            delayed_by_module[step.module_instance_id] = task

            # Track output producers
            if step.node_metadata:
                for output in step.node_metadata.get("outputs", []):
                    # outputs is List[InstanceNodePin]
                    producer_of_pin[output.node_id] = task

            # Track action tasks
            if step.module_kind == "action":
                action_tasks.append(task)

        return delayed_by_module, action_tasks

    def _make_task(self, step, producer_of_pin, run_id):
        """Create a delayed task for a pipeline step"""

        # Resolve module handler
        handler_cls = self.registry.resolve(step.module_ref)
        handler = handler_cls()

        # Prepare dependencies
        deps = {}
        for input_pin, mapping in step.input_field_mappings.items():
            source_pin = mapping["source_field"]
            if source_pin in producer_of_pin:
                deps[source_pin] = producer_of_pin[source_pin]
            else:
                raise ValueError(f"No producer for pin {source_pin}")

        @delayed(pure=(step.module_kind != "action"))
        def _run_instance(**upstream_outputs):
            t0 = time.perf_counter()
            executed_at = datetime.utcnow()

            # Build inputs
            inputs = {
                input_pin: upstream_outputs[mapping["source_field"]]
                for input_pin, mapping in step.input_field_mappings.items()
            }

            # Create execution context
            # Extract inputs and outputs from node_metadata dict
            metadata = step.node_metadata or {}
            context = ExecutionContext(
                inputs=metadata.get("inputs", []),
                outputs=metadata.get("outputs", []),
                module_instance_id=step.module_instance_id,
                run_id=run_id
            )

            try:
                outputs = handler.run(inputs, step.module_config, context)
                ok = True
                err = None
            except Exception as e:
                ok = False
                outputs = {}
                err = f"{e.__class__.__name__}: {e}"
                logger.error(f"Module {step.module_instance_id} failed: {err}")

            t1 = time.perf_counter()
            elapsed_ms = (t1 - t0) * 1000.0

            # Return all data needed for tracking
            return {
                "__ok__": ok,
                "__err__": err,
                "__elapsed_ms__": elapsed_ms,
                "__module_instance_id__": step.module_instance_id,
                "__module_kind__": step.module_kind,
                "__step_number__": step.step_number,
                "__inputs__": inputs,  # Keep for tracking
                "__executed_at__": executed_at,
                "__run_id__": run_id,  # Pass through for ExecutionStepCreate
                "outputs": outputs
            }

        return _run_instance(**deps)

    def _get_required_entries(self, steps):
        """Extract required entry pins from steps"""
        required = set()
        for step in steps:
            for mapping in step.input_field_mappings.values():
                if mapping.get("source_module_id") == "entry":
                    required.add(mapping["source_field"])
        return required

    def _process_results(self, results) -> Tuple[List[ExecutionStepCreate], List[Dict], List[ExecutionError], Dict[str, float]]:
        """
        Process execution results into domain objects.

        Returns:
            Tuple of:
            - List[ExecutionStepCreate]: Step execution records
            - List[Dict]: Action outputs
            - List[ExecutionError]: Execution errors
            - Dict[str, float]: Timing information
        """
        step_creates = []
        actions = []
        errors = []
        timings = {}

        for env in results:
            mid = env["__module_instance_id__"]
            timings[mid] = env["__elapsed_ms__"]

            # Create ExecutionStepCreate domain object
            step_create = ExecutionStepCreate(
                run_id=env["__run_id__"],
                module_instance_id=mid,
                step_number=env["__step_number__"],
                inputs=env["__inputs__"],
                outputs=env["outputs"],
                elapsed_ms=env["__elapsed_ms__"],
                error=env["__err__"],
                executed_at=env["__executed_at__"]
            )
            step_creates.append(step_create)

            if not env["__ok__"]:
                errors.append(ExecutionError(
                    code="MODULE_FAILED",
                    message=env["__err__"],
                    module_instance_id=mid
                ))
            else:
                actions.append({
                    "module_instance_id": mid,
                    "outputs": env["outputs"]
                })

        return step_creates, actions, errors, timings
```

- [x] **4.3 Create Execution Models**
**File**: New file `transformation_pipeline_server/src/shared/models/execution_result.py`

```python
from typing import Dict, Any, List, Literal, Optional
from pydantic import BaseModel, Field

class ExecutionError(BaseModel):
    """Error that occurred during execution"""
    code: str
    message: str
    module_instance_id: Optional[str] = None

class RunResult(BaseModel):
    """Result of a pipeline execution"""
    status: Literal["success", "failed"]
    run_id: str
    started_at: str
    completed_at: str
    actions: List[Dict[str, Any]] = Field(default_factory=list)
    errors: List[ExecutionError] = Field(default_factory=list)
    timings: Dict[str, float] = Field(default_factory=dict)
    # NEW: Optionally include execution history
    execution_trace: Optional[List[Dict[str, Any]]] = Field(default=None)
```

**File**: New file `transformation_pipeline_server/src/api/schemas/execution.py`

```python
from typing import Dict, Any, Optional
from pydantic import BaseModel

class ExecutionRequest(BaseModel):
    """Request to execute a pipeline"""
    entry_values: Dict[str, Any]
    scheduler: str = "threads"
    max_workers: Optional[int] = None
    fail_fast: bool = True
    include_trace: bool = False  # NEW: Option to include execution trace in response

class ExecutionResponse(BaseModel):
    """Response from pipeline execution"""
    # Inherits all fields from RunResult
    pass
```

- [x] **4.4 Sequential Fallback Executor** (Skipped - Optional)

The sequential executor is a simplified version for debugging that runs steps in order without Dask. It's useful for testing but not critical for the main implementation. We can implement this later if needed for debugging purposes.

## Phase 5: API Endpoints

- [ ] **5.1 Create Execution Endpoint**
**File**: `transformation_pipeline_server/src/api/routers/pipelines.py`

Add the following endpoint to handle pipeline execution:
```python
from api.schemas.execution import ExecutionRequest, ExecutionResponse
from features.pipeline.execution.executor import PipelineExecutor

@router.post("/{pipeline_id}/execute", response_model=ExecutionResponse)
async def execute_pipeline(
    pipeline_id: str,
    request: ExecutionRequest,
    pipeline_service: PipelineService = Depends(lambda: ServiceContainer.get_pipeline_service())
):
    """
    Execute a compiled pipeline with entry values

    Args:
        pipeline_id: Pipeline ID to execute
        request: Execution request with entry values

    Returns:
        ExecutionResponse with results, errors, and timings

    Raises:
        404: Pipeline not found
        400: Invalid entry values or pipeline not compiled
        500: Execution error
    """
    logger.info(f"Execution requested for pipeline: {pipeline_id}")

    try:
        # Get pipeline to verify it exists and get checksum
        pipeline = pipeline_service.get_pipeline(pipeline_id)

        if not pipeline.plan_checksum:
            raise HTTPException(
                status_code=400,
                detail="Pipeline has not been compiled yet"
            )

        # Execute pipeline
        executor = PipelineExecutor()
        result = executor.run_pipeline(
            pipeline_id=pipeline_id,
            plan_checksum=pipeline.plan_checksum,
            entry_values=request.entry_values,
            scheduler=request.scheduler,
            max_workers=request.max_workers,
            fail_fast=request.fail_fast
        )

        logger.info(f"Pipeline {pipeline_id} execution completed with status: {result.status}")

        return ExecutionResponse(**result.model_dump())

    except ObjectNotFoundError:
        raise HTTPException(status_code=404, detail=f"Pipeline {pipeline_id} not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}")
        raise HTTPException(status_code=500, detail="Pipeline execution failed")
```

## Phase 6: Frontend Updates

- [ ] **6.1 Add Execution UI**
**File**: New component `client/src/renderer/components/transformation-pipeline/ExecutePipelineModal.tsx`

Create a modal component that:
```typescript
interface ExecutePipelineModalProps {
  isOpen: boolean;
  onClose: () => void;
  pipelineId: string;
  entryPoints: EntryPoint[];  // From pipeline state
}

// Component will:
// 1. Display form fields for each entry point
// 2. Allow user to input values (with type-appropriate inputs)
// 3. Submit execution request to backend
// 4. Show execution progress/status
// 5. Display results in formatted output
// 6. Show any errors with module context

// Key features:
// - Dynamic form generation based on entry points
// - Type validation (string, number, boolean inputs)
// - Loading state during execution
// - Results display with timing information
// - Error display with helpful context
```

Implementation details:
- Use React Hook Form for dynamic form generation
- Type-specific input components (text, number, checkbox)
- Real-time validation based on entry point types
- Collapsible sections for results per module
- Copy-to-clipboard for results
- Export results as JSON

## Execution Audit Trail Addendum

### Problem Statement
For testing and production auditing, we need to track intermediate data as it flows through the pipeline, showing how each module transforms the data step by step.

### Option 1: In-Memory Trace (Development/Testing)
**Pros**: Fast, no persistence overhead
**Cons**: Lost on completion, limited by memory

Modify executor to collect traces:
```python
class ExecutionTrace:
    module_instance_id: str
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    elapsed_ms: float
    error: Optional[str]

# In executor, collect traces
traces: List[ExecutionTrace] = []
# Add to RunResult
```

### Option 2: Database Persistence (Production)
**Pros**: Permanent audit trail, queryable history
**Cons**: Storage overhead, slower execution

Create execution history table:
```python
class ExecutionRunModel(Base):
    __tablename__ = "execution_runs"

    run_id = Column(String, primary_key=True)
    pipeline_id = Column(String, ForeignKey("pipeline_definitions.id"))
    status = Column(String)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    entry_values = Column(Text)  # JSON

class ExecutionStepModel(Base):
    __tablename__ = "execution_steps"

    id = Column(Integer, primary_key=True)
    run_id = Column(String, ForeignKey("execution_runs.run_id"))
    module_instance_id = Column(String)
    step_number = Column(Integer)
    inputs = Column(Text)  # JSON - serialized inputs
    outputs = Column(Text)  # JSON - serialized outputs
    elapsed_ms = Column(Float)
    error = Column(Text, nullable=True)
    executed_at = Column(DateTime)
```

### Option 3: File-Based Logging (Hybrid)
**Pros**: Balance of performance and persistence
**Cons**: Requires log rotation, parsing for queries

Write to structured log files:
```python
# In executor, write to execution log
execution_logger = logging.getLogger("pipeline.execution")
execution_logger.info(json.dumps({
    "run_id": run_id,
    "module": module_instance_id,
    "inputs": serialize_for_logging(inputs),
    "outputs": serialize_for_logging(outputs),
    "elapsed_ms": elapsed_ms
}))
```

### Recommended Approach
We've implemented **Option 2** (database persistence) directly in the PipelineExecutor using repositories:

- ExecutionRunRepository handles run-level tracking
- ExecutionStepRepository handles step-level tracking
- The `enable_tracking` flag controls whether tracking is performed
- Repositories manage their own database sessions and error handling
- No intermediate tracker abstraction needed

### Data Serialization Considerations
- Large binary data: Store reference/hash, not full content
- Circular references: Use custom JSON encoder
- Sensitive data: Mask/redact based on configuration
- Size limits: Truncate large outputs with indicators

### UI Integration
Add to ExecutePipelineModal:
- "Show Execution Trace" accordion
- Step-by-step data flow visualization
- Before/after comparison per module
- Download trace as JSON
- Filter by module type or status