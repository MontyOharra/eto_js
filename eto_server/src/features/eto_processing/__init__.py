"""
ETO Processing Feature Module
Email-to-Order processing pipeline with template matching, data extraction, and transformation
"""

from .service import EtoProcessingService
from .template_matching_service import TemplateMatchingService
from .data_extraction_service import DataExtractionService
from .transformation_service import TransformationService
from .types import (
    EtoRun,
    ExtractionRule,
    ExtractionStep,
    ProcessingStepResult,
    EtoRunSummary
)

__all__ = [
    # Services
    'EtoProcessingService',
    'TemplateMatchingService',
    'DataExtractionService',
    'TransformationService',

    # Domain types
    'EtoRun',
    'ExtractionRule',
    'ExtractionStep',
    'ProcessingStepResult',
    'EtoRunSummary'
]