"""
Module test helpers.

Provides fixtures and utilities for testing pipeline modules in isolation
without needing a database, pipeline compiler, or any application services.
"""
import pytest
from typing import Any

from shared.types.pipelines import NodeInstance, ModuleExecutionContext
from features.modules.base import BaseModule


class ModuleTestHarness:
    """
    Test harness for running pipeline modules in isolation.

    Builds the NodeInstance pins and ModuleExecutionContext plumbing
    so tests can work with plain dicts of {name: value} and {name: type}.
    """

    @staticmethod
    def run(
        module_class: type[BaseModule],
        config: dict[str, Any],
        inputs: dict[str, Any],
        output_pins: dict[str, str],
    ) -> dict[str, Any]:
        """
        Run a module with the given config, inputs, and output pin definitions.

        Args:
            module_class: The module class to test (e.g., LlmExtractor)
            config: Config dict matching the module's ConfigModel
            inputs: Dict of {pin_label: value} for input pins
            output_pins: Dict of {pin_label: type_str} for output pins
                         e.g., {"address": "str", "start_time": "datetime"}

        Returns:
            Dict of {pin_label: value} from the module's output
        """
        # Look up IO shape from module meta to assign correct group indices
        meta = module_class.meta()
        input_groups = meta.io_shape.inputs.nodes if meta.io_shape.inputs else []
        output_groups = meta.io_shape.outputs.nodes if meta.io_shape.outputs else []

        # Build a mapping from group label -> group_index for inputs
        input_group_labels = {g.label: idx for idx, g in enumerate(input_groups)}
        output_group_labels = {g.label: idx for idx, g in enumerate(output_groups)}

        # Build input NodeInstances and the inputs dict keyed by node_id
        input_nodes = []
        inputs_by_node_id = {}
        for i, (name, value) in enumerate(inputs.items()):
            node_id = f"test_in_{i}"
            # Match input name to a group label, default to group 0
            group_index = input_group_labels.get(name, 0)
            input_nodes.append(NodeInstance(
                node_id=node_id,
                type="str",
                name=name,
                position_index=i,
                group_index=group_index,
            ))
            inputs_by_node_id[node_id] = value

        # Build output NodeInstances
        output_nodes = []
        for i, (name, pin_type) in enumerate(output_pins.items()):
            node_id = f"test_out_{i}"
            group_index = output_group_labels.get(name, 0)
            output_nodes.append(NodeInstance(
                node_id=node_id,
                type=pin_type,
                name=name,
                position_index=i,
                group_index=group_index,
            ))

        # Build execution context
        context = ModuleExecutionContext(
            inputs=input_nodes,
            outputs=output_nodes,
            module_instance_id="test_module",
        )

        # Validate and instantiate config
        cfg = module_class.ConfigModel(**config)

        # Run the module
        module = module_class()
        raw_result = module.run(
            inputs=inputs_by_node_id,
            cfg=cfg,
            context=context,
            access_conn_manager=None,
        )

        # Map node_id results back to pin labels
        node_id_to_name = {node.node_id: node.name for node in output_nodes}
        return {
            node_id_to_name[node_id]: value
            for node_id, value in raw_result.items()
            if node_id in node_id_to_name
        }


@pytest.fixture
def run_module():
    """Fixture that returns the module test harness run function."""
    return ModuleTestHarness.run
