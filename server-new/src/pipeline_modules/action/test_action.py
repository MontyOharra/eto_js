"""
Test Action Module
Simple action module for testing pipeline validation with no configuration
"""
from typing import Dict, Any
from pydantic import BaseModel
from shared.types import ActionModule, ModuleMeta, IOShape, IOSideShape, NodeGroup, NodeTypeRule
from features.modules.utils.decorators import register


class TestActionConfig(BaseModel):
    """Empty configuration for test action"""
    pass

@register
class TestAction(ActionModule):
    """
    Minimal action module for testing.

    Accepts one string input, has no configuration, and does nothing.
    Useful for testing pipeline validation.
    """

    id = "test_action"
    version = "1.0.0"
    title = "Test Action"
    description = "Simple test action with no configuration"
    category = "Test"
    color = "#10B981"  # Green
    ConfigModel = TestActionConfig

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
                outputs=IOSideShape(nodes=[])  # Actions have no outputs
            )
        )

    def run(self, inputs: Dict[str, Any], cfg: TestActionConfig, context: Any = None) -> Dict[str, Any]:
        """
        Execute the test action (does nothing)

        Args:
            inputs: Dictionary with single 'input' key containing string
            cfg: Empty configuration
            context: Execution context (unused)

        Returns:
            Empty dict (actions don't produce outputs)
        """
        # Test action does nothing - just for validation testing
        return {}
