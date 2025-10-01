"""
Boolean OR Logic Module
Infrastructure module for logical OR operation
"""
from typing import Dict, Any
from pydantic import BaseModel

from src.features.modules.core.contracts import LogicModule, ModuleMeta, IOShape, IOSideShape, StaticNodes, NodeSpec, NodeTypeRule
from src.features.modules.core.registry import register


class BooleanOrConfig(BaseModel):
    """Configuration for Boolean OR - no configuration needed"""
    pass


@register
class BooleanOr(LogicModule):
    """
    Boolean OR logic gate
    Takes two boolean inputs and outputs their logical OR result
    """

    # Class metadata
    id = "boolean_or"
    version = "1.0.0"
    title = "Boolean OR"
    description = "Logical OR operation on two boolean inputs"

    # Configuration model
    ConfigModel = BooleanOrConfig

    @classmethod
    def meta(cls) -> ModuleMeta:
        """Define I/O constraints for this module"""
        return ModuleMeta(
            io_shape=IOShape(
                inputs=IOSideShape(
                    static=StaticNodes(
                        slots=[
                            NodeSpec(
                                label="A",
                                typing=NodeTypeRule(allowed_types=["bool"])
                            ),
                            NodeSpec(
                                label="B",
                                typing=NodeTypeRule(allowed_types=["bool"])
                            )
                        ]
                    )
                ),
                outputs=IOSideShape(
                    static=StaticNodes(
                        slots=[
                            NodeSpec(
                                label="Or",
                                typing=NodeTypeRule(allowed_types=["bool"])
                            )
                        ]
                    )
                )
            )
        )

    def run(self, inputs: Dict[str, Any], cfg: BooleanOrConfig, context: Any = None) -> Dict[str, Any]:
        """
        Execute Boolean OR operation (not implemented yet)

        Args:
            inputs: Dictionary with two boolean inputs
            cfg: Validated configuration (empty)
            context: Execution context

        Returns:
            Dictionary with boolean result
        """
        # TODO: Implement execution logic
        raise NotImplementedError("Execution not implemented yet")