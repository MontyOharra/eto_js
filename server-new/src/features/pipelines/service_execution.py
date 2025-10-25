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
from datetime import datetime
from dask.delayed import delayed
from dask.base import compute

from shared.database import DatabaseConnectionManager
from shared.database.repositories import (
    PipelineDefinitionRepository,
    PipelineDefinitionStepRepository,
    EtoRunPipelineExecutionRepository,
    EtoRunPipelineExecutionStepRepository,
    ModuleCatalogRepository,
)
from shared.utils.registry import ModuleRegistry
from shared.types.pipeline_definition import PipelineDefinitionFull
from shared.types.pipeline_definition_step import PipelineDefinitionStepFull
from shared.types.pipelines import NodeInstance
from shared.types.pipeline_execution import (
    PipelineExecutionRun,
    PipelineExecutionRunCreate,
    PipelineExecutionStepCreate,
)
from shared.database.models import EtoStepStatus

logger = logging.getLogger(__name__)


class PipelineExecutionService:
    """
    Executes compiled pipelines using Dask task graphs.

    Orchestrates pipeline execution with:
    - Entry point validation
    - Lazy task graph construction
    - Transform/Logic → Action ordering (action barrier)
    - Audit trail persistence
    - Fail-fast error handling
    """

    connection_manager: DatabaseConnectionManager
    pipeline_repo: PipelineDefinitionRepository
    step_repo: PipelineDefinitionStepRepository
    run_repo: EtoRunPipelineExecutionRepository
    exec_step_repo: EtoRunPipelineExecutionStepRepository
    module_catalog_repo: ModuleCatalogRepository
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
        self.module_catalog_repo = ModuleCatalogRepository(connection_manager=connection_manager)

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
        logger.info(
            f"Starting pipeline execution for definition {pipeline_definition_id}, "
            f"ETO run {eto_run_id}"
        )

        # Step 1: Load pipeline and verify it's compiled
        pipeline = self._require_pipeline(pipeline_definition_id)
        steps = self._require_compiled_steps(pipeline.compiled_plan_id)

        # Step 2: Create execution run record (status: PROCESSING)
        run = self.run_repo.create(
            PipelineExecutionRunCreate(
                eto_run_id=eto_run_id,
                status=EtoStepStatus.PROCESSING,
                started_at=datetime.utcnow(),
            )
        )

        logger.info(f"Created execution run {run.id}")

        # Step 3: Build entry point mapping
        entry_name_to_ids = self._map_entry_names_to_pin_ids(pipeline)

        # TODO: Steps 5-11 (seed entry values, build graph, execute, update status)
        logger.warning("Execution not yet fully implemented - returning processing run")

        return run

    # ==================== Helper Methods (to be implemented) ====================

    def _require_pipeline(self, pipeline_definition_id: int) -> PipelineDefinitionFull:
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

    def _require_compiled_steps(self, compiled_plan_id: int) -> List[PipelineDefinitionStepFull]:
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
        pipeline: PipelineDefinitionFull
    ) -> Dict[str, List[str]]:
        """
        Build {entry_name -> [pin_id, ...]} from pipeline_state.entry_points.

        Entry points can feed multiple downstream pins.

        Args:
            pipeline: Pipeline definition

        Returns:
            Mapping of entry point names to pin IDs
        """
        entry_name_to_ids: Dict[str, List[str]] = {}

        for entry_point in pipeline.pipeline_state.entry_points:
            if entry_point.name not in entry_name_to_ids:
                entry_name_to_ids[entry_point.name] = []
            entry_name_to_ids[entry_point.name].append(entry_point.node_id)

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
        # TODO: Step 5
        raise NotImplementedError()

    def _make_step_task(
        self,
        step: PipelineDefinitionStepFull,
        producer_of_pin: Dict[str, Any],
        run_id: int,
        extra_dependencies: Optional[List[Any]] = None,
    ) -> Any:
        """
        Create delayed task for a module execution.

        Args:
            step: Pipeline step to execute
            producer_of_pin: Map of pin_id -> delayed value
            run_id: Execution run ID for audit trail
            extra_dependencies: Additional delayed dependencies (e.g., action barrier)

        Returns:
            Delayed task that produces {output_pin_id: value}
        """
        # TODO: Step 6
        raise NotImplementedError()

    def _publish_outputs_for_downstream(
        self,
        step: PipelineDefinitionStepFull,
        task: Any,
        producer_of_pin: Dict[str, Any],
    ) -> None:
        """
        Split module outputs into per-pin delayed futures.

        task produces: {output_pin_id -> value}
        We create: delayed futures for each output pin individually

        Args:
            step: Pipeline step
            task: Delayed task that produces outputs
            producer_of_pin: Map to update with new producers
        """
        # TODO: Step 7
        raise NotImplementedError()
