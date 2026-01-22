"""
Math Divide Transform Module
Divides multiple numeric inputs in order
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


class MathDivideConfig(BaseModel):
    """Configuration for Math Divide"""

    decimal_places: int | None = Field(
        default=None,
        description="Round result to N decimal places (None = no rounding)",
    )


@register
class MathDivide(BaseModule):
    """
    Math Divide transform module
    Divides inputs in order: a / b / c / ...
    """

    # Class metadata
    identifier = "math_divide"
    version = "1.0.0"
    title = "Divide"
    description = "Divide numbers in order"
    category = "Math"
    kind = "transform"
    color = "#8B5CF6"  # Purple

    # Configuration model
    ConfigModel = MathDivideConfig

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
        cfg: MathDivideConfig,
        context: Any,
        access_conn_manager: "AccessConnectionManager | None" = None,
    ) -> dict[str, Any]:
        """
        Execute division

        Args:
            inputs: Dictionary with numeric inputs
            cfg: Validated configuration
            context: Execution context with ordered inputs/outputs

        Returns:
            Dictionary with division result

        Raises:
            ValueError: If division by zero is attempted
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

        # Divide in order: a / b / c / ...
        result = values[0]
        for i, v in enumerate(values[1:], start=1):
            if v == 0:
                raise ValueError(f"Division by zero: cannot divide by input #{i + 1} (value: 0)")
            result /= v

        # Apply rounding if configured
        if cfg.decimal_places is not None:
            result = round(result, cfg.decimal_places)

        logger.info(f"Divided {len(values)} numbers: {values} = {result}")

        # Get output node ID
        output_node_id = context.outputs[0].node_id

        return {output_node_id: result}
