"""
Type Converter Transform Module
Infrastructure module for converting between data types
"""
from typing import Dict, Any
from pydantic import BaseModel

from shared.types import TransformModule, ModuleMeta, IOShape, IOSideShape, NodeGroup, NodeTypeRule
from features.modules.utils.decorators import register


class TypeConverterConfig(BaseModel):
    """Configuration for Type Converter - no configuration needed"""
    pass

@register
class TypeConverter(TransformModule):
    """
    Type Converter transform module
    Converts input data from one type to another type
    Input and output can be any type, conversion logic handles the transformation
    """

    # Class metadata
    id = "type_converter"
    version = "1.0.0"
    title = "Type Converter"
    description = "Convert data from one type to another"
    category = "Flow Control"
    color = "#FFFFFF"  # White

    # Configuration model
    ConfigModel = TypeConverterConfig

    @classmethod
    def meta(cls) -> ModuleMeta:
        """Define I/O constraints for this module"""
        return ModuleMeta(
            io_shape=IOShape(
                inputs=IOSideShape(
                    nodes=[
                        NodeGroup(
                            label="input_value",
                            min_count=1,
                            max_count=1,
                            typing=NodeTypeRule(allowed_types=[])
                        )
                    ]
                ),
                outputs=IOSideShape(
                    nodes=[
                        NodeGroup(
                            label="converted_value",
                            min_count=1,
                            max_count=1,
                            typing=NodeTypeRule(allowed_types=[])
                        )
                    ]
                )
            )
        )

    def run(self, inputs: Dict[str, Any], cfg: TypeConverterConfig, context: Any = None, services: Any = None) -> Dict[str, Any]:
        """
        Execute type conversion

        Args:
            inputs: Dictionary with one input value (key is node_id)
            cfg: Validated configuration (empty)
            context: Execution context with input/output type information

        Returns:
            Dictionary with converted value
        """
        # Get the input value (first and only value in the dict)
        input_node_id = list(inputs.keys())[0]
        input_value = inputs[input_node_id]

        output_type = context.outputs[0].type
        output_node_id = context.outputs[0].node_id


        try:
            converted_value = self._convert_value(input_value, output_type)
        except Exception as e:
            raise ValueError(f"Failed to convert {type(input_value).__name__} to {output_type}: {str(e)}")

        return {output_node_id: converted_value}

    def _convert_value(self, value: Any, target_type: str) -> Any:
        """
        Convert a value to the target type

        Args:
            value: The value to convert
            target_type: The target type ("str", "float", "bool", "datetime", "int", etc.)

        Returns:
            The converted value
        """
        from datetime import datetime
        import json

        # Handle None
        if value is None:
            if target_type == "str":
                return ""
            elif target_type == "bool":
                return False
            elif target_type in ["float", "int"]:
                return 0
            else:
                return None

        # Convert based on target type
        if target_type == "str":
            # Convert anything to string
            if isinstance(value, (dict, list)):
                # Use default parameter to handle datetime and other non-serializable objects
                return json.dumps(value, default=str)
            elif isinstance(value, datetime):
                return value.isoformat()
            else:
                return str(value)

        elif target_type == "float":
            # Convert to float
            if isinstance(value, str):
                # Handle boolean strings
                if value.lower() in ["true", "yes", "1"]:
                    return 1.0
                elif value.lower() in ["false", "no", "0", ""]:
                    return 0.0
                else:
                    return float(value)
            elif isinstance(value, bool):
                return float(value)
            elif isinstance(value, datetime):
                return value.timestamp()
            else:
                return float(value)

        elif target_type == "int":
            # Convert to integer
            if isinstance(value, str):
                # Handle boolean strings
                if value.lower() in ["true", "yes"]:
                    return 1
                elif value.lower() in ["false", "no", ""]:
                    return 0
                else:
                    # Try to parse as float first, then convert to int
                    return int(float(value))
            elif isinstance(value, bool):
                return int(value)
            elif isinstance(value, datetime):
                return int(value.timestamp())
            else:
                return int(value)

        elif target_type == "bool":
            # Convert to boolean
            if isinstance(value, str):
                return value.lower() not in ["", "false", "no", "0", "none", "null"]
            elif isinstance(value, (int, float)):
                return value != 0
            elif isinstance(value, datetime):
                return True  # A datetime is always truthy
            else:
                return bool(value)

        elif target_type == "datetime":
            # Convert to datetime
            if isinstance(value, str):
                # Try various datetime formats
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
                for fmt in formats:
                    try:
                        return datetime.strptime(value, fmt)
                    except ValueError:
                        continue
                # If no format matched, try to parse as ISO format
                return datetime.fromisoformat(value.replace('Z', '+00:00'))
            elif isinstance(value, (int, float)):
                # Assume it's a Unix timestamp
                return datetime.fromtimestamp(value)
            elif isinstance(value, datetime):
                return value
            else:
                raise ValueError(f"Cannot convert {type(value).__name__} to datetime")

        else:
            # Unknown target type, try basic conversion
            if target_type == "any" or target_type == "object":
                return value  # Return as-is for "any" type
            else:
                raise ValueError(f"Unsupported target type: {target_type}")
