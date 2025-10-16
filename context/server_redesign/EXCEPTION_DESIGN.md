# Server Redesign - Exception Design

## Overview

This document defines the exception hierarchy for the ETO processing system. The design philosophy emphasizes:

1. **Type-based semantics**: The exception class itself conveys meaning, not string error codes
2. **Minimal data**: Only include data necessary to understand what specifically failed
3. **Bubbling hierarchy**: Exceptions inherit to allow flexible catch patterns
4. **Simple serialization**: Easy conversion to dict for database storage
5. **Context-aware**: ETO run context already knows run_id and phase, no need to duplicate

---

## Design Principles

### Exception Hierarchy Purpose

The exception hierarchy enables flexible error handling at different levels:

```python
# Catch specific error
try:
    template_matching_func()
except NoTemplateMatchError:
    log.warning("No template matched")
    # Handle specifically

# Catch any template matching error
try:
    template_matching_func()
except TemplateMatchingError as e:
    log.error(f"Template matching failed: {e}")
    # Handle any template matching issue

# Catch any ETO processing error
try:
    process_eto_run()
except ETOProcessingError as e:
    # Save to database
    save_error_to_run(e)
```

### Critical vs Non-Critical

- **Non-Critical**: Specific, expected failure modes that we've explicitly designed for (no template match, validation failure, corrupted PDF, database connection lost, etc.)
- **Critical**: Catch-all for unexpected/unhandled errors indicating code bugs, import failures, syntax errors, or anything unanticipated

**Example**: `PDFSignatureExtractionError` is non-critical (we expect PDFs might be corrupted), but `TemplateMatchingCriticalError` is critical (something broke that we didn't plan for)

### Database Storage

Each exception provides `to_dict()` for serialization:

```python
try:
    raise ExtractionFieldNotFoundError("invoice_date")
except ETOProcessingError as e:
    error_data = e.to_dict()
    # {
    #   'exception_type': 'ExtractionFieldNotFoundError',
    #   'message': "Extraction field 'invoice_date' not found in PDF",
    #   'context': {'field_name': 'invoice_date'}
    # }

    eto_run.error_type = error_data['exception_type']
    eto_run.error_message = error_data['message']
    eto_run.error_details = json.dumps(error_data['context'])
```

---

## Base Exception Classes

### ETOProcessingError

```python
class ETOProcessingError(Exception):
    """Base exception for all ETO processing errors"""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize exception for database storage"""
        return {
            'exception_type': self.__class__.__name__,
            'message': str(self),
            'context': {k: v for k, v in self.__dict__.items()
                       if not k.startswith('_') and k not in ('args',)}
        }
```

**Purpose**: Root of all ETO exceptions, provides serialization

**Usage**:
- Catch at outermost level to handle any ETO error
- Never raised directly (use specific subclasses)

---

## Phase 1: Template Matching Exceptions

### Hierarchy

```
ETOProcessingError
└── TemplateMatchingError
    ├── NoTemplateMatchError
    ├── PDFSignatureExtractionError
    ├── TemplateDataCorruptedError
    ├── TemplateMatchingDatabaseError
    └── TemplateMatchingCriticalError (catch-all for unexpected errors)
```

### Base Exception

#### TemplateMatchingError

```python
class TemplateMatchingError(ETOProcessingError):
    """Base exception for template matching phase errors"""
    pass
```

**Purpose**: Base class for all template matching errors

**When to catch**: When you want to handle any template matching failure generically

**When to raise**: Never directly (use specific subclasses)

---

### Specific Expected Errors

---

#### NoTemplateMatchError

```python
class NoTemplateMatchError(TemplateMatchingError):
    """PDF signature did not match any template"""

    def __init__(self, pdf_file_id: int, templates_checked: int):
        self.pdf_file_id = pdf_file_id
        self.templates_checked = templates_checked
        super().__init__(
            f"No template matched PDF {pdf_file_id} "
            f"(checked {templates_checked} templates)"
        )
```

**Purpose**: No template matched the PDF signature (includes case where no templates exist)

**When to raise**:
- Template matching service finds no active templates in database
- Template matching service checks all templates and finds no match

**Context data**:
- `pdf_file_id`: ID of the PDF being matched
- `templates_checked`: Number of active templates that were checked (0 if none exist)

**Recovery**: User creates new template or manually selects existing template

**Example**:
```python
def match_template(pdf_file_id: int) -> PdfTemplate:
    templates = self.template_repo.get_templates_for_matching()

    if not templates:
        raise NoTemplateMatchError(pdf_file_id, templates_checked=0)

    for template in templates:
        if signature_matches(pdf, template):
            return template

    raise NoTemplateMatchError(pdf_file_id, templates_checked=len(templates))
```

---

#### PDFSignatureExtractionError

```python
class PDFSignatureExtractionError(TemplateMatchingError):
    """Failed to extract signature objects from PDF for matching"""

    def __init__(self, pdf_file_id: int, error: str):
        self.pdf_file_id = pdf_file_id
        self.extraction_error = error
        super().__init__(
            f"Could not extract signature from PDF {pdf_file_id}: {error}"
        )
```

**Purpose**: Cannot read/parse PDF to extract signature objects

**When to raise**:
- PDF file is corrupted or unreadable
- PDF parsing library returns error
- PDF signature objects are missing/corrupted in database

**Context data**:
- `pdf_file_id`: ID of the problematic PDF
- `extraction_error`: Details about what failed

**User message**: "Error reading PDF signature: file may be corrupted."

**Example**:
```python
def extract_signature(pdf_file_id: int) -> List[SignatureObject]:
    try:
        pdf = self.pdf_service.get_pdf(pdf_file_id)
        signature_objects = extract_signature_objects(pdf.objects_json)
        return signature_objects
    except (PDFCorruptedError, JSONDecodeError) as e:
        raise PDFSignatureExtractionError(pdf_file_id, str(e))
```

---

#### TemplateDataCorruptedError

```python
class TemplateDataCorruptedError(TemplateMatchingError):
    """Template signature data is corrupted or invalid"""

    def __init__(self, template_id: int, error: str):
        self.template_id = template_id
        self.corruption_details = error
        super().__init__(
            f"Template {template_id} has corrupted signature data: {error}"
        )
```

**Purpose**: Template's stored signature data cannot be parsed or is invalid

**When to raise**:
- Template signature_objects JSON is malformed
- Template signature_objects contains invalid data types
- Template version data is missing or corrupted

**Context data**:
- `template_id`: ID of the corrupted template
- `corruption_details`: Details about what's corrupted

**User message**: "Template data is corrupted. Please recreate the template."

**Example**:
```python
def load_template_signatures(template: PdfTemplate) -> List[SignatureObject]:
    try:
        signature_data = json.loads(template.signature_objects)
        return [SignatureObject(**obj) for obj in signature_data]
    except (JSONDecodeError, ValidationError) as e:
        raise TemplateDataCorruptedError(template.id, str(e))
```

---

#### TemplateMatchingDatabaseError

```python
class TemplateMatchingDatabaseError(TemplateMatchingError):
    """Database error while fetching templates"""

    def __init__(self, error: str):
        self.database_error = error
        super().__init__(f"Database error during template matching: {error}")
```

**Purpose**: Database connection or query failed during template matching

**When to raise**:
- Database connection lost
- SQL query error
- Repository-level exception that isn't handled

**Context data**:
- `database_error`: Original database error message

**User message**: "Database connection error. Please try again later."

**Example**:
```python
def get_templates_for_matching(self) -> List[PdfTemplate]:
    try:
        return self.template_repo.get_templates_for_matching()
    except RepositoryError as e:
        raise TemplateMatchingDatabaseError(str(e))
```

---

### Critical Error (Catch-All)

#### TemplateMatchingCriticalError

```python
class TemplateMatchingCriticalError(TemplateMatchingError):
    """Critical error in template matching (unexpected system failure)"""

    def __init__(self, error: str):
        self.original_error = error
        super().__init__(f"Critical error in template matching: {error}")
```

**Purpose**: Catch-all for any unexpected/unhandled error during template matching

**When to raise**:
- Import failures (module can't be imported)
- Syntax errors in code
- Unhandled exceptions we didn't anticipate
- Any `Exception` caught in outer try/except that isn't a specific TemplateMatchingError

**Context data**:
- `original_error`: Full error message from unexpected exception

**User message**: "A critical system error occurred. Please contact support."

**Example**:
```python
def match_template(pdf_file_id: int) -> PdfTemplate:
    try:
        templates = self._get_active_templates()
        signature = self._extract_signature(pdf_file_id)
        return self._find_best_match(signature, templates)
    except NoTemplateMatchError as e:
        raise e
    except PDFSignatureExtractionError as e:
        raise e
    except TemplateDataCorruptedError as e:
        raise e
    except TemplateMatchingDatabaseError as e:
        raise e
    except Exception as e:
        # Something unexpected happened - wrap in critical error
        raise TemplateMatchingCriticalError(str(e))
```

---

## Phase 2: Data Extraction Exceptions

### Hierarchy

```
ETOProcessingError
└── DataExtractionError
    ├── ExtractionFieldNotFoundError
    ├── ExtractionFieldValidationError
    ├── RequiredFieldMissingError
    ├── ExtractionFieldTypeError
    ├── PDFObjectAccessError
    ├── BoundingBoxInvalidError
    ├── ExtractionFieldDefinitionError
    └── DataExtractionCriticalError (catch-all for unexpected errors)
```

### Base Exception

#### DataExtractionError

```python
class DataExtractionError(ETOProcessingError):
    """Base exception for data extraction phase errors"""
    pass
```

**Purpose**: Base class for all data extraction errors

**When to catch**: When you want to handle any data extraction failure generically

**When to raise**: Never directly (use specific subclasses)

---

### Specific Expected Errors

---

#### ExtractionFieldNotFoundError

```python
class ExtractionFieldNotFoundError(DataExtractionError):
    """Extraction field bounding box found no text in PDF"""

    def __init__(self, field_name: str, bounding_box: Dict[str, float]):
        self.field_name = field_name
        self.bounding_box = bounding_box
        super().__init__(
            f"Extraction field '{field_name}' found no text at bounding box {bounding_box}"
        )
```

**Purpose**: Bounding box region contains no extractable text

**When to raise**:
- Bounding box overlays empty area of PDF
- Text exists but is not recognized by extraction algorithm
- Bounding box is positioned incorrectly

**Context data**:
- `field_name`: Name of the extraction field
- `bounding_box`: Coordinates of the bounding box (x, y, width, height)

**User message**: "Field '{field_name}' not found in PDF. Please verify template or enter manually."

**Example**:
```python
def extract_field(field: ExtractionField, pdf_objects: List[PdfObject]) -> str:
    text = extract_text_from_bounding_box(field.bounding_box, pdf_objects)
    if not text or text.strip() == "":
        raise ExtractionFieldNotFoundError(field.name, field.bounding_box)
    return text
```

---

#### ExtractionFieldValidationError

```python
class ExtractionFieldValidationError(DataExtractionError):
    """Extracted text failed regex validation"""

    def __init__(self, field_name: str, extracted_value: str, expected_pattern: str):
        self.field_name = field_name
        self.extracted_value = extracted_value
        self.expected_pattern = expected_pattern
        super().__init__(
            f"Extraction field '{field_name}' value '{extracted_value}' "
            f"does not match pattern '{expected_pattern}'"
        )
```

**Purpose**: Extracted text does not match configured regex pattern

**When to raise**:
- Text extracted successfully but fails validation regex
- Format doesn't match expected (e.g., date format wrong)

**Context data**:
- `field_name`: Name of the extraction field
- `extracted_value`: Text that was extracted
- `expected_pattern`: Regex pattern that was expected

**User message**: "Field '{field_name}' has invalid format. Expected: {pattern}. Got: {value}"

**Example**:
```python
def validate_extracted_field(field: ExtractionField, value: str) -> str:
    if field.validation_regex:
        if not re.match(field.validation_regex, value):
            raise ExtractionFieldValidationError(
                field.name,
                value,
                field.validation_regex
            )
    return value
```

---

#### RequiredFieldMissingError

```python
class RequiredFieldMissingError(DataExtractionError):
    """Required extraction field is empty or null"""

    def __init__(self, field_name: str):
        self.field_name = field_name
        super().__init__(f"Required field '{field_name}' is missing or empty")
```

**Purpose**: Field marked as required produced no value

**When to raise**:
- Required field extracted as empty string
- Required field extraction returned None

**Context data**:
- `field_name`: Name of the required field

**User message**: "Required field '{field_name}' is missing. Please provide a value."

**Example**:
```python
def check_required_fields(extracted_data: Dict[str, Any], fields: List[ExtractionField]):
    for field in fields:
        if field.is_required:
            value = extracted_data.get(field.name)
            if not value or (isinstance(value, str) and value.strip() == ""):
                raise RequiredFieldMissingError(field.name)
```

---

#### ExtractionFieldTypeError

```python
class ExtractionFieldTypeError(DataExtractionError):
    """Cannot coerce extracted text to expected type"""

    def __init__(self, field_name: str, extracted_value: str, expected_type: str):
        self.field_name = field_name
        self.extracted_value = extracted_value
        self.expected_type = expected_type
        super().__init__(
            f"Cannot convert field '{field_name}' value '{extracted_value}' "
            f"to type '{expected_type}'"
        )
```

**Purpose**: Extracted text cannot be converted to expected data type

**When to raise**:
- Cannot parse string to integer (e.g., "abc" → int)
- Cannot parse string to float (e.g., "12.34.56" → float)
- Cannot parse string to date (e.g., "not-a-date" → datetime)

**Context data**:
- `field_name`: Name of the extraction field
- `extracted_value`: Text that was extracted
- `expected_type`: Expected type (int, float, datetime, etc.)

**User message**: "Field '{field_name}' has invalid type. Expected {expected_type}, got '{extracted_value}'"

**Example**:
```python
def coerce_field_type(field: ExtractionField, value: str) -> Any:
    try:
        if field.field_type == "int":
            return int(value)
        elif field.field_type == "float":
            return float(value)
        elif field.field_type == "datetime":
            return datetime.fromisoformat(value)
        return value
    except (ValueError, TypeError) as e:
        raise ExtractionFieldTypeError(field.name, value, field.field_type)
```

---

#### PDFObjectAccessError

```python
class PDFObjectAccessError(DataExtractionError):
    """Cannot access PDF objects for extraction"""

    def __init__(self, pdf_file_id: int, error: str):
        self.pdf_file_id = pdf_file_id
        self.access_error = error
        super().__init__(
            f"Cannot access PDF objects for PDF {pdf_file_id}: {error}"
        )
```

**Purpose**: PDF objects cannot be loaded or accessed for extraction

**When to raise**:
- PDF objects_json is missing or null in database
- PDF objects_json is malformed and cannot be parsed
- PDF file record exists but has no extracted objects

**Context data**:
- `pdf_file_id`: ID of the PDF
- `access_error`: Details about access failure

**User message**: "Cannot access PDF data. File may need to be re-uploaded."

**Example**:
```python
def get_pdf_objects_for_extraction(pdf_file_id: int) -> List[PdfObject]:
    pdf = self.pdf_service.get_pdf(pdf_file_id)
    if not pdf.objects_json:
        raise PDFObjectAccessError(pdf_file_id, "objects_json is null")

    try:
        return parse_pdf_objects(pdf.objects_json)
    except JSONDecodeError as e:
        raise PDFObjectAccessError(pdf_file_id, f"Invalid JSON: {str(e)}")
```

---

#### BoundingBoxInvalidError

```python
class BoundingBoxInvalidError(DataExtractionError):
    """Bounding box coordinates are invalid or malformed"""

    def __init__(self, field_name: str, bounding_box: Any, error: str):
        self.field_name = field_name
        self.bounding_box = bounding_box
        self.validation_error = error
        super().__init__(
            f"Bounding box for field '{field_name}' is invalid: {error}"
        )
```

**Purpose**: Bounding box data structure is invalid or has impossible values

**When to raise**:
- Bounding box coordinates are negative
- Bounding box has zero width or height
- Bounding box coordinates are outside PDF page bounds
- Bounding box data is missing required fields

**Context data**:
- `field_name`: Name of the extraction field
- `bounding_box`: The invalid bounding box data
- `validation_error`: What's wrong with the bounding box

**User message**: "Field '{field_name}' has invalid bounding box. Template may be corrupted."

**Example**:
```python
def validate_bounding_box(field: ExtractionField) -> None:
    bb = field.bounding_box
    if bb.x < 0 or bb.y < 0:
        raise BoundingBoxInvalidError(field.name, bb, "Negative coordinates")
    if bb.width <= 0 or bb.height <= 0:
        raise BoundingBoxInvalidError(field.name, bb, "Zero or negative dimensions")
```

---

#### ExtractionFieldDefinitionError

```python
class ExtractionFieldDefinitionError(DataExtractionError):
    """Extraction field definition data is corrupted"""

    def __init__(self, template_id: int, error: str):
        self.template_id = template_id
        self.definition_error = error
        super().__init__(
            f"Extraction field definitions for template {template_id} are corrupted: {error}"
        )
```

**Purpose**: Template's extraction_fields JSON cannot be parsed or is invalid

**When to raise**:
- extraction_fields JSON is malformed
- extraction_fields missing required properties
- extraction_fields data types are wrong

**Context data**:
- `template_id`: ID of the template
- `definition_error`: Details about corruption

**User message**: "Template extraction fields are corrupted. Please recreate the template."

**Example**:
```python
def load_extraction_fields(template: PdfTemplate) -> List[ExtractionField]:
    try:
        fields_data = json.loads(template.extraction_fields)
        return [ExtractionField(**field) for field in fields_data]
    except (JSONDecodeError, ValidationError) as e:
        raise ExtractionFieldDefinitionError(template.id, str(e))
```

---

### Critical Error (Catch-All)

#### DataExtractionCriticalError

```python
class DataExtractionCriticalError(DataExtractionError):
    """Critical error in data extraction (unexpected system failure)"""

    def __init__(self, error: str):
        self.original_error = error
        super().__init__(f"Critical error in data extraction: {error}")
```

**Purpose**: Catch-all for any unexpected/unhandled error during data extraction

**When to raise**:
- Import failures (extraction module can't be imported)
- Syntax errors in extraction code
- Unhandled exceptions we didn't anticipate
- Any `Exception` caught in outer try/except that isn't a specific DataExtractionError

**Context data**:
- `original_error`: Full error message from unexpected exception

**User message**: "A critical system error occurred during extraction. Please contact support."

**Example**:
```python
def extract_data(pdf_file_id: int, template: PdfTemplate) -> Dict[str, Any]:
    try:
        pdf_objects = self._get_pdf_objects(pdf_file_id)
        fields = self._load_extraction_fields(template)
        return self._extract_all_fields(fields, pdf_objects)
    except ExtractionFieldNotFoundError as e:
        raise e
    except ExtractionFieldValidationError as e:
        raise e
    except RequiredFieldMissingError as e:
        raise e
    except ExtractionFieldTypeError as e:
        raise e
    except PDFObjectAccessError as e:
        raise e
    except BoundingBoxInvalidError as e:
        raise e
    except ExtractionFieldDefinitionError as e:
        raise e
    except Exception as e:
        # Something unexpected happened - wrap in critical error
        raise DataExtractionCriticalError(str(e))
```

---

## Phase 3: Pipeline Execution Exceptions

### Hierarchy

```
ETOProcessingError
└── PipelineExecutionError
    ├── ModuleExecutionError
    ├── ModuleValidationError
    ├── ModuleConfigurationError
    ├── ActionModuleError
    ├── PipelineTimeoutError
    ├── ModuleNotFoundError
    ├── ModuleLoadError
    ├── PipelineDefinitionCorruptedError
    ├── PipelineCompilationError
    ├── PipelineStepNotFoundError
    └── PipelineExecutionCriticalError (catch-all for unexpected errors)
```

### Base Exception

#### PipelineExecutionError

```python
class PipelineExecutionError(ETOProcessingError):
    """Base exception for pipeline execution phase errors"""
    pass
```

**Purpose**: Base class for all pipeline execution errors

**When to catch**: When you want to handle any pipeline execution failure generically

**When to raise**: Never directly (use specific subclasses)

---

### Specific Expected Errors

---

#### ModuleExecutionError

```python
class ModuleExecutionError(PipelineExecutionError):
    """Module's run() method raised an exception"""

    def __init__(self, module_id: str, step_index: int, original_error: str):
        self.module_id = module_id
        self.step_index = step_index
        self.original_error = original_error
        super().__init__(
            f"Module '{module_id}' failed at step {step_index}: {original_error}"
        )
```

**Purpose**: Module execution raised an exception during run()

**When to raise**:
- Module's run() method raises any exception
- Module encounters runtime error with data
- Module logic fails (e.g., division by zero, key error)

**Context data**:
- `module_id`: ID of the module that failed
- `step_index`: Position in pipeline execution
- `original_error`: Original exception message from module

**User message**: "Error executing module '{module_id}': {original_error}"

**Example**:
```python
def execute_module_step(step: PipelineDefinitionStep, inputs: Dict) -> Any:
    try:
        module_class = self.module_service.get_module_class(step.module_id)
        instance = module_class()
        return instance.run(inputs, step.config, context)
    except Exception as e:
        raise ModuleExecutionError(step.module_id, step.step_index, str(e))
```

---

#### ModuleValidationError

```python
class ModuleValidationError(PipelineExecutionError):
    """Module input validation failed"""

    def __init__(self, module_id: str, step_index: int, validation_errors: List[str]):
        self.module_id = module_id
        self.step_index = step_index
        self.validation_errors = validation_errors
        super().__init__(
            f"Module '{module_id}' at step {step_index} input validation failed: "
            f"{', '.join(validation_errors)}"
        )
```

**Purpose**: Module inputs don't match expected schema or constraints

**When to raise**:
- Input types don't match module's expected input types
- Input values out of acceptable range
- Required inputs are missing
- Input data structure is malformed

**Context data**:
- `module_id`: ID of the module
- `step_index`: Position in pipeline
- `validation_errors`: List of validation error messages

**User message**: "Module '{module_id}' received invalid inputs: {validation_errors}"

**Example**:
```python
def validate_module_inputs(module: BaseModule, inputs: Dict, step_index: int) -> None:
    errors = []
    meta = module.meta()

    for input_group in meta.io_shape.inputs.nodes:
        if input_group.label not in inputs:
            errors.append(f"Missing required input: {input_group.label}")

    if errors:
        raise ModuleValidationError(module.id, step_index, errors)
```

---

#### ModuleConfigurationError

```python
class ModuleConfigurationError(PipelineExecutionError):
    """Module configuration is invalid"""

    def __init__(self, module_id: str, step_index: int, config_errors: List[str]):
        self.module_id = module_id
        self.step_index = step_index
        self.config_errors = config_errors
        super().__init__(
            f"Module '{module_id}' at step {step_index} has invalid configuration: "
            f"{', '.join(config_errors)}"
        )
```

**Purpose**: Module's config doesn't pass Pydantic validation

**When to raise**:
- Config fields missing required values
- Config field types are wrong
- Config values fail validation constraints

**Context data**:
- `module_id`: ID of the module
- `step_index`: Position in pipeline
- `config_errors`: List of configuration validation errors

**User message**: "Module '{module_id}' configuration is invalid: {config_errors}"

**Example**:
```python
def validate_module_config(module_class: Type[BaseModule], config: Dict, step_index: int) -> BaseModel:
    try:
        return module_class.ConfigModel(**config)
    except ValidationError as e:
        errors = [f"{err['loc'][0]}: {err['msg']}" for err in e.errors()]
        raise ModuleConfigurationError(module_class.id, step_index, errors)
```

---

#### ActionModuleError

```python
class ActionModuleError(PipelineExecutionError):
    """Action module failed (first failure from action barrier)"""

    def __init__(self, module_id: str, step_index: int, action_type: str, error: str):
        self.module_id = module_id
        self.step_index = step_index
        self.action_type = action_type
        self.failure_reason = error
        super().__init__(
            f"Action module '{module_id}' ({action_type}) failed at step {step_index}: {error}"
        )
```

**Purpose**: Action module failed to perform side effect (email, file write, API call)

**When to raise**:
- Email send fails
- File write fails
- API call fails
- Database write fails (from action module)
- First action module failure encountered (others may have executed)

**Context data**:
- `module_id`: ID of the action module
- `step_index`: Position in pipeline
- `action_type`: Type of action (email, file, api, etc.)
- `failure_reason`: Why the action failed

**User message**: "Action failed: {action_type} - {failure_reason}"

**Example**:
```python
def execute_action_module(step: PipelineDefinitionStep, inputs: Dict) -> Any:
    try:
        module_class = self.module_service.get_module_class(step.module_id)
        instance = module_class()
        return instance.run(inputs, step.config, context)
    except Exception as e:
        action_type = getattr(module_class, 'action_type', 'unknown')
        raise ActionModuleError(step.module_id, step.step_index, action_type, str(e))
```

---

#### PipelineTimeoutError

```python
class PipelineTimeoutError(PipelineExecutionError):
    """Pipeline execution exceeded timeout limit"""

    def __init__(self, pipeline_id: int, timeout_seconds: int, elapsed_seconds: float, last_step: int):
        self.pipeline_id = pipeline_id
        self.timeout_seconds = timeout_seconds
        self.elapsed_seconds = elapsed_seconds
        self.last_completed_step = last_step
        super().__init__(
            f"Pipeline {pipeline_id} exceeded timeout ({timeout_seconds}s). "
            f"Ran for {elapsed_seconds:.1f}s, completed {last_step} steps"
        )
```

**Purpose**: Pipeline took too long to execute

**When to raise**:
- Pipeline execution time exceeds configured timeout
- Dask task timeout occurs
- Long-running module doesn't complete

**Context data**:
- `pipeline_id`: ID of the pipeline
- `timeout_seconds`: Configured timeout limit
- `elapsed_seconds`: Actual time elapsed
- `last_completed_step`: Last step that completed before timeout

**User message**: "Pipeline execution timed out after {elapsed_seconds}s (limit: {timeout_seconds}s)"

**Example**:
```python
def execute_pipeline_with_timeout(pipeline_id: int, timeout: int) -> Dict:
    start_time = time.time()
    last_step = 0

    try:
        return self._execute_pipeline(pipeline_id, timeout)
    except TimeoutException:
        elapsed = time.time() - start_time
        raise PipelineTimeoutError(pipeline_id, timeout, elapsed, last_step)
```

---

#### ModuleNotFoundError

```python
class ModuleNotFoundError(PipelineExecutionError):
    """Module doesn't exist in catalog or registry"""

    def __init__(self, module_id: str, step_index: int):
        self.module_id = module_id
        self.step_index = step_index
        super().__init__(
            f"Module '{module_id}' not found in catalog at step {step_index}"
        )
```

**Purpose**: Pipeline references a module that doesn't exist

**When to raise**:
- Module ID not in module catalog database
- Module ID not in module registry
- Module was deleted after pipeline was created

**Context data**:
- `module_id`: ID of the missing module
- `step_index`: Position in pipeline where module is needed

**User message**: "Module '{module_id}' not found. Pipeline may be outdated."

**Example**:
```python
def get_module_for_step(step: PipelineDefinitionStep) -> Type[BaseModule]:
    module_class = self.module_service.get_module_class(step.module_id)
    if not module_class:
        raise ModuleNotFoundError(step.module_id, step.step_index)
    return module_class
```

---

#### ModuleLoadError

```python
class ModuleLoadError(PipelineExecutionError):
    """Cannot dynamically load module class"""

    def __init__(self, module_id: str, handler_name: str, error: str):
        self.module_id = module_id
        self.handler_name = handler_name
        self.load_error = error
        super().__init__(
            f"Cannot load module '{module_id}' from handler '{handler_name}': {error}"
        )
```

**Purpose**: Module class cannot be imported or loaded

**When to raise**:
- handler_name import path is invalid
- Module file doesn't exist
- Module class has syntax errors
- Security validation fails for handler_name
- Import dependencies missing

**Context data**:
- `module_id`: ID of the module
- `handler_name`: Python import path that failed
- `load_error`: Details of import failure

**User message**: "Cannot load module '{module_id}'. System error."

**Example**:
```python
def load_module_from_handler(module_id: str, handler_name: str) -> Type[BaseModule]:
    try:
        module_path, class_name = handler_name.split(":")
        module = importlib.import_module(module_path)
        return getattr(module, class_name)
    except Exception as e:
        raise ModuleLoadError(module_id, handler_name, str(e))
```

---

#### PipelineDefinitionCorruptedError

```python
class PipelineDefinitionCorruptedError(PipelineExecutionError):
    """Pipeline definition data is corrupted or invalid"""

    def __init__(self, pipeline_id: int, error: str):
        self.pipeline_id = pipeline_id
        self.corruption_details = error
        super().__init__(
            f"Pipeline {pipeline_id} definition is corrupted: {error}"
        )
```

**Purpose**: Pipeline definition JSON cannot be parsed or is invalid

**When to raise**:
- pipeline_state JSON is malformed
- visual_state JSON is malformed
- Pipeline structure is invalid (missing required fields)

**Context data**:
- `pipeline_id`: ID of the pipeline
- `corruption_details`: What's wrong with the definition

**User message**: "Pipeline definition is corrupted. Template may need to be recreated."

**Example**:
```python
def load_pipeline_definition(pipeline_id: int) -> PipelineDefinition:
    try:
        pipeline = self.pipeline_repo.get_by_id(pipeline_id)
        return PipelineDefinition.from_db_model(pipeline)
    except (JSONDecodeError, ValidationError) as e:
        raise PipelineDefinitionCorruptedError(pipeline_id, str(e))
```

---

#### PipelineCompilationError

```python
class PipelineCompilationError(PipelineExecutionError):
    """Pipeline failed to compile"""

    def __init__(self, pipeline_id: int, stage: str, error: str):
        self.pipeline_id = pipeline_id
        self.compilation_stage = stage
        self.compilation_error = error
        super().__init__(
            f"Pipeline {pipeline_id} compilation failed at stage '{stage}': {error}"
        )
```

**Purpose**: Pipeline could not be compiled into executable steps

**When to raise**:
- Checksum calculation fails
- Graph pruning fails
- Topological sorting fails
- Step building fails

**Context data**:
- `pipeline_id`: ID of the pipeline
- `compilation_stage`: Which stage of compilation failed (checksum, pruning, sorting, steps)
- `compilation_error`: Details of compilation failure

**User message**: "Pipeline compilation failed. Template may be invalid."

**Example**:
```python
def compile_pipeline(pipeline_id: int) -> List[PipelineDefinitionStep]:
    try:
        pipeline = self.get_pipeline(pipeline_id)

        # Prune graph
        pruned = GraphPruner.prune(pipeline.pipeline_state)

        # Calculate checksum
        checksum = ChecksumCalculator.compute(pruned)

        # Build steps
        steps = PipelineCompiler.compile(pruned, checksum)
        return steps
    except Exception as e:
        stage = "compilation"  # Determine from traceback
        raise PipelineCompilationError(pipeline_id, stage, str(e))
```

---

#### PipelineStepNotFoundError

```python
class PipelineStepNotFoundError(PipelineExecutionError):
    """Compiled steps missing for pipeline"""

    def __init__(self, pipeline_id: int, checksum: str):
        self.pipeline_id = pipeline_id
        self.plan_checksum = checksum
        super().__init__(
            f"Compiled steps not found for pipeline {pipeline_id} (checksum: {checksum})"
        )
```

**Purpose**: Pipeline has checksum but compiled steps don't exist in database

**When to raise**:
- Pipeline references compiled plan that was deleted
- Checksum in pipeline_definitions doesn't match any compiled plan
- Database inconsistency between pipeline and steps

**Context data**:
- `pipeline_id`: ID of the pipeline
- `plan_checksum`: Checksum that couldn't be found

**User message**: "Pipeline execution plan missing. Template may need to be recompiled."

**Example**:
```python
def get_compiled_steps(pipeline: PipelineDefinition) -> List[PipelineDefinitionStep]:
    if not pipeline.plan_checksum:
        raise PipelineCompilationError(pipeline.id, "checksum", "No checksum found")

    steps = self.step_repo.get_by_checksum(pipeline.plan_checksum)
    if not steps:
        raise PipelineStepNotFoundError(pipeline.id, pipeline.plan_checksum)

    return steps
```

---

### Critical Error (Catch-All)

#### PipelineExecutionCriticalError

```python
class PipelineExecutionCriticalError(PipelineExecutionError):
    """Critical error in pipeline execution (unexpected system failure)"""

    def __init__(self, error: str):
        self.original_error = error
        super().__init__(f"Critical error in pipeline execution: {error}")
```

**Purpose**: Catch-all for any unexpected/unhandled error during pipeline execution

**When to raise**:
- Dask scheduler crashes
- Import failures (Dask, module registry, etc.)
- Syntax errors in pipeline execution code
- Unhandled exceptions we didn't anticipate
- Any `Exception` caught in outer try/except that isn't a specific PipelineExecutionError

**Context data**:
- `original_error`: Full error message from unexpected exception

**User message**: "A critical system error occurred during pipeline execution. Please contact support."

**Example**:
```python
def execute_pipeline(pipeline_id: int, entry_values: Dict) -> PipelineExecutionRun:
    try:
        pipeline = self._get_pipeline(pipeline_id)
        steps = self._get_compiled_steps(pipeline)
        return self._execute_dask_dag(steps, entry_values)
    except ModuleExecutionError as e:
        raise e
    except ModuleValidationError as e:
        raise e
    except ModuleConfigurationError as e:
        raise e
    except ActionModuleError as e:
        raise e
    except PipelineTimeoutError as e:
        raise e
    except ModuleNotFoundError as e:
        raise e
    except ModuleLoadError as e:
        raise e
    except PipelineDefinitionCorruptedError as e:
        raise e
    except PipelineCompilationError as e:
        raise e
    except PipelineStepNotFoundError as e:
        raise e
    except Exception as e:
        # Something unexpected happened - wrap in critical error
        raise PipelineExecutionCriticalError(str(e))
```

---

## Usage Patterns

### Pattern 1: Catch Specific Error

```python
def process_eto_run(eto_run_id: int):
    try:
        template = self.match_template(pdf_file_id)
    except NoTemplateMatchError:
        # User-friendly handling
        logger.warning(f"No template matched for ETO run {eto_run_id}")
        self.mark_run_needs_template(eto_run_id)
        return
```

### Pattern 2: Catch Phase-Level Errors

```python
def process_eto_run(eto_run_id: int):
    try:
        template = self.match_template(pdf_file_id)
        data = self.extract_data(pdf, template)
        results = self.execute_pipeline(template.pipeline, data)
    except TemplateMatchingError as e:
        # Handle all template matching errors
        logger.error(f"Template matching failed: {e}")
        self.save_error_to_run(eto_run_id, e)
    except DataExtractionError as e:
        # Handle all extraction errors
        logger.error(f"Data extraction failed: {e}")
        self.save_error_to_run(eto_run_id, e)
    except PipelineExecutionError as e:
        # Handle all pipeline errors
        logger.error(f"Pipeline execution failed: {e}")
        self.save_error_to_run(eto_run_id, e)
```

### Pattern 3: Catch All ETO Errors

```python
def process_eto_run(eto_run_id: int):
    try:
        # Full ETO process
        template = self.match_template(pdf_file_id)
        data = self.extract_data(pdf, template)
        results = self.execute_pipeline(template.pipeline, data)
        self.mark_run_complete(eto_run_id, results)
    except ETOProcessingError as e:
        # Catch any ETO error and save to database
        error_data = e.to_dict()
        self.eto_run_repo.update_error(
            eto_run_id,
            error_type=error_data['exception_type'],
            error_message=error_data['message'],
            error_details=json.dumps(error_data['context'])
        )
        logger.error(f"ETO run {eto_run_id} failed: {e}")
```

### Pattern 4: Re-raise with Context

```python
def match_template(pdf_file_id: int) -> PdfTemplate:
    try:
        # Attempt matching
        templates = self._get_active_templates()
        return self._find_best_match(pdf_file_id, templates)
    except TemplateMatchingError as e:
        # Add logging but re-raise
        logger.warning(f"Template matching failed for PDF {pdf_file_id}")
        raise e
```

### Pattern 5: Convert External Exceptions

```python
def extract_signature(pdf_file_id: int) -> List[SignatureObject]:
    try:
        pdf = self.pdf_service.get_pdf(pdf_file_id)
        return self._parse_signature(pdf)
    except (PDFLibraryError, JSONDecodeError) as e:
        # Convert external exception to our hierarchy
        raise PDFSignatureExtractionError(pdf_file_id, str(e))
```

---

## Database Schema Integration

### ETO Runs Table

```python
class ETORunModel(Base):
    __tablename__ = 'eto_runs'

    # ... other fields

    # Error tracking
    error_type: str | None  # Exception class name (e.g., "NoTemplateMatchError")
    error_message: str | None  # Human-readable message
    error_details: str | None  # JSON string of context dict
    error_phase: str | None  # "template_matching" | "data_extraction" | "pipeline_execution"
```

### Saving Errors

```python
def save_error_to_run(self, eto_run_id: int, error: ETOProcessingError):
    """Save error information to ETO run"""
    error_data = error.to_dict()

    # Determine phase from exception type
    phase = None
    if isinstance(error, TemplateMatchingError):
        phase = "template_matching"
    elif isinstance(error, DataExtractionError):
        phase = "data_extraction"
    elif isinstance(error, PipelineExecutionError):
        phase = "pipeline_execution"

    self.eto_run_repo.update(
        eto_run_id,
        ETORunUpdate(
            status="failed",
            error_type=error_data['exception_type'],
            error_message=error_data['message'],
            error_details=json.dumps(error_data['context']),
            error_phase=phase
        )
    )
```

---

## Implementation Notes

### Location

All exception classes should be defined in:
- `server/src/shared/exceptions/eto_processing.py`

### Imports

```python
from shared.exceptions import (
    ETOProcessingError,
    TemplateMatchingError,
    NoTemplateMatchError,
    TemplateMatchingCriticalError,
    PDFSignatureExtractionError,
    TemplateDataCorruptedError,
    TemplateMatchingDatabaseError,
    # ... other exceptions
)
```

### Testing

Each exception should have tests covering:
1. Basic instantiation
2. Message formatting
3. Context data accessibility
4. `to_dict()` serialization
5. Inheritance hierarchy (isinstance checks)

---

## Exception Summary

### Template Matching Exceptions ✅

**Total: 6 exception classes**

1. `TemplateMatchingError` - Base class
2. `NoTemplateMatchError` - No template matched (includes case where no templates exist)
3. `PDFSignatureExtractionError` - Cannot extract signature from PDF
4. `TemplateDataCorruptedError` - Template data is malformed
5. `TemplateMatchingDatabaseError` - Database connection/query error
6. `TemplateMatchingCriticalError` - Catch-all for unexpected errors

**User Experience:**
- Specific errors (2-5): Show clear, actionable messages ("No template matched", "PDF corrupted", etc.)
- Critical error (6): Generic error message directing user to contact support

---

### Data Extraction Exceptions ✅

**Total: 9 exception classes**

1. `DataExtractionError` - Base class
2. `ExtractionFieldNotFoundError` - Bounding box found no text
3. `ExtractionFieldValidationError` - Extracted text failed regex validation
4. `RequiredFieldMissingError` - Required field is empty
5. `ExtractionFieldTypeError` - Cannot coerce to expected type
6. `PDFObjectAccessError` - Cannot access PDF objects
7. `BoundingBoxInvalidError` - Bounding box coordinates invalid
8. `ExtractionFieldDefinitionError` - Extraction field definition corrupted
9. `DataExtractionCriticalError` - Catch-all for unexpected errors

**User Experience:**
- Specific errors (2-8): Show clear, actionable messages with field names and values
- Critical error (9): Generic error message directing user to contact support

---

### Pipeline Execution Exceptions ✅

**Total: 12 exception classes**

1. `PipelineExecutionError` - Base class
2. `ModuleExecutionError` - Module run() raised exception
3. `ModuleValidationError` - Module input validation failed
4. `ModuleConfigurationError` - Module config invalid
5. `ActionModuleError` - Action module failed (first from barrier)
6. `PipelineTimeoutError` - Pipeline exceeded timeout
7. `ModuleNotFoundError` - Module doesn't exist in catalog
8. `ModuleLoadError` - Cannot load module class
9. `PipelineDefinitionCorruptedError` - Pipeline definition corrupted
10. `PipelineCompilationError` - Pipeline compilation failed
11. `PipelineStepNotFoundError` - Compiled steps missing
12. `PipelineExecutionCriticalError` - Catch-all for unexpected errors

**User Experience:**
- Specific errors (2-11): Show clear, actionable messages with module/step details
- Critical error (12): Generic error message directing user to contact support

---

## Next Steps

1. **Finalize Template Matching Exceptions** ✅
2. **Design Data Extraction Exceptions** ✅
3. **Design Pipeline Execution Exceptions** ✅
4. **Implement Base Classes** - Create base exception classes in codebase
5. **Implement Specific Exceptions** - Create all specific exception classes
6. **Update Services** - Modify services to raise appropriate exceptions
7. **Update Error Handling** - Add exception handling in ETO processing flow
8. **Add Tests** - Create comprehensive exception tests

---

## Design Notes

- **Exceptions are raised at the point of failure**, not wrapped multiple times
- **Exception messages are clear and actionable** for end users
- **Context data is minimal** but sufficient for debugging
- **Critical exceptions are catch-alls** for unexpected errors (import failures, syntax errors, unhandled exceptions)
- **Non-critical exceptions are specific** expected failure modes we've designed for (even system-level ones like corrupted files)
- **Each phase has exactly one critical exception** as the final catch-all
