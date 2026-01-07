"""
Strip Characters Transform Module
Strip a specified number of characters from the beginning and/or end of text strings
"""
from typing import Dict, Any
from pydantic import BaseModel, Field

from shared.types import ModuleMeta, IOShape, IOSideShape, NodeGroup, NodeTypeRule
from features.modules.registry import register
from features.modules.base import TransformModule


class StripCharactersConfig(BaseModel):
    """Configuration for stripping characters from text"""
    count: int = Field(1, ge=0, description="Number of characters to strip")
    strip_from_start: bool = Field(True, description="Strip from the beginning of the string")
    strip_from_end: bool = Field(False, description="Strip from the end of the string")


@register
class StripCharacters(TransformModule):
    """
    Strip a specified number of characters from the start and/or end of a text string.
    Can strip from the beginning, end, or both.
    """

    # Class metadata
    identifier = "strip_characters"
    version = "1.0.0"
    title = "Strip Characters"
    description = "Remove a specified number of characters from the beginning and/or end of a text string"
    category = "String"
    color = "#3B82F6"  # Blue - matches string comparators

    # Configuration model
    ConfigModel = StripCharactersConfig

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

    def run(self, inputs: Dict[str, Any], cfg: StripCharactersConfig, context: Any = None, services: Any = None) -> Dict[str, Any]:
        """
        Strip characters from the start and/or end of the input text.

        Args:
            inputs: Dictionary with one text input
            cfg: Validated configuration with count and toggles
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

        # If count is 0 or no stripping enabled, return unchanged
        if cfg.count == 0 or (not cfg.strip_from_start and not cfg.strip_from_end):
            output_node_id = context.outputs[0].node_id
            return {output_node_id: result}

        # Strip from start
        if cfg.strip_from_start and cfg.count > 0:
            result = result[cfg.count:]

        # Strip from end
        if cfg.strip_from_end and cfg.count > 0 and len(result) > 0:
            if cfg.count < len(result):
                result = result[:-cfg.count]
            else:
                result = ""

        output_node_id = context.outputs[0].node_id
        return {output_node_id: result}
