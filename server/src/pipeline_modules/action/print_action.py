"""
Print Action Module
Prints messages to server backend logs for testing pipeline execution
"""
import logging
from typing import Dict, Any
from pydantic import BaseModel, Field
from shared.types import ActionModule, ModuleMeta, IOShape, IOSideShape, NodeGroup, NodeTypeRule
from features.modules.utils.decorators import register

logger = logging.getLogger(__name__)


class PrintActionConfig(BaseModel):
    """Configuration for print action"""
    prefix: str = Field("", description="Optional prefix to add before message")

@register
class PrintAction(ActionModule):
    """
    Action module that prints messages to server logs

    Useful for testing and debugging pipeline execution without
    requiring external systems (databases, email, etc.)
    """

    id = "print_action"
    version = "1.0.0"
    title = "Print to Server Log"
    description = "Prints a message to the server backend logs"
    category = "Print"
    color = "#EF4444"  # Red
    ConfigModel = PrintActionConfig

    @classmethod
    def meta(cls) -> ModuleMeta:
        return ModuleMeta(
            io_shape=IOShape(
                inputs=IOSideShape(nodes=[
                    NodeGroup(
                        label="message",
                        min_count=1,
                        max_count=1,
                        typing=NodeTypeRule(allowed_types=["str"])
                    )
                ]),
                outputs=IOSideShape(nodes=[])  # Actions typically have no outputs
            )
        )

    def run(self, inputs: Dict[str, Any], cfg: PrintActionConfig, context: Any = None) -> Dict[str, Any]:
        """
        Execute the print action

        Args:
            inputs: Dictionary with single 'message' key containing string to print
            cfg: Configuration with optional prefix
            context: Execution context (unused for this action)

        Returns:
            Empty dict (actions don't produce outputs)
        """
        # Get the single input value (first value from inputs dict)
        message = list(inputs.values())[0]

        # Log message with optional prefix (using WARNING level to ensure visibility)
        if cfg.prefix:
            log_message = f"[ACTION] {cfg.prefix}{message}"
        else:
            log_message = f"[ACTION] {message}"

        logger.warning(log_message)  # Using WARNING to ensure it shows in logs
        print(log_message)  # Also print to stdout for console visibility

        # Actions return empty dict
        return {}
