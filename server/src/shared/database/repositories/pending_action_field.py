"""
Pending Action Field Repository

Repository for pending_action_fields table with CRUD operations and specialized queries.
"""
import json
import logging
from typing import Any

from sqlalchemy import and_, func

from shared.database.repositories.base import BaseRepository
from shared.database.models import PendingActionFieldModel
from shared.exceptions.service import ObjectNotFoundError
from shared.types.pending_actions import (
    PendingActionField,
    PendingActionFieldCreate,
    PendingActionFieldUpdate,
)

logger = logging.getLogger(__name__)


class PendingActionFieldRepository(BaseRepository[PendingActionFieldModel]):
    """
    Repository for pending action field CRUD operations.

    Handles:
    - Basic CRUD for pending_action_fields table
    - Conversion between ORM models and domain dataclasses
    - Specialized queries for field retrieval, conflict resolution, and cleanup
    """

    @property
    def model_class(self) -> type[PendingActionFieldModel]:
        """Return the SQLAlchemy model class this repository manages"""
        return PendingActionFieldModel

    # ========== Conversion Methods ==========

    def _model_to_domain(self, model: PendingActionFieldModel) -> PendingActionField:
        """Convert ORM model to PendingActionField dataclass."""
        # Parse JSON value
        try:
            value = json.loads(model.value)
        except (json.JSONDecodeError, TypeError):
            value = model.value

        return PendingActionField(
            id=model.id,
            pending_action_id=model.pending_action_id,
            output_execution_id=model.output_execution_id,
            field_name=model.field_name,
            value=value,
            is_selected=model.is_selected,
            is_approved_for_update=model.is_approved_for_update,
        )

    def _serialize_value(self, value: Any) -> str:
        """Serialize a value to JSON string for storage."""
        if isinstance(value, str):
            # Already a string - check if it's valid JSON
            try:
                json.loads(value)
                return value  # Already valid JSON string
            except (json.JSONDecodeError, TypeError):
                # Plain string - serialize it
                return json.dumps(value)
        elif hasattr(value, 'model_dump'):
            # Pydantic model - convert to dict first
            return json.dumps(value.model_dump())
        elif isinstance(value, list) and value and hasattr(value[0], 'model_dump'):
            # List of Pydantic models
            return json.dumps([v.model_dump() for v in value])
        else:
            # Object/list - serialize to JSON
            return json.dumps(value)

    # ========== CRUD Operations ==========

    def create(self, data: PendingActionFieldCreate) -> PendingActionField:
        """
        Create new pending action field.

        Args:
            data: PendingActionFieldCreate with field data

        Returns:
            Created PendingActionField dataclass
        """
        with self._get_session() as session:
            model = self.model_class(
                pending_action_id=data.pending_action_id,
                output_execution_id=data.output_execution_id,
                field_name=data.field_name,
                value=self._serialize_value(data.value),
                is_selected=data.is_selected,
                is_approved_for_update=data.is_approved_for_update,
            )

            session.add(model)
            session.flush()

            return self._model_to_domain(model)

    def get_by_id(self, field_id: int) -> PendingActionField | None:
        """
        Get pending action field by ID.

        Args:
            field_id: Field ID

        Returns:
            PendingActionField dataclass or None if not found
        """
        with self._get_session() as session:
            model = session.get(self.model_class, field_id)

            if model is None:
                return None

            return self._model_to_domain(model)

    def update(self, field_id: int, updates: PendingActionFieldUpdate) -> PendingActionField:
        """
        Update pending action field. Only updates provided fields.

        Args:
            field_id: Field ID
            updates: PendingActionFieldUpdate with fields to update

        Returns:
            Updated PendingActionField dataclass

        Raises:
            ObjectNotFoundError: If field with given ID does not exist
        """
        with self._get_session() as session:
            model = session.get(self.model_class, field_id)

            if model is None:
                raise ObjectNotFoundError(f"Pending action field {field_id} not found")

            # Update only fields that were explicitly set
            for field_name in updates.model_fields_set:
                value = getattr(updates, field_name)
                setattr(model, field_name, value)

            session.flush()

            return self._model_to_domain(model)

    def delete(self, field_id: int) -> bool:
        """
        Delete pending action field by ID.

        Args:
            field_id: Field ID

        Returns:
            True if deleted, False if not found
        """
        with self._get_session() as session:
            model = session.get(self.model_class, field_id)

            if model is None:
                return False

            session.delete(model)
            session.flush()

            logger.debug(f"Deleted pending action field {field_id}")
            return True

    # ========== Specialized Query Operations ==========

    def get_fields_for_action(self, action_id: int) -> list[PendingActionField]:
        """
        Get all fields for a pending action.

        Args:
            action_id: Pending action ID

        Returns:
            List of PendingActionField dataclasses
        """
        with self._get_session() as session:
            models = (
                session.query(self.model_class)
                .filter(self.model_class.pending_action_id == action_id)
                .order_by(self.model_class.field_name, self.model_class.id)
                .all()
            )

            return [self._model_to_domain(model) for model in models]

    def get_selected_fields_for_action(self, action_id: int) -> dict[str, PendingActionField]:
        """
        Get only selected values for a pending action, keyed by field_name.

        Used during execution to get the final values to send to HTC.

        Args:
            action_id: Pending action ID

        Returns:
            Dict mapping field_name to the selected PendingActionField
        """
        with self._get_session() as session:
            models = (
                session.query(self.model_class)
                .filter(
                    and_(
                        self.model_class.pending_action_id == action_id,
                        self.model_class.is_selected == True,
                    )
                )
                .all()
            )

            return {
                model.field_name: self._model_to_domain(model)
                for model in models
            }

    def get_fields_by_output_execution(self, output_execution_id: int) -> list[PendingActionField]:
        """
        Get all fields contributed by a specific output execution.

        Used during cleanup to find fields that need to be removed when
        an output execution is reprocessed or deleted.

        Args:
            output_execution_id: Output execution ID

        Returns:
            List of PendingActionField dataclasses
        """
        with self._get_session() as session:
            models = (
                session.query(self.model_class)
                .filter(self.model_class.output_execution_id == output_execution_id)
                .all()
            )

            return [self._model_to_domain(model) for model in models]

    def delete_by_output_execution(self, output_execution_id: int) -> int:
        """
        Delete all fields contributed by a specific output execution.

        Used during cleanup when an output execution is reprocessed or deleted.

        Args:
            output_execution_id: Output execution ID

        Returns:
            Number of fields deleted
        """
        with self._get_session() as session:
            count = (
                session.query(self.model_class)
                .filter(self.model_class.output_execution_id == output_execution_id)
                .delete(synchronize_session=False)
            )

            session.flush()

            logger.debug(f"Deleted {count} fields for output execution {output_execution_id}")
            return count

    def delete_by_action_id(self, action_id: int) -> int:
        """
        Delete all fields for a pending action.

        Used when deleting an action entirely.

        Args:
            action_id: Pending action ID

        Returns:
            Number of fields deleted
        """
        with self._get_session() as session:
            count = (
                session.query(self.model_class)
                .filter(self.model_class.pending_action_id == action_id)
                .delete(synchronize_session=False)
            )

            session.flush()

            logger.debug(f"Deleted {count} fields for action {action_id}")
            return count

    def set_selection_for_field(
        self,
        action_id: int,
        field_name: str,
        selected_field_id: int
    ) -> None:
        """
        Set one field value as selected, deselecting all others for that field.

        Performs a single UPDATE query for efficiency.

        Args:
            action_id: Pending action ID
            field_name: Field name to update
            selected_field_id: ID of the field value to select
        """
        with self._get_session() as session:
            # Use a single UPDATE with CASE expression
            # SET is_selected = (id = selected_field_id)
            session.query(self.model_class).filter(
                and_(
                    self.model_class.pending_action_id == action_id,
                    self.model_class.field_name == field_name,
                )
            ).update(
                {
                    self.model_class.is_selected: (
                        self.model_class.id == selected_field_id
                    )
                },
                synchronize_session=False,
            )

            session.flush()

            logger.debug(
                f"Set field {selected_field_id} as selected for "
                f"action {action_id}, field {field_name}"
            )

    def clear_selection_for_field(self, action_id: int, field_name: str) -> None:
        """
        Clear selection for all values of a field (set all is_selected = FALSE).

        Used when a conflict is detected - all values become unselected
        until user resolves the conflict.

        Args:
            action_id: Pending action ID
            field_name: Field name to clear selection for
        """
        with self._get_session() as session:
            session.query(self.model_class).filter(
                and_(
                    self.model_class.pending_action_id == action_id,
                    self.model_class.field_name == field_name,
                )
            ).update(
                {self.model_class.is_selected: False},
                synchronize_session=False,
            )

            session.flush()

            logger.debug(
                f"Cleared selection for action {action_id}, field {field_name}"
            )

    def count_by_field_name(self, action_id: int) -> dict[str, int]:
        """
        Count values per field for a pending action.

        Used for conflict detection - if count > 1 for a field, there may be
        a conflict (unless values are identical).

        Args:
            action_id: Pending action ID

        Returns:
            Dict mapping field_name to count of values
        """
        with self._get_session() as session:
            results = (
                session.query(
                    self.model_class.field_name,
                    func.count(self.model_class.id).label("row_count"),
                )
                .filter(self.model_class.pending_action_id == action_id)
                .group_by(self.model_class.field_name)
                .all()
            )

            return {row.field_name: row.row_count for row in results}

    def has_extracted_fields(self, action_id: int) -> bool:
        """
        Check if any fields with output_execution_id IS NOT NULL exist for an action.

        Used during cleanup to determine if action should be deleted
        (no extracted fields remaining) or just recalculated.

        Args:
            action_id: Pending action ID

        Returns:
            True if at least one extracted field exists, False otherwise
        """
        with self._get_session() as session:
            exists = (
                session.query(self.model_class)
                .filter(
                    and_(
                        self.model_class.pending_action_id == action_id,
                        self.model_class.output_execution_id.isnot(None),
                    )
                )
                .first()
            ) is not None

            return exists
