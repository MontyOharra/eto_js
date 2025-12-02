"""
Pipeline Validation Exceptions
Exception classes for pipeline validation stages
"""
from typing import Optional, Dict, Any
from .service import ValidationError


class PipelineValidationError(ValidationError):
    """
    Base exception for all pipeline validation failures (400)

    Throws on first error encountered during validation.
    """

    def __init__(self, message: str, code: str, where: Optional[Dict[str, Any]] = None):
        """
        Initialize pipeline validation error

        Args:
            message: Human-readable error message
            code: Error code (e.g., "duplicate_node_id", "type_mismatch")
            where: Optional context (node_id, module_id, etc.)
        """
        self.code = code
        self.where = where
        super().__init__(message)


class SchemaValidationError(PipelineValidationError):
    """
    Stage 1: Schema validation failed

    Raised when basic schema validation fails:
    - Duplicate node IDs
    - Invalid pin types
    - Malformed module references
    """
    pass


class ModuleValidationError(PipelineValidationError):
    """
    Stage 3: Module validation failed

    Raised when module-level validation fails:
    - Module not found in catalog
    - Group cardinality violations
    - Type variable unification errors
    - Invalid config
    - No output modules present
    """
    pass


class EdgeValidationError(PipelineValidationError):
    """
    Stage 4: Edge validation failed

    Raised when connection validation fails:
    - Missing upstream connections
    - Multiple upstream connections
    - Type mismatches
    - Self-loops
    """
    pass


class GraphValidationError(PipelineValidationError):
    """
    Stage 5: Graph validation failed

    Raised when graph structure validation fails:
    - Cycles detected (not a DAG)
    """
    pass
