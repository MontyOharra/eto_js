"""
Pipeline Service
Service for pipeline save and load operations following ETO server patterns
"""
import logging
from typing import Optional, List

from src.shared.database.repositories.pipeline import PipelineRepository
from src.shared.exceptions import RepositoryError, ObjectNotFoundError
from src.shared.models.pipeline import Pipeline, PipelineCreate, PipelineSummary

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