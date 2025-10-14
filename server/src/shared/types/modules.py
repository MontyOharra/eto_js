"""
Shared module type definitions and base classes
"""
from typing import Optional, List, Dict, Type, Any
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from enum import Enum

class AllowedModuleNodeTypes(str, Enum):
    """Allowed module types"""
    STR = "str"
    FLOAT = "float"
    DATETIME = "datetime"
    BOOL = "bool"
    INT = "int"
    
class ModuleKind(str, Enum):
    """Module kind"""
    TRANSFORM = "transform"
    ACTION = "action"
    LOGIC = "logic"
    COMPARATOR = "comparator"


class NodeTypeRule(BaseModel):
    """Type rule for a node group - either allowed_types list or type_var"""
    # exactly one of these is AllowedModuleNodeTypes
    allowed_types: Optional[List[AllowedModuleNodeTypes]] = None  # per-pin whitelist; user picks independently
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
    type_params: Dict[str, List[AllowedModuleNodeTypes]] = Field(default_factory=dict)


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


class TransformModule(BaseModule):
    """
    Base class for Transform modules - pure functions that transform data
    Transform modules are stateless and should have no side effects
    """
    kind = ModuleKind.TRANSFORM

class ActionModule(BaseModule):
    """
    Base class for Action modules - modules that perform side effects
    Action modules may modify external state and require special handling
    """
    kind = ModuleKind.ACTION

class LogicModule(BaseModule):
    """
    Base class for Logic modules - conditional and control flow modules
    Logic modules handle branching, conditionals, and pipeline control flow
    """
    kind = ModuleKind.LOGIC

class ComparatorModule(BaseModule):
    """
    Base class for Comparator modules - comparison and boolean evaluation modules
    Comparator modules produce boolean outputs based on comparing inputs to config values
    """
    kind = ModuleKind.COMPARATOR
    
