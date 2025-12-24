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
import json

from shared.logging import get_logger
from shared.events.order_events import order_event_manager
from shared.database.repositories.eto_sub_run_output_execution import EtoSubRunOutputExecutionRepository
from shared.database.repositories.pending_order import PendingOrderRepository
from shared.database.repositories.pending_order_history import PendingOrderHistoryRepository
from shared.database.repositories.pending_update import PendingUpdateRepository
from shared.database.repositories.pending_update_history import PendingUpdateHistoryRepository
from shared.types.pending_orders import (
    PendingOrderCreate,
    PendingOrderUpdate,
    PendingOrderHistoryCreate,
    PendingUpdateCreate,
    PendingUpdateUpdate,
    PendingUpdateHistoryCreate,
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
        self._pending_update_history_repo = PendingUpdateHistoryRepository(
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

            # 4. Check for duplicate orders in HTC (requires manual review)
            htc_order_count = self._htc_service.count_orders_by_customer_and_hawb(
                customer_id=customer_id,
                hawb=hawb
            )

            # 5. Check if order exists in HTC
            htc_order_number = self._htc_service.lookup_order_by_customer_and_hawb(
                customer_id=customer_id,
                hawb=hawb
            )

            if htc_order_number is not None:
                # Order exists in HTC - create pending updates
                # Pass duplicate count so handler can set manual_review status if needed
                action_taken = self._handle_existing_order(
                    customer_id=customer_id,
                    hawb=hawb,
                    htc_order_number=htc_order_number,
                    sub_run_id=sub_run_id,
                    output_channel_data=output_channel_data,
                    htc_order_count=htc_order_count,
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
        sub_run_id: Optional[int],
        output_channel_data: Dict[str, Any],
        htc_order_count: int = 1,
    ) -> str:
        """
        Handle data for a HAWB that already exists in HTC.

        First compares incoming field values against current HTC values.
        Only fields with different values are processed as pending updates.
        Fields with identical values are ignored.

        Gets or creates a single pending_update record for this (customer_id, hawb)
        with status='pending'. Multiple field changes accumulate into the same
        record via history until user approves/rejects.

        If htc_order_count > 1, sets status to 'manual_review' instead of 'pending'
        to flag that multiple HTC orders exist and require manual intervention.

        Logic:
        1. Fetch current HTC field values
        2. Filter to only fields where new value differs from HTC value
        3. If no differences, return early
        4. If differences exist:
           - If no existing pending_update: create new one
           - For each differing field:
             - If no history: set value directly
             - If history exists and value matches pending: add history (not selected)
             - If history exists and value differs: conflict - clear selections, set NULL

        Args:
            customer_id: Customer ID
            hawb: HAWB string
            htc_order_number: The existing HTC order number
            sub_run_id: Source sub-run ID
            output_channel_data: Field values from pipeline
            htc_order_count: Number of HTC orders found (> 1 triggers manual_review)

        Returns:
            Action taken string for logging
        """
        logger.info(f"HAWB '{hawb}' exists in HTC as order {htc_order_number} - checking for differences")

        # Filter to valid field names only (exclude 'hawb' itself)
        field_data = self._extract_valid_fields(output_channel_data)

        if not field_data:
            logger.warning(f"No valid fields to update for HAWB '{hawb}'")
            return "no_valid_fields"

        # Fetch current HTC field values for comparison
        htc_fields = self._htc_service.get_order_fields(htc_order_number)
        if not htc_fields:
            logger.warning(f"Could not fetch HTC fields for order {htc_order_number} - skipping update")
            return "htc_lookup_failed"

        # Filter to only fields that differ from current HTC values
        differing_fields: Dict[str, Any] = {}

        # Fields that need special comparison logic
        ADDRESS_FIELDS = {"pickup_address", "delivery_address"}
        DIMS_FIELDS = {"dims"}

        for field_name, new_value in field_data.items():
            new_value_str = str(new_value)

            if field_name in DIMS_FIELDS:
                # Dims need semantic comparison, not string comparison
                htc_dims = getattr(htc_fields, field_name, None)
                if self._dims_are_equal(new_value, htc_dims):
                    logger.debug(f"Field '{field_name}' unchanged (dims semantically equal)")
                else:
                    differing_fields[field_name] = new_value
                    logger.debug(f"Field '{field_name}' differs: dims content changed")

            elif field_name in ADDRESS_FIELDS:
                # For address fields, compare by ID instead of string
                # This handles cases where addresses with/without zip resolve to same ID
                if field_name == "pickup_address":
                    current_address_id = htc_fields.pickup_address_id
                    current_address_str = htc_fields.pickup_address
                else:  # delivery_address
                    current_address_id = htc_fields.delivery_address_id
                    current_address_str = htc_fields.delivery_address

                logger.info(
                    f"[ADDRESS COMPARE] {field_name}: "
                    f"current_id={current_address_id}, current_str='{current_address_str}', "
                    f"new_str='{new_value_str}'"
                )

                # Look up the ID for the new address string (doesn't create if not found)
                new_address_id = self._htc_service.find_address_id(new_value_str)
                logger.info(f"[ADDRESS COMPARE] find_address_id('{new_value_str}') returned: {new_address_id}")

                if new_address_id is None:
                    # New address doesn't exist in HTC yet - definitely different
                    differing_fields[field_name] = new_value
                    logger.info(f"[ADDRESS COMPARE] Field '{field_name}' differs: new address not found in HTC (will create on update)")
                elif new_address_id != current_address_id:
                    # Address exists but has different ID - real change
                    differing_fields[field_name] = new_value
                    logger.info(f"[ADDRESS COMPARE] Field '{field_name}' differs: HTC ID={current_address_id} vs new ID={new_address_id}")
                else:
                    # Same address ID - no real change despite string difference
                    logger.info(f"[ADDRESS COMPARE] Field '{field_name}' unchanged (same address ID: {new_address_id})")
            else:
                # Non-address fields: use string comparison
                htc_value = getattr(htc_fields, field_name, None)
                # Normalize HTC value for comparison (None -> "", and convert to string)
                htc_value_str = str(htc_value) if htc_value is not None else ""

                if new_value_str != htc_value_str:
                    differing_fields[field_name] = new_value
                    logger.debug(f"Field '{field_name}' differs: HTC='{htc_value_str}' vs new='{new_value_str}'")
                else:
                    logger.debug(f"Field '{field_name}' unchanged: '{new_value_str}'")

        if not differing_fields:
            logger.info(f"No field differences found for HAWB '{hawb}' - no pending update needed")
            return "no_changes"

        logger.info(f"Found {len(differing_fields)} field(s) with differences for HAWB '{hawb}': {list(differing_fields.keys())}")

        # Replace field_data with only the differing fields
        field_data = differing_fields

        # Check if there's an active (status='pending') pending_update for this combo
        pending_update = self._pending_update_repo.get_active_by_customer_and_hawb(customer_id, hawb)
        was_created = pending_update is None

        if was_created:
            # Check if this needs manual review due to duplicate HTC orders
            is_duplicate = htc_order_count > 1

            if is_duplicate:
                logger.warning(
                    f"Multiple HTC orders ({htc_order_count}) found for customer {customer_id}, "
                    f"HAWB '{hawb}' - flagging pending update for manual review"
                )

            # Create new pending update
            # Don't set htc_order_number if there are duplicates (user must check manually)
            pending_update = self._pending_update_repo.create(
                PendingUpdateCreate(
                    customer_id=customer_id,
                    hawb=hawb,
                    htc_order_number=None if is_duplicate else htc_order_number,
                )
            )

            # Set status to manual_review if duplicates exist
            if is_duplicate:
                self._pending_update_repo.update(pending_update.id, cast(PendingUpdateUpdate, {
                    "status": "manual_review",
                }))
                logger.info(f"Created new pending update {pending_update.id} for HAWB '{hawb}' (status: manual_review, no htc_order_number)")
            else:
                logger.info(f"Created new pending update {pending_update.id} for HAWB '{hawb}'")

            # For new pending update, add history and set all fields directly
            history_creates = []
            field_updates: Dict[str, Any] = {}

            for field_name, new_value in field_data.items():
                new_value_str = str(new_value)

                # Add history record with is_selected=True
                history_creates.append(
                    PendingUpdateHistoryCreate(
                        pending_update_id=pending_update.id,
                        sub_run_id=sub_run_id,
                        field_name=field_name,
                        field_value=new_value_str,
                        is_selected=True,
                    )
                )

                # Set field value directly
                field_updates[field_name] = new_value_str

            # Create history records
            self._pending_update_history_repo.create_batch(history_creates)
            logger.info(f"Added {len(history_creates)} history records for new pending update {pending_update.id}")

            # Update field values
            if field_updates:
                field_updates["last_processed_at"] = datetime.now()
                self._pending_update_repo.update(pending_update.id, cast(PendingUpdateUpdate, field_updates))

        else:
            # Existing pending update - check for conflicts
            logger.info(f"Found existing pending update {pending_update.id} for HAWB '{hawb}'")

            history_creates: List[PendingUpdateHistoryCreate] = []
            field_updates: Dict[str, Any] = {}

            for field_name, new_value in field_data.items():
                new_value_str = str(new_value)

                # Check if field has existing history
                existing_history = self._pending_update_history_repo.get_by_field(
                    pending_update.id, field_name
                )

                if len(existing_history) == 0:
                    # No prior history - set new value and mark as selected
                    history_creates.append(
                        PendingUpdateHistoryCreate(
                            pending_update_id=pending_update.id,
                            sub_run_id=sub_run_id,
                            field_name=field_name,
                            field_value=new_value_str,
                            is_selected=True,
                        )
                    )
                    field_updates[field_name] = new_value_str
                    logger.debug(f"Field '{field_name}' has no history - setting to '{new_value_str}'")
                else:
                    # Has existing history - check if this exact value already exists
                    existing_values = {h.field_value for h in existing_history}

                    if new_value_str in existing_values:
                        # Value already exists in history - still add for sub-run tracking
                        # but don't select it (doesn't create a conflict since value is same)
                        history_creates.append(
                            PendingUpdateHistoryCreate(
                                pending_update_id=pending_update.id,
                                sub_run_id=sub_run_id,
                                field_name=field_name,
                                field_value=new_value_str,
                                is_selected=False,
                            )
                        )
                        logger.debug(f"Field '{field_name}' value '{new_value_str}' already in history - adding for sub-run tracking")
                        continue

                    # New value not in history - check for conflict
                    current_value = getattr(pending_update, field_name, None)

                    if current_value == new_value_str:
                        # Same as current value but not in history (shouldn't happen normally)
                        # Add history but don't select it
                        history_creates.append(
                            PendingUpdateHistoryCreate(
                                pending_update_id=pending_update.id,
                                sub_run_id=sub_run_id,
                                field_name=field_name,
                                field_value=new_value_str,
                                is_selected=False,
                            )
                        )
                        logger.debug(f"Field '{field_name}' value matches current - adding to history")
                    else:
                        # Different value - conflict!
                        # Clear all existing selections for this field
                        cleared_count = self._pending_update_history_repo.clear_selection_for_field(
                            pending_update.id, field_name
                        )
                        logger.debug(f"Cleared {cleared_count} selections for field '{field_name}'")

                        # Add new history as not selected
                        history_creates.append(
                            PendingUpdateHistoryCreate(
                                pending_update_id=pending_update.id,
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
                self._pending_update_history_repo.create_batch(history_creates)
                logger.info(f"Added {len(history_creates)} history records for existing pending update {pending_update.id}")

            # Apply field updates (including conflicts)
            if field_updates:
                field_updates["last_processed_at"] = datetime.now()
                self._pending_update_repo.update(pending_update.id, cast(PendingUpdateUpdate, field_updates))

        # Broadcast SSE event
        event_type = "pending_update_created" if was_created else "pending_update_updated"
        order_event_manager.broadcast_sync(event_type, {
            "id": pending_update.id,
            "hawb": hawb,
            "customer_id": customer_id,
            "htc_order_number": htc_order_number,
            "fields_changed": list(field_data.keys()),
        })

        return event_type

    def _handle_new_order(
        self,
        customer_id: int,
        hawb: str,
        sub_run_id: Optional[int],
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
                field_updates["last_processed_at"] = datetime.now()
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
                field_updates["last_processed_at"] = datetime.now()
                self._pending_order_repo.update(pending_order.id, cast(PendingOrderUpdate, field_updates))

        # Update status based on required fields
        self._update_pending_order_status(pending_order.id)

        # Note: HTC order creation is now handled by the HtcOrderWorker background process.
        # The pending order will stay at status="ready" until the worker picks it up.

        # Broadcast SSE event
        # Refresh to get updated status
        pending_order = self._pending_order_repo.get_by_id(pending_order.id)
        event_type = "pending_order_created" if was_created else "pending_order_updated"
        order_event_manager.broadcast_sync(event_type, {
            "id": pending_order.id,
            "hawb": hawb,
            "customer_id": customer_id,
            "status": pending_order.status if pending_order else "unknown",
            "fields_changed": list(field_data.keys()),
        })

        return event_type

    def _extract_valid_fields(self, output_channel_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract only valid field names from output channel data.

        Filters out 'hawb' (it's the key, not a field) and any unknown field names.
        Special handling for 'dims' field which needs JSON serialization.

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

            # Skip 'hawb_list' - it's processed into multiple HAWBs, not a field to store
            if field_name == "hawb_list":
                continue

            # Skip unknown field names
            if field_name not in VALID_FIELD_NAMES:
                logger.warning(f"Ignoring unknown field: {field_name}")
                continue

            # Skip None/empty values
            if value is None or value == "":
                continue

            # Special handling for dims - JSON serialize list/dict values
            if field_name == "dims":
                if isinstance(value, (list, dict)):
                    value = json.dumps(value)
                # If already a string (shouldn't happen normally), keep as-is

            valid_fields[field_name] = value

        return valid_fields

    def _dims_are_equal(self, new_dims: Any, htc_dims_json: Optional[str]) -> bool:
        """
        Compare dims semantically, not by string equality.

        Handles differences in:
        - Integer vs float representation (10 vs 10.0)
        - Extra fields in HTC (dim_weight) that pipeline doesn't output
        - Key ordering in JSON

        Args:
            new_dims: New dims value (could be list, dict, or JSON string)
            htc_dims_json: Current HTC dims as JSON string (or None)

        Returns:
            True if dims are semantically equal, False otherwise
        """
        # Normalize new_dims to a list
        if isinstance(new_dims, str):
            try:
                new_dims = json.loads(new_dims)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse new_dims as JSON: {new_dims}")
                return False

        # Normalize htc_dims to a list
        if htc_dims_json is None or htc_dims_json == "":
            htc_dims = []
        else:
            try:
                htc_dims = json.loads(htc_dims_json)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse htc_dims_json as JSON: {htc_dims_json}")
                return False

        # Handle single dim object (wrap in list)
        if isinstance(new_dims, dict):
            new_dims = [new_dims]
        if isinstance(htc_dims, dict):
            htc_dims = [htc_dims]

        # Both should be lists now
        if not isinstance(new_dims, list) or not isinstance(htc_dims, list):
            logger.warning(f"Dims not in expected format: new={type(new_dims)}, htc={type(htc_dims)}")
            return False

        # Different number of dims = not equal
        if len(new_dims) != len(htc_dims):
            logger.debug(f"Dims count differs: new={len(new_dims)}, htc={len(htc_dims)}")
            return False

        # Empty dims on both sides = equal
        if len(new_dims) == 0:
            return True

        # Extract comparable fields from each dim, normalize to floats
        # Only compare: height, length, width, qty, weight (not dim_weight which is calculated)
        def normalize_dim(dim: dict) -> tuple:
            """Extract and normalize the comparable fields from a dim."""
            return (
                float(dim.get("height", 0) or 0),
                float(dim.get("length", 0) or 0),
                float(dim.get("width", 0) or 0),
                float(dim.get("qty", 1) or 1),
                float(dim.get("weight", 0) or 0),
            )

        # Convert both to sets of normalized tuples for order-independent comparison
        try:
            new_set = set(normalize_dim(d) for d in new_dims)
            htc_set = set(normalize_dim(d) for d in htc_dims)
        except (TypeError, KeyError) as e:
            logger.warning(f"Failed to normalize dims for comparison: {e}")
            return False

        if new_set == htc_set:
            logger.debug(f"Dims are semantically equal: {new_set}")
            return True
        else:
            logger.debug(f"Dims differ: new={new_set}, htc={htc_set}")
            return False

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
        by_field: dict[str, list] = {}
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
                logger.debug(f"Unresolved conflict found for field '{field_name}' on pending order {pending_order_id}")
                return True

        return False

    def _update_pending_order_status(self, pending_order_id: int) -> None:
        """
        Update pending order status based on required fields and conflicts.

        Only updates status for orders in 'incomplete' or 'ready' states.
        Does not modify orders that are 'processing', 'created', or 'failed'.

        Status logic:
        - 'incomplete': One or more required fields are null, OR any field has unresolved conflicts
        - 'ready': All required fields are non-null AND no conflicts (queued for HTC worker)
        - 'processing': Being processed by worker (don't change)
        - 'created': Already created in HTC (don't change)
        - 'failed': HTC creation failed (don't change - user must retry)

        Args:
            pending_order_id: ID of the pending order to update
        """
        pending_order = self._pending_order_repo.get_by_id(pending_order_id)
        if not pending_order:
            logger.error(f"Pending order {pending_order_id} not found for status update")
            return

        # Don't change status if already in a terminal or processing state
        if pending_order.status in ("created", "processing", "failed"):
            logger.debug(f"Pending order {pending_order_id} status is '{pending_order.status}', skipping status update")
            return

        # Check if all required fields are set
        all_required_set = True
        for field_name in REQUIRED_FIELDS:
            value = getattr(pending_order, field_name, None)
            if value is None:
                all_required_set = False
                logger.debug(f"Required field '{field_name}' is missing for pending order {pending_order_id}")
                break

        # Check for unresolved conflicts (in any field, required or optional)
        has_conflicts = self._has_unresolved_conflicts(pending_order_id)
        if has_conflicts:
            logger.debug(f"Pending order {pending_order_id} has unresolved conflicts")

        # Ready only if all required fields set AND no unresolved conflicts
        new_status = "ready" if (all_required_set and not has_conflicts) else "incomplete"

        if pending_order.status != new_status:
            self._pending_order_repo.update(pending_order_id, {
                "status": new_status,
                "last_processed_at": datetime.now(),
            })
            logger.info(f"Updated pending order {pending_order_id} status: {pending_order.status} -> {new_status}")

    def cleanup_sub_run_contributions(self, sub_run_id: int) -> dict:
        """
        Clean up pending order contributions from a sub-run being deleted/reprocessed.

        This should be called BEFORE the sub-run is deleted to properly clean up
        the pending order data that was contributed by that sub-run.

        Flow:
        1. Delete all history entries for this sub-run
        2. For each affected pending order and field:
           - Recalculate field value from remaining history
           - Update pending order status
        3. Delete pending orders that have no remaining history

        Args:
            sub_run_id: ID of the sub-run being deleted

        Returns:
            Dict with cleanup statistics:
            - deleted_history_count: Number of history entries deleted
            - affected_pending_orders: Number of pending orders affected
            - deleted_pending_orders: Number of pending orders deleted (had no remaining history)
            - fields_recalculated: Total number of fields recalculated
        """
        logger.info(f"Cleaning up pending order contributions from sub-run {sub_run_id}")

        # 1. Delete history entries and get affected orders/fields
        result = self._pending_order_history_repo.delete_by_sub_run_id(sub_run_id)
        deleted_history_count = result["deleted_count"]
        affected_orders = result["affected_orders"]

        if deleted_history_count == 0:
            logger.info(f"No pending order contributions found for sub-run {sub_run_id}")
            return {
                "deleted_history_count": 0,
                "affected_pending_orders": 0,
                "deleted_pending_orders": 0,
                "fields_recalculated": 0,
            }

        logger.info(f"Deleted {deleted_history_count} history entries affecting {len(affected_orders)} pending orders")

        # 2. Recalculate field values for each affected pending order
        fields_recalculated = 0
        deleted_pending_orders = 0

        for pending_order_id, field_names in affected_orders.items():
            # Check if pending order still has any history
            remaining_history = self._pending_order_history_repo.get_by_pending_order_id(pending_order_id)

            if not remaining_history:
                # No history remaining - delete the pending order
                # But only if it hasn't been created in HTC yet
                pending_order = self._pending_order_repo.get_by_id(pending_order_id)
                if pending_order and pending_order.status not in ("created", "processing"):
                    self._pending_order_repo.delete(pending_order_id)
                    deleted_pending_orders += 1
                    logger.info(f"Deleted pending order {pending_order_id} (no remaining history)")
                continue

            # Recalculate each affected field
            for field_name in field_names:
                self._recalculate_field_value(pending_order_id, field_name)
                fields_recalculated += 1

            # Update status based on new field values
            self._update_pending_order_status(pending_order_id)

        logger.info(
            f"Sub-run {sub_run_id} cleanup complete: "
            f"{deleted_history_count} history entries deleted, "
            f"{fields_recalculated} fields recalculated, "
            f"{deleted_pending_orders} pending orders deleted"
        )

        return {
            "deleted_history_count": deleted_history_count,
            "affected_pending_orders": len(affected_orders),
            "deleted_pending_orders": deleted_pending_orders,
            "fields_recalculated": fields_recalculated,
        }

    def _recalculate_field_value(self, pending_order_id: int, field_name: str) -> None:
        """
        Recalculate a pending order field value based on remaining history.

        Logic:
        - If no history remains for field: set to NULL
        - If one entry with is_selected=True: keep that value
        - If no selected entry but only one unique value: auto-select it
        - If multiple unique values with no selection: conflict - set to NULL

        Args:
            pending_order_id: ID of the pending order
            field_name: Name of the field to recalculate
        """
        # Get remaining history for this field
        history_entries = self._pending_order_history_repo.get_by_field(pending_order_id, field_name)

        if not history_entries:
            # No history - set field to NULL
            self._pending_order_repo.update(pending_order_id, {
                field_name: None,
                "last_processed_at": datetime.now(),
            })
            logger.debug(f"Field '{field_name}' on pending order {pending_order_id}: no history, set to NULL")
            return

        # Check if there's a selected entry
        selected_entry = next((h for h in history_entries if h.is_selected), None)

        if selected_entry:
            # Keep the selected value
            self._pending_order_repo.update(pending_order_id, {
                field_name: selected_entry.field_value,
                "last_processed_at": datetime.now(),
            })
            logger.debug(f"Field '{field_name}' on pending order {pending_order_id}: kept selected value")
            return

        # No selected entry - check unique values
        unique_values = set(h.field_value for h in history_entries)

        if len(unique_values) == 1:
            # Only one unique value - auto-select the first entry
            value = history_entries[0].field_value
            self._pending_order_history_repo.update(history_entries[0].id, {"is_selected": True})
            self._pending_order_repo.update(pending_order_id, {
                field_name: value,
                "last_processed_at": datetime.now(),
            })
            logger.debug(f"Field '{field_name}' on pending order {pending_order_id}: auto-selected single value")
        else:
            # Multiple unique values - conflict, set to NULL
            self._pending_order_repo.update(pending_order_id, {
                field_name: None,
                "last_processed_at": datetime.now(),
            })
            logger.debug(
                f"Field '{field_name}' on pending order {pending_order_id}: "
                f"conflict ({len(unique_values)} values), set to NULL"
            )
