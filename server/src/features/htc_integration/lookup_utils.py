"""
HTC Lookup Utilities

Provides lookup operations for HTC database entities:
- Customer lookups
- Address info lookups
- ACI zone lookups
- Order lookups
"""

import json
from dataclasses import dataclass
from typing import Any, Callable, List, Optional

from shared.logging import get_logger

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


@dataclass
class HtcOrderFields:
    """
    All editable fields of an HTC order for comparison with pending updates.

    These fields map to the pending_orders/pending_updates field structure,
    allowing the frontend to show current HTC values vs proposed changes.
    """
    order_number: float
    customer_id: int
    hawb: str

    # Address IDs for comparison (comparing IDs is more reliable than string comparison)
    pickup_address_id: Optional[float]    # M_PUID - FavID of pickup address
    delivery_address_id: Optional[float]  # M_DelID - FavID of delivery address

    # Fields that can be updated (matching pending order field names)
    pickup_company_name: Optional[str]
    pickup_address: Optional[str]
    pickup_time_start: Optional[str]  # Combined date + time as ISO string
    pickup_time_end: Optional[str]    # Combined date + time as ISO string
    delivery_company_name: Optional[str]
    delivery_address: Optional[str]
    delivery_time_start: Optional[str]  # Combined date + time as ISO string
    delivery_time_end: Optional[str]    # Combined date + time as ISO string
    mawb: Optional[str]
    pickup_notes: Optional[str]
    delivery_notes: Optional[str]
    order_notes: Optional[str]
    dims: Optional[str]  # JSON string of dim objects from dims table


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


# ==================== Lookup Utils Class ====================

class HtcLookupUtils:
    """
    Utility class for HTC database lookups.

    Provides methods for looking up customers, addresses, ACI zones, and orders.
    """

    def __init__(
        self,
        get_connection: Callable[[], Any],
        co_id: int,
        br_id: int,
    ):
        """
        Initialize lookup utils.

        Args:
            get_connection: Callable that returns the database connection
            co_id: Company ID for HTC queries
            br_id: Branch ID for HTC queries
        """
        self._get_connection = get_connection
        self.CO_ID = co_id
        self.BR_ID = br_id

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
            The HTC order number (float) if found, None if not found.
            If multiple orders exist, returns the first one (use count_orders_by_customer_and_hawb
            to check for duplicates first).
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
                params = (customer_id, hawb, self.CO_ID, self.BR_ID)
                logger.info(f"HTC lookup query params: customer_id={customer_id} (type={type(customer_id).__name__}), hawb='{hawb}' (type={type(hawb).__name__}), CO_ID={self.CO_ID}, BR_ID={self.BR_ID}")
                cursor.execute(query, params)
                row = cursor.fetchone()

                if row is None:
                    logger.info(f"No order found for customer {customer_id}, HAWB '{hawb}'")
                    return None

                order_no = float(row[0]) if row[0] is not None else None
                logger.info(f"Found order {order_no} for customer {customer_id}, HAWB '{hawb}'")
                return order_no

        except Exception as e:
            logger.error(f"Failed to lookup order for customer {customer_id}, HAWB {hawb}: {e}")
            raise

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
        connection = self._get_connection()

        try:
            with connection.cursor() as cursor:
                query = """
                    SELECT COUNT(*)
                    FROM [HTC300_G040_T010A Open Orders]
                    WHERE [M_CustomerID] = ?
                      AND [M_HAWB] = ?
                      AND [M_CoID] = ?
                      AND [M_BrID] = ?
                """
                params = (customer_id, hawb, self.CO_ID, self.BR_ID)
                cursor.execute(query, params)
                row = cursor.fetchone()

                count = int(row[0]) if row and row[0] is not None else 0
                logger.info(f"HTC duplicate check: Found {count} order(s) for customer {customer_id}, HAWB '{hawb}'")
                return count

        except Exception as e:
            logger.error(f"Failed to count orders for customer {customer_id}, HAWB {hawb}: {e}")
            raise

    def get_order_address_id(
        self,
        order_number: float,
        is_pickup: bool = True,
    ) -> Optional[float]:
        """
        Get the address ID (M_PUID or M_DelID) from an existing order.

        Args:
            order_number: The HTC order number
            is_pickup: True to get pickup address ID, False for delivery

        Returns:
            The address FavID, or None if order not found
        """
        connection = self._get_connection()
        column = "M_PUID" if is_pickup else "M_DelID"

        try:
            with connection.cursor() as cursor:
                query = f"""
                    SELECT [{column}]
                    FROM [HTC300_G040_T010A Open Orders]
                    WHERE [M_OrderNo] = ?
                      AND [M_CoID] = ?
                      AND [M_BrID] = ?
                """
                cursor.execute(query, (order_number, self.CO_ID, self.BR_ID))
                row = cursor.fetchone()

                if row and row[0] is not None:
                    return float(row[0])
                return None

        except Exception as e:
            logger.error(f"Failed to get address ID for order {order_number}: {e}")
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

    def get_default_agent_id(self, customer_id: int) -> Optional[int]:
        """
        Get the default agent ID for a customer.

        Looks up the agent with agent_default=True for the given customer.

        Args:
            customer_id: The customer ID to look up the default agent for

        Returns:
            Agent ID if a default agent is found, None otherwise
        """
        connection = self._get_connection()

        try:
            with connection.cursor() as cursor:
                query = """
                    SELECT [Agent_ID]
                    FROM [HTC300_G080_T010 Agents]
                    WHERE [Agent_Customer_ID] = ? AND [agent_default] = True
                """
                cursor.execute(query, (customer_id,))
                row = cursor.fetchone()

                if row is None:
                    logger.debug(f"No default agent found for customer {customer_id}")
                    return None

                agent_id = int(row[0])
                logger.debug(f"Found default agent {agent_id} for customer {customer_id}")
                return agent_id

        except Exception as e:
            logger.error(f"Failed to get default agent for customer {customer_id}: {e}")
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

    def get_order_fields(self, order_number: float) -> Optional[HtcOrderFields]:
        """
        Get all editable fields of an HTC order for comparison with pending updates.

        Retrieves the current field values from the Open Orders table and the
        dimensions table, returning them in a structure that matches the
        pending order field names.

        Args:
            order_number: The HTC order number

        Returns:
            HtcOrderFields if found, None if not found
        """
        connection = self._get_connection()

        try:
            # Query order fields from Open Orders table
            with connection.cursor() as cursor:
                query = """
                    SELECT
                        [M_OrderNo],
                        [M_CustomerID],
                        [M_HAWB],
                        [M_PUID],
                        [M_PUCo],
                        [M_PULocn],
                        [M_PUDate],
                        [M_PUTimeStart],
                        [M_PUTimeEnd],
                        [M_DelID],
                        [M_DelCo],
                        [M_DelLocn],
                        [M_DelDate],
                        [M_DelTimeStart],
                        [M_DelTimeEnd],
                        [M_MAWB],
                        [M_PUNotes],
                        [M_DelNotes],
                        [M_OrderNotes]
                    FROM [HTC300_G040_T010A Open Orders]
                    WHERE [M_OrderNo] = ?
                      AND [M_CoID] = ?
                      AND [M_BrID] = ?
                """
                cursor.execute(query, (order_number, self.CO_ID, self.BR_ID))
                order_row = cursor.fetchone()

                if order_row is None:
                    logger.debug(f"Order {order_number} not found")
                    return None

            # Helper to combine date and time into ISO format
            def combine_datetime(date_val, time_val) -> Optional[str]:
                """Combine date and time fields into ISO datetime string."""
                if not date_val:
                    return None

                # Date could be a datetime object or string
                if hasattr(date_val, 'strftime'):
                    date_str = date_val.strftime("%Y-%m-%d")
                else:
                    date_str = str(date_val).strip()
                    # Convert MM/DD/YYYY to YYYY-MM-DD if needed
                    if '/' in date_str:
                        parts = date_str.split('/')
                        if len(parts) == 3:
                            date_str = f"{parts[2]}-{parts[0].zfill(2)}-{parts[1].zfill(2)}"

                # Time could be a time object or string
                if time_val:
                    if hasattr(time_val, 'strftime'):
                        time_str = time_val.strftime("%H:%M")
                    else:
                        time_str = str(time_val).strip()
                        # Handle HH:MM:SS format
                        if len(time_str) > 5:
                            time_str = time_str[:5]
                else:
                    time_str = "00:00"

                return f"{date_str}T{time_str}:00"

            # Query dims from the dims table
            dims_json: Optional[str] = None
            with connection.cursor() as cursor:
                dims_query = """
                    SELECT
                        [OD_UnitHeight],
                        [OD_UnitLength],
                        [OD_UnitWidth],
                        [OD_UnitQty],
                        [OD_UnitWeight],
                        [OD_UnitDimWeight]
                    FROM [HTC300_G040_T012A Open Order Dims]
                    WHERE [OD_OrderNo] = ?
                      AND [OD_CoID] = ?
                      AND [OD_BrID] = ?
                    ORDER BY [OD_DimID]
                """
                cursor.execute(dims_query, (order_number, self.CO_ID, self.BR_ID))
                dims_rows = cursor.fetchall()

                if dims_rows:
                    dims_list: List[dict] = []
                    for dim_row in dims_rows:
                        dims_list.append({
                            "height": float(dim_row[0]) if dim_row[0] is not None else 0,
                            "length": float(dim_row[1]) if dim_row[1] is not None else 0,
                            "width": float(dim_row[2]) if dim_row[2] is not None else 0,
                            "qty": int(dim_row[3]) if dim_row[3] is not None else 1,
                            "weight": float(dim_row[4]) if dim_row[4] is not None else 0,
                            "dim_weight": float(dim_row[5]) if dim_row[5] is not None else 0,
                        })
                    dims_json = json.dumps(dims_list)
                    logger.debug(f"Found {len(dims_list)} dims for order {order_number}")

            return HtcOrderFields(
                order_number=float(order_row[0]),
                customer_id=int(order_row[1]),
                hawb=str(order_row[2]) if order_row[2] else "",
                pickup_address_id=float(order_row[3]) if order_row[3] is not None else None,
                pickup_company_name=str(order_row[4]) if order_row[4] else None,
                pickup_address=str(order_row[5]) if order_row[5] else None,
                pickup_time_start=combine_datetime(order_row[6], order_row[7]),
                pickup_time_end=combine_datetime(order_row[6], order_row[8]),
                delivery_address_id=float(order_row[9]) if order_row[9] is not None else None,
                delivery_company_name=str(order_row[10]) if order_row[10] else None,
                delivery_address=str(order_row[11]) if order_row[11] else None,
                delivery_time_start=combine_datetime(order_row[12], order_row[13]),
                delivery_time_end=combine_datetime(order_row[12], order_row[14]),
                mawb=str(order_row[15]) if order_row[15] else None,
                pickup_notes=str(order_row[16]) if order_row[16] else None,
                delivery_notes=str(order_row[17]) if order_row[17] else None,
                order_notes=str(order_row[18]) if order_row[18] else None,
                dims=dims_json,
            )

        except Exception as e:
            logger.error(f"Failed to get order fields for {order_number}: {e}")
            raise
