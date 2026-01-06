"""
HTC Integration Service

Centralized service for all HTC Access database operations.
Provides order lookup, creation, and update functionality.

This is the single point of access for HTC database operations.
All other services should use this service rather than accessing
the HTC database directly.

Architecture:
    This service delegates to specialized utility classes:
    - HtcLookupUtils: Customer, address, and order lookups
    - HtcAddressUtils: Address parsing, normalization, and creation
    - HtcOrderUtils: Order number generation, creation, and updates
    - HtcOrderWorker: Background worker for creating HTC orders from pending orders
"""

from typing import Any

from shared.logging import get_logger
from shared.exceptions import OutputExecutionError
from shared.config.database import get_htc_apps_dir
from shared.config.storage import get_storage_configuration
from shared.database.access_connection import AccessConnectionManager, AccessConnection

from features.htc_integration.lookup_utils import (
    HtcLookupUtils,
    HtcOrderDetails,
    HtcOrderFields,
    AddressInfo,
    CustomerInfo,
)
from features.htc_integration.address_utils import HtcAddressUtils
from features.htc_integration.order_utils import HtcOrderUtils, PreparedOrderData
from features.htc_integration.attachment_utils import AttachmentManager, PdfSource, AttachmentResult
from shared.types.pending_orders import PendingOrder

logger = get_logger(__name__)


# Re-export types for backward compatibility
__all__ = [
    "HtcIntegrationService",
    "HtcOrderDetails",
    "HtcOrderFields",
    "AddressInfo",
    "CustomerInfo",
    "PreparedOrderData",
    "PdfSource",
    "AttachmentResult",
]


def _uppercase_str(value: str | None) -> str | None:
    """Uppercase a string value, returning None if input is None."""
    if value is None:
        return None
    return value.upper()


class HtcIntegrationService:
    """
    Centralized service for HTC Access database operations.

    Provides:
    - Order lookup by customer/HAWB
    - Order creation with automatic order number generation
    - Order updates
    - Order detail retrieval
    - Address lookup and creation

    All HTC database operations should go through this service
    to ensure consistency and proper connection management.
    """

    # Hardcoded values (always 1, 1 for local system - matches VBA legacy)
    CO_ID = 1
    BR_ID = 1

    def __init__(
        self,
        access_connection_manager: AccessConnectionManager,
        connection_manager: Any = None,
        database_name: str = "htc_300",
    ) -> None:
        """
        Initialize the service.

        Args:
            access_connection_manager: AccessConnectionManager for HTC database access
            connection_manager: Database connection manager (unused, kept for compatibility)
            database_name: Name of the database containing HTC tables
        """
        logger.debug("Initializing HtcIntegrationService...")

        self._access_connection_manager = access_connection_manager
        self._database_name = database_name

        # Initialize utility classes
        self._lookup_utils = HtcLookupUtils(
            get_connection=self._get_connection,
            co_id=self.CO_ID,
            br_id=self.BR_ID,
        )
        self._address_utils = HtcAddressUtils(
            get_connection=self._get_connection,
            co_id=self.CO_ID,
            br_id=self.BR_ID,
        )
        self._order_utils = HtcOrderUtils(
            get_connection=self._get_connection,
            co_id=self.CO_ID,
            br_id=self.BR_ID,
        )

        # Initialize attachment manager (optional - only if HTC_APPS_DIR is configured)
        self._attachment_manager: AttachmentManager | None = None
        htc_apps_dir = get_htc_apps_dir()
        if htc_apps_dir:
            eto_storage_path = get_storage_configuration()
            self._attachment_manager = AttachmentManager(
                htc_apps_dir=htc_apps_dir,
                eto_storage_path=eto_storage_path,
                connection=self._get_connection(),
                co_id=self.CO_ID,
                br_id=self.BR_ID,
            )
            logger.info(f"AttachmentManager initialized (HTC: {htc_apps_dir}, ETO: {eto_storage_path})")
        else:
            logger.warning("HTC_APPS_DIR not configured - attachment processing disabled")

        logger.info("HtcIntegrationService initialized successfully")

    def _get_connection(self) -> AccessConnection:
        """Get the HTC database connection."""
        return self._access_connection_manager.get_connection(self._database_name)

    # ==================== Lookup Operations ====================
    # Delegated to HtcLookupUtils

    def lookup_order_by_customer_and_hawb(
        self,
        customer_id: int,
        hawb: str,
    ) -> float | None:
        """
        Check if an order exists in HTC Open Orders for a customer/HAWB pair.

        Args:
            customer_id: The customer ID to look up
            hawb: The HAWB string to look up

        Returns:
            The HTC order number (float) if found, None if not found
        """
        return self._lookup_utils.lookup_order_by_customer_and_hawb(customer_id, hawb)

    def count_orders_by_customer_and_hawb(
        self,
        customer_id: int,
        hawb: str,
    ) -> int:
        """
        Count how many orders exist in HTC Open Orders for a customer/HAWB pair.

        This is used to detect duplicate orders that require manual intervention.

        Args:
            customer_id: The customer ID to look up
            hawb: The HAWB string to look up

        Returns:
            The count of matching orders (0, 1, or more)
        """
        return self._lookup_utils.count_orders_by_customer_and_hawb(customer_id, hawb)

    def get_customer_name(self, customer_id: int) -> str | None:
        """
        Look up customer name by customer ID.

        Args:
            customer_id: The customer ID to look up

        Returns:
            Customer name string if found, None if not found
        """
        return self._lookup_utils.get_customer_name(customer_id)

    def get_customer_info(self, customer_id: int) -> CustomerInfo | None:
        """
        Get full customer information for order creation.

        Args:
            customer_id: The customer ID to look up

        Returns:
            CustomerInfo dataclass if found, None if not found
        """
        return self._lookup_utils.get_customer_info(customer_id)

    def get_address_info(self, address_id: float) -> AddressInfo | None:
        """
        Get full address information for order creation.

        Args:
            address_id: The address ID (FavID) to look up

        Returns:
            AddressInfo dataclass if found, None if not found
        """
        return self._lookup_utils.get_address_info(address_id)

    def get_aci_letter(self, aci_id: int) -> str:
        """
        Get the ACI zone letter from an ACI ID.

        Args:
            aci_id: The ACI ID to look up

        Returns:
            ACI zone letter (e.g., "A", "B", "C", "D") or empty string if not found
        """
        return self._lookup_utils.get_aci_letter(aci_id)

    def get_order_details(self, order_number: float) -> HtcOrderDetails | None:
        """
        Get details of an HTC order by order number.

        Args:
            order_number: The HTC order number

        Returns:
            HtcOrderDetails if found, None if not found
        """
        return self._lookup_utils.get_order_details(order_number)

    def get_order_fields(self, order_number: float) -> HtcOrderFields | None:
        """
        Get all editable fields of an HTC order.

        Returns all field values that can be compared against pending updates,
        allowing the frontend to show current HTC values vs proposed changes.

        Args:
            order_number: The HTC order number

        Returns:
            HtcOrderFields if found, None if not found
        """
        return self._lookup_utils.get_order_fields(order_number)

    # ==================== Address Operations ====================
    # Delegated to HtcAddressUtils

    def find_address_id(self, address_string: str) -> float | None:
        """
        Find an address ID from a full address string.

        Args:
            address_string: Full address string to check
                e.g., "123 Main St, Suite 100, Dallas, TX 75201"

        Returns:
            Address ID (FavID as float) if found, None otherwise.
        """
        return self._address_utils.find_address_id(address_string)

    def find_or_create_address(
        self,
        address_string: str,
        company_name: str,
        country: str = "USA",
    ) -> float:
        """
        Find an existing address or create a new one.

        Args:
            address_string: Full address string to find/create
            company_name: Company name to use if creating new address
            country: Country name (default: "USA")

        Returns:
            Address ID (FavID) as float - either existing or newly created

        Raises:
            ValueError: If address cannot be parsed
            OutputExecutionError: If address creation fails
        """
        return self._address_utils.find_or_create_address(
            address_string=address_string,
            company_name=company_name,
            country=country,
        )

    # ==================== Order Operations ====================
    # Delegated to HtcOrderUtils

    def update_order_simple(self, order_number: float, updates: dict) -> None:
        """
        Update an existing order in HTC with a simple dict of field updates.

        This handles dims separately - if 'dims' is in updates, it will
        replace the existing dims records.

        Args:
            order_number: The HTC order number to update
            updates: Dict of field_name -> new_value (may include 'dims')

        Raises:
            OutputExecutionError: If update fails
        """
        import json

        # Uppercase all string fields for HTC database
        string_fields = [
            'hawb', 'mawb', 'pickup_company_name', 'pickup_address', 'pickup_notes',
            'delivery_company_name', 'delivery_address', 'delivery_notes', 'order_notes'
        ]
        for field in string_fields:
            if field in updates and updates[field] is not None:
                updates[field] = updates[field].upper()

        # Extract dims from updates if present
        dims = updates.pop('dims', None)

        # Update regular fields if any remain
        if updates:
            self._order_utils.update_order_fields(order_number, updates)

        # Handle dims separately (replace strategy)
        if dims is not None:
            # Parse dims if it's a JSON string
            if isinstance(dims, str):
                try:
                    dims = json.loads(dims)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse dims JSON for order {order_number}")
                    dims = None
            if dims:
                self._order_utils.replace_dims_records(order_number, dims)

    def remove_from_orders_in_work(self, order_number: float) -> None:
        """
        Remove an order from the Orders In Work table.

        Args:
            order_number: The HTC order number to remove
        """
        self._order_utils.remove_from_orders_in_work(order_number)

    def save_hawb_association(
        self,
        hawb: str,
        customer_id: int,
        order_number: float,
    ) -> bool:
        """
        Save a customer/HAWB association after order creation.

        Args:
            hawb: The HAWB string
            customer_id: The customer ID
            order_number: The order number this HAWB is associated with

        Returns:
            True if saved successfully, False if HAWB already exists
        """
        return self._order_utils.save_hawb_association(hawb, customer_id, order_number)

    def determine_order_type(
        self,
        pu_aci: str,
        pu_branch: bool,
        pu_carrier: bool,
        del_aci: str,
        del_branch: bool,
        del_carrier: bool,
    ) -> int:
        """
        Determine the order type based on pickup/delivery location characteristics.

        Args:
            pu_aci: Pickup ACI zone letter (A, B, C, D, etc.)
            pu_branch: Whether pickup location is a branch
            pu_carrier: Whether pickup location is a carrier
            del_aci: Delivery ACI zone letter
            del_branch: Whether delivery location is a branch
            del_carrier: Whether delivery location is a carrier

        Returns:
            Order type code (1, 2, 3, 4, 5, 8, 9, 10, or 11)
        """
        return self._order_utils.determine_order_type(
            pu_aci=pu_aci,
            pu_branch=pu_branch,
            pu_carrier=pu_carrier,
            del_aci=del_aci,
            del_branch=del_branch,
            del_carrier=del_carrier,
        )

    # ==================== Order Creation Orchestrator ====================

    def create_order(
        self,
        customer_id: int,
        hawb: str,
        pickup_company_name: str,
        pickup_address: str,
        pickup_time_start: str,
        pickup_time_end: str,
        delivery_company_name: str,
        delivery_address: str,
        delivery_time_start: str,
        delivery_time_end: str,
        mawb: str | None = None,
        pickup_notes: str | None = None,
        delivery_notes: str | None = None,
        order_notes: str | None = None,
        dims: list[dict[str, Any]] | None = None,
    ) -> float:
        """
        Create an HTC order from raw input data.

        This is the main orchestrator that follows the two-phase order creation flow:

        Phase 1 - Data Gathering:
            1. Resolve pickup address (find or create)
            2. Resolve delivery address (find or create)
            3. Look up full address info for both
            4. Look up customer info
            5. Determine order type
            6. Prepare all field values

        Phase 2 - Order Creation:
            7. Reserve order number (adds to OIW)
            8. Insert order record
            9. On success: update LON, remove from OIW, save HAWB, create history

        Args:
            customer_id: HTC customer ID
            hawb: House Air Waybill number
            pickup_company_name: Company name for pickup location
            pickup_address: Pickup street address (e.g., "123 Main St, Dallas, TX 75201")
            pickup_time_start: Pickup start datetime (e.g., "2025-12-15 09:00")
            pickup_time_end: Pickup end datetime
            delivery_company_name: Company name for delivery location
            delivery_address: Delivery street address (e.g., "456 Oak Ave, Fort Worth, TX 76102")
            delivery_time_start: Delivery start datetime
            delivery_time_end: Delivery end datetime
            mawb: Optional Master Air Waybill number
            pickup_notes: Optional pickup notes
            delivery_notes: Optional delivery notes
            order_notes: Optional general order notes
            dims: Optional list of dimension objects (each with height, length, width, qty, weight)

        Returns:
            The new HTC order number

        Raises:
            OutputExecutionError: If order creation fails
            ValueError: If required data is missing
        """
        logger.info(f"Creating HTC order for customer {customer_id}, HAWB: {hawb}")

        # ================================================================
        # UPPERCASE ALL STRING FIELDS FOR HTC DATABASE
        # ================================================================
        hawb = _uppercase_str(hawb) or ""
        mawb = _uppercase_str(mawb)
        pickup_company_name = _uppercase_str(pickup_company_name) or ""
        pickup_address = _uppercase_str(pickup_address) or ""
        pickup_notes = _uppercase_str(pickup_notes)
        delivery_company_name = _uppercase_str(delivery_company_name) or ""
        delivery_address = _uppercase_str(delivery_address) or ""
        delivery_notes = _uppercase_str(delivery_notes)
        order_notes = _uppercase_str(order_notes)

        # ================================================================
        # PHASE 1: DATA GATHERING
        # ================================================================

        # --- Step 1: Resolve pickup address ---
        if not pickup_address:
            raise ValueError("Pickup address is required")
        if not pickup_company_name:
            raise ValueError("Pickup company name is required")

        pu_address_id = self._address_utils.find_or_create_address(
            address_string=pickup_address,
            company_name=pickup_company_name,
        )
        logger.debug(f"Resolved pickup address ID: {pu_address_id}")

        # --- Step 2: Resolve delivery address ---
        if not delivery_address:
            raise ValueError("Delivery address is required")
        if not delivery_company_name:
            raise ValueError("Delivery company name is required")

        del_address_id = self._address_utils.find_or_create_address(
            address_string=delivery_address,
            company_name=delivery_company_name,
        )
        logger.debug(f"Resolved delivery address ID: {del_address_id}")

        # --- Step 3: Look up full pickup address info ---
        pu_addr = self._lookup_utils.get_address_info(pu_address_id)
        if not pu_addr:
            raise OutputExecutionError(f"Failed to get pickup address info for ID {pu_address_id}")

        pu_aci_letter = self._lookup_utils.get_aci_letter(pu_addr.aci_id)

        # --- Step 4: Look up full delivery address info ---
        del_addr = self._lookup_utils.get_address_info(del_address_id)
        if not del_addr:
            raise OutputExecutionError(f"Failed to get delivery address info for ID {del_address_id}")

        del_aci_letter = self._lookup_utils.get_aci_letter(del_addr.aci_id)

        # --- Step 5: Look up customer info ---
        customer = self._lookup_utils.get_customer_info(customer_id)
        if not customer:
            raise OutputExecutionError(f"Failed to get customer info for ID {customer_id}")

        # --- Step 5b: Look up default agent for customer ---
        default_agent_id = self._lookup_utils.get_default_agent_id(customer_id)
        if default_agent_id is None:
            raise OutputExecutionError(
                f"No default agent configured for customer {customer_id} ({customer.name}). "
                "Please set a default agent in HTC before creating orders for this customer."
            )
        logger.debug(f"Found default agent {default_agent_id} for customer {customer_id}")

        # --- Step 6: Determine order type ---
        order_type = self._order_utils.determine_order_type(
            pu_aci=pu_aci_letter,
            pu_branch=pu_addr.branch_yn,
            pu_carrier=pu_addr.carrier_yn,
            del_aci=del_aci_letter,
            del_branch=del_addr.branch_yn,
            del_carrier=del_addr.carrier_yn,
        )
        logger.debug(f"Determined order type: {order_type}")

        # --- Step 7: Parse dates and times ---
        pu_date, pu_time_start_parsed = self._order_utils.parse_datetime_string(pickup_time_start)
        _, pu_time_end_parsed = self._order_utils.parse_datetime_string(pickup_time_end)
        del_date, del_time_start_parsed = self._order_utils.parse_datetime_string(delivery_time_start)
        _, del_time_end_parsed = self._order_utils.parse_datetime_string(delivery_time_end)

        # --- Step 8: Prepare all field values ---
        prepared_data = PreparedOrderData(
            # Order type
            order_type=order_type,

            # Direct input
            customer_id=customer_id,
            hawb=hawb or "",
            mawb=mawb or "",
            order_notes=order_notes or "",
            pu_date=pu_date,
            pu_time_start=pu_time_start_parsed,
            pu_time_end=pu_time_end_parsed,
            pu_address_id=pu_address_id,
            pu_notes=pickup_notes or "",
            del_date=del_date,
            del_time_start=del_time_start_parsed,
            del_time_end=del_time_end_parsed,
            del_address_id=del_address_id,
            del_notes=delivery_notes or "",

            # Customer lookup
            customer_name=customer.name,
            customer_assessorials=customer.assessorials,
            customer_tariff=customer.tariff,
            customer_qb_list_id=customer.qb_list_id,
            customer_qb_full_name=customer.qb_full_name,
            customer_agent_id=default_agent_id,

            # Pickup address lookup
            pu_company=pu_addr.company,
            pu_location=pu_addr.formatted_location,
            pu_zip=pu_addr.zip_code,
            pu_latitude=pu_addr.latitude,
            pu_longitude=pu_addr.longitude,
            pu_aci=pu_aci_letter,
            pu_assessorials=pu_addr.assessorials,
            pu_carrier_yn=pu_addr.carrier_yn,
            pu_carrier_ground_yn=pu_addr.carrier_ground_yn,
            pu_intl_yn=pu_addr.international_yn,
            pu_local_yn=pu_addr.local_yn,
            pu_branch_yn=pu_addr.branch_yn,

            # Delivery address lookup
            del_company=del_addr.company,
            del_location=del_addr.formatted_location,
            del_zip=del_addr.zip_code,
            del_latitude=del_addr.latitude,
            del_longitude=del_addr.longitude,
            del_aci=del_aci_letter,
            del_assessorials=del_addr.assessorials,
            del_carrier_yn=del_addr.carrier_yn,
            del_carrier_ground_yn=del_addr.carrier_ground_yn,
            del_intl_yn=del_addr.international_yn,
            del_local_yn=del_addr.local_yn,
            del_branch_yn=del_addr.branch_yn,
        )

        # ================================================================
        # PHASE 2: ORDER CREATION
        # ================================================================

        order_number = None

        try:
            # --- Step 9: Reserve order number (adds to OIW) ---
            order_number = self._order_utils.generate_next_order_number()
            logger.info(f"Reserved order number: {order_number}")

            # --- Step 10: Insert order record ---
            self._order_utils.create_order_record(order_number, prepared_data)

            # --- Step 10b: Create dims records if provided ---
            if dims:
                self._order_utils.create_dims_records(order_number, dims)

            # --- Step 11: Finalize on success ---
            # Update LON
            self._order_utils.update_lon(order_number)

            # Remove from OIW (release lock)
            self._order_utils.remove_from_orders_in_work(order_number)

            # Save HAWB association
            self._order_utils.save_hawb_association(
                hawb=hawb,
                customer_id=customer_id,
                order_number=order_number,
            )

            # Create order history
            self._order_utils.create_order_history(
                order_number=order_number,
                customer_id=customer_id,
                customer_name=customer.name,
                tariff=customer.tariff or "Standard",
                status="ETO Generated",
                status_seq=35,
            )

            logger.info(f"Successfully created HTC order {order_number}")
            return order_number

        except Exception as e:
            logger.error(f"Failed to create HTC order: {e}")
            # Note: OIW entry remains if we fail - will be skipped by next order number generation
            raise OutputExecutionError(f"Failed to create HTC order: {e}") from e

    def create_order_from_pending(self, pending_order: PendingOrder) -> float:
        """
        Create an HTC order from a pending order.

        This is a convenience wrapper around create_order() that extracts
        the necessary fields from a PendingOrder dataclass.

        Args:
            pending_order: The PendingOrder dataclass with all required fields

        Returns:
            The new HTC order number

        Raises:
            OutputExecutionError: If order creation fails
            ValueError: If required data is missing
        """
        import json

        logger.info(f"Creating HTC order from pending order {pending_order.id}")

        # Parse dims from JSON string if present
        dims_list = None
        if pending_order.dims:
            try:
                dims_list = json.loads(pending_order.dims)
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse dims JSON for pending order {pending_order.id}: {e}")

        return self.create_order(
            customer_id=pending_order.customer_id,
            hawb=pending_order.hawb,
            pickup_company_name=pending_order.pickup_company_name,
            pickup_address=pending_order.pickup_address,
            pickup_time_start=pending_order.pickup_time_start,
            pickup_time_end=pending_order.pickup_time_end,
            delivery_company_name=pending_order.delivery_company_name,
            delivery_address=pending_order.delivery_address,
            delivery_time_start=pending_order.delivery_time_start,
            delivery_time_end=pending_order.delivery_time_end,
            mawb=pending_order.mawb,
            pickup_notes=pending_order.pickup_notes,
            delivery_notes=pending_order.delivery_notes,
            order_notes=pending_order.order_notes,
            dims=dims_list,
        )

    # ==================== Order Update Orchestrator ====================

    def update_order(
        self,
        order_number: float,
        pickup_company_name: str | None = None,
        pickup_address: str | None = None,
        pickup_time_start: str | None = None,
        pickup_time_end: str | None = None,
        delivery_company_name: str | None = None,
        delivery_address: str | None = None,
        delivery_time_start: str | None = None,
        delivery_time_end: str | None = None,
        mawb: str | None = None,
        pickup_notes: str | None = None,
        delivery_notes: str | None = None,
        order_notes: str | None = None,
        dims: list[dict[str, Any]] | None = None,
        approver_username: str | None = None,
        old_values: dict[str, Any] | None = None,
        new_values: dict[str, Any] | None = None,
    ) -> list[str]:
        """
        Update an existing HTC order with new field values.

        This orchestrator handles the complexity of updating an order:
        - Address fields: Finds or creates the address, then updates all related columns
        - DateTime fields: Parses and splits into date + time components
        - Simple fields: Direct updates (notes, mawb)

        After updates, recalculates order type if addresses changed.

        Args:
            order_number: The HTC order number to update
            pickup_company_name: New pickup company name (required if pickup_address provided)
            pickup_address: New pickup address string
            pickup_time_start: New pickup start datetime (ISO format)
            pickup_time_end: New pickup end datetime (ISO format)
            delivery_company_name: New delivery company name (required if delivery_address provided)
            delivery_address: New delivery address string
            delivery_time_start: New delivery start datetime (ISO format)
            delivery_time_end: New delivery end datetime (ISO format)
            mawb: New MAWB value
            pickup_notes: New pickup notes
            delivery_notes: New delivery notes
            order_notes: New order notes
            dims: New dimensions list (replaces existing dims)
            approver_username: Staff_Login of user who approved (for audit trail)
            old_values: Dict of field_name -> old value (before update) for audit trail
            new_values: Dict of field_name -> new value (after update) for audit trail

        Returns:
            List of field names that were updated

        Raises:
            OutputExecutionError: If update fails
            ValueError: If address provided without company name
        """
        logger.info(f"Updating HTC order {order_number}")

        # ================================================================
        # UPPERCASE ALL STRING FIELDS FOR HTC DATABASE
        # ================================================================
        mawb = _uppercase_str(mawb)
        pickup_company_name = _uppercase_str(pickup_company_name)
        pickup_address = _uppercase_str(pickup_address)
        pickup_notes = _uppercase_str(pickup_notes)
        delivery_company_name = _uppercase_str(delivery_company_name)
        delivery_address = _uppercase_str(delivery_address)
        delivery_notes = _uppercase_str(delivery_notes)
        order_notes = _uppercase_str(order_notes)

        htc_updates: dict[str, Any] = {}
        updated_fields: list[str] = []
        address_changed = False

        # Track address info for order type recalculation
        pu_addr_info = None
        del_addr_info = None

        # ================================================================
        # PICKUP ADDRESS HANDLING
        # ================================================================
        if pickup_address is not None:
            if not pickup_company_name:
                raise ValueError("pickup_company_name is required when updating pickup_address")

            # Find or create the address
            pu_address_id = self._address_utils.find_or_create_address(
                address_string=pickup_address,
                company_name=pickup_company_name,
            )
            logger.debug(f"Resolved pickup address ID: {pu_address_id}")

            # Get full address info
            pu_addr_info = self._lookup_utils.get_address_info(pu_address_id)
            if not pu_addr_info:
                raise OutputExecutionError(f"Failed to get pickup address info for ID {pu_address_id}")

            pu_aci_letter = self._lookup_utils.get_aci_letter(pu_addr_info.aci_id)

            # Add all pickup address columns to update
            htc_updates["M_PUID"] = pu_address_id
            htc_updates["M_PUCo"] = pu_addr_info.company
            htc_updates["M_PULocn"] = pu_addr_info.formatted_location
            htc_updates["M_PUZip"] = pu_addr_info.zip_code
            htc_updates["M_PULatitude"] = pu_addr_info.latitude
            htc_updates["M_PULongitude"] = pu_addr_info.longitude
            htc_updates["M_PUACI"] = pu_aci_letter
            htc_updates["M_PUAssessorials"] = pu_addr_info.assessorials
            htc_updates["M_PUCarrierYN"] = pu_addr_info.carrier_yn
            htc_updates["M_PUCarrierGroundYN"] = pu_addr_info.carrier_ground_yn
            htc_updates["M_PUIntlYN"] = pu_addr_info.international_yn
            htc_updates["M_PULocalYN"] = pu_addr_info.local_yn
            htc_updates["M_PUBranchYN"] = pu_addr_info.branch_yn

            updated_fields.append("pickup_address")
            updated_fields.append("pickup_company_name")
            address_changed = True

        # ================================================================
        # DELIVERY ADDRESS HANDLING
        # ================================================================
        if delivery_address is not None:
            if not delivery_company_name:
                raise ValueError("delivery_company_name is required when updating delivery_address")

            # Find or create the address
            del_address_id = self._address_utils.find_or_create_address(
                address_string=delivery_address,
                company_name=delivery_company_name,
            )
            logger.debug(f"Resolved delivery address ID: {del_address_id}")

            # Get full address info
            del_addr_info = self._lookup_utils.get_address_info(del_address_id)
            if not del_addr_info:
                raise OutputExecutionError(f"Failed to get delivery address info for ID {del_address_id}")

            del_aci_letter = self._lookup_utils.get_aci_letter(del_addr_info.aci_id)

            # Add all delivery address columns to update
            htc_updates["M_DelID"] = del_address_id
            htc_updates["M_DelCo"] = del_addr_info.company
            htc_updates["M_DelLocn"] = del_addr_info.formatted_location
            htc_updates["M_DelZip"] = del_addr_info.zip_code
            htc_updates["M_DelLatitude"] = del_addr_info.latitude
            htc_updates["M_DelLongitude"] = del_addr_info.longitude
            htc_updates["M_DelACI"] = del_aci_letter
            htc_updates["M_Del_Assessorials"] = del_addr_info.assessorials
            htc_updates["M_DelCarrierYN"] = del_addr_info.carrier_yn
            htc_updates["M_DelCarrierGroundYN"] = del_addr_info.carrier_ground_yn
            htc_updates["M_DelIntlYN"] = del_addr_info.international_yn
            htc_updates["M_DelLocalYN"] = del_addr_info.local_yn
            htc_updates["M_DelBranchYN"] = del_addr_info.branch_yn

            updated_fields.append("delivery_address")
            updated_fields.append("delivery_company_name")
            address_changed = True

        # ================================================================
        # PICKUP DATETIME HANDLING
        # ================================================================
        if pickup_time_start is not None:
            pu_date, pu_time_start_parsed = self._order_utils.parse_datetime_string(pickup_time_start)
            htc_updates["M_PUDate"] = pu_date
            htc_updates["M_PUTimeStart"] = pu_time_start_parsed
            updated_fields.append("pickup_time_start")

        if pickup_time_end is not None:
            _, pu_time_end_parsed = self._order_utils.parse_datetime_string(pickup_time_end)
            htc_updates["M_PUTimeEnd"] = pu_time_end_parsed
            updated_fields.append("pickup_time_end")

        # ================================================================
        # DELIVERY DATETIME HANDLING
        # ================================================================
        if delivery_time_start is not None:
            del_date, del_time_start_parsed = self._order_utils.parse_datetime_string(delivery_time_start)
            htc_updates["M_DelDate"] = del_date
            htc_updates["M_DelTimeStart"] = del_time_start_parsed
            updated_fields.append("delivery_time_start")

        if delivery_time_end is not None:
            _, del_time_end_parsed = self._order_utils.parse_datetime_string(delivery_time_end)
            htc_updates["M_DelTimeEnd"] = del_time_end_parsed
            updated_fields.append("delivery_time_end")

        # ================================================================
        # SIMPLE FIELD HANDLING
        # ================================================================
        if mawb is not None:
            htc_updates["M_MAWB"] = mawb
            updated_fields.append("mawb")

        if pickup_notes is not None:
            htc_updates["M_PUNotes"] = pickup_notes
            updated_fields.append("pickup_notes")

        if delivery_notes is not None:
            htc_updates["M_DelNotes"] = delivery_notes
            updated_fields.append("delivery_notes")

        if order_notes is not None:
            htc_updates["M_OrderNotes"] = order_notes
            updated_fields.append("order_notes")

        # ================================================================
        # DIMENSIONS HANDLING (replace strategy)
        # ================================================================
        if dims is not None:
            self._order_utils.replace_dims_records(order_number, dims)
            updated_fields.append("dims")

        # ================================================================
        # ORDER TYPE RECALCULATION (if address changed)
        # ================================================================
        if address_changed:
            # We need both pickup and delivery info to recalculate
            # If only one changed, fetch the other from the existing order
            if pu_addr_info is None:
                # Fetch existing pickup address from order
                existing_pu_id = self._lookup_utils.get_order_address_id(order_number, is_pickup=True)
                if existing_pu_id:
                    pu_addr_info = self._lookup_utils.get_address_info(existing_pu_id)

            if del_addr_info is None:
                # Fetch existing delivery address from order
                existing_del_id = self._lookup_utils.get_order_address_id(order_number, is_pickup=False)
                if existing_del_id:
                    del_addr_info = self._lookup_utils.get_address_info(existing_del_id)

            if pu_addr_info and del_addr_info:
                pu_aci_letter = self._lookup_utils.get_aci_letter(pu_addr_info.aci_id)
                del_aci_letter = self._lookup_utils.get_aci_letter(del_addr_info.aci_id)

                new_order_type = self._order_utils.determine_order_type(
                    pu_aci=pu_aci_letter,
                    pu_branch=pu_addr_info.branch_yn,
                    pu_carrier=pu_addr_info.carrier_yn,
                    del_aci=del_aci_letter,
                    del_branch=del_addr_info.branch_yn,
                    del_carrier=del_addr_info.carrier_yn,
                )
                htc_updates["M_OrderType"] = new_order_type
                logger.debug(f"Recalculated order type: {new_order_type}")

        # ================================================================
        # EXECUTE UPDATES
        # ================================================================
        if htc_updates:
            self._order_utils.update_order_fields(order_number, htc_updates)

        # ================================================================
        # CREATE UPDATE HISTORY
        # ================================================================
        if updated_fields:
            # Build detailed change description with old->new values
            self._order_utils.create_update_history(
                order_number=order_number,
                updated_fields=updated_fields,
                old_values=old_values or {},
                new_values=new_values or {},
                user_lid=approver_username,
            )

        logger.info(f"Successfully updated HTC order {order_number}: {updated_fields}")
        return updated_fields

    # ==================== Attachment Processing ====================

    def process_attachments(
        self,
        order_number: float,
        customer_id: int,
        hawb: str,
        pdf_sources: list[PdfSource],
    ) -> list[AttachmentResult]:
        """
        Process PDF attachments for an HTC order.

        Copies PDF files from ETO storage to HTC attachment storage and
        creates records in the HTC attachments table.

        Args:
            order_number: The HTC order number
            customer_id: Customer ID
            hawb: HAWB identifier (used in attachment filename)
            pdf_sources: List of PdfSource objects with PDF file info

        Returns:
            List of AttachmentResult for each processed attachment

        Note:
            If HTC_APPS_DIR is not configured, returns an empty list
            and logs a warning (attachment processing disabled).
        """
        if not self._attachment_manager:
            logger.warning(
                f"Skipping attachment processing for order {order_number}: "
                "HTC_APPS_DIR not configured"
            )
            return []

        if not pdf_sources:
            logger.debug(f"No PDF sources provided for order {order_number}")
            return []

        logger.info(
            f"Processing {len(pdf_sources)} attachment(s) for order {order_number} "
            f"(customer {customer_id}, HAWB {hawb})"
        )

        try:
            results = self._attachment_manager.process_attachments_for_order(
                order_number=order_number,
                customer_id=customer_id,
                hawb=hawb,
                pdf_sources=pdf_sources,
            )

            successful = sum(1 for r in results if r.success)
            if successful > 0:
                logger.info(
                    f"Successfully processed {successful}/{len(results)} attachments "
                    f"for order {order_number}"
                )

            return results

        except Exception as e:
            logger.error(f"Failed to process attachments for order {order_number}: {e}")
            return []

    def get_attachment_count(
        self,
        order_number: float,
    ) -> int:
        """
        Get the number of attachments for an order.

        Args:
            order_number: The HTC order number

        Returns:
            Number of attachments (0 if none or on error)
        """
        try:
            connection = self._get_connection()
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT COUNT(*) FROM [HTC300_G040_T014A Open Order Attachments]
                    WHERE [Att_CoID] = ? AND [Att_BrID] = ? AND [Att_OrderNo] = ?
                """, (self.CO_ID, self.BR_ID, order_number))
                result = cursor.fetchone()
                return result[0] if result else 0
        except Exception as e:
            logger.error(f"Failed to get attachment count for order {order_number}: {e}")
            return 0
