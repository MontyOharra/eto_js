"""
Order Management Service

User-facing operations for managing pending orders and updates.
Handles viewing, conflict resolution, and approval workflows.

This service handles all user interactions - automated processing
is handled by the OutputProcessingService.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from datetime import datetime

from shared.logging import get_logger
from shared.database.repositories.pending_order import PendingOrderRepository
from shared.database.repositories.pending_order_history import PendingOrderHistoryRepository
from shared.database.repositories.pending_update import PendingUpdateRepository
from shared.database.repositories.eto_sub_run import EtoSubRunRepository
from shared.database.repositories.eto_run import EtoRunRepository
from shared.database.repositories.pdf_file import PdfFileRepository
from shared.database.repositories.email import EmailRepository
from shared.database.repositories.pdf_template_version import PdfTemplateVersionRepository
from shared.database.repositories.pdf_template import PdfTemplateRepository
from shared.types.pending_orders import (
    PendingOrder,
    PendingOrderHistory,
    PendingUpdate,
    VALID_FIELD_NAMES,
    REQUIRED_FIELDS,
)

if TYPE_CHECKING:
    from shared.database.connection import DatabaseConnectionManager
    from features.htc_integration.service import HtcIntegrationService

logger = get_logger(__name__)


# ==================== Result Types ====================

@dataclass
class FieldOption:
    """An option for a field value from history."""
    history_id: int
    value: str
    sub_run_id: int
    pdf_filename: str
    is_selected: bool
    contributed_at: datetime


@dataclass
class FieldWithOptions:
    """A field with its current state and available options."""
    name: str
    label: str
    required: bool
    current_value: Optional[str]
    state: str  # 'empty', 'set', 'conflict', 'confirmed'
    options: List[FieldOption]


@dataclass
class ContributingSource:
    """Information about a source that contributed data."""
    sub_run_id: int
    run_id: int
    source_type: str  # 'email' or 'manual_upload'
    source_identifier: str  # Email sender or "Manual Upload"
    pdf_filename: str
    template_id: Optional[int]
    template_name: Optional[str]
    template_customer_id: Optional[int]
    template_customer_name: Optional[str]
    processed_at: datetime
    fields_contributed: List[str]


@dataclass
class PendingOrderDetail:
    """Full detail for a pending order including sources and field options."""
    id: int
    hawb: str
    customer_id: int
    customer_name: Optional[str]
    status: str
    htc_order_number: Optional[float]  # DOUBLE in Access DB, always whole numbers
    contributing_sources: List[ContributingSource]
    fields: List[FieldWithOptions]
    created_at: datetime
    updated_at: datetime
    htc_created_at: Optional[datetime]


@dataclass
class ResolveConflictsResult:
    """Result of resolving conflicts."""
    success: bool
    fields_updated: List[str]
    new_status: str


@dataclass
class ApproveResult:
    """Result of approving a pending order or update."""
    success: bool
    htc_order_number: Optional[float]
    message: str


# ==================== Field Labels ====================

FIELD_LABELS: Dict[str, str] = {
    "hawb": "HAWB",
    "mawb": "MAWB",
    "pickup_address": "Pickup Address",
    "pickup_time_start": "Pickup Start",
    "pickup_time_end": "Pickup End",
    "pickup_notes": "Pickup Notes",
    "delivery_address": "Delivery Address",
    "delivery_time_start": "Delivery Start",
    "delivery_time_end": "Delivery End",
    "delivery_notes": "Delivery Notes",
    "pieces": "Pieces",
    "weight": "Weight",
    "order_notes": "Order Notes",
}


# ==================== Service ====================

class OrderManagementService:
    """
    Service for user-facing order management operations.

    Provides:
    - Listing and filtering pending orders/updates
    - Detailed view with source information and conflict options
    - Conflict resolution (user selects correct value)
    - Approval workflow (creates/updates orders in HTC)
    """

    def __init__(
        self,
        connection_manager: 'DatabaseConnectionManager',
        htc_integration_service: 'HtcIntegrationService',
    ) -> None:
        """
        Initialize the service.

        Args:
            connection_manager: DatabaseConnectionManager for ETO database access
            htc_integration_service: Service for HTC database operations
        """
        logger.debug("Initializing OrderManagementService...")

        self._connection_manager = connection_manager
        self._htc_service = htc_integration_service

        # Initialize repositories
        self._pending_order_repo = PendingOrderRepository(
            connection_manager=connection_manager
        )
        self._pending_order_history_repo = PendingOrderHistoryRepository(
            connection_manager=connection_manager
        )
        self._pending_update_repo = PendingUpdateRepository(
            connection_manager=connection_manager
        )

        # Repositories for source lookup
        self._sub_run_repo = EtoSubRunRepository(
            connection_manager=connection_manager
        )
        self._run_repo = EtoRunRepository(
            connection_manager=connection_manager
        )
        self._pdf_file_repo = PdfFileRepository(
            connection_manager=connection_manager
        )
        self._email_repo = EmailRepository(
            connection_manager=connection_manager
        )
        self._template_version_repo = PdfTemplateVersionRepository(
            connection_manager=connection_manager
        )
        self._template_repo = PdfTemplateRepository(
            connection_manager=connection_manager
        )

        logger.info("OrderManagementService initialized successfully")

    # ==================== Pending Orders - Read ====================

    def get_pending_orders(
        self,
        status: Optional[str] = None,
        customer_id: Optional[int] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[PendingOrder]:
        """
        Get list of pending orders with optional filtering.

        Args:
            status: Filter by status ('incomplete', 'ready', 'created')
            customer_id: Filter by customer
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of PendingOrder objects
        """
        logger.debug(f"Getting pending orders: status={status}, customer={customer_id}")

        # TODO: Add filtering to repository method
        orders = self._pending_order_repo.get_all()

        # Apply filters
        if status:
            orders = [o for o in orders if o.status == status]
        if customer_id:
            orders = [o for o in orders if o.customer_id == customer_id]

        # Apply pagination
        orders = orders[offset:offset + limit]

        logger.info(f"Retrieved {len(orders)} pending orders")
        return orders

    def get_pending_order_detail(self, pending_order_id: int) -> Optional[PendingOrderDetail]:
        """
        Get full detail for a pending order including sources and field options.

        Args:
            pending_order_id: ID of the pending order

        Returns:
            PendingOrderDetail or None if not found
        """
        logger.debug(f"Getting detail for pending order {pending_order_id}")

        # 1. Get base pending order
        pending_order = self._pending_order_repo.get_by_id(pending_order_id)
        if not pending_order:
            logger.warning(f"Pending order {pending_order_id} not found")
            return None

        # 2. Get history records
        history_records = self._pending_order_history_repo.get_by_pending_order_id(pending_order_id)

        # 3. Build contributing sources
        contributing_sources = self._build_contributing_sources(history_records)

        # 4. Build fields with options
        fields = self._build_fields_with_options(pending_order, history_records)

        # 5. Get customer name from HTC
        customer_name = self._htc_service.get_customer_name(pending_order.customer_id)

        return PendingOrderDetail(
            id=pending_order.id,
            hawb=pending_order.hawb,
            customer_id=pending_order.customer_id,
            customer_name=customer_name,
            status=pending_order.status,
            htc_order_number=pending_order.htc_order_number,
            contributing_sources=contributing_sources,
            fields=fields,
            created_at=pending_order.created_at,
            updated_at=pending_order.updated_at,
            htc_created_at=pending_order.htc_created_at,
        )

    def _build_contributing_sources(
        self,
        history_records: List[PendingOrderHistory],
    ) -> List[ContributingSource]:
        """
        Build list of contributing sources from history records.

        Groups history by sub_run_id and gathers source information.

        Args:
            history_records: List of history records

        Returns:
            List of ContributingSource objects
        """
        # Group by sub_run_id
        by_sub_run: Dict[int, List[PendingOrderHistory]] = {}
        for record in history_records:
            sub_run_id = record.sub_run_id
            if sub_run_id not in by_sub_run:
                by_sub_run[sub_run_id] = []
            by_sub_run[sub_run_id].append(record)

        sources = []
        for sub_run_id, records in by_sub_run.items():
            # Fetch actual source info via repository lookups
            run_id = 0
            source_type = "unknown"
            source_identifier = "Unknown"
            pdf_filename = "Unknown"
            template_id = None
            template_name = None
            template_customer_id = None
            template_customer_name = None

            # Get sub_run to find eto_run_id and template_version_id
            sub_run = self._sub_run_repo.get_by_id(sub_run_id)
            if sub_run:
                run_id = sub_run.eto_run_id

                # Get template info if available
                if sub_run.template_version_id:
                    template_version = self._template_version_repo.get_by_id(sub_run.template_version_id)
                    if template_version:
                        template_id = template_version.template_id
                        template = self._template_repo.get_by_id(template_version.template_id)
                        if template:
                            template_name = template.name
                            template_customer_id = template.customer_id

                # Get run to find pdf_file_id and source_email_id
                run = self._run_repo.get_by_id(sub_run.eto_run_id)
                if run:
                    # Get PDF filename
                    if run.pdf_file_id:
                        pdf_file = self._pdf_file_repo.get_by_id(run.pdf_file_id)
                        if pdf_file:
                            pdf_filename = pdf_file.original_filename

                    # Get source type and identifier
                    if run.source_email_id:
                        source_type = "email"
                        email = self._email_repo.get_by_id(run.source_email_id)
                        if email:
                            source_identifier = email.sender_email or "Unknown sender"
                    else:
                        source_type = "manual"
                        source_identifier = "Manual Upload"

            sources.append(ContributingSource(
                sub_run_id=sub_run_id,
                run_id=run_id,
                source_type=source_type,
                source_identifier=source_identifier,
                pdf_filename=pdf_filename,
                template_id=template_id,
                template_name=template_name,
                template_customer_id=template_customer_id,
                template_customer_name=template_customer_name,
                processed_at=records[0].contributed_at,
                fields_contributed=[r.field_name for r in records],
            ))

        return sources

    def _build_fields_with_options(
        self,
        pending_order: PendingOrder,
        history_records: List[PendingOrderHistory],
    ) -> List[FieldWithOptions]:
        """
        Build list of fields with their options and calculated state.

        Args:
            pending_order: The pending order
            history_records: List of history records

        Returns:
            List of FieldWithOptions objects
        """
        # Group history by field name
        by_field: Dict[str, List[PendingOrderHistory]] = {}
        for record in history_records:
            field_name = record.field_name
            if field_name not in by_field:
                by_field[field_name] = []
            by_field[field_name].append(record)

        fields = []
        for field_name in VALID_FIELD_NAMES:
            history_for_field = by_field.get(field_name, [])
            current_value = getattr(pending_order, field_name, None)

            # Calculate state
            if len(history_for_field) == 0:
                state = "empty"
            elif any(h.is_selected for h in history_for_field):
                state = "confirmed"
            elif len(set(h.field_value for h in history_for_field)) > 1 and current_value is None:
                state = "conflict"
            else:
                state = "set"

            # Build options
            options = [
                FieldOption(
                    history_id=h.id,
                    value=h.field_value,
                    sub_run_id=h.sub_run_id,
                    pdf_filename="Unknown",  # TODO: Get from JOIN
                    is_selected=h.is_selected,
                    contributed_at=h.contributed_at,
                )
                for h in history_for_field
            ]

            fields.append(FieldWithOptions(
                name=field_name,
                label=FIELD_LABELS.get(field_name, field_name),
                required=field_name in REQUIRED_FIELDS,
                current_value=current_value,
                state=state,
                options=options,
            ))

        return fields

    # ==================== Pending Orders - Write ====================

    def resolve_conflicts(
        self,
        pending_order_id: int,
        selections: List[Dict[str, Any]],
    ) -> ResolveConflictsResult:
        """
        Resolve conflicts by selecting values from history.

        Args:
            pending_order_id: ID of the pending order
            selections: List of {"field_name": str, "history_id": int}

        Returns:
            ResolveConflictsResult with updated fields and new status
        """
        logger.info(f"Resolving conflicts for pending order {pending_order_id}")

        pending_order = self._pending_order_repo.get_by_id(pending_order_id)
        if not pending_order:
            raise ValueError(f"Pending order {pending_order_id} not found")

        fields_updated = []
        field_updates: Dict[str, Any] = {}

        for selection in selections:
            field_name = selection["field_name"]
            history_id = selection["history_id"]

            # Get the history record
            history = self._pending_order_history_repo.get_by_id(history_id)
            if not history:
                logger.warning(f"History record {history_id} not found, skipping")
                continue

            if history.pending_order_id != pending_order_id:
                logger.warning(f"History {history_id} doesn't belong to order {pending_order_id}")
                continue

            # Mark this history as selected
            self._pending_order_history_repo.update(history_id, {"is_selected": True})

            # Clear is_selected on other history records for this field
            other_history = self._pending_order_history_repo.get_by_field(
                pending_order_id, field_name
            )
            for h in other_history:
                if h.id != history_id:
                    self._pending_order_history_repo.update(h.id, {"is_selected": False})

            # Update the field value on pending order
            field_updates[field_name] = history.field_value
            fields_updated.append(field_name)

            logger.debug(f"Resolved {field_name} to '{history.field_value}'")

        # Apply field updates
        if field_updates:
            self._pending_order_repo.update(pending_order_id, field_updates)

        # Recalculate status
        self._update_pending_order_status(pending_order_id)

        # Get new status
        updated_order = self._pending_order_repo.get_by_id(pending_order_id)
        new_status = updated_order.status if updated_order else "unknown"

        logger.info(f"Resolved {len(fields_updated)} conflicts, new status: {new_status}")

        return ResolveConflictsResult(
            success=True,
            fields_updated=fields_updated,
            new_status=new_status,
        )

    def approve_pending_order(self, pending_order_id: int) -> ApproveResult:
        """
        Approve a pending order and create it in HTC.

        Args:
            pending_order_id: ID of the pending order to approve

        Returns:
            ApproveResult with HTC order number if successful
        """
        logger.info(f"Approving pending order {pending_order_id}")

        pending_order = self._pending_order_repo.get_by_id(pending_order_id)
        if not pending_order:
            return ApproveResult(
                success=False,
                htc_order_number=None,
                message=f"Pending order {pending_order_id} not found",
            )

        if pending_order.status != "ready":
            return ApproveResult(
                success=False,
                htc_order_number=None,
                message=f"Pending order is not ready (status: {pending_order.status})",
            )

        # Build order data for HTC
        order_data = self._build_htc_order_data(pending_order)

        try:
            # Create order in HTC
            htc_order_number = self._htc_service.create_order(order_data)

            # Update pending order status
            self._pending_order_repo.update(pending_order_id, {
                "status": "created",
                "htc_order_number": htc_order_number,
                "htc_created_at": datetime.now(),
            })

            logger.info(f"Created HTC order {htc_order_number} from pending order {pending_order_id}")

            return ApproveResult(
                success=True,
                htc_order_number=htc_order_number,
                message=f"Order created successfully: {htc_order_number}",
            )

        except Exception as e:
            logger.error(f"Failed to create HTC order: {e}")
            return ApproveResult(
                success=False,
                htc_order_number=None,
                message=f"Failed to create order: {str(e)}",
            )

    def reject_pending_order(self, pending_order_id: int, reason: Optional[str] = None) -> bool:
        """
        Reject/delete a pending order.

        Args:
            pending_order_id: ID of the pending order to reject
            reason: Optional reason for rejection

        Returns:
            True if successfully deleted
        """
        logger.info(f"Rejecting pending order {pending_order_id}: {reason}")

        # TODO: Implement soft delete or hard delete
        # For now, just delete
        self._pending_order_repo.delete(pending_order_id)

        return True

    def _build_htc_order_data(self, pending_order: PendingOrder) -> Dict[str, Any]:
        """
        Build order data dict for HTC creation.

        Args:
            pending_order: The pending order

        Returns:
            Dict with order data for HTC
        """
        return {
            "customer_id": pending_order.customer_id,
            "hawb": pending_order.hawb,
            "mawb": pending_order.mawb,
            "pickup_address": pending_order.pickup_address,
            "pickup_time_start": pending_order.pickup_time_start,
            "pickup_time_end": pending_order.pickup_time_end,
            "pickup_notes": pending_order.pickup_notes,
            "delivery_address": pending_order.delivery_address,
            "delivery_time_start": pending_order.delivery_time_start,
            "delivery_time_end": pending_order.delivery_time_end,
            "delivery_notes": pending_order.delivery_notes,
            "pieces": pending_order.pieces,
            "weight": pending_order.weight,
            "order_notes": pending_order.order_notes,
        }

    def _update_pending_order_status(self, pending_order_id: int) -> None:
        """
        Update pending order status based on required fields.

        Args:
            pending_order_id: ID of the pending order to update
        """
        pending_order = self._pending_order_repo.get_by_id(pending_order_id)
        if not pending_order:
            return

        if pending_order.status == "created":
            return

        all_required_set = True
        for field_name in REQUIRED_FIELDS:
            value = getattr(pending_order, field_name, None)
            if value is None:
                all_required_set = False
                break

        new_status = "ready" if all_required_set else "incomplete"

        if pending_order.status != new_status:
            self._pending_order_repo.update(pending_order_id, {"status": new_status})

    # ==================== Pending Updates ====================

    def get_pending_updates(
        self,
        status: Optional[str] = None,
        customer_id: Optional[int] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[PendingUpdate]:
        """
        Get list of pending updates with optional filtering.

        Args:
            status: Filter by status
            customer_id: Filter by customer
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of PendingUpdate objects
        """
        logger.debug(f"Getting pending updates: status={status}, customer={customer_id}")

        updates = self._pending_update_repo.get_all()

        # Apply filters
        if status:
            updates = [u for u in updates if u.status == status]
        if customer_id:
            updates = [u for u in updates if u.customer_id == customer_id]

        # Apply pagination
        updates = updates[offset:offset + limit]

        logger.info(f"Retrieved {len(updates)} pending updates")
        return updates

    def approve_pending_update(self, pending_update_id: int) -> ApproveResult:
        """
        Approve a pending update and apply it to HTC.

        Args:
            pending_update_id: ID of the pending update to approve

        Returns:
            ApproveResult
        """
        logger.info(f"Approving pending update {pending_update_id}")

        pending_update = self._pending_update_repo.get_by_id(pending_update_id)
        if not pending_update:
            return ApproveResult(
                success=False,
                htc_order_number=None,
                message=f"Pending update {pending_update_id} not found",
            )

        try:
            # Update the order in HTC
            self._htc_service.update_order(
                order_number=pending_update.htc_order_number,
                updates={pending_update.field_name: pending_update.proposed_value},
            )

            # Mark update as applied
            self._pending_update_repo.update(pending_update_id, {
                "status": "applied",
                "applied_at": datetime.now(),
            })

            logger.info(f"Applied pending update {pending_update_id} to HTC order {pending_update.htc_order_number}")

            return ApproveResult(
                success=True,
                htc_order_number=pending_update.htc_order_number,
                message=f"Update applied to order {pending_update.htc_order_number}",
            )

        except Exception as e:
            logger.error(f"Failed to apply pending update: {e}")
            return ApproveResult(
                success=False,
                htc_order_number=None,
                message=f"Failed to apply update: {str(e)}",
            )

    def reject_pending_update(self, pending_update_id: int, reason: Optional[str] = None) -> bool:
        """
        Reject a pending update.

        Args:
            pending_update_id: ID of the pending update to reject
            reason: Optional reason for rejection

        Returns:
            True if successfully rejected
        """
        logger.info(f"Rejecting pending update {pending_update_id}: {reason}")

        self._pending_update_repo.update(pending_update_id, {
            "status": "rejected",
            "rejected_reason": reason,
        })

        return True
