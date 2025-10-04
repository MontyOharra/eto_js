"""
LLM Parser Transform Module
Uses Large Language Model to parse and extract data from multiple text inputs
"""
from typing import Dict, Any
from pydantic import BaseModel, Field

from src.features.modules.core.contracts import TransformModule, ModuleMeta, IOShape, IOSideShape, NodeGroup, NodeTypeRule
from src.features.modules.core.registry import register


class LlmParserConfig(BaseModel):
    """Configuration for LLM Parser"""
    model: str = Field("gpt-4", description="Select the LLM model to use")
    prompt: str = Field("Extract and parse the relevant information from the input text.", description="Instructions for the LLM to parse the input text")


@register
class LlmParser(TransformModule):
    """
    LLM Parser transform module
    Uses Large Language Model to parse and extract data from multiple text inputs
    Supports 1 to inf string inputs and 1 to inf outputs of any type
    """

    # Class metadata
    id = "llm_parser"
    version = "1.0.0"
    title = "LLM Parser"
    description = "Use Large Language Model to parse and extract data from text"
    category = "AI"
    color = "#EC4899"  # Pink

    # Configuration model
    ConfigModel = LlmParserConfig

    @classmethod
    def meta(cls) -> ModuleMeta:
        """Define I/O constraints for this module"""
        return ModuleMeta(
            io_shape=IOShape(
                inputs=IOSideShape(
                    nodes=[
                        NodeGroup(
                            label="text_input",
                            min_count=1,
                            max_count=None,  # Unlimited inputs
                            typing=NodeTypeRule(allowed_types=["str"])
                        )
                    ]
                ),
                outputs=IOSideShape(
                    nodes=[
                        NodeGroup(
                            label="parsed_output",
                            min_count=1,
                            max_count=None,  # Unlimited outputs
                            typing=NodeTypeRule(allowed_types=["str", "float", "datetime", "bool"])
                        )
                    ]
                )
            )
        )

    def run(self, inputs: Dict[str, Any], cfg: LlmParserConfig, context: Any = None) -> Dict[str, Any]:
        """
        Execute LLM parsing (not implemented yet)

        Args:
            inputs: Dictionary with text inputs
            cfg: Validated configuration with model and prompt
            context: Execution context

        Returns:
            Dictionary with parsed outputs
        """
        # TODO: Implement execution logic
        raise NotImplementedError("Execution not implemented yet")