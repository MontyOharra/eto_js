"""
Dim Builder Transform Module
Builds a dimension object from individual components
"""
import logging
from typing import Dict, Any
from pydantic import BaseModel

from shared.types import TransformModule, ModuleMeta, IOShape, IOSideShape, NodeGroup, NodeTypeRule
from features.modules.utils.decorators import register

logger = logging.getLogger(__name__)


# Dimension object structure
# A dim is a dict with: height, length, width, qty, weight, dim_weight (calculated)
DimObject = Dict[str, Any]


class DimBuilderConfig(BaseModel):
    """Configuration for Dim Builder - no config needed"""
    pass


@register
class DimBuilder(TransformModule):
    """
    Dim Builder transform module
    Builds a dimension object from height, length, width, qty, and weight inputs
    """

    # Class metadata
    id = "dim_builder"
    version = "1.0.0"
    title = "Dim Builder"
    description = "Build a dimension object from individual components (H, L, W, qty, weight)"
    category = "Cargo"
    color = "#F97316"  # Orange

    # Configuration model
    ConfigModel = DimBuilderConfig

    @classmethod
    def meta(cls) -> ModuleMeta:
        """Define I/O constraints for this module"""
        return ModuleMeta(
            io_shape=IOShape(
                inputs=IOSideShape(
                    nodes=[
                        NodeGroup(
                            label="height",
                            typing=NodeTypeRule(allowed_types=["float", "int"]),
                            min_count=1,
                            max_count=1
                        ),
                        NodeGroup(
                            label="length",
                            typing=NodeTypeRule(allowed_types=["float", "int"]),
                            min_count=1,
                            max_count=1
                        ),
                        NodeGroup(
                            label="width",
                            typing=NodeTypeRule(allowed_types=["float", "int"]),
                            min_count=1,
                            max_count=1
                        ),
                        NodeGroup(
                            label="qty",
                            typing=NodeTypeRule(allowed_types=["int"]),
                            min_count=1,
                            max_count=1
                        ),
                        NodeGroup(
                            label="weight",
                            typing=NodeTypeRule(allowed_types=["float", "int"]),
                            min_count=1,
                            max_count=1
                        )
                    ]
                ),
                outputs=IOSideShape(
                    nodes=[
                        NodeGroup(
                            label="dim",
                            typing=NodeTypeRule(allowed_types=["dim"]),
                            min_count=1,
                            max_count=1
                        )
                    ]
                )
            )
        )

    def run(self, inputs: Dict[str, Any], cfg: DimBuilderConfig, context: Any, services: Any = None) -> Dict[str, Any]:
        """
        Execute dim object building

        Args:
            inputs: Dictionary with height, length, width, qty, weight inputs
            cfg: Validated configuration (empty for this module)
            context: Execution context with ordered inputs/outputs
            services: Not used for this module

        Returns:
            Dictionary with dim object output
        """
        # Get input values by group index order
        # Group 0: height, Group 1: length, Group 2: width, Group 3: qty, Group 4: weight
        height = 0.0
        length = 0.0
        width = 0.0
        qty = 1
        weight = 0.0

        for input_node in context.inputs:
            node_id = input_node.node_id
            group_index = input_node.group_index
            value = inputs.get(node_id, 0)

            if group_index == 0:  # height
                height = float(value) if value is not None else 0.0
            elif group_index == 1:  # length
                length = float(value) if value is not None else 0.0
            elif group_index == 2:  # width
                width = float(value) if value is not None else 0.0
            elif group_index == 3:  # qty
                qty = int(value) if value is not None else 1
            elif group_index == 4:  # weight
                weight = float(value) if value is not None else 0.0

        # Calculate dim weight: L * W * H / 144 (industry standard formula)
        dim_weight = (length * width * height) / 144.0

        # Build the dim object
        dim_obj: DimObject = {
            "height": height,
            "length": length,
            "width": width,
            "qty": qty,
            "weight": weight,
            "dim_weight": round(dim_weight, 2)
        }

        logger.info(f"Built dim object: {dim_obj}")

        # Get output node ID
        output_node_id = context.outputs[0].node_id

        return {
            output_node_id: dim_obj
        }
