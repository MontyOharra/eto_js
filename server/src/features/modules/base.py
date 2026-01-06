"""
Module Base Classes

Abstract base classes for transformation pipeline modules.
All module implementations inherit from these bases.
"""
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

from shared.types.modules import ModuleMeta, ModuleKind


class BaseModule(ABC):
    """
    Base class for all pipeline modules.

    Contains common fields and methods used across Transform/Logic/Comparator/Output modules.
    Subclasses must define class-level attributes and implement required methods.
    """

    # Class-level metadata (must be defined in subclasses)
    id: str
    version: str
    title: str
    description: str
    kind: ModuleKind
    ConfigModel: type[BaseModel]

    @classmethod
    @abstractmethod
    def meta(cls) -> ModuleMeta:
        """
        Return metadata about this module's I/O constraints.
        Must be implemented by each module.
        """
        return ModuleMeta()

    @classmethod
    def config_schema(cls) -> dict[str, Any]:
        """
        Return JSON Schema for this module's configuration.
        Generated from the ConfigModel Pydantic model.
        """
        return cls.ConfigModel.model_json_schema()

    @classmethod
    def config_class(cls) -> type[BaseModel]:
        """Return the ConfigModel class for this module."""
        return cls.ConfigModel

    @classmethod
    def validate_config(
        cls,
        cfg: BaseModel,
        inputs: list[Any],
        outputs: list[Any],
        services: Any = None
    ) -> list[str]:
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
            inputs: List of input pins for this module instance
            outputs: List of output pins for this module instance
            services: Optional services container providing access to database connections, etc.

        Returns:
            List of error messages (empty list if valid)
        """
        return []  # Default: no custom validation

    @classmethod
    def validate_wiring(
        cls,
        module_instance_id: str,
        cfg: dict[str, Any],
        instance_inputs: list[dict[str, Any]],
        instance_outputs: list[dict[str, Any]],
        upstream_of_input: dict[str, str]
    ) -> list[dict[str, Any]]:
        """
        Optional module-specific wiring validation hook.

        Args:
            module_instance_id: ID of this module instance in the pipeline
            cfg: Module configuration values
            instance_inputs: List of input pin definitions for this instance
            instance_outputs: List of output pin definitions for this instance
            upstream_of_input: Map of input pin ID -> upstream output pin ID

        Returns:
            List of validation errors (empty if valid)
        """
        return []

    @abstractmethod
    def run(
        self,
        inputs: dict[str, Any],
        cfg: Any,
        context: Any | None,
        services: Any | None = None
    ) -> dict[str, Any]:
        """
        Execute the module logic.

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
    Base class for Transform modules - pure functions that transform data.
    Transform modules are stateless and should have no side effects.
    """
    kind = ModuleKind.TRANSFORM


class LogicModule(BaseModule):
    """
    Base class for Logic modules - conditional and control flow modules.
    Logic modules handle branching, conditionals, and pipeline control flow.
    """
    kind = ModuleKind.LOGIC


class ComparatorModule(BaseModule):
    """
    Base class for Comparator modules - comparison and boolean evaluation modules.
    Comparator modules produce boolean outputs based on comparing inputs to config values.
    """
    kind = ModuleKind.COMPARATOR


class MiscModule(BaseModule):
    """
    Base class for Misc modules - modules that don't fit into any other category.
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

    def run(
        self,
        inputs: dict[str, Any],
        cfg: Any,
        context: Any | None,
        services: Any | None = None
    ) -> dict[str, Any]:
        """
        Output modules don't execute side effects directly.
        Returns empty dict - output modules have no pipeline outputs.
        """
        return {}
