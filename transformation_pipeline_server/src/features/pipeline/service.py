"""
Pipeline Service
Service for pipeline save and load operations following ETO server patterns
"""

import logging
from datetime import datetime

from typing import Optional, List, Dict, Any
from shared.types import (
    PipelineDefinition,
    PipelineDefinitionCreate,
    PipelineDefinitionSummary,
    PipelineState,
    PipelineValidationResult
)

from shared.database.repositories import (
    ModuleCatalogRepository,
    PipelineDefinitionStepRepository,
    PipelineDefinitionRepository,
    PipelineExecutionRunRepository,
    PipelineExecutionStepRepository,
)
from shared.exceptions import RepositoryError, ObjectNotFoundError, PipelineValidationError

from .utils.validation_orchestrator import PipelineValidator
from .utils.compilation import (
    GraphPruner,
    TopologicalSorter,
    ChecksumCalculator,
    PipelineCompiler,
)

from .execution.executor import PipelineExecutor

logger = logging.getLogger(__name__)


class PipelineService:
    """Service for pipeline save and load operations"""

    def __init__(self, connection_manager):
        """
        Initialize service with database connection

        Args:
            connection_manager: Database connection manager
        """
        if not connection_manager:
            raise RuntimeError("Database connection manager is required")

        self.connection_manager = connection_manager

        self.pipeline_repo: PipelineDefinitionRepository = PipelineDefinitionRepository(
            self.connection_manager
        )
        self.step_repo: PipelineDefinitionStepRepository = PipelineDefinitionStepRepository(
            self.connection_manager
        )
        self.module_catalog_repo: ModuleCatalogRepository = ModuleCatalogRepository(
            self.connection_manager
        )

        logger.info("Pipeline Service initialized")

    # === Core Operations (Save/Load) ===

    def create_pipeline(self, pipeline_create: PipelineDefinitionCreate) -> PipelineDefinition:
        """
        Create and compile a new pipeline with checksum-based caching

        Flow:
            1. Validate pipeline → get reachable_modules
            2. Prune graph → pruned_pipeline
            3. Calculate checksum
            4. Check if checksum exists in DB
            5a. IF EXISTS (cache hit):
                - Create pipeline record with checksum
            5b. IF NOT EXISTS (cache miss):
                - Compile steps from pruned pipeline
                - Create pipeline record
                - Save pipeline steps
            6. Return Pipeline domain object

        Args:
            pipeline_create: PipelineDefinitionCreate model with pipeline data

        Returns:
            Created Pipeline domain object (includes plan_checksum and compiled_at)

        Raises:
            ValidationError: If pipeline validation fails
            RepositoryError: If save operation fails
        """
        try:
            logger.info(f"Creating pipeline: {pipeline_create.name}")

            pipeline_state = pipeline_create.pipeline_state

            try:
                validation_result = self.validate_pipeline(pipeline_state)
            except ValueError as e:
                raise e

            reachable_modules = validation_result.reachable_modules

            logger.debug(
                f"Validation passed. {len(reachable_modules)} reachable modules"
            )

            # Step 2: Prune Graph
            pruned_pipeline = GraphPruner.prune(pipeline_state, reachable_modules)
            modules_pruned = len(pipeline_state.modules) - len(pruned_pipeline.modules)
            if modules_pruned > 0:
                logger.debug(f"Pruned {modules_pruned} dead branch module(s)")

            # Step 3: Calculate Checksum
            checksum = ChecksumCalculator.compute(pruned_pipeline)
            logger.debug(f"Computed checksum: {checksum[:12]}...")

            # Step 4: Check Cache
            cache_hit = self.step_repo.checksum_exists(checksum)

            compiled_at = datetime.now()

            # Prepare pipeline data with checksum
            pipeline_data = pipeline_create.model_dump_for_db()
            pipeline_data["plan_checksum"] = checksum
            pipeline_data["compiled_at"] = compiled_at

            if cache_hit:
                # Step 5a: Cache Hit - Create Pipeline Only
                logger.info(
                    f"Cache HIT for checksum {checksum[:12]}... - reusing existing steps"
                )
                pipeline = self.pipeline_repo.create_with_checksum(pipeline_data)

            else:
                # Step 5b: Cache Miss - Compile and Create Everything
                logger.info(
                    f"Cache MISS for checksum {checksum[:12]}... - compiling new steps"
                )

                # Compile: generate List[PipelineStepCreate]
                steps = PipelineCompiler.compile(pruned_pipeline, checksum)
                logger.debug(f"Compiled {len(steps)} execution steps")

                # Create pipeline record
                pipeline = self.pipeline_repo.create_with_checksum(pipeline_data)

                # Save steps
                saved_steps = self.step_repo.save_steps(steps)
                logger.info(
                    f"Saved {len(saved_steps)} pipeline steps for checksum {checksum[:12]}..."
                )

            logger.info(
                f"Successfully created pipeline: {pipeline.id} - {pipeline.name} (cache_hit={cache_hit})"
            )
            return pipeline

        except ValueError as e:
            logger.error(
                f"Failed to create pipeline: {pipeline_create.name} - validation failed"
            )
            raise
        except RepositoryError:
            logger.error(f"Failed to create pipeline: {pipeline_create.name}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating pipeline: {e}")
            raise RepositoryError(f"Failed to create pipeline: {e}") from e

    def get_pipeline(self, pipeline_definition_id: str) -> PipelineDefinition:
        """
        Get a single pipeline by ID

        Args:
            pipeline_id: Pipeline ID to retrieve

        Returns:
            Pipeline domain model

        Raises:
            ObjectNotFoundError: If pipeline not found
            RepositoryError: If retrieval fails
        """
        try:
            logger.debug(f"Getting pipeline: {pipeline_definition_id}")

            pipeline = self.pipeline_repo.get_by_id(pipeline_definition_id)

            if not pipeline:
                logger.warning(f"Pipeline not found: {pipeline_definition_id}")
                raise ObjectNotFoundError("Pipeline", pipeline_definition_id)

            logger.debug(f"Retrieved pipeline: {pipeline.id} - {pipeline.name}")
            return pipeline

        except ObjectNotFoundError:
            raise
        except RepositoryError:
            logger.error(f"Failed to get pipeline: {pipeline_definition_id}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting pipeline {pipeline_definition_id}: {e}")
            raise RepositoryError(f"Failed to get pipeline: {e}") from e

    def list_pipelines(self, include_inactive: bool = False) -> List[PipelineDefinition]:
        """
        Get all pipelines for selection

        Args:
            include_inactive: If True, include inactive pipelines

        Returns:
            List of Pipeline domain models

        Raises:
            RepositoryError: If retrieval fails
        """
        try:
            logger.debug(f"Listing pipelines (include_inactive={include_inactive})")

            pipelines = self.pipeline_repo.get_all(include_inactive=include_inactive)

            logger.info(f"Retrieved {len(pipelines)} pipelines")
            return pipelines

        except RepositoryError:
            logger.error("Failed to list pipelines")
            raise
        except Exception as e:
            logger.error(f"Unexpected error listing pipelines: {e}")
            raise RepositoryError(f"Failed to list pipelines: {e}") from e

    def list_pipeline_summaries(
        self, include_inactive: bool = False
    ) -> List[PipelineDefinitionSummary]:
        """
        Get pipeline summaries for lightweight UI operations (dropdowns, tables)

        Args:
            include_inactive: If True, include inactive pipelines

        Returns:
            List of PipelineDefinitionSummary models

        Raises:
            RepositoryError: If retrieval fails
        """
        try:
            logger.debug(
                f"Listing pipeline summaries (include_inactive={include_inactive})"
            )

            summaries = self.pipeline_repo.get_summaries(
                include_inactive=include_inactive
            )

            logger.info(f"Retrieved {len(summaries)} pipeline summaries")
            return summaries

        except RepositoryError:
            logger.error("Failed to list pipeline summaries")
            raise
        except Exception as e:
            logger.error(f"Unexpected error listing pipeline summaries: {e}")
            raise RepositoryError(f"Failed to list pipeline summaries: {e}") from e

    # === Validation Operations ===

    def validate_pipeline(self, pipeline_state: PipelineState) -> PipelineValidationResult:
        """
        Validate a pipeline state

        Args:
            pipeline_state: Pipeline state to validate

        Returns:
            ValidationResult with valid flag and any errors

        Raises:
            Exception: If validation process fails unexpectedly
        """
        try:
            logger.debug("Validating pipeline state")

            # Create validator with module catalog repository and run validation
            validator = PipelineValidator(module_catalog_repo=self.module_catalog_repo)
            result = validator.validate(pipeline_state)
            
            if not result.valid:
                logger.info(
                    f"Pipeline validation failed with {len(result.errors)} error(s)"
                )
                error_messages = [
                    f"{err.code}: {err.message}" for err in result.errors
                ]
                raise ValueError(
                    f"Pipeline validation failed: {'; '.join(error_messages)}"
                )
            return result

        except Exception as e:
            logger.error(f"Unexpected error during pipeline validation: {e}")
            # Re-raise to let caller handle it
            raise

    # === Execution Operations ===

    def execute_pipeline(
        self,
        pipeline_id: str,
        entry_values: Dict[str, Any],
        enable_tracking: bool = True,
    ) -> RunResult:
        """
        Execute a pipeline with given entry values.

        Args:
            pipeline_id: ID of the pipeline to execute
            entry_values: Entry point values for the pipeline (can use either entry point names or node IDs as keys)
            enable_tracking: Whether to persist execution history

        Returns:
            RunResult with execution status and outputs

        Raises:
            ObjectNotFoundError: If pipeline not found
            ValueError: If entry values are invalid
            RepositoryError: If database operations fail
        """
        try:
            # 1. Generate run ID
            logger.info(f"Starting pipeline execution: {pipeline_id}")

            # 2. Get pipeline and verify it exists
            pipeline = self.pipeline_repo.get_by_id(pipeline_id)
            if not pipeline:
                raise ObjectNotFoundError("Pipeline", pipeline_id)
            if not pipeline.plan_checksum:
                raise Exception(f"Pipeline: {pipeline_id} has not been compiled yet")

            # 3. Get compiled steps
            steps = self.step_repo.get_steps_by_checksum(pipeline.plan_checksum)
            if not steps:
                logger.error(f"No compiled steps found for pipeline {pipeline_id}")
                raise RepositoryError(
                    f"Pipeline {pipeline_id} is not properly compiled"
                )

            logger.info(f"Loaded {len(steps)} compiled steps for execution")

            # 4. Map entry point names to node IDs if needed
            mapped_entry_values = self._map_entry_values_to_node_ids(
                entry_values, pipeline.pipeline_json
            )
            logger.debug(f"Mapped entry values: {mapped_entry_values}")

            # 5. Create executor and run pipeline
            executor = PipelineExecutor()
            run_create, step_creates, run_result = executor.run_pipeline(
                pipeline_id=pipeline_id,
                run_id=run_id,
                steps=steps,
                entry_values=mapped_entry_values,
                pipeline_state=pipeline.pipeline_json,  # Pass pipeline state (it's actually a PipelineState object, not JSON)
            )

            # 5. Persist execution history if tracking enabled
            if enable_tracking:
                try:
                    # Initialize repositories
                    run_repo = ExecutionRunRepository(self.connection_manager)
                    step_repo = ExecutionStepRepository(self.connection_manager)

                    # Create run record
                    run_repo.create_run(run_create)

                    # Create step records
                    for step_create in step_creates:
                        step_repo.create_step(step_create)

                    # Update run status to completed
                    run_repo.update_run_status(
                        run_id,
                        run_result.status,
                        datetime.fromisoformat(run_result.completed_at),
                    )

                    logger.info(f"Execution history persisted for run {run_id}")

                except Exception as e:
                    # Log but don't fail the execution if tracking fails
                    logger.error(f"Failed to persist execution history: {e}")

            logger.info(
                f"Pipeline execution completed: {run_id}, status: {run_result.status}"
            )
            return run_result

        except (ObjectNotFoundError, ValueError):
            # Re-raise business logic exceptions
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error executing pipeline {pipeline_id}: {e}", exc_info=True
            )
            raise RepositoryError(f"Failed to execute pipeline: {e}") from e

    def _map_entry_values_to_node_ids(
        self, entry_values: Dict[str, Any], pipeline_state: PipelineState
    ) -> Dict[str, Any]:
        """
        Map entry point names to node IDs in entry values.

        The API expects entry values with entry point NAMES as keys:
        {"Input": "Hello World", "Config": {"setting": "value"}}

        This method maps those names to the internal node IDs used by the executor.

        Args:
            entry_values: Dictionary with entry point names as keys
            pipeline_state: Pipeline state containing entry point definitions

        Returns:
            Dictionary with node IDs as keys (for internal use by executor)

        Raises:
            ValueError: If an entry point name is not found
        """
        # Create mapping from name to node_id
        name_to_node_id = {}
        node_id_set = set()

        for entry_point in pipeline_state.entry_points:
            name_to_node_id[entry_point.name] = entry_point.node_id
            node_id_set.add(entry_point.node_id)

        # Map the entry values
        mapped_values = {}

        for key, value in entry_values.items():
            if key in node_id_set:
                # Already a node ID (for backward compatibility)
                mapped_values[key] = value
                logger.debug(f"Using node ID directly: '{key}'")
            elif key in name_to_node_id:
                # It's an entry point name, map to node ID
                node_id = name_to_node_id[key]
                mapped_values[node_id] = value
                logger.debug(f"Mapped entry point name '{key}' to node ID '{node_id}'")
            else:
                # Key not found as either name or node ID
                available_names = list(name_to_node_id.keys())
                raise ValueError(
                    f"Entry point '{key}' not found. "
                    f"Available entry points: {available_names}"
                )

        return mapped_values
