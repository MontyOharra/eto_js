"""
ETO Run Data Extraction Repository
Repository for eto_run_data_extractions table
"""
import json
import logging
from typing import Type, Optional

from shared.database.repositories.base import BaseRepository
from shared.database.models import EtoRunDataExtractionModel

# TODO: Import domain types when defined
# from shared.types.eto_runs import (
#     EtoRunDataExtraction,
#     EtoRunDataExtractionCreate,
# )

logger = logging.getLogger(__name__)


class EtoRunDataExtractionRepository(BaseRepository[EtoRunDataExtractionModel]):
    """
    Repository for data extraction stage records.

    Handles:
    - Creating extraction records
    - Updating status and results
    - JSON serialization of extracted_data field
    """

    @property
    def model_class(self) -> Type[EtoRunDataExtractionModel]:
        """Return the SQLAlchemy model class this repository manages"""
        return EtoRunDataExtractionModel

    # TODO: Implement repository methods:
    # - create(stage_data: EtoRunDataExtractionCreate) -> EtoRunDataExtraction
    # - get_by_run_id(run_id: int) -> EtoRunDataExtraction | None
    # - update_success(run_id: int, extracted_data: dict) -> EtoRunDataExtraction
    # - update_failure(run_id: int, error_message: str) -> EtoRunDataExtraction
    #
    # Private serialization methods:
    # - _serialize_extracted_data(data: dict) -> str
    # - _deserialize_extracted_data(json_str: str) -> dict
