"""
String Concatenator Transform Module
Concatenates multiple string inputs with configurable separator and formatting
"""
from typing import Dict, Any
from pydantic import BaseModel, Field

from ..core.contracts import TransformModule, ModuleMeta, DynamicSide
from ..core.registry import register


class StringConcatenatorConfig(BaseModel):
    """Configuration for string concatenation"""
    separator: str = Field(" ", description="Text to insert between concatenated strings")
    prefix: str = Field("", description="Text to add at the beginning of the result")
    suffix: str = Field("", description="Text to add at the end of the result")
    skip_empty: bool = Field(True, description="Skip empty or null inputs")
    trim_inputs: bool = Field(False, description="Trim whitespace from each input before concatenating")


@register
class StringConcatenator(TransformModule):
    """
    String concatenator module
    Joins multiple string inputs into a single output with configurable formatting
    """

    # Module metadata
    id = "string_concatenator"
    version = "1.0.0"
    title = "String Concatenator"
    description = "Concatenate multiple strings with configurable separator, prefix, and suffix"

    # UI customization
    color = "#10B981"  # Green
    category = "Text poopoo shit"

    # Configuration model
    ConfigModel = StringConcatenatorConfig

    @classmethod
    def meta(cls) -> ModuleMeta:
        """Define I/O constraints for this module"""
        return ModuleMeta(
            inputs=DynamicSide(
                allow=True,  # Dynamic inputs allowed
                min_count=2,  # At least two inputs required
                max_count=None,  # Unlimited inputs
                type=["str", "int", "float"]  # Multiple allowed types for demonstration
            ),
            outputs=DynamicSide(
                allow=False,  # Static output
                min_count=1,
                max_count=1,
                type=["str"]  # Output is a string
            )
        )

    def run(self, inputs: Dict[str, Any], cfg: StringConcatenatorConfig, context: Any = None) -> Dict[str, Any]:
        """
        Execute string concatenation on the inputs

        Args:
            inputs: Dictionary with variable number of string inputs
            cfg: Validated configuration
            context: Execution context with ordered inputs/outputs

        Returns:
            Dictionary with concatenated string output
        """
        # Collect all input values
        values_to_concat = []

        # If context provides ordered inputs, use that order
        if context and hasattr(context, 'instance_ordered_inputs'):
            # Use the order specified by the pipeline
            for input_id, value in context.instance_ordered_inputs:
                if value is not None:
                    str_value = str(value)

                    # Apply trimming if configured
                    if cfg.trim_inputs:
                        str_value = str_value.strip()

                    # Skip empty strings if configured
                    if cfg.skip_empty and not str_value:
                        continue

                    values_to_concat.append(str_value)
                elif not cfg.skip_empty:
                    # Include None as empty string if not skipping empty
                    values_to_concat.append("")
        else:
            # Fallback: sort inputs by key for consistent ordering
            sorted_inputs = sorted(inputs.items())
            for input_id, value in sorted_inputs:
                if value is not None:
                    str_value = str(value)

                    # Apply trimming if configured
                    if cfg.trim_inputs:
                        str_value = str_value.strip()

                    # Skip empty strings if configured
                    if cfg.skip_empty and not str_value:
                        continue

                    values_to_concat.append(str_value)
                elif not cfg.skip_empty:
                    # Include None as empty string if not skipping empty
                    values_to_concat.append("")

        # Concatenate with separator
        concatenated = cfg.separator.join(values_to_concat)

        # Add prefix and suffix
        result = f"{cfg.prefix}{concatenated}{cfg.suffix}"

        # Get output node ID from context or use default
        if context and hasattr(context, 'instance_ordered_outputs'):
            output_node_id = context.instance_ordered_outputs[0]["node_id"]
        else:
            output_node_id = "output_1"

        return {output_node_id: result}


# Module validation hook (optional)
    @classmethod
    def validate_wiring(cls,
                       module_instance_id: str,
                       config: Dict[str, Any],
                       instance_inputs: list,
                       instance_outputs: list,
                       upstream_of_input: Dict[str, str]) -> list:
        """
        Optional validation for module wiring

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Verify at least one input is connected
        if len(instance_inputs) < 1:
            errors.append({
                "type": "error",
                "message": "String concatenator requires at least one input"
            })

        # Verify exactly one output
        if len(instance_outputs) != 1:
            errors.append({
                "type": "error",
                "message": "String concatenator must have exactly one output"
            })

        return errors