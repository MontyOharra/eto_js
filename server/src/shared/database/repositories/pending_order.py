"""
Pending Order Repository
Repository for pending_orders table with CRUD operations
"""
import logging
from typing import Type, Optional, List, cast

from shared.database.repositories.base import BaseRepository
from shared.database.models import PendingOrderModel
from shared.types.pending_orders import (
    PendingOrder,
    PendingOrderCreate,
    PendingOrderUpdate,
    PendingOrderStatus,
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
            pickup_address=model.pickup_address,
            pickup_time_start=model.pickup_time_start,
            pickup_time_end=model.pickup_time_end,
            delivery_address=model.delivery_address,
            delivery_time_start=model.delivery_time_start,
            delivery_time_end=model.delivery_time_end,
            mawb=model.mawb,
            pickup_notes=model.pickup_notes,
            delivery_notes=model.delivery_notes,
            order_notes=model.order_notes,
            pieces=model.pieces,
            weight=model.weight,
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
        status: Optional[str] = None,
        customer_id: Optional[int] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[PendingOrder]:
        """
        List pending orders with optional filters.

        Args:
            status: Optional status filter
            customer_id: Optional customer ID filter
            limit: Optional limit on number of results
            offset: Optional offset for pagination

        Returns:
            List of PendingOrder dataclasses
        """
        with self._get_session() as session:
            query = session.query(self.model_class)

            if status:
                query = query.filter_by(status=status)

            if customer_id:
                query = query.filter_by(customer_id=customer_id)

            # Order by most recently updated
            query = query.order_by(self.model_class.updated_at.desc())

            if offset:
                query = query.offset(offset)

            if limit:
                query = query.limit(limit)

            models = query.all()

            return [self._model_to_domain(model) for model in models]
