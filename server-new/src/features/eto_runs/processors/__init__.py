"""
ETO Run Processors
Stage-specific processing logic for ETO workflow
"""
from .template_matching import TemplateMatchingProcessor
from .data_extraction import DataExtractionProcessor
from .data_transformation import DataTransformationProcessor

__all__ = [
    'TemplateMatchingProcessor',
    'DataExtractionProcessor',
    'DataTransformationProcessor'
]
