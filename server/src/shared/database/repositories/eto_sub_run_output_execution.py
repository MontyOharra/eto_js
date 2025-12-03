"""
ETO Sub-Run Output Execution Repository
Repository for eto_sub_run_output_executions table with CRUD operations
"""
import json
import logging
from typing import Any, Dict, Type, Optional, List

from shared.database.repositories.base import BaseRepository
from shared.database.models import EtoSubRunOutputExecutionModel
from shared.types.eto_sub_run_output_executions import (
    EtoSubRunOutputExecution,
    EtoSubRunOutputExecutionCreate,
    EtoSubRunOutputExecutionUpdate,
)

logger = logging.getLogger(__name__)


class EtoSubRunOutputExecutionRepository(BaseRepository[EtoSubRunOutputExecutionModel]):
    """
    Repository for ETO sub-run output execution CRUD operations.

    Handles:
    - Basic CRUD for eto_sub_run_output_executions table
    - Conversion between ORM models and domain dataclasses
    - JSON serialization/deserialization for input_data and result fields
    - Query operations for finding output executions by sub-run ID and status

    Manages output execution stage for individual sub-runs (order creation, etc.).
    """

    @property
    def model_class(self) -> Type[EtoSubRunOutputExecutionModel]:
        """Return the SQLAlchemy model class this repository manages"""
        return EtoSubRunOutputExecutionModel

    # ========== Serialization Methods ==========

    def _deserialize_json_dict(self, json_str: Optional[str]) -> Optional[Dict[str, Any]]:
        """Convert JSON string to dict"""
        if json_str is None:
            return None
        return json.loads(json_str)

    def _serialize_json_dict(self, data: Optional[Dict[str, Any]]) -> Optional[str]:
        """Convert dict to JSON string"""
        if data is None:
            return None
        return json.dumps(data)

    # ========== Conversion Methods ==========

    def _model_to_domain(self, model: EtoSubRunOutputExecutionModel) -> EtoSubRunOutputExecution:
        """
        Convert ORM model to EtoSubRunOutputExecution dataclass.

        Deserializes input_data and result from JSON strings to dicts.
        """
        return EtoSubRunOutputExecution(
            id=model.id,
            sub_run_id=model.sub_run_id,
            module_id=model.module_id,
            input_data=self._deserialize_json_dict(model.input_data_json),
            status=model.status,
            result=self._deserialize_json_dict(model.result_json),
            error_message=model.error_message,
            error_type=model.error_type,
            started_at=model.started_at,
            completed_at=model.completed_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    # ========== CRUD Operations ==========

    def create(self, data: EtoSubRunOutputExecutionCreate) -> EtoSubRunOutputExecution:
        """
        Create new sub-run output execution with status = "pending".

        Args:
            data: EtoSubRunOutputExecutionCreate with sub_run_id, module_id, and input_data

        Returns:
            Created EtoSubRunOutputExecution dataclass
        """
        with self._get_session() as session:
            # Create model with serialized input_data
            model = self.model_class(
                sub_run_id=data.sub_run_id,
                module_id=data.module_id,
                input_data_json=self._serialize_json_dict(data.input_data),
                # status defaults to "pending" via model default
                # result, error fields start as None
                # timestamps auto-set by server_default
            )

            session.add(model)
            session.flush()  # Get ID without committing

            return self._model_to_domain(model)

    def get_by_id(self, output_execution_id: int) -> Optional[EtoSubRunOutputExecution]:
        """
        Get output execution by ID.

        Args:
            output_execution_id: Output execution ID

        Returns:
            EtoSubRunOutputExecution dataclass or None if not found
        """
        with self._get_session() as session:
            model = session.get(self.model_class, output_execution_id)

            if model is None:
                return None

            return self._model_to_domain(model)

    def update(self, output_execution_id: int, updates: EtoSubRunOutputExecutionUpdate) -> Optional[EtoSubRunOutputExecution]:
        """
        Update output execution. Only updates provided fields.

        Uses dict keys to distinguish between:
        - Field not provided (key absent) - field will not be updated
        - Field explicitly set to None (key present, value None) - field will be cleared in database
        - Field set to value (key present) - field will be updated to that value

        Note: input_data and result are serialized to JSON before storage.

        Args:
            output_execution_id: Output execution ID
            updates: Dict of fields to update (TypedDict with all fields optional)

        Returns:
            Updated EtoSubRunOutputExecution dataclass or None if not found

        Raises:
            ValueError: If invalid field name provided
        """
        with self._get_session() as session:
            model = session.get(self.model_class, output_execution_id)

            if model is None:
                return None

            # Update only provided fields (iterate over dict keys)
            for field, value in updates.items():
                # Map domain field names to model field names
                model_field = field
                if field == "input_data":
                    model_field = "input_data_json"
                    value = self._serialize_json_dict(value)
                elif field == "result":
                    model_field = "result_json"
                    value = self._serialize_json_dict(value)

                if not hasattr(model, model_field):
                    raise ValueError(f"Invalid field for output execution update: {field}")

                setattr(model, model_field, value)

            session.flush()  # Persist changes

            return self._model_to_domain(model)

    # ========== Query Operations ==========

    def get_by_sub_run_id(self, sub_run_id: int) -> Optional[EtoSubRunOutputExecution]:
        """
        Get output execution by sub-run ID.
        Each sub-run should have at most one output execution record.

        Args:
            sub_run_id: Sub-run ID

        Returns:
            EtoSubRunOutputExecution dataclass or None if not found
        """
        with self._get_session() as session:
            model = session.query(self.model_class).filter_by(sub_run_id=sub_run_id).first()

            if model is None:
                return None

            return self._model_to_domain(model)

    def get_by_status(self, status: str, limit: Optional[int] = None) -> List[EtoSubRunOutputExecution]:
        """
        Get output executions by status.
        Useful for monitoring/debugging output execution processing.

        Args:
            status: Status to filter by (e.g., "pending", "processing", "success", "failure")
            limit: Optional limit on number of results

        Returns:
            List of EtoSubRunOutputExecution dataclasses
        """
        with self._get_session() as session:
            query = session.query(self.model_class).filter_by(status=status)

            if limit:
                query = query.limit(limit)

            models = query.all()

            return [self._model_to_domain(model) for model in models]

    def get_pending(self, limit: Optional[int] = None) -> List[EtoSubRunOutputExecution]:
        """
        Get pending output executions (convenience method).
        Useful for the output service to pick up pending executions.

        Args:
            limit: Optional limit on number of results

        Returns:
            List of EtoSubRunOutputExecution dataclasses with status="pending"
        """
        return self.get_by_status("pending", limit=limit)

    def delete(self, output_execution_id: int) -> bool:
        """
        Delete output execution record by ID.

        Args:
            output_execution_id: Output execution record ID

        Returns:
            True if deleted, False if not found
        """
        with self._get_session() as session:
            model = session.get(self.model_class, output_execution_id)

            if model is None:
                return False

            session.delete(model)
            session.flush()  # Persist deletion

            logger.debug(f"Deleted output execution record {output_execution_id}")
            return True
