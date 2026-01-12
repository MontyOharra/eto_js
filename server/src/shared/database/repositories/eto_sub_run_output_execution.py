"""
ETO Sub-Run Output Execution Repository

Repository for eto_sub_run_output_executions table with CRUD operations.
This table stores data snapshots of pipeline output - all processing state
tracking is handled by the pending_actions system.
"""
import json
import logging
from typing import Any

from shared.database.repositories.base import BaseRepository
from shared.database.models import EtoSubRunOutputExecutionModel
from shared.types.eto_sub_run_output_executions import (
    EtoSubRunOutputExecution,
    EtoSubRunOutputExecutionCreate,
)

logger = logging.getLogger(__name__)


class EtoSubRunOutputExecutionRepository(BaseRepository[EtoSubRunOutputExecutionModel]):
    """
    Repository for ETO sub-run output execution CRUD operations.

    Handles:
    - Basic CRUD for eto_sub_run_output_executions table
    - Conversion between ORM models and domain dataclasses
    - JSON serialization/deserialization for output_channel_data
    - Query operations for finding output executions by sub-run ID
    """

    @property
    def model_class(self) -> type[EtoSubRunOutputExecutionModel]:
        """Return the SQLAlchemy model class this repository manages"""
        return EtoSubRunOutputExecutionModel

    # ========== Serialization Methods ==========

    def _deserialize_json_dict(self, json_str: str | None) -> dict[str, Any] | None:
        """Convert JSON string to dict"""
        if json_str is None:
            return None
        return json.loads(json_str)

    def _serialize_json_dict(self, data: dict[str, Any] | None) -> str | None:
        """Convert dict to JSON string, handling datetime objects"""
        if data is None:
            return None
        return json.dumps(data, default=self._json_serializer)

    def _json_serializer(self, obj: Any) -> Any:
        """Custom JSON serializer for objects not serializable by default json code"""
        from datetime import datetime, date
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, date):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

    # ========== Conversion Methods ==========

    def _model_to_domain(self, model: EtoSubRunOutputExecutionModel) -> EtoSubRunOutputExecution:
        """
        Convert ORM model to EtoSubRunOutputExecution dataclass.
        """
        return EtoSubRunOutputExecution(
            id=model.id,
            sub_run_id=model.sub_run_id,
            customer_id=model.customer_id,
            hawb=model.hawb,
            output_channel_data=self._deserialize_json_dict(model.output_channel_data) or {},
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    # ========== CRUD Operations ==========

    def create(self, data: EtoSubRunOutputExecutionCreate) -> EtoSubRunOutputExecution:
        """
        Create new sub-run output execution record.

        Args:
            data: EtoSubRunOutputExecutionCreate with sub_run_id, customer_id, hawb, output_channel_data

        Returns:
            Created EtoSubRunOutputExecution dataclass
        """
        with self._get_session() as session:
            model = self.model_class(
                sub_run_id=data.sub_run_id,
                customer_id=data.customer_id,
                hawb=data.hawb,
                output_channel_data=self._serialize_json_dict(data.output_channel_data),
            )

            session.add(model)
            session.flush()  # Get ID without committing

            return self._model_to_domain(model)

    def get_by_id(self, output_execution_id: int) -> EtoSubRunOutputExecution | None:
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

    # ========== Query Operations ==========

    def get_by_sub_run_id(self, sub_run_id: int) -> list[EtoSubRunOutputExecution]:
        """
        Get all output executions for a sub-run.

        Args:
            sub_run_id: Sub-run ID

        Returns:
            List of EtoSubRunOutputExecution dataclasses
        """
        with self._get_session() as session:
            models = session.query(self.model_class).filter_by(sub_run_id=sub_run_id).all()
            return [self._model_to_domain(model) for model in models]

    def get_by_customer_and_hawb(self, customer_id: int, hawb: str) -> list[EtoSubRunOutputExecution]:
        """
        Get output executions by customer_id and hawb.
        Useful for looking up all executions for a specific order identifier.

        Args:
            customer_id: Customer ID
            hawb: HAWB value

        Returns:
            List of EtoSubRunOutputExecution dataclasses
        """
        with self._get_session() as session:
            models = session.query(self.model_class).filter_by(
                customer_id=customer_id,
                hawb=hawb
            ).all()
            return [self._model_to_domain(model) for model in models]

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
            session.flush()

            logger.debug(f"Deleted output execution record {output_execution_id}")
            return True

    def delete_by_sub_run_id(self, sub_run_id: int) -> int:
        """
        Delete all output execution records for a sub-run.

        Args:
            sub_run_id: Sub-run ID

        Returns:
            Number of records deleted
        """
        with self._get_session() as session:
            count = (
                session.query(self.model_class)
                .filter_by(sub_run_id=sub_run_id)
                .delete(synchronize_session=False)
            )
            session.flush()

            logger.debug(f"Deleted {count} output execution records for sub-run {sub_run_id}")
            return count
