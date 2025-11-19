"""
Get Order Number Module
Looks up existing order by HAWB (House Air Waybill) in the Orders table
"""
import logging
from typing import Dict, Any
from pydantic import BaseModel, Field

from shared.types import MiscModule, ModuleMeta, IOShape, IOSideShape, NodeGroup, NodeTypeRule
from features.modules.utils.decorators import register

logger = logging.getLogger(__name__)


class GetOrderNumberConfig(BaseModel):
    """Configuration for get order number lookup"""
    database: str = Field(
        default="htc_db",
        description="Database connection to use"
    )
    on_multiple_orders: str = Field(
        default="first",
        description="How to handle multiple matching orders (first/last/error)"
    )


@register
class GetOrderNumber(MiscModule):
    """
    Get Order Number Module

    Searches the Orders table for an existing order with the given HAWB.
    Returns whether an order exists and its order number if found.

    Fixed Inputs (by index):
        0. hawb (str) - House Air Waybill number (typically 8 characters)

    Fixed Outputs (by index):
        0. order_exists (bool) - True if order found, False otherwise
        1. order_number (int) - Order number if found, 0 if not found

    Query Strategy:
        Matches on: M_HAWB field in Orders table
        Returns: m_Orderno (order number)
    """

    # Class metadata
    id = "get_order_number"
    version = "1.0.0"
    title = "Get Order Number"
    description = "Check if order exists for HAWB and return order number"
    category = "Database"
    color = "#EAB308"  # Yellow

    # Configuration model
    ConfigModel = GetOrderNumberConfig

    @classmethod
    def meta(cls) -> ModuleMeta:
        """Define fixed I/O shape for this module"""
        return ModuleMeta(
            io_shape=IOShape(
                inputs=IOSideShape(
                    nodes=[
                        NodeGroup(
                            label="hawb",
                            min_count=1,
                            max_count=1,
                            typing=NodeTypeRule(allowed_types=["str"])
                        )
                    ]
                ),
                outputs=IOSideShape(
                    nodes=[
                        NodeGroup(
                            label="order_exists",
                            min_count=1,
                            max_count=1,
                            typing=NodeTypeRule(allowed_types=["bool"])
                        ),
                        NodeGroup(
                            label="order_number",
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
                data_db_manager = ServiceContainer._data_database_manager
                if data_db_manager:
                    available_connections = data_db_manager.list_databases()
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

    def run(self, inputs: Dict[str, Any], cfg: GetOrderNumberConfig, context: Any, services: Any = None) -> Dict[str, Any]:
        """
        Execute order number lookup query.

        Args:
            inputs: Dictionary with input values keyed by node_id
            cfg: Configuration (database, on_multiple_orders)
            context: Execution context with I/O metadata
            services: Service container for database access

        Returns:
            Dictionary with order_exists (bool) and order_number (int) outputs
        """
        logger.info(f"[GET ORDER NUMBER] Starting execution with database: {cfg.database}")

        # Get input pins by group index
        sorted_inputs = sorted(context.inputs, key=lambda pin: pin.group_index)
        sorted_outputs = sorted(context.outputs, key=lambda pin: pin.group_index)

        if len(sorted_inputs) != 1:
            raise RuntimeError(f"Get order number requires exactly 1 input, got {len(sorted_inputs)}")

        if len(sorted_outputs) != 2:
            raise RuntimeError(f"Get order number requires exactly 2 outputs, got {len(sorted_outputs)}")

        # Extract input value
        hawb_pin = sorted_inputs[0]
        hawb = inputs.get(hawb_pin.node_id)

        logger.info(f"[GET ORDER NUMBER] Input HAWB: {hawb}")

        # Validate HAWB
        if not hawb or not isinstance(hawb, str):
            logger.warning(f"[GET ORDER NUMBER] Invalid HAWB value: {hawb}")
            order_exists_pin = sorted_outputs[0]
            order_number_pin = sorted_outputs[1]
            return {
                order_exists_pin.node_id: False,
                order_number_pin.node_id: 0
            }

        # Hardcoded SQL query - search for HAWB in Orders table
        sql = """
            SELECT m_Orderno
            FROM [HTC300_G040_T010A Open Orders]
            WHERE M_HAWB = ?
        """

        # Get database connection
        if not services:
            raise RuntimeError("Services container not available - cannot access database")

        try:
            db_connection = services.get_connection(cfg.database)
            logger.info(f"[GET ORDER NUMBER] Retrieved connection for database: {cfg.database}")
        except Exception as e:
            raise RuntimeError(f"Failed to get database connection '{cfg.database}': {e}")

        # Execute query
        try:
            logger.info("=" * 80)
            logger.info("[GET ORDER NUMBER] Executing query...")
            logger.info(f"SQL: {sql.strip()}")
            logger.info(f"HAWB: {hawb}")
            logger.info("=" * 80)

            with db_connection.cursor() as cursor:
                cursor.execute(sql, (hawb,))
                rows = cursor.fetchall()

            logger.info(f"[GET ORDER NUMBER] Query returned {len(rows)} row(s)")

        except Exception as e:
            logger.error(f"[GET ORDER NUMBER] Query execution failed: {e}")
            raise RuntimeError(f"Order number lookup query failed: {e}")

        # Handle result cardinality
        order_exists = False
        order_number = 0

        if len(rows) == 0:
            # No order found
            logger.info(f"[GET ORDER NUMBER] No order found for HAWB: {hawb}")
            order_exists = False
            order_number = 0

        elif len(rows) > 1:
            # Multiple orders found - handle based on config
            if cfg.on_multiple_orders == "error":
                raise RuntimeError(
                    f"Multiple orders ({len(rows)}) found for HAWB: {hawb}"
                )
            elif cfg.on_multiple_orders == "first":
                order_number = int(rows[0].m_Orderno)
                order_exists = True
                logger.info(f"[GET ORDER NUMBER] Multiple orders found, using first: {order_number}")
            else:  # "last"
                order_number = int(rows[-1].m_Orderno)
                order_exists = True
                logger.info(f"[GET ORDER NUMBER] Multiple orders found, using last: {order_number}")

        else:
            # Exactly one order found
            order_number = int(rows[0].m_Orderno)
            order_exists = True
            logger.info(f"[GET ORDER NUMBER] Found order number: {order_number}")

        # Return outputs
        order_exists_pin = sorted_outputs[0]
        order_number_pin = sorted_outputs[1]

        outputs = {
            order_exists_pin.node_id: order_exists,
            order_number_pin.node_id: order_number
        }

        logger.info(f"[GET ORDER NUMBER] Execution complete - order_exists={order_exists}, order_number={order_number}")
        return outputs
