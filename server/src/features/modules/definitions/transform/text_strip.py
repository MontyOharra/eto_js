"""
Text Strip Transform Modules
Strip characters from the beginning or end of text strings
"""
from typing import Dict, Any
from pydantic import BaseModel, Field

from shared.types import TransformModule, ModuleMeta, IOShape, IOSideShape, NodeGroup, NodeTypeRule
from features.modules.utils.decorators import register


class StripStartConfig(BaseModel):
    """Configuration for stripping characters from the start of text"""
    count: int = Field(1, ge=0, description="Number of characters to strip from the start")


class StripEndConfig(BaseModel):
    """Configuration for stripping characters from the end of text"""
    count: int = Field(1, ge=0, description="Number of characters to strip from the end")


@register
class StripStart(TransformModule):
    """
    Strip characters from the start of a text string
    Removes the first N characters from the input text
    """

    # Class metadata
    id = "strip_start"
    version = "1.0.0"
    title = "Strip Start"
    description = "Remove a specified number of characters from the beginning of a text string"
    category = "Text"
    color = "#F97316"  # Orange

    # Configuration model
    ConfigModel = StripStartConfig

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

    def run(self, inputs: Dict[str, Any], cfg: StripStartConfig, context: Any = None, services: Any = None) -> Dict[str, Any]:
        """
        Strip characters from the start of the input text

        Args:
            inputs: Dictionary with one text input
            cfg: Validated configuration with count
            context: Execution context with ordered inputs/outputs

        Returns:
            Dictionary with stripped text output
        """
        if len(inputs) != 1:
            raise ValueError(f"Expected exactly 1 input, got {len(inputs)}")

        input_text = next(iter(inputs.values()))

        if not isinstance(input_text, str):
            raise ValueError(f"Expected string input, got {type(input_text)}")

        # Strip the first N characters
        stripped_text = input_text[cfg.count:] if cfg.count > 0 else input_text

        output_node_id = context.outputs[0].node_id
        return {output_node_id: stripped_text}


@register
class StripEnd(TransformModule):
    """
    Strip characters from the end of a text string
    Removes the last N characters from the input text
    """

    # Class metadata
    id = "strip_end"
    version = "1.0.0"
    title = "Strip End"
    description = "Remove a specified number of characters from the end of a text string"
    category = "Text"
    color = "#F97316"  # Orange

    # Configuration model
    ConfigModel = StripEndConfig

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

    def run(self, inputs: Dict[str, Any], cfg: StripEndConfig, context: Any = None, services: Any = None) -> Dict[str, Any]:
        """
        Strip characters from the end of the input text

        Args:
            inputs: Dictionary with one text input
            cfg: Validated configuration with count
            context: Execution context with ordered inputs/outputs

        Returns:
            Dictionary with stripped text output
        """
        if len(inputs) != 1:
            raise ValueError(f"Expected exactly 1 input, got {len(inputs)}")

        input_text = next(iter(inputs.values()))

        if not isinstance(input_text, str):
            raise ValueError(f"Expected string input, got {type(input_text)}")

        # Strip the last N characters
        if cfg.count > 0 and len(input_text) > 0:
            stripped_text = input_text[:-cfg.count] if cfg.count < len(input_text) else ""
        else:
            stripped_text = input_text

        output_node_id = context.outputs[0].node_id
        return {output_node_id: stripped_text}
