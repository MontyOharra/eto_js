"""
Pending Order Repository
Repository for pending_orders table with CRUD operations
"""
import logging
from typing import Type, Optional, List, Literal, cast

from shared.database.repositories.base import BaseRepository
from shared.database.models import PendingOrderModel
from shared.types.pending_orders import (
    PendingOrder,
    PendingOrderCreate,
    PendingOrderUpdate,
    PendingOrderStatus,
    PendingOrderListResult,
)

logger = logging.getLogger(__name__)


class PendingOrderRepository(BaseRepository[PendingOrderModel]):
    """
    Repository for pending order CRUD operations.

    Handles:
    - Basic CRUD for pending_orders table
    - Conversion between ORM models and domain dataclasses
    - Query operations for finding orders by status, customer, HAWB
    """

    @property
    def model_class(self) -> Type[PendingOrderModel]:
        """Return the SQLAlchemy model class this repository manages"""
        return PendingOrderModel

    # ========== Conversion Methods ==========

    def _model_to_domain(self, model: PendingOrderModel) -> PendingOrder:
        """
        Convert ORM model to PendingOrder dataclass.
        """
        return PendingOrder(
            id=model.id,
            customer_id=model.customer_id,
            hawb=model.hawb,
            status=cast(PendingOrderStatus, model.status),
            htc_order_number=model.htc_order_number,
            htc_created_at=model.htc_created_at,
            error_message=model.error_message,
            error_at=model.error_at,
            pickup_company_name=model.pickup_company_name,
            pickup_address=model.pickup_address,
            pickup_time_start=model.pickup_time_start,
            pickup_time_end=model.pickup_time_end,
            delivery_company_name=model.delivery_company_name,
            delivery_address=model.delivery_address,
            delivery_time_start=model.delivery_time_start,
            delivery_time_end=model.delivery_time_end,
            mawb=model.mawb,
            pickup_notes=model.pickup_notes,
            delivery_notes=model.delivery_notes,
            order_notes=model.order_notes,
            dims=model.dims,
            is_read=model.is_read,
            last_processed_at=model.last_processed_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    # ========== CRUD Operations ==========

    def create(self, data: PendingOrderCreate) -> PendingOrder:
        """
        Create new pending order with status = "incomplete".

        Args:
            data: PendingOrderCreate with customer_id and hawb

        Returns:
            Created PendingOrder dataclass
        """
        with self._get_session() as session:
            model = self.model_class(
                customer_id=data.customer_id,
                hawb=data.hawb,
                # status defaults to "incomplete" via model default
            )

            session.add(model)
            session.flush()  # Get ID without committing

            return self._model_to_domain(model)

    def get_by_id(self, pending_order_id: int) -> Optional[PendingOrder]:
        """
        Get pending order by ID.

        Args:
            pending_order_id: Pending order ID

        Returns:
            PendingOrder dataclass or None if not found
        """
        with self._get_session() as session:
            model = session.get(self.model_class, pending_order_id)

            if model is None:
                return None

            return self._model_to_domain(model)

    def update(self, pending_order_id: int, updates: PendingOrderUpdate) -> Optional[PendingOrder]:
        """
        Update pending order. Only updates provided fields.

        Args:
            pending_order_id: Pending order ID
            updates: Dict of fields to update (TypedDict with all fields optional)

        Returns:
            Updated PendingOrder dataclass or None if not found

        Raises:
            ValueError: If invalid field name provided
        """
        with self._get_session() as session:
            model = session.get(self.model_class, pending_order_id)

            if model is None:
                return None

            # Update only provided fields
            for field, value in updates.items():
                if not hasattr(model, field):
                    raise ValueError(f"Invalid field for pending order update: {field}")
                setattr(model, field, value)

            session.flush()

            return self._model_to_domain(model)

    def delete(self, pending_order_id: int) -> bool:
        """
        Delete pending order by ID.
        Also cascades to delete related history entries.

        Args:
            pending_order_id: Pending order ID

        Returns:
            True if deleted, False if not found
        """
        with self._get_session() as session:
            model = session.get(self.model_class, pending_order_id)

            if model is None:
                return False

            session.delete(model)
            session.flush()

            logger.debug(f"Deleted pending order {pending_order_id}")
            return True

    # ========== Query Operations ==========

    def get_by_customer_and_hawb(self, customer_id: int, hawb: str) -> Optional[PendingOrder]:
        """
        Get pending order by customer_id and hawb (unique constraint).

        Args:
            customer_id: Customer ID
            hawb: HAWB value

        Returns:
            PendingOrder dataclass or None if not found
        """
        with self._get_session() as session:
            model = session.query(self.model_class).filter_by(
                customer_id=customer_id,
                hawb=hawb
            ).first()

            if model is None:
                return None

            return self._model_to_domain(model)

    def get_by_status(self, status: str, limit: Optional[int] = None) -> List[PendingOrder]:
        """
        Get pending orders by status.

        Args:
            status: Status to filter by ("incomplete", "ready", "created")
            limit: Optional limit on number of results

        Returns:
            List of PendingOrder dataclasses
        """
        with self._get_session() as session:
            query = session.query(self.model_class).filter_by(status=status)

            if limit:
                query = query.limit(limit)

            models = query.all()

            return [self._model_to_domain(model) for model in models]

    def get_incomplete(self, limit: Optional[int] = None) -> List[PendingOrder]:
        """
        Get incomplete pending orders (convenience method).

        Args:
            limit: Optional limit on number of results

        Returns:
            List of PendingOrder dataclasses with status="incomplete"
        """
        return self.get_by_status("incomplete", limit=limit)

    def get_ready(self, limit: Optional[int] = None) -> List[PendingOrder]:
        """
        Get ready pending orders (convenience method).

        Args:
            limit: Optional limit on number of results

        Returns:
            List of PendingOrder dataclasses with status="ready"
        """
        return self.get_by_status("ready", limit=limit)

    def get_by_customer_id(self, customer_id: int, limit: Optional[int] = None) -> List[PendingOrder]:
        """
        Get all pending orders for a customer.

        Args:
            customer_id: Customer ID
            limit: Optional limit on number of results

        Returns:
            List of PendingOrder dataclasses
        """
        with self._get_session() as session:
            query = session.query(self.model_class).filter_by(customer_id=customer_id)

            if limit:
                query = query.limit(limit)

            models = query.all()

            return [self._model_to_domain(model) for model in models]

    def list_all(
        self,
        *,
        status: Optional[str] = None,
        customer_id: Optional[int] = None,
        search: Optional[str] = None,
        sort_by: Literal["created_at", "updated_at", "hawb"] = "updated_at",
        sort_order: Literal["asc", "desc"] = "desc",
        limit: int = 50,
        offset: int = 0,
    ) -> PendingOrderListResult:
        """
        List pending orders with filtering, search, sorting, and pagination.

        Args:
            status: Filter by status (incomplete, ready, processing, created, failed, rejected)
            customer_id: Filter by customer ID
            search: Search string - matches HAWB (case-insensitive partial match)
                    or exact HTC order number if numeric
            sort_by: Column to sort by (created_at, updated_at, hawb)
            sort_order: Sort direction (asc or desc)
            limit: Max records to return (default 50)
            offset: Records to skip (default 0)

        Returns:
            PendingOrderListResult with items and total count
        """
        with self._get_session() as session:
            # Build base query with filters
            query = session.query(self.model_class)

            if status:
                query = query.filter(self.model_class.status == status)

            if customer_id:
                query = query.filter(self.model_class.customer_id == customer_id)

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
            sort_column = getattr(self.model_class, sort_by)
            if sort_order == "desc":
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column.asc())

            # Apply pagination
            query = query.offset(offset).limit(limit)

            # Execute and convert to domain objects
            models = query.all()
            items = [self._model_to_domain(model) for model in models]

            return PendingOrderListResult(items=items, total=total)
