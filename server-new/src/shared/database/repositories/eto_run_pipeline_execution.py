"""
ETO Run Pipeline Execution Repository
Repository for eto_run_pipeline_executions table with CRUD operations
"""
import logging
from typing import Type, Optional
from datetime import datetime
from sqlalchemy import select

from shared.database.repositories.base import BaseRepository
from shared.database.models import EtoRunPipelineExecutionModel, EtoStepStatus
from shared.types.pipeline_execution import (
    PipelineExecutionRun,
    PipelineExecutionRunCreate,
)

logger = logging.getLogger(__name__)


class EtoRunPipelineExecutionRepository(BaseRepository[EtoRunPipelineExecutionModel]):
    """
    Repository for Pipeline Execution Run CRUD operations.

    Supports dual-mode operation:
    - Standalone: Pass connection_manager, auto-commits
    - UoW: Pass session, caller controls transaction

    Manages execution run lifecycle: create → update status → complete
    """

    @property
    def model_class(self) -> Type[EtoRunPipelineExecutionModel]:
        """Return the SQLAlchemy model class this repository manages"""
        return EtoRunPipelineExecutionModel

    def _model_to_domain(self, model: EtoRunPipelineExecutionModel) -> PipelineExecutionRun:
        """Convert ORM model to PipelineExecutionRun dataclass"""
        return PipelineExecutionRun(
            id=model.id,
            eto_run_id=model.eto_run_id,
            status=model.status,
            executed_actions=model.executed_actions,
            started_at=model.started_at,
            completed_at=model.completed_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def create(self, data: PipelineExecutionRunCreate) -> PipelineExecutionRun:
        """
        Create new pipeline execution run.

        Typically called at the start of pipeline execution with status=PROCESSING.

        Args:
            data: Execution run creation data

        Returns:
            Created execution run with full details
        """
        with self._get_session() as session:
            # Create ORM model
            run_model = self.model_class(
                eto_run_id=data.eto_run_id,
                status=data.status,
                executed_actions=data.executed_actions,
                started_at=data.started_at,
            )

            session.add(run_model)
            session.commit()
            session.refresh(run_model)

            return self._model_to_domain(run_model)

    def get_by_id(self, run_id: int) -> Optional[PipelineExecutionRun]:
        """
        Get execution run by ID.

        Args:
            run_id: Execution run ID

        Returns:
            Execution run with full details or None if not found
        """
        with self._get_session() as session:
            run = session.get(self.model_class, run_id)

            if run is None:
                return None

            return self._model_to_domain(run)

    def get_by_eto_run_id(self, eto_run_id: int) -> Optional[PipelineExecutionRun]:
        """
        Get execution run by ETO run ID.

        Useful for finding the execution associated with a specific ETO run.

        Args:
            eto_run_id: ETO run ID

        Returns:
            Most recent execution run for the ETO run or None if not found
        """
        with self._get_session() as session:
            stmt = select(self.model_class).where(
                self.model_class.eto_run_id == eto_run_id
            ).order_by(self.model_class.created_at.desc())

            result = session.execute(stmt)
            run = result.scalars().first()

            if run is None:
                return None

            return self._model_to_domain(run)

    def update_status(
        self,
        run_id: int,
        status: EtoStepStatus,
        completed_at: Optional[datetime] = None
    ) -> PipelineExecutionRun:
        """
        Update execution run status.

        Called when pipeline execution completes (success or failure).

        Args:
            run_id: Execution run ID
            status: New status (SUCCESS or FAILURE)
            completed_at: Completion timestamp (optional, defaults to now)

        Returns:
            Updated execution run

        Raises:
            ValueError: If run not found
        """
        with self._get_session() as session:
            run = session.get(self.model_class, run_id)

            if run is None:
                raise ValueError(f"Execution run {run_id} not found")

            # Update status
            run.status = status

            # Set completed_at if provided or if completing
            if status in (EtoStepStatus.SUCCESS, EtoStepStatus.FAILURE):
                run.completed_at = completed_at or datetime.utcnow()

            session.commit()
            session.refresh(run)

            return self._model_to_domain(run)
