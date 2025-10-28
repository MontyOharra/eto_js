"""
ETO Run Repository
Repository for eto_runs table with CRUD operations
"""
import logging
from typing import Type, Optional, Literal

from shared.database.repositories.base import BaseRepository
from shared.database.models import EtoRunModel

# TODO: Import domain types when defined
# from shared.types.eto_runs import (
#     EtoRun,
#     EtoRunListView,
#     EtoRunCreate,
# )

logger = logging.getLogger(__name__)


class EtoRunRepository(BaseRepository[EtoRunModel]):
    """
    Repository for ETO run CRUD operations.

    Handles:
    - Basic CRUD for eto_runs table
    - List queries with filtering (status) and sorting
    - Pagination support
    - Status updates (not_started, processing, success, failure, etc.)

    Note: Stage-specific data managed by separate repositories:
    - EtoRunTemplateMatchingRepository
    - EtoRunDataExtractionRepository
    - EtoRunPipelineExecutionRepository
    """

    @property
    def model_class(self) -> Type[EtoRunModel]:
        """Return the SQLAlchemy model class this repository manages"""
        return EtoRunModel

    # TODO: Implement repository methods:
    # - create(run_data: EtoRunCreate) -> EtoRun
    # - get_by_id(run_id: int) -> EtoRun | None
    # - list_runs(status, sort_by, sort_order, limit, offset) -> list[EtoRunListView]
    # - update_status(run_id: int, status: EtoRunStatus) -> EtoRun
    # - delete(run_id: int) -> None
    # - bulk_delete(run_ids: list[int]) -> None
