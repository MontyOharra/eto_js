"""
Pipeline Step Repository
Repository for compiled pipeline step operations
"""
import logging
from typing import List, Optional
from sqlalchemy.exc import SQLAlchemyError

from .base import BaseRepository
from src.shared.database.models import PipelineStepModel
from src.shared.models import PipelineStep, PipelineStepCreate
from src.shared.exceptions import RepositoryError

logger = logging.getLogger(__name__)


class PipelineStepRepository(BaseRepository[PipelineStepModel]):
    """
    Repository for pipeline step operations
    Manages compiled execution steps grouped by plan_checksum
    """

    @property
    def model_class(self):
        return PipelineStepModel

    def _convert_to_domain_object(self, db_model: PipelineStepModel) -> PipelineStep:
        """Convert SQLAlchemy model to domain object"""
        return PipelineStep.from_db_model(db_model)

    # ========== Core Step Operations ==========

    def get_steps_by_checksum(self, checksum: str) -> List[PipelineStep]:
        """
        Get all compiled steps for a given plan checksum

        Args:
            checksum: Plan checksum (SHA-256 hex string)

        Returns:
            List of PipelineStep domain objects, ordered by step_number
            Empty list if no steps found for this checksum
        """
        try:
            with self.connection_manager.session_scope() as session:
                db_models = session.query(self.model_class).filter(
                    self.model_class.plan_checksum == checksum
                ).order_by(self.model_class.step_number).all()

                logger.debug(f"Retrieved {len(db_models)} steps for checksum {checksum[:8]}...")

                return [self._convert_to_domain_object(model) for model in db_models]

        except SQLAlchemyError as e:
            logger.error(f"Error getting steps for checksum {checksum}: {e}")
            raise RepositoryError(f"Failed to get steps: {e}") from e

    def save_steps(self, steps: List[PipelineStepCreate]) -> List[PipelineStep]:
        """
        Bulk save compiled pipeline steps

        Args:
            steps: List of PipelineStepCreate domain objects to save

        Returns:
            List of saved PipelineStep domain objects with IDs

        Raises:
            RepositoryError: If save fails
        """
        try:
            with self.connection_manager.session_scope() as session:
                # Convert domain objects to database models
                db_models = []
                for step in steps:
                    data = step.model_dump_for_db()
                    db_model = self.model_class(**data)
                    db_models.append(db_model)

                # Bulk save
                session.add_all(db_models)
                session.flush()

                # Refresh to get IDs
                for model in db_models:
                    session.refresh(model)

                logger.info(f"Saved {len(db_models)} pipeline steps")

                # Convert back to domain objects
                return [self._convert_to_domain_object(model) for model in db_models]

        except SQLAlchemyError as e:
            logger.error(f"Error saving pipeline steps: {e}")
            raise RepositoryError(f"Failed to save steps: {e}") from e

    def checksum_exists(self, checksum: str) -> bool:
        """
        Check if compiled steps exist for a given checksum (cache check)

        Args:
            checksum: Plan checksum to check

        Returns:
            True if steps exist, False otherwise
        """
        try:
            with self.connection_manager.session_scope() as session:
                exists = session.query(self.model_class).filter(
                    self.model_class.plan_checksum == checksum
                ).first() is not None

                logger.debug(f"Checksum {checksum[:8]}... exists: {exists}")
                return exists

        except SQLAlchemyError as e:
            logger.error(f"Error checking checksum existence: {e}")
            raise RepositoryError(f"Failed to check checksum: {e}") from e

    def get_step_count_by_checksum(self, checksum: str) -> int:
        """
        Get count of steps for a given checksum

        Args:
            checksum: Plan checksum

        Returns:
            Number of steps
        """
        try:
            with self.connection_manager.session_scope() as session:
                count = session.query(self.model_class).filter(
                    self.model_class.plan_checksum == checksum
                ).count()

                return count

        except SQLAlchemyError as e:
            logger.error(f"Error counting steps for checksum: {e}")
            raise RepositoryError(f"Failed to count steps: {e}") from e

    def delete_steps_by_checksum(self, checksum: str) -> int:
        """
        Delete all steps for a given checksum

        Note: This should rarely be used - steps are meant to be immutable cache.
        Only use for cleanup/maintenance.

        Args:
            checksum: Plan checksum

        Returns:
            Number of steps deleted
        """
        try:
            with self.connection_manager.session_scope() as session:
                count = session.query(self.model_class).filter(
                    self.model_class.plan_checksum == checksum
                ).delete()

                logger.warning(f"Deleted {count} steps for checksum {checksum[:8]}...")
                return count

        except SQLAlchemyError as e:
            logger.error(f"Error deleting steps: {e}")
            raise RepositoryError(f"Failed to delete steps: {e}") from e
