"""
Math Add Transform Module
Sums multiple numeric inputs
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


class MathAddConfig(BaseModel):
    """Configuration for Math Add"""

    decimal_places: int | None = Field(
        default=None,
        description="Round result to N decimal places (None = no rounding)",
    )


@register
class MathAdd(BaseModule):
    """
    Math Add transform module
    Sums all numeric inputs
    """

    # Class metadata
    identifier = "math_add"
    version = "1.0.0"
    title = "Add"
    description = "Sum multiple numbers"
    category = "Math"
    kind = "transform"
    color = "#8B5CF6"  # Purple

    # Configuration model
    ConfigModel = MathAddConfig

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
        cfg: MathAddConfig,
        context: Any,
        access_conn_manager: "AccessConnectionManager | None" = None,
    ) -> dict[str, Any]:
        """
        Execute addition

        Args:
            inputs: Dictionary with numeric inputs
            cfg: Validated configuration
            context: Execution context with ordered inputs/outputs

        Returns:
            Dictionary with sum result
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

        # Sum all values
        result = sum(values)

        # Apply rounding if configured
        if cfg.decimal_places is not None:
            result = round(result, cfg.decimal_places)

        logger.info(f"Added {len(values)} numbers: {values} = {result}")

        # Get output node ID
        output_node_id = context.outputs[0].node_id

        return {output_node_id: result}
