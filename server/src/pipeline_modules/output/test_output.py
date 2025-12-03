"""
Test Output Module
Simple output module for testing the output execution system.
Contains a single string input field.
"""

from pydantic import BaseModel
from typing import Dict, Any, Optional

from shared.types.modules import (
    OutputModule,
    ModuleMeta,
    IOShape,
    IOSideShape,
    NodeGroup,
    NodeTypeRule,
)
from features.modules.utils.decorators import register


class TestOutputConfig(BaseModel):
    """Configuration for test output module (empty - no config needed)"""
    pass


@register
class TestOutput(OutputModule):
    """
    Test output module for validating the output execution system.

    This module collects a single string input and does nothing with it.
    Used for testing that:
    - Output modules execute in pipelines
    - Output module data is collected correctly
    - OutputExecutionService receives the correct data

    In production, the OutputExecutionService would receive:
    - module_id: "test_output"
    - input_data: {"test_value": "some string"}
    """

    id = "test_output"
    version = "1.0.0"
    title = "Test Output"
    description = "Simple test output module with one string input"
    kind = OutputModule.kind
    ConfigModel = TestOutputConfig

    @classmethod
    def meta(cls) -> ModuleMeta:
        """
        Define I/O shape: one string input, no outputs (terminal node).
        """
        return ModuleMeta(
            io_shape=IOShape(
                inputs=IOSideShape(
                    nodes=[
                        NodeGroup(
                            typing=NodeTypeRule(allowed_types=["str"]),
                            label="test_value",
                            min_count=1,
                            max_count=1
                        )
                    ]
                ),
                outputs=IOSideShape(nodes=[])  # Output modules have no outputs
            )
        )

    def run(
        self,
        inputs: Dict[str, Any],
        cfg: TestOutputConfig,
        context: Optional[Any],
        services: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Output modules don't execute side effects in the pipeline.
        Returns empty dict - actual execution happens in OutputExecutionService.

        Args:
            inputs: {"test_value_node_id": "some string value"}
            cfg: Empty config
            context: Module execution context
            services: Service container (unused)

        Returns:
            Empty dict (output modules are terminal nodes)
        """
        # Output modules just return empty dict
        # The pipeline service will collect the inputs and pass them to OutputExecutionService
        return {}
