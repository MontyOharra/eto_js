"""
ETO Processing Feature Module
Email-to-Order processing pipeline with template matching, data extraction, and transformation
"""

from .service import (
    EtoProcessingService,
    get_eto_processing_service,
    init_eto_processing_service,
    start_eto_processing_service,
    stop_eto_processing_service
)
from .template_matching_service import (
    TemplateMatchingService,
    get_template_matching_service,
    init_template_matching_service
)
from .data_extraction_service import (
    DataExtractionService,
    get_data_extraction_service,
    init_data_extraction_service
)
from .transformation_service import (
    TransformationService,
    get_transformation_service,
    init_transformation_service
)
from .types import (
    EtoRun,
    ExtractionRule,
    ExtractionStep,
    ProcessingStepResult,
    EtoRunSummary
)

__all__ = [
    # Core service
    'EtoProcessingService',
    'get_eto_processing_service',
    'init_eto_processing_service', 
    'start_eto_processing_service',
    'stop_eto_processing_service',
    
    # Dependent services
    'TemplateMatchingService',
    'get_template_matching_service',
    'init_template_matching_service',
    'DataExtractionService',
    'get_data_extraction_service',
    'init_data_extraction_service',
    'TransformationService',
    'get_transformation_service',
    'init_transformation_service',
    
    # Domain types
    'EtoRun',
    'ExtractionRule',
    'ExtractionStep',
    'ProcessingStepResult',
    'EtoRunSummary'
]