"""
Next Order Number Generator Module
Generates the next available order number using the same logic as the legacy VBA system
"""
import logging
from typing import Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

from shared.types import MiscModule, ModuleMeta, IOShape, IOSideShape, NodeGroup, NodeTypeRule
from features.modules.utils.decorators import register

logger = logging.getLogger(__name__)


class NextOrderNumberConfig(BaseModel):
    """Configuration for Next Order Number Generator"""
    database: str = Field(
        default="htc_db",
        description="Database name containing order tables (HTC300_Data)"
    )


@register
class NextOrderNumber(MiscModule):
    """
    Next Order Number Generator

    Generates the next available order number by:
    1. Reading last assigned order number from LON table
    2. Checking Orders In Work (OIW) table for conflicts
    3. Incrementing until finding an unused number
    4. Updating both LON and OIW tables
    5. Returning the new order number

    Replicates legacy VBA NextOrderNo function with hardcoded CoID=1, BrID=1
    """

    # Class metadata
    id = "next_order_number"
    version = "1.0.0"
    title = "Next Order Number"
    description = "Generate next available order number (legacy VBA logic)"
    category = "Generator"
    color = "#10B981"  # Green

    # Configuration model
    ConfigModel = NextOrderNumberConfig

    @classmethod
    def config_schema(cls) -> Dict[str, Any]:
        """
        Generate config schema with dynamic database connection enum.

        Injects available database connections from ServiceContainer
        into the 'database' field enum so the frontend renders a dropdown.
        """
        # Get base schema from Pydantic model
        schema = cls.ConfigModel.model_json_schema()

        # Try to inject available database connections
        try:
            from shared.services.service_container import ServiceContainer

            if ServiceContainer.is_initialized():
                # Get available business database connections (excludes 'main' system DB)
                data_db_manager = ServiceContainer._data_database_manager
                if data_db_manager:
                    available_connections = data_db_manager.list_databases()
                else:
                    available_connections = []

                if available_connections:
                    # Inject as enum for dropdown rendering
                    schema['properties']['database']['enum'] = available_connections
                    logger.debug(f"Injected database connections into schema: {available_connections}")

                    # Update default if current default not in available connections
                    current_default = schema['properties']['database'].get('default')
                    if current_default and current_default not in available_connections:
                        # Use first available connection as fallback
                        schema['properties']['database']['default'] = available_connections[0]
                        logger.debug(f"Updated default database to: {available_connections[0]}")
                else:
                    logger.warning("No database connections available in ServiceContainer")
            else:
                logger.warning("ServiceContainer not initialized yet - cannot inject database connections")

        except Exception as e:
            logger.warning(f"Could not inject database connections into schema: {e}")
            # Schema will still work, just won't have enum (will be text input instead)

        return schema

    @classmethod
    def meta(cls) -> ModuleMeta:
        """Define I/O constraints for this module"""
        return ModuleMeta(
            io_shape=IOShape(
                inputs=IOSideShape(),  # No inputs
                outputs=IOSideShape(
                    nodes=[
                        NodeGroup(
                            label="order_number",
                            min_count=1,
                            max_count=1,
                            typing=NodeTypeRule(allowed_types=["float", "int"])
                        )
                    ]
                )
            )
        )

    def run(self, inputs: Dict[str, Any], cfg: NextOrderNumberConfig, context: Any, services: Any = None) -> Dict[str, Any]:
        """
        Execute order number generation

        Args:
            inputs: Dictionary (empty, no inputs)
            cfg: Validated configuration with database name
            context: Execution context with output node info
            services: DatabaseManager for database access

        Returns:
            Dictionary with new order number
        """
        # Validate services
        if services is None:
            raise ValueError("DatabaseManager services required for next_order_number")

        # Hardcoded values (always 1, 1 for local system)
        CO_ID = 1
        BR_ID = 1

        # Get output node ID
        output_node_id = context.outputs[0].node_id

        # Get database connection
        connection = services.get_connection(cfg.database)

        # Step 1: Get last order number assigned (LON)
        with connection.cursor() as cursor:
            # Query LON table for CoID=1, BrID=1
            lon_query = """
                SELECT [lon_orderno]
                FROM [HTC300_G040_T000 Last OrderNo Assigned]
                WHERE [lon_coid] = ? AND [lon_brid] = ?
            """
            cursor.execute(lon_query, (CO_ID, BR_ID))
            lon_row = cursor.fetchone()

            if lon_row is None:
                # First order ever - initialize LON table
                cursor.execute("""
                    INSERT INTO [HTC300_G040_T000 Last OrderNo Assigned]
                    ([lon_coid], [lon_brid], [lon_orderno])
                    VALUES (?, ?, ?)
                """, (CO_ID, BR_ID, 1))
                # Commit happens automatically when context exits
                new_order_no = 1.0
            else:
                # Increment last order number
                new_order_no = float(lon_row[0]) + 1

        # Step 2: Check Orders In Work (OIW) and find unused number
        # Use read-only cursor for checking
        oiw_found = True
        while oiw_found:
            with connection.cursor() as cursor:
                # Query OIW table to check if this order number exists
                oiw_query = """
                    SELECT [oiw_coid], [oiw_brid], [oiw_orderno]
                    FROM [HTC300_G040_T005 Orders In Work]
                    WHERE [oiw_coid] = ? AND [oiw_brid] = ? AND [oiw_orderno] = ?
                """
                cursor.execute(oiw_query, (CO_ID, BR_ID, new_order_no))
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
            """, (new_order_no, CO_ID, BR_ID))

            # Add new order to OIW table
            current_time = datetime.now()
            current_user = "SYSTEM"  # Could be enhanced to get actual user

            cursor.execute("""
                INSERT INTO [HTC300_G040_T005 Orders In Work]
                ([oiw_coid], [oiw_brid], [oiw_orderno], [oiw_when], [oiw_user])
                VALUES (?, ?, ?, ?, ?)
            """, (CO_ID, BR_ID, new_order_no, current_time, current_user))
            # Commit happens automatically when context exits

        return {output_node_id: new_order_no}
