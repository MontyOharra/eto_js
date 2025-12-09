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
    def validate_config(
        cls,
        cfg: BasicOrderOutputConfig,
        inputs: list[Any],
        outputs: list[Any],
        services: Any = None
    ) -> list[str]:
        """
        Validate BasicOrderOutput configuration.

        Checks XOR constraint on address fields:
        - Exactly one of pickup_address_id or pickup_address_text must be connected
        - Exactly one of delivery_address_id or delivery_address_text must be connected

        Args:
            cfg: Validated config instance
            inputs: List of input pins for this module instance
            outputs: List of output pins for this module instance
            services: Optional services container

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        # Get the io_shape to map group_index -> label
        io_shape = cls.meta().io_shape
        group_labels = [group.label for group in io_shape.inputs.nodes]

        # Build a set of connected input labels based on group_index
        # A pin exists in inputs list = that group has a pin connected
        connected_labels = set()
        for pin in inputs:
            if pin.group_index < len(group_labels):
                connected_labels.add(group_labels[pin.group_index])

        # Check pickup address XOR constraint
        has_pickup_id = "pickup_address_id" in connected_labels
        has_pickup_text = "pickup_address_text" in connected_labels

        if has_pickup_id and has_pickup_text:
            errors.append(
                "Invalid pickup address configuration: both 'pickup_address_id' and 'pickup_address_text' are connected. "
                "Please connect only one - either use an existing address ID or provide address text, not both."
            )
        elif not has_pickup_id and not has_pickup_text:
            errors.append(
                "Missing pickup address: either 'pickup_address_id' or 'pickup_address_text' must be connected."
            )

        # Check delivery address XOR constraint
        has_delivery_id = "delivery_address_id" in connected_labels
        has_delivery_text = "delivery_address_text" in connected_labels

        if has_delivery_id and has_delivery_text:
            errors.append(
                "Invalid delivery address configuration: both 'delivery_address_id' and 'delivery_address_text' are connected. "
                "Please connect only one - either use an existing address ID or provide address text, not both."
            )
        elif not has_delivery_id and not has_delivery_text:
            errors.append(
                "Missing delivery address: either 'delivery_address_id' or 'delivery_address_text' must be connected."
            )

        return errors

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
                        label="pickup_time_start",
                        min_count=1,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["datetime"])
                    ),
                    NodeGroup(
                        label="pickup_time_end",
                        min_count=1,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["datetime"])
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
                        label="delivery_time_start",
                        min_count=1,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["datetime"])
                    ),
                    NodeGroup(
                        label="delivery_time_end",
                        min_count=1,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["datetime"])
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
