"""
Order Management Service

Unified service for pending action processing. Handles accumulation of field values
from sub-runs and manual input, execution against HTC, and user interactions.

Replaces the old OutputProcessingService and OrderManagementService.
"""
import logging
from typing import Any

from shared.types.pending_actions import (
    CleanupResult,
    ExecuteResult,
)

logger = logging.getLogger(__name__)


class OrderManagementService:
    """
    Unified service for pending action processing.

    Entry points:
    - process_sub_run_output: Called by EtoRunsService after pipeline execution
    - process_manual_input: Called by API for manual order creation
    - retry_failed_action: Called by API to retry failed execution

    User interactions:
    - resolve_conflict: Select value for conflicting field
    - set_user_value: Provide manual value override
    - set_field_approval: Toggle field inclusion for updates
    - reject_action: Reject pending action

    Cleanup:
    - cleanup_sub_run_contributions: Remove contributions when sub-run reprocessed
    """

    def __init__(self) -> None:
        """Initialize service with dependencies."""
        # TODO: Inject repositories and HTC service
        pass

    # ========== Accumulation Entry Points ==========

    def process_sub_run_output(self, sub_run_id: int) -> list[int]:
        """
        Process pipeline output from a sub-run.

        Fetches output_channel_data and customer_id from the sub-run's
        output execution record and associated template.

        Handles both single HAWB (hawb channel) and multiple HAWBs (hawb_list channel).
        Each HAWB gets its own pending action.

        Args:
            sub_run_id: ID of the completed sub-run

        Returns:
            List of pending_action_ids (one per HAWB found in output)
        """
        raise NotImplementedError()

    def process_manual_input(
        self,
        customer_id: int,
        hawb: str,
        field_values: dict[str, Any],
    ) -> int:
        """
        Process manually entered field values (no sub-run source).

        Validates field_values against ORDER_FIELDS. Unknown fields are rejected.
        If an active pending action exists for (customer_id, hawb), adds to it.
        Otherwise creates a new pending action.

        Auto-execution after reaching 'ready' status depends on system settings.

        Args:
            customer_id: Customer ID
            hawb: HAWB string (single value)
            field_values: Dict of field_name -> value (validated against ORDER_FIELDS)

        Returns:
            pending_action_id

        Raises:
            ValueError: If field_values contains invalid field names
        """
        raise NotImplementedError()

    # ========== Execution ==========

    def execute_action(self, pending_action_id: int) -> ExecuteResult:
        """
        Execute pending action against HTC (create or update order).

        Re-checks HTC state before executing (TOCTOU protection).
        For creates: sends all selected fields.
        For updates: sends only selected AND approved fields.

        Args:
            pending_action_id: ID of the pending action to execute

        Returns:
            ExecuteResult with success status, action_type, htc_order_number, error_message
        """
        raise NotImplementedError()

    def retry_failed_action(self, pending_action_id: int) -> None:
        """
        Re-attempt execution of a failed action.

        Preserves all field values and user modifications.
        Just retries the HTC write - no data re-extraction.

        Args:
            pending_action_id: ID of the failed pending action

        Raises:
            ValueError: If action is not in 'failed' status
        """
        raise NotImplementedError()

    # ========== User Interactions ==========

    def resolve_conflict(
        self,
        pending_action_id: int,
        field_name: str,
        selected_field_id: int,
    ) -> None:
        """
        User selects which value to use for a conflicting field.

        Sets is_selected=TRUE for the chosen value, FALSE for all others.
        Recalculates action status after resolution.

        Args:
            pending_action_id: ID of the pending action
            field_name: Name of the field with conflict
            selected_field_id: ID of the field value to select
        """
        raise NotImplementedError()

    def set_user_value(
        self,
        pending_action_id: int,
        field_name: str,
        value: Any,
    ) -> int:
        """
        User provides their own value for a field (overriding extracted data).

        Creates a new pending_action_fields row with sub_run_id=NULL.
        Sets is_selected=TRUE for this value, FALSE for all others.
        Recalculates action status after update.

        Args:
            pending_action_id: ID of the pending action
            field_name: Name of the field to set
            value: The value to set (will be validated/resolved based on field type)

        Returns:
            ID of the newly created field record
        """
        raise NotImplementedError()

    def set_field_approval(
        self,
        pending_action_id: int,
        field_name: str,
        is_approved: bool,
    ) -> None:
        """
        User toggles whether a field should be included in an update.

        Sets is_approved_for_update on the currently selected value.
        Only relevant for action_type='update'.

        Args:
            pending_action_id: ID of the pending action
            field_name: Name of the field to toggle
            is_approved: Whether to include this field in the update
        """
        raise NotImplementedError()

    def reject_action(
        self,
        pending_action_id: int,
        reason: str | None = None,
    ) -> None:
        """
        User rejects the pending action (will not be executed).

        Sets status to 'rejected'. Action cannot be retried after rejection.

        Args:
            pending_action_id: ID of the pending action to reject
            reason: Optional reason for rejection (stored for audit)
        """
        raise NotImplementedError()

    # ========== Cleanup ==========

    def cleanup_sub_run_contributions(self, sub_run_id: int) -> CleanupResult:
        """
        Remove all field contributions from a sub-run being reprocessed or deleted.

        Called by EtoRunsService when a sub-run is reprocessed or deleted.

        Steps:
        1. Delete all pending_action_fields WHERE sub_run_id = ?
        2. For each affected pending_action:
           a. Check if any extracted fields remain (sub_run_id IS NOT NULL)
           b. If NO extracted fields remain: delete the entire pending_action
           c. If extracted fields remain: recalculate status

        Args:
            sub_run_id: ID of the sub-run being reprocessed/deleted

        Returns:
            CleanupResult with affected action IDs and deletion info
        """
        raise NotImplementedError()
