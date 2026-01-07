"""
Address Lookup Module
Finds address location name and full address string using the Address Name Swaps table
"""
import logging
from typing import Dict, Any
from pydantic import BaseModel, Field

from shared.types import ModuleMeta, IOShape, IOSideShape, NodeGroup, NodeTypeRule
from features.modules.registry import register
from features.modules.base import MiscModule

logger = logging.getLogger(__name__)


class AddressNameSwapsLookupConfig(BaseModel):
    """Configuration for Address Lookup"""

    # No configuration needed - uses hardcoded databases
    pass


@register
class AddressNameSwapsLookup(MiscModule):
    """
    Address Lookup module
    Finds address location name and full address string by looking up
    the address name in the Address Name Swaps table, then fetching
    the address details from the Addresses table.
    """

    # Class metadata
    identifier = "address_name_swaps_lookup"
    version = "3.0.0"
    title = "Address Name Swaps Lookup"
    description = "Find address location name and full address using Address Name Swaps table"
    category = "Database"
    color = "#EAB308"  # Yellow

    # Configuration model
    ConfigModel = AddressNameSwapsLookupConfig

    @classmethod
    def meta(cls) -> ModuleMeta:
        """Define I/O constraints for this module"""
        return ModuleMeta(
            io_shape=IOShape(
                inputs=IOSideShape(
                    nodes=[
                        NodeGroup(
                            label="address_name",
                            typing=NodeTypeRule(allowed_types=["str"]),
                            min_count=1,
                            max_count=1
                        )
                    ]
                ),
                outputs=IOSideShape(
                    nodes=[
                        NodeGroup(
                            label="location_name",
                            typing=NodeTypeRule(allowed_types=["str"]),
                            min_count=1,
                            max_count=1
                        ),
                        NodeGroup(
                            label="address_string",
                            typing=NodeTypeRule(allowed_types=["str"]),
                            min_count=1,
                            max_count=1
                        ),
                        NodeGroup(
                            label="address_found",
                            typing=NodeTypeRule(allowed_types=["bool"]),
                            min_count=1,
                            max_count=1
                        )
                    ]
                )
            )
        )

    def run(self, inputs: Dict[str, Any], cfg: AddressNameSwapsLookupConfig, context: Any, services: Any = None) -> Dict[str, Any]:
        """
        Execute address lookup using Address Name Swaps table, then fetch address details.

        Args:
            inputs: Dictionary with address_name input
            cfg: Validated configuration
            context: Execution context with ordered inputs/outputs
            services: AccessConnectionManager for database access

        Returns:
            Dictionary with location_name, address_string, and address_found outputs
        """
        # Validate services
        if services is None:
            raise ValueError("AccessConnectionManager services required for address_lookup")

        # Get input
        input_node_id = list(inputs.keys())[0]
        address_name = inputs[input_node_id]

        # Get output node IDs
        location_name_output = context.outputs[0].node_id
        address_string_output = context.outputs[1].node_id
        address_found_output = context.outputs[2].node_id

        # Handle None/empty input
        if not address_name:
            logger.warning("Empty address name provided")
            raise ValueError("Address name cannot be empty")

        logger.info(f"Looking up address: '{address_name}'")

        # Get connection to HTC350D_Database (Address Name Swaps table)
        try:
            connection_350d = services.get_connection("htc_350d")
        except Exception as e:
            logger.error(f"Failed to get database connection 'htc_350d': {e}")
            raise ValueError(
                f"Could not connect to HTC350D database. "
                f"Ensure HTC_350D_CONNECTION_STRING is configured in .env file. Error: {e}"
            )

        # Step 1: Query Address Name Swaps table for exact match
        sql_name_swap = """
        SELECT NameSwap_SubNameID, NameSwap_SubName
        FROM [HTC350_G060_T100 Address Name Swaps]
        WHERE NameSwap_GivenName = ? AND NameSwap_Active = True
        """

        logger.debug(f"Executing address name swap lookup with name: '{address_name}'")

        try:
            with connection_350d.cursor() as cursor:
                cursor.execute(sql_name_swap, (address_name,))
                row = cursor.fetchone()
        except Exception as e:
            logger.error(f"Address Name Swaps query failed: {e}")
            raise ValueError(f"Address Name Swaps query failed: {e}")

        # Handle no match found in Name Swaps
        if row is None:
            logger.error(
                f"Address name '{address_name}' not found in Address Name Swaps table. "
                f"Please add this address to the HTC350_G060_T100 Address Name Swaps table."
            )
            raise ValueError(
                f"Address name '{address_name}' not found in Address Name Swaps table. "
                f"This address must be registered before it can be used."
            )

        address_id = row[0]  # NameSwap_SubNameID (FavID in Addresses table)
        logger.debug(f"Found address ID {address_id} for name '{address_name}'")

        # Step 2: Get connection to HTC300 database (Addresses table)
        try:
            connection_300 = services.get_connection("htc_300")
        except Exception as e:
            logger.error(f"Failed to get database connection 'htc_300': {e}")
            raise ValueError(
                f"Could not connect to HTC300 database. "
                f"Ensure HTC_300_CONNECTION_STRING is configured in .env file. Error: {e}"
            )

        # Step 3: Query Addresses table for full address details
        # Using CoID=1 and BrID=1 as per HtcIntegrationService convention
        sql_address = """
        SELECT
            [FavLocnName],
            [FavAddrLn1],
            [FavAddrLn2],
            [FavCity],
            [FavState],
            [FavZip],
            [FavCountry]
        FROM [HTC300_G060_T010 Addresses]
        WHERE [FavID] = ?
          AND [FavCoID] = 1
          AND [FavBrID] = 1
        """

        logger.debug(f"Executing address details lookup for ID: {address_id}")

        try:
            with connection_300.cursor() as cursor:
                cursor.execute(sql_address, (address_id,))
                addr_row = cursor.fetchone()
        except Exception as e:
            logger.error(f"Address details query failed: {e}")
            raise ValueError(f"Address details query failed: {e}")

        # Handle address not found in Addresses table
        if addr_row is None:
            logger.error(
                f"Address ID {address_id} not found in Addresses table. "
                f"The Address Name Swaps entry may reference an invalid address."
            )
            raise ValueError(
                f"Address ID {address_id} not found in Addresses table. "
                f"Please verify the Address Name Swaps configuration."
            )

        # Extract address details
        locn_name = str(addr_row[0]) if addr_row[0] else ""
        addr_ln1 = str(addr_row[1]) if addr_row[1] else ""
        addr_ln2 = str(addr_row[2]) if addr_row[2] else ""
        city = str(addr_row[3]) if addr_row[3] else ""
        state = str(addr_row[4]) if addr_row[4] else ""
        zip_code = str(addr_row[5]) if addr_row[5] else ""
        country = str(addr_row[6]) if addr_row[6] else ""

        # Build formatted address string: "{AddrLn1}, {AddrLn2}, {City}, {State} {Zip}, {Country}"
        # Omit AddrLn2 if empty
        address_parts = [addr_ln1]
        if addr_ln2:
            address_parts.append(addr_ln2)
        address_parts.append(city)
        # Combine state and zip: "TX 75201"
        state_zip = f"{state} {zip_code}".strip()
        if state_zip:
            address_parts.append(state_zip)
        address_parts.append(country)
        address_string = ", ".join(part for part in address_parts if part)

        logger.info(
            f"Successfully resolved address '{address_name}' -> "
            f"location_name='{locn_name}', address='{address_string}'"
        )

        return {
            location_name_output: locn_name,
            address_string_output: address_string,
            address_found_output: True
        }
