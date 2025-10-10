from typing import Literal

AllowedModuleTypes = Literal["str", "float", "datetime", "bool", "int"]
ModuleKind = Literal["transform", "action", "logic", "comparator"]
EtoRunStatus = Literal["not_started", "processing", "success", "failure", "needs_template", "skipped"]
EtoProcessingStep = Literal["template_matching", "extracting_data", "transforming_data"]
EtoErrorType = Literal["template_matching_error", "data_extraction_error", "transformation_error", "validation_error", "system_error"]