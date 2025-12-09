"""
Output Processing Service

Processes output channel data from pipeline executions.
Routes data to pending orders (new HAWBs) or pending updates (existing HAWBs in HTC).

This service handles automated processing only - no user interaction.
User-facing operations (viewing, conflict resolution, approvals) are handled
by the OrderManagementService.
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING, cast
from datetime import datetime, timezone

from shared.logging import get_logger
from shared.database.repositories.eto_sub_run_output_execution import EtoSubRunOutputExecutionRepository
from shared.database.repositories.pending_order import PendingOrderRepository
from shared.database.repositories.pending_order_history import PendingOrderHistoryRepository
from shared.database.repositories.pending_update import PendingUpdateRepository
from shared.types.pending_orders import (
    PendingOrderCreate,
    PendingOrderUpdate,
    PendingOrderHistoryCreate,
    PendingUpdateCreate,
    REQUIRED_FIELDS,
    VALID_FIELD_NAMES,
)

if TYPE_CHECKING:
    from shared.database.connection import DatabaseConnectionManager
    from features.htc_integration.service import HtcIntegrationService
    from shared.types.pending_orders import PendingOrder

logger = get_logger(__name__)


class OutputProcessingService:
    """
    Service for processing pipeline output into pending orders.

    Processes one output_execution record at a time. The EtoRunsService
    is responsible for creating the output_execution records (one per HAWB).

    Flow:
    1. Check if HAWB exists in HTC Open Orders table (via HtcIntegrationService)
    2. If exists: Create pending_updates records (one per field) for user approval
    3. If not exists:
       a. Get or create pending_order record
       b. Add history records for each field
       c. Handle conflicts when multiple sources provide different values
       d. Update pending_order status based on required fields
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
        logger.debug("Initializing OutputProcessingService...")

        self._connection_manager = connection_manager
        self._htc_service = htc_integration_service

        # Initialize repositories
        self._output_execution_repo = EtoSubRunOutputExecutionRepository(
            connection_manager=connection_manager
        )
        self._pending_order_repo = PendingOrderRepository(
            connection_manager=connection_manager
        )
        self._pending_order_history_repo = PendingOrderHistoryRepository(
            connection_manager=connection_manager
        )
        self._pending_update_repo = PendingUpdateRepository(
            connection_manager=connection_manager
        )

        logger.info("OutputProcessingService initialized successfully")

    def process(self, output_execution_id: int) -> None:
        """
        Process a single output execution record.

        Args:
            output_execution_id: ID of the output_execution to process
        """
        logger.info(f"Processing output execution {output_execution_id}")

        # 1. Get the record
        output_execution = self._output_execution_repo.get_by_id(output_execution_id)
        if not output_execution:
            logger.error(f"Output execution {output_execution_id} not found")
            raise ValueError(f"Output execution {output_execution_id} not found")

        # 2. Update status to 'processing'
        started_at = datetime.now(timezone.utc)
        self._output_execution_repo.update(output_execution_id, {
            "status": "processing",
            "started_at": started_at,
        })

        try:
            # 3. Extract data from output execution
            customer_id = output_execution.customer_id
            hawb = output_execution.hawb
            sub_run_id = output_execution.sub_run_id
            output_channel_data = output_execution.output_channel_data

            logger.info(f"Processing HAWB '{hawb}' for customer {customer_id}")

            # 4. Check if order already exists in HTC
            htc_order_number = self._htc_service.lookup_order_by_customer_and_hawb(
                customer_id=customer_id,
                hawb=hawb
            )

            if htc_order_number is not None:
                # Order exists in HTC - create pending updates
                action_taken = self._handle_existing_order(
                    customer_id=customer_id,
                    hawb=hawb,
                    htc_order_number=htc_order_number,
                    sub_run_id=sub_run_id,
                    output_channel_data=output_channel_data,
                )
            else:
                # Order doesn't exist in HTC - create/update pending order
                action_taken = self._handle_new_order(
                    customer_id=customer_id,
                    hawb=hawb,
                    sub_run_id=sub_run_id,
                    output_channel_data=output_channel_data,
                )

            # 5. Update output execution status to success
            completed_at = datetime.now(timezone.utc)
            self._output_execution_repo.update(output_execution_id, {
                "status": "success",
                "action_taken": action_taken,
                "completed_at": completed_at,
            })

            logger.info(f"Output execution {output_execution_id} completed: {action_taken}")

        except Exception as e:
            # Update status to 'error'
            completed_at = datetime.now(timezone.utc)
            self._output_execution_repo.update(output_execution_id, {
                "status": "error",
                "error_message": str(e),
                "error_type": type(e).__name__,
                "completed_at": completed_at,
            })
            logger.error(f"Output execution {output_execution_id} failed: {e}")
            raise

    def _handle_existing_order(
        self,
        customer_id: int,
        hawb: str,
        htc_order_number: float,
        sub_run_id: int,
        output_channel_data: Dict[str, Any],
    ) -> str:
        """
        Handle data for a HAWB that already exists in HTC.

        Creates pending_update records for each field, which will be
        queued for user approval before applying to HTC.

        Args:
            customer_id: Customer ID
            hawb: HAWB string
            htc_order_number: The existing HTC order number
            sub_run_id: Source sub-run ID
            output_channel_data: Field values from pipeline

        Returns:
            Action taken string for logging
        """
        logger.info(f"HAWB '{hawb}' exists in HTC as order {htc_order_number} - creating pending updates")

        # Filter to valid field names only (exclude 'hawb' itself)
        field_data = self._extract_valid_fields(output_channel_data)

        if not field_data:
            logger.warning(f"No valid fields to update for HAWB '{hawb}'")
            return "pending_updates_created"

        # Create pending update records
        update_creates = [
            PendingUpdateCreate(
                customer_id=customer_id,
                hawb=hawb,
                htc_order_number=htc_order_number,
                sub_run_id=sub_run_id,
                field_name=field_name,
                proposed_value=str(value),
            )
            for field_name, value in field_data.items()
        ]

        created_updates = self._pending_update_repo.create_batch(update_creates)
        logger.info(f"Created {len(created_updates)} pending updates for HAWB '{hawb}'")

        return "pending_updates_created"

    def _handle_new_order(
        self,
        customer_id: int,
        hawb: str,
        sub_run_id: int,
        output_channel_data: Dict[str, Any],
    ) -> str:
        """
        Handle data for a HAWB that doesn't exist in HTC.

        Checks pending_orders DB for existing record:
        - If no existing record: Create new pending order and set fields
        - If existing record: Compare new values against current values
          - If field has no history: set to new value
          - If field has history and new value differs: set to NULL (conflict)
          - If field has history and values match: keep current value

        Always adds history records for provenance tracking.

        Args:
            customer_id: Customer ID
            hawb: HAWB string
            sub_run_id: Source sub-run ID
            output_channel_data: Field values from pipeline

        Returns:
            Action taken string for logging
        """
        logger.info(f"HAWB '{hawb}' not in HTC - processing as pending order")

        # 1. Filter to valid field names first
        field_data = self._extract_valid_fields(output_channel_data)

        if not field_data:
            logger.warning(f"No valid fields contributed for HAWB '{hawb}'")
            return "no_valid_fields"

        # 2. Check if pending order already exists
        pending_order = self._pending_order_repo.get_by_customer_and_hawb(customer_id, hawb)
        was_created = pending_order is None

        if was_created:
            # Create new pending order
            pending_order = self._pending_order_repo.create(
                PendingOrderCreate(customer_id=customer_id, hawb=hawb)
            )
            logger.info(f"Created new pending order {pending_order.id} for HAWB '{hawb}'")

            # For new pending order, add history and set all fields directly
            history_creates = []
            field_updates: Dict[str, Any] = {}

            for field_name, new_value in field_data.items():
                new_value_str = str(new_value)

                # Add history record with is_selected=True (these are the selected values)
                history_creates.append(
                    PendingOrderHistoryCreate(
                        pending_order_id=pending_order.id,
                        sub_run_id=sub_run_id,
                        field_name=field_name,
                        field_value=new_value_str,
                        is_selected=True,
                    )
                )

                # Set field value directly (no conflicts possible on first entry)
                field_updates[field_name] = new_value_str

            # Create history records
            self._pending_order_history_repo.create_batch(history_creates)
            logger.info(f"Added {len(history_creates)} history records for new pending order {pending_order.id}")

            # Update field values
            if field_updates:
                self._pending_order_repo.update(pending_order.id, cast(PendingOrderUpdate, field_updates))

        else:
            # Existing pending order - check for conflicts
            logger.info(f"Found existing pending order {pending_order.id} for HAWB '{hawb}'")

            history_creates: List[PendingOrderHistoryCreate] = []
            field_updates: Dict[str, Any] = {}

            for field_name, new_value in field_data.items():
                new_value_str = str(new_value)

                # Check if field has existing history
                existing_history = self._pending_order_history_repo.get_by_field(
                    pending_order.id, field_name
                )

                if len(existing_history) == 0:
                    # No prior history - set new value and mark as selected
                    history_creates.append(
                        PendingOrderHistoryCreate(
                            pending_order_id=pending_order.id,
                            sub_run_id=sub_run_id,
                            field_name=field_name,
                            field_value=new_value_str,
                            is_selected=True,
                        )
                    )
                    field_updates[field_name] = new_value_str
                    logger.debug(f"Field '{field_name}' has no history - setting to '{new_value_str}'")
                else:
                    # Has existing history - check for conflict
                    current_value = getattr(pending_order, field_name, None)

                    if current_value == new_value_str:
                        # Same value - add history but don't select it (current is already selected)
                        history_creates.append(
                            PendingOrderHistoryCreate(
                                pending_order_id=pending_order.id,
                                sub_run_id=sub_run_id,
                                field_name=field_name,
                                field_value=new_value_str,
                                is_selected=False,
                            )
                        )
                        logger.debug(f"Field '{field_name}' value matches - no change")
                    else:
                        # Different value (or current is NULL) - conflict!
                        # Clear all existing selections for this field
                        cleared_count = self._pending_order_history_repo.clear_selection_for_field(
                            pending_order.id, field_name
                        )
                        logger.debug(f"Cleared {cleared_count} selections for field '{field_name}'")

                        # Add new history as not selected
                        history_creates.append(
                            PendingOrderHistoryCreate(
                                pending_order_id=pending_order.id,
                                sub_run_id=sub_run_id,
                                field_name=field_name,
                                field_value=new_value_str,
                                is_selected=False,
                            )
                        )

                        # Set field to NULL to indicate conflict
                        field_updates[field_name] = None
                        logger.info(
                            f"Conflict detected for field '{field_name}': "
                            f"current='{current_value}' vs new='{new_value_str}' - setting to NULL"
                        )

            # Create history records
            if history_creates:
                self._pending_order_history_repo.create_batch(history_creates)
                logger.info(f"Added {len(history_creates)} history records for existing pending order {pending_order.id}")

            # Apply field updates (including conflicts)
            if field_updates:
                self._pending_order_repo.update(pending_order.id, cast(PendingOrderUpdate, field_updates))

        # Update status based on required fields
        self._update_pending_order_status(pending_order.id)

        # Re-fetch the pending order to check if it's now ready for HTC creation
        updated_pending_order = self._pending_order_repo.get_by_id(pending_order.id)
        if updated_pending_order and updated_pending_order.status == "ready":
            # All required fields are filled - create order in HTC
            htc_order_number = self._create_htc_order(updated_pending_order)
            return "order_created"

        return "pending_order_created" if was_created else "pending_order_updated"

    def _extract_valid_fields(self, output_channel_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract only valid field names from output channel data.

        Filters out 'hawb' (it's the key, not a field) and any unknown field names.

        Args:
            output_channel_data: Raw output channel data from pipeline

        Returns:
            Dict with only valid field names and their values
        """
        valid_fields = {}
        for field_name, value in output_channel_data.items():
            # Skip 'hawb' - it's the key identifier, not a field to store
            if field_name == "hawb":
                continue

            # Skip unknown field names
            if field_name not in VALID_FIELD_NAMES:
                logger.warning(f"Ignoring unknown field: {field_name}")
                continue

            # Skip None/empty values
            if value is None or value == "":
                continue

            valid_fields[field_name] = value

        return valid_fields

    def _create_htc_order(self, pending_order: 'PendingOrder') -> float:
        """
        Create an order in HTC from a ready pending order.

        Updates the pending order with:
        - status = "created"
        - htc_order_number = the returned order number
        - htc_created_at = current timestamp

        Args:
            pending_order: The pending order with all required fields filled

        Returns:
            The HTC order number
        """
        logger.info(f"Creating HTC order for pending order {pending_order.id}")

        # Call HTC service to create the order
        htc_order_number = self._htc_service.create_order_from_pending(pending_order)

        # Update pending order with HTC info
        created_at = datetime.now(timezone.utc)
        self._pending_order_repo.update(pending_order.id, {
            "status": "created",
            "htc_order_number": htc_order_number,
            "htc_created_at": created_at,
        })

        logger.info(
            f"Pending order {pending_order.id} created in HTC as order {htc_order_number}"
        )

        return htc_order_number

    def _update_pending_order_status(self, pending_order_id: int) -> None:
        """
        Update pending order status based on required fields.

        Status logic:
        - 'created': Already created in HTC (don't change)
        - 'ready': All required fields are non-null
        - 'incomplete': One or more required fields are null

        Args:
            pending_order_id: ID of the pending order to update
        """
        pending_order = self._pending_order_repo.get_by_id(pending_order_id)
        if not pending_order:
            logger.error(f"Pending order {pending_order_id} not found for status update")
            return

        # Don't change status if already created
        if pending_order.status == "created":
            logger.debug(f"Pending order {pending_order_id} already created, skipping status update")
            return

        # Check if all required fields are set
        all_required_set = True
        for field_name in REQUIRED_FIELDS:
            value = getattr(pending_order, field_name, None)
            if value is None:
                all_required_set = False
                logger.debug(f"Required field '{field_name}' is missing for pending order {pending_order_id}")
                break

        new_status = "ready" if all_required_set else "incomplete"

        if pending_order.status != new_status:
            self._pending_order_repo.update(pending_order_id, {"status": new_status})
            logger.info(f"Updated pending order {pending_order_id} status: {pending_order.status} -> {new_status}")
