"""
Shared module type definitions and base classes
"""
from typing import Optional, List, Dict, Literal, Type, Any, TYPE_CHECKING
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field

from shared.exceptions.module_definitions import NotImplementedError

if TYPE_CHECKING:
    from .execution_context import ExecutionContext

# Type definitions
AllowedModuleTypes = Literal["str", "float", "datetime", "bool", "int"]
ModuleKind = Literal["transform", "action", "logic", "comparator"]


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

    @abstractmethod
    def run(self,
           inputs: Dict[str, Any],
           cfg: BaseModel,
           context: Optional['ExecutionContext'] = None) -> Dict[str, Any]:
        """
        Execute the module with given inputs and configuration

        Args:
            inputs: Input values keyed by node ID
            cfg: Validated configuration model instance
            context: ExecutionContext with node metadata and helper methods

        Returns:
            Output values keyed by node ID
        """
        raise NotImplementedError


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