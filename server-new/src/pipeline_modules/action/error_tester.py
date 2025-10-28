"""
Error Tester Module
Throws an error when executed - useful for testing error handling in pipelines
"""
from typing import Dict, Any
from pydantic import BaseModel, Field
from shared.types import TransformModule, ModuleMeta, IOShape, IOSideShape, NodeGroup, NodeTypeRule
from features.modules.utils.decorators import register


class ErrorTesterConfig(BaseModel):
    """Configuration for error tester"""
    error_message: str = Field(
        "This is a test error from the error_tester module",
        description="Custom error message to throw"
    )


@register
class ErrorTester(TransformModule):
    """
    Transform module that always throws an error when executed

    Useful for testing error handling, pipeline failure scenarios,
    and verifying that errors are properly caught and reported.
    """

    id = "error_tester"
    version = "1.0.0"
    title = "Error Tester"
    description = "Throws an error when executed (for testing error handling)"
    category = "Testing"
    color = "#DC2626"  # Dark red
    ConfigModel = ErrorTesterConfig

    @classmethod
    def meta(cls) -> ModuleMeta:
        return ModuleMeta(
            io_shape=IOShape(
                inputs=IOSideShape(nodes=[
                    NodeGroup(
                        label="input",
                        min_count=1,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["str"])
                    )
                ]),
                outputs=IOSideShape(nodes=[
                    NodeGroup(
                        label="output",
                        min_count=1,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["str"])
                    )
                ])
            )
        )

    def run(self, inputs: Dict[str, Any], cfg: ErrorTesterConfig, context: Any = None) -> Dict[str, Any]:
        """
        Execute the error tester - always throws an error

        Args:
            inputs: Dictionary with single 'input' value (unused)
            cfg: Configuration with custom error message
            context: Execution context (unused)

        Raises:
            RuntimeError: Always raises with the configured error message

        Returns:
            Never returns (always raises)
        """
        # Intentionally raise an error for testing
        raise RuntimeError(cfg.error_message)
