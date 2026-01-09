"""
Pending Action Repository

Repository for pending_actions table with CRUD operations and specialized queries.
"""
import logging
from datetime import datetime

from sqlalchemy import and_, or_
from sqlalchemy.orm import joinedload

from shared.database.repositories.base import BaseRepository
from shared.database.models import PendingActionModel, PendingActionFieldModel
from shared.exceptions.service import ObjectNotFoundError
from shared.types.pending_actions import (
    PendingAction,
    PendingActionCreate,
    PendingActionUpdate,
    PendingActionListView,
    PendingActionDetailView,
    PendingActionFieldView,
    PendingActionStatus,
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
        return PendingAction(
            id=model.id,
            customer_id=model.customer_id,
            hawb=model.hawb,
            htc_order_number=model.htc_order_number,
            action_type=model.action_type,
            status=model.status,
            required_fields_present=model.required_fields_present,
            conflict_count=model.conflict_count,
            error_message=model.error_message,
            error_at=model.error_at,
            is_read=model.is_read,
            created_at=model.created_at,
            updated_at=model.updated_at,
            last_processed_at=model.last_processed_at,
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
                    conflict_count=model.conflict_count,
                    is_read=model.is_read,
                    created_at=model.created_at,
                    updated_at=model.updated_at,
                    last_processed_at=model.last_processed_at,
                )
                for model in models
            ]

            return result, total

    def get_detail_with_fields(self, action_id: int) -> PendingActionDetailView | None:
        """
        Get pending action with all field values for detail view.

        Performs eager loading of fields and groups them by field_name.

        Args:
            action_id: Pending action ID

        Returns:
            PendingActionDetailView with fields grouped by field_name,
            or None if not found
        """
        with self._get_session() as session:
            model = (
                session.query(self.model_class)
                .options(joinedload(self.model_class.fields))
                .filter(self.model_class.id == action_id)
                .first()
            )

            if model is None:
                return None

            # Group fields by field_name
            fields_by_name: dict[str, list[PendingActionFieldView]] = {}

            for field in model.fields:
                field_view = PendingActionFieldView(
                    id=field.id,
                    field_name=field.field_name,
                    value=field.value,
                    is_selected=field.is_selected,
                    is_approved_for_update=field.is_approved_for_update,
                    sub_run_id=field.sub_run_id,
                    is_user_provided=field.sub_run_id is None,
                )

                if field.field_name not in fields_by_name:
                    fields_by_name[field.field_name] = []
                fields_by_name[field.field_name].append(field_view)

            return PendingActionDetailView(
                id=model.id,
                customer_id=model.customer_id,
                customer_name=None,  # Enriched at service layer
                hawb=model.hawb,
                htc_order_number=model.htc_order_number,
                action_type=model.action_type,
                status=model.status,
                required_fields_present=model.required_fields_present,
                conflict_count=model.conflict_count,
                error_message=model.error_message,
                error_at=model.error_at,
                is_read=model.is_read,
                created_at=model.created_at,
                updated_at=model.updated_at,
                last_processed_at=model.last_processed_at,
                fields=fields_by_name,
            )
