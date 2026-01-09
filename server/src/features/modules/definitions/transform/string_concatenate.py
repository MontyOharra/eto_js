"""
String Concatenate Transform Module
Concatenates multiple string inputs with a configurable separator
"""
import logging
from typing import Dict, Any
from pydantic import BaseModel, Field

from shared.types import ModuleMeta, IOShape, IOSideShape, NodeGroup, NodeTypeRule
from features.modules.registry import register
from features.modules.base import BaseModule

logger = logging.getLogger(__name__)


class StringConcatenateConfig(BaseModel):
    """Configuration for String Concatenate"""
    separator: str = Field(
        default=" ",
        description="Separator to use between concatenated strings"
    )


@register
class StringConcatenate(BaseModule):
    """
    String Concatenate transform module
    Concatenates multiple string inputs with a configurable separator
    """

    # Class metadata
    identifier = "string_concatenate"
    version = "1.0.0"
    title = "String Concatenate"
    description = "Concatenate multiple strings with a separator"
    category = "Text"
    kind = "transform"
    color = "#0EA5E9"  # Sky blue

    # Configuration model
    ConfigModel = StringConcatenateConfig

    @classmethod
    def meta(cls) -> ModuleMeta:
        """Define I/O constraints for this module"""
        return ModuleMeta(
            io_shape=IOShape(
                inputs=IOSideShape(
                    nodes=[
                        NodeGroup(
                            label="text",
                            typing=NodeTypeRule(allowed_types=["str"]),
                            min_count=2,
                            max_count=None  # Unlimited inputs
                        )
                    ]
                ),
                outputs=IOSideShape(
                    nodes=[
                        NodeGroup(
                            label="concatenated_text",
                            typing=NodeTypeRule(allowed_types=["str"]),
                            min_count=1,
                            max_count=1
                        )
                    ]
                )
            )
        )

    def run(self, inputs: Dict[str, Any], cfg: StringConcatenateConfig, context: Any) -> Dict[str, Any]:
        """
        Execute string concatenation

        Args:
            inputs: Dictionary with multiple string inputs
            cfg: Validated configuration with separator
            context: Execution context with ordered inputs/outputs
            services: Not used for this module

        Returns:
            Dictionary with concatenated string output
        """
        # Get input values in order from context
        input_values = []
        for input_node in context.inputs:
            node_id = input_node.node_id
            value = inputs.get(node_id, "")

            # Convert to string if not already
            if value is None:
                value = ""
            elif not isinstance(value, str):
                value = str(value)

            input_values.append(value)

        # Concatenate with separator
        concatenated = cfg.separator.join(input_values)

        logger.info(f"Concatenated {len(input_values)} strings with separator '{cfg.separator}'")

        # Get output node ID
        output_node_id = context.outputs[0].node_id

        return {
            output_node_id: concatenated
        }
