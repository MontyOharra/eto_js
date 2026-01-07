"""
Text Splitter Transform Module
Splits a string into a list of strings based on a delimiter
"""
import codecs
import logging
from typing import Dict, Any, List
from pydantic import BaseModel, Field

from shared.types import ModuleMeta, IOShape, IOSideShape, NodeGroup, NodeTypeRule
from features.modules.registry import register
from features.modules.base import TransformModule

logger = logging.getLogger(__name__)


class TextSplitterConfig(BaseModel):
    """Configuration for Text Splitter"""
    delimiter: str = Field(
        default=",",
        description="Character(s) to split on. Supports escape sequences: \\n (newline), \\t (tab), \\r (carriage return)"
    )
    strip_parts: bool = Field(
        default=True,
        description="Strip whitespace from each part"
    )
    remove_empty: bool = Field(
        default=True,
        description="Remove empty strings from result"
    )


@register
class TextSplitter(TransformModule):
    """
    Text Splitter transform module
    Splits a string into a list of strings based on a delimiter
    """

    # Class metadata
    identifier = "text_splitter"
    version = "1.0.0"
    title = "Text Splitter"
    description = "Split text into a list of strings based on a delimiter"
    category = "Text"
    color = "#8B5CF6"  # Purple

    # Configuration model
    ConfigModel = TextSplitterConfig

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
                            label="text_list",
                            typing=NodeTypeRule(allowed_types=["list[str]"]),
                            min_count=1,
                            max_count=1
                        )
                    ]
                )
            )
        )

    def run(self, inputs: Dict[str, Any], cfg: TextSplitterConfig, context: Any, services: Any = None) -> Dict[str, Any]:
        """
        Execute text splitting

        Args:
            inputs: Dictionary with input text
            cfg: Validated configuration with delimiter and options
            context: Execution context with ordered inputs/outputs
            services: Not used for this module

        Returns:
            Dictionary with list of strings output
        """
        # Get input value
        input_node_id = context.inputs[0].node_id
        input_text = inputs.get(input_node_id, "")

        # Convert to string if not already
        if input_text is None:
            input_text = ""
        elif not isinstance(input_text, str):
            input_text = str(input_text)

        # Decode escape sequences in delimiter (e.g., \n -> actual newline)
        try:
            delimiter = codecs.decode(cfg.delimiter, 'unicode_escape')
        except Exception:
            # If decoding fails, use the raw delimiter
            delimiter = cfg.delimiter

        # Split the text
        parts: List[str] = input_text.split(delimiter)

        # Strip whitespace if configured
        if cfg.strip_parts:
            parts = [p.strip() for p in parts]

        # Remove empty strings if configured
        if cfg.remove_empty:
            parts = [p for p in parts if p]

        logger.info(f"Split text into {len(parts)} parts using delimiter '{cfg.delimiter}' (resolved: {repr(delimiter)})")

        # Get output node ID
        output_node_id = context.outputs[0].node_id

        return {
            output_node_id: parts
        }
