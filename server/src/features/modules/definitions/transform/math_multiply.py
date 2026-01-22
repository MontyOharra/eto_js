"""
Math Multiply Transform Module
Multiplies multiple numeric inputs
"""
import logging
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from features.modules.base import BaseModule
from features.modules.registry import register
from shared.types import IOShape, IOSideShape, ModuleMeta, NodeGroup, NodeTypeRule

if TYPE_CHECKING:
    from shared.database.access_connection import AccessConnectionManager

logger = logging.getLogger(__name__)


class MathMultiplyConfig(BaseModel):
    """Configuration for Math Multiply"""

    decimal_places: int | None = Field(
        default=None,
        description="Round result to N decimal places (None = no rounding)",
    )


@register
class MathMultiply(BaseModule):
    """
    Math Multiply transform module
    Multiplies all numeric inputs
    """

    # Class metadata
    identifier = "math_multiply"
    version = "1.0.0"
    title = "Multiply"
    description = "Multiply multiple numbers"
    category = "Math"
    kind = "transform"
    color = "#8B5CF6"  # Purple

    # Configuration model
    ConfigModel = MathMultiplyConfig

    @classmethod
    def meta(cls) -> ModuleMeta:
        """Define I/O constraints for this module"""
        return ModuleMeta(
            io_shape=IOShape(
                inputs=IOSideShape(
                    nodes=[
                        NodeGroup(
                            label="number",
                            typing=NodeTypeRule(allowed_types=["int", "float"]),
                            min_count=2,
                            max_count=None,  # Unlimited inputs
                        )
                    ]
                ),
                outputs=IOSideShape(
                    nodes=[
                        NodeGroup(
                            label="result",
                            typing=NodeTypeRule(allowed_types=["float"]),
                            min_count=1,
                            max_count=1,
                        )
                    ]
                ),
            )
        )

    def run(
        self,
        inputs: dict[str, Any],
        cfg: MathMultiplyConfig,
        context: Any,
        access_conn_manager: "AccessConnectionManager | None" = None,
    ) -> dict[str, Any]:
        """
        Execute multiplication

        Args:
            inputs: Dictionary with numeric inputs
            cfg: Validated configuration
            context: Execution context with ordered inputs/outputs

        Returns:
            Dictionary with product result
        """
        # Get input values in order from context
        values = []
        for input_node in context.inputs:
            node_id = input_node.node_id
            value = inputs.get(node_id, 0)

            # Convert to float
            if value is None:
                value = 0.0
            else:
                value = float(value)

            values.append(value)

        # Multiply all values
        result = 1.0
        for v in values:
            result *= v

        # Apply rounding if configured
        if cfg.decimal_places is not None:
            result = round(result, cfg.decimal_places)

        logger.info(f"Multiplied {len(values)} numbers: {values} = {result}")

        # Get output node ID
        output_node_id = context.outputs[0].node_id

        return {output_node_id: result}
