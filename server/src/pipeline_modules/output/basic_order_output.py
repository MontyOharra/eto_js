"""
Basic Order Output Module
Pipeline exit point for basic order creation with required and optional fields.
"""
from typing import Dict, Any
from pydantic import BaseModel

from shared.types import OutputModule, ModuleMeta, IOShape, IOSideShape, NodeGroup, NodeTypeRule
from features.modules.utils.decorators import register


class BasicOrderOutputConfig(BaseModel):
    """
    Configuration for basic order output.
    Currently no config options - all data comes from inputs.
    """
    pass


@register
class BasicOrderOutput(OutputModule):
    """
    Basic Order Output Module

    Acts as a pipeline exit point that collects fields for order creation.
    This module does NOT execute side effects directly - it collects data
    that is passed to the OutputExecutionService for processing.

    The service handles:
    - Creating or updating orders based on HAWB existence
    - Resolving addresses (by ID or creating new from text)
    - Transferring PDF attachments to HTC storage
    - Sending confirmation emails

    Required Inputs:
        - customer_id (int): Customer identifier
        - hawb (str): House Air Waybill number
        - pickup_date (date): Pickup date
        - pickup_time_start (time): Pickup window start
        - pickup_time_end (time): Pickup window end
        - pickup_address_id (int, optional*): Existing address ID for pickup
        - pickup_address_text (str, optional*): Full address text for new pickup address
        - delivery_date (date): Delivery date
        - delivery_time_start (time): Delivery window start
        - delivery_time_end (time): Delivery window end
        - delivery_address_id (int, optional*): Existing address ID for delivery
        - delivery_address_text (str, optional*): Full address text for new delivery address

        * For each location, either address_id OR address_text must be provided

    Optional Inputs:
        - mawb (str): Master Air Waybill number
        - pickup_notes (str): Notes for pickup
        - delivery_notes (str): Notes for delivery
        - order_notes (str): General order notes
    """

    id = "basic_order_output"
    version = "1.0.0"
    title = "Basic Order Output"
    description = "Collects fields for basic order creation with pickup and delivery info"
    category = "Output"
    color = "#10B981"  # Green
    ConfigModel = BasicOrderOutputConfig

    @classmethod
    def meta(cls) -> ModuleMeta:
        return ModuleMeta(
            io_shape=IOShape(
                inputs=IOSideShape(nodes=[
                    # ==========================================
                    # REQUIRED FIELDS
                    # ==========================================

                    # Customer
                    NodeGroup(
                        label="customer_id",
                        min_count=1,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["int"])
                    ),

                    # HAWB (required identifier)
                    NodeGroup(
                        label="hawb",
                        min_count=1,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["str"])
                    ),

                    # ==========================================
                    # PICKUP FIELDS
                    # ==========================================

                    NodeGroup(
                        label="pickup_date",
                        min_count=1,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["date"])
                    ),
                    NodeGroup(
                        label="pickup_time_start",
                        min_count=1,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["time"])
                    ),
                    NodeGroup(
                        label="pickup_time_end",
                        min_count=1,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["time"])
                    ),

                    # Pickup address - Option 1: Existing address ID
                    NodeGroup(
                        label="pickup_address_id",
                        min_count=0,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["int"])
                    ),
                    # Pickup address - Option 2: Full address text (will be parsed/created)
                    NodeGroup(
                        label="pickup_address_text",
                        min_count=0,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["str"])
                    ),

                    # ==========================================
                    # DELIVERY FIELDS
                    # ==========================================

                    NodeGroup(
                        label="delivery_date",
                        min_count=1,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["date"])
                    ),
                    NodeGroup(
                        label="delivery_time_start",
                        min_count=1,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["time"])
                    ),
                    NodeGroup(
                        label="delivery_time_end",
                        min_count=1,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["time"])
                    ),

                    # Delivery address - Option 1: Existing address ID
                    NodeGroup(
                        label="delivery_address_id",
                        min_count=0,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["int"])
                    ),
                    # Delivery address - Option 2: Full address text (will be parsed/created)
                    NodeGroup(
                        label="delivery_address_text",
                        min_count=0,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["str"])
                    ),

                    # ==========================================
                    # OPTIONAL FIELDS
                    # ==========================================

                    NodeGroup(
                        label="mawb",
                        min_count=0,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["str"])
                    ),
                    NodeGroup(
                        label="pickup_notes",
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
                    NodeGroup(
                        label="order_notes",
                        min_count=0,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["str"])
                    ),
                ]),
                outputs=IOSideShape(nodes=[])  # No outputs - this is a terminal/exit point
            )
        )

    def run(
        self,
        inputs: Dict[str, Any],
        cfg: BasicOrderOutputConfig,
        context: Any = None,
        services: Any = None
    ) -> Dict[str, Any]:
        """
        Output modules don't execute side effects directly.

        The pipeline execution service collects the inputs to this module
        and passes them to OutputExecutionService for actual processing.

        Returns:
            Empty dict - output modules have no pipeline outputs
        """
        return {}
