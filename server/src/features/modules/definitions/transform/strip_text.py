"""
Strip Text Transform Module
Strip specific text from the beginning and/or end of strings
"""
from typing import Dict, Any
from pydantic import BaseModel, Field

from shared.types import ModuleMeta, IOShape, IOSideShape, NodeGroup, NodeTypeRule
from features.modules.registry import register
from features.modules.base import BaseModule
from shared.database.access_connection import AccessConnectionManager


class StripTextConfig(BaseModel):
    """Configuration for stripping specific text from a string"""
    text: str = Field(..., description="The specific text to strip")
    strip_from_start: bool = Field(True, description="Strip from the beginning of the string")
    strip_from_end: bool = Field(False, description="Strip from the end of the string")
    case_sensitive: bool = Field(False, description="Whether matching is case-sensitive")


@register
class StripText(BaseModule):
    """
    Strip specific text from the start and/or end of a string.
    Only removes the text if it actually exists at the specified position.
    """

    # Class metadata
    identifier = "strip_text"
    version = "1.0.0"
    title = "Strip Text"
    description = "Remove specific text from the beginning and/or end of a string"
    category = "String"
    kind = "transform"
    color = "#3B82F6"  # Blue - matches string comparators

    # Configuration model
    ConfigModel = StripTextConfig

    @classmethod
    def meta(cls) -> ModuleMeta:
        """Define I/O constraints for this module"""
        return ModuleMeta(
            io_shape=IOShape(
                inputs=IOSideShape(
                    nodes=[
                        NodeGroup(
                            label="input_text",
                            typing=NodeTypeRule(allowed_types=["str"]),
                            min_count=1,
                            max_count=1
                        )
                    ]
                ),
                outputs=IOSideShape(
                    nodes=[
                        NodeGroup(
                            label="stripped_text",
                            typing=NodeTypeRule(allowed_types=["str"]),
                            min_count=1,
                            max_count=1
                        )
                    ]
                )
            )
        )

    def run(self, inputs: Dict[str, Any], cfg: StripTextConfig, context: Any = None, access_conn_manager: AccessConnectionManager | None = None) -> Dict[str, Any]:
        """
        Strip specific text from the start and/or end of the input string.

        Args:
            inputs: Dictionary with one text input
            cfg: Validated configuration with text to strip and toggles
            context: Execution context with ordered inputs/outputs

        Returns:
            Dictionary with stripped text output
        """
        if len(inputs) != 1:
            raise ValueError(f"Expected exactly 1 input, got {len(inputs)}")

        input_text = next(iter(inputs.values()))

        if not isinstance(input_text, str):
            raise ValueError(f"Expected string input, got {type(input_text)}")

        result = input_text
        strip_text = cfg.text

        # If no text to strip, return unchanged
        if not strip_text:
            output_node_id = context.outputs[0].node_id
            return {output_node_id: result}

        # For case-insensitive matching, we need to check lowercase versions
        # but strip the original text length
        if cfg.case_sensitive:
            # Strip from start
            if cfg.strip_from_start and result.startswith(strip_text):
                result = result[len(strip_text):]

            # Strip from end
            if cfg.strip_from_end and result.endswith(strip_text):
                result = result[:-len(strip_text)]
        else:
            # Case-insensitive matching
            result_lower = result.lower()
            strip_text_lower = strip_text.lower()

            # Strip from start
            if cfg.strip_from_start and result_lower.startswith(strip_text_lower):
                result = result[len(strip_text):]

            # Strip from end (need to recompute lower since result may have changed)
            result_lower = result.lower()
            if cfg.strip_from_end and result_lower.endswith(strip_text_lower):
                result = result[:-len(strip_text)]

        output_node_id = context.outputs[0].node_id
        return {output_node_id: result}
