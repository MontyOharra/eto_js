"""
Output Definitions

Abstract base class and concrete implementations for output module processing.
Each definition handles order creation/update logic for a specific output module type.
"""

from features.pipeline_results.output_definitions.base import OutputDefinitionBase

__all__ = [
    "OutputDefinitionBase",
]
