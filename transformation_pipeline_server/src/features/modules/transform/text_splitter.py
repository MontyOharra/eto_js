"""
Text Splitter Transform Module
Splits text input into multiple outputs based on a delimiter
"""
from typing import Dict, Any
from pydantic import BaseModel, Field

from shared.models import TransformModule, ModuleMeta, IOShape, IOSideShape, NodeGroup, NodeTypeRule
from shared.utils.registry import register


class TextSplitterConfig(BaseModel):
    """Configuration for Text Splitter"""
    split_character: str = Field(",", description="Character to split on")

@register
class TextSplitter(TransformModule):
    """
    Text Splitter transform module
    Takes one text input and splits it into multiple text outputs
    """

    # Class metadata
    id = "text_splitter"
    version = "1.0.0"
    title = "Text Splitter"
    description = "Split text input into multiple outputs based on a delimiter"
    category = "Text"
    color = "#EC4899"  # Pink

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
                            min_count=1,
                            max_count=1,
                            typing=NodeTypeRule(allowed_types=["str"])
                        )
                    ]
                ),
                outputs=IOSideShape(
                    nodes=[
                        NodeGroup(
                            label="split_text",
                            min_count=2,
                            max_count=None,  # Unlimited outputs
                            typing=NodeTypeRule(allowed_types=["str"])
                        )
                    ]
                )
            )
        )

    def run(self, inputs: Dict[str, Any], cfg: TextSplitterConfig, context: Any = None) -> Dict[str, Any]:
        """
        Execute text splitting (not implemented yet)

        Args:
            inputs: Dictionary with one text input
            cfg: Validated configuration with split character
            context: Execution context

        Returns:
            Dictionary with split text outputs
        """
        # TODO: Implement execution logic
        raise NotImplementedError("Execution not implemented yet")
