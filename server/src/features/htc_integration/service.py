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
class AddressInfo:
    """Full address information for order creation."""
    fav_id: float
    company: str              # FavCompany → M_PUCo / M_DelCo
    locn_name: str            # FavLocnName
    addr_ln1: str             # FavAddrLn1
    addr_ln2: str             # FavAddrLn2
    city: str                 # FavCity
    state: str                # FavState
    zip_code: str             # FavZip → M_PUZip / M_DelZip
    country: str              # FavCountry
    latitude: str             # FavLatitude → M_PULatitude
    longitude: str            # FavLongitude → M_PULongitude
    aci_id: int               # FavACIID (convert to letter via get_aci_letter)
    assessorials: str         # FavAssessorials → M_PUAssessorials
    carrier_yn: bool          # FavCarrierYN → M_PUCarrierYN
    carrier_ground_yn: bool   # FavCarrierGroundYN → M_PUCarrierGroundYN
    international_yn: bool    # FavInternational → M_PUIntlYN
    local_yn: bool            # FavLocalYN → M_PULocalYN
    branch_yn: bool           # FavBranchAddressYN → M_PUBranchYN

    @property
    def formatted_location(self) -> str:
        """
        Format location string for M_PULocn / M_DelLocn.
        Format: '{AddrLn1}, {AddrLn2}, {City}, {State}, {Country}'
        If AddrLn2 is empty, omit it.
        """
        parts = [self.addr_ln1]
        if self.addr_ln2:
            parts.append(self.addr_ln2)
        parts.extend([self.city, self.state, self.country])
        return ', '.join(parts)


@dataclass
class CustomerInfo:
    """Customer information for order creation."""
    customer_id: int
    name: str                 # Customer → m_Customer
    assessorials: str         # Cus_Assessorials → M_CustAssessorials
    tariff: str               # Cus_Tariff → M_Tariff
    qb_list_id: str           # Cus_QBCustomerRefListID → M_QBCustomerListID
    qb_full_name: str         # Cus_QBCustomerRefFullName → M_QBCustFullName


@dataclass
class HtcOrderCreate:
    """Data required to create an order in HTC."""
    customer_id: int
    hawb: str
    mawb: Optional[str] = None


@dataclass
class PreparedOrderData:
    """
    All data needed to INSERT an order into HTC300_G040_T010A Open Orders.

    This dataclass is populated during Phase 1 (data gathering) of order creation,
    then passed to _create_order_record() in Phase 2.
    """
    # === System Generated ===
    order_type: int                    # 1-11, from determine_order_type()

    # === Direct Input (from pending order) ===
    customer_id: int
    hawb: str
    mawb: str
    order_notes: str
    pu_date: str                       # MM/DD/YYYY format
    pu_time_start: str                 # HH:MM format
    pu_time_end: str                   # HH:MM format
    pu_address_id: float               # FavID
    pu_notes: str
    del_date: str                      # MM/DD/YYYY format
    del_time_start: str                # HH:MM format
    del_time_end: str                  # HH:MM format
    del_address_id: float              # FavID
    del_notes: str

    # === Customer Lookup ===
    customer_name: str
    customer_assessorials: str
    customer_tariff: str
    customer_qb_list_id: str
    customer_qb_full_name: str

    # === Pickup Address Lookup ===
    pu_company: str
    pu_location: str                   # Formatted: "AddrLn1, City, State, Country"
    pu_zip: str
    pu_latitude: str
    pu_longitude: str
    pu_aci: str                        # Single letter (A, B, C, D)
    pu_assessorials: str
    pu_carrier_yn: bool
    pu_carrier_ground_yn: bool
    pu_intl_yn: bool
    pu_local_yn: bool
    pu_branch_yn: bool

    # === Delivery Address Lookup ===
    del_company: str
    del_location: str                  # Formatted: "AddrLn1, City, State, Country"
    del_zip: str
    del_latitude: str
    del_longitude: str
    del_aci: str                       # Single letter (A, B, C, D)
    del_assessorials: str
    del_carrier_yn: bool
    del_carrier_ground_yn: bool
    del_intl_yn: bool
    del_local_yn: bool
    del_branch_yn: bool


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

    def get_customer_name(self, customer_id: int) -> Optional[str]:
        """
        Look up customer name by customer ID.

        Args:
            customer_id: The customer ID to look up

        Returns:
            Customer name string if found, None if not found
        """
        connection = self._get_connection()

        try:
            with connection.cursor() as cursor:
                query = """
                    SELECT [Customer]
                    FROM [HTC300_G030_T010 Customers]
                    WHERE [CustomerID] = ?
                """
                cursor.execute(query, (customer_id,))
                row = cursor.fetchone()

                if row is None:
                    logger.debug(f"Customer {customer_id} not found")
                    return None

                customer_name = str(row[0]) if row[0] else None
                logger.debug(f"Found customer name '{customer_name}' for ID {customer_id}")
                return customer_name

        except Exception as e:
            logger.error(f"Failed to lookup customer name for ID {customer_id}: {e}")
            return None

    def get_customer_info(self, customer_id: int) -> Optional[CustomerInfo]:
        """
        Get full customer information for order creation.

        Args:
            customer_id: The customer ID to look up

        Returns:
            CustomerInfo dataclass if found, None if not found
        """
        connection = self._get_connection()

        try:
            with connection.cursor() as cursor:
                query = """
                    SELECT
                        [CustomerID],
                        [Customer],
                        [Cus_Assessorials],
                        [Cus_Tariff],
                        [Cus_QBCustomerRefListID],
                        [Cus_QBCustomerRefFullName]
                    FROM [HTC300_G030_T010 Customers]
                    WHERE [CustomerID] = ?
                """
                cursor.execute(query, (customer_id,))
                row = cursor.fetchone()

                if row is None:
                    logger.debug(f"Customer {customer_id} not found")
                    return None

                customer_info = CustomerInfo(
                    customer_id=int(row[0]),
                    name=str(row[1]) if row[1] else "",
                    assessorials=str(row[2]) if row[2] else "",
                    tariff=str(row[3]) if row[3] else "",
                    qb_list_id=str(row[4]) if row[4] else "",
                    qb_full_name=str(row[5]) if row[5] else "",
                )

                logger.debug(f"Found customer info for ID {customer_id}: {customer_info.name}")
                return customer_info

        except Exception as e:
            logger.error(f"Failed to get customer info for ID {customer_id}: {e}")
            return None

    def get_address_info(self, address_id: float) -> Optional[AddressInfo]:
        """
        Get full address information for order creation.

        Args:
            address_id: The address ID (FavID) to look up

        Returns:
            AddressInfo dataclass if found, None if not found
        """
        connection = self._get_connection()

        try:
            with connection.cursor() as cursor:
                query = """
                    SELECT
                        [FavID],
                        [FavCompany],
                        [FavLocnName],
                        [FavAddrLn1],
                        [FavAddrLn2],
                        [FavCity],
                        [FavState],
                        [FavZip],
                        [FavCountry],
                        [FavLatitude],
                        [FavLongitude],
                        [FavACIID],
                        [FavAssessorials],
                        [FavCarrierYN],
                        [FavCarrierGroundYN],
                        [FavInternational],
                        [FavLocalYN],
                        [FavBranchAddressYN]
                    FROM [HTC300_G060_T010 Addresses]
                    WHERE [FavID] = ?
                      AND [FavCoID] = ?
                      AND [FavBrID] = ?
                """
                cursor.execute(query, (address_id, self.CO_ID, self.BR_ID))
                row = cursor.fetchone()

                if row is None:
                    logger.debug(f"Address {address_id} not found")
                    return None

                address_info = AddressInfo(
                    fav_id=float(row[0]),
                    company=str(row[1]) if row[1] else "",
                    locn_name=str(row[2]) if row[2] else "",
                    addr_ln1=str(row[3]) if row[3] else "",
                    addr_ln2=str(row[4]) if row[4] else "",
                    city=str(row[5]) if row[5] else "",
                    state=str(row[6]) if row[6] else "",
                    zip_code=str(row[7]) if row[7] else "",
                    country=str(row[8]) if row[8] else "",
                    latitude=str(row[9]) if row[9] else "",
                    longitude=str(row[10]) if row[10] else "",
                    aci_id=int(row[11]) if row[11] else 0,
                    assessorials=str(row[12]) if row[12] else "",
                    carrier_yn=bool(row[13]) if row[13] is not None else False,
                    carrier_ground_yn=bool(row[14]) if row[14] is not None else False,
                    international_yn=bool(row[15]) if row[15] is not None else False,
                    local_yn=bool(row[16]) if row[16] is not None else False,
                    branch_yn=bool(row[17]) if row[17] is not None else False,
                )

                logger.debug(f"Found address info for ID {address_id}: {address_info.company}")
                return address_info

        except Exception as e:
            logger.error(f"Failed to get address info for ID {address_id}: {e}")
            return None

    def get_aci_letter(self, aci_id: int) -> str:
        """
        Get the ACI zone letter from an ACI ID.

        Args:
            aci_id: The ACI ID to look up

        Returns:
            ACI zone letter (e.g., "A", "B", "C", "D") or empty string if not found
        """
        if not aci_id or aci_id == 0:
            return ""

        connection = self._get_connection()

        try:
            with connection.cursor() as cursor:
                query = """
                    SELECT [AREA]
                    FROM [HTC300_G010_T010 DFW_ACI_Data]
                    WHERE [ID] = ?
                      AND [ACICoID] = ?
                      AND [ACIBrID] = ?
                      AND [Active] = 1
                """
                cursor.execute(query, (aci_id, self.CO_ID, self.BR_ID))
                row = cursor.fetchone()

                if row is None:
                    logger.debug(f"ACI ID {aci_id} not found")
                    return ""

                area = str(row[0]).strip() if row[0] else ""
                logger.debug(f"Found ACI letter '{area}' for ID {aci_id}")
                return area

        except Exception as e:
            logger.error(f"Failed to get ACI letter for ID {aci_id}: {e}")
            return ""

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

    # ==================== Order Number Generation ====================

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

                # Step 3: Add to OIW (reserves/locks the number)
                # NOTE: LON is updated AFTER successful order creation via _update_lon()
                with connection.cursor() as cursor:
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

    # ==================== Order Creation Orchestrator ====================

    def create_order(
        self,
        customer_id: int,
        hawb: str,
        pickup_address: str,
        pickup_time_start: str,
        pickup_time_end: str,
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
            pickup_address: Full pickup address string (e.g., "Company, 123 Main St, Dallas, TX 75201")
            pickup_time_start: Pickup start datetime (e.g., "2025-12-15 09:00")
            pickup_time_end: Pickup end datetime
            delivery_address: Full delivery address string
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

        # Extract company name from address (first line before comma, or use address as-is)
        pu_company = self._extract_company_from_address(pickup_address)
        pu_address_id = self.find_or_create_address(
            address_string=pickup_address,
            company_name=pu_company,
        )
        logger.debug(f"Resolved pickup address ID: {pu_address_id}")

        # --- Step 2: Resolve delivery address ---
        if not delivery_address:
            raise ValueError("Delivery address is required")

        del_company = self._extract_company_from_address(delivery_address)
        del_address_id = self.find_or_create_address(
            address_string=delivery_address,
            company_name=del_company,
        )
        logger.debug(f"Resolved delivery address ID: {del_address_id}")

        # --- Step 3: Look up full pickup address info ---
        pu_addr = self.get_address_info(pu_address_id)
        if not pu_addr:
            raise OutputExecutionError(f"Failed to get pickup address info for ID {pu_address_id}")

        pu_aci_letter = self.get_aci_letter(pu_addr.aci_id)

        # --- Step 4: Look up full delivery address info ---
        del_addr = self.get_address_info(del_address_id)
        if not del_addr:
            raise OutputExecutionError(f"Failed to get delivery address info for ID {del_address_id}")

        del_aci_letter = self.get_aci_letter(del_addr.aci_id)

        # --- Step 5: Look up customer info ---
        customer = self.get_customer_info(customer_id)
        if not customer:
            raise OutputExecutionError(f"Failed to get customer info for ID {customer_id}")

        # --- Step 6: Determine order type ---
        order_type = self.determine_order_type(
            pu_aci=pu_aci_letter,
            pu_branch=pu_addr.branch_yn,
            pu_carrier=pu_addr.carrier_yn,
            del_aci=del_aci_letter,
            del_branch=del_addr.branch_yn,
            del_carrier=del_addr.carrier_yn,
        )
        logger.debug(f"Determined order type: {order_type}")

        # --- Step 7: Parse dates and times ---
        pu_date, pu_time_start_parsed = self._parse_datetime_string(pickup_time_start)
        _, pu_time_end_parsed = self._parse_datetime_string(pickup_time_end)
        del_date, del_time_start_parsed = self._parse_datetime_string(delivery_time_start)
        _, del_time_end_parsed = self._parse_datetime_string(delivery_time_end)

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
            order_number = self._generate_next_order_number()
            logger.info(f"Reserved order number: {order_number}")

            # --- Step 10: Insert order record ---
            self._create_order_record(order_number, prepared_data)

            # --- Step 11: Insert dimension record ---
            self._create_dimension_record(
                order_number=order_number,
                pieces=pieces or 1,
                weight=weight or 0.0,
            )

            # --- Step 12: Finalize on success ---
            # Update LON
            self._update_lon(order_number)

            # Remove from OIW (release lock)
            self.remove_from_orders_in_work(order_number)

            # Save HAWB association
            self.save_hawb_association(
                hawb=hawb,
                customer_id=customer_id,
                order_number=order_number,
            )

            # Create order history
            self._create_order_history(
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
            pickup_address=pending_order.pickup_address,
            pickup_time_start=pending_order.pickup_time_start,
            pickup_time_end=pending_order.pickup_time_end,
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

    def _extract_company_from_address(self, address_string: str) -> str:
        """
        Extract company name from an address string.

        The address string format is typically:
        "Company Name, Street Address, City, State ZIP"

        If no comma is found, returns the whole string.

        Args:
            address_string: The full address string

        Returns:
            The company name portion
        """
        if not address_string:
            return ""

        # Try to get the first part before the comma as company name
        parts = address_string.split(',')
        if len(parts) > 1:
            return parts[0].strip()
        else:
            # No comma - might just be a street address
            return address_string.strip()

    def _parse_datetime_string(self, datetime_str: Optional[str]) -> tuple[str, str]:
        """
        Parse a datetime string into date and time components.

        Args:
            datetime_str: String in format "YYYY-MM-DD HH:MM" or "MM/DD/YYYY HH:MM"
                         or just a time like "HH:MM"

        Returns:
            Tuple of (date_str, time_str) in formats ("MM/DD/YYYY", "HH:MM")
            Returns ("", "") if input is None or empty
        """
        if not datetime_str:
            return ("", "")

        datetime_str = datetime_str.strip()

        # Try to parse as full datetime
        try:
            # Try ISO format first (YYYY-MM-DD HH:MM)
            if 'T' in datetime_str or (len(datetime_str) > 10 and datetime_str[4] == '-'):
                dt = datetime.fromisoformat(datetime_str.replace('T', ' ').split('.')[0])
                return (dt.strftime("%m/%d/%Y"), dt.strftime("%H:%M"))

            # Try MM/DD/YYYY HH:MM format
            if '/' in datetime_str and ' ' in datetime_str:
                parts = datetime_str.split(' ')
                date_part = parts[0]
                time_part = parts[1] if len(parts) > 1 else ""
                return (date_part, time_part)

            # If it's just a time (HH:MM), use today's date
            if ':' in datetime_str and len(datetime_str) <= 5:
                today = datetime.now().strftime("%m/%d/%Y")
                return (today, datetime_str)

            # Return as-is if we can't parse
            return (datetime_str, "")

        except Exception as e:
            logger.warning(f"Failed to parse datetime string '{datetime_str}': {e}")
            return (datetime_str, "")

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

    def _update_lon(self, order_number: float) -> None:
        """
        Update the Last Order Number Assigned table after successful order creation.

        This should be called AFTER the order is successfully created, not during
        order number generation. The OIW table handles the "lock" during creation.

        Args:
            order_number: The order number that was just successfully assigned
        """
        logger.debug(f"Updating LON to {order_number}")

        connection = self._get_connection()

        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE [HTC300_G040_T000 Last OrderNo Assigned]
                    SET [lon_orderno] = ?
                    WHERE [lon_coid] = ? AND [lon_brid] = ?
                """, (order_number, self.CO_ID, self.BR_ID))

            logger.debug(f"Updated LON to {order_number}")

        except Exception as e:
            logger.error(f"Failed to update LON to {order_number}: {e}")
            raise

    def save_hawb_association(
        self,
        hawb: str,
        customer_id: int,
        order_number: float,
    ) -> bool:
        """
        Save a customer/HAWB association after order creation.

        Records which HAWB was used for which customer/order. The HAWB is the
        primary key, so duplicate HAWBs will fail silently (matching VBA behavior
        where reusing a HAWB is sometimes acceptable).

        Args:
            hawb: The HAWB string
            customer_id: The customer ID
            order_number: The order number this HAWB is associated with

        Returns:
            True if saved successfully, False if HAWB already exists
        """
        if not hawb or not hawb.strip():
            logger.debug("Empty HAWB, skipping association save")
            return False

        connection = self._get_connection()

        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO [HTC300_G040_T040 HAWB Values]
                    ([ExistingHAWBValues], [HAWBCoID], [HAWBBrID], [HAWBCustomerID], [HAWBOrder])
                    VALUES (?, ?, ?, ?, ?)
                """, (hawb.strip(), self.CO_ID, self.BR_ID, customer_id, order_number))

            logger.debug(f"Saved HAWB association: {hawb} -> order {order_number}")
            return True

        except Exception as e:
            # HAWB is primary key - duplicate insert will fail
            # This is expected behavior (VBA uses On Error Resume Next)
            if "duplicate" in str(e).lower() or "unique" in str(e).lower() or "primary" in str(e).lower():
                logger.debug(f"HAWB {hawb} already exists, skipping")
                return False
            else:
                logger.error(f"Failed to save HAWB association: {e}")
                raise

    def _create_order_history(
        self,
        order_number: float,
        customer_id: int,
        customer_name: str,
        tariff: str,
        status: str,
        status_seq: int,
        attachment_count: int = 0,
    ) -> None:
        """
        Create an order history record for audit trail.

        Args:
            order_number: The order number
            customer_id: The customer ID
            customer_name: The customer name
            tariff: The tariff used
            status: The order status string
            status_seq: The status sequence number
            attachment_count: Number of attachments (default 0)
        """
        connection = self._get_connection()

        # Build the change description (matches VBA format)
        change_desc = (
            f"Order #{int(order_number)} Customer: {customer_name} (#{customer_id}) "
            f"Created with 1 Dim, 0 Assessorials, 0 Drivers, and {attachment_count} Attachments, "
            f"assigned $0.00 using the {tariff} tariff; "
            f"Status = {status}({status_seq})"
        )

        now = datetime.now()
        user_id = "ETO_SYSTEM"

        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO [HTC300_G040_T030 Orders Update History]
                    ([Orders_UpdtDate], [Orders_UpdtLID], [Orders_CoID], [Orders_BrID],
                     [Orders_OrderNbr], [Orders_Changes])
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (now, user_id, self.CO_ID, self.BR_ID, order_number, change_desc))

            logger.debug(f"Created order history for order {order_number}")

        except Exception as e:
            # Log but don't fail order creation if history fails
            logger.warning(f"Failed to create order history for order {order_number}: {e}")

    def _create_dimension_record(
        self,
        order_number: float,
        pieces: int = 1,
        weight: float = 0.0,
        length: int = 1,
        width: int = 1,
        height: int = 1,
        unit_type: str = "EA",
    ) -> None:
        """
        Create a dimension record for an order.

        Args:
            order_number: The order number
            pieces: Number of pieces (default 1)
            weight: Total weight (default 0.0)
            length: Length in inches (default 1)
            width: Width in inches (default 1)
            height: Height in inches (default 1)
            unit_type: Unit type code (default "EA" for each)
        """
        connection = self._get_connection()

        # Calculate dimensional weight (L x W x H / 139 for air freight)
        dim_weight = (length * width * height) / 139.0

        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO [HTC300_G040_T012A Open Order Dims]
                    ([OD_CoID], [OD_BrID], [OD_OrderNo], [OD_DimID],
                     [OD_UnitType], [OD_UnitQty], [OD_UnitHeight],
                     [OD_UnitLength], [OD_UnitWidth], [OD_UnitWeight], [OD_UnitDimWeight])
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    self.CO_ID,
                    self.BR_ID,
                    order_number,
                    1,  # OD_DimID - first dimension record
                    unit_type,
                    pieces,
                    height,
                    length,
                    width,
                    weight,
                    dim_weight,
                ))

            logger.debug(f"Created dimension record for order {order_number}")

        except Exception as e:
            logger.error(f"Failed to create dimension record for order {order_number}: {e}")
            raise

    def _create_order_record(
        self,
        order_number: float,
        data: 'PreparedOrderData',
    ) -> None:
        """
        Create the main order record in HTC300_G040_T010A Open Orders.

        This is the core INSERT with all 75 fields. The data parameter should
        be fully populated from Phase 1 (data gathering).

        Args:
            order_number: The reserved order number from _generate_next_order_number()
            data: PreparedOrderData with all field values ready

        Raises:
            OutputExecutionError: If the INSERT fails
        """
        connection = self._get_connection()

        # Default values
        status = "ETO Generated"
        status_seq = 35

        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO [HTC300_G040_T010A Open Orders] (
                        [M_CoID], [M_BrID], [M_OrderNo], [M_OrderType],
                        [M_CustomerID], [m_Customer], [M_CustAssessorials], [M_Tariff],
                        [M_QBCustomerListID], [M_QBCustFullName], [M_CustAgent],
                        [M_HAWB], [M_MAWB], [M_OrderNotes],
                        [M_PUDate], [M_PUTimeStart], [M_PUTimeEnd],
                        [M_PUID], [M_PUCo], [M_PULocn], [M_PUZip],
                        [M_PULatitude], [M_PULongitude], [M_PUACI],
                        [M_PUAssessorials], [M_PUCarrierYN], [M_PUCarrierGroundYN],
                        [M_PUIntlYN], [M_PULocalYN], [M_PUBranchYN],
                        [M_PUContactName], [M_PUContactMeans], [M_PUNotes],
                        [M_DelDate], [M_DelTimeStart], [M_DelTimeEnd],
                        [M_DelID], [M_DelCo], [M_DelLocn], [M_DelZip],
                        [M_DelLatitude], [M_DelLongitude], [M_DelACI],
                        [M_Del_Assessorials], [M_DelCarrierYN], [M_DelCarrierGroundYN],
                        [M_DelIntlYN], [M_DelLocalYN], [M_DelBranchYN],
                        [M_DelContactName], [M_DelContactMeans], [M_DelNotes],
                        [M_Status], [m_StatSeq],
                        [M_Rate], [M_FSC], [M_Services], [M_Charges],
                        [M_Costs], [M_StorageChgs], [M_Adjustments], [M_DeclaredValue],
                        [M_AutoAssessYN], [M_WgtChgsCalcYN],
                        [M_PUSpecificYN], [M_DelSpecificYN],
                        [M_ProNbr], [M_Driver],
                        [M_PODSig], [M_PODDate], [M_PODTime], [M_PODNotes],
                        [M_RatingNotes], [M_QBInvoiceRefNumber], [M_QBInvoiceLineSeqNo]
                    ) VALUES (
                        ?, ?, ?, ?,
                        ?, ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?,
                        ?, ?,
                        ?, ?, ?, ?,
                        ?, ?, ?, ?,
                        ?, ?,
                        ?, ?,
                        ?, ?,
                        ?, ?, ?, ?,
                        ?, ?, ?
                    )
                """, (
                    # System
                    self.CO_ID,                          # M_CoID
                    self.BR_ID,                          # M_BrID
                    order_number,                        # M_OrderNo
                    data.order_type,                     # M_OrderType

                    # Customer
                    data.customer_id,                    # M_CustomerID
                    data.customer_name,                  # m_Customer
                    data.customer_assessorials,          # M_CustAssessorials
                    data.customer_tariff,                # M_Tariff
                    data.customer_qb_list_id,            # M_QBCustomerListID
                    data.customer_qb_full_name,          # M_QBCustFullName
                    None,                                # M_CustAgent (DEFERRED - needs DB update)

                    # Order info
                    data.hawb,                           # M_HAWB
                    data.mawb,                           # M_MAWB
                    data.order_notes,                    # M_OrderNotes

                    # Pickup times
                    data.pu_date,                        # M_PUDate
                    data.pu_time_start,                  # M_PUTimeStart
                    data.pu_time_end,                    # M_PUTimeEnd

                    # Pickup address
                    data.pu_address_id,                  # M_PUID
                    data.pu_company,                     # M_PUCo
                    data.pu_location,                    # M_PULocn
                    data.pu_zip,                         # M_PUZip
                    data.pu_latitude,                    # M_PULatitude
                    data.pu_longitude,                   # M_PULongitude
                    data.pu_aci,                         # M_PUACI
                    data.pu_assessorials,                # M_PUAssessorials
                    data.pu_carrier_yn,                  # M_PUCarrierYN
                    data.pu_carrier_ground_yn,           # M_PUCarrierGroundYN
                    data.pu_intl_yn,                     # M_PUIntlYN
                    data.pu_local_yn,                    # M_PULocalYN
                    data.pu_branch_yn,                   # M_PUBranchYN
                    "",                                  # M_PUContactName
                    "",                                  # M_PUContactMeans
                    data.pu_notes,                       # M_PUNotes

                    # Delivery times
                    data.del_date,                       # M_DelDate
                    data.del_time_start,                 # M_DelTimeStart
                    data.del_time_end,                   # M_DelTimeEnd

                    # Delivery address
                    data.del_address_id,                 # M_DelID
                    data.del_company,                    # M_DelCo
                    data.del_location,                   # M_DelLocn
                    data.del_zip,                        # M_DelZip
                    data.del_latitude,                   # M_DelLatitude
                    data.del_longitude,                  # M_DelLongitude
                    data.del_aci,                        # M_DelACI
                    data.del_assessorials,               # M_Del_Assessorials
                    data.del_carrier_yn,                 # M_DelCarrierYN
                    data.del_carrier_ground_yn,          # M_DelCarrierGroundYN
                    data.del_intl_yn,                    # M_DelIntlYN
                    data.del_local_yn,                   # M_DelLocalYN
                    data.del_branch_yn,                  # M_DelBranchYN
                    "",                                  # M_DelContactName
                    "",                                  # M_DelContactMeans
                    data.del_notes,                      # M_DelNotes

                    # Status
                    status,                              # M_Status
                    status_seq,                          # m_StatSeq

                    # Financial (all zero)
                    0,                                   # M_Rate
                    0,                                   # M_FSC
                    0,                                   # M_Services
                    0,                                   # M_Charges
                    0,                                   # M_Costs
                    0,                                   # M_StorageChgs
                    0,                                   # M_Adjustments
                    0,                                   # M_DeclaredValue

                    # Boolean flags
                    False,                               # M_AutoAssessYN
                    False,                               # M_WgtChgsCalcYN
                    True,                               # M_PUSpecificYN
                    True,                               # M_DelSpecificYN

                    # Empty fields (populated later)
                    "",                                  # M_ProNbr
                    "",                                  # M_Driver
                    "",                                  # M_PODSig
                    "",                                  # M_PODDate
                    "",                                  # M_PODTime
                    "",                                  # M_PODNotes
                    "",                                  # M_RatingNotes
                    "",                                  # M_QBInvoiceRefNumber
                    None,                                # M_QBInvoiceLineSeqNo
                ))

            logger.info(f"Created order record {order_number} for customer {data.customer_id}")

        except Exception as e:
            logger.error(f"Failed to create order record {order_number}: {e}")
            raise OutputExecutionError(f"Failed to create order record: {e}") from e

    # ==================== Address Resolution ====================
    #
    # Address matching strategy: Normalized exact match with precision focus
    #
    # - We normalize for valid variations (abbreviations, punctuation, case)
    # - We do NOT fuzzy match - if it doesn't match after normalization, no match
    # - False negatives are OK (create new correct address)
    # - False positives are NOT OK (avoid matching to bad data)
    #
    # Database notes:
    # - Suite/unit info is stored IN FavAddrLn1 (e.g., "4901 KELLER SPRINGS #106D")
    # - FavAddrLn2 is rarely used
    # - Some addresses have incomplete/incorrect data - we don't try to match those

    # Street type abbreviations - map full names to standard abbreviations
    STREET_TYPE_ABBREV = {
        'STREET': 'ST',
        'AVENUE': 'AVE',
        'BOULEVARD': 'BLVD',
        'PARKWAY': 'PKWY',
        'DRIVE': 'DR',
        'ROAD': 'RD',
        'LANE': 'LN',
        'COURT': 'CT',
        'CIRCLE': 'CIR',
        'PLACE': 'PL',
        'HIGHWAY': 'HWY',
        'FREEWAY': 'FWY',
        'EXPRESSWAY': 'EXPY',
        'TERRACE': 'TER',
        'TRAIL': 'TRL',
        'WAY': 'WAY',
        'LOOP': 'LOOP',
        'CROSSING': 'XING',
        'SQUARE': 'SQ',
        'PASS': 'PASS',
        'PATH': 'PATH',
        'PIKE': 'PIKE',
        'ALLEY': 'ALY',
        'BEND': 'BND',
        'COVE': 'CV',
        'CREEK': 'CRK',
        'ESTATE': 'EST',
        'ESTATES': 'ESTS',
        'FALLS': 'FLS',
        'FERRY': 'FRY',
        'FIELD': 'FLD',
        'FIELDS': 'FLDS',
        'FLAT': 'FLT',
        'FLATS': 'FLTS',
        'FORD': 'FRD',
        'FOREST': 'FRST',
        'FORGE': 'FRG',
        'FORK': 'FRK',
        'FORKS': 'FRKS',
        'GARDEN': 'GDN',
        'GARDENS': 'GDNS',
        'GATEWAY': 'GTWY',
        'GLEN': 'GLN',
        'GREEN': 'GRN',
        'GROVE': 'GRV',
        'HARBOR': 'HBR',
        'HAVEN': 'HVN',
        'HEIGHTS': 'HTS',
        'HILL': 'HL',
        'HILLS': 'HLS',
        'HOLLOW': 'HOLW',
        'INLET': 'INLT',
        'ISLAND': 'IS',
        'ISLANDS': 'ISS',
        'JUNCTION': 'JCT',
        'KEY': 'KY',
        'KNOLL': 'KNL',
        'LAKE': 'LK',
        'LAKES': 'LKS',
        'LANDING': 'LNDG',
        'MEADOW': 'MDW',
        'MEADOWS': 'MDWS',
        'MILL': 'ML',
        'MILLS': 'MLS',
        'MISSION': 'MSN',
        'MOUNT': 'MT',
        'MOUNTAIN': 'MTN',
        'ORCHARD': 'ORCH',
        'PARK': 'PARK',
        'PARKS': 'PARK',
        'POINT': 'PT',
        'POINTS': 'PTS',
        'PORT': 'PRT',
        'PRAIRIE': 'PR',
        'RANCH': 'RNCH',
        'RAPIDS': 'RPDS',
        'RIDGE': 'RDG',
        'RIVER': 'RIV',
        'RUN': 'RUN',
        'SHORE': 'SHR',
        'SHORES': 'SHRS',
        'SPRING': 'SPG',
        'SPRINGS': 'SPGS',
        'STATION': 'STA',
        'STREAM': 'STRM',
        'SUMMIT': 'SMT',
        'TRACE': 'TRCE',
        'TRACK': 'TRAK',
        'TURNPIKE': 'TPKE',
        'VALLEY': 'VLY',
        'VIEW': 'VW',
        'VIEWS': 'VWS',
        'VILLAGE': 'VLG',
        'VISTA': 'VIS',
        'WALK': 'WALK',
        'WELL': 'WL',
        'WELLS': 'WLS',
    }

    # Directional abbreviations
    DIRECTIONAL_ABBREV = {
        'NORTH': 'N',
        'SOUTH': 'S',
        'EAST': 'E',
        'WEST': 'W',
        'NORTHEAST': 'NE',
        'NORTHWEST': 'NW',
        'SOUTHEAST': 'SE',
        'SOUTHWEST': 'SW',
    }

    # Unit type abbreviations
    UNIT_TYPE_ABBREV = {
        'APARTMENT': 'APT',
        'BUILDING': 'BLDG',
        'DEPARTMENT': 'DEPT',
        'FLOOR': 'FL',
        'SUITE': 'STE',
        'UNIT': 'UNIT',
        'ROOM': 'RM',
        'SPACE': 'SPC',
        'STOP': 'STOP',
        'TRAILER': 'TRLR',
        'BOX': 'BOX',
        'LOBBY': 'LBBY',
        'LOWER': 'LOWR',
        'OFFICE': 'OFC',
        'PENTHOUSE': 'PH',
        'PIER': 'PIER',
        'REAR': 'REAR',
        'SIDE': 'SIDE',
        'SLIP': 'SLIP',
        'UPPER': 'UPPR',
        'HANGAR': 'HNGR',
        'BASEMENT': 'BSMT',
        'FRONT': 'FRNT',
    }

    def normalize_address_component(self, text: str) -> str:
        """
        Normalize a single address component (street name, city, etc).

        Normalization steps:
        1. Uppercase
        2. Remove periods
        3. Collapse multiple spaces
        4. Strip whitespace

        This does NOT expand/abbreviate - that's done separately for matching.
        """
        if not text:
            return ''

        result = text.upper()
        result = result.replace('.', '')
        result = ' '.join(result.split())  # Collapse multiple spaces
        return result.strip()

    # Unit type designators to strip during normalization (we keep only the identifier)
    UNIT_DESIGNATORS_TO_STRIP = {
        '#', 'SUITE', 'STE', 'UNIT', 'APT', 'APARTMENT', 'BLDG', 'BUILDING',
        'FL', 'FLOOR', 'RM', 'ROOM', 'SPC', 'SPACE', 'DEPT', 'DEPARTMENT',
        'OFC', 'OFFICE', 'TRLR', 'TRAILER', 'LOT', 'SLIP', 'PIER', 'HNGR',
        'HANGAR', 'LBBY', 'LOBBY', 'PH', 'PENTHOUSE', 'BSMT', 'BASEMENT',
        'FRNT', 'FRONT', 'REAR', 'SIDE', 'LOWR', 'LOWER', 'UPPR', 'UPPER',
    }

    def normalize_street_for_matching(self, street: str) -> str:
        """
        Normalize a street address for comparison matching.

        Steps:
        1. Basic normalization (uppercase, remove periods, collapse spaces)
        2. Expand all abbreviations to full forms for consistent comparison
        3. Strip unit type designators (keep only the identifier)
           So "#106D", "Suite 106D", "Ste 106D" all become just "106D"

        Args:
            street: Street address string (e.g., "123 N. Main St. #100")

        Returns:
            Normalized string (e.g., "123 NORTH MAIN STREET 100")
        """
        if not street:
            return ''

        # Basic normalization
        result = self.normalize_address_component(street)

        # Handle "#" attached to identifier (e.g., "#106D" -> "# 106D")
        # This ensures we can strip the "#" as a separate word
        import re
        result = re.sub(r'#(\w)', r'# \1', result)

        # Build reverse mappings (abbrev -> full) for expansion
        street_expand = {v: k for k, v in self.STREET_TYPE_ABBREV.items()}
        dir_expand = {v: k for k, v in self.DIRECTIONAL_ABBREV.items()}

        # Split into words and process each
        words = result.split()
        normalized_words = []

        for word in words:
            # Skip unit type designators entirely (we keep only the identifier)
            if word in self.UNIT_DESIGNATORS_TO_STRIP:
                continue
            # Try to expand street types
            elif word in street_expand:
                normalized_words.append(street_expand[word])
            # Try to expand directionals
            elif word in dir_expand:
                normalized_words.append(dir_expand[word])
            else:
                normalized_words.append(word)

        return ' '.join(normalized_words)

    def parse_address_string(self, address_string: str) -> Optional[Dict[str, str]]:
        """
        Parse a US address string into components using the usaddress library.

        Args:
            address_string: Full address string to parse
                e.g., "123 Main St, Suite 100, Dallas, TX 75201"

        Returns:
            Dictionary with parsed components:
            - street: Full street line including suite/unit (e.g., "123 Main St Suite 100")
            - city: City name
            - state: State abbreviation
            - zip_code: ZIP code (without +4)
            Returns None if parsing fails or essential components missing.
        """
        try:
            import usaddress
        except ImportError:
            logger.error("usaddress library not installed. Run: pip install usaddress")
            raise ImportError("usaddress library required for address parsing")

        if not address_string or not address_string.strip():
            logger.debug("Empty address string provided")
            return None

        logger.debug(f"Parsing address: '{address_string}'")

        try:
            parsed, address_type = usaddress.tag(address_string)
        except usaddress.RepeatedLabelError as e:
            logger.warning(f"Address parsing ambiguous (repeated labels): {e}")
            return None

        # Build full street line (everything before city/state/zip)
        # This includes suite/unit info since that's how DB stores it
        street_parts = []

        # Street number
        if 'AddressNumber' in parsed:
            street_parts.append(parsed['AddressNumber'])

        # Pre-directional (N, S, E, W)
        if 'StreetNamePreDirectional' in parsed:
            street_parts.append(parsed['StreetNamePreDirectional'])

        # Street name
        if 'StreetName' in parsed:
            street_parts.append(parsed['StreetName'])

        # Street type (St, Ave, Blvd)
        if 'StreetNamePostType' in parsed:
            street_parts.append(parsed['StreetNamePostType'])

        # Post-directional
        if 'StreetNamePostDirectional' in parsed:
            street_parts.append(parsed['StreetNamePostDirectional'])

        # Suite/unit/apt - append to street line (matches DB storage)
        if 'OccupancyType' in parsed:
            street_parts.append(parsed['OccupancyType'])
        if 'OccupancyIdentifier' in parsed:
            street_parts.append(parsed['OccupancyIdentifier'])
        if 'SubaddressType' in parsed:
            street_parts.append(parsed['SubaddressType'])
        if 'SubaddressIdentifier' in parsed:
            street_parts.append(parsed['SubaddressIdentifier'])

        street = ' '.join(street_parts)

        # Extract location components
        city = parsed.get('PlaceName', '')
        state = parsed.get('StateName', '')
        zip_code = parsed.get('ZipCode', '')

        # Validate we have minimum required components
        if not street or not city or not state or not zip_code:
            logger.debug(f"Missing required components - street: '{street}', "
                        f"city: '{city}', state: '{state}', zip: '{zip_code}'")
            return None

        result = {
            'street': street,
            'city': city,
            'state': state,
            'zip_code': zip_code,
        }

        logger.debug(f"Parsed address: {result}")
        return result

    def find_address_by_text(
        self,
        street: str,
        city: str,
        state: str,
        zip_code: str,
    ) -> Optional[float]:
        """
        Search for an existing address in the database using normalized matching.

        Strategy:
        1. Filter candidates by city/state/zip (exact match after basic normalization)
        2. Load all matching addresses
        3. Normalize both input street and DB streets
        4. Find exact match after normalization

        Args:
            street: Full street line including suite (e.g., "123 Main St Suite 100")
            city: City name
            state: State abbreviation (e.g., "TX")
            zip_code: ZIP code (e.g., "75201")

        Returns:
            Address ID (FavID as float) if found, None otherwise.
        """
        connection = self._get_connection()

        # Normalize location components for filtering
        norm_city = self.normalize_address_component(city)
        norm_state = self.normalize_address_component(state)
        # For zip, just take first 5 digits
        norm_zip = zip_code[:5] if zip_code else ''

        # Normalize input street for comparison
        norm_input_street = self.normalize_street_for_matching(street)

        logger.debug(f"Searching for address - normalized street: '{norm_input_street}', "
                     f"city: '{norm_city}', state: '{norm_state}', zip: '{norm_zip}'")

        # Query: filter by city/state/zip (case-insensitive via UCASE - Access syntax)
        # We'll normalize the street comparison in Python for more control
        query = """
            SELECT FavID, FavAddrLn1, FavAddrLn2
            FROM [HTC300_G060_T010 Addresses]
            WHERE UCASE(FavCity) = ?
              AND UCASE(FavState) = ?
              AND LEFT(FavZip, 5) = ?
              AND FavActive = 1
        """
        params = (norm_city, norm_state, norm_zip)

        try:
            with connection.cursor() as cursor:
                cursor.execute(query, params)
                rows = cursor.fetchall()

                if not rows:
                    logger.debug(f"No addresses found for {norm_city}, {norm_state} {norm_zip}")
                    return None

                logger.debug(f"Found {len(rows)} candidate addresses in {norm_city}, {norm_state}")

                # Check each candidate for normalized match
                for row in rows:
                    # Combine FavAddrLn1 and FavAddrLn2 for comparison
                    db_street_parts = [row.FavAddrLn1 or '']
                    if row.FavAddrLn2:
                        db_street_parts.append(row.FavAddrLn2)
                    db_street = ' '.join(db_street_parts)

                    # Normalize DB street
                    norm_db_street = self.normalize_street_for_matching(db_street)

                    # Exact match after normalization
                    if norm_input_street == norm_db_street:
                        address_id = float(row.FavID)
                        logger.debug(f"Found matching address: ID={address_id}, "
                                    f"DB street='{db_street}'")
                        return address_id

                logger.debug(f"No normalized match found for '{norm_input_street}'")
                return None

        except Exception as e:
            logger.error(f"Failed to search for address: {e}")
            raise

    def find_address_id(self, address_string: str) -> Optional[float]:
        """
        Find an address ID from a full address string.

        This is the main entry point for address lookup.
        It parses the address string and searches for a normalized match.

        Strategy: Precision over recall
        - We normalize for valid variations (abbreviations, punctuation, case)
        - We do NOT fuzzy match - if it doesn't match, return None
        - False negatives are OK (caller can create new correct address)
        - False positives are NOT OK (we don't match to bad data)

        Args:
            address_string: Full address string to check
                e.g., "123 Main St, Suite 100, Dallas, TX 75201"

        Returns:
            Address ID (FavID as float) if found, None otherwise.
        """
        # Step 1: Parse the address string
        parsed = self.parse_address_string(address_string)

        if not parsed:
            logger.debug(f"Could not parse address: '{address_string}'")
            return None

        # Step 2: Search for the address in the database
        return self.find_address_by_text(
            street=parsed['street'],
            city=parsed['city'],
            state=parsed['state'],
            zip_code=parsed['zip_code'],
        )

    # ==================== Address Creation ====================
    #
    # See docs/htc-integration/address-creation.md for full specification
    #

    def generate_keycheck(
        self,
        locn_name: str,
        addr_ln1: str,
        addr_ln2: str,
        city: str,
        zip_code: str,
        country: str,
    ) -> str:
        """
        Generate the FavKeycheck value for an address.

        Replicates VBA SpComPer_Removed function:
        - Concatenates: LocnName + AddrLn1 + AddrLn2 + City + Zip + Country
        - Removes spaces, commas, and periods
        - Returns uppercase string

        Args:
            locn_name: Location name
            addr_ln1: Address line 1
            addr_ln2: Address line 2
            city: City name
            zip_code: ZIP code
            country: Country name

        Returns:
            Keycheck string (max 100 chars to fit VARCHAR(100))
        """
        # Concatenate all parts
        combined = f"{locn_name}{addr_ln1}{addr_ln2}{city}{zip_code}{country}"

        # Remove spaces, commas, periods and uppercase
        result = combined.upper()
        result = result.replace(' ', '')
        result = result.replace(',', '')
        result = result.replace('.', '')

        # Truncate to 100 chars (VARCHAR(100) limit)
        return result[:100]

    def generate_keycounts(self, keycheck: str) -> str:
        """
        Generate the FavKeyCounts value from a keycheck string.

        Algorithm (replicates VBA logic):
        1. Count occurrences of each character in keycheck
        2. Sort alphabetically by character
        3. Format as: "A,5;B,3;C,1;..." (character,count pairs separated by semicolons)

        Args:
            keycheck: The keycheck string to analyze

        Returns:
            Formatted character count string (max 255 chars to fit VARCHAR(255))
        """
        if not keycheck:
            return ''

        # Count character occurrences
        char_counts: Dict[str, int] = {}
        for char in keycheck:
            char_counts[char] = char_counts.get(char, 0) + 1

        # Sort alphabetically by character
        sorted_chars = sorted(char_counts.keys())

        # Build result string: "A,5;B,3;..."
        parts = [f"{char},{char_counts[char]}" for char in sorted_chars]
        result = ';'.join(parts) + ';'

        # Truncate to 255 chars (VARCHAR(255) limit)
        return result[:255]

    def get_next_fav_id(self) -> float:
        """
        Get the next available FavID for a new address.

        Replicates VBA HTC200_GetNewAddrID function:
        - Query MAX(FavID) from addresses table
        - Return MAX + 1

        Returns:
            Next available FavID as float
        """
        connection = self._get_connection()

        try:
            with connection.cursor() as cursor:
                query = "SELECT MAX(FavID) FROM [HTC300_G060_T010 Addresses]"
                cursor.execute(query)
                row = cursor.fetchone()

                if row is None or row[0] is None:
                    # No addresses exist yet
                    return 1.0

                return float(row[0]) + 1

        except Exception as e:
            logger.error(f"Failed to get next FavID: {e}")
            raise

    def lookup_aci_by_zip(self, zip_code: str) -> tuple:
        """
        Look up ACI data by ZIP code.

        Queries the DFW_ACI_Data table to find the ACI ID for a given ZIP code.

        Args:
            zip_code: ZIP code to look up (uses first 5 characters)

        Returns:
            Tuple of (aci_listed: bool, aci_id: int)
            - (True, ID) if found
            - (False, 0) if not found
        """
        connection = self._get_connection()

        # Normalize zip to first 5 digits
        norm_zip = zip_code[:5] if zip_code else ''

        if not norm_zip:
            return (False, 0)

        try:
            with connection.cursor() as cursor:
                query = """
                    SELECT ID
                    FROM [HTC300_G010_T010 DFW_ACI_Data]
                    WHERE ZIP_CODE = ?
                      AND Active = 1
                """
                cursor.execute(query, (norm_zip,))
                row = cursor.fetchone()

                if row is None:
                    logger.debug(f"No ACI data found for ZIP {norm_zip}")
                    return (False, 0)

                aci_id = int(row[0])
                logger.debug(f"Found ACI ID {aci_id} for ZIP {norm_zip}")
                return (True, aci_id)

        except Exception as e:
            logger.error(f"Failed to lookup ACI for ZIP {zip_code}: {e}")
            # Fail gracefully - return not found
            return (False, 0)

    def geocode_address(
        self,
        addr_ln1: str,
        city: str,
        state: str,
        zip_code: str,
    ) -> tuple:
        """
        Geocode an address to get latitude/longitude.

        PLACEHOLDER: Returns empty strings for now.
        Will be implemented with actual geocoding service later.

        Args:
            addr_ln1: Street address
            city: City name
            state: State abbreviation
            zip_code: ZIP code

        Returns:
            Tuple of (latitude: str, longitude: str)
            Currently returns ("", "") as placeholder.
        """
        # TODO: Implement actual geocoding (Google Maps, Nominatim, etc.)
        logger.debug(f"Geocoding placeholder called for: {addr_ln1}, {city}, {state} {zip_code}")
        return ("", "")

    def create_address(
        self,
        company_name: str,
        addr_ln1: str,
        city: str,
        state: str,
        zip_code: str,
        country: str = "USA",
        addr_ln2: str = "",
    ) -> float:
        """
        Create a new address record in the HTC database.

        See docs/htc-integration/address-creation.md for full field mapping.

        Args:
            company_name: Company/location name (used for both FavCompany and FavLocnName)
            addr_ln1: Address line 1
            city: City name
            state: State abbreviation
            zip_code: ZIP code
            country: Country name (default: "United States")
            addr_ln2: Address line 2 (optional)

        Returns:
            The new FavID (address ID) as float

        Raises:
            OutputExecutionError: If address creation fails
        """
        logger.info(f"Creating new address: {addr_ln1}, {city}, {state} {zip_code}")

        # Generate keycheck and keycounts
        keycheck = self.generate_keycheck(
            locn_name=company_name,
            addr_ln1=addr_ln1,
            addr_ln2=addr_ln2,
            city=city,
            zip_code=zip_code,
            country=country,
        )
        keycounts = self.generate_keycounts(keycheck)

        # Get next FavID
        fav_id = self.get_next_fav_id()

        # Lookup ACI data
        aci_listed, aci_id = self.lookup_aci_by_zip(zip_code)

        # Geocode address (placeholder)
        latitude, longitude = self.geocode_address(addr_ln1, city, state, zip_code)

        # Current timestamp and user
        now = datetime.now()
        added_by = "eto"

        # Default values
        assessorials = "." * 100  # 100 dots

        connection = self._get_connection()

        try:
            with connection.cursor() as cursor:
                query = """
                    INSERT INTO [HTC300_G060_T010 Addresses] (
                        FavCoID,
                        FavBrID,
                        FavID,
                        FavKeycheck,
                        FavKeyCounts,
                        FavBranchAddressYN,
                        FavCompany,
                        FavLocnName,
                        FavAddrLn1,
                        FavAddrLn2,
                        FavCity,
                        FavState,
                        FavZip,
                        FavCountry,
                        FavLatitude,
                        FavLongitude,
                        FavACIListed,
                        FavACIID,
                        FavFirstName,
                        FavLastName,
                        FavEMail,
                        FavPhone,
                        FavExt,
                        FavAssessorials,
                        FavCarrierYN,
                        FavLocalYN,
                        FavInternational,
                        FavWaitTimeDefault,
                        FavActive,
                        FavDateAdded,
                        FavAddedBy,
                        FavDateModified,
                        FavChgdby,
                        FavCarrierGroundYN
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?
                    )
                """

                params = (
                    self.CO_ID,              # FavCoID = 1
                    self.BR_ID,              # FavBrID = 1
                    fav_id,                  # FavID
                    keycheck,                # FavKeycheck
                    keycounts,               # FavKeyCounts
                    False,                   # FavBranchAddressYN
                    company_name,            # FavCompany
                    company_name,            # FavLocnName (same as company)
                    addr_ln1,                # FavAddrLn1
                    addr_ln2,                # FavAddrLn2
                    city,                    # FavCity
                    state,                   # FavState
                    zip_code,                # FavZip
                    country,                 # FavCountry
                    latitude,                # FavLatitude
                    longitude,               # FavLongitude
                    aci_listed,              # FavACIListed
                    aci_id,                  # FavACIID
                    "",                      # FavFirstName
                    "",                      # FavLastName
                    "",                      # FavEMail
                    "",                      # FavPhone
                    "",                      # FavExt
                    assessorials,            # FavAssessorials
                    False,                   # FavCarrierYN
                    False,                   # FavLocalYN
                    False,                   # FavInternational
                    0,                       # FavWaitTimeDefault
                    True,                    # FavActive
                    now,                     # FavDateAdded
                    added_by,                # FavAddedBy
                    now,                     # FavDateModified
                    added_by,                # FavChgdby
                    False,                   # FavCarrierGroundYN
                )

                cursor.execute(query, params)

            # Add history record for the new address
            self._add_address_history(
                fav_id=fav_id,
                company_name=company_name,
                addr_ln1=addr_ln1,
                addr_ln2=addr_ln2,
                city=city,
                state=state,
                zip_code=zip_code,
                action="added",
            )

            logger.info(f"Created new address with FavID: {fav_id}")
            return fav_id

        except Exception as e:
            logger.error(f"Failed to create address: {e}")
            raise OutputExecutionError(f"Failed to create address: {e}") from e

    def _add_address_history(
        self,
        fav_id: float,
        company_name: str,
        addr_ln1: str,
        addr_ln2: str,
        city: str,
        state: str,
        zip_code: str,
        action: str = "added",
    ) -> None:
        """
        Add a record to the Addresses Update History table.

        Args:
            fav_id: The FavID of the address
            company_name: Company/location name
            addr_ln1: Address line 1
            addr_ln2: Address line 2
            city: City name
            state: State abbreviation
            zip_code: ZIP code
            action: Description of action (e.g., "added", "updated")
        """
        connection = self._get_connection()

        # Build the change description (matches existing records format)
        # Format: "Address ID {FavID}, '{CompanyName} / {LocnName}' added to Pickup/Delivery Address List"
        change_desc = f"Address ID {int(fav_id)}, '{company_name} / {company_name}' {action} to Pickup/Delivery Address List"

        now = datetime.now()
        user_id = "eto"

        try:
            with connection.cursor() as cursor:
                query = """
                    INSERT INTO [HTC300_G060_T030 Addresses Update History] (
                        Addr_UpdtDate,
                        Addr_UpdtLID,
                        Addr_UpdtCoID,
                        Addr_UpdtBrID,
                        Addr_ID,
                        Addr_Chgs
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """
                cursor.execute(query, (
                    now,
                    user_id,
                    self.CO_ID,
                    self.BR_ID,
                    fav_id,
                    change_desc,
                ))

            logger.debug(f"Added address history record for FavID: {fav_id}")

        except Exception as e:
            # Log but don't fail the address creation if history fails
            logger.warning(f"Failed to add address history for FavID {fav_id}: {e}")

    # ==================== Order Type Classification ====================
    #
    # Order types based on pickup/delivery location characteristics.
    # See docs/htc-integration/order-creation.md for full specification.
    #
    # ACI Service Area: Letters A-D represent the local service area.
    # Locations outside A-D are considered "out of area" (Hot Shot territory).
    #

    # Valid ACI zones for local service area
    LOCAL_ACI_ZONES = {'A', 'B', 'C', 'D'}

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

        Classification Rules (checked in order):
        | Type | Code | PU Branch | PU Carrier | PU ACI | Del Branch | Del Carrier | Del ACI |
        |------|------|-----------|------------|--------|------------|-------------|---------|
        | Transfer | 8 | Y | N | A-D | N | Y | A-D |
        | Hot Shot | 4 | - | - | not A-D | - | - | not A-D |
        | Recovery | 1 | N | Y | A-D | - | N | A-D |
        | Drop | 2 | N | Y or N | A-D | N | Y | A-D |
        | Point-to-Point | 3 | N | N | A-D | N | N | A-D |
        | Dock Transfer | 5 | Y | - | - | Y | - | - |
        | Pickup | 9 | N | N | A-D | Y | N | A-D |
        | Delivery | 10 | Y | N | A-D | N | N | A-D |
        | Not Established | 11 | - | - | - | - | - | - |

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
        # Normalize ACI to uppercase for comparison
        pu_aci_upper = (pu_aci or '').upper()
        del_aci_upper = (del_aci or '').upper()

        # Check if locations are within local service area (A-D)
        pu_in_area = pu_aci_upper in self.LOCAL_ACI_ZONES
        del_in_area = del_aci_upper in self.LOCAL_ACI_ZONES

        # Transfer (8): Branch to Carrier, both within service area
        # PU: Branch=Y, Carrier=N, ACI=A-D
        # Del: Branch=N, Carrier=Y, ACI=A-D
        if (pu_branch and not pu_carrier and pu_in_area and
                not del_branch and del_carrier and del_in_area):
            logger.debug("Order type: Transfer (8)")
            return 8

        # Hot Shot (4): Either location outside service area
        # (checked after Transfer since Transfer requires both in area)
        if not pu_in_area or not del_in_area:
            logger.debug(f"Order type: Hot Shot (4) - PU ACI '{pu_aci_upper}' in area: {pu_in_area}, "
                        f"Del ACI '{del_aci_upper}' in area: {del_in_area}")
            return 4

        # From here, both locations are within service area (A-D)

        # Recovery (1): From carrier to non-carrier
        # PU: Branch=N, Carrier=Y
        # Del: Carrier=N (Branch doesn't matter)
        if not pu_branch and pu_carrier and not del_carrier:
            logger.debug("Order type: Recovery (1)")
            return 1

        # Drop (2): To carrier (covers customer→carrier and carrier→carrier)
        # PU: Branch=N, Carrier=Y or N
        # Del: Branch=N, Carrier=Y
        if not pu_branch and not del_branch and del_carrier:
            logger.debug("Order type: Drop (2)")
            return 2

        # Point-to-Point (3): Neither is branch or carrier
        # PU: Branch=N, Carrier=N
        # Del: Branch=N, Carrier=N
        if not pu_branch and not pu_carrier and not del_branch and not del_carrier:
            logger.debug("Order type: Point-to-Point (3)")
            return 3

        # Dock Transfer (5): Branch to Branch
        # PU: Branch=Y (Carrier doesn't matter)
        # Del: Branch=Y (Carrier doesn't matter)
        if pu_branch and del_branch:
            logger.debug("Order type: Dock Transfer (5)")
            return 5

        # Pickup (9): To branch
        # PU: Branch=N, Carrier=N
        # Del: Branch=Y, Carrier=N
        if not pu_branch and not pu_carrier and del_branch and not del_carrier:
            logger.debug("Order type: Pickup (9)")
            return 9

        # Delivery (10): From branch to customer
        # PU: Branch=Y, Carrier=N
        # Del: Branch=N, Carrier=N
        if pu_branch and not pu_carrier and not del_branch and not del_carrier:
            logger.debug("Order type: Delivery (10)")
            return 10

        # Not Established (11): Fallback for unmatched scenarios
        logger.warning(f"Order type: Not Established (11) - "
                      f"PU(branch={pu_branch}, carrier={pu_carrier}, aci='{pu_aci_upper}'), "
                      f"Del(branch={del_branch}, carrier={del_carrier}, aci='{del_aci_upper}')")
        return 11

    def find_or_create_address(
        self,
        address_string: str,
        company_name: str,
        country: str = "USA",
    ) -> float:
        """
        Find an existing address or create a new one.

        This is the main entry point for address resolution with creation fallback.

        Process:
        1. Parse the address string
        2. Search for existing address
        3. If found, return existing FavID
        4. If not found, create new address and return new FavID

        Args:
            address_string: Full address string to find/create
                e.g., "123 Main St, Suite 100, Dallas, TX 75201"
            company_name: Company name to use if creating new address
            country: Country name (default: "United States")

        Returns:
            Address ID (FavID) as float - either existing or newly created

        Raises:
            ValueError: If address cannot be parsed
            OutputExecutionError: If address creation fails
        """
        logger.info(f"Finding or creating address: '{address_string}'")

        # Step 1: Parse the address string
        parsed = self.parse_address_string(address_string)

        if not parsed:
            raise ValueError(f"Could not parse address: '{address_string}'")

        # Step 2: Search for existing address
        existing_id = self.find_address_by_text(
            street=parsed['street'],
            city=parsed['city'],
            state=parsed['state'],
            zip_code=parsed['zip_code'],
        )

        if existing_id is not None:
            logger.info(f"Found existing address with FavID: {existing_id}")
            return existing_id

        # Step 3: Create new address
        logger.info(f"Address not found, creating new address")
        new_id = self.create_address(
            company_name=company_name,
            addr_ln1=parsed['street'],
            city=parsed['city'],
            state=parsed['state'],
            zip_code=parsed['zip_code'],
            country=country,
        )

        return new_id
