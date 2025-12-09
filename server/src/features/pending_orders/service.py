"""
Pending Orders Service

Processes output channel data from pipeline executions.
Routes data to pending orders (new HAWBs) or pending updates (existing HAWBs in HTC).
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING
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
from features.pipeline_results.helpers.orders import OrderHelpers

if TYPE_CHECKING:
    from shared.database.connection import DatabaseConnectionManager
    from shared.database.data_database_manager import DataDatabaseManager

logger = get_logger(__name__)


class PendingOrdersService:
    """
    Service for processing output channel data into pending orders.

    Processes one output_execution record at a time. The EtoRunsService
    is responsible for creating the output_execution records (one per HAWB).

    Flow:
    1. Check if HAWB exists in HTC Open Orders table
    2. If exists: Create pending_updates records (one per field) for user approval
    3. If not exists:
       a. Get or create pending_order record
       b. Add history records for each field
       c. Recompute field values from history (handle conflicts)
       d. Update pending_order status based on required fields
    """

    def __init__(
        self,
        connection_manager: 'DatabaseConnectionManager',
        data_database_manager: 'DataDatabaseManager',
    ) -> None:
        """
        Initialize the service.

        Args:
            connection_manager: DatabaseConnectionManager for ETO database access
            data_database_manager: DataDatabaseManager for HTC Access database access
        """
        logger.debug("Initializing PendingOrdersService...")

        self._connection_manager = connection_manager
        self._data_database_manager = data_database_manager

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

        # Initialize HTC helpers
        self._order_helpers = OrderHelpers(
            data_database_manager=data_database_manager,
            database_name="htc_300_db"
        )

        logger.info("PendingOrdersService initialized successfully")

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
            htc_order_number = self._order_helpers.lookup_order_by_customer_and_hawb(
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

                # Add history record
                history_creates.append(
                    PendingOrderHistoryCreate(
                        pending_order_id=pending_order.id,
                        sub_run_id=sub_run_id,
                        field_name=field_name,
                        field_value=new_value_str,
                        is_selected=False,
                    )
                )

                # Set field value directly (no conflicts possible on first entry)
                field_updates[field_name] = new_value_str

            # Create history records
            self._pending_order_history_repo.create_batch(history_creates)
            logger.info(f"Added {len(history_creates)} history records for new pending order {pending_order.id}")

            # Update field values
            if field_updates:
                self._pending_order_repo.update(pending_order.id, field_updates)

        else:
            # Existing pending order - check for conflicts
            logger.info(f"Found existing pending order {pending_order.id} for HAWB '{hawb}'")

            history_creates = []
            field_updates: Dict[str, Any] = {}

            for field_name, new_value in field_data.items():
                new_value_str = str(new_value)

                # Add history record for provenance (always)
                history_creates.append(
                    PendingOrderHistoryCreate(
                        pending_order_id=pending_order.id,
                        sub_run_id=sub_run_id,
                        field_name=field_name,
                        field_value=new_value_str,
                        is_selected=False,
                    )
                )

                # Check if field has existing history
                existing_history = self._pending_order_history_repo.get_by_field(
                    pending_order.id, field_name
                )

                if len(existing_history) == 0:
                    # No prior history - just set the new value
                    field_updates[field_name] = new_value_str
                    logger.debug(f"Field '{field_name}' has no history - setting to '{new_value_str}'")
                else:
                    # Has existing history - check for conflict
                    current_value = getattr(pending_order, field_name, None)

                    if current_value is None:
                        # Field is already in conflict state or empty
                        # Don't change - user needs to resolve existing conflict first
                        logger.debug(f"Field '{field_name}' already NULL (conflict/empty) - keeping as NULL")
                    elif current_value == new_value_str:
                        # Same value - no change needed
                        logger.debug(f"Field '{field_name}' value matches - no change")
                    else:
                        # Different value - set to NULL to indicate conflict
                        field_updates[field_name] = None
                        logger.info(
                            f"Conflict detected for field '{field_name}': "
                            f"current='{current_value}' vs new='{new_value_str}' - setting to NULL"
                        )

            # Create history records
            self._pending_order_history_repo.create_batch(history_creates)
            logger.info(f"Added {len(history_creates)} history records for existing pending order {pending_order.id}")

            # Apply field updates (including conflicts)
            if field_updates:
                self._pending_order_repo.update(pending_order.id, field_updates)

        # Update status based on required fields
        self._update_pending_order_status(pending_order.id)

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

    def _recompute_pending_order_fields(self, pending_order_id: int) -> None:
        """
        Recompute all field values for a pending order based on history.

        For each field:
        - If user has selected a value (is_selected=True): use that value
        - If all history entries have the same value: use that value (auto-set)
        - If multiple different values exist: set field to NULL (conflict)

        Args:
            pending_order_id: ID of the pending order to update
        """
        logger.debug(f"Recomputing fields for pending order {pending_order_id}")

        updates: PendingOrderUpdate = {}

        for field_name in VALID_FIELD_NAMES:
            computed_value = self._compute_field_value(pending_order_id, field_name)
            updates[field_name] = computed_value  # type: ignore

        # Apply all field updates at once
        self._pending_order_repo.update(pending_order_id, updates)
        logger.debug(f"Updated {len(updates)} fields for pending order {pending_order_id}")

    def _compute_field_value(self, pending_order_id: int, field_name: str) -> Optional[str]:
        """
        Compute the value for a single field based on history.

        Logic:
        1. If a history entry is marked is_selected=True, use that value
        2. If all history entries have the same value, use it (consensus)
        3. If multiple different values exist, return None (conflict)
        4. If no history entries exist, return None (empty)

        Args:
            pending_order_id: Pending order ID
            field_name: Field name to compute

        Returns:
            The computed field value, or None if empty/conflict
        """
        # Check if user has selected a value
        selected = self._pending_order_history_repo.get_selected_for_field(
            pending_order_id, field_name
        )
        if selected:
            return selected.field_value

        # Get all unique values for this field
        unique_values = self._pending_order_history_repo.get_unique_values_for_field(
            pending_order_id, field_name
        )

        if len(unique_values) == 0:
            # No values - field is empty
            return None
        elif len(unique_values) == 1:
            # Single value or all agree - auto-set
            return unique_values[0]
        else:
            # Multiple different values - conflict, set to NULL
            logger.info(
                f"Conflict detected for field '{field_name}' on pending order {pending_order_id}: "
                f"{len(unique_values)} different values"
            )
            return None

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
