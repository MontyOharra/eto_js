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

from typing import Any, Optional, TYPE_CHECKING

from shared.logging import get_logger
from shared.exceptions import OutputExecutionError
from shared.database.repositories.pending_order import PendingOrderRepository

from features.htc_integration.lookup_utils import (
    HtcLookupUtils,
    HtcOrderDetails,
    HtcOrderFields,
    AddressInfo,
    CustomerInfo,
)
from features.htc_integration.address_utils import HtcAddressUtils
from features.htc_integration.order_utils import HtcOrderUtils, PreparedOrderData
from features.htc_integration.htc_order_worker import HtcOrderWorker

if TYPE_CHECKING:
    from shared.database.data_database_manager import DataDatabaseManager
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
]


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
        data_database_manager: 'DataDatabaseManager',
        connection_manager: Any = None,
        database_name: str = "htc_300_db",
        worker_enabled: bool = True,
        worker_polling_interval: int = 5,
        worker_max_concurrent: int = 5,
    ) -> None:
        """
        Initialize the service.

        Args:
            data_database_manager: DataDatabaseManager for HTC database access
            connection_manager: Database connection manager for pending order repo
            database_name: Name of the database containing HTC tables
            worker_enabled: Whether to enable the HTC order worker
            worker_polling_interval: Seconds between worker polling cycles
            worker_max_concurrent: Maximum concurrent orders to process
        """
        logger.debug("Initializing HtcIntegrationService...")

        self._data_database_manager = data_database_manager
        self._database_name = database_name
        self._pending_order_repo = PendingOrderRepository(connection_manager=connection_manager) if connection_manager else None

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

        # Initialize HTC order worker (only if pending_order_repo is available)
        if self._pending_order_repo:
            self._worker = HtcOrderWorker(
                get_ready_pending_orders_callback=self.get_ready_pending_orders,
                create_htc_order_callback=self.create_htc_order_by_id,
                mark_processing_callback=self.mark_pending_order_processing,
                mark_created_callback=self.mark_pending_order_created,
                mark_failed_callback=self.mark_pending_order_failed,
                enabled=worker_enabled,
                max_concurrent=worker_max_concurrent,
                polling_interval=worker_polling_interval,
            )
        else:
            self._worker = None
            if worker_enabled:
                logger.warning("HTC order worker disabled: connection_manager not provided")

        logger.info("HtcIntegrationService initialized successfully")

    def _get_connection(self) -> Any:
        """Get the HTC database connection."""
        return self._data_database_manager.get_connection(self._database_name)

    # ==================== Worker Lifecycle ====================

    async def startup(self) -> bool:
        """
        Start the HTC order worker background process.

        Returns:
            True if worker started successfully, False otherwise
        """
        if not self._worker:
            logger.warning("HTC order worker not available (no connection_manager)")
            return False
        return await self._worker.startup()

    async def shutdown(self, graceful: bool = True) -> bool:
        """
        Stop the HTC order worker background process.

        Args:
            graceful: If True, wait for current batch to complete

        Returns:
            True if worker stopped successfully
        """
        if not self._worker:
            return False
        return await self._worker.shutdown(graceful=graceful)

    def get_worker_status(self) -> dict:
        """Get the current status of the HTC order worker."""
        if not self._worker:
            return {"enabled": False, "running": False, "error": "Worker not initialized"}
        return self._worker.get_status()

    # ==================== Lookup Operations ====================
    # Delegated to HtcLookupUtils

    def lookup_order_by_customer_and_hawb(
        self,
        customer_id: int,
        hawb: str,
    ) -> Optional[float]:
        """
        Check if an order exists in HTC Open Orders for a customer/HAWB pair.

        Args:
            customer_id: The customer ID to look up
            hawb: The HAWB string to look up

        Returns:
            The HTC order number (float) if found, None if not found
        """
        return self._lookup_utils.lookup_order_by_customer_and_hawb(customer_id, hawb)

    def get_customer_name(self, customer_id: int) -> Optional[str]:
        """
        Look up customer name by customer ID.

        Args:
            customer_id: The customer ID to look up

        Returns:
            Customer name string if found, None if not found
        """
        return self._lookup_utils.get_customer_name(customer_id)

    def get_customer_info(self, customer_id: int) -> Optional[CustomerInfo]:
        """
        Get full customer information for order creation.

        Args:
            customer_id: The customer ID to look up

        Returns:
            CustomerInfo dataclass if found, None if not found
        """
        return self._lookup_utils.get_customer_info(customer_id)

    def get_address_info(self, address_id: float) -> Optional[AddressInfo]:
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

    def get_order_details(self, order_number: float) -> Optional[HtcOrderDetails]:
        """
        Get details of an HTC order by order number.

        Args:
            order_number: The HTC order number

        Returns:
            HtcOrderDetails if found, None if not found
        """
        return self._lookup_utils.get_order_details(order_number)

    def get_order_fields(self, order_number: float) -> Optional[HtcOrderFields]:
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

    def find_address_id(self, address_string: str) -> Optional[float]:
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

    def update_order(self, order_number: float, updates: dict) -> None:
        """
        Update an existing order in HTC.

        Args:
            order_number: The HTC order number to update
            updates: Dict of field_name -> new_value

        Raises:
            OutputExecutionError: If update fails
        """
        self._order_utils.update_order(order_number, updates)

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
        mawb: Optional[str] = None,
        pickup_notes: Optional[str] = None,
        delivery_notes: Optional[str] = None,
        order_notes: Optional[str] = None,
        pieces: Optional[int] = None,
        weight: Optional[float] = None,
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
            9. Insert dimension record
            10. On success: update LON, remove from OIW, save HAWB, create history

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
            pieces: Optional piece count (defaults to 1)
            weight: Optional weight (defaults to 0.0)

        Returns:
            The new HTC order number

        Raises:
            OutputExecutionError: If order creation fails
            ValueError: If required data is missing
        """
        logger.info(f"Creating HTC order for customer {customer_id}, HAWB: {hawb}")

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

            # --- Step 11: Insert dimension record ---
            self._order_utils.create_dimension_record(
                order_number=order_number,
                pieces=pieces or 1,
                weight=weight or 0.0,
            )

            # --- Step 12: Finalize on success ---
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

    def create_order_from_pending(self, pending_order: 'PendingOrder') -> float:
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
        logger.info(f"Creating HTC order from pending order {pending_order.id}")

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
            pieces=pending_order.pieces,
            weight=pending_order.weight,
        )

    # ==================== Worker Callback Methods ====================
    # These methods are used by HtcOrderWorker to process pending orders

    def get_ready_pending_orders(self, limit: int) -> list:
        """
        Get pending orders with status='ready' for worker processing.

        Args:
            limit: Maximum number of orders to return

        Returns:
            List of PendingOrder dataclasses
        """
        return self._pending_order_repo.get_ready(limit=limit)

    def mark_pending_order_processing(self, pending_order_id: int) -> None:
        """
        Mark a pending order as 'processing' (being created in HTC).

        Args:
            pending_order_id: ID of the pending order
        """
        self._pending_order_repo.update(pending_order_id, {
            "status": "processing",
            "error_message": None,
            "error_at": None,
        })
        logger.info(f"Pending order {pending_order_id} marked as processing")

    def mark_pending_order_created(self, pending_order_id: int, htc_order_number: float) -> None:
        """
        Mark a pending order as 'created' after successful HTC creation.

        Args:
            pending_order_id: ID of the pending order
            htc_order_number: The HTC order number that was created
        """
        from datetime import datetime, timezone
        self._pending_order_repo.update(pending_order_id, {
            "status": "created",
            "htc_order_number": htc_order_number,
            "htc_created_at": datetime.now(timezone.utc),
            "error_message": None,
            "error_at": None,
        })
        logger.info(f"Pending order {pending_order_id} marked as created (HTC order {htc_order_number})")

    def mark_pending_order_failed(self, pending_order_id: int, error_message: str) -> None:
        """
        Mark a pending order as 'failed' after HTC creation failure.

        Args:
            pending_order_id: ID of the pending order
            error_message: The error message describing the failure
        """
        from datetime import datetime, timezone
        self._pending_order_repo.update(pending_order_id, {
            "status": "failed",
            "error_message": error_message,
            "error_at": datetime.now(timezone.utc),
        })
        logger.error(f"Pending order {pending_order_id} marked as failed: {error_message}")

    def create_htc_order_by_id(self, pending_order_id: int) -> float:
        """
        Create an HTC order from a pending order by ID.

        Used by the worker to create orders. First fetches the pending order,
        then calls create_order_from_pending.

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

        return self.create_order_from_pending(pending_order)

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
        })
        logger.info(f"Pending order {pending_order_id} reset to 'ready' for retry")
        return True
