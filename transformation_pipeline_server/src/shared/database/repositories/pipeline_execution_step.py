"""
Execution Step Repository
Repository for execution step operations
"""
import logging
from sqlalchemy.exc import SQLAlchemyError

from typing import List
from shared.types import PipelineExecutionStep, PipelineExecutionStepCreate

from shared.database.models import PipelineExecutionStepModel
from shared.exceptions import RepositoryError

from .base import BaseRepository

logger = logging.getLogger(__name__)


class PipelineExecutionStepRepository(BaseRepository[PipelineExecutionStepModel]):
    """Repository for execution step operations"""

    @property
    def model_class(self):
        return PipelineExecutionStepModel

    def _convert_to_domain_object(self, db_model: PipelineExecutionStepModel) -> PipelineExecutionStep:
        """Convert SQLAlchemy model to domain object"""
        return PipelineExecutionStep.from_db_model(db_model)

    def create(self, step_create: PipelineExecutionStepCreate) -> PipelineExecutionStep:
        """Add an execution step to the history"""
        try:
            with self.connection_manager.session_scope() as session:
                data = step_create.model_dump_for_db()
                model = self.model_class(**data)
                session.add(model)
                session.flush()
                session.refresh(model)

                logger.debug(f"Created execution step for module {step_create.module_instance_id}")
                return self._convert_to_domain_object(model)

        except SQLAlchemyError as e:
            logger.error(f"Error creating execution step: {e}")
            raise RepositoryError(f"Failed to create execution step: {e}") from e

    def get_steps_by_run(self, run_id: int) -> List[PipelineExecutionStep]:
        """Get all execution steps for a run"""
        try:
            with self.connection_manager.session_scope() as session:
                models = session.query(self.model_class).filter_by(
                    run_id=run_id
                ).order_by(
                    self.model_class.step_number
                ).all()

                return [self._convert_to_domain_object(m) for m in models]

        except SQLAlchemyError as e:
            logger.error(f"Error getting steps for run {run_id}: {e}")
            raise RepositoryError(f"Failed to get execution steps: {e}") from e