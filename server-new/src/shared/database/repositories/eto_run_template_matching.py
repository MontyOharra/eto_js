"""
ETO Run Template Matching Repository
Repository for eto_run_template_matchings table
"""
import logging
from typing import Type, Optional

from shared.database.repositories.base import BaseRepository
from shared.database.models import EtoRunTemplateMatchingModel

# TODO: Import domain types when defined
# from shared.types.eto_runs import (
#     EtoRunTemplateMatching,
#     EtoRunTemplateMatchingCreate,
# )

logger = logging.getLogger(__name__)


class EtoRunTemplateMatchingRepository(BaseRepository[EtoRunTemplateMatchingModel]):
    """
    Repository for template matching stage records.

    Handles:
    - Creating template matching records
    - Updating status and results
    - Recording matched template or error information
    """

    @property
    def model_class(self) -> Type[EtoRunTemplateMatchingModel]:
        """Return the SQLAlchemy model class this repository manages"""
        return EtoRunTemplateMatchingModel

    # TODO: Implement repository methods:
    # - create(stage_data: EtoRunTemplateMatchingCreate) -> EtoRunTemplateMatching
    # - get_by_run_id(run_id: int) -> EtoRunTemplateMatching | None
    # - update_success(run_id: int, template_id: int, version_id: int) -> EtoRunTemplateMatching
    # - update_failure(run_id: int, error_message: str) -> EtoRunTemplateMatching
