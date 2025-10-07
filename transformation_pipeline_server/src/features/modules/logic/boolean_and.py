"""
Boolean AND Logic Module
Infrastructure module for logical AND operation
"""
from typing import Dict, Any
from pydantic import BaseModel

from shared.models import LogicModule, ModuleMeta, IOShape, IOSideShape, NodeGroup, NodeTypeRule
from shared.utils.registry import register


class BooleanAndConfig(BaseModel):
    """Configuration for Boolean AND - no configuration needed"""
    pass

@register
class BooleanAnd(LogicModule):
    """
    Boolean AND logic gate
    Takes two boolean inputs and outputs their logical AND result
    """

    # Class metadata
    id = "boolean_and"
    version = "1.0.0"
    title = "Boolean AND"
    description = "Logical AND operation on two boolean inputs"
    category = "Gate"
    color = "#10B981"  # Green

    # Configuration model
    ConfigModel = BooleanAndConfig

    @classmethod
    def meta(cls) -> ModuleMeta:
        """Define I/O constraints for this module"""
        return ModuleMeta(
            io_shape=IOShape(
                inputs=IOSideShape(
                    nodes=[
                        NodeGroup(
                            label="A",
                            min_count=1,
                            max_count=1,
                            typing=NodeTypeRule(allowed_types=["bool"])
                        ),
                        NodeGroup(
                            label="B",
                            min_count=1,
                            max_count=1,
                            typing=NodeTypeRule(allowed_types=["bool"])
                        )
                    ]
                ),
                outputs=IOSideShape(
                    nodes=[
                        NodeGroup(
                            label="And",
                            min_count=1,
                            max_count=1,
                            typing=NodeTypeRule(allowed_types=["bool"])
                        )
                    ]
                )
            )
        )

    def run(self, inputs: Dict[str, Any], cfg: BooleanAndConfig, context: Any = None) -> Dict[str, Any]:
        """
        Execute Boolean AND operation (not implemented yet)

        Args:
            inputs: Dictionary with two boolean inputs
            cfg: Validated configuration (empty)
            context: Execution context

        Returns:
            Dictionary with boolean result
        """
        # TODO: Implement execution logic
        raise NotImplementedError("Execution not implemented yet")
