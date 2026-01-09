"""
Unified Actions Repository
Repository for querying the unified_actions_view (read-only)
"""
import logging
from typing import Optional, Literal, cast

from sqlalchemy import case

from shared.database.repositories.base import BaseRepository
from shared.database.models import UnifiedActionsViewModel
from server.src.shared.types.pending_orders_old import (
    UnifiedAction,
    UnifiedActionType,
    UnifiedActionsListResult,
)

logger = logging.getLogger(__name__)


class UnifiedActionsRepository(BaseRepository[UnifiedActionsViewModel]):
    """
    Repository for querying the unified_actions_view.

    This is a READ-ONLY repository - the view combines pending_orders
    and pending_updates tables. For writes, use the individual repositories.

    Provides efficient filtering, sorting, and pagination across both
    pending orders (creates) and pending updates (updates).
    """

    @property
    def model_class(self):
        return UnifiedActionsViewModel

    # ========== Conversion Methods ==========

    def _model_to_domain(self, model: UnifiedActionsViewModel) -> UnifiedAction:
        """Convert ORM model to UnifiedAction dataclass."""
        return UnifiedAction(
            type=cast(UnifiedActionType, model.type),
            id=model.id,
            customer_id=model.customer_id,
            hawb=model.hawb,
            htc_order_number=model.htc_order_number,
            status=model.status,
            is_read=model.is_read,
            error_message=model.error_message,
            last_processed_at=model.last_processed_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    # ========== Query Operations ==========

    def list_all(
        self,
        *,
        type_filter: Optional[Literal["create", "update"]] = None,
        status: Optional[str] = None,
        customer_id: Optional[int] = None,
        search: Optional[str] = None,
        is_read: Optional[bool] = None,
        sort_by: Literal["created_at", "updated_at", "last_processed_at", "hawb"] = "last_processed_at",
        sort_order: Literal["asc", "desc"] = "desc",
        limit: int = 50,
        offset: int = 0,
    ) -> UnifiedActionsListResult:
        """
        List unified actions with filtering, search, sorting, and pagination.

        Args:
            type_filter: Filter by type ('create' for pending orders, 'update' for pending updates)
            status: Filter by status (values depend on type)
            customer_id: Filter by customer ID
            search: Search string - matches HAWB (case-insensitive partial match)
                    or exact HTC order number if numeric
            is_read: Filter by read/unread status
            sort_by: Column to sort by
            sort_order: Sort direction (asc or desc)
            limit: Max records to return (default 50)
            offset: Records to skip (default 0)

        Returns:
            UnifiedActionsListResult with items and total count
        """
        with self._get_session() as session:
            query = session.query(self.model_class)

            # Apply filters
            if type_filter:
                query = query.filter(self.model_class.type == type_filter)

            if status:
                query = query.filter(self.model_class.status == status)

            if customer_id:
                query = query.filter(self.model_class.customer_id == customer_id)

            if is_read is not None:
                query = query.filter(self.model_class.is_read == is_read)

            if search:
                search_term = search.strip()
                if search_term:
                    # Try to parse as HTC order number first
                    try:
                        order_num = float(search_term)
                        query = query.filter(
                            self.model_class.htc_order_number == order_num
                        )
                    except ValueError:
                        # Not a number - search HAWB with case-insensitive partial match
                        query = query.filter(
                            self.model_class.hawb.ilike(f"%{search_term}%")
                        )

            # Get total count BEFORE applying pagination
            total = query.count()

            # Apply sorting
            # SQL Server doesn't support NULLS LAST/FIRST, so use CASE expression
            # to push NULLs to the end for DESC or beginning for ASC
            sort_column = getattr(self.model_class, sort_by)
            null_sort = case((sort_column.is_(None), 1), else_=0)

            if sort_order == "desc":
                # For DESC: sort NULLs last (null_sort ASC puts 0s first, then 1s)
                query = query.order_by(null_sort.asc(), sort_column.desc())
            else:
                # For ASC: sort NULLs first (null_sort ASC puts 0s first, but we want NULLs first)
                query = query.order_by(null_sort.desc(), sort_column.asc())

            # Apply pagination
            query = query.offset(offset).limit(limit)

            # Execute and convert to domain objects
            models = query.all()
            items = [self._model_to_domain(model) for model in models]

            return UnifiedActionsListResult(items=items, total=total)

    def get_by_type_and_id(
        self,
        action_type: Literal["create", "update"],
        action_id: int,
    ) -> Optional[UnifiedAction]:
        """
        Get a single unified action by type and ID.

        Args:
            action_type: 'create' or 'update'
            action_id: The ID (pending_order.id or pending_update.id)

        Returns:
            UnifiedAction or None if not found
        """
        with self._get_session() as session:
            model = session.query(self.model_class).filter(
                self.model_class.type == action_type,
                self.model_class.id == action_id,
            ).first()

            if model is None:
                return None

            return self._model_to_domain(model)
