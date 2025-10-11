"""
Execution Run Repository
Repository for execution run operations
"""
import logging
from sqlalchemy.exc import SQLAlchemyError

from typing import List, Optional
from shared.types import PipelineExecutionRun, PipelineExecutionRunCreate

from shared.database.models import PipelineExecutionRunModel
from shared.exceptions import RepositoryError

from .base import BaseRepository


logger = logging.getLogger(__name__)


class PipelineExecutionRunRepository(BaseRepository[PipelineExecutionRunModel]):
    """Repository for execution run operations"""

    @property
    def model_class(self):
        return PipelineExecutionRunModel

    def _convert_to_domain_object(self, db_model: PipelineExecutionRunModel) -> PipelineExecutionRun:
        """Convert SQLAlchemy model to domain object"""
        return PipelineExecutionRun.from_db_model(db_model)

    def create(self, run_create: PipelineExecutionRunCreate) -> PipelineExecutionRun:
        """Create a new execution run"""
        try:
            with self.connection_manager.session_scope() as session:
                data = run_create.model_dump_for_db()
                model = self.model_class(**data)
                session.add(model)
                session.flush()
                session.refresh(model)

                logger.info(f"Created execution run: {model.id}")
                return self._convert_to_domain_object(model)

        except SQLAlchemyError as e:
            logger.error(f"Error creating execution run: {e}")
            raise RepositoryError(f"Failed to create execution run: {e}") from e

    def update_run_status(self, id: int, status: str) -> Optional[PipelineExecutionRun]:
        """Update run status on completion"""
        try:
            with self.connection_manager.session_scope() as session:
                model = session.query(self.model_class).filter_by(id=id).first()

                if not model:
                    logger.warning(f"Execution run not found: {id}")
                    return None

                model.status = status
                session.flush()
                session.refresh(model)

                logger.info(f"Updated execution run status: {id} -> {status}")
                return self._convert_to_domain_object(model)

        except SQLAlchemyError as e:
            logger.error(f"Error updating execution run {id}: {e}")
            raise RepositoryError(f"Failed to update execution run: {e}") from e

    def get_run_by_id(self, id: int) -> Optional[PipelineExecutionRun]:
        """Get execution run by ID"""
        try:
            with self.connection_manager.session_scope() as session:
                model = session.query(self.model_class).filter_by(id=id).first()

                if not model:
                    return None

                return self._convert_to_domain_object(model)

        except SQLAlchemyError as e:
            logger.error(f"Error getting execution run {id}: {e}")
            raise RepositoryError(f"Failed to get execution run: {e}") from e

    def get_runs_by_pipeline(self, pipeline_id: int, limit: int = 10) -> List[PipelineExecutionRun]:
        """Get recent execution runs for a pipeline"""
        try:
            with self.connection_manager.session_scope() as session:
                models = session.query(self.model_class).filter_by(
                    pipeline_id=pipeline_id
                ).limit(limit).all()

                return [self._convert_to_domain_object(m) for m in models]

        except SQLAlchemyError as e:
            logger.error(f"Error getting runs for pipeline {pipeline_id}: {e}")
            raise RepositoryError(f"Failed to get execution runs: {e}") from e