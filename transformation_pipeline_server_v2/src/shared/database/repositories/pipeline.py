"""
Pipeline Repository
Repository for pipeline operations following ETO server patterns
"""
import logging
import uuid
from typing import Optional, List
from sqlalchemy.exc import SQLAlchemyError

from .base import BaseRepository
from src.shared.database.models import PipelineDefinitionModel
from src.shared.models.pipeline import Pipeline, PipelineCreate, PipelineSummary
from src.shared.exceptions import RepositoryError, ObjectNotFoundError

logger = logging.getLogger(__name__)


class PipelineRepository(BaseRepository[PipelineDefinitionModel]):
    """
    Repository for pipeline operations
    Manages pipelines with immutable design - only get, list, and create operations
    """

    @property
    def model_class(self):
        return PipelineDefinitionModel

    def _generate_pipeline_id(self) -> str:
        """Generate unique pipeline ID"""
        return f"pipeline_{uuid.uuid4().hex[:12]}"

    def _convert_to_domain_object(self, db_model: PipelineDefinitionModel) -> Pipeline:
        """Convert SQLAlchemy model to domain object"""
        return Pipeline.from_db_model(db_model)

    def _convert_to_summary(self, db_model: PipelineDefinitionModel) -> PipelineSummary:
        """Convert SQLAlchemy model to summary object"""
        pipeline = self._convert_to_domain_object(db_model)
        return PipelineSummary.from_full_pipeline(pipeline)

    # ========== Required Operations (Get, List, Upload) ==========

    def create(self, pipeline_create: PipelineCreate) -> Pipeline:
        """
        Upload/create new pipeline from Pydantic model
        Pipelines are immutable once created

        Args:
            pipeline_create: PipelineCreate model with pipeline data

        Returns:
            Created Pipeline domain model
        """
        try:
            with self.connection_manager.get_session_context() as session:
                # Generate ID
                pipeline_id = self._generate_pipeline_id()

                # Convert to database format with JSON serialization
                data = pipeline_create.model_dump_for_db()
                data['id'] = pipeline_id

                # Create model instance
                model = self.model_class(**data)
                session.add(model)
                session.flush()  # Get ID before commit
                session.refresh(model)

                logger.info(f"Created pipeline: {pipeline_id} - {pipeline_create.name}")

                # Return domain model
                return self._convert_to_domain_object(model)

        except SQLAlchemyError as e:
            logger.error(f"Error creating pipeline: {e}")
            raise RepositoryError(f"Failed to create pipeline: {e}") from e

    def get_by_id(self, pipeline_id: str) -> Optional[Pipeline]:
        """
        Get pipeline by ID

        Args:
            pipeline_id: Pipeline ID to search for

        Returns:
            Pipeline domain object or None if not found
        """
        try:
            with self.connection_manager.get_session_context() as session:
                model = session.get(self.model_class, pipeline_id)

                if not model:
                    logger.debug(f"Pipeline not found: {pipeline_id}")
                    return None

                return self._convert_to_domain_object(model)

        except SQLAlchemyError as e:
            logger.error(f"Error getting pipeline {pipeline_id}: {e}")
            raise RepositoryError(f"Failed to get pipeline: {e}") from e

    def get_all(self, include_inactive: bool = False) -> List[Pipeline]:
        """
        Get all pipelines (list operation)

        Args:
            include_inactive: If True, include inactive pipelines

        Returns:
            List of Pipeline domain objects
        """
        try:
            with self.connection_manager.get_session_context() as session:
                query = session.query(self.model_class)

                # Filter by active status if requested
                if not include_inactive:
                    query = query.filter(self.model_class.is_active == True)

                # Order by creation date (newest first)
                query = query.order_by(self.model_class.created_at.desc())

                models = query.all()
                logger.debug(f"Retrieved {len(models)} pipelines")

                return [self._convert_to_domain_object(model) for model in models]

        except SQLAlchemyError as e:
            logger.error(f"Error getting all pipelines: {e}")
            raise RepositoryError(f"Failed to get pipelines: {e}") from e

    def get_summaries(self, include_inactive: bool = False) -> List[PipelineSummary]:
        """
        Get pipeline summaries for list views (lightweight)

        Args:
            include_inactive: If True, include inactive pipelines

        Returns:
            List of PipelineSummary objects
        """
        try:
            with self.connection_manager.get_session_context() as session:
                query = session.query(self.model_class)

                # Filter by active status if requested
                if not include_inactive:
                    query = query.filter(self.model_class.is_active == True)

                # Order by creation date (newest first)
                query = query.order_by(self.model_class.created_at.desc())

                models = query.all()
                logger.debug(f"Retrieved {len(models)} pipeline summaries")

                return [self._convert_to_summary(model) for model in models]

        except SQLAlchemyError as e:
            logger.error(f"Error getting pipeline summaries: {e}")
            raise RepositoryError(f"Failed to get pipeline summaries: {e}") from e