"""
Core Module Contracts - Base classes and type definitions
Based on the transformation pipeline design document
"""
from typing import Optional, Literal, Dict, Any, List, Union, Type
from pydantic import BaseModel, Field
from abc import ABC, abstractmethod


# Type definitions
Scalar = Literal["str", "int", "float", "datetime", "bool"]


class DynamicSide(BaseModel):
    """Configuration for dynamic I/O behavior on one side (inputs or outputs)"""
    allow: bool = True
    min_count: int = 0
    max_count: Optional[int] = None  # None = unbounded
    type: List[Scalar] = Field(default=["str"])  # Array of allowed types - empty array means all types allowed


class ModuleMeta(BaseModel):
    """Metadata defining I/O constraints for a module"""
    inputs: DynamicSide = DynamicSide()   # one dynamic list per side
    outputs: DynamicSide = DynamicSide()  # one dynamic list per side


class CommonCore(ABC):
    """
    Shared core functionality for all module types
    Contains common fields and methods used across Transform/Action/Logic modules
    """

    # Class-level metadata (must be defined in subclasses)
    id: str
    version: str
    title: str
    description: str
    kind: Literal["transform", "action", "logic"] = "transform"

    # Configuration model type - must be defined in subclasses
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
           context: Any = None) -> Dict[str, Any]:
        """
        Execute the module with given inputs and configuration

        Args:
            inputs: Input values keyed by node ID
            cfg: Validated configuration model instance
            context: Execution context with ordered inputs/outputs and other runtime info

        Returns:
            Output values keyed by node ID
        """
        raise NotImplementedError


class TransformModule(CommonCore):
    """
    Base class for Transform modules - pure functions that transform data
    Transform modules are stateless and should have no side effects
    """
    kind: Literal["transform"] = "transform"


class ActionModule(CommonCore):
    """
    Base class for Action modules - modules that perform side effects
    Action modules may modify external state and require special handling
    """
    kind: Literal["action"] = "action"


class LogicModule(CommonCore):
    """
    Base class for Logic modules - conditional and control flow modules
    Logic modules handle branching, conditionals, and pipeline control flow
    """
    kind: Literal["logic"] = "logic"