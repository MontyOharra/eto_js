"""
Value Generator Module
Misc module that outputs a configured value with no inputs
"""
from typing import Dict, Any
from pydantic import BaseModel, Field

from shared.types import MiscModule, ModuleMeta, IOShape, IOSideShape, NodeGroup, NodeTypeRule
from features.modules.utils.decorators import register


class GeneratorConfig(BaseModel):
    """Configuration for Value Generator"""
    output_value: str = Field(..., description="Value to output from the generator (coalesces to the output node type)")

@register
class Generator(MiscModule):
    """
    Value Generator
    Outputs a configured value with no inputs
    The value is type-converted to match the output node's type
    """

    # Class metadata
    id = "generator"
    version = "1.0.0"
    title = "Value Generator"
    description = "Output a configured value (no inputs required)"
    category = "Generator"
    color = "#10B981"  # Green

    # Configuration model
    ConfigModel = GeneratorConfig

    @classmethod
    def meta(cls) -> ModuleMeta:
        """Define I/O constraints for this module"""
        return ModuleMeta(
            io_shape=IOShape(
                inputs=IOSideShape(),  # No inputs
                outputs=IOSideShape(
                    nodes=[
                        NodeGroup(
                            label="value",
                            min_count=1,
                            max_count=1,
                            typing=NodeTypeRule(allowed_types=[])  # Any type
                        )
                    ]
                )
            )
        )

    def run(self, inputs: Dict[str, Any], cfg: GeneratorConfig, context: Any) -> Dict[str, Any]:
        """
        Execute value generation

        Args:
            inputs: Dictionary (empty, no inputs)
            cfg: Validated configuration with output_value
            context: Execution context with output type information

        Returns:
            Dictionary with generated value (type-coalesced)
        """
        from datetime import datetime
        import json

        # Get output node metadata
        output_node = context.outputs[0]
        output_node_id = output_node.node_id
        output_type = output_node.type

        # Convert the configured string value to the output type
        value = cfg.output_value

        try:
            # If target type is string, return as-is
            if output_type == "str":
                converted_value = value

            # Handle empty string
            elif value == "":
                if output_type == "bool":
                    converted_value = False
                elif output_type in ["float", "int"]:
                    converted_value = 0
                else:
                    converted_value = None

            # Convert based on target type
            elif output_type == "float":
                if value.lower() in ["true", "yes", "1"]:
                    converted_value = 1.0
                elif value.lower() in ["false", "no", "0"]:
                    converted_value = 0.0
                else:
                    converted_value = float(value)

            elif output_type == "int":
                if value.lower() in ["true", "yes"]:
                    converted_value = 1
                elif value.lower() in ["false", "no"]:
                    converted_value = 0
                else:
                    converted_value = int(float(value))

            elif output_type == "bool":
                converted_value = value.lower() not in ["", "false", "no", "0", "none", "null"]

            elif output_type == "datetime":
                formats = [
                    "%Y-%m-%d %H:%M:%S",
                    "%Y-%m-%dT%H:%M:%S",
                    "%Y-%m-%dT%H:%M:%S.%f",
                    "%Y-%m-%dT%H:%M:%SZ",
                    "%Y-%m-%dT%H:%M:%S.%fZ",
                    "%Y-%m-%d",
                    "%m/%d/%Y",
                    "%d/%m/%Y",
                ]
                parsed = False
                for fmt in formats:
                    try:
                        converted_value = datetime.strptime(value, fmt)
                        parsed = True
                        break
                    except ValueError:
                        continue
                if not parsed:
                    converted_value = datetime.fromisoformat(value.replace('Z', '+00:00'))

            else:
                # Unknown target type or "any"
                if output_type == "any" or output_type == "object":
                    try:
                        converted_value = json.loads(value)
                    except:
                        converted_value = value
                else:
                    raise ValueError(f"Unsupported target type: {output_type}")

        except Exception as e:
            raise ValueError(
                f"Failed to convert configured value '{cfg.output_value}' to type {output_type}: {str(e)}"
            )

        return {output_node_id: converted_value}
