"""
Shared module type definitions and base classes
"""
from typing import Optional, List, Dict, Literal, Type, Any, TYPE_CHECKING
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field, ConfigDict

from .pipeline_state import InstanceNodePin
from .enums import AllowedModuleTypes, ModuleKind

from shared.exceptions import NotImplementedError


class NodeTypeRule(BaseModel):
    """Type rule for a node group - either allowed_types list or type_var"""
    # exactly one of these is AllowedModuleTypes
    allowed_types: Optional[List[AllowedModuleTypes]] = None  # per-pin whitelist; user picks independently
    type_var: Optional[str] = None             # e.g., "T" (unifies across pins)


class NodeGroup(BaseModel):
    """Definition of a group of nodes (pins) with cardinality constraints"""
    min_count: int = 1
    max_count: Optional[int] = 1
    typing: NodeTypeRule
    label: str


class IOSideShape(BaseModel):
    """Shape definition for one side of I/O (inputs or outputs)"""
    nodes: List[NodeGroup] = []  # exact count, fixed order


class IOShape(BaseModel):
    """Complete I/O shape definition for a module"""
    inputs: IOSideShape = IOSideShape()
    outputs: IOSideShape = IOSideShape()
    type_params: Dict[str, List[AllowedModuleTypes]] = Field(default_factory=dict)


class ModuleMeta(BaseModel):
    """Metadata defining I/O constraints for a module"""
    io_shape: IOShape = IOShape()


class ModuleExecutionContext(BaseModel):
    """Context passed to module handlers with node metadata and helpers"""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    inputs: List[InstanceNodePin]      # Input pins metadata
    outputs: List[InstanceNodePin]     # Output pins metadata
    module_instance_id: str             # For debugging/logging
    services: Optional[Any] = None      # Access to service container (ServiceContainer type)

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


class BaseModule(ABC):
    """
    Shared core functionality for all module types
    Contains common fields and methods used across Transform/Action/Logic/Comparator modules
    """

    # Class-level metadata (must be defined in subclasses)
    id: str
    version: str
    title: str
    description: str
    kind: ModuleKind
    ConfigModel: Type[BaseModel]

    @classmethod
    @abstractmethod
    def meta(cls) -> ModuleMeta:
        """
        Return metadata about this module's I/O constraints
        Must be implemented by each module
        """
        return ModuleMeta()

    @classmethod
    def config_schema(cls) -> Dict[str, Any]:
        """
        Return JSON Schema for this module's configuration
        Generated from the ConfigModel Pydantic model
        """
        return cls.ConfigModel.model_json_schema()
    
    @classmethod
    def config_class(cls) -> Type[BaseModel]:
        """
        Return the ConfigModel class for this module
        """
        return cls.ConfigModel

    @classmethod
    def validate_wiring(cls,
                       module_instance_id: str,
                       config: Dict[str, Any],
                       instance_inputs: List[Dict[str, Any]],
                       instance_outputs: List[Dict[str, Any]],
                       upstream_of_input: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        Optional module-specific wiring validation hook

        Args:
            module_instance_id: ID of this module instance in the pipeline
            config: Module configuration values
            instance_inputs: List of input pin definitions for this instance
            instance_outputs: List of output pin definitions for this instance
            upstream_of_input: Map of input pin ID -> upstream output pin ID

        Returns:
            List of validation errors (empty if valid)
        """
        return []

    def run(self,
           inputs: Dict[str, Any],
           cfg: BaseModel,
           context: Optional['ModuleExecutionContext'] = None) -> Dict[str, Any]:
        """
        Execute the module with given inputs and configuration

        Args:
            inputs: Input values keyed by node ID
            cfg: Validated configuration model instance
            context: ExecutionContext with node metadata and helper methods

        Returns:
            Output values keyed by node ID
        """
        # Provide helpful error message with module information
        module_id = f"{self.id}:{self.version}"
        module_class_name = self.__class__.__name__
        raise NotImplementedError(module_id=module_id, module_class_name=module_class_name)


class TransformModule(BaseModule):
    """
    Base class for Transform modules - pure functions that transform data
    Transform modules are stateless and should have no side effects
    """
    kind: ModuleKind = "transform"


class ActionModule(BaseModule):
    """
    Base class for Action modules - modules that perform side effects
    Action modules may modify external state and require special handling
    """
    kind: ModuleKind = "action"


class LogicModule(BaseModule):
    """
    Base class for Logic modules - conditional and control flow modules
    Logic modules handle branching, conditionals, and pipeline control flow
    """
    kind: ModuleKind = "logic"


class ComparatorModule(BaseModule):
    """
    Base class for Comparator modules - comparison and boolean evaluation modules
    Comparator modules produce boolean outputs based on comparing inputs to config values
    """
    kind: ModuleKind = "comparator"
    
