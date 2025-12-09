"""
HTC Integration Service

Centralized service for all HTC Access database operations.
Provides order lookup, creation, and update functionality.

This is the single point of access for HTC database operations.
All other services should use this service rather than accessing
the HTC database directly.

Thread Safety:
    Uses class-level locks for operations that require atomic
    read-modify-write sequences (e.g., order number generation).
    This is necessary because pyodbc connections are not thread-safe.
"""

import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional, TYPE_CHECKING

from shared.logging import get_logger
from shared.exceptions import OutputExecutionError

if TYPE_CHECKING:
    from shared.database.data_database_manager import DataDatabaseManager
    from shared.types.pending_orders import PendingOrder

logger = get_logger(__name__)


# ==================== Result Types ====================

@dataclass
class HtcOrderDetails:
    """Details of an HTC order."""
    order_number: float
    customer_id: int
    hawb: str
    mawb: Optional[str]
    status: Optional[str]
    # Add more fields as needed


@dataclass
class HtcOrderCreate:
    """Data required to create an order in HTC."""
    customer_id: int
    hawb: str
    mawb: Optional[str] = None
    pickup_address: Optional[str] = None
    pickup_time_start: Optional[datetime] = None
    pickup_time_end: Optional[datetime] = None
    pickup_notes: Optional[str] = None
    delivery_address: Optional[str] = None
    delivery_time_start: Optional[datetime] = None
    delivery_time_end: Optional[datetime] = None
    delivery_notes: Optional[str] = None
    pieces: Optional[int] = None
    weight: Optional[float] = None
    order_notes: Optional[str] = None


# ==================== Service ====================

class HtcIntegrationService:
    """
    Centralized service for HTC Access database operations.

    Provides:
    - Order lookup by customer/HAWB
    - Order creation with automatic order number generation
    - Order updates
    - Order detail retrieval

    All HTC database operations should go through this service
    to ensure consistency and proper connection management.
    """

    # Hardcoded values (always 1, 1 for local system - matches VBA legacy)
    CO_ID = 1
    BR_ID = 1

    # Class-level lock for thread-safe order number generation
    _order_number_lock = threading.Lock()

    def __init__(
        self,
        data_database_manager: 'DataDatabaseManager',
        database_name: str = "htc_300_db",
    ) -> None:
        """
        Initialize the service.

        Args:
            data_database_manager: DataDatabaseManager for HTC database access
            database_name: Name of the database containing HTC tables
        """
        logger.debug("Initializing HtcIntegrationService...")

        self._data_database_manager = data_database_manager
        self._database_name = database_name

        logger.info("HtcIntegrationService initialized successfully")

    def _get_connection(self) -> Any:
        """Get the HTC database connection."""
        return self._data_database_manager.get_connection(self._database_name)

    # ==================== Lookup Operations ====================

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
        connection = self._get_connection()

        try:
            with connection.cursor() as cursor:
                query = """
                    SELECT [M_OrderNo]
                    FROM [HTC300_G040_T010A Open Orders]
                    WHERE [M_CustomerID] = ?
                      AND [M_HAWB] = ?
                      AND [M_CoID] = ?
                      AND [M_BrID] = ?
                """
                cursor.execute(query, (customer_id, hawb, self.CO_ID, self.BR_ID))
                row = cursor.fetchone()

                if row is None:
                    logger.debug(f"No order found for customer {customer_id}, HAWB {hawb}")
                    return None

                order_no = float(row[0]) if row[0] is not None else None
                logger.debug(f"Found order {order_no} for customer {customer_id}, HAWB {hawb}")
                return order_no

        except Exception as e:
            logger.error(f"Failed to lookup order for customer {customer_id}, HAWB {hawb}: {e}")
            raise

    def get_order_details(self, order_number: float) -> Optional[HtcOrderDetails]:
        """
        Get details of an HTC order by order number.

        Args:
            order_number: The HTC order number

        Returns:
            HtcOrderDetails if found, None if not found
        """
        connection = self._get_connection()

        try:
            with connection.cursor() as cursor:
                query = """
                    SELECT [M_OrderNo], [M_CustomerID], [M_HAWB], [M_MAWB]
                    FROM [HTC300_G040_T010A Open Orders]
                    WHERE [M_OrderNo] = ?
                      AND [M_CoID] = ?
                      AND [M_BrID] = ?
                """
                cursor.execute(query, (order_number, self.CO_ID, self.BR_ID))
                row = cursor.fetchone()

                if row is None:
                    logger.debug(f"Order {order_number} not found")
                    return None

                return HtcOrderDetails(
                    order_number=float(row[0]),
                    customer_id=int(row[1]),
                    hawb=str(row[2]) if row[2] else "",
                    mawb=str(row[3]) if row[3] else None,
                    status=None,  # TODO: Determine status field
                )

        except Exception as e:
            logger.error(f"Failed to get order details for {order_number}: {e}")
            raise

    # ==================== Order Creation ====================

    def create_order(self, order_data: Dict[str, Any]) -> float:
        """
        Create a new order in HTC.

        Generates a new order number and inserts the order into
        the Open Orders table.

        Args:
            order_data: Dict with order fields (customer_id, hawb, etc.)

        Returns:
            The new HTC order number

        Raises:
            OutputExecutionError: If order creation fails
        """
        logger.info(f"Creating HTC order for customer {order_data.get('customer_id')}, HAWB {order_data.get('hawb')}")

        # Generate order number (thread-safe)
        order_number = self._generate_next_order_number()

        connection = self._get_connection()

        try:
            with connection.cursor() as cursor:
                # Build INSERT query
                # TODO: Map order_data fields to actual HTC column names
                query = """
                    INSERT INTO [HTC300_G040_T010A Open Orders]
                    ([M_CoID], [M_BrID], [M_OrderNo], [M_CustomerID], [M_HAWB], [M_MAWB])
                    VALUES (?, ?, ?, ?, ?, ?)
                """
                cursor.execute(query, (
                    self.CO_ID,
                    self.BR_ID,
                    order_number,
                    order_data.get("customer_id"),
                    order_data.get("hawb"),
                    order_data.get("mawb"),
                ))

            logger.info(f"Created HTC order {order_number}")
            return order_number

        except Exception as e:
            logger.error(f"Failed to create HTC order: {e}")
            raise OutputExecutionError(f"Failed to create HTC order: {e}") from e

    def _generate_next_order_number(self) -> float:
        """
        Generate the next available order number.

        Replicates legacy VBA NextOrderNo function:
        1. Read last assigned order number from LON table
        2. Increment by 1 to get candidate
        3. Check Orders In Work (OIW) table for conflicts
        4. If conflict found, increment and repeat check
        5. Add new order to OIW table
        6. Update LON table with new order number
        7. Return the new order number

        Thread Safety:
            Uses a class-level lock to ensure only one thread
            can generate an order number at a time.

        Returns:
            New order number as float (matches VBA Double type)

        Raises:
            OutputExecutionError: If database operations fail
        """
        with self._order_number_lock:
            connection = self._get_connection()

            try:
                # Step 1: Get last order number assigned (LON)
                with connection.cursor() as cursor:
                    lon_query = """
                        SELECT [lon_orderno]
                        FROM [HTC300_G040_T000 Last OrderNo Assigned]
                        WHERE [lon_coid] = ? AND [lon_brid] = ?
                    """
                    cursor.execute(lon_query, (self.CO_ID, self.BR_ID))
                    lon_row = cursor.fetchone()

                    if lon_row is None:
                        # First order ever - initialize LON table
                        cursor.execute("""
                            INSERT INTO [HTC300_G040_T000 Last OrderNo Assigned]
                            ([lon_coid], [lon_brid], [lon_orderno])
                            VALUES (?, ?, ?)
                        """, (self.CO_ID, self.BR_ID, 1))
                        new_order_no = 1.0
                    else:
                        # Increment last order number
                        new_order_no = float(lon_row[0]) + 1

                # Step 2: Check Orders In Work (OIW) and find unused number
                oiw_found = True
                while oiw_found:
                    with connection.cursor() as cursor:
                        oiw_query = """
                            SELECT [oiw_coid], [oiw_brid], [oiw_orderno]
                            FROM [HTC300_G040_T005 Orders In Work]
                            WHERE [oiw_coid] = ? AND [oiw_brid] = ? AND [oiw_orderno] = ?
                        """
                        cursor.execute(oiw_query, (self.CO_ID, self.BR_ID, new_order_no))
                        oiw_row = cursor.fetchone()

                        if oiw_row is not None:
                            new_order_no += 1
                            oiw_found = True
                        else:
                            oiw_found = False

                # Step 3: Update LON table and add to OIW
                with connection.cursor() as cursor:
                    cursor.execute("""
                        UPDATE [HTC300_G040_T000 Last OrderNo Assigned]
                        SET [lon_orderno] = ?
                        WHERE [lon_coid] = ? AND [lon_brid] = ?
                    """, (new_order_no, self.CO_ID, self.BR_ID))

                    current_time = datetime.now()
                    current_user = "ETO_SYSTEM"

                    cursor.execute("""
                        INSERT INTO [HTC300_G040_T005 Orders In Work]
                        ([oiw_coid], [oiw_brid], [oiw_orderno], [oiw_when], [oiw_user])
                        VALUES (?, ?, ?, ?, ?)
                    """, (self.CO_ID, self.BR_ID, new_order_no, current_time, current_user))

                logger.info(f"Generated next order number: {new_order_no}")
                return new_order_no

            except Exception as e:
                logger.error(f"Failed to generate next order number: {e}")
                raise OutputExecutionError(f"Failed to generate next order number: {e}") from e

    # ==================== Order Updates ====================

    def update_order(self, order_number: float, updates: Dict[str, Any]) -> None:
        """
        Update an existing order in HTC.

        Args:
            order_number: The HTC order number to update
            updates: Dict of field_name -> new_value

        Raises:
            OutputExecutionError: If update fails
        """
        logger.info(f"Updating HTC order {order_number} with {len(updates)} fields")

        if not updates:
            logger.warning(f"No updates provided for order {order_number}")
            return

        connection = self._get_connection()

        try:
            # Build UPDATE query dynamically
            # TODO: Map field names to actual HTC column names
            field_mapping = {
                "hawb": "M_HAWB",
                "mawb": "M_MAWB",
                # Add more field mappings as needed
            }

            set_clauses = []
            values = []

            for field_name, value in updates.items():
                htc_column = field_mapping.get(field_name)
                if htc_column:
                    set_clauses.append(f"[{htc_column}] = ?")
                    values.append(value)
                else:
                    logger.warning(f"Unknown field '{field_name}' - skipping")

            if not set_clauses:
                logger.warning(f"No valid fields to update for order {order_number}")
                return

            # Add WHERE clause values
            values.extend([order_number, self.CO_ID, self.BR_ID])

            query = f"""
                UPDATE [HTC300_G040_T010A Open Orders]
                SET {', '.join(set_clauses)}
                WHERE [M_OrderNo] = ? AND [M_CoID] = ? AND [M_BrID] = ?
            """

            with connection.cursor() as cursor:
                cursor.execute(query, values)

            logger.info(f"Updated HTC order {order_number}")

        except Exception as e:
            logger.error(f"Failed to update HTC order {order_number}: {e}")
            raise OutputExecutionError(f"Failed to update HTC order: {e}") from e

    # ==================== Order Deletion ====================

    def create_order_from_pending(self, pending_order: 'PendingOrder') -> float:
        """
        Create an HTC order from a pending order.

        TEMPORARY DUMMY IMPLEMENTATION: Just prints the data and returns a dummy order number.
        Will be replaced with actual HTC creation logic later.

        Args:
            pending_order: The PendingOrder dataclass with all required fields

        Returns:
            The new HTC order number (currently a dummy value)
        """
        logger.info("=" * 60)
        logger.info("HTC ORDER CREATION (DUMMY)")
        logger.info("=" * 60)
        logger.info(f"Pending Order ID: {pending_order.id}")
        logger.info(f"Customer ID: {pending_order.customer_id}")
        logger.info(f"HAWB: {pending_order.hawb}")
        logger.info("-" * 40)
        logger.info("REQUIRED FIELDS:")
        logger.info(f"  Pickup Address: {pending_order.pickup_address}")
        logger.info(f"  Pickup Time Start: {pending_order.pickup_time_start}")
        logger.info(f"  Pickup Time End: {pending_order.pickup_time_end}")
        logger.info(f"  Delivery Address: {pending_order.delivery_address}")
        logger.info(f"  Delivery Time Start: {pending_order.delivery_time_start}")
        logger.info(f"  Delivery Time End: {pending_order.delivery_time_end}")
        logger.info("-" * 40)
        logger.info("OPTIONAL FIELDS:")
        logger.info(f"  MAWB: {pending_order.mawb}")
        logger.info(f"  Pickup Notes: {pending_order.pickup_notes}")
        logger.info(f"  Delivery Notes: {pending_order.delivery_notes}")
        logger.info(f"  Order Notes: {pending_order.order_notes}")
        logger.info(f"  Pieces: {pending_order.pieces}")
        logger.info(f"  Weight: {pending_order.weight}")
        logger.info("=" * 60)

        # TODO: Replace with actual HTC create_order call
        # For now, return a dummy order number
        dummy_order_number = 99999.0
        logger.info(f"DUMMY: Would create HTC order, returning dummy order number: {dummy_order_number}")

        return dummy_order_number

    def remove_from_orders_in_work(self, order_number: float) -> None:
        """
        Remove an order from the Orders In Work table.

        Called after an order is completed/closed.

        Args:
            order_number: The HTC order number to remove
        """
        logger.info(f"Removing order {order_number} from Orders In Work")

        connection = self._get_connection()

        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    DELETE FROM [HTC300_G040_T005 Orders In Work]
                    WHERE [oiw_coid] = ? AND [oiw_brid] = ? AND [oiw_orderno] = ?
                """, (self.CO_ID, self.BR_ID, order_number))

            logger.info(f"Removed order {order_number} from Orders In Work")

        except Exception as e:
            logger.error(f"Failed to remove order {order_number} from OIW: {e}")
            raise
