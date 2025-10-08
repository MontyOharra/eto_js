"""
Execution Context Model
Provides context and helper methods for module execution with node metadata
"""
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

from .pipeline_state import InstanceNodePin

class ExecutionContext(BaseModel):
    """Context passed to module handlers with node metadata and helpers"""
    inputs: List[InstanceNodePin]      # Input pins metadata
    outputs: List[InstanceNodePin]     # Output pins metadata
    module_instance_id: str             # For debugging/logging
    run_id: str                         # Execution run ID

    def get_input_type(self, index: int = 0) -> str:
        """Get type of input at given index"""
        if not self.inputs:
            raise IndexError("No inputs in context")
        if index >= len(self.inputs):
            raise IndexError(f"Input index {index} out of range")
        return self.inputs[index].type

    def get_output_type(self, index: int = 0) -> str:
        """Get type of output at given index"""
        if not self.outputs:
            raise IndexError("No outputs in context")
        if index >= len(self.outputs):
            raise IndexError(f"Output index {index} out of range")
        return self.outputs[index].type

    def get_input_names(self) -> Dict[str, str]:
        """Get mapping of node_id to user-assigned names"""
        return {pin.node_id: pin.name for pin in self.inputs}

    def get_output_names(self) -> Dict[str, str]:
        """Get mapping of node_id to user-assigned names"""
        return {pin.node_id: pin.name for pin in self.outputs}

    def resolve_placeholders(self, template: str, inputs: Dict[str, Any]) -> str:
        """Replace {name} placeholders with actual values"""
        result = template
        # Replace input placeholders
        for pin in self.inputs:
            placeholder = f"{{{pin.name}}}"
            value = inputs.get(pin.node_id, "")
            result = result.replace(placeholder, str(value))
        # Also support output placeholders for prompts
        for pin in self.outputs:
            placeholder = f"{{{pin.name}}}"
            # Keep output placeholders as-is for LLM to understand
            result = result.replace(placeholder, f"[{pin.name}]")
        return result

    def get_input_by_name(self, name: str, inputs: Dict[str, Any]) -> Any:
        """Get input value by user-assigned name"""
        for pin in self.inputs:
            if pin.name == name:
                return inputs.get(pin.node_id)
        raise KeyError(f"No input with name '{name}'")

    def get_input_groups(self) -> Dict[int, List[InstanceNodePin]]:
        """Get inputs organized by group"""
        groups: Dict[int, List[InstanceNodePin]] = {}
        for pin in self.inputs:
            if pin.group_index not in groups:
                groups[pin.group_index] = []
            groups[pin.group_index].append(pin)
        return groups

    def get_output_groups(self) -> Dict[int, List[InstanceNodePin]]:
        """Get outputs organized by group"""
        groups: Dict[int, List[InstanceNodePin]] = {}
        for pin in self.outputs:
            if pin.group_index not in groups:
                groups[pin.group_index] = []
            groups[pin.group_index].append(pin)
        return groups