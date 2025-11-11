"""
Pipeline Execution Service
Builds a Dask task graph from compiled steps and executes with auditing.

Usage:
    service = PipelineExecutionService(cm, services)
    run = service.execute_pipeline(
        pipeline_definition_id=123,
        eto_run_id=456,
        entry_values_by_name={"origin": "SFO", "destination": "LAX"}
    )
"""

from typing import Dict, Any, List, Tuple, Optional
import logging
from datetime import datetime, date
from threading import Lock
from dask.delayed import delayed
from dask.base import compute

from shared.database import DatabaseConnectionManager
from shared.database.repositories import (
    PipelineDefinitionRepository,
    PipelineDefinitionStepRepository,
    EtoRunPipelineExecutionRepository,
    EtoRunPipelineExecutionStepRepository,
    ModuleRepository,
)
from features.modules.utils.registry import ModuleRegistry
from shared.types.pipeline_definition import PipelineDefinition
from shared.types.pipeline_definition_step import PipelineDefinitionStep
from shared.types.pipelines import NodeInstance
from shared.types.pipeline_execution import (
    PipelineExecutionRun,
    PipelineExecutionRunCreate,
    PipelineExecutionStepCreate,
    # Simulation types
    PipelineExecutionStepResult,
    ActionExecutionData,
    PipelineExecutionResult,
)

logger = logging.getLogger(__name__)


# ==================== Utility Classes ====================


class ExecutionCancelled:
    """
    Sentinel class to indicate a module did not execute due to upstream failure.

    When a module fails, it returns ExecutionCancelled instances for all outputs.
    Downstream modules detect this and skip execution, propagating the sentinel.
    This prevents downstream modules from executing with empty/invalid data.
    """
    def __init__(self, reason: str = "Upstream module failed"):
        self.reason = reason

    def __repr__(self):
        return f"ExecutionCancelled({self.reason})"


class BranchNotTaken:
    """
    Sentinel class to indicate a module did not execute because its branch was not selected.

    Used by conditional branching modules (if_branch) to skip execution of modules
    in the non-selected branch path. Similar to ExecutionCancelled but with different
    semantic meaning - the branch was intentionally not selected based on a condition,
    not cancelled due to an error.
    """
    def __init__(self, reason: str = "Branch not selected"):
        self.reason = reason

    def __repr__(self):
        return f"BranchNotTaken({self.reason})"


class StepResultCollector:
    """
    Thread-safe collector for execution step results.

    Used during Dask execution to collect module execution results
    as they complete. Thread-safe because Dask may execute tasks
    in parallel threads.
    """

    def __init__(self):
        self.results: List[PipelineExecutionStepResult] = []
        self.lock = Lock()

    def add(self, result: PipelineExecutionStepResult) -> None:
        """Add a step result to the collection (thread-safe)"""
        with self.lock:
            self.results.append(result)

    def get_all(self) -> List[PipelineExecutionStepResult]:
        """Get all collected results, sorted by step_number"""
        with self.lock:
            return sorted(self.results, key=lambda s: s.step_number)


class ActionDataCollector:
    """
    Thread-safe collector for action execution data.

    Collects data about action modules during graph execution.
    Actions are not executed during simulation - only their data is collected
    to show users what would happen in production.
    """

    def __init__(self):
        self.actions: List[ActionExecutionData] = []
        self.lock = Lock()

    def add(self, data: ActionExecutionData) -> None:
        """Add action data to the collection (thread-safe)"""
        with self.lock:
            self.actions.append(data)

    def get_all(self) -> List[ActionExecutionData]:
        """Get all collected action data"""
        with self.lock:
            return list(self.actions)

    def to_executed_actions_dict(self) -> Dict[str, Dict[str, Any]]:
        """
        Convert collected actions to executed_actions format.

        Returns:
            Dict in format: {"module_title": {"upstream_pin_name": "value", ...}, ...}
            If multiple actions have the same title, appends #1, #2, etc.
        """
        with self.lock:
            result = {}
            title_counts: Dict[str, int] = {}

            for action in self.actions:
                title = action.module_title

                # Track how many times we've seen this title
                if title in title_counts:
                    title_counts[title] += 1
                    unique_title = f"{title} #{title_counts[title]}"
                else:
                    title_counts[title] = 1
                    # First occurrence - check if we'll have duplicates
                    # Count total occurrences
                    total_count = sum(1 for a in self.actions if a.module_title == title)
                    if total_count > 1:
                        unique_title = f"{title} #1"
                    else:
                        unique_title = title

                result[unique_title] = action.inputs

            return result


# ==================== Serialization Utilities ====================


def _serialize_value(value: Any, type_hint: str) -> Any:
    """
    Serialize a value to JSON-compatible format for audit storage.

    Args:
        value: Raw value from module execution
        type_hint: Type hint from pin metadata ("datetime", "str", etc.)

    Returns:
        JSON-serializable value
    """
    if type_hint == "datetime":
        if isinstance(value, (datetime, date)):
            return value.isoformat()
    return value


def _serialize_io_for_audit(
    io_dict: Dict[str, Any],
    pins: List[NodeInstance]
) -> Dict[str, Dict[str, Any]]:
    """
    Transform {node_id: value} to {node_id: {name, value, type}} for execution visualization.

    This converts raw module I/O into a format suitable for ExecutedPipelineViewer,
    which needs node_id as keys and name as a field for proper visualization.

    NOTE: This is used for OUTPUTS. For INPUTS, use _serialize_inputs_for_audit instead.

    Args:
        io_dict: Raw I/O from module execution {node_id: value}
        pins: Pin metadata with node_id, name, and type

    Returns:
        Dict in format: {node_id: {name, value, type}}

    Example:
        Input:  {"m1_out_0": "ABC123"}, [NodeInstance(node_id="m1_out_0", name="hawb", type="str")]
        Output: {"m1_out_0": {"name": "hawb", "value": "ABC123", "type": "str"}}
    """
    result = {}
    for pin in pins:
        if pin.node_id in io_dict:
            raw_value = io_dict[pin.node_id]
            result[pin.node_id] = {
                "name": pin.name,
                "value": _serialize_value(raw_value, pin.type),
                "type": pin.type
            }
    return result


def _serialize_inputs_for_audit(
    io_dict: Dict[str, Any],
    pins: List[NodeInstance],
    input_field_mappings: Dict[str, str],
    all_nodes_metadata: Dict[str, List[NodeInstance]],
    entry_points_lookup: Dict[str, str]
) -> Dict[str, Dict[str, Any]]:
    """
    Transform inputs to {node_id: {name, value, type}} using UPSTREAM pin names.

    For inputs, we want to show the upstream output pin name (what's connected),
    not the current module's input pin name (which is just the group name).

    Args:
        io_dict: Raw inputs from module execution {input_node_id: value}
        pins: Input pin metadata with node_id, name, and type
        input_field_mappings: Maps input_pin_id -> upstream_output_pin_id
        all_nodes_metadata: All node metadata from pipeline state to look up upstream pin names
        entry_points_lookup: Entry point node_id -> name mapping

    Returns:
        Dict in format: {input_node_id: {name: upstream_pin_name, value, type}}

    Example:
        Input:
            io_dict = {"module2_in_0": "ABC123"}
            pins = [NodeInstance(node_id="module2_in_0", name="text", type="str")]
            input_field_mappings = {"module2_in_0": "transform_out_0"}
            all_nodes_metadata has NodeInstance(node_id="transform_out_0", name="hawb", type="str")
        Output:
            {"module2_in_0": {"name": "hawb", "value": "ABC123", "type": "str"}}
    """
    # Build a lookup map of node_id -> name from all metadata
    node_id_to_name = {}
    for node_list in all_nodes_metadata.values():
        for node in node_list:
            node_id_to_name[node.node_id] = node.name

    # Add entry points to the lookup
    node_id_to_name.update(entry_points_lookup)

    result = {}
    for pin in pins:
        if pin.node_id in io_dict:
            raw_value = io_dict[pin.node_id]

            # Look up the upstream pin that's connected to this input
            upstream_pin_id = input_field_mappings.get(pin.node_id)

            # Use upstream pin name if found, otherwise fall back to current pin name
            if upstream_pin_id and upstream_pin_id in node_id_to_name:
                display_name = node_id_to_name[upstream_pin_id]
            else:
                # Fallback: use the input pin name
                display_name = pin.name
                logger.warning(
                    f"Could not find upstream pin name for input {pin.node_id}, "
                    f"upstream_pin_id={upstream_pin_id}, using fallback name: {display_name}"
                )

            result[pin.node_id] = {
                "name": display_name,
                "value": _serialize_value(raw_value, pin.type),
                "type": pin.type
            }
    return result


def _convert_to_named_inputs(
    io_dict: Dict[str, Any],
    pins: List[NodeInstance]
) -> Dict[str, Any]:
    """
    Convert {node_id: value} to {node_name: value} for action execution.

    Actions need inputs keyed by name (not node ID) for handler execution.

    Args:
        io_dict: Raw I/O from graph {node_id: value}
        pins: Pin metadata with node_id and name

    Returns:
        Dict in format: {node_name: value}

    Example:
        Input:  {"m1_in_0": "ABC123"}, [NodeInstance(node_id="m1_in_0", name="hawb", ...)]
        Output: {"hawb": "ABC123"}
    """
    result = {}
    for pin in pins:
        if pin.node_id in io_dict:
            result[pin.name] = io_dict[pin.node_id]
    return result


def _convert_to_upstream_named_inputs(
    inputs_dict: Dict[str, Any],
    input_field_mappings: Dict[str, str],
    all_nodes_metadata: Dict[str, List[NodeInstance]],
    entry_points_lookup: Dict[str, str]
) -> Dict[str, Any]:
    """
    Convert action inputs to use upstream output pin names.

    For actions, we want to show the connected upstream output pin names
    as keys, not the action's input pin names.

    Args:
        inputs_dict: {input_pin_id: value}
        input_field_mappings: {input_pin_id: upstream_output_pin_id}
        all_nodes_metadata: All node metadata from pipeline state to look up pin names
        entry_points_lookup: Mapping of entry point node_id -> name

    Returns:
        Dict in format: {upstream_pin_name: value}

    Example:
        Input:
            inputs_dict = {"action_in_0": "value"}
            input_field_mappings = {"action_in_0": "transform_out_0"}
            all_nodes_metadata has NodeInstance(node_id="transform_out_0", name="pu")
        Output:
            {"pu": "value"}
    """
    result = {}

    # Build a lookup map of node_id -> name from all metadata
    node_id_to_name = {}
    for node_list in all_nodes_metadata.values():
        for node in node_list:
            node_id_to_name[node.node_id] = node.name

    # Add entry points to the lookup
    node_id_to_name.update(entry_points_lookup)

    # For each input, find its upstream output pin name
    for input_pin_id, value in inputs_dict.items():
        upstream_pin_id = input_field_mappings.get(input_pin_id)
        if upstream_pin_id and upstream_pin_id in node_id_to_name:
            upstream_name = node_id_to_name[upstream_pin_id]
            result[upstream_name] = value
        else:
            # Fallback: use the input pin name if we can't find upstream
            # This shouldn't happen in normal execution
            logger.warning(
                f"Could not find upstream pin name for {input_pin_id}, "
                f"upstream_pin_id={upstream_pin_id}"
            )
            result[input_pin_id] = value

    return result


class PipelineExecutionService:
    """
    Executes compiled pipelines using Dask task graphs.

    Orchestrates pipeline execution with:
    - Entry point validation
    - Lazy task graph construction
    - Transform/Logic → Action ordering (action barrier)
    - Audit trail persistence
    - Branch-isolated error handling (independent DAG branches continue on error)
    """

    connection_manager: DatabaseConnectionManager
    pipeline_repo: PipelineDefinitionRepository
    step_repo: PipelineDefinitionStepRepository
    run_repo: EtoRunPipelineExecutionRepository
    exec_step_repo: EtoRunPipelineExecutionStepRepository
    module_catalog_repo: ModuleRepository
    module_registry: ModuleRegistry
    services: Optional[Any]

    def __init__(
        self,
        connection_manager: DatabaseConnectionManager,
        services: Optional[Any] = None
    ) -> None:
        """
        Initialize pipeline execution service.

        Args:
            connection_manager: Database connection manager
            services: ServiceContainer for accessing other services (optional)

        Raises:
            RuntimeError: If connection_manager is None
        """
        if not connection_manager:
            raise RuntimeError("Database connection manager is required")

        self.connection_manager = connection_manager
        self.services = services
        self.module_registry = ModuleRegistry()

        # Initialize repositories
        self.pipeline_repo = PipelineDefinitionRepository(connection_manager=connection_manager)
        self.step_repo = PipelineDefinitionStepRepository(connection_manager=connection_manager)
        self.run_repo = EtoRunPipelineExecutionRepository(connection_manager=connection_manager)
        self.exec_step_repo = EtoRunPipelineExecutionStepRepository(connection_manager=connection_manager)
        self.module_catalog_repo = ModuleRepository(connection_manager=connection_manager)

        logger.info("PipelineExecutionService initialized")

    # ==================== Public API ====================

    def simulate_pipeline(
        self,
        steps: List[PipelineDefinitionStep],
        entry_values_by_name: Dict[str, Any],
        pipeline_state,  # PipelineState from pipelines module
    ) -> PipelineExecutionResult:
        """
        Execute a compiled pipeline WITHOUT executing actions (SIMULATION MODE).

        Used for:
        - Template builder preview
        - Pipeline testing
        - Dry runs

        Actions are NOT executed - only their input data is collected
        to show users what would happen in production.

        Policy:
          - Fail fast on missing required entry names
          - Extra entry names are ignored (logged)
          - All Action modules run only after all Transform/Logic modules succeed
          - Actions collect data but DON'T execute
          - Independent DAG branches continue execution even if one branch fails
          - Status is "success" (no errors), "partial" (some errors), or "failed" (all errors)

        Args:
            steps: Compiled pipeline steps to execute
            entry_values_by_name: Entry point values keyed by entry point name
            pipeline_state: Pipeline state containing entry points for mapping

        Returns:
            PipelineExecutionResult with steps and action data (actions.executed=False)

        Raises:
            ValueError: Missing required entry values
            RuntimeError: Module not found
        """
        return self._execute_pipeline_internal(
            steps=steps,
            entry_values_by_name=entry_values_by_name,
            pipeline_state=pipeline_state,
            execute_actions=False
        )

    def execute_pipeline(
        self,
        steps: List[PipelineDefinitionStep],
        entry_values_by_name: Dict[str, Any],
        pipeline_state,  # PipelineState from pipelines module
    ) -> PipelineExecutionResult:
        """
        Execute a compiled pipeline WITH actions (PRODUCTION MODE).

        Used for:
        - ETO production runs
        - Any workflow requiring actual action execution

        Actions ARE executed - side effects will occur (emails sent, API calls made, etc.)

        Policy:
          - Fail fast on missing required entry names
          - Extra entry names are ignored (logged)
          - All Action modules run only after all Transform/Logic modules succeed
          - Actions execute and produce side effects
          - Independent DAG branches continue execution even if one branch fails
          - Status is "success" (no errors), "partial" (some errors), or "failed" (all errors)

        Args:
            steps: Compiled pipeline steps to execute
            entry_values_by_name: Entry point values keyed by entry point name
            pipeline_state: Pipeline state containing entry points for mapping

        Returns:
            PipelineExecutionResult with steps and executed action results

        Raises:
            ValueError: Missing required entry values
            RuntimeError: Module not found
        """
        return self._execute_pipeline_internal(
            steps=steps,
            entry_values_by_name=entry_values_by_name,
            pipeline_state=pipeline_state,
            execute_actions=True
        )

    def _execute_pipeline_internal(
        self,
        steps: List[PipelineDefinitionStep],
        entry_values_by_name: Dict[str, Any],
        pipeline_state,  # PipelineState from pipelines module
        execute_actions: bool,
    ) -> PipelineExecutionResult:
        """
        Internal pipeline execution implementation.

        Args:
            steps: Compiled pipeline steps to execute
            entry_values_by_name: Entry point values keyed by entry point name
            pipeline_state: Pipeline state containing entry points for mapping
            execute_actions: If True, execute actions; if False, only collect action data

        Returns:
            PipelineExecutionResult with steps and action data

        Raises:
            ValueError: Missing required entry values
            RuntimeError: Module not found or execution failed
        """
        logger.info(f"Starting pipeline simulation with {len(steps)} steps")

        # Step 1: Map entry points
        entry_name_to_ids = self._map_entry_names_to_pin_ids_from_state(pipeline_state)

        # Step 2: Seed entry values
        producer_of_pin, missing, extras = self._seed_entry_values(
            entry_values_by_name, entry_name_to_ids
        )

        if missing:
            msg = f"Missing required entry values: {', '.join(missing)}"
            logger.error(msg)
            raise ValueError(msg)

        if extras:
            logger.warning(f"Ignoring extra entry values: {', '.join(extras)}")

        # Step 3: Build collectors
        collector = StepResultCollector()
        action_collector = ActionDataCollector()

        # Step 3.5: Build global node metadata lookup for actions
        # Actions need to look up upstream pin names from all steps
        all_nodes_metadata: Dict[str, List[NodeInstance]] = {}
        for step in steps:
            if step.node_metadata:
                for key, nodes in step.node_metadata.items():
                    if key not in all_nodes_metadata:
                        all_nodes_metadata[key] = []
                    all_nodes_metadata[key].extend(nodes)

        # Step 3.6: Build entry points lookup {node_id -> name}
        # Actions connected to entry points need to look up entry point names
        entry_points_lookup: Dict[str, str] = {
            ep.outputs[0].node_id: ep.name
            for ep in pipeline_state.entry_points
            if ep.outputs
        }

        # Step 4: Build Dask graph
        task_of_step: Dict[str, Any] = {}
        non_action_tasks: List[Any] = []
        action_steps: List[PipelineDefinitionStep] = []

        # Determine module kind for each step
        for step in steps:
            module_id = step.module_ref.split(":")[0] if ":" in step.module_ref else step.module_ref
            handler = self.module_registry.get(module_id)
            if handler and handler.kind.value == 'action':
                action_steps.append(step)
            else:
                # Transform or logic module
                task = self._make_step_task(step, producer_of_pin, collector, action_collector, all_nodes_metadata, entry_points_lookup, execute_actions=execute_actions)
                task_of_step[step.module_instance_id] = task
                self._publish_outputs_for_downstream(step, task, producer_of_pin)
                non_action_tasks.append(task)

        # Step 5: Create action barrier
        if non_action_tasks:
            barrier = delayed(lambda *args: True, pure=True)(*non_action_tasks)
        else:
            barrier = delayed(lambda: True, pure=True)()

        # Step 6: Build action tasks (depend on barrier + upstreams)
        for step in action_steps:
            task = self._make_step_task(
                step, producer_of_pin, collector, action_collector, all_nodes_metadata, entry_points_lookup,
                extra_dependencies=[barrier],
                execute_actions=execute_actions
            )
            task_of_step[step.module_instance_id] = task
            self._publish_outputs_for_downstream(step, task, producer_of_pin)

        # Step 7: Execute graph
        try:
            leaves = [t for t in task_of_step.values()] or list(producer_of_pin.values())
            if leaves:
                logger.info(f"Executing Dask graph with {len(leaves)} leaf tasks")
                compute(*leaves)  # No longer raises on first failure (modules return empty dicts)

            logger.info("Pipeline execution graph completed")
        except Exception as e:
            # Catch any unexpected errors during graph execution
            logger.exception(f"Unexpected error during pipeline execution: {e}")

        # Step 8: Collect all errors from execution steps
        collected_steps = collector.get_all()
        errors = [step.error for step in collected_steps if step.error]

        # Determine overall status based on error count
        if not errors:
            status = "success"
            error = None
            logger.info("Pipeline execution succeeded - all modules completed successfully")
        elif len(errors) == len(collected_steps):
            status = "failed"
            error = f"All {len(errors)} module(s) failed"
            logger.error(f"Pipeline execution failed completely: {error}")
        else:
            status = "partial"
            error = f"{len(errors)} of {len(collected_steps)} module(s) failed"
            logger.warning(f"Pipeline execution partially succeeded: {error}")

        # Log detailed error information
        logger.info(f"Returning pipeline result: status={status}, steps_count={len(collected_steps)}, errors_count={len(errors)}")
        for step in collected_steps:
            if step.error:
                logger.error(f"  Step {step.step_number} ({step.module_instance_id}): FAILED - {step.error}")
            else:
                logger.debug(f"  Step {step.step_number} ({step.module_instance_id}): SUCCESS")

        return PipelineExecutionResult(
            status=status,
            steps=collected_steps,
            executed_actions=action_collector.to_executed_actions_dict(),
            error=error
        )

    # ==================== Helper Methods (to be implemented) ====================

    def _require_pipeline(self, pipeline_definition_id: int) -> PipelineDefinition:
        """
        Load pipeline and verify it's compiled.

        Args:
            pipeline_definition_id: Pipeline definition ID

        Returns:
            Pipeline definition with full details

        Raises:
            ValueError: If pipeline not found
            RuntimeError: If pipeline not compiled
        """
        pipeline = self.pipeline_repo.get_by_id(pipeline_definition_id)

        if pipeline is None:
            raise ValueError(f"Pipeline definition {pipeline_definition_id} not found")

        if pipeline.compiled_plan_id is None:
            raise RuntimeError(
                f"Pipeline definition {pipeline_definition_id} is not compiled. "
                "Cannot execute uncompiled pipeline."
            )

        logger.debug(
            f"Loaded pipeline {pipeline_definition_id} with compiled plan {pipeline.compiled_plan_id}"
        )

        return pipeline

    def _require_compiled_steps(self, compiled_plan_id: int) -> List[PipelineDefinitionStep]:
        """
        Load compiled steps ordered by step_number.

        Args:
            compiled_plan_id: Compiled plan ID

        Returns:
            List of steps in execution order

        Raises:
            ValueError: If no steps found
        """
        steps = self.step_repo.get_steps_by_plan_id(compiled_plan_id)

        if not steps:
            raise ValueError(f"No compiled steps found for plan {compiled_plan_id}")

        logger.debug(f"Loaded {len(steps)} compiled steps for plan {compiled_plan_id}")

        return steps

    def _map_entry_names_to_pin_ids(
        self,
        pipeline: PipelineDefinition
    ) -> Dict[str, List[str]]:
        """
        Build {entry_name -> [pin_id, ...]} from pipeline_state.entry_points.

        Entry points can feed multiple downstream pins.

        Args:
            pipeline: Pipeline definition

        Returns:
            Mapping of entry point names to pin IDs
        """
        return self._map_entry_names_to_pin_ids_from_state(pipeline.pipeline_state)

    def _map_entry_names_to_pin_ids_from_state(
        self,
        pipeline_state
    ) -> Dict[str, List[str]]:
        """
        Build {entry_name -> [pin_id, ...]} from pipeline_state.entry_points.

        Entry points can feed multiple downstream pins.

        Args:
            pipeline_state: Pipeline state with entry points

        Returns:
            Mapping of entry point names to pin IDs
        """
        entry_name_to_ids: Dict[str, List[str]] = {}

        for entry_point in pipeline_state.entry_points:
            if entry_point.name not in entry_name_to_ids:
                entry_name_to_ids[entry_point.name] = []
            # Get node_id from first output pin
            if entry_point.outputs:
                entry_name_to_ids[entry_point.name].append(entry_point.outputs[0].node_id)

        logger.debug(f"Mapped {len(entry_name_to_ids)} entry point names to pin IDs")

        return entry_name_to_ids

    def _generate_mock_outputs(self, output_nodes: List[NodeInstance]) -> Dict[str, Any]:
        """
        Generate mock/placeholder output values for action modules during simulation.

        This allows downstream modules to execute even though actions don't run in simulation.
        Mock values are clearly identifiable as simulated data.

        Args:
            output_nodes: List of output NodeInstance objects from the action module

        Returns:
            Dictionary mapping node_id to mock value based on node type
        """
        from datetime import datetime

        mock_outputs = {}

        for node in output_nodes:
            node_type = node.type.lower()

            if node_type == "int":
                # Use 999999 as a clearly mock integer value
                mock_outputs[node.node_id] = 999999
            elif node_type == "str":
                # Use descriptive mock string
                mock_outputs[node.node_id] = f"MOCK_{node.name.upper()}"
            elif node_type == "bool":
                # Default to True for mock boolean
                mock_outputs[node.node_id] = True
            elif node_type == "float":
                # Use 999.99 as mock float
                mock_outputs[node.node_id] = 999.99
            elif node_type == "datetime":
                # Use current datetime as mock
                mock_outputs[node.node_id] = datetime.now()
            else:
                # For unknown types, use a mock string
                mock_outputs[node.node_id] = f"MOCK_OUTPUT"

        logger.debug(f"Generated mock outputs: {mock_outputs}")
        return mock_outputs

    def _seed_entry_values(
        self,
        entry_values_by_name: Dict[str, Any],
        entry_name_to_ids: Dict[str, List[str]],
    ) -> Tuple[Dict[str, Any], List[str], List[str]]:
        """
        Seed producer_of_pin with entry values wrapped in delayed tasks.

        Args:
            entry_values_by_name: Entry values provided by caller
            entry_name_to_ids: Mapping of entry names to pin IDs

        Returns:
            Tuple of (producer_of_pin, missing_names, extra_names)
            - producer_of_pin: {pin_id -> delayed(value)}
            - missing_names: Required entry names not provided
            - extra_names: Provided entry names not used
        """
        expected = set(entry_name_to_ids.keys())
        provided = set(entry_values_by_name.keys())
        missing = sorted(expected - provided)
        extras = sorted(provided - expected)

        @delayed(pure=True)  # type: ignore
        def _const(v):
            """Tiny wrapper so everything in the graph is delayed"""
            return v

        producer_of_pin: Dict[str, Any] = {}
        for name, node_ids in entry_name_to_ids.items():
            if name in entry_values_by_name:
                v = entry_values_by_name[name]
                for pin_id in node_ids:
                    producer_of_pin[pin_id] = _const(v)

        logger.debug(
            f"Seeded {len(producer_of_pin)} entry point pins. "
            f"Missing: {missing}, Extras: {extras}"
        )

        return producer_of_pin, missing, extras

    def _make_step_task(
        self,
        step: PipelineDefinitionStep,
        producer_of_pin: Dict[str, Any],
        collector: StepResultCollector,
        action_collector: ActionDataCollector,
        all_nodes_metadata: Dict[str, List[NodeInstance]],
        entry_points_lookup: Dict[str, str],
        extra_dependencies: Optional[List[Any]] = None,
        execute_actions: bool = False,
    ) -> Any:
        """
        Create delayed task for a module execution.

        For transforms/logic: Execute handler and return outputs
        For actions: Execute (if execute_actions=True) or just collect data (if False)

        Args:
            step: Pipeline step to execute
            producer_of_pin: Map of pin_id -> delayed value
            collector: Collector for step results
            action_collector: Collector for action data
            all_nodes_metadata: All node metadata for pin name lookups
            entry_points_lookup: Entry point node_id -> name mapping
            extra_dependencies: Additional delayed dependencies (e.g., action barrier)
            execute_actions: If True, execute action handlers; if False, only collect data

        Returns:
            Delayed task that produces {output_pin_id: value}
        """
        # Resolve handler
        module_id = step.module_ref.split(":")[0] if ":" in step.module_ref else step.module_ref

        # Debug logging for module lookup
        all_modules = self.module_registry.get_all()
        logger.debug(f"Looking for module_id: {module_id}")
        logger.debug(f"Registry has {len(all_modules)} modules")
        logger.debug(f"Registry instance ID: {id(self.module_registry)}")

        handler = self.module_registry.get(module_id)
        if not handler:
            raise RuntimeError(f"Module handler not found for {step.module_ref}")

        ConfigModel = handler.config_class()
        handlerInstance = handler()

        # Determine module kind from handler class
        module_kind = handler.kind.value  # "transform", "logic", or "action"
        is_action = (module_kind == "action")

        # Build execution context
        inputs_metadata = step.node_metadata.get("inputs") or []
        outputs_metadata = step.node_metadata.get("outputs") or []

        from shared.types.pipelines import ModuleExecutionContext
        ctx = ModuleExecutionContext(
            inputs=inputs_metadata,
            outputs=outputs_metadata,
            module_instance_id=step.module_instance_id,
            services=self.services,
        )

        # Gather upstream producers
        input_ids = list(step.input_field_mappings.keys())
        upstream_ids = [step.input_field_mappings[iid] for iid in input_ids]

        # Debug logging to diagnose missing pin IDs
        logger.debug(f"Step {step.module_instance_id}: Looking up upstream pins: {upstream_ids}")
        logger.debug(f"Available pins in producer_of_pin: {list(producer_of_pin.keys())}")

        # Check for missing pins before lookup
        missing_pins = [uid for uid in upstream_ids if uid not in producer_of_pin]
        if missing_pins:
            logger.error(
                f"Step {step.module_instance_id} requires pins {missing_pins} "
                f"which are not available. Available pins: {list(producer_of_pin.keys())}"
            )
            raise KeyError(
                f"Missing upstream pins {missing_pins} for step {step.module_instance_id}. "
                f"This may indicate incorrect topological ordering or missing entry points."
            )

        upstream_tasks = [producer_of_pin[uid] for uid in upstream_ids]

        if extra_dependencies:
            upstream_tasks = upstream_tasks + list(extra_dependencies)

        @delayed(pure=False)  # type: ignore
        def _run_module(*resolved):
            """
            Execute module (or collect action data).

            resolved contains:
            - first len(input_ids) items: resolved input values
            - remaining items: barrier tokens (ignored)
            """
            # Build {input_pin_id: value}
            values = resolved[:len(input_ids)]
            inputs_dict = {inp_id: val for inp_id, val in zip(input_ids, values)}

            # Check if any upstream input is ExecutionCancelled sentinel
            # If so, skip execution and propagate cancellation downstream
            cancelled_inputs = [val for val in values if isinstance(val, ExecutionCancelled)]
            if cancelled_inputs:
                reason = cancelled_inputs[0].reason  # Use first cancellation reason
                logger.info(f"Skipping module {step.module_instance_id} due to upstream cancellation: {reason}")

                # Create ExecutionCancelled sentinel for all outputs
                sentinel = ExecutionCancelled(reason)
                outputs_dict = {pin.node_id: sentinel for pin in ctx.outputs}

                # DO NOT record step result - module didn't execute, shouldn't appear in steps array
                # This ensures not_executed modules are truly absent from execution results

                return outputs_dict  # Return sentinel values for downstream propagation

            # Check if any upstream input is BranchNotTaken sentinel
            # If so, skip execution and propagate branch skip downstream
            branch_not_taken = [val for val in values if isinstance(val, BranchNotTaken)]
            if branch_not_taken:
                reason = branch_not_taken[0].reason  # Use first branch reason
                logger.info(f"Skipping module {step.module_instance_id} - branch not selected: {reason}")

                # Create BranchNotTaken sentinel for all outputs
                sentinel = BranchNotTaken(reason)
                outputs_dict = {pin.node_id: sentinel for pin in ctx.outputs}

                # DO NOT record step result - module didn't execute, shouldn't appear in steps array
                # Branch not taken modules don't appear in execution results

                return outputs_dict  # Return sentinel values for downstream propagation

            if is_action:
                # Convert inputs to upstream pin names for better UX
                upstream_named_inputs = _convert_to_upstream_named_inputs(
                    inputs_dict,
                    step.input_field_mappings,
                    all_nodes_metadata,
                    entry_points_lookup
                )

                # Get module title from handler for display
                module_title = getattr(handler, 'title', module_id)

                if execute_actions:
                    # ============ PRODUCTION MODE: Execute action ============
                    try:
                        # Create validated config instance
                        config_instance = ConfigModel(**step.module_config)

                        # Execute action handler (SIDE EFFECTS OCCUR HERE)
                        outputs_dict = handlerInstance.run(
                            inputs=inputs_dict,  # Use raw node_id keyed inputs
                            cfg=config_instance,
                            context=ctx
                        )
                        error = None

                        logger.info(f"Executed action {step.module_instance_id}: {module_title}")

                        # Collect for audit trail with execution flag
                        action_collector.add(ActionExecutionData(
                            module_instance_id=step.module_instance_id,
                            module_title=module_title,
                            action_module_id=module_id,
                            inputs=upstream_named_inputs,
                            config=step.module_config,
                            executed=True,
                            outputs=outputs_dict,
                            error=None
                        ))

                    except Exception as e:
                        outputs_dict = {}
                        error = f"{type(e).__name__}: {e}"
                        logger.exception(f"Action {step.module_instance_id} failed: {e}")

                        # Collect failure for audit
                        action_collector.add(ActionExecutionData(
                            module_instance_id=step.module_instance_id,
                            module_title=module_title,
                            action_module_id=module_id,
                            inputs=upstream_named_inputs,
                            config=step.module_config,
                            executed=True,
                            outputs=None,
                            error=error
                        ))
                else:
                    # ============ SIMULATION MODE: Just collect data ============
                    action_collector.add(ActionExecutionData(
                        module_instance_id=step.module_instance_id,
                        module_title=module_title,
                        action_module_id=module_id,
                        inputs=upstream_named_inputs,
                        config=step.module_config,
                        executed=False,  # Flag: simulation only
                        outputs=None,
                        error=None
                    ))

                    # Generate mock outputs so downstream modules can execute
                    outputs_dict = self._generate_mock_outputs(ctx.outputs)
                    error = None

                    logger.debug(f"Collected action data for {step.module_instance_id} (simulation) with mock outputs")

                    # Actions in simulation mode don't create step results (they didn't execute)
                    # Return mock outputs for downstream dependencies but don't audit
                    return outputs_dict

            else:
                # Transform/Logic module: Execute normally
                try:
                    # Create validated config instance (module expects Pydantic model, not dict)
                    config_instance = ConfigModel(**step.module_config)
                    outputs_dict = handlerInstance.run(
                        inputs=inputs_dict,
                        cfg=config_instance,
                        context=ctx
                    )
                    error = None
                    logger.debug(f"Executed {module_kind} module {step.module_instance_id}")
                except Exception as e:
                    outputs_dict = {}
                    error = f"{type(e).__name__}: {e}"
                    logger.exception(f"Module {step.module_instance_id} failed: {e}")

            # Serialize for audit trail (only for transform/logic and executed actions)
            # For inputs: look up upstream pin names for better UX
            audit_inputs = _serialize_inputs_for_audit(
                inputs_dict,
                ctx.inputs,
                step.input_field_mappings,
                all_nodes_metadata,
                entry_points_lookup
            )
            # For outputs: use the output pin names from this module
            audit_outputs = _serialize_io_for_audit(outputs_dict, ctx.outputs) if outputs_dict else {}

            # Collect step result (only for modules that actually executed)
            step_result = PipelineExecutionStepResult(
                module_instance_id=step.module_instance_id,
                step_number=step.step_number,
                inputs=audit_inputs,
                outputs=audit_outputs,
                error=error
            )
            collector.add(step_result)
            logger.info(f"Collected step result for {step.module_instance_id}: error={error}")

            # Branch-isolated error handling: Don't raise, let other branches continue
            # Return ExecutionCancelled sentinels if module failed to prevent downstream execution
            if error:
                logger.error(f"Module {step.module_instance_id} failed: {error}, cancelling downstream execution")
                # Create ExecutionCancelled sentinel for all outputs
                sentinel = ExecutionCancelled(f"Module {step.module_instance_id} failed: {error}")
                return {pin.node_id: sentinel for pin in ctx.outputs}

            return outputs_dict

        task = _run_module(*upstream_tasks)
        return task

    def _publish_outputs_for_downstream(
        self,
        step: PipelineDefinitionStep,
        task: Any,
        producer_of_pin: Dict[str, Any],
    ) -> None:
        """
        Split module outputs into per-pin delayed futures.

        After creating a task for a module, expose each output pin as its own
        delayed node in the graph so downstream inputs can depend on specific pins.

        task produces: {output_pin_id -> value}
        We create: delayed futures for each output pin individually

        Args:
            step: Pipeline step
            task: Delayed task that produces outputs
            producer_of_pin: Map to update with new producers
        """
        output_pins: List[NodeInstance] = step.node_metadata.get("outputs") or []

        for pin in output_pins:
            node_id = pin.node_id

            @delayed(pure=True)  # type: ignore
            def _select(outputs: Dict[str, Any], key: str):
                """Select a specific output from the module's output dict"""
                return outputs.get(key)

            producer_of_pin[node_id] = _select(task, node_id)

        logger.debug(f"Published {len(output_pins)} outputs for {step.module_instance_id}")
