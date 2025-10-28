"""
ETO Runs Service
Business logic for ETO processing lifecycle and control operations
"""
import logging
from typing import Optional, Literal

# TODO: Import domain types when defined
# from shared.types.eto_runs import (
#     EtoRun,
#     EtoRunListView,
#     EtoRunDetail,
#     EtoRunCreate,
#     ...
# )

# TODO: Import repositories when defined
# from shared.database.repositories.eto_run import EtoRunRepository
# from shared.database.repositories.eto_run_template_matching import EtoRunTemplateMatchingRepository
# from shared.database.repositories.eto_run_data_extraction import EtoRunDataExtractionRepository
# from shared.database.repositories.eto_run_pipeline_execution import EtoRunPipelineExecutionRepository

logger = logging.getLogger(__name__)


class EtoRunsService:
    """
    Service for ETO run lifecycle management.

    Handles:
    - Listing runs with filtering and pagination
    - Retrieving run details with all stage data
    - Creating runs from manual PDF upload
    - Bulk operations (reprocess, skip, delete)
    """

    def __init__(
        self,
        # TODO: Add repository dependencies
    ):
        """Initialize service with repository dependencies."""
        pass

    # TODO: Implement service methods:
    # - list_runs(status, sort_by, sort_order, limit, offset) -> list[EtoRunListView]
    # - get_run_detail(run_id: int) -> EtoRunDetail
    # - create_run_from_upload(pdf_file_id: int) -> EtoRun
    # - reprocess_runs(run_ids: list[int]) -> None
    # - skip_runs(run_ids: list[int]) -> None
    # - delete_runs(run_ids: list[int]) -> None
