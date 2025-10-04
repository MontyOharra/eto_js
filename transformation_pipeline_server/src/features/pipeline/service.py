"""
Pipeline Service
Service for pipeline save and load operations following ETO server patterns
"""
import logging
from typing import Optional, List

from src.shared.database.repositories.pipeline import PipelineRepository
from src.shared.database.repositories.module_catalog import ModuleCatalogRepository
from src.shared.exceptions import RepositoryError, ObjectNotFoundError
from src.shared.models.pipeline import Pipeline, PipelineCreate, PipelineSummary, PipelineState
from src.features.pipeline.validation.validator import PipelineValidator
from src.features.pipeline.validation.errors import ValidationResult
from src.features.pipeline.compilation.graph_pruner import GraphPruner

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

        # Repository layer - with explicit type annotations for IDE support
        self.pipeline_repo: PipelineRepository = PipelineRepository(self.connection_manager)
        self.module_catalog_repo: ModuleCatalogRepository = ModuleCatalogRepository(self.connection_manager)

        logger.info("Pipeline Service initialized")

    # === Core Operations (Save/Load) ===

    def upload_pipeline(self, pipeline_create: PipelineCreate) -> Pipeline:
        """
        Upload/save a new pipeline

        Args:
            pipeline_create: PipelineCreate model with pipeline data

        Returns:
            Created Pipeline domain model

        Raises:
            RepositoryError: If save operation fails
        """
        try:
            logger.info(f"Uploading pipeline: {pipeline_create.name}")

            # Delegate to repository for persistence
            pipeline = self.pipeline_repo.create(pipeline_create)

            logger.info(f"Successfully uploaded pipeline: {pipeline.id} - {pipeline.name}")
            return pipeline

        except RepositoryError:
            logger.error(f"Failed to upload pipeline: {pipeline_create.name}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error uploading pipeline: {e}")
            raise RepositoryError(f"Failed to upload pipeline: {e}") from e

    def get_pipeline(self, pipeline_id: str) -> Pipeline:
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
            logger.debug(f"Getting pipeline: {pipeline_id}")

            pipeline = self.pipeline_repo.get_by_id(pipeline_id)

            if not pipeline:
                logger.warning(f"Pipeline not found: {pipeline_id}")
                raise ObjectNotFoundError("Pipeline", pipeline_id)

            logger.debug(f"Retrieved pipeline: {pipeline.id} - {pipeline.name}")
            return pipeline

        except ObjectNotFoundError:
            raise
        except RepositoryError:
            logger.error(f"Failed to get pipeline: {pipeline_id}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting pipeline {pipeline_id}: {e}")
            raise RepositoryError(f"Failed to get pipeline: {e}") from e

    def list_pipelines(self, include_inactive: bool = False) -> List[Pipeline]:
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

    def list_pipeline_summaries(self, include_inactive: bool = False) -> List[PipelineSummary]:
        """
        Get pipeline summaries for lightweight UI operations (dropdowns, tables)

        Args:
            include_inactive: If True, include inactive pipelines

        Returns:
            List of PipelineSummary models

        Raises:
            RepositoryError: If retrieval fails
        """
        try:
            logger.debug(f"Listing pipeline summaries (include_inactive={include_inactive})")

            summaries = self.pipeline_repo.get_summaries(include_inactive=include_inactive)

            logger.info(f"Retrieved {len(summaries)} pipeline summaries")
            return summaries

        except RepositoryError:
            logger.error("Failed to list pipeline summaries")
            raise
        except Exception as e:
            logger.error(f"Unexpected error listing pipeline summaries: {e}")
            raise RepositoryError(f"Failed to list pipeline summaries: {e}") from e

    # === Validation Operations ===

    def validate_pipeline(self, pipeline_state: PipelineState) -> ValidationResult:
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

            if result.valid:
                logger.debug("Pipeline validation passed")
            else:
                logger.debug(f"Pipeline validation failed with {len(result.errors)} error(s)")

            return result

        except Exception as e:
            logger.error(f"Unexpected error during pipeline validation: {e}")
            # Re-raise to let caller handle it
            raise

    def test_upload_pipeline(self, pipeline_create: PipelineCreate) -> bool:
        """
        TEST METHOD: Validate and prune pipeline (compilation step 1)

        This method is under development and will eventually handle full compilation.
        Currently it:
        1. Validates the pipeline
        2. Prunes dead branches using GraphPruner
        3. Prints debug info about pruning results

        Args:
            pipeline_create: Pipeline creation data

        Returns:
            True if validation and pruning succeeded, False otherwise
        """
        try:
            logger.info(f"[TEST_UPLOAD] Starting test upload for pipeline: {pipeline_create.name}")

            # Step 1: Validate the pipeline
            logger.info("[TEST_UPLOAD] Step 1: Validating pipeline...")
            validator = PipelineValidator(module_catalog_repo=self.module_catalog_repo)
            result = validator.validate(pipeline_create.pipeline_json)

            if not result.valid:
                logger.error(f"[TEST_UPLOAD] Validation failed with {len(result.errors)} error(s):")
                for i, error in enumerate(result.errors, 1):
                    logger.error(f"[TEST_UPLOAD]   Error {i}: {error.code.value} - {error.message}")
                return False

            logger.info("[TEST_UPLOAD] ✓ Validation passed")

            # Step 2: Prune the pipeline using reachable modules from validator
            logger.info("[TEST_UPLOAD] Step 2: Pruning pipeline...")

            original_pipeline = pipeline_create.pipeline_json
            reachable_modules = validator.reachable_modules

            # Debug: Print original state
            logger.debug(f"[TEST_UPLOAD] Original pipeline:")
            logger.debug(f"[TEST_UPLOAD]   - Entry points: {len(original_pipeline.entry_points)}")
            logger.debug(f"[TEST_UPLOAD]   - Modules: {len(original_pipeline.modules)}")
            logger.debug(f"[TEST_UPLOAD]   - Connections: {len(original_pipeline.connections)}")
            logger.debug(f"[TEST_UPLOAD]   - Module IDs: {[m.module_instance_id for m in original_pipeline.modules]}")

            # Prune using GraphPruner
            pruned_pipeline = GraphPruner.prune(original_pipeline, reachable_modules)

            # Debug: Print pruned state
            logger.debug(f"[TEST_UPLOAD] Pruned pipeline:")
            logger.debug(f"[TEST_UPLOAD]   - Entry points: {len(pruned_pipeline.entry_points)}")
            logger.debug(f"[TEST_UPLOAD]   - Modules: {len(pruned_pipeline.modules)}")
            logger.debug(f"[TEST_UPLOAD]   - Connections: {len(pruned_pipeline.connections)}")
            logger.debug(f"[TEST_UPLOAD]   - Module IDs: {[m.module_instance_id for m in pruned_pipeline.modules]}")

            # Calculate what was pruned
            original_module_ids = {m.module_instance_id for m in original_pipeline.modules}
            pruned_module_ids = {m.module_instance_id for m in pruned_pipeline.modules}
            removed_modules = original_module_ids - pruned_module_ids

            if removed_modules:
                logger.info(f"[TEST_UPLOAD] ✓ Pruned {len(removed_modules)} dead branch module(s): {list(removed_modules)}")
            else:
                logger.info(f"[TEST_UPLOAD] ✓ No dead branches found - all {len(original_pipeline.modules)} modules are reachable")

            # Show connection pruning
            connections_removed = len(original_pipeline.connections) - len(pruned_pipeline.connections)
            if connections_removed > 0:
                logger.info(f"[TEST_UPLOAD] ✓ Removed {connections_removed} connection(s) to dead branches")

            logger.info("[TEST_UPLOAD] ✅ Test upload completed successfully")
            return True

        except Exception as e:
            logger.error(f"[TEST_UPLOAD] ❌ Unexpected error during test upload: {e}", exc_info=True)
            return False

    # === Utility Operations ===

    def pipeline_exists(self, pipeline_id: str) -> bool:
        """
        Check if a pipeline exists

        Args:
            pipeline_id: Pipeline ID to check

        Returns:
            True if pipeline exists, False otherwise

        Raises:
            RepositoryError: If check operation fails
        """
        try:
            logger.debug(f"Checking pipeline existence: {pipeline_id}")

            exists = self.pipeline_repo.get_by_id(pipeline_id) is not None

            logger.debug(f"Pipeline {pipeline_id} exists: {exists}")
            return exists

        except RepositoryError:
            logger.error(f"Failed to check pipeline existence: {pipeline_id}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error checking pipeline existence {pipeline_id}: {e}")
            raise RepositoryError(f"Failed to check pipeline existence: {e}") from e