"""
Pending Action Repository

Repository for pending_actions table with CRUD operations and specialized queries.
"""
import json
import logging
from datetime import datetime

from sqlalchemy import and_, func, select

from shared.database.repositories.base import BaseRepository
from shared.database.models import PendingActionModel, PendingActionFieldModel
from shared.exceptions.service import ObjectNotFoundError
from shared.types.pending_actions import (
    PendingAction,
    PendingActionCreate,
    PendingActionUpdate,
    PendingActionListView,
    PendingActionStatus,
    ExecutionResult,
    REQUIRED_ORDER_FIELDS,
    OPTIONAL_ORDER_FIELDS,
)

logger = logging.getLogger(__name__)

# Terminal statuses - actions in these states are not "active"
TERMINAL_STATUSES: set[PendingActionStatus] = {"completed", "rejected", "failed"}


class PendingActionRepository(BaseRepository[PendingActionModel]):
    """
    Repository for pending action CRUD operations.

    Handles:
    - Basic CRUD for pending_actions table
    - Conversion between ORM models and domain dataclasses
    - Specialized queries for active action lookup, list views, and detail views
    """

    @property
    def model_class(self) -> type[PendingActionModel]:
        """Return the SQLAlchemy model class this repository manages"""
        return PendingActionModel

    # ========== Conversion Methods ==========

    def _model_to_domain(self, model: PendingActionModel) -> PendingAction:
        """Convert ORM model to PendingAction dataclass."""
        # Parse execution_result JSON if present
        execution_result = None
        if model.execution_result:
            try:
                result_data = json.loads(model.execution_result)
                execution_result = ExecutionResult(**result_data)
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f"Failed to parse execution_result for action {model.id}: {e}")

        return PendingAction(
            id=model.id,
            customer_id=model.customer_id,
            hawb=model.hawb,
            htc_order_number=model.htc_order_number,
            action_type=model.action_type,
            status=model.status,
            required_fields_present=model.required_fields_present,
            optional_fields_present=model.optional_fields_present,
            conflict_count=model.conflict_count,
            error_message=model.error_message,
            error_at=model.error_at,
            is_read=model.is_read,
            created_at=model.created_at,
            updated_at=model.updated_at,
            last_processed_at=model.last_processed_at,
            execution_result=execution_result,
        )

    # ========== CRUD Operations ==========

    def create(self, data: PendingActionCreate) -> PendingAction:
        """
        Create new pending action with status = "accumulating".

        Args:
            data: PendingActionCreate with customer_id, hawb, action_type

        Returns:
            Created PendingAction dataclass
        """
        with self._get_session() as session:
            model = self.model_class(
                customer_id=data.customer_id,
                hawb=data.hawb,
                action_type=data.action_type,
                htc_order_number=data.htc_order_number,
                # status defaults to "accumulating" via server_default
                # timestamps auto-set by server_default
            )

            session.add(model)
            session.flush()

            return self._model_to_domain(model)

    def get_by_id(self, action_id: int) -> PendingAction | None:
        """
        Get pending action by ID.

        Args:
            action_id: Pending action ID

        Returns:
            PendingAction dataclass or None if not found
        """
        with self._get_session() as session:
            model = session.get(self.model_class, action_id)

            if model is None:
                return None

            return self._model_to_domain(model)

    def update(self, action_id: int, updates: PendingActionUpdate) -> PendingAction:
        """
        Update pending action. Only updates provided fields.

        Uses Pydantic's model_fields_set to distinguish between:
        - Field not provided: not in model_fields_set (don't update)
        - Field set to None: in model_fields_set with None value (set NULL)
        - Field set to value: in model_fields_set with value (update)

        Args:
            action_id: Pending action ID
            updates: PendingActionUpdate with fields to update

        Returns:
            Updated PendingAction dataclass

        Raises:
            ObjectNotFoundError: If action with given ID does not exist
        """
        with self._get_session() as session:
            model = session.get(self.model_class, action_id)

            if model is None:
                raise ObjectNotFoundError(f"Pending action {action_id} not found")

            # Update only fields that were explicitly set
            for field_name in updates.model_fields_set:
                value = getattr(updates, field_name)
                # Serialize execution_result to JSON string for storage
                if field_name == "execution_result" and value is not None:
                    value = value.model_dump_json()
                setattr(model, field_name, value)

            session.flush()

            return self._model_to_domain(model)

    def delete(self, action_id: int) -> bool:
        """
        Delete pending action by ID.

        Note: This will cascade delete all associated pending_action_fields
        due to the ondelete="CASCADE" foreign key constraint.

        Args:
            action_id: Pending action ID

        Returns:
            True if deleted, False if not found
        """
        with self._get_session() as session:
            model = session.get(self.model_class, action_id)

            if model is None:
                return False

            session.delete(model)
            session.flush()

            logger.debug(f"Deleted pending action {action_id}")
            return True

    # ========== Specialized Query Operations ==========

    def get_active_by_customer_hawb(
        self,
        customer_id: int,
        hawb: str
    ) -> PendingAction | None:
        """
        Get active pending action for a customer/HAWB pair.

        "Active" means status is NOT in terminal states (completed, rejected, failed).
        Used during accumulation to find existing action to add fields to.

        Args:
            customer_id: Customer ID
            hawb: HAWB string

        Returns:
            PendingAction dataclass or None if no active action exists
        """
        with self._get_session() as session:
            model = (
                session.query(self.model_class)
                .filter(
                    and_(
                        self.model_class.customer_id == customer_id,
                        self.model_class.hawb == hawb,
                        ~self.model_class.status.in_(TERMINAL_STATUSES),
                    )
                )
                .first()
            )

            if model is None:
                return None

            return self._model_to_domain(model)

    def get_all_with_counts(
        self,
        status: PendingActionStatus | None = None,
        action_type: str | None = None,
        is_read: bool | None = None,
        customer_id: int | None = None,
        search_query: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        order_by: str = "last_processed_at",
        desc: bool = True,
    ) -> tuple[list[PendingActionListView], int]:
        """
        Get pending actions for list view with optional filtering and pagination.

        Note: customer_name enrichment is done at the service layer (from HTC).

        Args:
            status: Filter by status (optional)
            action_type: Filter by action type (optional)
            is_read: Filter by read status (optional)
            customer_id: Filter by customer ID (optional)
            search_query: Search in HAWB (optional)
            limit: Maximum number of results (optional)
            offset: Number of results to skip (optional)
            order_by: Field to order by (default: last_processed_at)
            desc: Sort descending if True (default: True - newest first)

        Returns:
            Tuple of (list of PendingActionListView, total count before pagination)
        """
        with self._get_session() as session:
            query = session.query(self.model_class)

            # Apply filters
            if status is not None:
                query = query.filter(self.model_class.status == status)

            if action_type is not None:
                query = query.filter(self.model_class.action_type == action_type)

            if is_read is not None:
                query = query.filter(self.model_class.is_read == is_read)

            if customer_id is not None:
                query = query.filter(self.model_class.customer_id == customer_id)

            if search_query:
                search_pattern = f"%{search_query}%"
                query = query.filter(self.model_class.hawb.ilike(search_pattern))

            # Get total count before pagination
            total = query.count()

            # Apply ordering
            if hasattr(self.model_class, order_by):
                order_column = getattr(self.model_class, order_by)
                if desc:
                    query = query.order_by(order_column.desc())
                else:
                    query = query.order_by(order_column)
            else:
                logger.warning(
                    f"Field '{order_by}' does not exist on PendingActionModel, "
                    "using last_processed_at"
                )
                query = query.order_by(self.model_class.last_processed_at.desc())

            # Apply pagination
            if offset is not None:
                query = query.offset(offset)
            if limit is not None:
                query = query.limit(limit)

            # Execute and convert
            models = query.all()

            # Get field names for all actions in result set (single query)
            action_ids = [model.id for model in models]
            field_names_by_action: dict[int, list[str]] = {aid: [] for aid in action_ids}
            error_field_counts: dict[int, int] = {aid: 0 for aid in action_ids}

            if action_ids:
                # Get distinct field names per action
                field_rows = (
                    session.query(
                        PendingActionFieldModel.pending_action_id,
                        PendingActionFieldModel.field_name,
                    )
                    .filter(PendingActionFieldModel.pending_action_id.in_(action_ids))
                    .distinct()
                    .order_by(
                        PendingActionFieldModel.pending_action_id,
                        PendingActionFieldModel.field_name,
                    )
                    .all()
                )
                for row in field_rows:
                    field_names_by_action[row.pending_action_id].append(row.field_name)

                # Count failed fields per action
                from sqlalchemy import func
                error_rows = (
                    session.query(
                        PendingActionFieldModel.pending_action_id,
                        func.count(PendingActionFieldModel.id).label('error_count'),
                    )
                    .filter(PendingActionFieldModel.pending_action_id.in_(action_ids))
                    .filter(PendingActionFieldModel.processing_status == 'failed')
                    .group_by(PendingActionFieldModel.pending_action_id)
                    .all()
                )
                for row in error_rows:
                    error_field_counts[row.pending_action_id] = row.error_count

            result = [
                PendingActionListView(
                    id=model.id,
                    customer_id=model.customer_id,
                    customer_name=None,  # Enriched at service layer
                    hawb=model.hawb,
                    htc_order_number=model.htc_order_number,
                    action_type=model.action_type,
                    status=model.status,
                    required_fields_present=model.required_fields_present,
                    required_fields_total=len(REQUIRED_ORDER_FIELDS),
                    optional_fields_present=model.optional_fields_present,
                    optional_fields_total=len(OPTIONAL_ORDER_FIELDS),
                    field_names=field_names_by_action.get(model.id, []),
                    conflict_count=model.conflict_count,
                    error_field_count=error_field_counts.get(model.id, 0),
                    error_message=model.error_message,
                    is_read=model.is_read,
                    created_at=model.created_at,
                    updated_at=model.updated_at,
                    last_processed_at=model.last_processed_at,
                )
                for model in models
            ]

            return result, total

    def get_ready_creates_after(
        self,
        created_after: datetime,
        limit: int = 50,
    ) -> list[PendingAction]:
        """
        Get create actions in "ready" status created after the given timestamp.

        Used by the auto-create worker to find eligible actions for automatic approval.
        Returns actions in FIFO order (oldest first).

        Args:
            created_after: Only return actions created after this timestamp
            limit: Maximum number of actions to return

        Returns:
            List of PendingAction dataclasses ordered by created_at ASC
        """
        with self._get_session() as session:
            models = (
                session.query(self.model_class)
                .filter(
                    and_(
                        self.model_class.action_type == "create",
                        self.model_class.status == "ready",
                        self.model_class.created_at > created_after,
                    )
                )
                .order_by(self.model_class.created_at.asc())
                .limit(limit)
                .all()
            )

            return [self._model_to_domain(model) for model in models]
