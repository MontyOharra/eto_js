"""
Order Management Service

Unified service for pending action processing. Handles accumulation of field values
from output executions and manual input, execution against HTC, and user interactions.
"""
import json
import logging
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal, TYPE_CHECKING

from shared.database import DatabaseConnectionManager
from shared.database.repositories.pending_action import PendingActionRepository
from shared.database.repositories.pending_action_field import PendingActionFieldRepository
from shared.database.repositories.eto_sub_run_output_execution import EtoSubRunOutputExecutionRepository
from shared.database.repositories.eto_run import EtoRunRepository
from shared.database.repositories.eto_sub_run import EtoSubRunRepository
from shared.database.repositories.pdf_file import PdfFileRepository
from shared.database.repositories.email import EmailRepository
from shared.database.repositories.system_settings import SystemSettingsRepository

if TYPE_CHECKING:
    from features.email.service import EmailService

from shared.types.eto_runs import EtoRunCreate, EtoRunUpdate
from shared.types.eto_sub_runs import EtoSubRunCreate, EtoSubRunUpdate
from shared.types.eto_sub_run_output_executions import EtoSubRunOutputExecutionCreate
from shared.types.pdf_files import PdfFileCreate, PdfObjects, TextWord, GraphicRect, GraphicLine, GraphicCurve, Image, Table

from shared.types.pending_actions import (
    PendingAction,
    PendingActionCreate,
    PendingActionUpdate,
    PendingActionFieldCreate,
    PendingActionFieldUpdate,
    PendingActionType,
    PendingActionStatus,
    PendingActionListView,
    PendingActionDetailView,
    PendingActionFieldView,
    ContributingSource,
    CleanupResult,
    ExecuteResult,
    ExecutionResult,
    VerifyTypeResult,
    ORDER_FIELDS,
    REQUIRED_ORDER_FIELDS,
    OPTIONAL_ORDER_FIELDS,
    LocationValue,
    DatetimeRangeValue,
    DimObject,
)

from features.htc_integration import HtcIntegrationService
from features.htc_integration.attachment_utils import PdfSource
from shared.events.order_events import order_event_manager

from .transformers import FIELD_TRANSFORMERS

logger = logging.getLogger(__name__)


# =============================================================================
# Result Types for Per-Field Processing
# =============================================================================

@dataclass
class FieldProcessingResult:
    """Result of processing a single field."""
    field_name: str
    status: Literal["success", "failed"]
    error: str | None = None


@dataclass
class OutputProcessingResult:
    """
    Aggregated result of processing all fields from an output execution.

    This is returned by process_output_execution() and NEVER raises - all
    errors are captured per-field in the results list.
    """
    pending_action_id: int | None  # None if no action created (e.g., no fields)
    field_results: list[FieldProcessingResult] = field(default_factory=list)

    @property
    def has_failures(self) -> bool:
        """True if any field failed processing."""
        return any(f.status == "failed" for f in self.field_results)

    @property
    def failed_fields(self) -> list[str]:
        """List of field names that failed processing."""
        return [f.field_name for f in self.field_results if f.status == "failed"]

    @property
    def successful_fields(self) -> list[str]:
        """List of field names that processed successfully."""
        return [f.field_name for f in self.field_results if f.status == "success"]

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
        """
        Initialize service with dependencies.

        Args:
            connection_manager: Database connection manager for ETO database
            htc_integration_service: Service for HTC database operations
        """
        self.connection_manager = connection_manager
        self.htc_service = htc_integration_service

        # Repositories
        self.pending_action_repo = PendingActionRepository(connection_manager=connection_manager)
        self.pending_action_field_repo = PendingActionFieldRepository(connection_manager=connection_manager)
        self.output_execution_repo = EtoSubRunOutputExecutionRepository(connection_manager=connection_manager)

        # Additional repositories for mock data creation and email tracing
        self.eto_run_repo = EtoRunRepository(connection_manager=connection_manager)
        self.eto_sub_run_repo = EtoSubRunRepository(connection_manager=connection_manager)
        self.pdf_file_repo = PdfFileRepository(connection_manager=connection_manager)
        self._email_repo = EmailRepository(connection_manager=connection_manager)
        self._system_settings_repo = SystemSettingsRepository(connection_manager=connection_manager)

        # Locks for preventing race conditions when creating pending actions
        # Key: (customer_id, hawb) -> Lock
        # Prevents duplicate actions when multiple sub-runs for same order process concurrently
        self._action_locks: dict[tuple[int, str], threading.Lock] = {}
        self._action_locks_lock = threading.Lock()  # Protects the _action_locks dict itself

    def _get_email_service(self) -> "EmailService | None":
        """
        Lazily get the email service from ServiceContainer.

        Uses lazy resolution to avoid circular dependency at initialization time:
        email → eto_runs → order_management → email
        """
        try:
            from shared.services.service_container import ServiceContainer
            return ServiceContainer.get('email')
        except Exception as e:
            logger.warning(f"Could not get email service: {e}")
            return None

    # ========== Main Entry Point ==========

    def process_output_execution(self, output_execution_id: int) -> OutputProcessingResult:
        """
        Main entry point - processes a single output execution record.

        Called by EtoRunsService after creating the output_execution data snapshot.

        IMPORTANT: This method NEVER raises exceptions. All errors are captured
        per-field in the returned OutputProcessingResult. This allows sub-runs
        to succeed even when some field transformations fail.

        Args:
            output_execution_id: ID of the output execution to process

        Returns:
            OutputProcessingResult with per-field success/failure information
        """
        # 1. Load the data snapshot
        output_execution = self.output_execution_repo.get_by_id(output_execution_id)
        if not output_execution:
            logger.error(f"Output execution {output_execution_id} not found")
            return OutputProcessingResult(pending_action_id=None)

        # 2. Determine action type by checking HTC for existing orders
        try:
            action_type, htc_order_number = self._determine_action_type(
                customer_id=output_execution.customer_id,
                hawb=output_execution.hawb,
            )
        except Exception as e:
            logger.error(f"Failed to determine action type: {e}")
            return OutputProcessingResult(pending_action_id=None)

        # 3. Check if pending action already exists (for event type determination)
        existing_action = self.pending_action_repo.get_active_by_customer_hawb(
            customer_id=output_execution.customer_id,
            hawb=output_execution.hawb,
        )
        is_new_action = existing_action is None

        # 4. Find or create the pending action record
        try:
            pending_action = self._get_or_create_pending_action(
                customer_id=output_execution.customer_id,
                hawb=output_execution.hawb,
                action_type=action_type,
                htc_order_number=htc_order_number,
            )
        except Exception as e:
            logger.error(f"Failed to create/get pending action: {e}")
            return OutputProcessingResult(pending_action_id=None)

        # 5. For updates, get current HTC values for changed field detection
        current_htc_values: dict[str, Any] | None = None
        if action_type == "update" and htc_order_number is not None:
            try:
                htc_fields = self.htc_service.get_order_fields(order_number=htc_order_number)
                if htc_fields:
                    from features.order_management.transformers import transform_htc_values_to_order_fields
                    current_htc_values = transform_htc_values_to_order_fields(asdict(htc_fields))
            except Exception as e:
                logger.warning(f"Could not fetch HTC values for comparison: {e}")

        # 6. Process each field independently - never let one field's failure affect others
        field_results = self._process_fields_independently(
            pending_action_id=pending_action.id,
            output_execution_id=output_execution_id,
            output_channel_data=output_execution.output_channel_data,
            action_type=action_type,
            current_htc_values=current_htc_values,
        )

        # 7. Recalculate action status based on current field state
        try:
            updated_action = self._recalculate_action_status(pending_action.id)
        except Exception as e:
            logger.error(f"Failed to recalculate action status: {e}")
            # Return what we have - fields were processed
            return OutputProcessingResult(
                pending_action_id=pending_action.id,
                field_results=field_results,
            )

        # 8. Broadcast event for real-time UI updates
        try:
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
        except Exception as e:
            logger.warning(f"Failed to broadcast event: {e}")

        # Log summary
        result = OutputProcessingResult(
            pending_action_id=updated_action.id,
            field_results=field_results,
        )
        if result.has_failures:
            logger.warning(
                f"Output execution {output_execution_id} processed with failures: "
                f"success={result.successful_fields}, failed={result.failed_fields}"
            )
        else:
            logger.debug(
                f"Output execution {output_execution_id} processed successfully: "
                f"fields={result.successful_fields}"
            )

        return result

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

    def _get_action_lock(self, customer_id: int, hawb: str) -> threading.Lock:
        """
        Get or create a lock for a specific (customer_id, hawb) pair.

        Used to prevent race conditions when multiple sub-runs for the same
        order are processed concurrently.
        """
        key = (customer_id, hawb)
        with self._action_locks_lock:
            if key not in self._action_locks:
                self._action_locks[key] = threading.Lock()
            return self._action_locks[key]

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

        Uses per-(customer_id, hawb) locking to prevent race conditions when
        multiple sub-runs for the same order are processed concurrently.
        """
        # Use lock to prevent duplicate action creation from concurrent sub-runs
        lock = self._get_action_lock(customer_id, hawb)
        with lock:
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

    def _process_fields_independently(
        self,
        pending_action_id: int,
        output_execution_id: int,
        output_channel_data: dict[str, Any],
        action_type: PendingActionType,
        current_htc_values: dict[str, Any] | None,
    ) -> list[FieldProcessingResult]:
        """
        Process each field independently, capturing errors per-field.

        This is the core of the decoupled error handling - each field is processed
        in isolation, so one field's failure doesn't affect others.

        Args:
            pending_action_id: ID of the pending action to add fields to
            output_execution_id: ID of the source output execution
            output_channel_data: Raw output channel data from pipeline
            action_type: Whether this is a create or update
            current_htc_values: Current HTC values for change detection (updates only)

        Returns:
            List of FieldProcessingResult for each processed field
        """
        results: list[FieldProcessingResult] = []

        # Iterate over all defined order fields
        for field_name, field_def in ORDER_FIELDS.items():
            # Extract source channel values for this field
            source_values = {
                channel: output_channel_data.get(channel)
                for channel in field_def.source_channels
            }

            # Skip if no source channels have values
            if not any(v is not None for v in source_values.values()):
                continue

            # Process this single field with error isolation
            result = self._process_single_field(
                pending_action_id=pending_action_id,
                output_execution_id=output_execution_id,
                field_name=field_name,
                field_def=field_def,
                source_values=source_values,
                action_type=action_type,
                current_htc_values=current_htc_values,
            )
            results.append(result)

        return results

    def _process_single_field(
        self,
        pending_action_id: int,
        output_execution_id: int,
        field_name: str,
        field_def: Any,  # OrderFieldDef
        source_values: dict[str, Any],
        action_type: PendingActionType,
        current_htc_values: dict[str, Any] | None,
    ) -> FieldProcessingResult:
        """
        Process a single field with full error isolation. Never raises.

        Attempts transformation, address resolution (for location fields),
        and stores the result. On any failure, stores the field with
        processing_status='failed' and the error message.

        Args:
            pending_action_id: ID of the pending action
            output_execution_id: ID of the source output execution
            field_name: Name of the field being processed
            field_def: Field definition from ORDER_FIELDS
            source_values: Raw source channel values for this field
            action_type: Whether this is a create or update
            current_htc_values: Current HTC values for change detection

        Returns:
            FieldProcessingResult indicating success or failure
        """
        raw_value_json = json.dumps(source_values)

        try:
            # Step 1: Transform using the appropriate transformer
            transformer = FIELD_TRANSFORMERS.get(field_def.data_type)
            if not transformer:
                raise ValueError(f"No transformer for data_type: {field_def.data_type}")

            transformed_value = transformer(source_values)
            if transformed_value is None:
                # No value produced - skip storing
                return FieldProcessingResult(field_name=field_name, status="success")

            # Step 2: For location fields, resolve address ID with fallback
            if field_name in ("pickup_location", "delivery_location"):
                transformed_value = self._resolve_location_with_fallback(
                    field_name=field_name,
                    location_value=transformed_value,
                    raw_source_values=source_values,
                )

            # Step 3: Determine if this field changed from HTC (for updates)
            is_changed = True  # Default: always approve for creates
            if action_type == "update" and current_htc_values is not None:
                is_changed = self._is_field_changed(
                    field_name=field_name,
                    proposed_value=transformed_value,
                    htc_value=current_htc_values.get(field_name),
                )
                if not is_changed:
                    # For updates, skip unchanged fields entirely
                    logger.debug(f"Skipping unchanged field '{field_name}'")
                    return FieldProcessingResult(field_name=field_name, status="success")

            # Step 4: Store the field value
            self._store_field_value(
                pending_action_id=pending_action_id,
                output_execution_id=output_execution_id,
                field_name=field_name,
                value=transformed_value,
                raw_value=raw_value_json,
                processing_status="success",
                processing_error=None,
                is_approved_for_update=is_changed,
            )

            return FieldProcessingResult(field_name=field_name, status="success")

        except Exception as e:
            logger.warning(f"Field '{field_name}' processing failed: {e}")

            # Store the failed field with error info
            try:
                self._store_field_value(
                    pending_action_id=pending_action_id,
                    output_execution_id=output_execution_id,
                    field_name=field_name,
                    value=None,  # No transformed value
                    raw_value=raw_value_json,
                    processing_status="failed",
                    processing_error=str(e),
                    is_approved_for_update=False,  # Failed fields not approved
                )
            except Exception as store_error:
                logger.error(f"Failed to store error for field '{field_name}': {store_error}")

            return FieldProcessingResult(
                field_name=field_name,
                status="failed",
                error=str(e),
            )

    def _resolve_location_with_fallback(
        self,
        field_name: str,
        location_value: LocationValue,
        raw_source_values: dict[str, Any],
    ) -> LocationValue:
        """
        Resolve address ID for a location field with cascading fallback.

        Strategy:
        1. First check if address can be parsed (validate format)
        2. If parsing fails → try LLM fallback, then raise error
        3. If parsing succeeds → try HTC lookup
           - Found in HTC → return with address_id
           - Not found in HTC → return WITHOUT address_id (new address is OK!)

        The key distinction is:
        - Parse failure = error (malformed address, needs LLM to interpret)
        - Not found in HTC = success (valid new address, will be created later)

        Args:
            field_name: Name of the location field
            location_value: Transformed LocationValue to resolve
            raw_source_values: Original source values for LLM fallback

        Returns:
            LocationValue with resolved address_id (if found) or None (if new address)

        Raises:
            ValueError: If address cannot be PARSED by any method
        """
        # If already has address_id, no resolution needed
        if location_value.address_id is not None:
            return location_value

        address = location_value.address
        if not address:
            # No address to resolve - return as-is
            return location_value

        # Step 1: Check if address can be parsed (validate format)
        parsed = self.htc_service.parse_address_string(address)

        if parsed is not None:
            # Parsing succeeded - address format is valid
            logger.debug(f"Address for {field_name} parsed successfully: {parsed}")

            # Step 2: Try to find existing address in HTC
            try:
                address_id = self.htc_service.find_address_id(address)
                if address_id is not None:
                    logger.debug(f"Resolved {field_name} address_id via HTC lookup: {address_id}")
                    # Get canonical address info from HTC
                    addr_info = self.htc_service.get_address_info(address_id)
                    if addr_info:
                        formatted_address = addr_info.addr_ln1
                        if addr_info.addr_ln2:
                            formatted_address = f"{addr_info.addr_ln1} {addr_info.addr_ln2}"
                        formatted_address = f"{formatted_address}, {addr_info.city}, {addr_info.state} {addr_info.zip_code}"

                        return LocationValue(
                            address_id=int(address_id),
                            name=addr_info.company,
                            address=formatted_address,
                        )
                    else:
                        return LocationValue(
                            address_id=int(address_id),
                            name=location_value.name,
                            address=location_value.address,
                        )
                else:
                    # Not found in HTC - but that's OK! It's a valid new address
                    # Rebuild clean address from parsed components (filters out garbage like "Order #100000")
                    # Include addr_ln2 (suite, dock, etc.) if present
                    addr_ln2 = parsed.get('addr_ln2', '')
                    if addr_ln2:
                        clean_address = f"{parsed['addr_ln1']} {addr_ln2}, {parsed['city']}, {parsed['state']} {parsed['zip_code']}"
                    else:
                        clean_address = f"{parsed['addr_ln1']}, {parsed['city']}, {parsed['state']} {parsed['zip_code']}"

                    # Validate the rebuilt address can be parsed again
                    # This catches cases where usaddress parsed garbage into addr_ln2
                    # that makes the rebuilt address unparseable
                    reparse_check = self.htc_service.parse_address_string(clean_address.upper())
                    if reparse_check is None:
                        raise ValueError(
                            f"Address has ambiguous or conflicting secondary line info "
                            f"(suite, unit, etc.): '{addr_ln2}' in address '{address}'"
                        )

                    logger.debug(
                        f"Address for {field_name} not found in HTC (new address). "
                        f"Raw: '{address}' -> Clean: '{clean_address}'"
                    )
                    return LocationValue(
                        address_id=None,
                        name=location_value.name,
                        address=clean_address.upper(),
                    )
            except Exception as e:
                logger.warning(f"HTC address lookup failed for {field_name}: {e}")
                # If lookup itself failed (DB error etc), still return as valid new address
                # Use clean address from parsed components
                addr_ln2 = parsed.get('addr_ln2', '')
                if addr_ln2:
                    clean_address = f"{parsed['addr_ln1']} {addr_ln2}, {parsed['city']}, {parsed['state']} {parsed['zip_code']}"
                else:
                    clean_address = f"{parsed['addr_ln1']}, {parsed['city']}, {parsed['state']} {parsed['zip_code']}"

                # Validate the rebuilt address can be parsed again
                reparse_check = self.htc_service.parse_address_string(clean_address.upper())
                if reparse_check is None:
                    raise ValueError(
                        f"Address has ambiguous or conflicting secondary line info "
                        f"(suite, unit, etc.): '{addr_ln2}' in address '{address}'"
                    )

                return LocationValue(
                    address_id=None,
                    name=location_value.name,
                    address=clean_address.upper(),
                )

        # Parsing failed - try LLM fallback
        logger.debug(f"Address parsing failed for {field_name}, trying LLM fallback: '{address}'")
        try:
            llm_result = self._resolve_address_via_llm(
                field_name=field_name,
                raw_source_values=raw_source_values,
            )
            if llm_result is not None:
                logger.debug(f"Resolved {field_name} address via LLM: {llm_result}")
                return llm_result
        except Exception as e:
            logger.warning(f"LLM address fallback failed for {field_name}: {e}")

        # Parsing failed and LLM couldn't help - this is an actual error
        raise ValueError(
            f"Could not parse address for {field_name}: '{address}' - "
            f"address format is invalid and could not be interpreted"
        )

    def _resolve_address_via_llm(
        self,
        field_name: str,
        raw_source_values: dict[str, Any],
    ) -> LocationValue | None:
        """
        Use LLM to parse address when primary methods fail.

        This is a STUB for future implementation. Currently returns None
        to indicate the fallback is not available.

        TODO: Implement LLM-based address parsing:
        1. Extract address string from raw_source_values
        2. Call OpenAI API to parse address components
        3. Look up or create address in HTC
        4. Return LocationValue with resolved address_id

        Args:
            field_name: Name of the location field (for logging)
            raw_source_values: Original source values containing address data

        Returns:
            LocationValue with resolved address_id, or None if unavailable
        """
        # STUB: LLM address parsing not yet implemented
        logger.debug(f"LLM address fallback not implemented for {field_name}")
        return None

    def _is_field_changed(
        self,
        field_name: str,
        proposed_value: Any,
        htc_value: Any,
    ) -> bool:
        """
        Determine if a proposed value differs from the current HTC value.

        Args:
            field_name: Name of the field
            proposed_value: Value from pipeline output
            htc_value: Current value in HTC

        Returns:
            True if values differ, False if they match
        """
        # If HTC has no value, it's a new value - changed
        if htc_value is None:
            return True

        # Location fields: compare by address_id only
        if field_name in ("pickup_location", "delivery_location"):
            proposed_id = None
            htc_id = None

            if hasattr(proposed_value, "address_id"):
                proposed_id = proposed_value.address_id
            elif isinstance(proposed_value, dict):
                proposed_id = proposed_value.get("address_id")

            if isinstance(htc_value, dict):
                htc_id = htc_value.get("address_id")

            # If proposed address_id is null, treat as changed (needs resolution)
            if proposed_id is None:
                return True

            return proposed_id != htc_id

        # Other fields: normalized comparison
        proposed_normalized = self._normalize_value_for_comparison(proposed_value)
        htc_normalized = self._normalize_value_for_comparison(htc_value)
        return proposed_normalized != htc_normalized

    def _store_field_value(
        self,
        pending_action_id: int,
        output_execution_id: int,
        field_name: str,
        value: Any,
        raw_value: str,
        processing_status: Literal["success", "failed"],
        processing_error: str | None,
        is_approved_for_update: bool,
    ) -> None:
        """
        Store a field value with processing status information.

        Handles conflict detection for existing values:
        - If no existing values: create with is_selected=True
        - If value matches existing: skip (duplicate)
        - If value differs: clear selections, create with is_selected=False

        Args:
            pending_action_id: ID of the pending action
            output_execution_id: ID of the output execution
            field_name: Name of the field
            value: Transformed value (or None for failed fields)
            raw_value: JSON string of original source values
            processing_status: "success" or "failed"
            processing_error: Error message if failed
            is_approved_for_update: Whether field should be included in updates
        """
        # Get existing values for this field
        existing_fields = self.pending_action_field_repo.get_fields_for_action(pending_action_id)
        existing_for_field = [f for f in existing_fields if f.field_name == field_name]

        # For failed fields, always store (no conflict checking)
        if processing_status == "failed":
            self.pending_action_field_repo.create(
                data=PendingActionFieldCreate(
                    pending_action_id=pending_action_id,
                    output_execution_id=output_execution_id,
                    field_name=field_name,
                    value=value,
                    is_selected=False,  # Failed fields are never selected
                    is_approved_for_update=False,
                    processing_status=processing_status,
                    processing_error=processing_error,
                    raw_value=raw_value,
                )
            )
            return

        # Serialize value for comparison
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
                    is_approved_for_update=is_approved_for_update,
                    processing_status=processing_status,
                    processing_error=processing_error,
                    raw_value=raw_value,
                )
            )
        else:
            # Check if value matches any existing value
            value_matches = any(
                self._serialize_value_for_comparison(existing.value) == new_value_json
                for existing in existing_for_field
            )

            if value_matches:
                # Duplicate value - skip
                logger.debug(f"Skipping duplicate value for field '{field_name}'")
            else:
                # Different value - conflict! Clear all selections
                inherit_approval = existing_for_field[0].is_approved_for_update
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
                        is_approved_for_update=inherit_approval,
                        processing_status=processing_status,
                        processing_error=processing_error,
                        raw_value=raw_value,
                    )
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

        When an address ID is found, the name and address are replaced with the
        canonical values from the HTC address table to ensure consistency.

        Args:
            order_fields: Dict of transformed order fields

        Returns:
            Updated order_fields with resolved address IDs and canonical address data
        """
        from shared.types.pending_actions import LocationValue

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
                    # Look up canonical address data from HTC address table
                    addr_info = self.htc_service.get_address_info(address_id)
                    if addr_info:
                        # Use standardized data from the address table
                        formatted_address = addr_info.addr_ln1
                        if addr_info.addr_ln2:
                            formatted_address = f"{addr_info.addr_ln1} {addr_info.addr_ln2}"
                        formatted_address = f"{formatted_address}, {addr_info.city}, {addr_info.state} {addr_info.zip_code}"

                        order_fields[field_name] = LocationValue(
                            address_id=int(address_id),
                            name=addr_info.company,  # Use company from address table
                            address=formatted_address,  # Use formatted address from address table
                        )
                    else:
                        # Fallback: just set the ID, keep original name/address
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
                    # Look up canonical address data from HTC address table
                    addr_info = self.htc_service.get_address_info(address_id)
                    if addr_info:
                        # Use standardized data from the address table
                        formatted_address = addr_info.addr_ln1
                        if addr_info.addr_ln2:
                            formatted_address = f"{addr_info.addr_ln1} {addr_info.addr_ln2}"
                        formatted_address = f"{formatted_address}, {addr_info.city}, {addr_info.state} {addr_info.zip_code}"

                        location["address_id"] = int(address_id)
                        location["name"] = addr_info.company
                        location["address"] = formatted_address
                    else:
                        # Fallback: just set the ID
                        location["address_id"] = int(address_id)
                else:
                    logger.debug(f"Could not resolve address for {field_name}: {address}")

        return order_fields

    def _identify_changed_fields(
        self,
        order_fields: dict[str, Any],
        htc_order_number: float,
    ) -> tuple[dict[str, Any], set[str]]:
        """
        Identify which fields differ from current HTC values.

        For updates, we store ALL contributed fields but track which ones
        actually differ from HTC. This allows:
        - Users to see all contributed values
        - Changed fields to be auto-approved for update
        - Unchanged fields to be stored but not auto-approved (user can toggle)

        Args:
            order_fields: Transformed order fields to store
            htc_order_number: HTC order number to fetch current values

        Returns:
            Tuple of (all_fields, changed_field_names_set)
        """
        # Fetch current HTC values
        htc_fields = self.htc_service.get_order_fields(order_number=htc_order_number)
        if htc_fields is None:
            logger.warning(f"Could not fetch HTC fields for order {htc_order_number}, treating all as changed")
            return order_fields, set(order_fields.keys())

        # Transform HTC values to match our field structure
        from features.order_management.transformers import transform_htc_values_to_order_fields
        from dataclasses import asdict
        current_htc_values = transform_htc_values_to_order_fields(asdict(htc_fields))

        changed_fields: set[str] = set()
        location_fields = {"pickup_location", "delivery_location"}

        for field_name, proposed_value in order_fields.items():
            htc_value = current_htc_values.get(field_name)

            # If HTC has no value for this field, it's a new value - changed
            if htc_value is None:
                logger.debug(f"Field '{field_name}': HTC has no value, marking as changed")
                changed_fields.add(field_name)
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

                # If proposed address_id is null, treat as changed (needs resolution)
                if proposed_id is None:
                    logger.debug(f"Field '{field_name}': proposed address_id is None, marking as changed")
                    changed_fields.add(field_name)
                    continue

                # If address_ids differ, mark as changed
                if proposed_id != htc_id:
                    logger.debug(f"Field '{field_name}': address_ids differ ({proposed_id} vs {htc_id}), marking as changed")
                    changed_fields.add(field_name)
                else:
                    logger.debug(f"Field '{field_name}': address_ids match ({proposed_id}), unchanged")
                continue

            # Normalize for comparison
            proposed_normalized = self._normalize_value_for_comparison(proposed_value)
            htc_normalized = self._normalize_value_for_comparison(htc_value)

            if proposed_normalized != htc_normalized:
                logger.debug(f"Field '{field_name}': values differ, marking as changed")
                changed_fields.add(field_name)
            else:
                logger.debug(f"Field '{field_name}': values match, unchanged")

        return order_fields, changed_fields

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
        changed_fields: set[str] | None = None,
    ) -> None:
        """
        Add field values to pending action, handling conflict detection.

        For each field:
        - If no existing values: create with is_selected=True
          - For creates (changed_fields=None): is_approved_for_update=True
          - For updates: is_approved_for_update=True only if field is in changed_fields
        - If value matches existing: skip (duplicate - no point storing same value twice)
        - If value differs: clear all selections, create with is_selected=False
          and inherit is_approved_for_update from existing values

        Args:
            pending_action_id: ID of the pending action
            output_execution_id: ID of the output execution contributing this value
            fields: Dict of field_name -> value to add
            changed_fields: Set of field names that differ from HTC values (for updates).
                           None means all fields should be auto-approved (creates).
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
                # Auto-approve if: creates (changed_fields=None) OR field is in changed_fields
                should_approve = changed_fields is None or field_name in changed_fields
                logger.debug(
                    f"Adding first value for field '{field_name}' "
                    f"(auto-selected, approved={should_approve})"
                )
                self.pending_action_field_repo.create(
                    data=PendingActionFieldCreate(
                        pending_action_id=pending_action_id,
                        output_execution_id=output_execution_id,
                        field_name=field_name,
                        value=value,
                        is_selected=True,
                        is_approved_for_update=should_approve,
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
                    # Inherit approval status from existing values (they should all be the same)
                    inherit_approval = existing_for_field[0].is_approved_for_update

                    logger.debug(
                        f"Conflict detected for field '{field_name}' - clearing selections, "
                        f"inheriting approval={inherit_approval}"
                    )
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
                            is_approved_for_update=inherit_approval,
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

            # If multiple values exist, always show for user to see/change selection
            # This allows users to switch between options even if one matches HTC
            if len(field_values) > 1:
                filtered[field_name] = field_values
                continue

            # Single value - compare to HTC to decide whether to show
            # (Skip if somehow empty - shouldn't happen but be safe)
            if len(field_values) == 0:
                continue

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
        3. "incomplete" if missing required fields (or required field has error selected)
        4. "ready" if all requirements met

        Also updates denormalized counts:
        - required_fields_present (only counts fields with successful selected values)
        - conflict_count

        Auto-selects single-value fields that aren't selected (can happen after
        conflict resolution when one value is deleted).

        Note: Fields with processing_status='failed' selected do NOT count as present.
        They are tracked separately via error_field_count in the repository.
        """
        # Get current action state
        action = self.pending_action_repo.get_by_id(pending_action_id)
        if not action:
            raise ValueError(f"Pending action {pending_action_id} not found")

        # Count values per field to detect unresolved conflicts
        value_counts = self.pending_action_field_repo.count_by_field_name(pending_action_id)

        # Get selected fields (the "current" values)
        selected_fields = self.pending_action_field_repo.get_selected_fields_for_action(pending_action_id)
        selected_field_names = set(selected_fields.keys())

        # Auto-select single-value fields that aren't selected
        # This can happen when a conflict existed and one value was deleted during cleanup
        for field_name, count in value_counts.items():
            if count == 1 and field_name not in selected_field_names:
                logger.debug(f"Auto-selecting single value for field '{field_name}' on action {pending_action_id}")
                self.pending_action_field_repo.auto_select_single_value(
                    action_id=pending_action_id,
                    field_name=field_name,
                )
                selected_field_names.add(field_name)

        # Re-fetch selected fields after auto-select to get processing_status
        selected_fields = self.pending_action_field_repo.get_selected_fields_for_action(pending_action_id)

        # Separate successful and failed selected fields
        # Only successful fields count as "present" for required/optional counts
        successful_selected_names = {
            field_name
            for field_name, field in selected_fields.items()
            if field.processing_status == "success"
        }
        failed_selected_names = {
            field_name
            for field_name, field in selected_fields.items()
            if field.processing_status == "failed"
        }

        # Calculate conflict count: fields with multiple values but no selection
        conflict_count = 0
        for field_name, count in value_counts.items():
            if count > 1 and field_name not in selected_fields:
                conflict_count += 1

        # Calculate required and optional fields present (only successful ones count!)
        required_fields_present = len(successful_selected_names.intersection(REQUIRED_ORDER_FIELDS))
        optional_fields_present = len(successful_selected_names.intersection(OPTIONAL_ORDER_FIELDS))

        # Check if any required field has a failed value selected (should be incomplete)
        required_fields_with_errors = len(failed_selected_names.intersection(REQUIRED_ORDER_FIELDS))

        # Determine status based on priority
        # Note: "incomplete" only applies to creates - updates don't have required fields
        new_status: PendingActionStatus
        if action.action_type == "ambiguous":
            new_status = "ambiguous"
        elif conflict_count > 0:
            new_status = "conflict"
        elif action.action_type == "create" and (
            required_fields_present < len(REQUIRED_ORDER_FIELDS) or required_fields_with_errors > 0
        ):
            # Incomplete if missing required fields OR if any required field has error selected
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
            f"conflicts={conflict_count}, required_with_errors={required_fields_with_errors}"
        )

        return updated_action

    # ========== TOCTOU Verification ==========

    def verify_and_update_action_type(self, pending_action_id: int) -> VerifyTypeResult:
        """
        Re-check HTC and update action type if needed (TOCTOU protection).

        Called:
        - When user visits detail page (proactive refresh)
        - Before approval (safety check)

        Handles all transitions:
        - create → update (order_created_externally)
        - create → ambiguous (multiple orders created)
        - update → create (order_deleted_converting_to_create)
        - update → ambiguous (additional orders created)
        - ambiguous → create (all orders deleted)
        - ambiguous → update (only one order remains)

        Args:
            pending_action_id: ID of the pending action to verify

        Returns:
            VerifyTypeResult with old/new types and whether change occurred
        """
        # 1. Get current action
        action = self.pending_action_repo.get_by_id(pending_action_id)
        if action is None:
            raise ValueError(f"Pending action {pending_action_id} not found")

        old_action_type = action.action_type
        old_htc_order_number = action.htc_order_number

        # 2. Re-determine type from HTC
        new_action_type, new_htc_order_number = self._determine_action_type(
            customer_id=action.customer_id,
            hawb=action.hawb,
        )

        type_changed = (
            old_action_type != new_action_type or
            old_htc_order_number != new_htc_order_number
        )

        if type_changed:
            logger.info(
                f"Action {pending_action_id} type changed: "
                f"{old_action_type} → {new_action_type}, "
                f"order {old_htc_order_number} → {new_htc_order_number}"
            )

            # 3. Update the action type and order number
            self.pending_action_repo.update(
                action_id=pending_action_id,
                updates=PendingActionUpdate(
                    action_type=new_action_type,
                    htc_order_number=new_htc_order_number,
                ),
            )

            # 4. Recalculate status (create can be incomplete, update cannot, ambiguous is always ambiguous)
            updated_action = self._recalculate_action_status(pending_action_id)
            new_status = updated_action.status

            # 5. Broadcast change via SSE
            order_event_manager.broadcast_sync("pending_action_updated", {
                "id": pending_action_id,
                "status": new_status,
                "action_type": new_action_type,
            })
        else:
            new_status = action.status

        return VerifyTypeResult(
            pending_action_id=pending_action_id,
            type_changed=type_changed,
            old_action_type=old_action_type,
            new_action_type=new_action_type,
            old_htc_order_number=old_htc_order_number,
            new_htc_order_number=new_htc_order_number,
            new_status=new_status,
        )

    def _get_review_reason_for_type_change(self, verify_result: VerifyTypeResult) -> str:
        """
        Determine the review reason based on how the action type changed.

        Args:
            verify_result: Result from verify_and_update_action_type

        Returns:
            Review reason string for the ExecuteResult
        """
        old_type = verify_result.old_action_type
        new_type = verify_result.new_action_type

        if old_type == "create" and new_type == "update":
            return "order_created_externally"
        elif old_type == "create" and new_type == "ambiguous":
            return "ambiguous"
        elif old_type == "update" and new_type == "create":
            return "order_deleted_converting_to_create"
        elif old_type == "update" and new_type == "ambiguous":
            return "ambiguous"
        elif old_type == "ambiguous" and new_type == "create":
            return "order_deleted_converting_to_create"
        elif old_type == "ambiguous" and new_type == "update":
            return "order_created_externally"
        else:
            # htc_order_number changed (different order found)
            return "htc_values_changed"

    def _refresh_location_address_ids(self, pending_action_id: int) -> bool:
        """
        Re-check and update location field address_ids that may have been resolved.

        When a pending action is created, location fields (pickup_location, delivery_location)
        may have address_id=None if the address didn't exist in HTC at that time.
        Later, the address may be created (by another order or manually in HTC).

        This method re-checks location fields with null address_ids and updates them
        if the address now exists in HTC.

        Called when viewing detail page (similar to TOCTOU verification for action type).

        Args:
            pending_action_id: ID of the pending action to refresh

        Returns:
            True if any address_ids were updated, False otherwise
        """
        location_fields = ["pickup_location", "delivery_location"]
        any_updated = False

        # Get all fields for this action
        fields = self.pending_action_field_repo.get_fields_for_action(pending_action_id)

        for field in fields:
            if field.field_name not in location_fields:
                continue

            # Parse the location value
            location_value = field.value
            if location_value is None:
                continue

            # Handle both dict and object forms
            if isinstance(location_value, dict):
                address_id = location_value.get("address_id")
                address = location_value.get("address")
                name = location_value.get("name")
            elif hasattr(location_value, "address_id"):
                address_id = location_value.address_id
                address = location_value.address
                name = location_value.name
            else:
                continue

            # Skip if already has an address_id
            if address_id is not None:
                continue

            # Skip if no address to look up
            if not address:
                continue

            # Try to find the address in HTC
            resolved_id = self.htc_service.find_address_id(address)
            if resolved_id is None:
                continue

            # Address was found! Update the field value with resolved address_id
            logger.info(
                f"Refreshed {field.field_name} address_id for action {pending_action_id}: "
                f"resolved to {resolved_id}"
            )

            # Get canonical address data from HTC
            addr_info = self.htc_service.get_address_info(resolved_id)
            if addr_info:
                # Use standardized data from the address table
                formatted_address = addr_info.addr_ln1
                if addr_info.addr_ln2:
                    formatted_address = f"{addr_info.addr_ln1} {addr_info.addr_ln2}"
                formatted_address = f"{formatted_address}, {addr_info.city}, {addr_info.state} {addr_info.zip_code}"

                new_value = LocationValue(
                    address_id=int(resolved_id),
                    name=addr_info.company,
                    address=formatted_address,
                )
            else:
                # Fallback: just set the ID, keep original name/address
                new_value = LocationValue(
                    address_id=int(resolved_id),
                    name=name or "",
                    address=address,
                )

            # Update the field with the new value
            self.pending_action_field_repo.update(
                field_id=field.id,
                updates=PendingActionFieldUpdate(value=new_value.model_dump()),
            )
            any_updated = True

        return any_updated

    # ========== Execution ==========

    def approve_action(
        self,
        pending_action_id: int,
        detail_viewed_at: datetime | None = None,
        approver_user_id: str | None = None,
    ) -> ExecuteResult:
        """
        Approve a pending action for execution.

        Validates the action can be approved, then delegates to execute_action()
        for the actual execution flow (currently stub with logging).

        Args:
            pending_action_id: ID of the pending action to approve
            detail_viewed_at: When the user first viewed the detail page (for TOCTOU check).
                             If provided for update actions, we check if HTC was modified
                             after this time and require review if so.

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

        # Check status is valid for approval/retry
        # "failed" is allowed for retry attempts
        if action.status not in ("ready", "incomplete", "conflict", "failed"):
            logger.warning(
                f"Cannot approve: pending action {pending_action_id} status is "
                f"'{action.status}', expected 'ready', 'incomplete', 'conflict', or 'failed'"
            )
            return ExecuteResult(
                pending_action_id=pending_action_id,
                success=False,
                action_type=action.action_type,
                htc_order_number=action.htc_order_number,
                error_message=f"Cannot approve action with status '{action.status}'",
            )

        # Delegate to execute_action for the full execution flow
        return self.execute_action(
            pending_action_id=pending_action_id,
            detail_viewed_at=detail_viewed_at,
            approver_user_id=approver_user_id,
        )

    def execute_action(
        self,
        pending_action_id: int,
        detail_viewed_at: datetime | None = None,
        approver_user_id: str | None = None,
    ) -> ExecuteResult:
        """
        Execute pending action against HTC (create or update order).

        Unified method that combines TOCTOU checks and actual execution.

        Flow:
        1. TOCTOU Step 1: Verify action type hasn't changed (Create↔Update)
        2. TOCTOU Step 2: For updates, check if HTC modified since user viewed detail
        3. Set status to "processing"
        4. Get fields to send (all selected for creates, approved only for updates)
        5. Extract typed field values and execute against HTC
        6. Phase 4: Post-execution (attachments)
        7. Set status to "completed" or "failed"

        Args:
            pending_action_id: ID of the pending action to execute
            detail_viewed_at: When user first viewed detail page (for TOCTOU check)
            approver_user_id: User ID of the approver (for audit trail in updates)

        Returns:
            ExecuteResult with success status and details
        """
        logger.info(f"Executing pending action {pending_action_id}")

        # Get the action
        action = self.pending_action_repo.get_by_id(pending_action_id)
        if action is None:
            logger.warning(f"Cannot execute: pending action {pending_action_id} not found")
            return ExecuteResult(
                pending_action_id=pending_action_id,
                success=False,
                action_type="create",
                htc_order_number=None,
                error_message=f"Pending action {pending_action_id} not found",
            )

        # ================================================================
        # TOCTOU STEP 1: Verify action type hasn't changed
        # ================================================================
        verify_result = self.verify_and_update_action_type(pending_action_id)

        if verify_result.type_changed:
            review_reason = self._get_review_reason_for_type_change(verify_result)
            logger.info(
                f"TOCTOU: Action {pending_action_id} type changed, requires review. "
                f"Reason: {review_reason}"
            )
            return ExecuteResult(
                pending_action_id=pending_action_id,
                success=True,
                action_type=verify_result.new_action_type,
                htc_order_number=verify_result.new_htc_order_number,
                error_message=None,
                requires_review=True,
                review_reason=review_reason,
            )

        # Re-fetch action after verification (may have been updated)
        action = self.pending_action_repo.get_by_id(pending_action_id)
        if action is None:
            return ExecuteResult(
                pending_action_id=pending_action_id,
                success=False,
                action_type="create",
                htc_order_number=None,
                error_message=f"Pending action {pending_action_id} not found after verification",
            )

        # ================================================================
        # TOCTOU STEP 2: For updates, check if HTC modified since viewing
        # ================================================================
        if (
            action.action_type == "update"
            and action.htc_order_number is not None
            and detail_viewed_at is not None
        ):
            try:
                was_modified = self.htc_service.check_order_modified_since(
                    order_number=action.htc_order_number,
                    since_datetime=detail_viewed_at,
                )
                if was_modified:
                    logger.info(
                        f"TOCTOU: Order {action.htc_order_number} was modified in HTC "
                        f"since user viewed detail at {detail_viewed_at}"
                    )
                    return ExecuteResult(
                        pending_action_id=pending_action_id,
                        success=True,
                        action_type=action.action_type,
                        htc_order_number=action.htc_order_number,
                        error_message=None,
                        requires_review=True,
                        review_reason="htc_values_changed",
                    )
            except Exception as e:
                logger.warning(
                    f"Failed to check HTC modification history for order "
                    f"{action.htc_order_number}: {e}"
                )

        # ================================================================
        # EXECUTION: All TOCTOU checks passed - proceed with execution
        # ================================================================

        try:
            # Set status to "processing"
            self.pending_action_repo.update(
                pending_action_id,
                PendingActionUpdate(status="processing", last_processed_at=datetime.now(timezone.utc)),
            )

            # Broadcast processing status
            order_event_manager.broadcast_sync("pending_action_updated", {
                "id": pending_action_id,
                "status": "processing",
                "action_type": action.action_type,
            })

            # Get fields to send
            selected_fields = self.pending_action_field_repo.get_selected_fields_for_action(pending_action_id)
            if action.action_type == "update":
                fields_to_send = {
                    name: field for name, field in selected_fields.items()
                    if field.is_approved_for_update
                }
            else:
                fields_to_send = selected_fields

            logger.info(f"Fields to send: {list(fields_to_send.keys())}")
            # Extract typed field values from fields_to_send
            # Location fields -> LocationValue
            pickup_location: LocationValue | None = None
            if "pickup_location" in fields_to_send:
                val = fields_to_send["pickup_location"].value
                if isinstance(val, dict):
                    pickup_location = LocationValue(**val)
                elif isinstance(val, LocationValue):
                    pickup_location = val

            delivery_location: LocationValue | None = None
            if "delivery_location" in fields_to_send:
                val = fields_to_send["delivery_location"].value
                if isinstance(val, dict):
                    delivery_location = LocationValue(**val)
                elif isinstance(val, LocationValue):
                    delivery_location = val

            # Datetime fields -> DatetimeRangeValue
            pickup_datetime: DatetimeRangeValue | None = None
            if "pickup_datetime" in fields_to_send:
                val = fields_to_send["pickup_datetime"].value
                if isinstance(val, dict):
                    pickup_datetime = DatetimeRangeValue(**val)
                elif isinstance(val, DatetimeRangeValue):
                    pickup_datetime = val

            delivery_datetime: DatetimeRangeValue | None = None
            if "delivery_datetime" in fields_to_send:
                val = fields_to_send["delivery_datetime"].value
                if isinstance(val, dict):
                    delivery_datetime = DatetimeRangeValue(**val)
                elif isinstance(val, DatetimeRangeValue):
                    delivery_datetime = val

            # String fields
            pickup_notes: str | None = None
            if "pickup_notes" in fields_to_send:
                pickup_notes = fields_to_send["pickup_notes"].value

            delivery_notes: str | None = None
            if "delivery_notes" in fields_to_send:
                delivery_notes = fields_to_send["delivery_notes"].value

            mawb: str | None = None
            if "mawb" in fields_to_send:
                mawb = fields_to_send["mawb"].value

            order_notes: str | None = None
            if "order_notes" in fields_to_send:
                order_notes = fields_to_send["order_notes"].value

            # Dims field -> list[DimObject]
            dims: list[DimObject] | None = None
            if "dims" in fields_to_send:
                val = fields_to_send["dims"].value
                if isinstance(val, list):
                    dims = [
                        DimObject(**d) if isinstance(d, dict) else d
                        for d in val
                    ]

            # Build new_values dict for execution result snapshot
            # Store structured objects (as dicts) so frontend can render with same formatting
            exec_new_values: dict[str, Any] = {}
            if pickup_location:
                exec_new_values["pickup_location"] = pickup_location.model_dump()
            if pickup_datetime:
                exec_new_values["pickup_datetime"] = pickup_datetime.model_dump()
            if delivery_location:
                exec_new_values["delivery_location"] = delivery_location.model_dump()
            if delivery_datetime:
                exec_new_values["delivery_datetime"] = delivery_datetime.model_dump()
            if mawb is not None:
                exec_new_values["mawb"] = mawb
            if pickup_notes is not None:
                exec_new_values["pickup_notes"] = pickup_notes
            if delivery_notes is not None:
                exec_new_values["delivery_notes"] = delivery_notes
            if order_notes is not None:
                exec_new_values["order_notes"] = order_notes
            if dims is not None:
                exec_new_values["dims"] = [d.model_dump() if hasattr(d, 'model_dump') else d for d in dims]

            # For updates, capture old values from HTC before executing
            # Use same structured format as new_values for consistent rendering
            exec_old_values: dict[str, Any] | None = None
            if action.action_type == "update" and action.htc_order_number is not None:
                try:
                    current_htc = self.htc_service.get_order_fields(action.htc_order_number)
                    if current_htc:
                        exec_old_values = {}
                        if "pickup_location" in exec_new_values and current_htc.pickup_company_name:
                            exec_old_values["pickup_location"] = {
                                "address_id": int(current_htc.pickup_address_id) if current_htc.pickup_address_id else None,
                                "name": current_htc.pickup_company_name,
                                "address": current_htc.pickup_address or "",
                            }
                        if "pickup_datetime" in exec_new_values and current_htc.pickup_time_start:
                            # Parse the combined datetime string (format: "YYYY-MM-DDTHH:MM:00")
                            pu_date = current_htc.pickup_time_start.split("T")[0] if "T" in (current_htc.pickup_time_start or "") else ""
                            pu_start = current_htc.pickup_time_start.split("T")[1][:5] if "T" in (current_htc.pickup_time_start or "") else ""
                            pu_end = current_htc.pickup_time_end.split("T")[1][:5] if current_htc.pickup_time_end and "T" in current_htc.pickup_time_end else ""
                            exec_old_values["pickup_datetime"] = {
                                "date": pu_date,
                                "time_start": pu_start,
                                "time_end": pu_end,
                            }
                        if "delivery_location" in exec_new_values and current_htc.delivery_company_name:
                            exec_old_values["delivery_location"] = {
                                "address_id": int(current_htc.delivery_address_id) if current_htc.delivery_address_id else None,
                                "name": current_htc.delivery_company_name,
                                "address": current_htc.delivery_address or "",
                            }
                        if "delivery_datetime" in exec_new_values and current_htc.delivery_time_start:
                            # Parse the combined datetime string (format: "YYYY-MM-DDTHH:MM:00")
                            del_date = current_htc.delivery_time_start.split("T")[0] if "T" in (current_htc.delivery_time_start or "") else ""
                            del_start = current_htc.delivery_time_start.split("T")[1][:5] if "T" in (current_htc.delivery_time_start or "") else ""
                            del_end = current_htc.delivery_time_end.split("T")[1][:5] if current_htc.delivery_time_end and "T" in current_htc.delivery_time_end else ""
                            exec_old_values["delivery_datetime"] = {
                                "date": del_date,
                                "time_start": del_start,
                                "time_end": del_end,
                            }
                        if "mawb" in exec_new_values:
                            exec_old_values["mawb"] = current_htc.mawb or ""
                        if "pickup_notes" in exec_new_values:
                            exec_old_values["pickup_notes"] = current_htc.pickup_notes or ""
                        if "delivery_notes" in exec_new_values:
                            exec_old_values["delivery_notes"] = current_htc.delivery_notes or ""
                        if "order_notes" in exec_new_values:
                            exec_old_values["order_notes"] = current_htc.order_notes or ""
                        if "dims" in exec_new_values:
                            exec_old_values["dims"] = current_htc.dims or []
                except Exception as e:
                    logger.warning(f"Could not fetch old HTC values for audit: {e}")

            # Execute based on action type
            if action.action_type == "create":
                # Validate required fields for create
                if pickup_location is None:
                    raise ValueError("Missing required field: pickup_location")
                if delivery_location is None:
                    raise ValueError("Missing required field: delivery_location")
                if pickup_datetime is None:
                    raise ValueError("Missing required field: pickup_datetime")
                if delivery_datetime is None:
                    raise ValueError("Missing required field: delivery_datetime")

                order_number = self._execute_create(
                    action=action,
                    pickup_location=pickup_location,
                    pickup_datetime=pickup_datetime,
                    delivery_location=delivery_location,
                    delivery_datetime=delivery_datetime,
                    pickup_notes=pickup_notes,
                    delivery_notes=delivery_notes,
                    mawb=mawb,
                    order_notes=order_notes,
                    dims=dims,
                )
            else:
                # Update - all fields optional
                self._execute_update(
                    action=action,
                    pickup_location=pickup_location,
                    pickup_datetime=pickup_datetime,
                    delivery_location=delivery_location,
                    delivery_datetime=delivery_datetime,
                    pickup_notes=pickup_notes,
                    delivery_notes=delivery_notes,
                    mawb=mawb,
                    order_notes=order_notes,
                    dims=dims,
                    approver_user_id=approver_user_id,
                )
                order_number = action.htc_order_number

            # Phase 4: Post-execution - process attachments
            if order_number is not None:
                try:
                    pdf_sources = self._get_pdf_sources_for_action(pending_action_id)
                    if pdf_sources:
                        attachment_results = self.htc_service.process_attachments(
                            order_number=order_number,
                            customer_id=action.customer_id,
                            hawb=action.hawb,
                            pdf_sources=pdf_sources,
                        )
                        successful = sum(1 for r in attachment_results if r.success)
                        logger.info(
                            f"Processed {successful}/{len(attachment_results)} attachments "
                            f"for order {int(order_number)}"
                        )
                except Exception as attach_error:
                    # Log but don't fail - order was created/updated successfully
                    logger.error(
                        f"Failed to process attachments for order {int(order_number)}: {attach_error}"
                    )

            # Phase 4b: Email notifications (for creates only)
            if action.action_type == "create" and order_number is not None:
                self._send_order_created_notification(pending_action_id, order_number)

        except Exception as e:
            # Failure - mark as failed so user can retry
            logger.error(f"Failed to execute pending action {pending_action_id}: {e}")
            error_time = datetime.now(timezone.utc)
            self.pending_action_repo.update(
                pending_action_id,
                PendingActionUpdate(
                    status="failed",
                    error_message=str(e),
                    error_at=error_time,
                    last_processed_at=error_time,
                ),
            )

            # Broadcast failure status
            order_event_manager.broadcast_sync("pending_action_updated", {
                "id": pending_action_id,
                "status": "failed",
                "action_type": action.action_type,
            })

            return ExecuteResult(
                pending_action_id=pending_action_id,
                success=False,
                action_type=action.action_type,
                htc_order_number=action.htc_order_number,
                error_message=str(e),
            )

        # Success - build execution result snapshot and mark as completed
        execution_time = datetime.now(timezone.utc)
        execution_result = ExecutionResult(
            action_type=action.action_type,
            executed_at=execution_time,
            approver_user_id=approver_user_id,
            htc_order_number=order_number,
            fields_updated=list(exec_new_values.keys()),
            old_values=exec_old_values,
            new_values=exec_new_values,
        )

        self.pending_action_repo.update(
            pending_action_id,
            PendingActionUpdate(
                status="completed",
                htc_order_number=order_number,
                last_processed_at=execution_time,
                execution_result=execution_result,
            ),
        )

        # Broadcast success status
        order_event_manager.broadcast_sync("pending_action_updated", {
            "id": pending_action_id,
            "status": "completed",
            "action_type": action.action_type,
        })

        logger.info(f"Successfully executed pending action {pending_action_id}")

        return ExecuteResult(
            pending_action_id=pending_action_id,
            success=True,
            action_type=action.action_type,
            htc_order_number=order_number,
            error_message=None,
        )

    def _execute_create(
        self,
        action: PendingAction,
        # Required fields
        pickup_location: LocationValue,
        pickup_datetime: DatetimeRangeValue,
        delivery_location: LocationValue,
        delivery_datetime: DatetimeRangeValue,
        # Optional fields
        pickup_notes: str | None = None,
        delivery_notes: str | None = None,
        mawb: str | None = None,
        order_notes: str | None = None,
        dims: list[DimObject] | None = None,
    ) -> float:
        """
        Execute a create action against HTC.

        Handles:
        1. Address resolution (create addresses if address_id is None)
        2. Transform field values to HTC format
        3. Call htc_service.create_order()

        Args:
            action: The pending action being executed (provides customer_id, hawb)
            pickup_location: Pickup location with address_id (or None to create)
            pickup_datetime: Pickup date and time window
            delivery_location: Delivery location with address_id (or None to create)
            delivery_datetime: Delivery date and time window
            pickup_notes: Optional pickup instructions
            delivery_notes: Optional delivery instructions
            mawb: Optional master airway bill number
            order_notes: Optional general order notes
            dims: Optional list of dimension objects

        Returns:
            The newly created HTC order number

        Raises:
            Exception: If address creation or order creation fails
        """
        # Step 1: Resolve pickup address
        if pickup_location.address_id is not None:
            pickup_location_id = float(pickup_location.address_id)
            logger.info(f"Using existing pickup address ID: {pickup_location_id}")
        else:
            logger.info(f"Creating new pickup address: {pickup_location.name}, {pickup_location.address}")
            pickup_location_id = self.htc_service.find_or_create_address(
                address_string=pickup_location.address,
                company_name=pickup_location.name,
            )
            logger.info(f"Created pickup address with ID: {pickup_location_id}")

        # Step 2: Resolve delivery address
        if delivery_location.address_id is not None:
            delivery_location_id = float(delivery_location.address_id)
            logger.info(f"Using existing delivery address ID: {delivery_location_id}")
        else:
            logger.info(f"Creating new delivery address: {delivery_location.name}, {delivery_location.address}")
            delivery_location_id = self.htc_service.find_or_create_address(
                address_string=delivery_location.address,
                company_name=delivery_location.name,
            )
            logger.info(f"Created delivery address with ID: {delivery_location_id}")

        # Step 3: Create the order
        order_number = self.htc_service.create_order(
            customer_id=action.customer_id,
            hawb=action.hawb,
            pickup_location_id=pickup_location_id,
            delivery_location_id=delivery_location_id,
            pickup_date=pickup_datetime.date,
            pickup_time_start=pickup_datetime.time_start,
            pickup_time_end=pickup_datetime.time_end,
            delivery_date=delivery_datetime.date,
            delivery_time_start=delivery_datetime.time_start,
            delivery_time_end=delivery_datetime.time_end,
            mawb=mawb,
            pickup_notes=pickup_notes,
            delivery_notes=delivery_notes,
            order_notes=order_notes,
            dims=dims,
        )

        logger.info(f"Created HTC order {order_number} for action {action.id}")
        return order_number

    def _execute_update(
        self,
        action: PendingAction,
        # All fields are optional for updates
        pickup_location: LocationValue | None = None,
        pickup_datetime: DatetimeRangeValue | None = None,
        delivery_location: LocationValue | None = None,
        delivery_datetime: DatetimeRangeValue | None = None,
        pickup_notes: str | None = None,
        delivery_notes: str | None = None,
        mawb: str | None = None,
        order_notes: str | None = None,
        dims: list[DimObject] | None = None,
        approver_user_id: str | None = None,
    ) -> list[str]:
        """
        Execute an update action against HTC.

        Handles:
        1. Address resolution (create addresses if address_id is None)
        2. Call htc_service.update_order() with provided fields

        Args:
            action: The pending action being executed (provides htc_order_number)
            pickup_location: Optional new pickup location
            pickup_datetime: Optional new pickup date and time window
            delivery_location: Optional new delivery location
            delivery_datetime: Optional new delivery date and time window
            pickup_notes: Optional new pickup instructions
            delivery_notes: Optional new delivery instructions
            mawb: Optional new master airway bill number
            order_notes: Optional new general order notes
            dims: Optional new list of dimension objects
            approver_user_id: User ID of the approver for audit trail

        Returns:
            List of field names that were updated

        Raises:
            Exception: If address creation or order update fails
        """
        if action.htc_order_number is None:
            raise ValueError(f"Cannot execute update: action {action.id} has no htc_order_number")

        order_number = action.htc_order_number

        # Resolve pickup address if provided
        pickup_location_id: float | None = None
        if pickup_location is not None:
            if pickup_location.address_id is not None:
                pickup_location_id = float(pickup_location.address_id)
                logger.info(f"Using existing pickup address ID: {pickup_location_id}")
            else:
                logger.info(f"Creating new pickup address: {pickup_location.name}, {pickup_location.address}")
                pickup_location_id = self.htc_service.find_or_create_address(
                    address_string=pickup_location.address,
                    company_name=pickup_location.name,
                )
                logger.info(f"Created pickup address with ID: {pickup_location_id}")

        # Resolve delivery address if provided
        delivery_location_id: float | None = None
        if delivery_location is not None:
            if delivery_location.address_id is not None:
                delivery_location_id = float(delivery_location.address_id)
                logger.info(f"Using existing delivery address ID: {delivery_location_id}")
            else:
                logger.info(f"Creating new delivery address: {delivery_location.name}, {delivery_location.address}")
                delivery_location_id = self.htc_service.find_or_create_address(
                    address_string=delivery_location.address,
                    company_name=delivery_location.name,
                )
                logger.info(f"Created delivery address with ID: {delivery_location_id}")

        # Call update_order with all provided fields
        updated_fields = self.htc_service.update_order(
            order_number=order_number,
            pickup_location_id=pickup_location_id,
            delivery_location_id=delivery_location_id,
            pickup_date=pickup_datetime.date if pickup_datetime else None,
            pickup_time_start=pickup_datetime.time_start if pickup_datetime else None,
            pickup_time_end=pickup_datetime.time_end if pickup_datetime else None,
            delivery_date=delivery_datetime.date if delivery_datetime else None,
            delivery_time_start=delivery_datetime.time_start if delivery_datetime else None,
            delivery_time_end=delivery_datetime.time_end if delivery_datetime else None,
            mawb=mawb,
            pickup_notes=pickup_notes,
            delivery_notes=delivery_notes,
            order_notes=order_notes,
            dims=dims,
            approver_username=approver_user_id,
        )

        logger.info(f"Updated HTC order {order_number} for action {action.id}: {updated_fields}")
        return updated_fields

    def _get_pdf_sources_for_action(self, pending_action_id: int) -> list[PdfSource]:
        """
        Get PDF file information from all emails that contributed to this pending action.

        Changed from previous behavior: Now returns ALL PDFs from contributing emails,
        not just the ones that had data extracted. This ensures forms like BOLs, PODs,
        etc. get attached even if they didn't match a template.

        Data path:
          pending_action_fields → output_execution → sub_run → run → source_email
          → ALL runs with that email → ALL pdf_files

        Args:
            pending_action_id: ID of the pending action

        Returns:
            List of PdfSource objects with PDF file info (deduplicated by pdf_file_id)
        """
        # Get all fields for this action
        fields = self.pending_action_field_repo.get_fields_for_action(pending_action_id)

        # Get unique output_execution_ids (excluding None for user-provided values)
        output_execution_ids = set(
            f.output_execution_id for f in fields if f.output_execution_id is not None
        )

        # Collect unique source_email_ids and pdf_file_ids from runs without source emails
        source_email_ids: set[int] = set()
        manual_pdf_ids: set[int] = set()  # PDFs from manual uploads (no source_email_id)

        for output_execution_id in output_execution_ids:
            output_execution = self.output_execution_repo.get_by_id(output_execution_id)
            if not output_execution:
                continue

            sub_run = self.eto_sub_run_repo.get_by_id(output_execution.sub_run_id)
            if not sub_run:
                continue

            run = self.eto_run_repo.get_by_id(sub_run.eto_run_id)
            if not run:
                continue

            if run.source_email_id:
                source_email_ids.add(run.source_email_id)
            else:
                # Manual upload - collect the PDF directly
                manual_pdf_ids.add(run.pdf_file_id)

        # Get ALL PDFs from contributing emails
        seen_pdf_ids: set[int] = set()
        pdf_sources: list[PdfSource] = []

        for email_id in source_email_ids:
            # Get all runs that came from this email
            email_runs = self.eto_run_repo.get_by_source_email_id(email_id)

            for run in email_runs:
                if run.pdf_file_id in seen_pdf_ids:
                    continue
                seen_pdf_ids.add(run.pdf_file_id)

                pdf_file = self.pdf_file_repo.get_by_id(run.pdf_file_id)
                if not pdf_file:
                    logger.warning(f"PDF file {run.pdf_file_id} not found for run {run.id}")
                    continue

                pdf_sources.append(PdfSource(
                    pdf_file_id=pdf_file.id,
                    original_filename=pdf_file.original_filename,
                    file_path=pdf_file.file_path,
                ))

        # Add PDFs from manual uploads
        for pdf_id in manual_pdf_ids:
            if pdf_id in seen_pdf_ids:
                continue
            seen_pdf_ids.add(pdf_id)

            pdf_file = self.pdf_file_repo.get_by_id(pdf_id)
            if not pdf_file:
                logger.warning(f"PDF file {pdf_id} not found (manual upload)")
                continue

            pdf_sources.append(PdfSource(
                pdf_file_id=pdf_file.id,
                original_filename=pdf_file.original_filename,
                file_path=pdf_file.file_path,
            ))

        logger.debug(
            f"Found {len(pdf_sources)} PDF files from {len(source_email_ids)} emails "
            f"and {len(manual_pdf_ids)} manual uploads for pending action {pending_action_id}"
        )
        return pdf_sources

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
                field_names=item.field_names,
                conflict_count=item.conflict_count,
                error_field_count=item.error_field_count,
                error_message=item.error_message,
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

        TOCTOU Protection: On every detail view request for non-terminal actions,
        we re-verify the action type against HTC. This ensures the user sees the
        most up-to-date state (e.g., if someone created the order in HTC, a "create"
        action becomes an "update").

        Address Refresh: For non-terminal actions, we also re-check location fields
        with null address_ids to see if those addresses now exist in HTC.

        Terminal State Protection: Completed, rejected, and failed actions are
        immutable - no TOCTOU or address refresh is performed. They represent
        historical records of what happened.

        Args:
            action_id: ID of the pending action

        Returns:
            PendingActionDetailView with all field values and contributing sources,
            or None if action not found
        """
        # 1. Get the action first to check terminal state
        action = self.pending_action_repo.get_by_id(action_id)
        if action is None:
            return None

        # 2. For non-terminal actions, refresh location address_ids and verify action type
        terminal_statuses = ("completed", "rejected", "failed")
        if action.status not in terminal_statuses:
            # 2a. Refresh location address_ids (may have been resolved since creation)
            self._refresh_location_address_ids(action_id)

            # 2b. Verify action type is still correct (TOCTOU protection)
            try:
                self.verify_and_update_action_type(action_id)
            except ValueError:
                # Action not found (shouldn't happen, but be safe)
                return None

            # 2c. Re-fetch action after potential updates
            action = self.pending_action_repo.get_by_id(action_id)
            if action is None:
                return None

        # 3. Get fields with source chain data (single JOIN query)
        fields_with_sources = self.pending_action_field_repo.get_fields_with_sources_for_action(action_id)

        # 4. Build field views grouped by field_name
        fields: dict[str, list[PendingActionFieldView]] = {}
        for row in fields_with_sources:
            field_view = PendingActionFieldView(
                id=row["id"],
                field_name=row["field_name"],
                value=row["value"],
                is_selected=row["is_selected"],
                is_approved_for_update=row["is_approved_for_update"],
                sub_run_id=row["sub_run_id"],
                processing_status=row["processing_status"],
                processing_error=row["processing_error"],
                raw_value=row["raw_value"],
                contributed_at=row["contributed_at"],
                source_filename=row["pdf_filename"],
            )
            if row["field_name"] not in fields:
                fields[row["field_name"]] = []
            fields[row["field_name"]].append(field_view)

        # 5. Build contributing sources (grouped by sub_run_id)
        sources_by_sub_run: dict[int, dict] = {}
        user_contributed_fields: set[str] = set()
        for row in fields_with_sources:
            sub_run_id = row["sub_run_id"]
            if sub_run_id is None:
                # User-provided value — collect for synthetic source
                user_contributed_fields.add(row["field_name"])
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

        # Add synthetic source for user-provided fields
        if user_contributed_fields:
            contributing_sources.append(
                ContributingSource(
                    sub_run_id=None,
                    pdf_filename="Manual Entry",
                    template_name=None,
                    source_type="user",
                    source_identifier="Manual Entry",
                    fields_contributed=sorted(user_contributed_fields),
                    contributed_at=action.updated_at,
                )
            )

        # Sort by contributed_at descending (most recent first)
        contributing_sources.sort(key=lambda s: s.contributed_at, reverse=True)

        # 6. Get current HTC values for updates
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

        # 7. Build and return the detail view
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
            execution_result=action.execution_result,
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
        result = self.process_output_execution(output_execution.id)

        if result.pending_action_id:
            # Fetch the full pending action for return
            pending_action = self.pending_action_repo.get_by_id(result.pending_action_id)
            if result.has_failures:
                logger.warning(
                    f"Mock output execution processed with field errors: "
                    f"pending_action_id={result.pending_action_id}, "
                    f"success={result.successful_fields}, failed={result.failed_fields}"
                )
            else:
                logger.info(
                    f"Mock output execution processed: pending_action_id={result.pending_action_id}, "
                    f"action_type={pending_action.action_type if pending_action else 'unknown'}, "
                    f"fields={result.successful_fields}"
                )
            return pending_action
        else:
            logger.info(
                f"Mock output execution had no changes compared to HTC - no pending action created"
            )
            return None

    # ========== User Interactions ==========

    def select_field_value(
        self,
        pending_action_id: int,
        field_id: int,
    ) -> PendingAction:
        """
        Select a specific field value for a pending action.

        Used for:
        - Resolving conflicts (selecting one of multiple conflicting values)
        - Changing a previously selected value

        Sets is_selected=TRUE for the chosen value, FALSE for all other values
        of the same field. Recalculates action status after selection.

        Args:
            pending_action_id: ID of the pending action
            field_id: ID of the pending_action_field record to select

        Returns:
            Updated PendingAction with recalculated status

        Raises:
            ValueError: If the field doesn't exist or doesn't belong to this action
        """
        logger.info(f"Selecting field value {field_id} for action {pending_action_id}")

        # Get the field record to find its field_name
        field = self.pending_action_field_repo.get_by_id(field_id)
        if field is None:
            raise ValueError(f"Field {field_id} not found")

        if field.pending_action_id != pending_action_id:
            raise ValueError(
                f"Field {field_id} does not belong to action {pending_action_id}"
            )

        # Set selection (selects this one, deselects others with same field_name)
        self.pending_action_field_repo.set_selection_for_field(
            action_id=pending_action_id,
            field_name=field.field_name,
            selected_field_id=field_id,
        )

        # Recalculate action status (conflict may be resolved now)
        updated_action = self._recalculate_action_status(pending_action_id)

        # Broadcast update event
        order_event_manager.broadcast_sync("pending_action_updated", {
            "id": updated_action.id,
            "status": updated_action.status,
            "action_type": updated_action.action_type,
        })

        logger.info(
            f"Selected field {field_id} ({field.field_name}) for action {pending_action_id}, "
            f"new status: {updated_action.status}"
        )

        return updated_action

    def set_user_value(
        self,
        pending_action_id: int,
        field_name: str,
        value: Any,
    ) -> tuple[int, PendingAction]:
        """
        User provides their own value for a field (overriding extracted data).

        Creates a new pending_action_fields row with output_execution_id=NULL.
        Sets is_selected=TRUE for this value, FALSE for all others.
        Recalculates action status after update.

        Args:
            pending_action_id: ID of the pending action
            field_name: Field name (must be a valid ORDER_FIELDS key)
            value: Raw value from frontend, validated and transformed by data_type

        Returns:
            Tuple of (new field ID, updated PendingAction)

        Raises:
            ValueError: If field_name is invalid or value doesn't match expected type
        """
        logger.info(f"Setting user value for action {pending_action_id}, field '{field_name}'")

        # 1. Validate field_name
        if field_name not in ORDER_FIELDS:
            raise ValueError(f"Unknown field name: '{field_name}'")

        field_def = ORDER_FIELDS[field_name]

        # 2. Validate action exists
        action = self.pending_action_repo.get_by_id(pending_action_id)
        if action is None:
            raise ValueError(f"Pending action {pending_action_id} not found")

        # 3. Validate and transform value based on data_type
        transformed_value = self._validate_and_transform_user_value(
            field_name=field_name,
            data_type=field_def.data_type,
            value=value,
        )

        # 4. Deselect all existing values for this field
        self.pending_action_field_repo.clear_selection_for_field(
            action_id=pending_action_id,
            field_name=field_name,
        )

        # 5. Create the new field record (auto-selected)
        new_field = self.pending_action_field_repo.create(
            data=PendingActionFieldCreate(
                pending_action_id=pending_action_id,
                output_execution_id=None,  # User-provided value
                field_name=field_name,
                value=transformed_value,
                is_selected=True,
                is_approved_for_update=True,
                processing_status="success",
                raw_value=json.dumps(value),  # Store original frontend payload
            )
        )

        # 6. Recalculate action status
        updated_action = self._recalculate_action_status(pending_action_id)

        # 7. Broadcast update event
        order_event_manager.broadcast_sync("pending_action_updated", {
            "id": updated_action.id,
            "status": updated_action.status,
            "action_type": updated_action.action_type,
        })

        logger.info(
            f"User value set for field '{field_name}' on action {pending_action_id}, "
            f"field_id={new_field.id}, new status: {updated_action.status}"
        )

        return new_field.id, updated_action

    def _validate_and_transform_user_value(
        self,
        field_name: str,
        data_type: str,
        value: Any,
    ) -> Any:
        """
        Validate and transform a user-provided value to the internal format.

        Args:
            field_name: The field name (for error messages)
            data_type: The expected data type (string, datetime_range, location, dims)
            value: The raw value from the frontend

        Returns:
            Transformed value in internal format

        Raises:
            ValueError: If value doesn't match expected structure
        """
        if data_type == "string":
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Field '{field_name}' requires a non-empty string value")
            return value.strip().upper()

        elif data_type == "datetime_range":
            if not isinstance(value, dict):
                raise ValueError(f"Field '{field_name}' requires a datetime range object")

            date = value.get("date")
            start_time = value.get("startTime")
            end_time = value.get("endTime")

            if not date or not start_time or not end_time:
                raise ValueError(
                    f"Field '{field_name}' requires date, startTime, and endTime"
                )

            return DatetimeRangeValue(
                date=date,
                time_start=start_time,
                time_end=end_time,
            )

        elif data_type == "location":
            if not isinstance(value, dict):
                raise ValueError(f"Field '{field_name}' requires a location object")

            mode = value.get("mode")

            if mode == "select":
                address_id = value.get("addressId")
                if address_id is None:
                    raise ValueError(f"Field '{field_name}': must select an address")

                # Look up address info from HTC
                addr_info = self.htc_service.get_address_info(float(address_id))
                if addr_info is None:
                    raise ValueError(
                        f"Field '{field_name}': address ID {address_id} not found in HTC"
                    )

                # Format address string same as _format_address_from_info
                street = addr_info.addr_ln1
                if addr_info.addr_ln2:
                    street = f"{addr_info.addr_ln1} {addr_info.addr_ln2}"
                formatted = f"{street}, {addr_info.city}, {addr_info.state} {addr_info.zip_code}"

                return LocationValue(
                    address_id=int(address_id),
                    name=addr_info.company.upper(),
                    address=formatted.upper(),
                )

            elif mode == "create":
                company_name = value.get("companyName", "").strip()
                address = value.get("address", "").strip()

                if not company_name or not address:
                    raise ValueError(
                        f"Field '{field_name}': company name and address are required"
                    )

                return LocationValue(
                    address_id=None,  # New address, not yet in HTC
                    name=company_name.upper(),
                    address=address.upper(),
                )

            else:
                raise ValueError(
                    f"Field '{field_name}': location mode must be 'select' or 'create'"
                )

        elif data_type == "dims":
            if not isinstance(value, list) or len(value) == 0:
                raise ValueError(f"Field '{field_name}' requires a non-empty list of dimensions")

            dims = []
            for i, row in enumerate(value):
                if not isinstance(row, dict):
                    raise ValueError(f"Field '{field_name}': row {i} must be an object")

                try:
                    dims.append(DimObject(
                        qty=int(row.get("qty", 0)),
                        length=round(float(row.get("length", 0)), 3),
                        width=round(float(row.get("width", 0)), 3),
                        height=round(float(row.get("height", 0)), 3),
                        weight=round(float(row.get("weight", 0)), 3),
                    ))
                except (TypeError, ValueError) as e:
                    raise ValueError(
                        f"Field '{field_name}': invalid values in row {i}: {e}"
                    )

            return dims

        else:
            raise ValueError(f"Unsupported data type '{data_type}' for field '{field_name}'")

    def set_field_approval(
        self,
        pending_action_id: int,
        field_name: str,
        is_approved: bool,
    ) -> bool:
        """
        Toggle whether a field should be included in an update.

        Sets is_approved_for_update on ALL values for this field (approval is
        per-field-name, not per-value). Only relevant for action_type='update'.

        Args:
            pending_action_id: ID of the pending action
            field_name: Name of the field to toggle
            is_approved: Whether the field should be included in the update

        Returns:
            The new approval status

        Raises:
            ValueError: If action not found or is not an update type
        """
        logger.info(
            f"Setting field approval for action {pending_action_id}, "
            f"field {field_name}, approved={is_approved}"
        )

        # Verify the action exists and is an update type
        action = self.pending_action_repo.get_by_id(pending_action_id)
        if action is None:
            raise ValueError(f"Pending action {pending_action_id} not found")

        if action.action_type != "update":
            raise ValueError(
                f"Field approval only applies to updates, not {action.action_type}"
            )

        # Update approval for all values of this field
        rows_updated = self.pending_action_field_repo.set_approval_for_field(
            action_id=pending_action_id,
            field_name=field_name,
            is_approved=is_approved,
        )

        if rows_updated == 0:
            raise ValueError(
                f"No field values found for field '{field_name}' on action {pending_action_id}"
            )

        # Broadcast update event
        order_event_manager.broadcast_sync("pending_action_updated", {
            "id": action.id,
            "status": action.status,
            "action_type": action.action_type,
        })

        logger.info(
            f"Set approval={is_approved} for {rows_updated} values of "
            f"field '{field_name}' on action {pending_action_id}"
        )

        return is_approved

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

        IMPORTANT: Actions in terminal states (completed, rejected, failed) are preserved
        as historical records. Their field contributions are NOT deleted, and the actions
        themselves are not modified or deleted.

        Steps:
        1. Find all pending_action_ids affected by this output_execution
        2. Identify which actions are in terminal states (skip these)
        3. Delete pending_action_fields for non-terminal actions only
        4. For each non-terminal affected pending_action:
           a. Check if any extracted fields remain (output_execution_id IS NOT NULL)
           b. If NO extracted fields remain: delete the entire pending_action
           c. If extracted fields remain: recalculate status

        Args:
            output_execution_id: ID of the output execution being cleaned up

        Returns:
            CleanupResult with counts of deleted fields and actions
        """
        terminal_statuses = ("completed", "rejected", "failed")

        logger.debug(f"Cleaning up contributions from output execution {output_execution_id}")

        # Step 1: Find all affected pending actions
        fields = self.pending_action_field_repo.get_fields_by_output_execution(output_execution_id)

        if not fields:
            logger.debug(f"No fields found for output execution {output_execution_id}")
            return CleanupResult(fields_deleted=0, actions_deleted=0, actions_recalculated=0)

        # Get unique pending_action_ids
        affected_action_ids = set(f.pending_action_id for f in fields)
        logger.debug(f"Found {len(fields)} fields affecting {len(affected_action_ids)} actions")

        # Step 2: Identify terminal actions (these are preserved as historical records)
        terminal_action_ids: set[int] = set()
        non_terminal_action_ids: set[int] = set()

        for action_id in affected_action_ids:
            action = self.pending_action_repo.get_by_id(action_id)
            if action and action.status in terminal_statuses:
                terminal_action_ids.add(action_id)
                logger.debug(
                    f"Preserving terminal action {action_id} (status={action.status}) - "
                    f"contributions will not be deleted"
                )
            else:
                non_terminal_action_ids.add(action_id)

        if terminal_action_ids:
            logger.info(
                f"Skipping cleanup for {len(terminal_action_ids)} terminal action(s): "
                f"{terminal_action_ids}"
            )

        # Step 3: Delete fields only for non-terminal actions
        fields_deleted = 0
        if non_terminal_action_ids:
            fields_deleted = self.pending_action_field_repo.delete_by_output_execution_excluding_actions(
                output_execution_id, terminal_action_ids
            )

        # Step 4: Process each non-terminal affected action
        actions_deleted = 0
        actions_recalculated = 0

        for action_id in non_terminal_action_ids:
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
            f"fields={fields_deleted}, actions_deleted={actions_deleted}, "
            f"recalculated={actions_recalculated}, preserved={len(terminal_action_ids)}"
        )

        return CleanupResult(
            fields_deleted=fields_deleted,
            actions_deleted=actions_deleted,
            actions_recalculated=actions_recalculated,
        )

    def get_terminal_actions_for_sub_run(self, sub_run_id: int) -> list[dict]:
        """
        Check if a sub-run contributed to any pending actions in terminal states.

        Terminal states are: completed, rejected, failed

        Used to warn users before reprocessing a sub-run that contributed to
        actions that have already been approved/rejected.

        Args:
            sub_run_id: ID of the sub-run to check

        Returns:
            List of dicts with info about affected terminal actions:
            [{"id": 1, "hawb": "ABC123", "status": "completed", "action_type": "create"}, ...]
        """
        terminal_statuses = ("completed", "rejected", "failed")

        # Find all output executions for this sub-run
        output_executions = self.output_execution_repo.get_by_sub_run_id(sub_run_id)

        if not output_executions:
            return []

        # Collect all affected pending action IDs
        affected_action_ids: set[int] = set()
        for output_execution in output_executions:
            fields = self.pending_action_field_repo.get_fields_by_output_execution(output_execution.id)
            for field in fields:
                affected_action_ids.add(field.pending_action_id)

        if not affected_action_ids:
            return []

        # Check which of these actions are in terminal states
        terminal_actions = []
        for action_id in affected_action_ids:
            action = self.pending_action_repo.get_by_id(action_id)
            if action and action.status in terminal_statuses:
                terminal_actions.append({
                    "id": action.id,
                    "hawb": action.hawb,
                    "status": action.status,
                    "action_type": action.action_type,
                })

        return terminal_actions

    # ========== Email Notifications ==========

    def _get_contributing_email_details(self, pending_action_id: int) -> dict[str, datetime]:
        """
        Get sender email addresses and their received dates from all sources
        that contributed to this pending action.

        Data path: pending_action_fields → output_execution → sub_run → run → email

        Only returns addresses from email sources (not manual uploads which have
        no source_email_id).

        Args:
            pending_action_id: ID of the pending action

        Returns:
            Dict mapping email address to received_date (may be empty if all
            sources were manual uploads)
        """
        # Get all fields for this action to find unique output_execution_ids
        fields = self.pending_action_field_repo.get_fields_for_action(pending_action_id)

        # Collect unique output_execution_ids (excluding None for user-provided values)
        output_execution_ids = set(
            f.output_execution_id for f in fields
            if f.output_execution_id is not None
        )

        if not output_execution_ids:
            return {}

        email_details: dict[str, datetime] = {}

        for output_exec_id in output_execution_ids:
            # Get output execution to find sub_run_id
            output_exec = self.output_execution_repo.get_by_id(output_exec_id)
            if not output_exec:
                continue

            # Get sub_run to find eto_run_id
            sub_run = self.eto_sub_run_repo.get_by_id(output_exec.sub_run_id)
            if not sub_run:
                continue

            # Get run to find source_email_id
            run = self.eto_run_repo.get_by_id(sub_run.eto_run_id)
            if not run or not run.source_email_id:
                # Manual upload - no email to send
                continue

            # Get email record for sender info
            email = self._email_repo.get_by_id(run.source_email_id)
            if email and email.sender_email and email.received_date:
                # Keep the most recent date if multiple emails from same sender
                if (
                    email.sender_email not in email_details or
                    email.received_date > email_details[email.sender_email]
                ):
                    email_details[email.sender_email] = email.received_date

        return email_details

    def _build_order_created_email(
        self,
        action: PendingAction,
        htc_order_number: float,
        email_received_date: datetime,
    ) -> tuple[str, str, str]:
        """
        Build email subject and body for order creation notification.

        Args:
            action: The pending action that was executed
            htc_order_number: The HTC order number
            email_received_date: The date/time the source email was received

        Returns:
            Tuple of (subject, plain_text_body, html_body)
        """
        order_num = int(htc_order_number)
        subject = f"HTC Order Created - #{order_num} - {action.hawb}"

        # Convert email received date from UTC to CST for display
        from zoneinfo import ZoneInfo
        cst_tz = ZoneInfo("America/Chicago")
        if email_received_date.tzinfo is None:
            # Assume naive datetime is UTC
            email_received_date = email_received_date.replace(tzinfo=timezone.utc)
        email_received_cst = email_received_date.astimezone(cst_tz)
        formatted_date = email_received_cst.strftime("%B %d, %Y at %I:%M %p CST")

        # Get customer name for the email
        customer_name = self.htc_service.get_customer_name(action.customer_id)
        customer_display = customer_name or f"Customer #{action.customer_id}"

        # Build plain text body
        lines = [
            f"An order has been created from your email received on {formatted_date}.",
            f"Thank you for your business.",
            "",
            "Order Details:",
            f"  HTC Order Number: #{order_num}",
            f"  HAWB: {action.hawb}",
            f"  Customer: {customer_display}",
            "",
            "This is an automated notification from the Harrah Email-To-Order system.",
        ]

        plain_body = "\n".join(lines)

        # Build HTML body
        html_body = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <h2 style="color: #2c5282;">HTC Order Created</h2>
    <p>An order has been created from your email received on <strong>{formatted_date}</strong>.</p>
    <p>Thank you for your business.</p>

    <table style="border-collapse: collapse; margin: 20px 0;">
        <tr>
            <td style="padding: 8px; font-weight: bold;">HTC Order Number:</td>
            <td style="padding: 8px;">#{order_num}</td>
        </tr>
        <tr>
            <td style="padding: 8px; font-weight: bold;">HAWB:</td>
            <td style="padding: 8px;">{action.hawb}</td>
        </tr>
        <tr>
            <td style="padding: 8px; font-weight: bold;">Customer:</td>
            <td style="padding: 8px;">{customer_display}</td>
        </tr>
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
        recipient_email: str,
        subject: str,
        body: str,
        body_html: str,
    ) -> bool:
        """
        Send notification email to a recipient.

        Uses system setting 'email.default_sender_account_id' for sender.
        Logs errors but does not raise - email failure should not block order processing.

        Args:
            recipient_email: Recipient email address
            subject: Email subject
            body: Plain text email body
            body_html: HTML email body

        Returns:
            True if email sent successfully, False otherwise
        """
        email_service = self._get_email_service()
        if not email_service:
            logger.debug("Email service not available - skipping notification")
            return False

        # Get sender account from system settings
        sender_account_id_str = self._system_settings_repo.get("email.default_sender_account_id")
        if not sender_account_id_str:
            logger.warning("No default sender account configured - skipping email notification")
            return False

        try:
            sender_account_id = int(sender_account_id_str)
        except ValueError:
            logger.error(f"Invalid sender account ID in settings: {sender_account_id_str}")
            return False

        try:
            result = email_service.send_email(
                account_id=sender_account_id,
                to_address=recipient_email,
                subject=subject,
                body=body,
                body_html=body_html,
            )
            if result.success:
                logger.info(f"Sent order notification email to {recipient_email}")
                return True
            else:
                logger.warning(f"Failed to send notification to {recipient_email}: {result.message}")
                return False
        except Exception as e:
            logger.error(f"Error sending notification to {recipient_email}: {e}")
            return False

    def _send_order_created_notification(
        self,
        pending_action_id: int,
        htc_order_number: float,
    ) -> None:
        """
        Send email notification for a newly created order.

        Sends personalized emails to each recipient with their specific email date.
        Only sends to email sources - manual uploads do not receive notifications.

        Args:
            pending_action_id: ID of the pending action
            htc_order_number: The HTC order number that was created
        """
        try:
            # Get recipient emails with their received dates
            email_details = self._get_contributing_email_details(pending_action_id)
            if not email_details:
                logger.debug(
                    f"No email recipients for pending action {pending_action_id} - "
                    "skipping notification (likely manual upload)"
                )
                return

            # Get pending action details
            action = self.pending_action_repo.get_by_id(pending_action_id)
            if not action:
                logger.warning(f"Cannot send notification: pending action {pending_action_id} not found")
                return

            # Build and send personalized email for each recipient
            sent_count = 0
            for recipient_email, received_date in email_details.items():
                subject, body, body_html = self._build_order_created_email(
                    action, htc_order_number, received_date
                )
                if self._send_order_notification(recipient_email, subject, body, body_html):
                    sent_count += 1

            if sent_count > 0:
                logger.info(
                    f"Sent {sent_count} order created notification(s) for "
                    f"pending action {pending_action_id}"
                )

        except Exception as e:
            # Log but don't fail - email notification should not block order processing
            logger.error(
                f"Failed to send order created notification for pending action "
                f"{pending_action_id}: {e}"
            )

    # ==================== Address Lookup ====================

    def list_addresses(
        self,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        """
        Get active addresses from HTC database with search and pagination.

        Used by the AddFieldModal to populate address dropdowns for
        pickup_location and delivery_location fields.

        Returns:
            Tuple of (list of address dicts, total matching count)
        """
        return self.htc_service.list_addresses(search=search, limit=limit, offset=offset)
