"""
Pipeline Repository
Repository for managing transformation pipeline database operations
"""
import logging
import uuid
from typing import Optional, List, Dict, Any
from sqlalchemy.exc import SQLAlchemyError

from src.shared.database.models import PipelineDefinitionModel, PipelineStepModel
from src.shared.models.pipeline import Pipeline, PipelineCreate, PipelineUpdate, PipelineSummary

logger = logging.getLogger(__name__)


class RepositoryError(Exception):
    """Base exception for repository operations"""
    pass


class ObjectNotFoundError(RepositoryError):
    """Raised when requested object is not found"""
    def __init__(self, object_type: str, object_id: any):
        super().__init__(f"{object_type} with ID {object_id} not found")
        self.object_type = object_type
        self.object_id = object_id


class PipelineRepository:
    """
    Repository for pipeline operations
    Manages CRUD operations for transformation pipelines
    """

    def __init__(self, connection_manager):
        """Initialize repository with connection manager"""
        if not connection_manager:
            raise ValueError("DatabaseConnectionManager is required")

        self.connection_manager = connection_manager
        self.model_class = PipelineDefinitionModel
        logger.debug(f"Initialized {self.__class__.__name__}")

    def _generate_pipeline_id(self) -> str:
        """Generate unique pipeline ID"""
        return f"pipeline_{uuid.uuid4().hex[:12]}"

    def _convert_to_domain_object(self, db_model: PipelineDefinitionModel) -> Pipeline:
        """Convert SQLAlchemy model to domain object"""
        # For now, we'll need to add created_by_user and status fields to the DB model
        # These are missing from the current schema but required by the domain model
        return Pipeline.from_db_model(db_model)

    def _convert_to_summary(self, db_model: PipelineDefinitionModel) -> PipelineSummary:
        """Convert SQLAlchemy model to summary object"""
        pipeline = self._convert_to_domain_object(db_model)
        return PipelineSummary.from_full_pipeline(pipeline)

    # ========== CRUD Operations with Pydantic Types ==========

    def create(self, pipeline_create: PipelineCreate) -> Pipeline:
        """
        Create new pipeline from Pydantic model

        Args:
            pipeline_create: PipelineCreate model with pipeline data

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

                # Add missing fields that are in domain model but not in DB yet
                # These should be added to the database schema
                data.pop('start_modules', None)  # Remove computed fields
                data.pop('end_modules', None)

                # Rename pipeline_json to match DB column name
                data['pipeline_json'] = data.pop('pipeline_json')
                data['visual_json'] = data.pop('visual_json')

                # Create model instance
                model = self.model_class(**data)
                session.add(model)
                session.flush()  # Get ID before commit

                logger.info(f"Created pipeline: {pipeline_id}")

                # Return domain model
                return self._convert_to_domain_object(model)

        except SQLAlchemyError as e:
            logger.error(f"Error creating pipeline: {e}")
            raise RepositoryError(f"Failed to create pipeline: {e}") from e

    def update(self, pipeline_id: str, pipeline_update: PipelineUpdate) -> Pipeline:
        """
        Update existing pipeline from Pydantic update model

        Args:
            pipeline_id: Pipeline ID
            pipeline_update: PipelineUpdate model with fields to update

        Returns:
            Updated Pipeline

        Raises:
            ObjectNotFoundError: If pipeline not found
        """
        try:
            with self.connection_manager.session_scope() as session:
                model = session.query(self.model_class).filter(
                    self.model_class.id == pipeline_id
                ).first()

                if not model:
                    raise ObjectNotFoundError('Pipeline', pipeline_id)

                # Get update dict with JSON serialization for modified fields only
                updates = pipeline_update.model_dump_for_db(exclude_unset=True)

                # Remove computed fields
                updates.pop('start_modules', None)
                updates.pop('end_modules', None)

                # Apply updates
                for key, value in updates.items():
                    if hasattr(model, key):
                        setattr(model, key, value)

                session.flush()

                logger.info(f"Updated pipeline: {pipeline_id}")

                # Return updated domain model
                return self._convert_to_domain_object(model)

        except ObjectNotFoundError:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error updating pipeline {pipeline_id}: {e}")
            raise RepositoryError(f"Failed to update pipeline: {e}") from e

    def get_by_id(self, pipeline_id: str) -> Optional[Pipeline]:
        """
        Get pipeline by ID

        Args:
            pipeline_id: Pipeline ID to search for

        Returns:
            Pipeline domain object or None if not found
        """
        try:
            with self.connection_manager.session_scope() as session:
                model = session.query(self.model_class).filter(
                    self.model_class.id == pipeline_id
                ).first()

                if not model:
                    logger.debug(f"Pipeline not found: {pipeline_id}")
                    return None

                return self._convert_to_domain_object(model)

        except SQLAlchemyError as e:
            logger.error(f"Error getting pipeline {pipeline_id}: {e}")
            raise RepositoryError(f"Failed to get pipeline: {e}") from e

    def get_all(self, include_archived: bool = False) -> List[Pipeline]:
        """
        Get all pipelines

        Args:
            include_archived: If True, include archived pipelines

        Returns:
            List of Pipeline domain objects
        """
        try:
            with self.connection_manager.session_scope() as session:
                query = session.query(self.model_class)

                # Filter out archived if not requested
                # Note: This requires adding a status field to the DB model
                # For now, return all pipelines

                query = query.order_by(
                    self.model_class.updated_at.desc()
                )

                models = query.all()

                return [self._convert_to_domain_object(model) for model in models]

        except SQLAlchemyError as e:
            logger.error(f"Error getting all pipelines: {e}")
            raise RepositoryError(f"Failed to get pipelines: {e}") from e

    def get_summaries(self, include_archived: bool = False) -> List[PipelineSummary]:
        """
        Get pipeline summaries for list views (lightweight)

        Args:
            include_archived: If True, include archived pipelines

        Returns:
            List of PipelineSummary objects
        """
        try:
            with self.connection_manager.session_scope() as session:
                query = session.query(self.model_class)

                query = query.order_by(
                    self.model_class.updated_at.desc()
                )

                models = query.all()

                return [self._convert_to_summary(model) for model in models]

        except SQLAlchemyError as e:
            logger.error(f"Error getting pipeline summaries: {e}")
            raise RepositoryError(f"Failed to get pipeline summaries: {e}") from e

    def get_by_name(self, name: str) -> List[Pipeline]:
        """
        Get pipelines by name

        Args:
            name: Pipeline name (can have multiple with same name)

        Returns:
            List of Pipeline domain objects
        """
        try:
            with self.connection_manager.session_scope() as session:
                models = session.query(self.model_class).filter(
                    self.model_class.name == name
                ).order_by(
                    self.model_class.updated_at.desc()
                ).all()

                return [self._convert_to_domain_object(model) for model in models]

        except SQLAlchemyError as e:
            logger.error(f"Error getting pipelines by name {name}: {e}")
            raise RepositoryError(f"Failed to get pipelines by name: {e}") from e

    def search(self, search_term: str) -> List[PipelineSummary]:
        """
        Search pipelines by name or description

        Args:
            search_term: Term to search for

        Returns:
            List of matching PipelineSummary objects
        """
        try:
            with self.connection_manager.session_scope() as session:
                search_pattern = f"%{search_term}%"

                models = session.query(self.model_class).filter(
                    (self.model_class.name.ilike(search_pattern)) |
                    (self.model_class.description.ilike(search_pattern))
                ).order_by(
                    self.model_class.updated_at.desc()
                ).all()

                return [self._convert_to_summary(model) for model in models]

        except SQLAlchemyError as e:
            logger.error(f"Error searching pipelines with term '{search_term}': {e}")
            raise RepositoryError(f"Failed to search pipelines: {e}") from e

    def exists(self, pipeline_id: str) -> bool:
        """
        Check if pipeline exists

        Args:
            pipeline_id: Pipeline ID

        Returns:
            True if pipeline exists
        """
        try:
            with self.connection_manager.session_scope() as session:
                exists = session.query(self.model_class).filter(
                    self.model_class.id == pipeline_id
                ).first() is not None

                logger.debug(f"Pipeline exists check {pipeline_id}: {exists}")
                return exists

        except SQLAlchemyError as e:
            logger.error(f"Error checking pipeline existence {pipeline_id}: {e}")
            raise RepositoryError(f"Failed to check pipeline existence: {e}") from e

    def delete(self, pipeline_id: str, hard_delete: bool = False) -> bool:
        """
        Delete a pipeline

        Args:
            pipeline_id: Pipeline ID
            hard_delete: If True, permanently delete. Otherwise, mark as archived.

        Returns:
            True if deleted, False if not found
        """
        try:
            with self.connection_manager.session_scope() as session:
                model = session.query(self.model_class).filter(
                    self.model_class.id == pipeline_id
                ).first()

                if not model:
                    logger.warning(f"Pipeline not found for deletion: {pipeline_id}")
                    return False

                if hard_delete:
                    # Also delete related pipeline steps
                    session.query(PipelineStepModel).filter(
                        PipelineStepModel.pipeline_id == pipeline_id
                    ).delete()

                    session.delete(model)
                    logger.info(f"Hard deleted pipeline: {pipeline_id}")
                else:
                    # Soft delete - requires adding status field to DB model
                    # For now, we'll do hard delete
                    session.delete(model)
                    logger.info(f"Deleted pipeline: {pipeline_id}")

                session.flush()
                return True

        except SQLAlchemyError as e:
            logger.error(f"Error deleting pipeline {pipeline_id}: {e}")
            raise RepositoryError(f"Failed to delete pipeline: {e}") from e

    def duplicate(self, pipeline_id: str, new_name: Optional[str] = None) -> Pipeline:
        """
        Duplicate an existing pipeline

        Args:
            pipeline_id: ID of pipeline to duplicate
            new_name: Optional new name for the duplicate

        Returns:
            New Pipeline domain object

        Raises:
            ObjectNotFoundError: If source pipeline not found
        """
        try:
            # Get source pipeline
            source = self.get_by_id(pipeline_id)
            if not source:
                raise ObjectNotFoundError('Pipeline', pipeline_id)

            # Create duplicate
            pipeline_create = PipelineCreate(
                name=new_name or f"{source.name} (Copy)",
                description=source.description,
                pipeline_json=source.pipeline_json,
                visual_json=source.visual_json,
                created_by_user=source.created_by_user
            )

            return self.create(pipeline_create)

        except ObjectNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error duplicating pipeline {pipeline_id}: {e}")
            raise RepositoryError(f"Failed to duplicate pipeline: {e}") from e

    def get_pipeline_stats(self) -> Dict[str, Any]:
        """
        Get statistics about pipelines in the system

        Returns:
            Dictionary with pipeline statistics
        """
        try:
            with self.connection_manager.session_scope() as session:
                total_count = session.query(self.model_class).count()

                # Get counts by status (when status field is added)
                # For now, just return total

                return {
                    "total_pipelines": total_count,
                    "draft_pipelines": 0,  # To be implemented
                    "active_pipelines": 0,  # To be implemented
                    "archived_pipelines": 0,  # To be implemented
                }

        except SQLAlchemyError as e:
            logger.error(f"Error getting pipeline statistics: {e}")
            raise RepositoryError(f"Failed to get pipeline statistics: {e}") from e