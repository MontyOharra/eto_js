"""
Basic Text Cleaner Transform Module
Example implementation following the transformation pipeline design
"""
import re
from typing import Dict, Any
from pydantic import BaseModel, Field

from shared.types import TransformModule, ModuleMeta, IOShape, IOSideShape, NodeGroup, NodeTypeRule
from features.modules.utils.decorators import register


class TextCleanerConfig(BaseModel):
    """Configuration for text cleaning operations"""
    strip_whitespace: bool = Field(True, description="Remove leading/trailing whitespace")
    normalize_spaces: bool = Field(True, description="Convert multiple spaces to single space")
    remove_empty_lines: bool = Field(False, description="Remove empty lines")
    replace_newlines_with_spaces: bool = Field(False, description="Replace newline characters with spaces")
    to_lowercase: bool = Field(False, description="Convert text to lowercase")

@register
class BasicTextCleaner(TransformModule):
    """
    Basic text cleaning transform module
    Cleans and normalizes text input
    """

    # Class metadata
    id = "basic_text_cleaner"
    version = "1.0.0"
    title = "Basic Text Cleaner"
    description = "Clean and normalize text by removing extra whitespace and applying basic transformations"
    category = "Text"
    color = "#0EA5E9"  # Sky blue

    # Configuration model
    ConfigModel = TextCleanerConfig

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
                            label="cleaned_text",
                            typing=NodeTypeRule(allowed_types=["str"]),
                            min_count=1,
                            max_count=1
                        )
                    ]
                )
            )
        )

    def run(self, inputs: Dict[str, Any], cfg: TextCleanerConfig, context: Any = None, services: Any = None) -> Dict[str, Any]:
        """
        Execute text cleaning on the input

        Args:
            inputs: Dictionary with one text input
            cfg: Validated configuration
            context: Execution context with ordered inputs/outputs

        Returns:
            Dictionary with cleaned text output
        """
        # Get the input text (should be exactly one input)
        if len(inputs) != 1:
            raise ValueError(f"Expected exactly 1 input, got {len(inputs)}")

        input_text = next(iter(inputs.values()))

        if not isinstance(input_text, str):
            raise ValueError(f"Expected string input, got {type(input_text)}")

        # Apply cleaning operations based on configuration
        cleaned_text = input_text

        if cfg.replace_newlines_with_spaces:
            # Replace newlines with spaces (do this first before other operations)
            cleaned_text = cleaned_text.replace('\r\n', ' ').replace('\n', ' ').replace('\r', ' ')

        if cfg.strip_whitespace:
            cleaned_text = cleaned_text.strip()

        if cfg.normalize_spaces:
            # Replace multiple spaces/tabs with single space
            cleaned_text = re.sub(r'\s+', ' ', cleaned_text)

        if cfg.remove_empty_lines:
            # Remove empty lines
            lines = cleaned_text.split('\n')
            lines = [line for line in lines if line.strip()]
            cleaned_text = '\n'.join(lines)

        if cfg.to_lowercase:
            cleaned_text = cleaned_text.lower()

        # Return output using context.outputs[0].node_id
        # Context always provides the output node metadata
        output_node_id = context.outputs[0].node_id

        return {output_node_id: cleaned_text}