"""ETO Processing specific exceptions"""
from typing import Optional
from .service import ServiceError
from ..models.eto_processing import EtoErrorType, EtoProcessingStep


class EtoProcessingError(ServiceError):
    """Base exception for ETO processing pipeline failures"""

    def __init__(
        self,
        message: str,
        eto_run_id: int,
        error_type: EtoErrorType,
        processing_step: EtoProcessingStep,
        original_exception: Optional[Exception] = None
    ):
        super().__init__(message)
        self.eto_run_id = eto_run_id
        self.error_type = error_type
        self.processing_step = processing_step
        self.original_exception = original_exception

    def __str__(self) -> str:
        base_msg = f"ETO Run {self.eto_run_id} failed at {self.processing_step.value}: {super().__str__()}"
        if self.original_exception:
            base_msg += f" (caused by: {self.original_exception})"
        return base_msg


class EtoStatusValidationError(EtoProcessingError):
    """ETO run status validation failed - wrong state for operation"""

    def __init__(
        self,
        eto_run_id: int,
        processing_step: EtoProcessingStep,
        current_status: str,
        expected_status: str,
        additional_requirements: Optional[str] = None
    ):
        message = f"Invalid status '{current_status}' for {processing_step.value}, expected '{expected_status}'"
        if additional_requirements:
            message += f" and {additional_requirements}"

        super().__init__(
            message=message,
            eto_run_id=eto_run_id,
            error_type=EtoErrorType.VALIDATION_ERROR,
            processing_step=processing_step
        )
        self.current_status = current_status
        self.expected_status = expected_status
        self.additional_requirements = additional_requirements


class EtoTemplateMatchingError(EtoProcessingError):
    """Template matching step failed"""

    def __init__(self, eto_run_id: int, message: str, original_exception: Optional[Exception] = None):
        super().__init__(
            message=message,
            eto_run_id=eto_run_id,
            error_type=EtoErrorType.TEMPLATE_MATCHING_ERROR,
            processing_step=EtoProcessingStep.TEMPLATE_MATCHING,
            original_exception=original_exception
        )


class EtoDataExtractionError(EtoProcessingError):
    """Data extraction step failed"""

    def __init__(self, eto_run_id: int, message: str, original_exception: Optional[Exception] = None):
        super().__init__(
            message=message,
            eto_run_id=eto_run_id,
            error_type=EtoErrorType.DATA_EXTRACTION_ERROR,
            processing_step=EtoProcessingStep.EXTRACTING_DATA,
            original_exception=original_exception
        )


class EtoTransformationError(EtoProcessingError):
    """Data transformation step failed"""

    def __init__(self, eto_run_id: int, message: str, original_exception: Optional[Exception] = None):
        super().__init__(
            message=message,
            eto_run_id=eto_run_id,
            error_type=EtoErrorType.TRANSFORMATION_ERROR,
            processing_step=EtoProcessingStep.TRANSFORMING_DATA,
            original_exception=original_exception
        )