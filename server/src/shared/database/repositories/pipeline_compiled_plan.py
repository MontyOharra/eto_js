"""
Pipeline Compiled Plan Repository
Repository for pipeline_compiled_plans table with CRUD operations
"""
import logging
from typing import Type, Optional
from sqlalchemy import select

from shared.database.repositories.base import BaseRepository
from shared.database.models import PipelineCompiledPlanModel
from shared.types.pipeline_compiled_plan import (
    PipelineCompiledPlanFull,
    PipelineCompiledPlanCreate,
)

logger = logging.getLogger(__name__)


class PipelineCompiledPlanRepository(BaseRepository[PipelineCompiledPlanModel]):
    """
    Repository for Pipeline Compiled Plan CRUD operations.

    Supports dual-mode operation:
    - Standalone: Pass connection_manager, auto-commits
    - UoW: Pass session, caller controls transaction

    This table is append-only (no updates) - compiled plans are immutable.
    Checksum-based deduplication allows multiple pipeline definitions
    to share the same compiled plan.
    """

    @property
    def model_class(self) -> Type[PipelineCompiledPlanModel]:
        """Return the SQLAlchemy model class this repository manages"""
        return PipelineCompiledPlanModel

    def _model_to_full(self, model: PipelineCompiledPlanModel) -> PipelineCompiledPlanFull:
        """Convert ORM model to PipelineCompiledPlanFull dataclass"""
        return PipelineCompiledPlanFull(
            id=model.id,
            plan_checksum=model.plan_checksum,
            compiled_at=model.compiled_at,
            created_at=model.created_at,
            updated_at=model.updated_at
        )

    def create(self, create_data: PipelineCompiledPlanCreate) -> PipelineCompiledPlanFull:
        """
        Create new compiled plan.

        Args:
            create_data: Compiled plan creation data with checksum and timestamp

        Returns:
            Created compiled plan with full details

        Note:
            Caller should check get_by_checksum() first to avoid creating
            duplicate plans with the same checksum.
        """
        with self._get_session() as session:
            # Create ORM model
            compiled_plan = self.model_class(
                plan_checksum=create_data.plan_checksum,
                compiled_at=create_data.compiled_at
            )

            session.add(compiled_plan)
            session.commit()
            session.refresh(compiled_plan)

            return self._model_to_full(compiled_plan)

    def get_by_checksum(self, checksum: str) -> Optional[PipelineCompiledPlanFull]:
        """
        Get compiled plan by checksum (for deduplication).

        This is the critical method for avoiding redundant compilation.
        Before compiling a pipeline, services should check if a plan
        with this checksum already exists.

        Args:
            checksum: SHA-256 checksum of the pruned pipeline structure

        Returns:
            Compiled plan if exists, None otherwise
        """
        with self._get_session() as session:
            stmt = select(self.model_class).where(
                self.model_class.plan_checksum == checksum
            )
            result = session.execute(stmt)
            compiled_plan = result.scalar_one_or_none()

            if compiled_plan is None:
                return None

            return self._model_to_full(compiled_plan)

    def get_by_id(self, plan_id: int) -> Optional[PipelineCompiledPlanFull]:
        """
        Get compiled plan by ID.

        Args:
            plan_id: Compiled plan ID

        Returns:
            Compiled plan with full details or None if not found
        """
        with self._get_session() as session:
            compiled_plan = session.get(self.model_class, plan_id)

            if compiled_plan is None:
                return None

            return self._model_to_full(compiled_plan)