"""
Pipeline Repository
Repository for pipeline operations following ETO server patterns
"""
import logging
import uuid
from typing import Optional, List
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError

from .base import BaseRepository
from src.shared.database.models import PipelineDefinitionModel
from shared.types import PipelineDefinition, PipelineDefinitionCreate, PipelineDefinitionSummary
from src.shared.exceptions import RepositoryError, ObjectNotFoundError

logger = logging.getLogger(__name__)


class PipelineDefinitionRepository(BaseRepository[PipelineDefinitionModel]):
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

    def _convert_to_domain_object(self, db_model: PipelineDefinitionModel) -> PipelineDefinition:
        """Convert SQLAlchemy model to domain object"""
        return PipelineDefinition.from_db_model(db_model)

    def _convert_to_summary(self, db_model: PipelineDefinitionModel) -> PipelineDefinitionSummary:
        """Convert SQLAlchemy model to summary object"""
        pipeline = self._convert_to_domain_object(db_model)
        return PipelineDefinitionSummary.from_full_pipeline_definition(pipeline)

    # ========== Required Operations (Get, List, Upload) ==========

    def create(self, pipeline_create: PipelineDefinitionCreate) -> PipelineDefinition:
        """
        Upload/create new pipeline from Pydantic model
        Pipelines are immutable once created

        Args:
            pipeline_create: PipelineDefinitionCreate model with pipeline data

        Returns:
            Created Pipeline domain model
        """
        try:
            with self.connection_manager.session_scope() as session:
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

    def get_by_id(self, pipeline_id: int) -> Optional[PipelineDefinition]:
        """
        Get pipeline by ID

        Args:
            pipeline_id: Pipeline ID to search for

        Returns:
            Pipeline domain object or None if not found
        """
        try:
            with self.connection_manager.session_scope() as session:
                model = session.get(self.model_class, pipeline_id)

                if not model:
                    logger.debug(f"Pipeline not found: {pipeline_id}")
                    return None

                return self._convert_to_domain_object(model)

        except SQLAlchemyError as e:
            logger.error(f"Error getting pipeline {pipeline_id}: {e}")
            raise RepositoryError(f"Failed to get pipeline: {e}") from e

    def get_all(self, include_inactive: bool = False) -> List[PipelineDefinition]:
        """
        Get all pipelines (list operation)

        Args:
            include_inactive: If True, include inactive pipelines

        Returns:
            List of Pipeline domain objects
        """
        try:
            with self.connection_manager.session_scope() as session:
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

    def get_summaries(self, include_inactive: bool = False) -> List[PipelineDefinitionSummary]:
        """
        Get pipeline summaries for list views (lightweight)

        Args:
            include_inactive: If True, include inactive pipelines

        Returns:
            List of PipelineDefinitionSummary objects
        """
        try:
            with self.connection_manager.session_scope() as session:
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

    def create_with_checksum(self, data: dict) -> PipelineDefinition:
        """
        Create pipeline with pre-calculated checksum

        Used when checksum is calculated before creation (compilation flow)

        Args:
            data: Pipeline data dict (from model_dump_for_db) with 'plan_checksum' and 'compiled_at' already set

        Returns:
            Created Pipeline domain object
        """
        try:
            with self.connection_manager.session_scope() as session:
                # Generate ID if not present

                # Create model instance
                model = self.model_class(**data)
                session.add(model)
                session.flush()
                session.refresh(model)

                checksum_preview = data.get('plan_checksum', 'none')
                checksum_str = checksum_preview[:8] + "..." if checksum_preview and checksum_preview != 'none' else 'none'
                logger.info(f"Created pipeline: {model.id} - {model.name} with checksum {checksum_str}")

                return self._convert_to_domain_object(model)

        except SQLAlchemyError as e:
            logger.error(f"Error creating pipeline: {e}")
            raise RepositoryError(f"Failed to create pipeline: {e}") from e

    # ========== Compilation-Related Operations ==========

    def update_pipeline_checksum(self, pipeline_id: int, checksum: str, compiled_at: datetime) -> PipelineDefinition:
        """
        Update pipeline's plan_checksum and compiled_at timestamp

        Args:
            pipeline_id: Pipeline ID to update
            checksum: Plan checksum to set
            compiled_at: Compilation timestamp

        Returns:
            Updated Pipeline domain object

        Raises:
            ObjectNotFoundError: If pipeline doesn't exist
            RepositoryError: If update fails
        """
        try:
            with self.connection_manager.session_scope() as session:
                model = session.get(self.model_class, pipeline_id)

                if not model:
                    raise ObjectNotFoundError('Pipeline', pipeline_id)

                model.plan_checksum = checksum
                model.compiled_at = compiled_at
                session.flush()
                session.refresh(model)

                logger.info(f"Updated pipeline {pipeline_id} with checksum {checksum[:8]}...")

                return self._convert_to_domain_object(model)

        except ObjectNotFoundError:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error updating pipeline checksum: {e}")
            raise RepositoryError(f"Failed to update checksum: {e}") from e