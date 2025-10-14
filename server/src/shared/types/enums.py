from enum import Enum

class EtoRunStatus(str, Enum):
    """ETO run status states"""
    NOT_STARTED = "not_started"      # Initial state - no processing has begun
    PROCESSING = "processing"        # Currently being processed
    SUCCESS = "success"              # Successfully completed end-to-end
    FAILURE = "failure"              # Failed at some point - see error fields
    NEEDS_TEMPLATE = "needs_template" # Template matching failed - needs new template
    SKIPPED = "skipped"              # Intentionally skipped (e.g., duplicate, filtered out)


class EtoProcessingStep(str, Enum):
    """Current step when status=processing"""
    TEMPLATE_MATCHING = "template_matching"    # Finding matching template
    EXTRACTING_DATA = "extracting_data"        # Extracting field values
    TRANSFORMING_DATA = "transforming_data"    # Running transformation pipeline


class EtoErrorType(str, Enum):
    """Error categorization for failures"""
    TEMPLATE_MATCHING_ERROR = "template_matching_error"    # No template found/matched
    DATA_EXTRACTION_ERROR = "data_extraction_error"       # Field extraction failed
    TRANSFORMATION_ERROR = "transformation_error"         # Pipeline transformation failed
    VALIDATION_ERROR = "validation_error"                 # Data validation failed
    SYSTEM_ERROR = "system_error"                        # Infrastructure/unexpected errors