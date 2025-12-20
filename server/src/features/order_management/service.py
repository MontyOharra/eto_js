"""
Order Management Service

User-facing operations for managing pending orders and updates.
Handles viewing, conflict resolution, and approval workflows.

Also manages the HTC order worker for automated order creation
and sends email notifications when orders are created/updated.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING
from datetime import datetime, timezone

from shared.logging import get_logger
from shared.events.order_events import order_event_manager
from shared.database.repositories.pending_order import PendingOrderRepository
from shared.database.repositories.pending_order_history import PendingOrderHistoryRepository
from shared.database.repositories.pending_update import PendingUpdateRepository
from shared.database.repositories.pending_update_history import PendingUpdateHistoryRepository
from shared.database.repositories.eto_sub_run import EtoSubRunRepository
from shared.database.repositories.eto_run import EtoRunRepository
from shared.database.repositories.pdf_file import PdfFileRepository
from shared.database.repositories.email import EmailRepository
from shared.database.repositories.pdf_template_version import PdfTemplateVersionRepository
from shared.database.repositories.pdf_template import PdfTemplateRepository
from shared.database.repositories.system_settings import SystemSettingsRepository
from shared.types.pending_orders import (
    PendingOrder,
    PendingOrderHistory,
    PendingUpdate,
    PendingOrderStatus,
    FieldState,
    VALID_FIELD_NAMES,
    REQUIRED_FIELDS,
)
from features.htc_integration.htc_order_worker import HtcOrderWorker

if TYPE_CHECKING:
    from shared.database.connection import DatabaseConnectionManager
    from features.htc_integration.service import HtcIntegrationService
    from features.email.service import EmailService

logger = get_logger(__name__)


# ==================== Result Types ====================

@dataclass
class FieldOption:
    """An option for a field value from history."""
    history_id: int
    value: str
    sub_run_id: Optional[int]  # None for mock/test data
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
    state: FieldState
    options: List[FieldOption]


@dataclass
class ContributingSource:
    """Information about a source that contributed data."""
    sub_run_id: Optional[int]  # None for mock/test data
    run_id: Optional[int]  # None for mock/test data
    source_type: str  # 'email', 'manual', or 'mock'
    source_identifier: str  # Email sender, "Manual Upload", or "Mock Test Data"
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
    status: PendingOrderStatus
    htc_order_number: Optional[float]  # DOUBLE in Access DB, always whole numbers
    contributing_sources: List[ContributingSource]
    fields: List[FieldWithOptions]
    created_at: datetime
    updated_at: datetime
    htc_created_at: Optional[datetime]
    error_message: Optional[str]
    error_at: Optional[datetime]


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
    "pickup_company_name": "Pickup Company",
    "pickup_address": "Pickup Address",
    "pickup_time_start": "Pickup Start",
    "pickup_time_end": "Pickup End",
    "pickup_notes": "Pickup Notes",
    "delivery_company_name": "Delivery Company",
    "delivery_address": "Delivery Address",
    "delivery_time_start": "Delivery Start",
    "delivery_time_end": "Delivery End",
    "delivery_notes": "Delivery Notes",
    "order_notes": "Order Notes",
}


def get_field_label(field_name: str) -> str:
    """
    Get human-readable label for a field name.
    Falls back to title-cased field name if not in mapping.
    """
    return FIELD_LABELS.get(field_name, field_name.replace("_", " ").title())


# ==================== Service ====================

class OrderManagementService:
    """
    Service for user-facing order management operations.

    Provides:
    - Listing and filtering pending orders/updates
    - Detailed view with source information and conflict options
    - Conflict resolution (user selects correct value)
    - Approval workflow (creates/updates orders in HTC)
    - Automated order creation via HTC order worker
    - Email notifications when orders are created/updated
    """

    def __init__(
        self,
        connection_manager: 'DatabaseConnectionManager',
        htc_integration_service: 'HtcIntegrationService',
        email_service: Optional['EmailService'] = None,
        worker_enabled: bool = True,
        worker_polling_interval: int = 5,
        worker_max_concurrent: int = 5,
    ) -> None:
        """
        Initialize the service.

        Args:
            connection_manager: DatabaseConnectionManager for ETO database access
            htc_integration_service: Service for HTC database operations
            email_service: Service for sending email notifications (optional)
            worker_enabled: Whether to enable the HTC order worker
            worker_polling_interval: Seconds between worker polling cycles
            worker_max_concurrent: Maximum concurrent orders to process
        """
        logger.debug("Initializing OrderManagementService...")

        self._connection_manager = connection_manager
        self._htc_service = htc_integration_service
        self._email_service = email_service

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
        self._pending_update_history_repo = PendingUpdateHistoryRepository(
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
        self._system_settings_repo = SystemSettingsRepository(
            connection_manager=connection_manager
        )

        # Initialize HTC order worker
        self._worker = HtcOrderWorker(
            get_ready_pending_orders_callback=self._get_ready_pending_orders,
            create_htc_order_callback=self._create_htc_order_by_id,
            mark_processing_callback=self._mark_pending_order_processing,
            mark_created_callback=self._mark_pending_order_created,
            mark_failed_callback=self._mark_pending_order_failed,
            is_auto_create_enabled_callback=self._is_auto_create_enabled,
            enabled=worker_enabled,
            max_concurrent=worker_max_concurrent,
            polling_interval=worker_polling_interval,
        )

        logger.info("OrderManagementService initialized successfully")

    def _is_auto_create_enabled(self) -> bool:
        """
        Check if automatic order creation is enabled in settings.

        Returns:
            True if auto-create is enabled (default), False if disabled
        """
        setting_value = self._system_settings_repo.get("order_management.auto_create_enabled")
        # Default to True if not set
        if setting_value is None:
            return True
        return setting_value.lower() == "true"

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
            error_message=pending_order.error_message,
            error_at=pending_order.error_at,
        )

    def _build_contributing_sources(
        self,
        history_records: List[PendingOrderHistory],
    ) -> List[ContributingSource]:
        """
        Build list of contributing sources from history records.

        Groups history by sub_run_id and gathers source information.
        Handles None sub_run_id (mock/test data) specially.

        Args:
            history_records: List of history records

        Returns:
            List of ContributingSource objects
        """
        # Group by sub_run_id (use a dict that can handle None keys)
        by_sub_run: Dict[Optional[int], List[PendingOrderHistory]] = {}
        for record in history_records:
            sub_run_id = record.sub_run_id
            if sub_run_id not in by_sub_run:
                by_sub_run[sub_run_id] = []
            by_sub_run[sub_run_id].append(record)

        sources = []
        for sub_run_id, records in by_sub_run.items():
            # Handle mock/test data (sub_run_id is None)
            if sub_run_id is None:
                sources.append(ContributingSource(
                    sub_run_id=None,
                    run_id=None,
                    source_type="mock",
                    source_identifier="Mock Test Data",
                    pdf_filename="(No PDF)",
                    template_id=None,
                    template_name=None,
                    template_customer_id=None,
                    template_customer_name=None,
                    processed_at=records[0].contributed_at,
                    fields_contributed=[r.field_name for r in records],
                ))
                continue

            # Fetch actual source info via repository lookups
            run_id: Optional[int] = None
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
                label=get_field_label(field_name),
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
            field_updates["last_processed_at"] = datetime.now()
            self._pending_order_repo.update(pending_order_id, field_updates)

        # Recalculate status
        self._update_pending_order_status(pending_order_id)

        # Get new status
        updated_order = self._pending_order_repo.get_by_id(pending_order_id)
        new_status = updated_order.status if updated_order else "unknown"

        logger.info(f"Resolved {len(fields_updated)} conflicts, new status: {new_status}")

        # Broadcast SSE event
        order_event_manager.broadcast_sync("pending_order_updated", {
            "id": pending_order_id,
            "status": new_status,
            "fields_updated": fields_updated,
            "action": "conflict_resolved",
        })

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
                "last_processed_at": datetime.now(),
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

        # Broadcast SSE event
        order_event_manager.broadcast_sync("pending_order_deleted", {
            "id": pending_order_id,
        })

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
            "order_notes": pending_order.order_notes,
        }

    def _has_unresolved_conflicts(self, pending_order_id: int) -> bool:
        """
        Check if a pending order has any unresolved conflicts.

        A conflict exists when a field has multiple different values in history
        and none of them has been selected (is_selected=True).

        Args:
            pending_order_id: ID of the pending order to check

        Returns:
            True if there are any unresolved conflicts, False otherwise
        """
        history_records = self._pending_order_history_repo.get_by_pending_order_id(pending_order_id)

        # Group history by field name
        by_field: Dict[str, List] = {}
        for record in history_records:
            if record.field_name not in by_field:
                by_field[record.field_name] = []
            by_field[record.field_name].append(record)

        # Check each field for conflicts
        for field_name, records in by_field.items():
            unique_values = set(r.field_value for r in records)
            has_selection = any(r.is_selected for r in records)

            # Conflict: multiple unique values and no selection made
            if len(unique_values) > 1 and not has_selection:
                return True

        return False

    def _update_pending_order_status(self, pending_order_id: int) -> None:
        """
        Update pending order status based on required fields and conflicts.

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

        # Check for unresolved conflicts (in any field, required or optional)
        has_conflicts = self._has_unresolved_conflicts(pending_order_id)

        # Ready only if all required fields set AND no unresolved conflicts
        new_status = "ready" if (all_required_set and not has_conflicts) else "incomplete"

        if pending_order.status != new_status:
            self._pending_order_repo.update(pending_order_id, {
                "status": new_status,
                "last_processed_at": datetime.now(),
            })

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

        Also sends email notification to all contributing email addresses.

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

        # Collect all non-null fields to update
        update_fields = {}
        updated_field_names = []
        for field_name in VALID_FIELD_NAMES:
            if field_name == "hawb":
                continue  # HAWB is the identifier, not updatable
            value = getattr(pending_update, field_name, None)
            if value is not None:
                update_fields[field_name] = value
                updated_field_names.append(field_name)

        if not update_fields:
            return ApproveResult(
                success=False,
                htc_order_number=pending_update.htc_order_number,
                message="No fields to update",
            )

        try:
            # Update the order in HTC
            self._htc_service.update_order(
                order_number=pending_update.htc_order_number,
                updates=update_fields,
            )

            # Mark update as applied
            self._pending_update_repo.update(pending_update_id, {
                "status": "applied",
                "applied_at": datetime.now(),
                "last_processed_at": datetime.now(),
            })

            logger.info(f"Applied pending update {pending_update_id} to HTC order {pending_update.htc_order_number}")

            # Send email notification
            self._send_order_updated_notification(pending_update_id, updated_field_names)

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
            "last_processed_at": datetime.now(),
        })

        # Broadcast SSE event
        order_event_manager.broadcast_sync("pending_update_resolved", {
            "id": pending_update_id,
            "status": "rejected",
        })

        return True

    # ==================== Worker Lifecycle ====================

    async def startup(self) -> bool:
        """
        Start the HTC order worker background process.

        Returns:
            True if worker started successfully, False otherwise
        """
        return await self._worker.startup()

    async def shutdown(self, graceful: bool = True) -> bool:
        """
        Stop the HTC order worker background process.

        Args:
            graceful: If True, wait for current batch to complete

        Returns:
            True if worker stopped successfully
        """
        return await self._worker.shutdown(graceful=graceful)

    def get_worker_status(self) -> dict:
        """Get the current status of the HTC order worker."""
        return self._worker.get_status()

    # ==================== Worker Callbacks ====================

    def _get_ready_pending_orders(self, limit: int) -> List[PendingOrder]:
        """
        Get pending orders with status='ready' for worker processing.

        Args:
            limit: Maximum number of orders to return

        Returns:
            List of PendingOrder dataclasses
        """
        return self._pending_order_repo.get_ready(limit=limit)

    def _mark_pending_order_processing(self, pending_order_id: int) -> None:
        """
        Mark a pending order as 'processing' (being created in HTC).

        Args:
            pending_order_id: ID of the pending order
        """
        self._pending_order_repo.update(pending_order_id, {
            "status": "processing",
            "error_message": None,
            "error_at": None,
            "last_processed_at": datetime.now(),
        })
        logger.info(f"Pending order {pending_order_id} marked as processing")

    def _mark_pending_order_created(self, pending_order_id: int, htc_order_number: float) -> None:
        """
        Mark a pending order as 'created' after successful HTC creation.

        Also sends email notification to all contributing email addresses.

        Args:
            pending_order_id: ID of the pending order
            htc_order_number: The HTC order number that was created
        """
        self._pending_order_repo.update(pending_order_id, {
            "status": "created",
            "htc_order_number": htc_order_number,
            "htc_created_at": datetime.now(timezone.utc),
            "error_message": None,
            "error_at": None,
            "last_processed_at": datetime.now(),
        })
        logger.info(f"Pending order {pending_order_id} marked as created (HTC order {htc_order_number})")

        # Broadcast SSE event
        order_event_manager.broadcast_sync("pending_order_updated", {
            "id": pending_order_id,
            "status": "created",
            "htc_order_number": int(htc_order_number),
            "action": "htc_created",
        })

        # Send email notification
        self._send_order_created_notification(pending_order_id, htc_order_number)

    def _mark_pending_order_failed(self, pending_order_id: int, error_message: str) -> None:
        """
        Mark a pending order as 'failed' after HTC creation failure.

        Args:
            pending_order_id: ID of the pending order
            error_message: The error message describing the failure
        """
        self._pending_order_repo.update(pending_order_id, {
            "status": "failed",
            "error_message": error_message,
            "error_at": datetime.now(timezone.utc),
            "last_processed_at": datetime.now(),
        })
        logger.error(f"Pending order {pending_order_id} marked as failed: {error_message}")

        # Broadcast SSE event
        order_event_manager.broadcast_sync("pending_order_updated", {
            "id": pending_order_id,
            "status": "failed",
            "error_message": error_message,
            "action": "htc_failed",
        })

    def _create_htc_order_by_id(self, pending_order_id: int) -> float:
        """
        Create an HTC order from a pending order by ID.

        Used by the worker to create orders. First fetches the pending order,
        then calls create_order_from_pending on HTC service.

        Args:
            pending_order_id: ID of the pending order

        Returns:
            The new HTC order number

        Raises:
            ValueError: If pending order not found
            Various HTC errors if creation fails
        """
        pending_order = self._pending_order_repo.get_by_id(pending_order_id)
        if not pending_order:
            raise ValueError(f"Pending order {pending_order_id} not found")

        return self._htc_service.create_order_from_pending(pending_order)

    def retry_pending_order(self, pending_order_id: int) -> bool:
        """
        Retry a failed pending order by resetting its status to 'ready'.

        Args:
            pending_order_id: ID of the pending order to retry

        Returns:
            True if reset successful, False if order not found or not in failed state
        """
        pending_order = self._pending_order_repo.get_by_id(pending_order_id)
        if not pending_order:
            logger.warning(f"Cannot retry: pending order {pending_order_id} not found")
            return False

        if pending_order.status != "failed":
            logger.warning(
                f"Cannot retry: pending order {pending_order_id} status is "
                f"'{pending_order.status}', expected 'failed'"
            )
            return False

        self._pending_order_repo.update(pending_order_id, {
            "status": "ready",
            "error_message": None,
            "error_at": None,
            "last_processed_at": datetime.now(),
        })
        logger.info(f"Pending order {pending_order_id} reset to 'ready' for retry")
        return True

    # ==================== Email Notifications ====================

    def _get_contributing_email_details(self, pending_order_id: int) -> Dict[str, datetime]:
        """
        Get sender email addresses and their received dates from all sub_runs that contributed to this pending order.

        Data path: pending_order_history -> eto_sub_run -> eto_run -> email

        Only returns addresses from email sources (not manual uploads which have no source_email_id).

        Args:
            pending_order_id: ID of the pending order

        Returns:
            Dict mapping email address to received_date (may be empty if all sources were manual uploads)
        """
        history_records = self._pending_order_history_repo.get_by_pending_order_id(pending_order_id)

        # Get unique sub_run_ids (excluding None for mock data)
        sub_run_ids = set(h.sub_run_id for h in history_records if h.sub_run_id is not None)

        email_details: Dict[str, datetime] = {}
        for sub_run_id in sub_run_ids:
            sub_run = self._sub_run_repo.get_by_id(sub_run_id)
            if sub_run:
                run = self._run_repo.get_by_id(sub_run.eto_run_id)
                if run and run.source_email_id:
                    email = self._email_repo.get_by_id(run.source_email_id)
                    if email and email.sender_email and email.received_date:
                        # Keep the most recent date if multiple emails from same sender
                        if email.sender_email not in email_details or email.received_date > email_details[email.sender_email]:
                            email_details[email.sender_email] = email.received_date

        return email_details

    def _get_contributing_email_details_for_update(self, pending_update_id: int) -> Dict[str, datetime]:
        """
        Get sender email addresses and their received dates from all sub_runs that contributed to this pending update.

        Data path: pending_update_history -> eto_sub_run -> eto_run -> email

        Only returns addresses from email sources (not manual uploads which have no source_email_id).

        Args:
            pending_update_id: ID of the pending update

        Returns:
            Dict mapping email address to received_date (may be empty if all sources were manual uploads)
        """
        history_records = self._pending_update_history_repo.get_by_pending_update_id(pending_update_id)

        # Get unique sub_run_ids (excluding None for mock data)
        sub_run_ids = set(h.sub_run_id for h in history_records if h.sub_run_id is not None)

        email_details: Dict[str, datetime] = {}
        for sub_run_id in sub_run_ids:
            sub_run = self._sub_run_repo.get_by_id(sub_run_id)
            if sub_run:
                run = self._run_repo.get_by_id(sub_run.eto_run_id)
                if run and run.source_email_id:
                    email = self._email_repo.get_by_id(run.source_email_id)
                    if email and email.sender_email and email.received_date:
                        # Keep the most recent date if multiple emails from same sender
                        if email.sender_email not in email_details or email.received_date > email_details[email.sender_email]:
                            email_details[email.sender_email] = email.received_date

        return email_details

    def _build_order_created_email(
        self,
        pending_order: PendingOrder,
        htc_order_number: float,
        email_received_date: datetime,
    ) -> Tuple[str, str, str]:
        """
        Build email subject and body for order creation notification.

        Args:
            pending_order: The pending order that was created
            htc_order_number: The HTC order number
            email_received_date: The date/time the source email was received

        Returns:
            Tuple of (subject, plain_text_body, html_body)
        """
        order_num = int(htc_order_number)
        subject = f"HTC Order Created - #{order_num} - {pending_order.hawb}"

        # Format the email received date
        formatted_date = email_received_date.strftime("%B %d, %Y at %I:%M %p")

        # Build plain text body
        lines = [
            f"An order has been created from your email sent at {formatted_date}. Thank you for your business.",
            f"",
            f"Order Details:",
            f"  HTC Order Number: #{order_num}",
            f"  HAWB: {pending_order.hawb}",
        ]

        if pending_order.mawb:
            lines.append(f"  MAWB: {pending_order.mawb}")

        lines.append(f"")

        # Pickup info
        if pending_order.pickup_address or pending_order.pickup_time_start:
            lines.append(f"Pickup:")
            if pending_order.pickup_company_name:
                lines.append(f"  Company: {pending_order.pickup_company_name}")
            if pending_order.pickup_address:
                lines.append(f"  Address: {pending_order.pickup_address}")
            if pending_order.pickup_time_start:
                lines.append(f"  Time: {pending_order.pickup_time_start} - {pending_order.pickup_time_end or 'N/A'}")
            if pending_order.pickup_notes:
                lines.append(f"  Notes: {pending_order.pickup_notes}")
            lines.append(f"")

        # Delivery info
        if pending_order.delivery_address or pending_order.delivery_time_start:
            lines.append(f"Delivery:")
            if pending_order.delivery_company_name:
                lines.append(f"  Company: {pending_order.delivery_company_name}")
            if pending_order.delivery_address:
                lines.append(f"  Address: {pending_order.delivery_address}")
            if pending_order.delivery_time_start:
                lines.append(f"  Time: {pending_order.delivery_time_start} - {pending_order.delivery_time_end or 'N/A'}")
            if pending_order.delivery_notes:
                lines.append(f"  Notes: {pending_order.delivery_notes}")
            lines.append(f"")

        if pending_order.order_notes:
            lines.append(f"Notes: {pending_order.order_notes}")
            lines.append(f"")

        lines.append(f"This is an automated notification from the Harrah Email-To-Order system.")

        plain_body = "\n".join(lines)

        # Build HTML body
        html_body = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <h2 style="color: #2c5282;">HTC Order Created</h2>
    <p>An order has been created from your email sent at {formatted_date}. Thank you for your business.</p>

    <table style="border-collapse: collapse; margin: 20px 0;">
        <tr>
            <td style="padding: 8px; font-weight: bold;">HTC Order Number:</td>
            <td style="padding: 8px;">#{order_num}</td>
        </tr>
        <tr>
            <td style="padding: 8px; font-weight: bold;">HAWB:</td>
            <td style="padding: 8px;">{pending_order.hawb}</td>
        </tr>
        {f'<tr><td style="padding: 8px; font-weight: bold;">MAWB:</td><td style="padding: 8px;">{pending_order.mawb}</td></tr>' if pending_order.mawb else ''}
    </table>

    <p style="color: #666; font-size: 12px; margin-top: 30px;">
        This is an automated notification from the Harrah Email-To-Order system.
    </p>
</body>
</html>
"""

        return subject, plain_body, html_body

    def _build_order_updated_email(
        self,
        pending_update: PendingUpdate,
        updated_fields: List[str],
        email_received_date: datetime,
    ) -> Tuple[str, str, str]:
        """
        Build email subject and body for order update notification.

        Args:
            pending_update: The pending update that was applied
            updated_fields: List of field names that were updated
            email_received_date: The date/time the source email was received

        Returns:
            Tuple of (subject, plain_text_body, html_body)
        """
        order_num = int(pending_update.htc_order_number) if pending_update.htc_order_number else "Unknown"
        subject = f"HTC Order Updated - #{order_num} - {pending_update.hawb}"

        # Format the email received date
        formatted_date = email_received_date.strftime("%B %d, %Y at %I:%M %p")

        # Build plain text body
        lines = [
            f"An order has been updated from your email sent at {formatted_date}. Thank you for your business.",
            f"",
            f"Order Details:",
            f"  HTC Order Number: #{order_num}",
            f"  HAWB: {pending_update.hawb}",
        ]

        lines.append(f"")
        lines.append(f"Updated Fields:")

        for field_name in updated_fields:
            field_label = get_field_label(field_name)
            field_value = getattr(pending_update, field_name, None)
            if field_value:
                lines.append(f"  {field_label}: {field_value}")

        lines.append(f"")
        lines.append(f"This is an automated notification from the Harrah Email-To-Order system.")

        plain_body = "\n".join(lines)

        # Build HTML body
        field_rows = ""
        for field_name in updated_fields:
            field_label = get_field_label(field_name)
            field_value = getattr(pending_update, field_name, None)
            if field_value:
                field_rows += f'<tr><td style="padding: 8px; font-weight: bold;">{field_label}:</td><td style="padding: 8px;">{field_value}</td></tr>'

        html_body = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <h2 style="color: #2c5282;">HTC Order Updated</h2>
    <p>An order has been updated from your email sent at {formatted_date}. Thank you for your business.</p>

    <table style="border-collapse: collapse; margin: 20px 0;">
        <tr>
            <td style="padding: 8px; font-weight: bold;">HTC Order Number:</td>
            <td style="padding: 8px;">#{order_num}</td>
        </tr>
        <tr>
            <td style="padding: 8px; font-weight: bold;">HAWB:</td>
            <td style="padding: 8px;">{pending_update.hawb}</td>
        </tr>
    </table>

    <h3 style="color: #2c5282;">Updated Fields</h3>
    <table style="border-collapse: collapse; margin: 20px 0;">
        {field_rows}
    </table>

    <p style="color: #666; font-size: 12px; margin-top: 30px;">
        This is an automated notification from the Harrah Email-To-Order system.
    </p>
</body>
</html>
"""

        return subject, plain_body, html_body

    def _send_order_notification(
        self,
        recipient_emails: List[str],
        subject: str,
        body: str,
        body_html: str,
    ) -> None:
        """
        Send notification email to all recipients.

        Uses system setting 'email.default_sender_account_id' for sender.
        Logs errors but does not raise - email failure should not block order processing.

        Args:
            recipient_emails: List of recipient email addresses
            subject: Email subject
            body: Plain text email body
            body_html: HTML email body
        """
        if not self._email_service:
            logger.warning("Email service not available - skipping notification")
            return

        if not recipient_emails:
            logger.debug("No recipient emails - skipping notification")
            return

        # Get sender account from system settings
        sender_account_id_str = self._system_settings_repo.get("email.default_sender_account_id")
        if not sender_account_id_str:
            logger.warning("No default sender account configured - skipping email notification")
            return

        try:
            sender_account_id = int(sender_account_id_str)
        except ValueError:
            logger.error(f"Invalid sender account ID in settings: {sender_account_id_str}")
            return

        # Send to each recipient
        for recipient in recipient_emails:
            try:
                result = self._email_service.send_email(
                    account_id=sender_account_id,
                    to_address=recipient,
                    subject=subject,
                    body=body,
                    body_html=body_html,
                )
                if result.success:
                    logger.info(f"Sent notification email to {recipient}")
                else:
                    logger.warning(f"Failed to send notification to {recipient}: {result.message}")
            except Exception as e:
                logger.error(f"Error sending notification to {recipient}: {e}")

    def _send_order_created_notification(self, pending_order_id: int, htc_order_number: float) -> None:
        """
        Send email notification for a newly created order.

        Sends personalized emails to each recipient with their specific email date.

        Args:
            pending_order_id: ID of the pending order
            htc_order_number: The HTC order number that was created
        """
        try:
            # Get recipient emails with their received dates
            email_details = self._get_contributing_email_details(pending_order_id)
            if not email_details:
                logger.debug(f"No email recipients for pending order {pending_order_id} - skipping notification")
                return

            # Get pending order details
            pending_order = self._pending_order_repo.get_by_id(pending_order_id)
            if not pending_order:
                logger.warning(f"Cannot send notification: pending order {pending_order_id} not found")
                return

            # Build and send personalized email for each recipient
            for recipient_email, received_date in email_details.items():
                subject, body, body_html = self._build_order_created_email(
                    pending_order, htc_order_number, received_date
                )
                self._send_order_notification([recipient_email], subject, body, body_html)

        except Exception as e:
            logger.error(f"Failed to send order created notification for {pending_order_id}: {e}")

    def _send_order_updated_notification(
        self,
        pending_update_id: int,
        updated_fields: List[str],
    ) -> None:
        """
        Send email notification for an updated order.

        Sends personalized emails to each recipient with their specific email date.

        Args:
            pending_update_id: ID of the pending update
            updated_fields: List of field names that were updated
        """
        try:
            # Get recipient emails with their received dates
            email_details = self._get_contributing_email_details_for_update(pending_update_id)
            if not email_details:
                logger.debug(f"No email recipients for pending update {pending_update_id} - skipping notification")
                return

            # Get pending update details
            pending_update = self._pending_update_repo.get_by_id(pending_update_id)
            if not pending_update:
                logger.warning(f"Cannot send notification: pending update {pending_update_id} not found")
                return

            # Build and send personalized email for each recipient
            for recipient_email, received_date in email_details.items():
                subject, body, body_html = self._build_order_updated_email(
                    pending_update, updated_fields, received_date
                )
                self._send_order_notification([recipient_email], subject, body, body_html)

        except Exception as e:
            logger.error(f"Failed to send order updated notification for {pending_update_id}: {e}")
