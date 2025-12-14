"""
Pending Update Repository
Repository for pending_updates table with CRUD operations
"""
import logging
from typing import Type, Optional, List, cast

from shared.database.repositories.base import BaseRepository
from shared.database.models import PendingUpdateModel
from shared.types.pending_orders import (
    PendingUpdate,
    PendingUpdateCreate,
    PendingUpdateUpdate,
    PendingUpdateStatus,
)

logger = logging.getLogger(__name__)


class PendingUpdateRepository(BaseRepository[PendingUpdateModel]):
    """
    Repository for pending update CRUD operations.

    Handles:
    - Basic CRUD for pending_updates table
    - Conversion between ORM models and domain dataclasses
    - Query operations for finding updates by status, customer, HAWB, order
    - Bulk operations for approve/reject

    Structure mirrors PendingOrderRepository - one record per (customer_id, hawb)
    with status='pending'. Field changes accumulate via history table.
    """

    @property
    def model_class(self) -> Type[PendingUpdateModel]:
        """Return the SQLAlchemy model class this repository manages"""
        return PendingUpdateModel

    # ========== Conversion Methods ==========

    def _model_to_domain(self, model: PendingUpdateModel) -> PendingUpdate:
        """
        Convert ORM model to PendingUpdate dataclass.
        """
        return PendingUpdate(
            id=model.id,
            customer_id=model.customer_id,
            hawb=model.hawb,
            htc_order_number=model.htc_order_number,
            status=cast(PendingUpdateStatus, model.status),
            # Field values
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
            pieces=model.pieces,
            weight=model.weight,
            is_read=model.is_read,
            # Timestamps
            created_at=model.created_at,
            updated_at=model.updated_at,
            reviewed_at=model.reviewed_at,
        )

    # ========== CRUD Operations ==========

    def create(self, data: PendingUpdateCreate) -> PendingUpdate:
        """
        Create new pending update with status = "pending".

        Args:
            data: PendingUpdateCreate with customer_id, hawb, htc_order_number

        Returns:
            Created PendingUpdate dataclass
        """
        with self._get_session() as session:
            model = self.model_class(
                customer_id=data.customer_id,
                hawb=data.hawb,
                htc_order_number=data.htc_order_number,
                # status defaults to "pending" via model default
                # All field values start as NULL
            )

            session.add(model)
            session.flush()  # Get ID without committing

            return self._model_to_domain(model)

    def get_by_id(self, pending_update_id: int) -> Optional[PendingUpdate]:
        """
        Get pending update by ID.

        Args:
            pending_update_id: Pending update ID

        Returns:
            PendingUpdate dataclass or None if not found
        """
        with self._get_session() as session:
            model = session.get(self.model_class, pending_update_id)

            if model is None:
                return None

            return self._model_to_domain(model)

    def update(self, pending_update_id: int, updates: PendingUpdateUpdate) -> Optional[PendingUpdate]:
        """
        Update pending update. Only updates provided fields.

        Args:
            pending_update_id: Pending update ID
            updates: Dict of fields to update (TypedDict with all fields optional)

        Returns:
            Updated PendingUpdate dataclass or None if not found

        Raises:
            ValueError: If invalid field name provided
        """
        with self._get_session() as session:
            model = session.get(self.model_class, pending_update_id)

            if model is None:
                return None

            # Update only provided fields
            for field, value in updates.items():
                if not hasattr(model, field):
                    raise ValueError(f"Invalid field for pending update update: {field}")
                setattr(model, field, value)

            session.flush()

            return self._model_to_domain(model)

    def delete(self, pending_update_id: int) -> bool:
        """
        Delete pending update by ID.

        Args:
            pending_update_id: Pending update ID

        Returns:
            True if deleted, False if not found
        """
        with self._get_session() as session:
            model = session.get(self.model_class, pending_update_id)

            if model is None:
                return False

            session.delete(model)
            session.flush()

            logger.debug(f"Deleted pending update {pending_update_id}")
            return True

    # ========== Query Operations ==========

    def get_by_status(self, status: str, limit: Optional[int] = None) -> List[PendingUpdate]:
        """
        Get pending updates by status.

        Args:
            status: Status to filter by ("pending", "approved", "rejected")
            limit: Optional limit on number of results

        Returns:
            List of PendingUpdate dataclasses
        """
        with self._get_session() as session:
            query = session.query(self.model_class).filter_by(status=status)

            if limit:
                query = query.limit(limit)

            models = query.all()

            return [self._model_to_domain(model) for model in models]

    def get_pending(self, limit: Optional[int] = None) -> List[PendingUpdate]:
        """
        Get pending updates awaiting review (convenience method).

        Args:
            limit: Optional limit on number of results

        Returns:
            List of PendingUpdate dataclasses with status="pending"
        """
        return self.get_by_status("pending", limit=limit)

    def get_by_customer_and_hawb(self, customer_id: int, hawb: str) -> List[PendingUpdate]:
        """
        Get all pending updates for a specific customer and HAWB (all statuses).

        Args:
            customer_id: Customer ID
            hawb: HAWB value

        Returns:
            List of PendingUpdate dataclasses ordered by created_at desc
        """
        with self._get_session() as session:
            models = session.query(self.model_class).filter_by(
                customer_id=customer_id,
                hawb=hawb
            ).order_by(self.model_class.created_at.desc()).all()

            return [self._model_to_domain(model) for model in models]

    def get_active_by_customer_and_hawb(self, customer_id: int, hawb: str) -> Optional[PendingUpdate]:
        """
        Get the active (status='pending') pending update for a customer and HAWB.
        There should only be one active pending update per (customer_id, hawb) combo.

        Args:
            customer_id: Customer ID
            hawb: HAWB value

        Returns:
            PendingUpdate dataclass or None if no active update exists
        """
        with self._get_session() as session:
            model = session.query(self.model_class).filter_by(
                customer_id=customer_id,
                hawb=hawb,
                status="pending"
            ).first()

            if model is None:
                return None

            return self._model_to_domain(model)

    def get_by_htc_order_number(self, htc_order_number: float) -> List[PendingUpdate]:
        """
        Get pending updates for a specific HTC order.

        Args:
            htc_order_number: HTC order number

        Returns:
            List of PendingUpdate dataclasses
        """
        with self._get_session() as session:
            models = session.query(self.model_class).filter_by(
                htc_order_number=htc_order_number
            ).order_by(self.model_class.created_at.desc()).all()

            return [self._model_to_domain(model) for model in models]

    def list_all(
        self,
        status: Optional[str] = None,
        customer_id: Optional[int] = None,
        hawb: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> tuple[List[PendingUpdate], int]:
        """
        List pending updates with optional filters and pagination.

        Args:
            status: Optional status filter
            customer_id: Optional customer ID filter
            hawb: Optional HAWB filter
            limit: Optional limit on number of results
            offset: Optional offset for pagination

        Returns:
            Tuple of (list of PendingUpdate dataclasses, total count)
        """
        with self._get_session() as session:
            query = session.query(self.model_class)

            if status:
                query = query.filter_by(status=status)

            if customer_id:
                query = query.filter_by(customer_id=customer_id)

            if hawb:
                query = query.filter_by(hawb=hawb)

            # Get total count before pagination
            total = query.count()

            # Order by most recently updated
            query = query.order_by(self.model_class.updated_at.desc())

            if offset:
                query = query.offset(offset)

            if limit:
                query = query.limit(limit)

            models = query.all()

            return [self._model_to_domain(model) for model in models], total

    # ========== Bulk Operations ==========

    def bulk_update_status(
        self,
        update_ids: List[int],
        status: str,
        reviewed_at: Optional["datetime"] = None
    ) -> int:
        """
        Bulk update status for multiple pending updates.
        Used for bulk approve/reject operations.

        Args:
            update_ids: List of pending update IDs
            status: New status ("approved" or "rejected")
            reviewed_at: Optional reviewed timestamp (defaults to now if not provided)

        Returns:
            Number of records updated
        """
        from datetime import datetime

        if not update_ids:
            return 0

        with self._get_session() as session:
            update_values = {"status": status}
            if reviewed_at:
                update_values["reviewed_at"] = reviewed_at
            else:
                update_values["reviewed_at"] = datetime.utcnow()

            count = session.query(self.model_class).filter(
                self.model_class.id.in_(update_ids)
            ).update(update_values, synchronize_session=False)

            session.flush()

            return count
