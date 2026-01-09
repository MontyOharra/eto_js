"""
Pending Update History Repository
Repository for pending_update_history table with CRUD operations
"""
import logging
from typing import Type, Optional, List

from shared.database.repositories.base import BaseRepository
from shared.database.models import PendingUpdateHistoryModel
from server.deprecated.pending_orders_old import (
    PendingUpdateHistory,
    PendingUpdateHistoryCreate,
    PendingUpdateHistoryUpdate,
)

logger = logging.getLogger(__name__)


class PendingUpdateHistoryRepository(BaseRepository[PendingUpdateHistoryModel]):
    """
    Repository for pending update history CRUD operations.

    Handles:
    - Basic CRUD for pending_update_history table
    - Conversion between ORM models and domain dataclasses
    - Query operations for finding history entries by update and field
    - Conflict resolution operations (is_selected flag)

    Mirrors PendingOrderHistoryRepository for consistency.
    """

    @property
    def model_class(self) -> Type[PendingUpdateHistoryModel]:
        """Return the SQLAlchemy model class this repository manages"""
        return PendingUpdateHistoryModel

    # ========== Conversion Methods ==========

    def _model_to_domain(self, model: PendingUpdateHistoryModel) -> PendingUpdateHistory:
        """
        Convert ORM model to PendingUpdateHistory dataclass.
        """
        return PendingUpdateHistory(
            id=model.id,
            pending_update_id=model.pending_update_id,
            sub_run_id=model.sub_run_id,
            field_name=model.field_name,
            field_value=model.field_value,
            is_selected=model.is_selected,
            contributed_at=model.contributed_at,
        )

    # ========== CRUD Operations ==========

    def create(self, data: PendingUpdateHistoryCreate) -> PendingUpdateHistory:
        """
        Create new history entry.

        Args:
            data: PendingUpdateHistoryCreate with pending_update_id, sub_run_id, field_name, field_value

        Returns:
            Created PendingUpdateHistory dataclass
        """
        with self._get_session() as session:
            model = self.model_class(
                pending_update_id=data.pending_update_id,
                sub_run_id=data.sub_run_id,
                field_name=data.field_name,
                field_value=data.field_value,
                is_selected=data.is_selected,
            )

            session.add(model)
            session.flush()  # Get ID without committing

            return self._model_to_domain(model)

    def create_batch(self, entries: List[PendingUpdateHistoryCreate]) -> List[PendingUpdateHistory]:
        """
        Create multiple history entries in a batch.

        Args:
            entries: List of PendingUpdateHistoryCreate

        Returns:
            List of created PendingUpdateHistory dataclasses
        """
        with self._get_session() as session:
            models = []
            for data in entries:
                model = self.model_class(
                    pending_update_id=data.pending_update_id,
                    sub_run_id=data.sub_run_id,
                    field_name=data.field_name,
                    field_value=data.field_value,
                    is_selected=data.is_selected,
                )
                session.add(model)
                models.append(model)

            session.flush()  # Get IDs without committing

            return [self._model_to_domain(model) for model in models]

    def get_by_id(self, history_id: int) -> Optional[PendingUpdateHistory]:
        """
        Get history entry by ID.

        Args:
            history_id: History entry ID

        Returns:
            PendingUpdateHistory dataclass or None if not found
        """
        with self._get_session() as session:
            model = session.get(self.model_class, history_id)

            if model is None:
                return None

            return self._model_to_domain(model)

    def update(self, history_id: int, updates: PendingUpdateHistoryUpdate) -> Optional[PendingUpdateHistory]:
        """
        Update history entry. Only updates provided fields.

        Args:
            history_id: History entry ID
            updates: Dict of fields to update (typically just is_selected)

        Returns:
            Updated PendingUpdateHistory dataclass or None if not found

        Raises:
            ValueError: If invalid field name provided
        """
        with self._get_session() as session:
            model = session.get(self.model_class, history_id)

            if model is None:
                return None

            # Update only provided fields
            for field, value in updates.items():
                if not hasattr(model, field):
                    raise ValueError(f"Invalid field for history update: {field}")
                setattr(model, field, value)

            session.flush()

            return self._model_to_domain(model)

    def delete(self, history_id: int) -> bool:
        """
        Delete history entry by ID.

        Args:
            history_id: History entry ID

        Returns:
            True if deleted, False if not found
        """
        with self._get_session() as session:
            model = session.get(self.model_class, history_id)

            if model is None:
                return False

            session.delete(model)
            session.flush()

            logger.debug(f"Deleted pending update history entry {history_id}")
            return True

    # ========== Query Operations ==========

    def get_by_pending_update_id(self, pending_update_id: int) -> List[PendingUpdateHistory]:
        """
        Get all history entries for a pending update.

        Args:
            pending_update_id: Pending update ID

        Returns:
            List of PendingUpdateHistory dataclasses ordered by contributed_at
        """
        with self._get_session() as session:
            models = session.query(self.model_class).filter_by(
                pending_update_id=pending_update_id
            ).order_by(self.model_class.contributed_at.asc()).all()

            return [self._model_to_domain(model) for model in models]

    def get_by_field(self, pending_update_id: int, field_name: str) -> List[PendingUpdateHistory]:
        """
        Get history entries for a specific field on a pending update.

        Args:
            pending_update_id: Pending update ID
            field_name: Field name to filter by

        Returns:
            List of PendingUpdateHistory dataclasses ordered by contributed_at
        """
        with self._get_session() as session:
            models = session.query(self.model_class).filter_by(
                pending_update_id=pending_update_id,
                field_name=field_name
            ).order_by(self.model_class.contributed_at.asc()).all()

            return [self._model_to_domain(model) for model in models]

    def get_selected_for_field(self, pending_update_id: int, field_name: str) -> Optional[PendingUpdateHistory]:
        """
        Get the selected history entry for a specific field (if any).

        Args:
            pending_update_id: Pending update ID
            field_name: Field name to filter by

        Returns:
            PendingUpdateHistory with is_selected=True or None if none selected
        """
        with self._get_session() as session:
            model = session.query(self.model_class).filter_by(
                pending_update_id=pending_update_id,
                field_name=field_name,
                is_selected=True
            ).first()

            if model is None:
                return None

            return self._model_to_domain(model)

    def clear_selection_for_field(self, pending_update_id: int, field_name: str) -> int:
        """
        Clear is_selected flag for all entries of a specific field.
        Used before setting a new selection during conflict resolution.

        Args:
            pending_update_id: Pending update ID
            field_name: Field name

        Returns:
            Number of entries updated
        """
        with self._get_session() as session:
            count = session.query(self.model_class).filter_by(
                pending_update_id=pending_update_id,
                field_name=field_name,
                is_selected=True
            ).update({"is_selected": False})

            session.flush()

            return count

    def get_by_sub_run_id(self, sub_run_id: int) -> List[PendingUpdateHistory]:
        """
        Get all history entries contributed by a specific sub-run.

        Args:
            sub_run_id: Sub-run ID

        Returns:
            List of PendingUpdateHistory dataclasses
        """
        with self._get_session() as session:
            models = session.query(self.model_class).filter_by(
                sub_run_id=sub_run_id
            ).all()

            return [self._model_to_domain(model) for model in models]

    def get_unique_values_for_field(self, pending_update_id: int, field_name: str) -> List[str]:
        """
        Get unique values contributed for a specific field.
        Used to detect conflicts (multiple different values).

        Args:
            pending_update_id: Pending update ID
            field_name: Field name

        Returns:
            List of unique field values
        """
        with self._get_session() as session:
            results = session.query(self.model_class.field_value).filter_by(
                pending_update_id=pending_update_id,
                field_name=field_name
            ).distinct().all()

            return [r[0] for r in results]

    def delete_by_sub_run_id(self, sub_run_id: int) -> dict:
        """
        Delete all history entries contributed by a specific sub-run.
        Used when reprocessing a sub-run to clean up old contributions.

        Args:
            sub_run_id: Sub-run ID whose contributions should be deleted

        Returns:
            Dict with:
            - deleted_count: Number of history entries deleted
            - affected_updates: Dict mapping pending_update_id to list of affected field_names
        """
        with self._get_session() as session:
            # First, find all affected entries to track what will be deleted
            entries = session.query(self.model_class).filter_by(
                sub_run_id=sub_run_id
            ).all()

            # Track affected pending updates and their fields
            affected_updates: dict[int, set[str]] = {}
            for entry in entries:
                if entry.pending_update_id not in affected_updates:
                    affected_updates[entry.pending_update_id] = set()
                affected_updates[entry.pending_update_id].add(entry.field_name)

            # Delete all entries for this sub-run
            deleted_count = session.query(self.model_class).filter_by(
                sub_run_id=sub_run_id
            ).delete()

            session.flush()

            logger.info(f"Deleted {deleted_count} pending update history entries for sub-run {sub_run_id}")

            # Convert sets to lists for JSON serialization
            return {
                "deleted_count": deleted_count,
                "affected_updates": {
                    update_id: list(fields)
                    for update_id, fields in affected_updates.items()
                }
            }
