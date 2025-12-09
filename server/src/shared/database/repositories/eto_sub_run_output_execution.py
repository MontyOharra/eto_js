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
    - JSON serialization/deserialization for output_channel_data
    - Query operations for finding output executions by sub-run ID and status
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
            status=model.status,
            action_taken=model.action_taken,
            htc_order_number=model.htc_order_number,
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
                # status defaults to "pending" via model default
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

            # Update only provided fields
            for field, value in updates.items():
                if not hasattr(model, field):
                    raise ValueError(f"Invalid field for output execution update: {field}")
                setattr(model, field, value)

            session.flush()

            return self._model_to_domain(model)

    # ========== Query Operations ==========

    def get_by_sub_run_id(self, sub_run_id: int) -> List[EtoSubRunOutputExecution]:
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

    def get_by_status(self, status: str, limit: Optional[int] = None) -> List[EtoSubRunOutputExecution]:
        """
        Get output executions by status.

        Args:
            status: Status to filter by (e.g., "pending", "processing", "success", "error")
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

        Args:
            limit: Optional limit on number of results

        Returns:
            List of EtoSubRunOutputExecution dataclasses with status="pending"
        """
        return self.get_by_status("pending", limit=limit)

    def get_by_customer_and_hawb(self, customer_id: int, hawb: str) -> List[EtoSubRunOutputExecution]:
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
