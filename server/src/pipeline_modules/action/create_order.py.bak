"""
Create Order Action Module
Creates an order in the HTC database system based on VBA CreateNewOrder logic
"""
import logging
from typing import Dict, Any
from pydantic import BaseModel, Field
from shared.types import ActionModule, ModuleMeta, IOShape, IOSideShape, NodeGroup, NodeTypeRule
from features.modules.utils.decorators import register

logger = logging.getLogger(__name__)


class CreateOrderConfig(BaseModel):
    """Configuration for create order action"""
    company_id: int = Field(..., description="Company ID (sCoID)")
    branch_id: int = Field(..., description="Branch ID (sBrID)")
    default_agent_id: int = Field(159, description="Default agent ID if not specified")


@register
class CreateOrder(ActionModule):
    """
    Action module that creates an order in the HTC database.

    Based on VBA CreateNewOrder procedure which:
    1. Generates next order number
    2. Creates main order record
    3. Creates dimension record
    4. Creates history record
    5. Optionally creates delivery info if provided
    6. Returns created order number

    Supports optional delivery information - if not provided, creates pickup-only order.
    """

    id = "create_order"
    version = "1.0.0"
    title = "Create Order"
    description = "Creates a new order in the HTC database with pickup and optional delivery information"
    category = "Database"
    color = "#10B981"  # Green

    ConfigModel = CreateOrderConfig

    @classmethod
    def meta(cls) -> ModuleMeta:
        return ModuleMeta(
            io_shape=IOShape(
                inputs=IOSideShape(nodes=[
                    # ===== Required Core Fields =====
                    NodeGroup(
                        label="customer_id",
                        min_count=1,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["int"])
                    ),
                    NodeGroup(
                        label="hawb",
                        min_count=1,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["str"])
                    ),

                    # ===== Optional Waybill Fields =====
                    NodeGroup(
                        label="mawb",
                        min_count=0,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["str"])
                    ),

                    # ===== Required Pickup Information =====
                    NodeGroup(
                        label="pickup_address_id",
                        min_count=1,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["int"])
                    ),
                    NodeGroup(
                        label="pickup_date",
                        min_count=1,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["str"])
                    ),
                    NodeGroup(
                        label="pickup_time_start",
                        min_count=1,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["str"])
                    ),
                    NodeGroup(
                        label="pickup_time_end",
                        min_count=1,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["str"])
                    ),

                    # ===== Optional Pickup Fields =====
                    NodeGroup(
                        label="pickup_notes",
                        min_count=0,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["str"])
                    ),

                    # ===== Optional Delivery Information =====
                    # All delivery fields are optional (min_count=0)
                    # If delivery_address_id is provided, date/times should also be provided
                    NodeGroup(
                        label="delivery_address_id",
                        min_count=0,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["int"])
                    ),
                    NodeGroup(
                        label="delivery_date",
                        min_count=0,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["str"])
                    ),
                    NodeGroup(
                        label="delivery_time_start",
                        min_count=0,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["str"])
                    ),
                    NodeGroup(
                        label="delivery_time_end",
                        min_count=0,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["str"])
                    ),
                    NodeGroup(
                        label="delivery_notes",
                        min_count=0,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["str"])
                    ),

                    # ===== Required Shipment Information =====
                    NodeGroup(
                        label="pieces",
                        min_count=1,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["int"])
                    ),
                    NodeGroup(
                        label="weight",
                        min_count=1,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["int"])
                    ),

                    # ===== Optional Order Fields =====
                    NodeGroup(
                        label="order_notes",
                        min_count=0,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["str"])
                    ),
                ]),
                outputs=IOSideShape(nodes=[
                    # Output the created order number for downstream modules
                    NodeGroup(
                        label="order_number",
                        min_count=1,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["int"])
                    ),
                ])
            )
        )

    def run(self, inputs: Dict[str, Any], cfg: CreateOrderConfig, context: Any = None) -> Dict[str, Any]:
        """
        Execute the create order action.

        This will:
        1. Validate and sanitize all inputs (dates, times, etc.)
        2. Generate next order number
        3. Determine order type based on pickup/delivery addresses
        4. Create order record in HTC300_G040_T010A Open Orders
        5. Create dimension record in HTC300_G040_T012A Open Order Dims
        6. Create history record in HTC300_G040_T030 Orders Update History
        7. Update order number tracking tables
        8. Return created order number

        Args:
            inputs: Dictionary with input values (some may be missing if optional)
            cfg: Configuration with company_id, branch_id, default_agent_id
            context: Execution context with services

        Returns:
            Dictionary with single output: {"order_number": created_order_id}
        """
        # TODO: Implement order creation logic based on VBA CreateNewOrder
        # This is a placeholder that will be implemented later

        logger.info(f"[CREATE ORDER] Would create order with inputs: {inputs}")
        logger.info(f"[CREATE ORDER] Config: company_id={cfg.company_id}, branch_id={cfg.branch_id}")

        # Check which optional fields were provided
        has_delivery = "delivery_address_id" in inputs
        has_mawb = "mawb" in inputs
        has_pickup_notes = "pickup_notes" in inputs
        has_delivery_notes = "delivery_notes" in inputs
        has_order_notes = "order_notes" in inputs

        logger.info(
            f"[CREATE ORDER] Optional fields: "
            f"delivery={has_delivery}, mawb={has_mawb}, "
            f"pickup_notes={has_pickup_notes}, delivery_notes={has_delivery_notes}, "
            f"order_notes={has_order_notes}"
        )

        # Placeholder: Return a mock order number
        # In production, this would be the actual created order number from database
        mock_order_number = 999999

        # Get the output pin node_id from context
        output_pin = context.outputs[0]  # First (and only) output pin

        return {
            output_pin.node_id: mock_order_number
        }
