"""
Order Management Service

Unified service for pending action processing. Handles accumulation of field values
from output executions and manual input, execution against HTC, and user interactions.
"""
import json
import logging
from typing import Any

from shared.database import DatabaseConnectionManager
from shared.database.repositories.pending_action import PendingActionRepository
from shared.database.repositories.pending_action_field import PendingActionFieldRepository
from shared.database.repositories.eto_sub_run_output_execution import EtoSubRunOutputExecutionRepository

from shared.types.pending_actions import (
    PendingAction,
    PendingActionCreate,
    PendingActionUpdate,
    PendingActionFieldCreate,
    PendingActionType,
    PendingActionStatus,
    CleanupResult,
    ExecuteResult,
    ORDER_FIELDS,
    REQUIRED_ORDER_FIELDS,
)

from features.htc_integration import HtcIntegrationService

from .transformers import FIELD_TRANSFORMERS

logger = logging.getLogger(__name__)

class OrderManagementService:
    """
    Unified service for pending action processing.

    Main Entry Point:
    - process_output_execution: Called by EtoRunsService after pipeline execution

    User Interactions:
    - resolve_conflict: Select value for conflicting field
    - set_user_value: Provide manual value override
    - set_field_approval: Toggle field inclusion for updates
    - reject_action: Reject pending action

    Execution:
    - execute_action: Execute pending action against HTC
    - retry_failed_action: Retry failed execution

    Cleanup:
    - cleanup_output_execution_contributions: Remove contributions when output execution reprocessed
    """

    def __init__(
        self,
        connection_manager: DatabaseConnectionManager,
        htc_integration_service: HtcIntegrationService,
    ) -> None:
        """Initialize service with dependencies."""
        self.connection_manager = connection_manager
        self.htc_service = htc_integration_service

        # Repositories
        self.pending_action_repo = PendingActionRepository(connection_manager)
        self.pending_action_field_repo = PendingActionFieldRepository(connection_manager)
        self.output_execution_repo = EtoSubRunOutputExecutionRepository(connection_manager)

    # ========== Main Entry Point ==========

    def process_output_execution(self, output_execution_id: int) -> PendingAction:
        """
        Main entry point - processes a single output execution record.

        Called by EtoRunsService after creating the output_execution data snapshot.

        Args:
            output_execution_id: ID of the output execution to process

        Returns:
            The created or updated PendingAction
        """
        # 1. Load the data snapshot
        output_execution = self.output_execution_repo.get_by_id(output_execution_id)
        if not output_execution:
            raise ValueError(f"Output execution {output_execution_id} not found")

        # 2. Determine action type by checking HTC for existing orders
        action_type, htc_order_number = self._determine_action_type(
            customer_id=output_execution.customer_id,
            hawb=output_execution.hawb,
        )

        # 3. Find or create the pending action record
        pending_action = self._get_or_create_pending_action(
            customer_id=output_execution.customer_id,
            hawb=output_execution.hawb,
            action_type=action_type,
            htc_order_number=htc_order_number,
        )

        # 4. Transform output channels -> order fields
        order_fields = self._transform_output_to_fields(
            output_channel_data=output_execution.output_channel_data,
        )

        # 5. Add field values to pending action (handles conflict detection)
        self._add_fields_to_action(
            pending_action_id=pending_action.id,
            output_execution_id=output_execution_id,
            fields=order_fields,
        )

        # 6. Recalculate action status based on current field state
        updated_action = self._recalculate_action_status(pending_action.id)

        return updated_action

    # ========== Sub-Methods (Processing) ==========

    def _determine_action_type(
        self,
        customer_id: int,
        hawb: str,
    ) -> tuple[PendingActionType, float | None]:
        """
        Check HTC to determine if this should be a create, update, or ambiguous action.

        Returns:
            Tuple of (action_type, htc_order_number)
            - ("create", None) if no existing order
            - ("update", order_number) if exactly one existing order
            - ("ambiguous", None) if multiple existing orders
        """
        # Count existing orders for this customer/HAWB
        order_count = self.htc_service.count_orders_by_customer_and_hawb(
            customer_id=customer_id,
            hawb=hawb,
        )

        if order_count == 0:
            logger.debug(f"No existing order for customer {customer_id}, HAWB '{hawb}' - action: create")
            return ("create", None)

        elif order_count == 1:
            # Get the order number for the update
            order_number = self.htc_service.lookup_order_by_customer_and_hawb(
                customer_id=customer_id,
                hawb=hawb,
            )
            logger.debug(f"Found existing order {order_number} for customer {customer_id}, HAWB '{hawb}' - action: update")
            return ("update", order_number)

        else:
            # Multiple orders exist - ambiguous situation requiring user resolution
            logger.warning(
                f"Multiple orders ({order_count}) found for customer {customer_id}, HAWB '{hawb}' - action: ambiguous"
            )
            return ("ambiguous", None)

    def _get_or_create_pending_action(
        self,
        customer_id: int,
        hawb: str,
        action_type: PendingActionType,
        htc_order_number: float | None,
    ) -> PendingAction:
        """
        Find existing active pending action or create a new one.

        If found, may update action_type/htc_order_number if they changed
        (e.g., order created in HTC since last check).
        """
        # Try to find existing active action
        existing = self.pending_action_repo.get_active_by_customer_hawb(
            customer_id=customer_id,
            hawb=hawb,
        )

        if existing is not None:
            # Check if we need to update action_type or htc_order_number
            needs_update = (
                existing.action_type != action_type or
                existing.htc_order_number != htc_order_number
            )

            if needs_update:
                logger.debug(
                    f"Updating pending action {existing.id}: "
                    f"action_type {existing.action_type} -> {action_type}, "
                    f"htc_order_number {existing.htc_order_number} -> {htc_order_number}"
                )
                return self.pending_action_repo.update(
                    action_id=existing.id,
                    updates=PendingActionUpdate(
                        action_type=action_type,
                        htc_order_number=htc_order_number,
                    ),
                )

            return existing

        # Create new pending action
        logger.debug(
            f"Creating new pending action for customer {customer_id}, "
            f"HAWB '{hawb}', action_type={action_type}"
        )
        return self.pending_action_repo.create(
            data=PendingActionCreate(
                customer_id=customer_id,
                hawb=hawb,
                action_type=action_type,
                htc_order_number=htc_order_number,
            ),
        )

    def _transform_output_to_fields(
        self,
        output_channel_data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Transform output channels -> order fields using ORDER_FIELDS definitions.

        Iterates over ORDER_FIELDS, extracts relevant source channels,
        and applies the appropriate transformer based on data_type.
        """
        result: dict[str, Any] = {}

        for field_name, field_def in ORDER_FIELDS.items():
            # Extract source channel values for this field
            source_values = {
                channel: output_channel_data.get(channel)
                for channel in field_def.source_channels
            }

            # Skip if no source channels have values
            if not any(v is not None for v in source_values.values()):
                continue

            # Get transformer for this data type
            transformer = FIELD_TRANSFORMERS.get(field_def.data_type)
            if not transformer:
                logger.warning(f"No transformer for data_type: {field_def.data_type}")
                continue

            # Transform and store
            field_value = transformer(source_values)
            if field_value is not None:
                result[field_name] = field_value

        return result

    def _add_fields_to_action(
        self,
        pending_action_id: int,
        output_execution_id: int,
        fields: dict[str, Any],
    ) -> None:
        """
        Add field values to pending action, handling conflict detection.

        For each field:
        - If no existing values: create with is_selected=True
        - If value matches existing: create with is_selected=False (duplicate)
        - If value differs: clear all selections, create with is_selected=False (conflict)
        """
        # Get all existing fields for this action
        existing_fields = self.pending_action_field_repo.get_fields_for_action(pending_action_id)

        # Group existing fields by field_name
        fields_by_name: dict[str, list[Any]] = {}
        for field in existing_fields:
            if field.field_name not in fields_by_name:
                fields_by_name[field.field_name] = []
            fields_by_name[field.field_name].append(field)

        for field_name, value in fields.items():
            existing_for_field = fields_by_name.get(field_name, [])

            # Serialize value for comparison (handles complex objects like LocationValue)
            new_value_json = self._serialize_value_for_comparison(value)

            if not existing_for_field:
                # No existing values - first value is auto-selected
                logger.debug(f"Adding first value for field '{field_name}' (auto-selected)")
                self.pending_action_field_repo.create(
                    data=PendingActionFieldCreate(
                        pending_action_id=pending_action_id,
                        output_execution_id=output_execution_id,
                        field_name=field_name,
                        value=value,
                        is_selected=True,
                    )
                )
            else:
                # Check if value matches any existing value
                value_matches = any(
                    self._serialize_value_for_comparison(existing.value) == new_value_json
                    for existing in existing_for_field
                )

                if value_matches:
                    # Duplicate value - add but don't select
                    logger.debug(f"Adding duplicate value for field '{field_name}'")
                    self.pending_action_field_repo.create(
                        data=PendingActionFieldCreate(
                            pending_action_id=pending_action_id,
                            output_execution_id=output_execution_id,
                            field_name=field_name,
                            value=value,
                            is_selected=False,
                        )
                    )
                else:
                    # Different value - conflict! Clear all selections
                    logger.debug(f"Conflict detected for field '{field_name}' - clearing selections")
                    self.pending_action_field_repo.clear_selection_for_field(
                        action_id=pending_action_id,
                        field_name=field_name,
                    )
                    self.pending_action_field_repo.create(
                        data=PendingActionFieldCreate(
                            pending_action_id=pending_action_id,
                            output_execution_id=output_execution_id,
                            field_name=field_name,
                            value=value,
                            is_selected=False,
                        )
                    )

    def _serialize_value_for_comparison(self, value: Any) -> str:
        """Serialize a value to JSON string for comparison purposes."""
        if hasattr(value, 'model_dump'):
            # Pydantic model
            return json.dumps(value.model_dump(), sort_keys=True)
        elif isinstance(value, list) and value and hasattr(value[0], 'model_dump'):
            # List of Pydantic models
            return json.dumps([v.model_dump() for v in value], sort_keys=True)
        else:
            return json.dumps(value, sort_keys=True)

    def _recalculate_action_status(self, pending_action_id: int) -> PendingAction:
        """
        Recalculate and update action status based on current field state.

        Status priority:
        1. "ambiguous" if action_type == "ambiguous"
        2. "conflict" if any field has unresolved conflicts
        3. "incomplete" if missing required fields
        4. "ready" if all requirements met

        Also updates denormalized counts:
        - required_fields_present
        - conflict_count
        """
        # Get current action state
        action = self.pending_action_repo.get_by_id(pending_action_id)
        if not action:
            raise ValueError(f"Pending action {pending_action_id} not found")

        # Get selected fields (the "current" values)
        selected_fields = self.pending_action_field_repo.get_selected_fields_for_action(pending_action_id)
        selected_field_names = set(selected_fields.keys())

        # Count values per field to detect unresolved conflicts
        value_counts = self.pending_action_field_repo.count_by_field_name(pending_action_id)

        # Calculate conflict count: fields with multiple values but no selection
        conflict_count = 0
        for field_name, count in value_counts.items():
            if count > 1 and field_name not in selected_field_names:
                conflict_count += 1

        # Calculate required fields present
        required_fields_present = len(selected_field_names.intersection(REQUIRED_ORDER_FIELDS))

        # Determine status based on priority
        new_status: PendingActionStatus
        if action.action_type == "ambiguous":
            new_status = "ambiguous"
        elif conflict_count > 0:
            new_status = "conflict"
        elif required_fields_present < len(REQUIRED_ORDER_FIELDS):
            new_status = "incomplete"
        else:
            new_status = "ready"

        # Update action with new status and counts
        updated_action = self.pending_action_repo.update(
            action_id=pending_action_id,
            updates=PendingActionUpdate(
                status=new_status,
                required_fields_present=required_fields_present,
                conflict_count=conflict_count,
            ),
        )

        logger.debug(
            f"Recalculated action {pending_action_id}: status={new_status}, "
            f"required_fields={required_fields_present}/{len(REQUIRED_ORDER_FIELDS)}, "
            f"conflicts={conflict_count}"
        )

        return updated_action

    # ========== Execution ==========

    def execute_action(self, pending_action_id: int) -> ExecuteResult:
        """
        Execute pending action against HTC (create or update order).

        Re-checks HTC state before executing (TOCTOU protection).
        For creates: sends all selected fields.
        For updates: sends only selected AND approved fields.
        """
        # TODO: Implement HTC execution
        raise NotImplementedError()

    def retry_failed_action(self, pending_action_id: int) -> None:
        """
        Re-attempt execution of a failed action.

        Preserves all field values and user modifications.
        Just retries the HTC write - no data re-extraction.
        """
        # TODO: Implement retry logic
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
        """
        # TODO: Implement conflict resolution
        raise NotImplementedError()

    def set_user_value(
        self,
        pending_action_id: int,
        field_name: str,
        value: Any,
    ) -> int:
        """
        User provides their own value for a field (overriding extracted data).

        Creates a new pending_action_fields row with output_execution_id=NULL.
        Sets is_selected=TRUE for this value, FALSE for all others.
        Recalculates action status after update.

        Returns:
            ID of the newly created field record
        """
        # TODO: Implement user value setting
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
        """
        # TODO: Implement field approval toggle
        raise NotImplementedError()

    def reject_action(
        self,
        pending_action_id: int,
        reason: str | None = None,
    ) -> None:
        """
        User rejects the pending action (will not be executed).

        Sets status to 'rejected'. Action cannot be retried after rejection.
        """
        # TODO: Implement rejection
        raise NotImplementedError()

    # ========== Cleanup ==========

    def cleanup_output_execution_contributions(self, output_execution_id: int) -> CleanupResult:
        """
        Remove all field contributions from an output execution being reprocessed or deleted.

        Called by EtoRunsService when an output execution is reprocessed or deleted.

        Steps:
        1. Find all pending_action_ids affected by this output_execution
        2. Delete all pending_action_fields WHERE output_execution_id = ?
        3. For each affected pending_action:
           a. Check if any extracted fields remain (output_execution_id IS NOT NULL)
           b. If NO extracted fields remain: delete the entire pending_action
           c. If extracted fields remain: recalculate status
        """
        # TODO: Implement cleanup
        raise NotImplementedError()
