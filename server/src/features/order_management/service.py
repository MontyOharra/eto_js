"""
Order Management Service

Unified service for pending action processing. Handles accumulation of field values
from output executions and manual input, execution against HTC, and user interactions.
"""
import json
import logging
from dataclasses import asdict
from typing import Any

from datetime import datetime, timezone

from shared.database import DatabaseConnectionManager
from shared.database.repositories.pending_action import PendingActionRepository
from shared.database.repositories.pending_action_field import PendingActionFieldRepository
from shared.database.repositories.eto_sub_run_output_execution import EtoSubRunOutputExecutionRepository
from shared.database.repositories.eto_run import EtoRunRepository
from shared.database.repositories.eto_sub_run import EtoSubRunRepository
from shared.database.repositories.pdf_file import PdfFileRepository

from shared.types.eto_runs import EtoRunCreate, EtoRunUpdate
from shared.types.eto_sub_runs import EtoSubRunCreate, EtoSubRunUpdate
from shared.types.eto_sub_run_output_executions import EtoSubRunOutputExecutionCreate
from shared.types.pdf_files import PdfFileCreate, PdfObjects, TextWord, GraphicRect, GraphicLine, GraphicCurve, Image, Table

from shared.types.pending_actions import (
    PendingAction,
    PendingActionCreate,
    PendingActionUpdate,
    PendingActionFieldCreate,
    PendingActionType,
    PendingActionStatus,
    PendingActionListView,
    PendingActionDetailView,
    PendingActionFieldView,
    ContributingSource,
    CleanupResult,
    ExecuteResult,
    ORDER_FIELDS,
    REQUIRED_ORDER_FIELDS,
    OPTIONAL_ORDER_FIELDS,
)

from features.htc_integration import HtcIntegrationService
from shared.events.order_events import order_event_manager

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
        self.pending_action_repo = PendingActionRepository(connection_manager=connection_manager)
        self.pending_action_field_repo = PendingActionFieldRepository(connection_manager=connection_manager)
        self.output_execution_repo = EtoSubRunOutputExecutionRepository(connection_manager=connection_manager)

        # Additional repositories for mock data creation
        self.eto_run_repo = EtoRunRepository(connection_manager=connection_manager)
        self.eto_sub_run_repo = EtoSubRunRepository(connection_manager=connection_manager)
        self.pdf_file_repo = PdfFileRepository(connection_manager=connection_manager)

    # ========== Main Entry Point ==========

    def process_output_execution(self, output_execution_id: int) -> PendingAction | None:
        """
        Main entry point - processes a single output execution record.

        Called by EtoRunsService after creating the output_execution data snapshot.

        Args:
            output_execution_id: ID of the output execution to process

        Returns:
            The created or updated PendingAction, or None if the output had no
            changes compared to HTC (for updates only - creates always return an action)
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

        # 3. Transform output channels -> order fields
        order_fields = self._transform_output_to_fields(
            output_channel_data=output_execution.output_channel_data,
        )

        # 3b. Resolve address IDs for location fields
        order_fields = self._resolve_address_ids(order_fields)

        # 3c. For updates, filter out fields that match current HTC values BEFORE
        # creating the pending action. If no fields differ, skip entirely.
        if action_type == "update" and htc_order_number is not None:
            order_fields = self._filter_unchanged_fields_for_storage(
                order_fields, htc_order_number
            )
            if not order_fields:
                logger.info(
                    f"No changed fields for update on HAWB '{output_execution.hawb}' - "
                    f"skipping pending action creation"
                )
                return None

        # 4. Check if pending action already exists (for event type determination)
        existing_action = self.pending_action_repo.get_active_by_customer_hawb(
            customer_id=output_execution.customer_id,
            hawb=output_execution.hawb,
        )
        is_new_action = existing_action is None

        # 5. Find or create the pending action record
        pending_action = self._get_or_create_pending_action(
            customer_id=output_execution.customer_id,
            hawb=output_execution.hawb,
            action_type=action_type,
            htc_order_number=htc_order_number,
        )

        # 6. Add field values to pending action (handles conflict detection)
        self._add_fields_to_action(
            pending_action_id=pending_action.id,
            output_execution_id=output_execution_id,
            fields=order_fields,
        )

        # 7. Recalculate action status based on current field state
        updated_action = self._recalculate_action_status(pending_action.id)

        # 8. Broadcast event for real-time UI updates
        event_type = "pending_action_created" if is_new_action else "pending_action_updated"
        order_event_manager.broadcast_sync(
            event_type,
            {
                "id": updated_action.id,
                "status": updated_action.status,
                "action_type": updated_action.action_type,
                "hawb": updated_action.hawb,
                "customer_id": updated_action.customer_id,
            }
        )

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

    def _resolve_address_ids(self, order_fields: dict[str, Any]) -> dict[str, Any]:
        """
        Resolve address IDs for location fields by looking up addresses in HTC.

        For pickup_location and delivery_location fields, if address_id is None
        but address is present, attempts to find a matching address in the HTC database.

        Args:
            order_fields: Dict of transformed order fields

        Returns:
            Updated order_fields with resolved address IDs
        """
        location_fields = ["pickup_location", "delivery_location"]

        for field_name in location_fields:
            if field_name not in order_fields:
                continue

            location = order_fields[field_name]

            # Handle both dict and LocationValue objects
            if hasattr(location, "address_id"):
                # LocationValue object
                if location.address_id is not None:
                    continue  # Already has an address_id

                address = location.address
                if not address:
                    continue

                # Try to find address in HTC
                address_id = self.htc_service.find_address_id(address)
                if address_id is not None:
                    logger.debug(f"Resolved {field_name} address_id: {address_id}")
                    # Create new LocationValue with resolved ID
                    from shared.types.pending_actions import LocationValue
                    order_fields[field_name] = LocationValue(
                        address_id=int(address_id),
                        name=location.name,
                        address=location.address,
                    )
                else:
                    logger.debug(f"Could not resolve address for {field_name}: {address}")

            elif isinstance(location, dict):
                # Already a dict (e.g., from model_dump)
                if location.get("address_id") is not None:
                    continue

                address = location.get("address")
                if not address:
                    continue

                address_id = self.htc_service.find_address_id(address)
                if address_id is not None:
                    logger.debug(f"Resolved {field_name} address_id: {address_id}")
                    location["address_id"] = int(address_id)
                else:
                    logger.debug(f"Could not resolve address for {field_name}: {address}")

        return order_fields

    def _filter_unchanged_fields_for_storage(
        self,
        order_fields: dict[str, Any],
        htc_order_number: float,
    ) -> dict[str, Any]:
        """
        Filter out fields that match current HTC values before storage.

        For updates, we only want to store fields that actually differ from HTC.
        This ensures that 'contributions' only show actual changes.

        Args:
            order_fields: Transformed order fields to potentially store
            htc_order_number: HTC order number to fetch current values

        Returns:
            Filtered dict containing only fields that differ from HTC
        """
        # Fetch current HTC values
        htc_fields = self.htc_service.get_order_fields(order_number=htc_order_number)
        if htc_fields is None:
            logger.warning(f"Could not fetch HTC fields for order {htc_order_number}, storing all fields")
            return order_fields

        # Transform HTC values to match our field structure
        from features.order_management.transformers import transform_htc_values_to_order_fields
        from dataclasses import asdict
        current_htc_values = transform_htc_values_to_order_fields(asdict(htc_fields))

        filtered: dict[str, Any] = {}
        location_fields = {"pickup_location", "delivery_location"}

        for field_name, proposed_value in order_fields.items():
            htc_value = current_htc_values.get(field_name)

            # If HTC has no value for this field, it's a new value - include it
            if htc_value is None:
                logger.debug(f"Field '{field_name}': HTC has no value, including")
                filtered[field_name] = proposed_value
                continue

            # Location fields: compare by address_id only
            if field_name in location_fields:
                proposed_id = None
                htc_id = None

                # Extract proposed address_id
                if isinstance(proposed_value, dict):
                    proposed_id = proposed_value.get("address_id")
                elif hasattr(proposed_value, "address_id"):
                    proposed_id = proposed_value.address_id

                # Extract HTC address_id
                if isinstance(htc_value, dict):
                    htc_id = htc_value.get("address_id")

                # If proposed address_id is null, include (needs resolution)
                if proposed_id is None:
                    logger.debug(f"Field '{field_name}': proposed address_id is None, including")
                    filtered[field_name] = proposed_value
                    continue

                # If address_ids match, exclude
                if proposed_id == htc_id:
                    logger.debug(f"Field '{field_name}': address_ids match ({proposed_id}), excluding")
                    continue

                # Different address_ids - include
                logger.debug(f"Field '{field_name}': address_ids differ ({proposed_id} vs {htc_id}), including")
                filtered[field_name] = proposed_value
                continue

            # Normalize for comparison
            proposed_normalized = self._normalize_value_for_comparison(proposed_value)
            htc_normalized = self._normalize_value_for_comparison(htc_value)

            if proposed_normalized != htc_normalized:
                logger.debug(f"Field '{field_name}': values differ, including")
                filtered[field_name] = proposed_value
            else:
                logger.debug(f"Field '{field_name}': values match, excluding")

        return filtered

    def _normalize_value_for_comparison(self, value: Any) -> str:
        """Normalize a value to a string for comparison."""
        if isinstance(value, str):
            return value.strip()
        elif hasattr(value, 'model_dump'):
            # Single Pydantic model
            return json.dumps(value.model_dump(), sort_keys=True)
        elif isinstance(value, list) and value and hasattr(value[0], 'model_dump'):
            # List of Pydantic models (e.g., list[DimObject])
            return json.dumps([v.model_dump() for v in value], sort_keys=True)
        else:
            return json.dumps(value, sort_keys=True)

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
        - If value matches existing: skip (duplicate - no point storing same value twice)
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
                    # Duplicate value - skip entirely (no point storing identical values)
                    logger.debug(f"Skipping duplicate value for field '{field_name}'")
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

    def _filter_unchanged_fields(
        self,
        fields: dict[str, list[PendingActionFieldView]],
        current_htc_values: dict[str, Any],
    ) -> dict[str, list[PendingActionFieldView]]:
        """
        Filter out fields where the proposed value matches the current HTC value.

        For updates, we only want to show fields that actually differ from HTC.

        Rules:
        - If field has multiple values (conflict), always show it (user must resolve)
        - If field has single value or selected value, compare to HTC value
        - For location fields: compare by address_id only
          - If proposed address_id is null → always include (needs resolution)
          - If address_ids match → exclude (same address)
        - For other fields: JSON-normalized comparison
        """
        filtered: dict[str, list[PendingActionFieldView]] = {}
        location_fields = {"pickup_location", "delivery_location"}

        for field_name, field_values in fields.items():
            htc_value = current_htc_values.get(field_name)

            # If HTC has no value for this field, it's a new value - include it
            if htc_value is None:
                filtered[field_name] = field_values
                continue

            # If multiple values exist (conflict), always show for user resolution
            if len(field_values) > 1:
                # Check if there's a selected value
                selected = [fv for fv in field_values if fv.is_selected]
                if not selected:
                    # No selection yet - conflict, show all
                    filtered[field_name] = field_values
                    continue
                # Has selection - compare selected value to HTC
                proposed_value = selected[0].value
            else:
                # Single value
                proposed_value = field_values[0].value

            # Location fields: compare by address_id only
            if field_name in location_fields:
                proposed_id = None
                htc_id = None

                # Extract proposed address_id
                if isinstance(proposed_value, dict):
                    proposed_id = proposed_value.get("address_id")
                elif hasattr(proposed_value, "address_id"):
                    proposed_id = proposed_value.address_id

                # Extract HTC address_id
                if isinstance(htc_value, dict):
                    htc_id = htc_value.get("address_id")
                elif hasattr(htc_value, "address_id"):
                    htc_id = htc_value.address_id

                # If proposed address_id is null, it's always an update (needs resolution)
                if proposed_id is None:
                    filtered[field_name] = field_values
                    continue

                # If address_ids match, exclude (same address)
                if proposed_id == htc_id:
                    continue  # Same address - not an update

                # Different address_ids - include
                filtered[field_name] = field_values
                continue

            # String fields: normalize whitespace before comparison
            if isinstance(proposed_value, str) and isinstance(htc_value, str):
                proposed_normalized = proposed_value.strip()
                htc_normalized = htc_value.strip()

                if proposed_normalized != htc_normalized:
                    filtered[field_name] = field_values
                continue

            # Other fields: JSON-normalized comparison
            try:
                proposed_normalized = json.dumps(proposed_value, sort_keys=True)
                htc_normalized = json.dumps(htc_value, sort_keys=True)

                if proposed_normalized != htc_normalized:
                    filtered[field_name] = field_values
            except (TypeError, ValueError):
                # Can't serialize for comparison - include to be safe
                filtered[field_name] = field_values

        return filtered

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

        # Calculate required and optional fields present
        required_fields_present = len(selected_field_names.intersection(REQUIRED_ORDER_FIELDS))
        optional_fields_present = len(selected_field_names.intersection(OPTIONAL_ORDER_FIELDS))

        # Determine status based on priority
        # Note: "incomplete" only applies to creates - updates don't have required fields
        new_status: PendingActionStatus
        if action.action_type == "ambiguous":
            new_status = "ambiguous"
        elif conflict_count > 0:
            new_status = "conflict"
        elif action.action_type == "create" and required_fields_present < len(REQUIRED_ORDER_FIELDS):
            new_status = "incomplete"
        else:
            new_status = "ready"

        # Update action with new status, counts, and last_processed_at
        updated_action = self.pending_action_repo.update(
            action_id=pending_action_id,
            updates=PendingActionUpdate(
                status=new_status,
                required_fields_present=required_fields_present,
                optional_fields_present=optional_fields_present,
                conflict_count=conflict_count,
                last_processed_at=datetime.now(timezone.utc),
            ),
        )

        logger.debug(
            f"Recalculated action {pending_action_id}: status={new_status}, "
            f"required={required_fields_present}/{len(REQUIRED_ORDER_FIELDS)}, "
            f"optional={optional_fields_present}/{len(OPTIONAL_ORDER_FIELDS)}, "
            f"conflicts={conflict_count}"
        )

        return updated_action

    # ========== Execution ==========

    def approve_action(self, pending_action_id: int) -> ExecuteResult:
        """
        Approve a pending action for execution.

        For now, this sets the status to 'completed' and logs what would be sent to HTC.
        Future: Will actually execute against HTC via execute_action().

        Args:
            pending_action_id: ID of the pending action to approve

        Returns:
            ExecuteResult with success status and details
        """
        logger.info(f"Approving pending action {pending_action_id}")

        # Get the action
        action = self.pending_action_repo.get_by_id(pending_action_id)
        if action is None:
            logger.warning(f"Cannot approve: pending action {pending_action_id} not found")
            return ExecuteResult(
                pending_action_id=pending_action_id,
                success=False,
                action_type="create",  # default
                htc_order_number=None,
                error_message=f"Pending action {pending_action_id} not found",
            )

        # Check status is valid for approval
        if action.status not in ("ready", "incomplete", "conflict"):
            logger.warning(
                f"Cannot approve: pending action {pending_action_id} status is "
                f"'{action.status}', expected 'ready', 'incomplete', or 'conflict'"
            )
            return ExecuteResult(
                pending_action_id=pending_action_id,
                success=False,
                action_type=action.action_type,
                htc_order_number=action.htc_order_number,
                error_message=f"Cannot approve action with status '{action.status}'",
            )

        # Get selected fields to show what would be sent
        selected_fields = self.pending_action_field_repo.get_selected_fields_for_action(pending_action_id)

        # Log what would happen
        logger.info(f"=== MOCK APPROVAL: Pending Action {pending_action_id} ===")
        logger.info(f"Action Type: {action.action_type}")
        logger.info(f"Customer ID: {action.customer_id}")
        logger.info(f"HAWB: {action.hawb}")
        if action.htc_order_number:
            logger.info(f"HTC Order Number: {action.htc_order_number}")
        logger.info(f"Selected fields that would be sent to HTC:")
        for field_name, field in selected_fields.items():
            # For updates, check is_approved_for_update
            if action.action_type == "update":
                if field.is_approved_for_update:
                    logger.info(f"  - {field_name}: {field.value}")
                else:
                    logger.info(f"  - {field_name}: {field.value} (NOT approved for update, would be skipped)")
            else:
                logger.info(f"  - {field_name}: {field.value}")
        logger.info(f"=== END MOCK APPROVAL ===")

        # Update status to completed
        self.pending_action_repo.update(
            pending_action_id,
            PendingActionUpdate(
                status="completed",
                last_processed_at=datetime.now(timezone.utc),
            ),
        )

        # Broadcast SSE event
        order_event_manager.broadcast_sync("pending_action_updated", {
            "id": pending_action_id,
            "status": "completed",
            "action_type": action.action_type,
        })

        logger.info(f"Pending action {pending_action_id} approved (mock - status set to completed)")

        return ExecuteResult(
            pending_action_id=pending_action_id,
            success=True,
            action_type=action.action_type,
            htc_order_number=action.htc_order_number,
            error_message=None,
        )

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

    # ========== Read Operations ==========

    def list_pending_actions(
        self,
        status: PendingActionStatus | None = None,
        action_type: PendingActionType | None = None,
        is_read: bool | None = None,
        customer_id: int | None = None,
        search_query: str | None = None,
        limit: int = 50,
        offset: int = 0,
        order_by: str = "updated_at",
        desc: bool = True,
    ) -> tuple[list[PendingActionListView], int]:
        """
        List pending actions with filtering, pagination, and customer name enrichment.

        Args:
            status: Filter by status (optional)
            action_type: Filter by action type - "create", "update", "ambiguous" (optional)
            is_read: Filter by read status (optional)
            customer_id: Filter by customer ID (optional)
            search_query: Search in HAWB (optional)
            limit: Maximum number of results (default 50)
            offset: Number of results to skip (default 0)
            order_by: Field to order by (default: updated_at)
            desc: Sort descending if True (default: True)

        Returns:
            Tuple of (list of PendingActionListView with customer names, total count)
        """
        # Get paginated results from repository
        items, total = self.pending_action_repo.get_all_with_counts(
            status=status,
            action_type=action_type,
            is_read=is_read,
            customer_id=customer_id,
            search_query=search_query,
            limit=limit,
            offset=offset,
            order_by=order_by,
            desc=desc,
        )

        # Enrich items with customer names
        enriched_items = [
            PendingActionListView(
                id=item.id,
                customer_id=item.customer_id,
                customer_name=self.htc_service.get_customer_name(item.customer_id),
                hawb=item.hawb,
                htc_order_number=item.htc_order_number,
                action_type=item.action_type,
                status=item.status,
                required_fields_present=item.required_fields_present,
                required_fields_total=item.required_fields_total,
                optional_fields_present=item.optional_fields_present,
                optional_fields_total=item.optional_fields_total,
                conflict_count=item.conflict_count,
                is_read=item.is_read,
                created_at=item.created_at,
                updated_at=item.updated_at,
                last_processed_at=item.last_processed_at,
            )
            for item in items
        ]

        return enriched_items, total

    def set_read_status(self, pending_action_id: int, is_read: bool) -> None:
        """
        Set the read/unread status of a pending action.

        This is an idempotent operation - setting to the same value has no effect.

        Args:
            pending_action_id: ID of the pending action
            is_read: True to mark as read, False to mark as unread
        """
        self.pending_action_repo.update(
            action_id=pending_action_id,
            updates=PendingActionUpdate(is_read=is_read),
        )
        logger.debug(f"Set pending action {pending_action_id} is_read={is_read}")

    def get_pending_action_detail(self, action_id: int) -> PendingActionDetailView | None:
        """
        Get detailed view of a pending action including fields and contributing sources.

        For updates, also fetches current HTC values for comparison display.

        Args:
            action_id: ID of the pending action

        Returns:
            PendingActionDetailView with all field values and contributing sources,
            or None if action not found
        """
        # 1. Get the pending action
        action = self.pending_action_repo.get_by_id(action_id)
        if action is None:
            return None

        # 2. Get fields with source chain data (single JOIN query)
        fields_with_sources = self.pending_action_field_repo.get_fields_with_sources_for_action(action_id)

        # 3. Build field views grouped by field_name
        fields: dict[str, list[PendingActionFieldView]] = {}
        for row in fields_with_sources:
            field_view = PendingActionFieldView(
                id=row["id"],
                field_name=row["field_name"],
                value=row["value"],
                is_selected=row["is_selected"],
                is_approved_for_update=row["is_approved_for_update"],
                sub_run_id=row["sub_run_id"],
            )
            if row["field_name"] not in fields:
                fields[row["field_name"]] = []
            fields[row["field_name"]].append(field_view)

        # 4. Build contributing sources (grouped by sub_run_id)
        sources_by_sub_run: dict[int, dict] = {}
        for row in fields_with_sources:
            sub_run_id = row["sub_run_id"]
            if sub_run_id is None:
                # User-provided value, skip for contributing sources
                continue

            if sub_run_id not in sources_by_sub_run:
                # Determine source identifier
                source_type = row["source_type"] or "manual"
                if source_type == "email" and row["source_email"]:
                    source_identifier = row["source_email"]
                else:
                    source_identifier = "Manual Upload"

                sources_by_sub_run[sub_run_id] = {
                    "sub_run_id": sub_run_id,
                    "pdf_filename": row["pdf_filename"] or "Unknown",
                    "template_name": row["template_name"],
                    "source_type": source_type,
                    "source_identifier": source_identifier,
                    "fields_contributed": set(),
                    "contributed_at": row["contributed_at"],
                }

            sources_by_sub_run[sub_run_id]["fields_contributed"].add(row["field_name"])

        # Convert to ContributingSource objects
        contributing_sources = [
            ContributingSource(
                sub_run_id=src["sub_run_id"],
                pdf_filename=src["pdf_filename"],
                template_name=src["template_name"],
                source_type=src["source_type"],
                source_identifier=src["source_identifier"],
                fields_contributed=sorted(src["fields_contributed"]),
                contributed_at=src["contributed_at"],
            )
            for src in sources_by_sub_run.values()
        ]
        # Sort by contributed_at descending (most recent first)
        contributing_sources.sort(key=lambda s: s.contributed_at, reverse=True)

        # 5. Get current HTC values for updates
        current_htc_values: dict[str, Any] | None = None
        if action.action_type == "update" and action.htc_order_number is not None:
            htc_fields = self.htc_service.get_order_fields(
                order_number=action.htc_order_number
            )
            if htc_fields is not None:
                # Convert dataclass to dict, then transform to ORDER_FIELDS structure
                from features.order_management.transformers import transform_htc_values_to_order_fields
                raw_htc_values = asdict(htc_fields)
                current_htc_values = transform_htc_values_to_order_fields(raw_htc_values)

                # Filter out fields where proposed value matches HTC value
                fields = self._filter_unchanged_fields(fields, current_htc_values)

        # 6. Build and return the detail view
        return PendingActionDetailView(
            id=action.id,
            customer_id=action.customer_id,
            customer_name=self.htc_service.get_customer_name(action.customer_id),
            hawb=action.hawb,
            htc_order_number=action.htc_order_number,
            action_type=action.action_type,
            status=action.status,
            required_fields_present=action.required_fields_present,
            required_fields_total=len(REQUIRED_ORDER_FIELDS),
            optional_fields_present=action.optional_fields_present,
            optional_fields_total=len(OPTIONAL_ORDER_FIELDS),
            conflict_count=action.conflict_count,
            error_message=action.error_message,
            error_at=action.error_at,
            is_read=action.is_read,
            created_at=action.created_at,
            updated_at=action.updated_at,
            last_processed_at=action.last_processed_at,
            fields=fields,
            contributing_sources=contributing_sources,
            current_htc_values=current_htc_values,
        )

    # ========== Mock Data Creation ==========

    def create_mock_output_execution(
        self,
        customer_id: int,
        hawb: str,
        output_channel_data: dict[str, Any],
        pdf_filename: str = "mock_document.pdf",
    ) -> PendingAction | None:
        """
        Create a mock output execution and process it through the normal flow.

        Creates minimal stub records (pdf_file, eto_run, sub_run, output_execution)
        with source_type='mock', then calls process_output_execution to trigger
        the normal accumulation flow.

        This allows testing the pending action system in isolation from ETO.

        Args:
            customer_id: Customer ID for the order
            hawb: HAWB for the order
            output_channel_data: Dict of output channel values (e.g., {"pickup_time_start": "2024-01-15 09:00"})
            pdf_filename: Optional filename for the mock PDF (default: "mock_document.pdf")

        Returns:
            The created or updated PendingAction, or None if update had no changes
        """
        logger.info(
            f"Creating mock output execution: customer_id={customer_id}, "
            f"hawb={hawb}, channels={list(output_channel_data.keys())}"
        )

        # 1. Create a minimal mock PDF file record
        empty_objects = PdfObjects(
            text_words=[],
            graphic_rects=[],
            graphic_lines=[],
            graphic_curves=[],
            images=[],
            tables=[],
        )
        pdf_file = self.pdf_file_repo.create(
            pdf_data=PdfFileCreate(
                original_filename=pdf_filename,
                file_hash=f"mock_{datetime.now().timestamp()}",
                file_size_bytes=0,
                file_path=f"mock/{pdf_filename}",
                stored_at=datetime.now(),
                extracted_objects=empty_objects,
                page_count=1,
            )
        )
        logger.debug(f"Created mock PDF file: id={pdf_file.id}")

        # 2. Create a mock ETO run with source_type='mock'
        eto_run = self.eto_run_repo.create(
            data=EtoRunCreate(
                pdf_file_id=pdf_file.id,
                source_type="mock",
                source_email_id=None,
            )
        )
        # Set status to 'success' so the ETO worker doesn't try to process it
        self.eto_run_repo.update(
            run_id=eto_run.id,
            updates=EtoRunUpdate(status="success"),
        )
        logger.debug(f"Created mock ETO run: id={eto_run.id} (status=success)")

        # 3. Create a mock sub-run (single page, no template)
        sub_run = self.eto_sub_run_repo.create(
            data=EtoSubRunCreate(
                eto_run_id=eto_run.id,
                matched_pages="[1]",
                template_version_id=None,
            )
        )
        # Set status to 'success' so the ETO worker doesn't try to process it
        self.eto_sub_run_repo.update(
            sub_run_id=sub_run.id,
            updates=EtoSubRunUpdate(status="success"),
        )
        logger.debug(f"Created mock sub-run: id={sub_run.id} (status=success)")

        # 4. Create the output execution with the provided channel data
        output_execution = self.output_execution_repo.create(
            data=EtoSubRunOutputExecutionCreate(
                sub_run_id=sub_run.id,
                customer_id=customer_id,
                hawb=hawb,
                output_channel_data=output_channel_data,
            )
        )
        logger.debug(f"Created mock output execution: id={output_execution.id}")

        # 5. Process through the normal flow
        pending_action = self.process_output_execution(output_execution.id)

        if pending_action:
            logger.info(
                f"Mock output execution processed: pending_action_id={pending_action.id}, "
                f"status={pending_action.status}, action_type={pending_action.action_type}"
            )
        else:
            logger.info(
                f"Mock output execution had no changes compared to HTC - no pending action created"
            )

        return pending_action

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
    ) -> bool:
        """
        User rejects the pending action (will not be executed).

        Sets status to 'rejected'. Action cannot be retried after rejection.

        Args:
            pending_action_id: ID of the pending action to reject
            reason: Optional reason for rejection

        Returns:
            True if successfully rejected, False if action not found or invalid status
        """
        logger.info(f"Rejecting pending action {pending_action_id}: {reason}")

        # Get the action
        action = self.pending_action_repo.get_by_id(pending_action_id)
        if action is None:
            logger.warning(f"Cannot reject: pending action {pending_action_id} not found")
            return False

        # Check status is valid for rejection (not already terminal)
        terminal_statuses = ("completed", "rejected", "failed")
        if action.status in terminal_statuses:
            logger.warning(
                f"Cannot reject: pending action {pending_action_id} status is "
                f"'{action.status}', already in terminal state"
            )
            return False

        # Update status to rejected
        self.pending_action_repo.update(
            pending_action_id,
            PendingActionUpdate(
                status="rejected",
                error_message=reason,
                last_processed_at=datetime.now(timezone.utc),
            ),
        )

        # Broadcast SSE event
        order_event_manager.broadcast_sync("pending_action_updated", {
            "id": pending_action_id,
            "status": "rejected",
            "action_type": action.action_type,
        })

        logger.info(f"Pending action {pending_action_id} rejected")
        return True

    # ========== Cleanup ==========

    def cleanup_sub_run_contributions(self, sub_run_id: int) -> CleanupResult:
        """
        Remove all field contributions from a sub-run being reprocessed.

        Called by EtoRunsService BEFORE reprocessing a sub-run.

        Steps:
        1. Find all output executions for this sub_run_id
        2. For each output execution, clean up its field contributions
        3. Return aggregated cleanup results

        Args:
            sub_run_id: ID of the sub-run being reprocessed

        Returns:
            CleanupResult with counts of deleted fields and actions
        """
        logger.info(f"Cleaning up contributions from sub-run {sub_run_id}")

        # Find all output executions for this sub-run
        output_executions = self.output_execution_repo.get_by_sub_run_id(sub_run_id)

        if not output_executions:
            logger.debug(f"No output executions found for sub-run {sub_run_id}")
            return CleanupResult(
                fields_deleted=0,
                actions_deleted=0,
                actions_recalculated=0,
            )

        # Aggregate cleanup results
        total_fields_deleted = 0
        total_actions_deleted = 0
        total_actions_recalculated = 0

        for output_execution in output_executions:
            result = self.cleanup_output_execution_contributions(output_execution.id)
            total_fields_deleted += result.fields_deleted
            total_actions_deleted += result.actions_deleted
            total_actions_recalculated += result.actions_recalculated

        logger.info(
            f"Sub-run {sub_run_id} cleanup complete: "
            f"fields_deleted={total_fields_deleted}, "
            f"actions_deleted={total_actions_deleted}, "
            f"actions_recalculated={total_actions_recalculated}"
        )

        return CleanupResult(
            fields_deleted=total_fields_deleted,
            actions_deleted=total_actions_deleted,
            actions_recalculated=total_actions_recalculated,
        )

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

        Args:
            output_execution_id: ID of the output execution being cleaned up

        Returns:
            CleanupResult with counts of deleted fields and actions
        """
        logger.debug(f"Cleaning up contributions from output execution {output_execution_id}")

        # Step 1: Find all affected pending actions
        fields = self.pending_action_field_repo.get_fields_by_output_execution(output_execution_id)

        if not fields:
            logger.debug(f"No fields found for output execution {output_execution_id}")
            return CleanupResult(fields_deleted=0, actions_deleted=0, actions_recalculated=0)

        # Get unique pending_action_ids
        affected_action_ids = set(f.pending_action_id for f in fields)
        logger.debug(f"Found {len(fields)} fields affecting {len(affected_action_ids)} actions")

        # Step 2: Delete all fields for this output execution
        fields_deleted = self.pending_action_field_repo.delete_by_output_execution(output_execution_id)

        # Step 3: Process each affected action
        actions_deleted = 0
        actions_recalculated = 0

        for action_id in affected_action_ids:
            # Check if any extracted fields remain
            has_fields = self.pending_action_field_repo.has_extracted_fields(action_id)

            if not has_fields:
                # No extracted fields remain - delete the action
                logger.debug(f"Deleting pending action {action_id} (no fields remaining)")
                self.pending_action_repo.delete(action_id)
                actions_deleted += 1

                # Broadcast deletion event
                order_event_manager.broadcast_sync("pending_action_deleted", {
                    "id": action_id,
                })
            else:
                # Fields remain - recalculate status
                logger.debug(f"Recalculating status for pending action {action_id}")
                updated_action = self._recalculate_action_status(action_id)
                actions_recalculated += 1

                # Broadcast update event
                order_event_manager.broadcast_sync("pending_action_updated", {
                    "id": updated_action.id,
                    "status": updated_action.status,
                    "action_type": updated_action.action_type,
                })

        logger.debug(
            f"Output execution {output_execution_id} cleanup: "
            f"fields={fields_deleted}, actions_deleted={actions_deleted}, recalculated={actions_recalculated}"
        )

        return CleanupResult(
            fields_deleted=fields_deleted,
            actions_deleted=actions_deleted,
            actions_recalculated=actions_recalculated,
        )
