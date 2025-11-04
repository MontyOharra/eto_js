"""
Create HTC Order Action Module
Creates an order in the HTC Access database
"""
import logging
from typing import Dict, Any
from pydantic import BaseModel

from shared.types import ActionModule, ModuleMeta, IOShape, IOSideShape, NodeGroup, NodeTypeRule
from features.modules.utils.decorators import register

logger = logging.getLogger(__name__)


class CreateHtcOrderConfig(BaseModel):
    """Configuration for create HTC order action - no config for now"""
    pass


@register
class CreateHtcOrder(ActionModule):
    """
    Action module that creates an order in the HTC Access database.

    Creates a record in the "orders" table with:
    - hawb (required)
    - pickup_address (required)
    - delivery_address (optional)

    Returns the created order_id.
    """

    id = "create_htc_order"
    version = "1.0.0"
    title = "Create HTC Order"
    description = "Creates a new order in the HTC Access database"
    category = "Database"
    color = "#10B981"  # Green

    ConfigModel = CreateHtcOrderConfig

    @classmethod
    def meta(cls) -> ModuleMeta:
        return ModuleMeta(
            io_shape=IOShape(
                inputs=IOSideShape(nodes=[
                    # Required fields
                    NodeGroup(
                        label="hawb",
                        min_count=1,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["str"])
                    ),
                    NodeGroup(
                        label="pickup_address",
                        min_count=1,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["str"])
                    ),

                    # Optional delivery address
                    NodeGroup(
                        label="delivery_address",
                        min_count=0,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["str"])
                    ),
                ]),
                outputs=IOSideShape(nodes=[
                    # Output the created order ID
                    NodeGroup(
                        label="order_id",
                        min_count=1,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["int"])
                    ),
                ])
            )
        )

    def run(self, inputs: Dict[str, Any], cfg: CreateHtcOrderConfig, context: Any = None) -> Dict[str, Any]:
        """
        Execute the create HTC order action.

        Args:
            inputs: Dictionary with input values (hawb, pickup_address, optional delivery_address)
            cfg: Configuration (empty for now)
            context: Execution context with services

        Returns:
            Dictionary with single output: {"order_id": created_order_id}
        """
        if not context or not context.services:
            raise RuntimeError("CreateHtcOrder requires service container access")

        # Get input values by matching context input nodes to inputs dict
        hawb_input = next(node for node in context.inputs if node.label == "hawb")
        pickup_input = next(node for node in context.inputs if node.label == "pickup_address")

        hawb = inputs[hawb_input.node_id]
        pickup_address = inputs[pickup_input.node_id]

        # Check for optional delivery address
        delivery_address = None
        delivery_input = next((node for node in context.inputs if node.label == "delivery_address"), None)
        if delivery_input and delivery_input.node_id in inputs:
            delivery_address = inputs[delivery_input.node_id]

        logger.info(f"[CREATE HTC ORDER] Creating order with HAWB: {hawb}")
        logger.info(f"[CREATE HTC ORDER] Pickup: {pickup_address}")
        if delivery_address:
            logger.info(f"[CREATE HTC ORDER] Delivery: {delivery_address}")
        else:
            logger.info(f"[CREATE HTC ORDER] No delivery address (pickup only)")

        # Get the HTC database connection
        try:
            htc_db = context.services.get_connection('htc_db')
            logger.info("[CREATE HTC ORDER] Successfully accessed htc_db connection")
        except ValueError as e:
            logger.error(f"[CREATE HTC ORDER] Failed to access htc_db: {e}")
            raise RuntimeError(
                "HTC database not configured. "
                "Set HTC_DB_CONNECTION_STRING in .env file to enable order creation."
            ) from e

        # Create order in database
        try:
            with htc_db.cursor() as cursor:
                logger.info("[CREATE HTC ORDER] Executing INSERT into orders table...")

                # Insert order record
                cursor.execute(
                    """
                    INSERT INTO orders (hawb, pickup_address, delivery_address)
                    VALUES (?, ?, ?)
                    """,
                    (hawb, pickup_address, delivery_address)
                )

                # Get the auto-generated order_id
                cursor.execute("SELECT @@IDENTITY")
                order_id = cursor.fetchone()[0]

                logger.info(f"[CREATE HTC ORDER] Order created successfully with ID: {order_id}")

        except Exception as e:
            logger.error(f"[CREATE HTC ORDER] Database operation failed: {e}", exc_info=True)
            raise RuntimeError(f"Failed to create HTC order: {e}") from e

        # Get output node and return order_id
        output_pin = context.outputs[0]

        return {
            output_pin.node_id: int(order_id)
        }
