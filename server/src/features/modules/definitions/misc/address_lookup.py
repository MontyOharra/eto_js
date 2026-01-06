"""
Address Lookup Module
Looks up address ID from the Addresses table using parsed address components
"""
import logging
from typing import Dict, Any, List
from pydantic import BaseModel, Field

from shared.types import ModuleMeta, IOShape, IOSideShape, NodeGroup, NodeTypeRule
from features.modules.registry import register
from features.modules.base import MiscModule

logger = logging.getLogger(__name__)


class AddressLookupConfig(BaseModel):
    """Configuration for address lookup"""
    database: str = Field(
        default="htc_db",
        description="Database connection to use"
    )
    on_multiple_rows: str = Field(
        default="first",
        description="How to handle multiple matching addresses (first/last/error)"
    )
    on_no_rows: str = Field(
        default="error",
        description="How to handle no matching address (error/null)"
    )


@register
class AddressLookup(MiscModule):
    """
    Address Lookup Module

    Searches the Addresses table for a matching address based on parsed components.

    Fixed Inputs (by index):
        0. company_name (str) - Company name
        1. address_line_1 (str) - Street address
        2. city (str) - City name
        3. state (str) - State abbreviation (2 chars)
        4. zip_code (str) - ZIP code

    Fixed Output:
        - address_id (int) - The FavID of the matching address

    Query Strategy:
        Matches on: Company, Address Line 1, City, State, ZIP
        Returns the FavID (address identifier)
    """

    # Class metadata
    id = "address_lookup"
    version = "1.0.0"
    title = "Address Lookup"
    description = "Find address ID from parsed address components"
    category = "Database"
    color = "#EAB308"  # Yellow

    # Configuration model
    ConfigModel = AddressLookupConfig

    @classmethod
    def meta(cls) -> ModuleMeta:
        """Define fixed I/O shape for this module"""
        return ModuleMeta(
            io_shape=IOShape(
                inputs=IOSideShape(
                    nodes=[
                        NodeGroup(
                            label="company_name",
                            min_count=1,
                            max_count=1,
                            typing=NodeTypeRule(allowed_types=["str"])
                        ),
                        NodeGroup(
                            label="address_line_1",
                            min_count=1,
                            max_count=1,
                            typing=NodeTypeRule(allowed_types=["str"])
                        ),
                        NodeGroup(
                            label="city",
                            min_count=1,
                            max_count=1,
                            typing=NodeTypeRule(allowed_types=["str"])
                        ),
                        NodeGroup(
                            label="state",
                            min_count=1,
                            max_count=1,
                            typing=NodeTypeRule(allowed_types=["str"])
                        ),
                        NodeGroup(
                            label="zip_code",
                            min_count=1,
                            max_count=1,
                            typing=NodeTypeRule(allowed_types=["str"])
                        )
                    ]
                ),
                outputs=IOSideShape(
                    nodes=[
                        NodeGroup(
                            label="address_id",
                            min_count=1,
                            max_count=1,
                            typing=NodeTypeRule(allowed_types=["int"])
                        )
                    ]
                )
            )
        )

    @classmethod
    def config_schema(cls) -> Dict[str, Any]:
        """
        Generate config schema with dynamic database connection enum.
        """
        # Get base schema from Pydantic model
        schema = cls.ConfigModel.model_json_schema()

        # Try to inject available database connections
        try:
            from shared.services.service_container import ServiceContainer

            if ServiceContainer.is_initialized():
                access_db_manager = ServiceContainer._access_connection_manager
                if access_db_manager:
                    available_connections = access_db_manager.list_databases()
                else:
                    available_connections = []

                if available_connections:
                    schema['properties']['database']['enum'] = available_connections
                    logger.debug(f"Injected database connections: {available_connections}")

                    # Update default if needed
                    current_default = schema['properties']['database'].get('default')
                    if current_default and current_default not in available_connections:
                        schema['properties']['database']['default'] = available_connections[0]
                else:
                    logger.warning("No database connections available")
            else:
                logger.warning("ServiceContainer not initialized")

        except Exception as e:
            logger.warning(f"Could not inject database connections: {e}")

        return schema

    def run(self, inputs: Dict[str, Any], cfg: AddressLookupConfig, context: Any, services: Any = None) -> Dict[str, Any]:
        """
        Execute address lookup query.

        Args:
            inputs: Dictionary with input values keyed by node_id
            cfg: Configuration (database, on_multiple_rows, on_no_rows)
            context: Execution context with I/O metadata
            services: Service container for database access

        Returns:
            Dictionary with address_id output keyed by node_id
        """
        logger.info(f"[ADDRESS LOOKUP] Starting execution with database: {cfg.database}")

        # Get input pins by group index (not by name, to avoid name dependency)
        # Sort by group_index to ensure correct ordering
        sorted_inputs = sorted(context.inputs, key=lambda pin: pin.group_index)
        sorted_outputs = sorted(context.outputs, key=lambda pin: pin.group_index)

        if len(sorted_inputs) != 5:
            raise RuntimeError(f"Address lookup requires exactly 5 inputs, got {len(sorted_inputs)}")

        if len(sorted_outputs) != 1:
            raise RuntimeError(f"Address lookup requires exactly 1 output, got {len(sorted_outputs)}")

        # Extract input values by index
        company_name_pin = sorted_inputs[0]
        address_line_1_pin = sorted_inputs[1]
        city_pin = sorted_inputs[2]
        state_pin = sorted_inputs[3]
        zip_code_pin = sorted_inputs[4]

        company_name = inputs.get(company_name_pin.node_id)
        address_line_1 = inputs.get(address_line_1_pin.node_id)
        city = inputs.get(city_pin.node_id)
        state = inputs.get(state_pin.node_id)
        zip_code = inputs.get(zip_code_pin.node_id)

        logger.info(f"[ADDRESS LOOKUP] Input values:")
        logger.info(f"  company_name: {company_name}")
        logger.info(f"  address_line_1: {address_line_1}")
        logger.info(f"  city: {city}")
        logger.info(f"  state: {state}")
        logger.info(f"  zip_code: {zip_code}")

        # Hardcoded SQL query
        # Matches on Company, Address Line 1, City, State, ZIP
        sql = """
            SELECT FavID
            FROM [HTC300_G060_T010 Addresses]
            WHERE FavCompany = ?
              AND FavAddrLn1 = ?
              AND FavCity = ?
              AND FavState = ?
              AND FavZip = ?
              AND FavActive = 1
        """

        # Build parameter tuple in the order matching the query
        params = (company_name, address_line_1, city, state, zip_code)

        # Get database connection
        if not services:
            raise RuntimeError("Services container not available - cannot access database")

        try:
            db_connection = services.get_connection(cfg.database)
            logger.info(f"[ADDRESS LOOKUP] Retrieved connection for database: {cfg.database}")
        except Exception as e:
            raise RuntimeError(f"Failed to get database connection '{cfg.database}': {e}")

        # Execute query
        try:
            logger.info("=" * 80)
            logger.info("[ADDRESS LOOKUP] Executing query...")
            logger.info(f"SQL: {sql.strip()}")
            logger.info(f"Params: {params}")
            logger.info("=" * 80)

            with db_connection.cursor() as cursor:
                cursor.execute(sql, params)
                rows = cursor.fetchall()

            logger.info(f"[ADDRESS LOOKUP] Query returned {len(rows)} row(s)")

        except Exception as e:
            logger.error(f"[ADDRESS LOOKUP] Query execution failed: {e}")
            raise RuntimeError(f"Address lookup query failed: {e}")

        # Handle result cardinality
        address_id = None

        if len(rows) == 0:
            # No address found
            if cfg.on_no_rows == "error":
                raise RuntimeError(
                    f"No address found matching: company='{company_name}', "
                    f"address='{address_line_1}', city='{city}', state='{state}', zip='{zip_code}'"
                )
            # Return None
            logger.info("[ADDRESS LOOKUP] No address found, returning None")
            address_id = None

        elif len(rows) > 1:
            # Multiple addresses found
            if cfg.on_multiple_rows == "error":
                raise RuntimeError(
                    f"Multiple addresses ({len(rows)}) found matching: company='{company_name}', "
                    f"address='{address_line_1}', city='{city}', state='{state}', zip='{zip_code}'"
                )
            elif cfg.on_multiple_rows == "first":
                address_id = int(rows[0].FavID)
                logger.info(f"[ADDRESS LOOKUP] Multiple addresses found, using first: {address_id}")
            else:  # "last"
                address_id = int(rows[-1].FavID)
                logger.info(f"[ADDRESS LOOKUP] Multiple addresses found, using last: {address_id}")

        else:
            # Exactly one address found
            address_id = int(rows[0].FavID)
            logger.info(f"[ADDRESS LOOKUP] Found address ID: {address_id}")

        # Return output
        output_pin = sorted_outputs[0]
        outputs = {
            output_pin.node_id: address_id
        }

        logger.info(f"[ADDRESS LOOKUP] Execution complete - returning address_id={address_id}")
        return outputs
