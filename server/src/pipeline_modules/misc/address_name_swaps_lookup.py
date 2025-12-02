"""
Address Lookup Module
Finds address address ID using the Address Name Swaps table
"""
import logging
from typing import Dict, Any
from pydantic import BaseModel, Field

from shared.types import MiscModule, ModuleMeta, IOShape, IOSideShape, NodeGroup, NodeTypeRule
from features.modules.utils.decorators import register

logger = logging.getLogger(__name__)


class AddressNameSwapsLookupConfig(BaseModel):
    """Configuration for Address Lookup"""

    # No configuration needed - uses hardcoded databases
    pass


@register
class AddressNameSwapsLookup(MiscModule):
    """
    Address Lookup module
    Finds address address ID by looking up the address name in the Address Name Swaps table
    """

    # Class metadata
    id = "address_name_swaps_lookup"
    version = "2.0.0"
    title = "Address Name Swaps Lookup"
    description = "Find address address ID using Address Name Swaps table"
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
                            label="address_id",
                            typing=NodeTypeRule(allowed_types=["int", "float"]),
                            min_count=1,
                            max_count=1
                        ),
                        NodeGroup(
                            label="address_found",
                            typing=NodeTypeRule(allowed_types=["bool"]),
                            min_count=1,
                            max_count=1
                        ),
                        NodeGroup(
                            label="actual_address_name",
                            typing=NodeTypeRule(allowed_types=["str"]),
                            min_count=1,
                            max_count=1
                        )
                    ]
                )
            )
        )

    def run(self, inputs: Dict[str, Any], cfg: AddressNameSwapsLookupConfig, context: Any, services: Any = None) -> Dict[str, Any]:
        """
        Execute address lookup using Address Name Swaps table

        Args:
            inputs: Dictionary with address_name input
            cfg: Validated configuration
            context: Execution context with ordered inputs/outputs
            services: DataDatabaseManager for database access

        Returns:
            Dictionary with address_id, address_found, and actual_address_name outputs
        """
        # Validate services
        if services is None:
            raise ValueError("DataDatabaseManager services required for address_lookup")

        # Get input
        input_node_id = list(inputs.keys())[0]
        address_name = inputs[input_node_id]

        # Get output node IDs
        address_id_output = context.outputs[0].node_id
        address_found_output = context.outputs[1].node_id
        actual_name_output = context.outputs[2].node_id

        # Handle None/empty input
        if not address_name:
            logger.warning("Empty address name provided")
            raise ValueError("Address name cannot be empty")

        logger.info(f"Looking up address: '{address_name}'")

        # Get connection to HTC350D_Database (Address Name Swaps table)
        try:
            connection = services.get_connection("htc_350d_db")
        except Exception as e:
            logger.error(f"Failed to get database connection 'htc_350d_db': {e}")
            raise ValueError(
                f"Could not connect to HTC350D database. "
                f"Ensure HTC_350D_DB_CONNECTION_STRING is configured in .env file. Error: {e}"
            )

        # Query Address Name Swaps table for exact match
        sql = """
        SELECT NameSwap_SubNameID, NameSwap_SubName
        FROM [HTC350_G060_T100 Address Name Swaps]
        WHERE NameSwap_GivenName = ? AND NameSwap_Active = True
        """

        logger.debug(f"Executing address lookup query with name: '{address_name}'")

        # Execute query using pyodbc cursor (with context manager)
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, (address_name,))
                row = cursor.fetchone()
        except Exception as e:
            logger.error(f"Database query failed: {e}")
            raise ValueError(f"Database query failed: {e}")

        # Handle no match found
        if row is None:
            logger.error(
                f"Address name '{address_name}' not found in Address Name Swaps table. "
                f"Please add this address to the HTC350_G060_T100 Address Name Swaps table."
            )
            raise ValueError(
                f"Address name '{address_name}' not found in Address Name Swaps table. "
                f"This address must be registered before it can be used."
            )

        # Extract results
        address_id = row[0]  # NameSwap_SubNameID
        actual_name = row[1]  # NameSwap_SubName

        logger.info(
            f"Successfully mapped address '{address_name}' to '{actual_name}' (ID: {address_id})"
        )

        return {
            address_id_output: float(address_id),
            address_found_output: True,
            actual_name_output: actual_name if actual_name else ""
        }
