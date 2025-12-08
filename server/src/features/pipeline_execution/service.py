"""
Pipeline Execution Service
Builds a Dask task graph from compiled steps and executes with auditing.

Executes pipelines as pure data transformation graphs. Output modules collect
their inputs but do not execute side effects - that responsibility is delegated
to the OutputExecutionService via the ETO orchestrator.

Usage:
    service = PipelineExecutionService(cm, services)
    result = service.execute_pipeline(
        steps=compiled_steps,
        entry_values_by_name={"origin": "SFO", "destination": "LAX"},
        pipeline_state=pipeline_state
    )

    # Result contains output_module_id and output_module_inputs
    # Orchestrator passes these to OutputExecutionService
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
    ModuleRepository,
)
from features.modules.utils.registry import ModuleRegistry
from shared.types.pipeline_definition import PipelineDefinition
from shared.types.pipeline_definition_step import PipelineDefinitionStep
from shared.types.pipelines import NodeInstance
from shared.types.pipeline_execution import (
    PipelineExecutionStepResult,
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
            # Skip sentinel values (ExecutionCancelled, BranchNotTaken)
            # These are internal control flow markers and should not be serialized
            if isinstance(raw_value, (ExecutionCancelled, BranchNotTaken)):
                continue
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

            # Skip sentinel values (ExecutionCancelled, BranchNotTaken)
            # These are internal control flow markers and should not be serialized
            if isinstance(raw_value, (ExecutionCancelled, BranchNotTaken)):
                continue

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


class PipelineExecutionService:
    """
    Executes compiled pipelines using Dask task graphs.

    Orchestrates pure data transformation with:
    - Entry point validation
    - Lazy task graph construction in topological order
    - Audit trail persistence
    - Branch-isolated error handling (independent DAG branches continue on error)
    - Output module data collection (returned to orchestrator for execution)

    Output modules are terminal nodes that collect their inputs but do not execute
    side effects. The orchestrator passes output module data to OutputExecutionService.
    """

    connection_manager: DatabaseConnectionManager
    pipeline_repo: PipelineDefinitionRepository
    step_repo: PipelineDefinitionStepRepository
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
        self.module_catalog_repo = ModuleRepository(connection_manager=connection_manager)

        logger.info("PipelineExecutionService initialized")

    # ==================== Public API ====================

    def execute_pipeline(
        self,
        steps: List[PipelineDefinitionStep],
        entry_values_by_name: Dict[str, Any],
        pipeline_state,  # PipelineState from pipelines module
    ) -> PipelineExecutionResult:
        """
        Execute a compiled pipeline as pure data transformation.

        All modules (transform, logic, misc, output) execute in topological order.
        Output modules collect their inputs but do not execute side effects.
        The orchestrator is responsible for executing outputs via OutputExecutionService.

        Policy:
          - Fail fast on missing required entry names
          - Extra entry names are ignored (logged)
          - All modules execute in topological order (no special scheduling)
          - Output modules return empty outputs (they're terminal nodes)
          - Independent DAG branches continue execution even if one branch fails
          - Status is "success" (no errors), "partial" (some errors), or "failed" (all errors)

        Args:
            steps: Compiled pipeline steps to execute
            entry_values_by_name: Entry point values keyed by entry point name
            pipeline_state: Pipeline state containing entry points for mapping

        Returns:
            PipelineExecutionResult with:
            - steps: Execution audit trail
            - output_module_id: Which output module to execute (None if no output module)
            - output_module_inputs: Input data for output module {name: value}
            - error: Error message if pipeline failed

        Raises:
            ValueError: Missing required entry values
            RuntimeError: Module not found
        """
        logger.info(f"Starting pipeline execution with {len(steps)} steps")

        # Step 1: Map entry points
        entry_name_to_ids = self._map_entry_names_to_pin_ids_from_state(pipeline_state)

        # Debug: Log entry point mapping for diagnosis
        logger.debug(f"Pipeline entry points (name -> pin_ids): {entry_name_to_ids}")
        logger.debug(f"Provided entry values (from extraction): {list(entry_values_by_name.keys())}")

        # Step 2: Seed entry values
        producer_of_pin, missing, extras = self._seed_entry_values(
            entry_values_by_name, entry_name_to_ids
        )

        if missing:
            msg = f"Missing required entry values: {', '.join(missing)}"
            logger.error(f"Entry point name mismatch - Pipeline expects: {list(entry_name_to_ids.keys())}, "
                        f"Extraction provided: {list(entry_values_by_name.keys())}")
            logger.error(msg)
            raise ValueError(msg)

        if extras:
            logger.warning(f"Ignoring extra entry values: {', '.join(extras)}")

        # Step 3: Build collector
        collector = StepResultCollector()

        # Step 4: Build global node metadata lookup for input name resolution
        all_nodes_metadata: Dict[str, List[NodeInstance]] = {}
        for step in steps:
            if step.node_metadata:
                for key, nodes in step.node_metadata.items():
                    if key not in all_nodes_metadata:
                        all_nodes_metadata[key] = []
                    all_nodes_metadata[key].extend(nodes)

        # Step 5: Build entry points lookup {node_id -> name}
        entry_points_lookup: Dict[str, str] = {
            ep.outputs[0].node_id: ep.name
            for ep in pipeline_state.entry_points
            if ep.outputs
        }

        # Step 6: Build Dask graph (all modules in topological order)
        task_of_step: Dict[str, Any] = {}
        output_channel_values: Dict[str, Any] = {}  # Collected output channel values

        for step in steps:
            # Check if this is an output channel step (module_ref is None)
            if step.module_ref is None:
                # Output channel step - create collection task
                task = self._make_output_channel_collection_task(
                    step, producer_of_pin, output_channel_values
                )
                task_of_step[step.module_instance_id] = task
                # No downstream publishing - output channels are terminal nodes
                channel_type = step.module_config.get("channel_type", "unknown")
                logger.debug(f"Created output channel collection task: {step.module_instance_id} (channel_type={channel_type})")
            else:
                # Regular module step
                module_id = step.module_ref.split(":")[0] if ":" in step.module_ref else step.module_ref

                # Create task for this step
                task = self._make_step_task(step, producer_of_pin, collector, all_nodes_metadata, entry_points_lookup)
                task_of_step[step.module_instance_id] = task
                self._publish_outputs_for_downstream(step, task, producer_of_pin)

        # Step 7: Execute graph
        try:
            leaves = [t for t in task_of_step.values()] or list(producer_of_pin.values())
            if leaves:
                logger.info(f"Executing Dask graph with {len(leaves)} leaf tasks")
                compute(*leaves)

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

        # Step 9: Log collected output channel values
        if output_channel_values:
            logger.info(f"Output channel values collected: {list(output_channel_values.keys())}")
            for channel_type, value in output_channel_values.items():
                logger.debug(f"  {channel_type}: {value}")
        else:
            logger.debug("No output channel values collected")

        return PipelineExecutionResult(
            status=status,
            steps=collected_steps,
            output_channel_values=output_channel_values,
            error=error
        )

    # ==================== Helper Methods ====================

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

        logger.debug(f"Loaded pipeline {pipeline_definition_id}")

        return pipeline

    def _require_compiled_steps(self, pipeline_definition_id: int) -> List[PipelineDefinitionStep]:
        """
        Load compiled steps ordered by step_number.

        Args:
            pipeline_definition_id: Pipeline definition ID

        Returns:
            List of steps in execution order

        Raises:
            ValueError: If no steps found
        """
        steps = self.step_repo.get_steps_by_definition_id(pipeline_definition_id)

        if not steps:
            raise ValueError(f"No compiled steps found for pipeline {pipeline_definition_id}")

        logger.debug(f"Loaded {len(steps)} compiled steps for pipeline {pipeline_definition_id}")

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
        all_nodes_metadata: Dict[str, List[NodeInstance]],
        entry_points_lookup: Dict[str, str],
    ) -> Any:
        """
        Create delayed task for a module execution.

        All modules (transform, logic, misc, output) execute the same way.
        Output modules return empty dict (they're terminal nodes).

        Args:
            step: Pipeline step to execute
            producer_of_pin: Map of pin_id -> delayed value
            collector: Collector for step results
            all_nodes_metadata: All node metadata for pin name lookups
            entry_points_lookup: Entry point node_id -> name mapping

        Returns:
            Delayed task that produces {output_pin_id: value}
        """
        # Resolve handler
        module_id = step.module_ref.split(":")[0] if ":" in step.module_ref else step.module_ref

        handler = self.module_registry.get(module_id)
        if not handler:
            raise RuntimeError(f"Module handler not found for {step.module_ref}")

        ConfigModel = handler.config_class()
        handlerInstance = handler()

        # Build execution context
        inputs_metadata = step.node_metadata.get("inputs") or []
        outputs_metadata = step.node_metadata.get("outputs") or []

        from shared.types.pipelines import ModuleExecutionContext
        ctx = ModuleExecutionContext(
            inputs=inputs_metadata,
            outputs=outputs_metadata,
            module_instance_id=step.module_instance_id,
        )

        # Gather upstream producers
        input_ids = list(step.input_field_mappings.keys())
        upstream_ids = [step.input_field_mappings[iid] for iid in input_ids]

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

        @delayed(pure=False)  # type: ignore
        def _run_module(*resolved):
            """
            Execute module.

            resolved contains input values in order.
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
                return outputs_dict  # Return sentinel values for downstream propagation

            # Check if any upstream input is BranchNotTaken sentinel
            # If so, skip execution and propagate branch skip downstream
            branch_not_taken = [val for val in values if isinstance(val, BranchNotTaken)]
            if branch_not_taken:
                reason = branch_not_taken[0].reason  # Use first branch reason
                logger.info(f"Skipping module {step.module_instance_id} due to branch not taken: {reason}")

                # Create BranchNotTaken sentinel for all outputs
                sentinel = BranchNotTaken(reason)
                outputs_dict = {pin.node_id: sentinel for pin in ctx.outputs}

                # DO NOT record step result - module didn't execute, shouldn't appear in steps array
                return outputs_dict  # Return sentinel values for downstream propagation

            # Execute module (all modules execute the same way)
            try:
                # Create validated config instance
                config_instance = ConfigModel(**step.module_config)
                outputs_dict = handlerInstance.run(
                    inputs=inputs_dict,
                    cfg=config_instance,
                    context=ctx,
                    services=self.services
                )
                error = None
                logger.debug(f"Executed module {step.module_instance_id}")
            except Exception as e:
                outputs_dict = {}
                error = f"{type(e).__name__}: {e}"
                logger.exception(f"Module {step.module_instance_id} failed: {e}")

            # Serialize for audit trail
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

            # Collect step result
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

    def _make_output_channel_collection_task(
        self,
        step: PipelineDefinitionStep,
        producer_of_pin: Dict[str, Any],
        output_channel_values: Dict[str, Any],
    ) -> Any:
        """
        Create a Dask task that collects the input value for an output channel.

        Output channels are terminal nodes in the DAG - they consume values but
        produce nothing. The collected value is stored in output_channel_values dict.

        Args:
            step: Output channel step (module_ref is None)
            producer_of_pin: Map of pin_id -> delayed value
            output_channel_values: Dict to store collected values (mutated by task)

        Returns:
            Delayed task that collects the input value
        """
        channel_type = step.module_config.get("channel_type", "unknown")

        # Get the upstream producer for the input pin
        # Output channels have exactly one input
        if not step.input_field_mappings:
            logger.warning(f"Output channel {step.module_instance_id} has no input mappings")
            return delayed(lambda: None)()

        input_pin_id = list(step.input_field_mappings.keys())[0]
        upstream_pin_id = step.input_field_mappings[input_pin_id]

        if upstream_pin_id not in producer_of_pin:
            logger.error(
                f"Output channel {step.module_instance_id} references missing upstream pin {upstream_pin_id}"
            )
            return delayed(lambda: None)()

        upstream_task = producer_of_pin[upstream_pin_id]

        @delayed(pure=False)  # type: ignore
        def _collect_output_channel(value, ch_type: str):
            """
            Collect the value flowing into this output channel.

            Args:
                value: The value from upstream
                ch_type: The channel type (e.g., "hawb", "pickup_address")
            """
            # Skip sentinel values (ExecutionCancelled, BranchNotTaken)
            if isinstance(value, (ExecutionCancelled, BranchNotTaken)):
                logger.debug(f"Output channel {ch_type} received sentinel value, skipping collection")
                return None

            # Store the collected value
            output_channel_values[ch_type] = value
            logger.info(f"Collected output channel '{ch_type}': {value}")
            return value

        return _collect_output_channel(upstream_task, channel_type)
