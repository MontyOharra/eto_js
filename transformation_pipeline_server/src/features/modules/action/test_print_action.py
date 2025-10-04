"""
Test for PrintAction Module
"""
import sys
import io
import os
from pathlib import Path

# Add src to Python path
project_root = str(Path(__file__).parent.parent.parent.parent.parent)
src_path = os.path.join(project_root, 'src')
sys.path.insert(0, src_path)
sys.path.insert(0, project_root)

from src.features.modules.action.print_action import PrintAction, PrintActionConfig


def test_print_action_basic():
    """Test PrintAction with basic message"""
    # Create instance
    action = PrintAction()

    # Prepare inputs and config
    inputs = {"message_in": "Hello from pipeline!"}
    config = PrintActionConfig(prefix="")

    # Capture stdout
    captured_output = io.StringIO()
    sys.stdout = captured_output

    # Run action
    result = action.run(inputs, config)

    # Restore stdout
    sys.stdout = sys.__stdout__

    # Verify output
    output = captured_output.getvalue()
    assert "[ACTION] Hello from pipeline!" in output

    # Verify empty result
    assert result == {}

    print("PASS: test_print_action_basic")


def test_print_action_with_prefix():
    """Test PrintAction with prefix"""
    action = PrintAction()

    inputs = {"msg": "Test message"}
    config = PrintActionConfig(prefix="[TEST] ")

    # Capture stdout
    captured_output = io.StringIO()
    sys.stdout = captured_output

    # Run action
    result = action.run(inputs, config)

    # Restore stdout
    sys.stdout = sys.__stdout__

    # Verify output
    output = captured_output.getvalue()
    assert "[ACTION] [TEST] Test message" in output
    assert result == {}

    print("PASS: test_print_action_with_prefix")


def test_print_action_metadata():
    """Test PrintAction metadata"""
    # Check class attributes
    assert PrintAction.id == "print_action"
    assert PrintAction.version == "1.0.0"
    assert PrintAction.title == "Print to Server Log"
    assert PrintAction.kind == "action"

    # Check metadata
    meta = PrintAction.meta()
    assert len(meta.io_shape.inputs.nodes) == 1
    assert meta.io_shape.inputs.nodes[0].label == "message"
    assert meta.io_shape.inputs.nodes[0].min_count == 1
    assert meta.io_shape.inputs.nodes[0].max_count == 1
    assert "str" in meta.io_shape.inputs.nodes[0].typing.allowed_types

    # Actions should have no outputs
    assert len(meta.io_shape.outputs.nodes) == 0

    print("PASS: test_print_action_metadata")


def test_print_action_config():
    """Test PrintAction config validation"""
    # Valid configs
    config1 = PrintActionConfig()
    assert config1.prefix == ""

    config2 = PrintActionConfig(prefix="[INFO] ")
    assert config2.prefix == "[INFO] "

    print("PASS: test_print_action_config")


if __name__ == "__main__":
    print("Running PrintAction tests...")
    print()

    test_print_action_metadata()
    test_print_action_config()
    test_print_action_basic()
    test_print_action_with_prefix()

    print()
    print("All tests passed!")
