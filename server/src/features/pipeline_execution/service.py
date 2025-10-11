"""
Pipeline Execution Service
Builds a Dask task graph from compiled steps and executes with auditing.

Usage:
    service = PipelineExecutionService(cm, module_registry)
    run = service.execute_pipeline(pipeline_id="pipeline_123", entry_values={"origin":"..", "airport":".."})
"""

from __future__ import annotations
from typing import Dict, Any, List, Tuple, Optional

import json
import logging
from datetime import datetime, date
from dask.delayed import delayed
from dask.base import compute

from shared.database.repositories import PipelineDefinitionRepository, PipelineDefinitionStepRepository, PipelineExecutionRunRepository, PipelineExecutionStepRepository
from shared.utils.registry import ModuleRegistry

from shared.types import (
    PipelineDefinition,
    PipelineDefinitionStep,
    PipelineExecutionRun,
    PipelineExecutionRunCreate,
    PipelineExecutionStepCreate,
    ModuleExecutionContext,
    InstanceNodePin
)

logger = logging.getLogger(__name__)


# === Serialization Utilities for Audit Trail ===

def _serialize_value(value: Any, type_hint: str) -> Any:
    """Serialize a value to JSON-compatible format for audit storage"""
    if type_hint == "datetime":
        if isinstance(value, (datetime, date)):
            return value.isoformat()
    return value


def _serialize_io_for_audit(io_dict: Dict[str, Any], pins: List[InstanceNodePin]) -> Dict[str, Dict[str, Any]]:
    """
    Transform {node_id: value} to {node_name: {value, type}} for audit persistence

    Args:
        io_dict: Raw I/O from module execution {node_id: value}
        pins: Pin metadata with node_id, name, and type

    Returns:
        {node_name: {value: serialized_value, type: type_hint}}
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


class PipelineExecutionService:
    def __init__(self, connection_manager, services=None):
        """
        Dependencies:
          - connection_manager: provides session_scope()
          - services: ServiceContainer for accessing other services (optional, will be set if not provided)
        """
        if not connection_manager:
            raise RuntimeError("Database connection manager is required")

        self.connection_manager = connection_manager
        self.module_registry = ModuleRegistry()
        self.services = services  # Store services reference

        # Repos
        self.pipeline_repo = PipelineDefinitionRepository(self.connection_manager)
        self.step_repo = PipelineDefinitionStepRepository(self.connection_manager)
        self.run_repo = PipelineExecutionRunRepository(self.connection_manager)
        self.exec_step_repo = PipelineExecutionStepRepository(self.connection_manager)

        logger.info("PipelineExecutionService initialized")

    # ------------------------- Public API ------------------------------------

    def execute_pipeline(
        self,
        pipeline_definition_id: int,
        entry_values_by_name: Dict[str, Any],
    ) -> PipelineExecutionRun:
        """
        Execute a compiled pipeline with the provided entry values (keyed by entry *names*).

        Policy:
          - Fail fast on missing required entry names.
          - Extra entry names are ignored (logged).
          - All Action modules run only after all Transform/Logic modules succeed.
          - On any module error, the whole run is marked failed and no further tasks are executed.

        Returns:
          PipelineExecutionRun (final status + stored entry payload)
        """
        # 1) Load pipeline and compiled steps
        pipeline = self._require_pipeline(pipeline_definition_id)
        steps = self._require_compiled_steps(pipeline)
        
        run = self.run_repo.create(
            PipelineExecutionRunCreate(
                pipeline_definition_id=pipeline.id,
                entry_values=entry_values_by_name,
            )
        )

        # 2) Build entry name -> pin id map from the pipeline's entry_points (lean, no giant JSON scan)
        entry_name_to_ids = self._map_entry_names_to_pin_ids(pipeline)

        # 3) Validate & seed entry values (pin producers)
        producer_of_pin, missing, extras = self._seed_entry_values(entry_values_by_name, entry_name_to_ids)
        if missing:
            msg = f"Missing required entry names: {', '.join(missing)}"
            run = self.run_repo.update_run_status(pipeline_definition_id, status="failed")
            logger.error(msg)
            raise ValueError(msg)

        if extras:
            logger.warning("Ignoring extra entry names not used by this pipeline: %s", ", ".join(extras))

        run_id = run.id

        # 5) Build Dask graph
        task_of_step: Dict[str, Any] = {}
        non_action_tasks: List[Any] = []
        action_steps: List[PipelineDefinitionStep] = []

        for step in steps:
            if step.module_kind == 'action':  # defer actions to the end
                action_steps.append(step)
                continue

            task = self._make_step_task(step, producer_of_pin, run_id)
            task_of_step[step.module_instance_id] = task
            # expose this step's outputs as producers for downstream inputs
            self._publish_outputs_for_downstream(step, task, producer_of_pin)
            non_action_tasks.append(task)

        # Barrier: actions depend on all non-actions AND their own upstreams
        barrier = delayed(lambda *args: True, pure=True)(*non_action_tasks) if non_action_tasks else delayed(lambda: True, pure=True)()

        for step in action_steps:
            task = self._make_step_task(step, producer_of_pin, run_id, extra_dependencies=[barrier])
            task_of_step[step.module_instance_id] = task
            self._publish_outputs_for_downstream(step, task, producer_of_pin)

        # 6) Execute (compute all leaves; actions are included)
        try:
            leaves = [t for t in task_of_step.values()] or list(producer_of_pin.values())
            if leaves:
                compute(*leaves)  # raises on first failure
            if run:
                self.run_repo.update_run_status(run_id, "success")
        except Exception as e:
            logger.exception("Pipeline execution failed: %s", e)
            if run:
                self.run_repo.update_run_status(run_id, "failed")
            # Let caller see the error (API can surface details)
            raise

        # 7) Return final run (or a lightweight result if history is disabled)
        if run:
            # fetch fresh in case repo returns updated object
            run_fresh = self.run_repo.get_run_by_id(run.id)
            return run_fresh or run
        else:
            # Build a synthetic result when not persisting
            return PipelineExecutionRun(
                id=-1,
                pipeline_definition_id=pipeline_definition_id,
                status="success",
                entry_values=entry_values_by_name,
            )

    # ------------------------- Internals -------------------------------------

    def _require_pipeline(self, pipeline_definition_id: int) -> PipelineDefinition:
        pipeline = self.pipeline_repo.get_by_id(pipeline_definition_id)
        if not pipeline:
            from shared.exceptions import ObjectNotFoundError
            raise ObjectNotFoundError("Pipeline", pipeline_definition_id)
        if not pipeline.plan_checksum:
            raise RuntimeError(f"Pipeline {pipeline_definition_id} has not been compiled")
        return pipeline  # :contentReference[oaicite:8]{index=8}

    def _require_compiled_steps(self, pipeline: PipelineDefinition) -> List[PipelineDefinitionStep]:
        assert pipeline.plan_checksum is not None
        steps = self.step_repo.get_steps_by_checksum(pipeline.plan_checksum)  # ordered by step_number
        if not steps:
            from shared.exceptions import RepositoryError
            raise RepositoryError(f"No compiled steps found for checksum={pipeline.plan_checksum}")
        return steps  # :contentReference[oaicite:9]{index=9}

    def _map_entry_names_to_pin_ids(self, pipeline: PipelineDefinition) -> Dict[str, List[str]]:
        """Build {entry_name -> [entry_pin_id, ...]} from pipeline_state.entry_points."""
        mapping: Dict[str, List[str]] = {}
        for ep in pipeline.pipeline_state.entry_points:
            mapping.setdefault(ep.name, []).append(ep.node_id)
        return mapping  # :contentReference[oaicite:10]{index=10}

    def _seed_entry_values(
        self,
        entry_values_by_name: Dict[str, Any],
        entry_name_to_ids: Dict[str, List[str]],
    ) -> Tuple[Dict[str, Any], List[str], List[str]]:
        """
        Returns:
          producer_of_pin: {pin_id -> delayed(value)}
          missing_names: names required by the plan but absent from payload
          extra_names: names provided but unused in this plan
        """
        expected = set(entry_name_to_ids.keys())
        provided = set(entry_values_by_name.keys())
        missing = sorted(expected - provided)
        extras = sorted(provided - expected)

        @delayed(pure=True)
        def _const(v):  # tiny wrapper so everything in the graph is delayed
            return v

        producer_of_pin: Dict[str, Any] = {}
        for name, node_ids in entry_name_to_ids.items():
            if name in entry_values_by_name:
                v = entry_values_by_name[name]
                for pin_id in node_ids:
                    producer_of_pin[pin_id] = _const(v)
        return producer_of_pin, missing, extras

    def _make_step_task(
        self,
        step: PipelineDefinitionStep,
        producer_of_pin: Dict[str, Any],
        run_id: Optional[int],
        extra_dependencies: Optional[List[Any]] = None,
    ):
        """
        Build a delayed task that:
          - waits for all upstream input producers
          - calls the module handler.run(...)
          - persists an execution step row (inputs/outputs or error)
          - returns a dict {output_pin_id: value, ...}
        """

        # Resolve handler
        # module_ref format is "module_id:version", but registry stores by module_id only
        module_id = step.module_ref.split(":")[0] if ":" in step.module_ref else step.module_ref
        handler = self.module_registry.get(module_id)
        if not handler:
            raise RuntimeError(f"Module handler not found for {step.module_ref}")

        ConfigModel = handler.config_class()
        handlerInstance = handler()

        # Gather upstream producers for each input pin id
        input_ids = list(step.input_field_mappings.keys())
        upstream_ids = [step.input_field_mappings[iid] for iid in input_ids]

        # Convert InstanceNodePin to plain dict for stable JSON context
        inputs = step.node_metadata.get("inputs") or []
        outputs = step.node_metadata.get("outputs") or []
        
        ctx = ModuleExecutionContext(
            module_instance_id=step.module_instance_id,
            inputs=inputs,
            outputs=outputs,
            services=self.services,
        )

        # Collect the upstream delayed values in order of input_ids
        upstream_tasks = [producer_of_pin[uid] for uid in upstream_ids]

        if extra_dependencies:
            upstream_tasks = upstream_tasks + list(extra_dependencies)

        @delayed(pure=False)
        def _run_module(*resolved):
            """
            resolved packs:
              - first len(input_ids) items: resolved input values in the same order
              - then optional barrier tokens (ignored)
            """
            # 1) Build {input_pin_id: value}
            values = resolved[: len(input_ids)]
            inputs = {inp_id: val for inp_id, val in zip(input_ids, values)}

            # 2) Run handler
            try:
                outputs = handlerInstance.run(inputs=inputs, cfg=ConfigModel(**step.module_config), context=ctx)
                error = None
            except Exception as e:
                outputs = {}
                error = f"{type(e).__name__}: {e}"
                logger.exception("Module %s failed: %s", step.module_instance_id, e)

            # 3) Persist audit row
            if run_id is not None:
                try:
                    # Serialize I/O for audit trail: {node_id: value} -> {node_name: {value, type}}
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
                    # Persistence must not hide the original failure
                    logger.exception("Failed to persist execution step for %s: %s", step.module_instance_id, pe)

            # 4) On error, raise to stop the whole run
            if error:
                raise RuntimeError(error)

            # 5) Return outputs to downstream
            return outputs

        task = _run_module(*upstream_tasks)
        return task

    def _publish_outputs_for_downstream(self, step: PipelineDefinitionStep, task, producer_of_pin: Dict[str, Any]) -> None:
        """
        After creating a task for a module, expose each output pin as its own delayed node in the graph:

        task produces Dict[output_pin_id -> value]
        we split that dict into individual delayed futures so downstream inputs can depend on the specific pin.
        """

        output_pins: List[InstanceNodePin] = step.node_metadata.get("outputs") or []

        for pin in output_pins:
            node_id = pin.node_id

            @delayed(pure=True)
            def _select(outputs: Dict[str, Any], key: str):
                return outputs.get(key)

            producer_of_pin[node_id] = _select(task, node_id)
