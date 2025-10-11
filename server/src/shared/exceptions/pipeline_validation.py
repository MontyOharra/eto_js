"""
Pipeline validation exception classes
Defines exception classes that wrap validation result data models
"""
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from shared.types import PipelineValidationResult, PipelineValidationError


class PipelineValidationFailedException(Exception):
    """
    Raised when pipeline validation fails
    Carries the full ValidationResult for structured error handling in API responses
    """
    def __init__(self, validation_result: 'PipelineValidationResult'):
        # Import at runtime to avoid circular dependency
        from shared.types import PipelineValidationResult, PipelineValidationError
        self.validation_result: PipelineValidationResult = validation_result
        self.errors: List[PipelineValidationError] = validation_result.errors
        # Simple message for logging
        super().__init__(f"Pipeline validation failed with {len(self.errors)} error(s)")
