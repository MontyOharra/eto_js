"""
Order Helpers

Helper utilities for order operations using the Access database.
Used by output definitions to perform order-related database operations.
"""

import threading
from datetime import datetime
from typing import Any

from shared.logging import get_logger
from shared.exceptions import OutputExecutionError

logger = get_logger(__name__)


class OrderHelpers:
    """
    Helper utilities for order operations.

    Provides database operations for order management using the Access database
    connection. Used by output definitions to perform order-related operations.

    Thread Safety:
        Uses a class-level lock for order number generation to prevent race
        conditions when multiple worker threads attempt to generate order
        numbers simultaneously. This is necessary because:
        1. pyodbc connections are not thread-safe (threadsafety=1)
        2. Order number generation must be atomic (read-increment-write)
    """

    # Hardcoded values (always 1, 1 for local system - matches VBA legacy)
    CO_ID = 1
    BR_ID = 1

    # Class-level lock for thread-safe order number generation
    # Shared across all instances to serialize Access database operations
    _order_number_lock = threading.Lock()

    def __init__(self, data_database_manager: Any, database_name: str = "htc_300_db"):
        """
        Initialize order helpers.

        Args:
            data_database_manager: DataDatabaseManager instance for database access
            database_name: Name of the database containing order tables
        """
        self._data_database_manager = data_database_manager
        self._database_name = database_name

    def _get_connection(self) -> Any:
        """Get the database connection."""
        return self._data_database_manager.get_connection(self._database_name)

    def generate_next_order_number(self) -> float:
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
            This method uses a class-level lock to ensure only one thread
            can generate an order number at a time. This prevents:
            - pyodbc cursor conflicts (HY010 Function sequence error)
            - Race conditions leading to duplicate order numbers

        Returns:
            New order number as float (matches VBA Double type)

        Raises:
            OutputExecutionError: If database operations fail
        """
        # Acquire lock to ensure thread-safe access to the Access database
        # This serializes order number generation across all worker threads
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
                            # Order number already in work, increment and try again
                            new_order_no += 1
                            oiw_found = True
                        else:
                            # Order number not in work, we can use it
                            oiw_found = False

                # Step 3: Update LON table and add to OIW in a single transaction
                with connection.cursor() as cursor:
                    # Update LON table with new order number
                    cursor.execute("""
                        UPDATE [HTC300_G040_T000 Last OrderNo Assigned]
                        SET [lon_orderno] = ?
                        WHERE [lon_coid] = ? AND [lon_brid] = ?
                    """, (new_order_no, self.CO_ID, self.BR_ID))

                    # Add new order to OIW table
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
