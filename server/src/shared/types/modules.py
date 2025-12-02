"""
Shared module type definitions and base classes
"""
from typing import Optional, List, Dict, Type, Any, Literal
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pydantic import BaseModel
from enum import Enum
from datetime import datetime

# Type alias for allowed node types - equivalent to TypeScript union: "str" | "float" | "datetime" | "date" | "time" | "bool" | "int"
AllowedNodeType = Literal["str", "float", "datetime", "date", "time", "bool", "int"]


class ModuleKind(str, Enum):
    """Module kind"""
    TRANSFORM = "transform"
    ACTION = "action"
    LOGIC = "logic"
    COMPARATOR = "comparator"
    MISC = "misc"
    OUTPUT = "output"


@dataclass(frozen=True)
class NodeTypeRule:
    """Type rule for a node group - either allowed_types list or type_var"""
    allowed_types: Optional[List[AllowedNodeType]] = None  # per-pin whitelist; user picks independently
    type_var: Optional[str] = None             # e.g., "T" (unifies across pins)


@dataclass(frozen=True)
class NodeGroup:
    """Definition of a group of nodes (pins) with cardinality constraints"""
    typing: NodeTypeRule
    label: str
    min_count: int = 1
    max_count: Optional[int] = 1


@dataclass(frozen=True)
class IOSideShape:
    """Shape definition for one side of I/O (inputs or outputs)"""
    nodes: List[NodeGroup] = field(default_factory=list)  # exact count, fixed order


@dataclass(frozen=True)
class IOShape:
    """Complete I/O shape definition for a module"""
    inputs: IOSideShape = field(default_factory=IOSideShape)
    outputs: IOSideShape = field(default_factory=IOSideShape)
    type_params: Dict[str, List[AllowedNodeType]] = field(default_factory=dict)


@dataclass(frozen=True)
class ModuleMeta:
    """Metadata defining I/O constraints for a module"""
    io_shape: IOShape = field(default_factory=IOShape)


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
    def validate_config(cls, cfg: BaseModel, inputs: List[Any], outputs: List[Any], services: Any = None) -> List[str]:
        """
        Optional custom config validation hook.
        Called after Pydantic schema validation passes.

        This method allows modules to implement custom validation logic that goes beyond
        basic schema validation. For example:
        - Validating SQL queries reference correct input/output pin names
        - Checking interdependent config fields
        - Validating external resource references
        - Checking database tables/schemas exist (requires services parameter)

        Args:
            cfg: Validated config instance (Pydantic model)
            inputs: List of input pins for this module instance (NodeInstance objects)
            outputs: List of output pins for this module instance (NodeInstance objects)
            services: Optional services container providing access to database connections, etc.

        Returns:
            List of error messages (empty list if valid)

        Example:
            @classmethod
            def validate_config(cls, cfg, inputs, outputs, services=None):
                errors = []
                input_names = {pin.name for pin in inputs}
                if cfg.required_input not in input_names:
                    errors.append(f"Config references undefined input: {cfg.required_input}")

                # Check database table exists (if services provided)
                if services and hasattr(cfg, 'table_name'):
                    db_conn = services.get_database_connection(cfg.database)
                    if not table_exists(db_conn, cfg.table_name):
                        errors.append(f"Table '{cfg.table_name}' does not exist in database")

                return errors
        """
        return []  # Default: no custom validation

    @classmethod
    def validate_wiring(cls,
                       module_instance_id: str,
                       cfg: Dict[str, Any],
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
    def run(self, inputs: Dict[str, Any], cfg: Any, context: Optional[Any], services: Optional[Any] = None) -> Dict[str, Any]:
        """
        Execute the module logic

        Args:
            inputs: Dictionary of input values keyed by node_id
            cfg: Validated configuration instance (Pydantic model)
            context: Execution context with I/O metadata (inputs/outputs pins)
            services: Service container for accessing databases, repositories, etc.

        Returns:
            Dictionary of output values keyed by node_id
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

class MiscModule(BaseModule):
    """
    Base class for Misc modules - modules that don't fit into any other category
    """
    kind = ModuleKind.MISC
    
    
class OutputModule(BaseModule):
    """
    Base class for Output modules - pipeline exit points that collect data for order processing.

    Output modules do NOT execute side effects directly. Instead, they:
    1. Define the inputs they need (via meta())
    2. Act as terminal nodes in the pipeline (no outputs)
    3. Have their input data collected by pipeline execution
    4. Pass that data to OutputExecutionService for actual processing

    The OutputExecutionService handles:
    - Creating or updating orders
    - Resolving addresses
    - Transferring PDF attachments
    - Sending emails
    - Other side effects that need full system context
    """
    kind = ModuleKind.OUTPUT

    def run(self, inputs: Dict[str, Any], cfg: Any, context: Optional[Any], services: Optional[Any] = None) -> Dict[str, Any]:
        """
        Output modules don't execute side effects directly.
        Returns empty dict - output modules have no pipeline outputs.
        """
        return {}


@dataclass(frozen=True)
class ModuleCreate:
    """Domain type for creating new module catalog entries"""
    id: str
    version: str
    name: str
    description: Optional[str]
    module_kind: ModuleKind
    meta: ModuleMeta
    config_schema: Dict[str, Any]
    handler_name: str
    color: str = "#3B82F6"
    category: str = "Processing"
    is_active: bool = True


@dataclass(frozen=True)
class ModuleUpdate:
    """Domain type for updating module catalog entries"""
    name: Optional[str] = None
    description: Optional[str] = None
    module_kind: Optional[ModuleKind] = None
    meta: Optional[ModuleMeta] = None
    config_schema: Optional[Dict[str, Any]] = None
    handler_name: Optional[str] = None
    color: Optional[str] = None
    category: Optional[str] = None
    is_active: Optional[bool] = None


@dataclass(frozen=True)
class Module:
    """Full module catalog domain object retrieved from database"""
    id: str
    version: str
    name: str
    description: Optional[str]
    module_kind: ModuleKind
    meta: ModuleMeta
    config_schema: Dict[str, Any]
    handler_name: str
    color: str
    category: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
