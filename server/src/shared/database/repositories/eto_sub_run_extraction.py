"""
ETO Sub-Run Extraction Repository
Repository for eto_sub_run_extractions table with CRUD operations
"""
import json
import logging
from typing import Any, Dict, List, Type, Optional

from shared.database.repositories.base import BaseRepository
from shared.database.models import EtoSubRunExtractionModel
from shared.types.eto_sub_run_extractions import (
    EtoSubRunExtraction,
    EtoSubRunExtractionCreate,
    EtoSubRunExtractionUpdate,
)

logger = logging.getLogger(__name__)


class EtoSubRunExtractionRepository(BaseRepository[EtoSubRunExtractionModel]):
    """
    Repository for ETO sub-run extraction CRUD operations.

    Handles:
    - Basic CRUD for eto_sub_run_extractions table
    - Conversion between ORM models and domain dataclasses
    - JSON serialization/deserialization for extracted_data field
    - Query operations for finding extractions by sub-run ID and status

    Manages data extraction stage for individual sub-runs.
    """

    @property
    def model_class(self) -> Type[EtoSubRunExtractionModel]:
        """Return the SQLAlchemy model class this repository manages"""
        return EtoSubRunExtractionModel

    # ========== Serialization Methods ==========

    def _deserialize_extracted_data(self, json_str: Optional[str]) -> Optional[List[Dict[str, Any]]]:
        """Convert JSON string to list of extracted field dicts"""
        if json_str is None:
            return None
        return json.loads(json_str)

    def _serialize_extracted_data(self, data: Optional[List[Dict[str, Any]]]) -> Optional[str]:
        """Convert list of extracted field dicts to JSON string"""
        if data is None:
            return None
        return json.dumps(data)

    # ========== Conversion Methods ==========

    def _model_to_domain(self, model: EtoSubRunExtractionModel) -> EtoSubRunExtraction:
        """
        Convert ORM model to EtoSubRunExtraction dataclass.

        Deserializes extracted_data from JSON string to list of dicts.
        """
        return EtoSubRunExtraction(
            id=model.id,
            sub_run_id=model.sub_run_id,
            status=model.status,
            extracted_data=self._deserialize_extracted_data(model.extracted_data),
            error_message=model.error_message,
            started_at=model.started_at,
            completed_at=model.completed_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    # ========== CRUD Operations ==========

    def create(self, data: EtoSubRunExtractionCreate) -> EtoSubRunExtraction:
        """
        Create new sub-run extraction with status = "processing".

        Args:
            data: EtoSubRunExtractionCreate with sub_run_id

        Returns:
            Created EtoSubRunExtraction dataclass
        """
        with self._get_session() as session:
            # Create model with defaults
            model = self.model_class(
                sub_run_id=data.sub_run_id,
                # status defaults to "processing" via model default
                # extracted_data starts as None
                # timestamps auto-set by server_default
            )

            session.add(model)
            session.flush()  # Get ID without committing

            return self._model_to_domain(model)

    def get_by_id(self, extraction_id: int) -> Optional[EtoSubRunExtraction]:
        """
        Get extraction by ID.

        Args:
            extraction_id: Extraction ID

        Returns:
            EtoSubRunExtraction dataclass or None if not found
        """
        with self._get_session() as session:
            model = session.get(self.model_class, extraction_id)

            if model is None:
                return None

            return self._model_to_domain(model)

    def update(self, extraction_id: int, updates: EtoSubRunExtractionUpdate) -> Optional[EtoSubRunExtraction]:
        """
        Update extraction. Only updates provided fields.

        Uses dict keys to distinguish between:
        - Field not provided (key absent) - field will not be updated
        - Field explicitly set to None (key present, value None) - field will be cleared in database
        - Field set to value (key present) - field will be updated to that value

        Note: extracted_data is serialized to JSON before storage.

        Args:
            extraction_id: Extraction ID
            updates: Dict of fields to update (TypedDict with all fields optional)

        Returns:
            Updated EtoSubRunExtraction dataclass or None if not found

        Raises:
            ValueError: If invalid field name provided
        """
        with self._get_session() as session:
            model = session.get(self.model_class, extraction_id)

            if model is None:
                return None

            # Update only provided fields (iterate over dict keys)
            for field, value in updates.items():
                if not hasattr(model, field):
                    raise ValueError(f"Invalid field for extraction update: {field}")

                # Serialize extracted_data to JSON
                if field == "extracted_data":
                    assert type(value) == List[Dict[str, Any]] | None
                    value = self._serialize_extracted_data(value)

                setattr(model, field, value)

            session.flush()  # Persist changes

            return self._model_to_domain(model)

    # ========== Query Operations ==========

    def get_by_sub_run_id(self, sub_run_id: int) -> Optional[EtoSubRunExtraction]:
        """
        Get extraction by sub-run ID.
        Each sub-run should have at most one extraction record.

        Args:
            sub_run_id: Sub-run ID

        Returns:
            EtoSubRunExtraction dataclass or None if not found
        """
        with self._get_session() as session:
            model = session.query(self.model_class).filter_by(sub_run_id=sub_run_id).first()

            if model is None:
                return None

            return self._model_to_domain(model)

    def get_by_status(self, status: str, limit: Optional[int] = None) -> List[EtoSubRunExtraction]:
        """
        Get extractions by status.
        Useful for monitoring/debugging extraction processing.

        Args:
            status: Status to filter by (e.g., "processing", "success", "failure")
            limit: Optional limit on number of results

        Returns:
            List of EtoSubRunExtraction dataclasses
        """
        with self._get_session() as session:
            query = session.query(self.model_class).filter_by(status=status)

            if limit:
                query = query.limit(limit)

            models = query.all()

            return [self._model_to_domain(model) for model in models]

    def delete(self, extraction_id: int) -> bool:
        """
        Delete extraction record by ID.

        Args:
            extraction_id: Extraction record ID

        Returns:
            True if deleted, False if not found
        """
        with self._get_session() as session:
            model = session.get(self.model_class, extraction_id)

            if model is None:
                return False

            session.delete(model)
            session.flush()  # Persist deletion

            logger.debug(f"Deleted extraction record {extraction_id}")
            return True
