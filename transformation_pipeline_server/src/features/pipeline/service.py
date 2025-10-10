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
    PipelineValidationResult,
    PipelineValidationError
)

from shared.database.repositories import (
    ModuleCatalogRepository,
    PipelineDefinitionStepRepository,
    PipelineDefinitionRepository
)
from shared.exceptions import RepositoryError, ObjectNotFoundError, PipelineValidationFailedException

from .utils.validation_orchestrator import PipelineValidator
from .utils.compilation import (
    GraphPruner,
    TopologicalSorter,
    ChecksumCalculator,
    PipelineCompiler,
)

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

            # Validate pipeline - let PipelineValidationFailedException propagate
            validation_result = self.validate_pipeline(pipeline_state)

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

        except PipelineValidationFailedException:
            # Let validation errors propagate to API layer - not a service error
            raise
        except RepositoryError:
            logger.error(f"Failed to create pipeline: {pipeline_create.name}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating pipeline: {e}")
            raise RepositoryError(f"Failed to create pipeline: {e}") from e

    def get_pipeline(self, pipeline_definition_id: int) -> PipelineDefinition:
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
        logger.debug("Validating pipeline state")

        # Create validator with module catalog repository and run validation
        validator = PipelineValidator(module_catalog_repo=self.module_catalog_repo)
        result = validator.validate(pipeline_state)

        if not result.valid:
            logger.warning(
                f"⚠️  Pipeline validation failed with {len(result.errors)} error(s)"
            )
            # Log error summary (not full details - API will return structured errors)
            for err in result.errors:
                # Truncate long messages for logging
                msg_preview = err.message[:80] + "..." if len(err.message) > 80 else err.message
                logger.warning(f"   • {err.code}: {msg_preview}")

            # Raise structured exception (API will catch and format for response)
            raise PipelineValidationFailedException(result)

        return result