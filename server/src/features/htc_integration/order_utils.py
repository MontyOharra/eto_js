"""
HTC Order Utilities

Provides order-related operations for the HTC database:
- Order number generation
- Order record creation
- Order updates
- Order type classification
- Supporting records (dimensions, history, HAWB associations)
"""

import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, Optional, TYPE_CHECKING

from shared.logging import get_logger
from shared.exceptions import OutputExecutionError

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


# ==================== Result Types ====================

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


# Valid ACI zones for local service area
LOCAL_ACI_ZONES = {'A', 'B', 'C', 'D'}


# ==================== Order Utils Class ====================

class HtcOrderUtils:
    """
    Utility class for HTC order operations.

    Provides methods for order number generation, order record creation,
    order updates, and supporting records.
    """

    def __init__(
        self,
        get_connection: Callable[[], Any],
        co_id: int,
        br_id: int,
    ):
        """
        Initialize order utils.

        Args:
            get_connection: Callable that returns the database connection
            co_id: Company ID for HTC queries
            br_id: Branch ID for HTC queries
        """
        self._get_connection = get_connection
        self.CO_ID = co_id
        self.BR_ID = br_id
        self._order_number_lock = threading.Lock()

    # ==================== Order Number Generation ====================

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
                # NOTE: LON is updated AFTER successful order creation via update_lon()
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

    def update_lon(self, order_number: float) -> None:
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

    def create_order_history(
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

    def create_dimension_record(
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

    def create_order_record(
        self,
        order_number: float,
        data: 'PreparedOrderData',
    ) -> None:
        """
        Create the main order record in HTC300_G040_T010A Open Orders.

        This is the core INSERT with all 75 fields. The data parameter should
        be fully populated from Phase 1 (data gathering).

        Args:
            order_number: The reserved order number from generate_next_order_number()
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
                    True,                                # M_PUSpecificYN
                    True,                                # M_DelSpecificYN

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

    # ==================== Order Type Classification ====================

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
        pu_in_area = pu_aci_upper in LOCAL_ACI_ZONES
        del_in_area = del_aci_upper in LOCAL_ACI_ZONES

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

    # ==================== Helper Methods ====================

    def extract_company_from_address(self, address_string: str) -> str:
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

    def parse_datetime_string(self, datetime_str: Optional[str]) -> tuple:
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
