"""
Order Management Service

Unified service for pending action processing. Handles accumulation of field values
from output executions and manual input, execution against HTC, and user interactions.
"""
import logging
from typing import Any, Callable

from shared.database import DatabaseConnectionManager
from shared.database.repositories.pending_action import PendingActionRepository
from shared.database.repositories.pending_action_field import PendingActionFieldRepository
from shared.database.repositories.eto_sub_run_output_execution import EtoSubRunOutputExecutionRepository

from shared.types.pending_actions import (
    PendingAction,
    PendingActionCreate,
    PendingActionUpdate,
    PendingActionType,
    PendingActionStatus,
    CleanupResult,
    ExecuteResult,
    LocationValue,
    DimObject,
    ORDER_FIELDS,
    OrderFieldDataType,
)

logger = logging.getLogger(__name__)


# =========================
# Field Transformers
# =========================

# Transformer signature: (source_channel_values) -> transformed value
FieldTransformer = Callable[[dict[str, Any]], Any]


def transform_string_field(source_values: dict[str, Any]) -> str | None:
    """Passthrough - returns first non-None value as string."""
    for value in source_values.values():
        if value is not None:
            return str(value)
    return None


def transform_location_field(source_values: dict[str, Any]) -> LocationValue | None:
    """
    Combines company_name + address channels into LocationValue.

    Note: address_id resolution (HTC lookup) happens separately during execution,
    not during accumulation.
    """
    company_name = None
    address = None

    for key, value in source_values.items():
        if value is None:
            continue
        if "company_name" in key:
            company_name = value
        elif "address" in key:
            address = value

    if not company_name and not address:
        return None

    return LocationValue(
        address_id=None,  # Resolved during execution
        name=company_name or "",
        address=address or "",
    )


def transform_dims_field(source_values: dict[str, Any]) -> list[DimObject] | None:
    """Parses dims and calculates dim_weight for each entry."""
    raw_dims = source_values.get("dims")
    if not raw_dims or not isinstance(raw_dims, list):
        return None

    result = []
    for dim in raw_dims:
        try:
            dim_weight = (dim["length"] * dim["width"] * dim["height"]) / 144
            result.append(DimObject(
                length=dim["length"],
                width=dim["width"],
                height=dim["height"],
                qty=dim["qty"],
                weight=dim["weight"],
                dim_weight=dim_weight,
            ))
        except (KeyError, TypeError) as e:
            logger.warning(f"Invalid dims entry, skipping: {dim} - {e}")
            continue

    return result if result else None


# Registry: each data_type maps to its transformer
FIELD_TRANSFORMERS: dict[OrderFieldDataType, FieldTransformer] = {
    "string": transform_string_field,
    "location": transform_location_field,
    "dims": transform_dims_field,
}


# =========================
# Service
# =========================

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

    def __init__(self, connection_manager: DatabaseConnectionManager) -> None:
        """Initialize service with dependencies."""
        self.connection_manager = connection_manager

        # Repositories
        self.pending_action_repo = PendingActionRepository(connection_manager)
        self.pending_action_field_repo = PendingActionFieldRepository(connection_manager)
        self.output_execution_repo = EtoSubRunOutputExecutionRepository(connection_manager)

        # TODO: Inject HTC service for action type determination and execution

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
        # TODO: Implement HTC lookup
        # For now, assume create
        pass
        return ("create", None)

    def _get_or_create_pending_action(
        self,
        customer_id: int,
        hawb: str,
        action_type: PendingActionType,
        htc_order_number: float | None,
    ) -> PendingAction:
        """
        Find existing active pending action or create a new one.

        If found, may update action_type if it changed (e.g., order created in HTC since last check).
        """
        # TODO: Implement find or create logic
        pass

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
        # TODO: Implement field addition with conflict detection
        pass

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
        # TODO: Implement status recalculation
        pass

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
