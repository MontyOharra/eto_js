"""
Shared module type definitions and base classes
"""
from typing import Optional, List, Dict, Type, Any
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pydantic import BaseModel
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


@dataclass(frozen=True)
class NodeTypeRule:
    """Type rule for a node group - either allowed_types list or type_var"""
    # exactly one of these is AllowedModuleNodeTypes
    allowed_types: Optional[List[AllowedModuleNodeTypes]] = None  # per-pin whitelist; user picks independently
    type_var: Optional[str] = None             # e.g., "T" (unifies across pins)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'allowed_types': [t.value if isinstance(t, AllowedModuleNodeTypes) else t for t in self.allowed_types] if self.allowed_types else None,
            'type_var': self.type_var
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "NodeTypeRule":
        """Create from dictionary"""
        return NodeTypeRule(
            allowed_types=[AllowedModuleNodeTypes(t) for t in data.get('allowed_types', [])] if data.get('allowed_types') else None,
            type_var=data.get('type_var')
        )


@dataclass(frozen=True)
class NodeGroup:
    """Definition of a group of nodes (pins) with cardinality constraints"""
    typing: NodeTypeRule
    label: str
    min_count: int = 1
    max_count: Optional[int] = 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'min_count': self.min_count,
            'max_count': self.max_count,
            'typing': self.typing.to_dict(),
            'label': self.label
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "NodeGroup":
        """Create from dictionary"""
        return NodeGroup(
            typing=NodeTypeRule.from_dict(data['typing']),
            label=data['label'],
            min_count=data.get('min_count', 1),
            max_count=data.get('max_count', 1)
        )


@dataclass(frozen=True)
class IOSideShape:
    """Shape definition for one side of I/O (inputs or outputs)"""
    nodes: List[NodeGroup] = field(default_factory=list)  # exact count, fixed order

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'nodes': [node.to_dict() for node in self.nodes]
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "IOSideShape":
        """Create from dictionary"""
        return IOSideShape(
            nodes=[NodeGroup.from_dict(node) for node in data.get('nodes', [])]
        )


@dataclass(frozen=True)
class IOShape:
    """Complete I/O shape definition for a module"""
    inputs: IOSideShape = field(default_factory=IOSideShape)
    outputs: IOSideShape = field(default_factory=IOSideShape)
    type_params: Dict[str, List[AllowedModuleNodeTypes]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'inputs': self.inputs.to_dict(),
            'outputs': self.outputs.to_dict(),
            'type_params': {
                key: [t.value if isinstance(t, AllowedModuleNodeTypes) else t for t in types]
                for key, types in self.type_params.items()
            }
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "IOShape":
        """Create from dictionary"""
        return IOShape(
            inputs=IOSideShape.from_dict(data.get('inputs', {})),
            outputs=IOSideShape.from_dict(data.get('outputs', {})),
            type_params={
                key: [AllowedModuleNodeTypes(t) for t in types]
                for key, types in data.get('type_params', {}).items()
            }
        )


@dataclass(frozen=True)
class ModuleMeta:
    """Metadata defining I/O constraints for a module"""
    io_shape: IOShape = field(default_factory=IOShape)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'io_shape': self.io_shape.to_dict()
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ModuleMeta":
        """Create from dictionary (replaces Pydantic model_validate)"""
        return ModuleMeta(
            io_shape=IOShape.from_dict(data.get('io_shape', {}))
        )


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
    
    @abstractmethod
    def run(self, inputs: Dict[str, Any], config: Dict[str, Any], context: Optional[Any]) -> Dict[str, Any]:
        """
        Execute the module logic
        """
        return {}

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
