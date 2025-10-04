"""
Tests for GraphPruner
"""
import pytest
from src.features.pipeline.compilation.graph_pruner import GraphPruner
from src.shared.models.pipeline import (
    PipelineState, ModuleInstance, NodeConnection,
    EntryPoint, InstanceNodePin
)


def test_all_modules_reachable_no_pruning():
    """
    Test case: All modules are reachable, nothing should be pruned

    Pipeline:
      entry -> module1 -> module2 -> action
    Reachable: {module1, module2, action}
    Expected: All 3 modules kept, all connections kept
    """
    # Build test pipeline
    pipeline = PipelineState(
        entry_points=[
            EntryPoint(node_id="entry1", name="test_entry")
        ],
        modules=[
            ModuleInstance(
                module_instance_id="module1",
                module_ref="test:1.0.0",
                module_kind="transform",
                config={},
                inputs=[InstanceNodePin(node_id="m1_in", type="str", name="input", position_index=0, group_index=0)],
                outputs=[InstanceNodePin(node_id="m1_out", type="str", name="output", position_index=0, group_index=0)]
            ),
            ModuleInstance(
                module_instance_id="module2",
                module_ref="test:1.0.0",
                module_kind="transform",
                config={},
                inputs=[InstanceNodePin(node_id="m2_in", type="str", name="input", position_index=0, group_index=0)],
                outputs=[InstanceNodePin(node_id="m2_out", type="str", name="output", position_index=0, group_index=0)]
            ),
            ModuleInstance(
                module_instance_id="action",
                module_ref="print:1.0.0",
                module_kind="action",
                config={},
                inputs=[InstanceNodePin(node_id="action_in", type="str", name="message", position_index=0, group_index=0)],
                outputs=[]
            )
        ],
        connections=[
            NodeConnection(from_node_id="entry1", to_node_id="m1_in"),
            NodeConnection(from_node_id="m1_out", to_node_id="m2_in"),
            NodeConnection(from_node_id="m2_out", to_node_id="action_in")
        ]
    )

    reachable = {"module1", "module2", "action"}

    # Prune
    pruned = GraphPruner.prune(pipeline, reachable)

    # Assert: Nothing pruned
    assert len(pruned.modules) == 3
    assert len(pruned.connections) == 3
    assert len(pruned.entry_points) == 1
    assert {m.module_instance_id for m in pruned.modules} == reachable


def test_dead_branch_pruned():
    """
    Test case: Dead branch exists and should be removed

    Pipeline:
      entry -> module1 -> action
      entry -> dead_module (not connected to action)
    Reachable: {module1, action}
    Expected: 2 modules kept (dead_module removed), only relevant connections kept
    """
    pipeline = PipelineState(
        entry_points=[
            EntryPoint(node_id="entry1", name="test_entry")
        ],
        modules=[
            ModuleInstance(
                module_instance_id="module1",
                module_ref="test:1.0.0",
                module_kind="transform",
                config={},
                inputs=[InstanceNodePin(node_id="m1_in", type="str", name="input", position_index=0, group_index=0)],
                outputs=[InstanceNodePin(node_id="m1_out", type="str", name="output", position_index=0, group_index=0)]
            ),
            ModuleInstance(
                module_instance_id="dead_module",
                module_ref="test:1.0.0",
                module_kind="transform",
                config={},
                inputs=[InstanceNodePin(node_id="dead_in", type="str", name="input", position_index=0, group_index=0)],
                outputs=[InstanceNodePin(node_id="dead_out", type="str", name="output", position_index=0, group_index=0)]
            ),
            ModuleInstance(
                module_instance_id="action",
                module_ref="print:1.0.0",
                module_kind="action",
                config={},
                inputs=[InstanceNodePin(node_id="action_in", type="str", name="message", position_index=0, group_index=0)],
                outputs=[]
            )
        ],
        connections=[
            NodeConnection(from_node_id="entry1", to_node_id="m1_in"),
            NodeConnection(from_node_id="m1_out", to_node_id="action_in"),
            NodeConnection(from_node_id="entry1", to_node_id="dead_in"),  # Dead connection
        ]
    )

    reachable = {"module1", "action"}

    # Prune
    pruned = GraphPruner.prune(pipeline, reachable)

    # Assert: Dead module removed
    assert len(pruned.modules) == 2
    assert {m.module_instance_id for m in pruned.modules} == reachable

    # Assert: Dead connection removed
    assert len(pruned.connections) == 2
    assert all(conn.to_node_id != "dead_in" for conn in pruned.connections)


def test_complex_dead_branch_chain():
    """
    Test case: Chain of dead modules all removed together

    Pipeline:
      entry -> module1 -> module2 -> action
      entry -> dead1 -> dead2 -> dead3
    Reachable: {module1, module2, action}
    Expected: 3 modules kept (all dead* removed), connections for dead branches removed
    """
    pipeline = PipelineState(
        entry_points=[EntryPoint(node_id="entry1", name="test")],
        modules=[
            # Reachable chain
            ModuleInstance(
                module_instance_id="module1", module_ref="test:1.0.0", module_kind="transform", config={},
                inputs=[InstanceNodePin(node_id="m1_in", type="str", name="in", position_index=0, group_index=0)],
                outputs=[InstanceNodePin(node_id="m1_out", type="str", name="out", position_index=0, group_index=0)]
            ),
            ModuleInstance(
                module_instance_id="module2", module_ref="test:1.0.0", module_kind="transform", config={},
                inputs=[InstanceNodePin(node_id="m2_in", type="str", name="in", position_index=0, group_index=0)],
                outputs=[InstanceNodePin(node_id="m2_out", type="str", name="out", position_index=0, group_index=0)]
            ),
            ModuleInstance(
                module_instance_id="action", module_ref="print:1.0.0", module_kind="action", config={},
                inputs=[InstanceNodePin(node_id="action_in", type="str", name="msg", position_index=0, group_index=0)],
                outputs=[]
            ),
            # Dead chain
            ModuleInstance(
                module_instance_id="dead1", module_ref="test:1.0.0", module_kind="transform", config={},
                inputs=[InstanceNodePin(node_id="d1_in", type="str", name="in", position_index=0, group_index=0)],
                outputs=[InstanceNodePin(node_id="d1_out", type="str", name="out", position_index=0, group_index=0)]
            ),
            ModuleInstance(
                module_instance_id="dead2", module_ref="test:1.0.0", module_kind="transform", config={},
                inputs=[InstanceNodePin(node_id="d2_in", type="str", name="in", position_index=0, group_index=0)],
                outputs=[InstanceNodePin(node_id="d2_out", type="str", name="out", position_index=0, group_index=0)]
            ),
            ModuleInstance(
                module_instance_id="dead3", module_ref="test:1.0.0", module_kind="transform", config={},
                inputs=[InstanceNodePin(node_id="d3_in", type="str", name="in", position_index=0, group_index=0)],
                outputs=[InstanceNodePin(node_id="d3_out", type="str", name="out", position_index=0, group_index=0)]
            ),
        ],
        connections=[
            # Reachable connections
            NodeConnection(from_node_id="entry1", to_node_id="m1_in"),
            NodeConnection(from_node_id="m1_out", to_node_id="m2_in"),
            NodeConnection(from_node_id="m2_out", to_node_id="action_in"),
            # Dead connections
            NodeConnection(from_node_id="entry1", to_node_id="d1_in"),
            NodeConnection(from_node_id="d1_out", to_node_id="d2_in"),
            NodeConnection(from_node_id="d2_out", to_node_id="d3_in"),
        ]
    )

    reachable = {"module1", "module2", "action"}

    # Prune
    pruned = GraphPruner.prune(pipeline, reachable)

    # Assert: Only reachable modules kept
    assert len(pruned.modules) == 3
    assert {m.module_instance_id for m in pruned.modules} == reachable

    # Assert: Only reachable connections kept
    assert len(pruned.connections) == 3
    dead_pins = {"d1_in", "d1_out", "d2_in", "d2_out", "d3_in", "d3_out"}
    for conn in pruned.connections:
        assert conn.from_node_id not in dead_pins
        assert conn.to_node_id not in dead_pins


def test_entry_points_always_kept():
    """
    Test case: Entry points are always kept even if unused

    Pipeline:
      entry1 -> module1 -> action
      entry2 (not connected to anything)
    Reachable: {module1, action}
    Expected: Both entry points kept even though entry2 is unused
    """
    pipeline = PipelineState(
        entry_points=[
            EntryPoint(node_id="entry1", name="used_entry"),
            EntryPoint(node_id="entry2", name="unused_entry")
        ],
        modules=[
            ModuleInstance(
                module_instance_id="module1", module_ref="test:1.0.0", module_kind="transform", config={},
                inputs=[InstanceNodePin(node_id="m1_in", type="str", name="in", position_index=0, group_index=0)],
                outputs=[InstanceNodePin(node_id="m1_out", type="str", name="out", position_index=0, group_index=0)]
            ),
            ModuleInstance(
                module_instance_id="action", module_ref="print:1.0.0", module_kind="action", config={},
                inputs=[InstanceNodePin(node_id="action_in", type="str", name="msg", position_index=0, group_index=0)],
                outputs=[]
            ),
        ],
        connections=[
            NodeConnection(from_node_id="entry1", to_node_id="m1_in"),
            NodeConnection(from_node_id="m1_out", to_node_id="action_in"),
        ]
    )

    reachable = {"module1", "action"}

    # Prune
    pruned = GraphPruner.prune(pipeline, reachable)

    # Assert: Both entry points kept
    assert len(pruned.entry_points) == 2
    assert {ep.node_id for ep in pruned.entry_points} == {"entry1", "entry2"}


def test_empty_reachable_set():
    """
    Test case: No modules are reachable (edge case, shouldn't happen after validation)

    Expected: Empty modules list, no connections, but entry points kept
    """
    pipeline = PipelineState(
        entry_points=[EntryPoint(node_id="entry1", name="test")],
        modules=[
            ModuleInstance(
                module_instance_id="module1", module_ref="test:1.0.0", module_kind="transform", config={},
                inputs=[InstanceNodePin(node_id="m1_in", type="str", name="in", position_index=0, group_index=0)],
                outputs=[InstanceNodePin(node_id="m1_out", type="str", name="out", position_index=0, group_index=0)]
            ),
        ],
        connections=[
            NodeConnection(from_node_id="entry1", to_node_id="m1_in"),
        ]
    )

    reachable = set()  # Empty set

    # Prune
    pruned = GraphPruner.prune(pipeline, reachable)

    # Assert: Everything pruned except entry points
    assert len(pruned.modules) == 0
    assert len(pruned.connections) == 0
    assert len(pruned.entry_points) == 1


def test_original_pipeline_unchanged():
    """
    Test case: Ensure original pipeline_state is not modified (immutability)
    """
    pipeline = PipelineState(
        entry_points=[EntryPoint(node_id="entry1", name="test")],
        modules=[
            ModuleInstance(
                module_instance_id="module1", module_ref="test:1.0.0", module_kind="transform", config={},
                inputs=[InstanceNodePin(node_id="m1_in", type="str", name="in", position_index=0, group_index=0)],
                outputs=[InstanceNodePin(node_id="m1_out", type="str", name="out", position_index=0, group_index=0)]
            ),
            ModuleInstance(
                module_instance_id="dead", module_ref="test:1.0.0", module_kind="transform", config={},
                inputs=[InstanceNodePin(node_id="d_in", type="str", name="in", position_index=0, group_index=0)],
                outputs=[InstanceNodePin(node_id="d_out", type="str", name="out", position_index=0, group_index=0)]
            ),
        ],
        connections=[
            NodeConnection(from_node_id="entry1", to_node_id="m1_in"),
            NodeConnection(from_node_id="entry1", to_node_id="d_in"),
        ]
    )

    original_module_count = len(pipeline.modules)
    original_connection_count = len(pipeline.connections)

    reachable = {"module1"}

    # Prune
    pruned = GraphPruner.prune(pipeline, reachable)

    # Assert: Original unchanged
    assert len(pipeline.modules) == original_module_count
    assert len(pipeline.connections) == original_connection_count

    # Assert: Pruned is different
    assert len(pruned.modules) < original_module_count
    assert len(pruned.connections) < original_connection_count


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
