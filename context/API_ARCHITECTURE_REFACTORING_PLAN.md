# API Architecture Refactoring Plan

**Created:** 2025-10-27
**Status:** Analysis Complete, Ready for Implementation
**Scope:** Align pdf_files, pipelines, and pdf_templates routers with email_configs/modules standard

---

## Executive Summary

We've established a consistent API architecture pattern using `email_configs` and `modules` as the reference standard. This document outlines exactly what needs to change in the other API routers to match this pattern.

**Files Analyzed:**
- ✅ Reference Standard: `api/routers/email_configs.py`, `api/routers/modules.py`
- ✅ Already Compliant: `api/routers/pdf_files.py` (no changes needed)
- ⚠️ Needs Minor Updates: `api/routers/pipelines.py` (2 issues)
- ⚠️ Needs Major Refactoring: `api/routers/pdf_templates.py` (5 issues)

---

## The Reference Standard Pattern

### Architecture Layers

```
┌─────────────────────────────────────────┐
│  API Router (HTTP Layer)                │
│  - Receive request                      │
│  - Call mapper (request → domain)       │
│  - Call service (business logic)        │
│  - Call mapper (domain → response)      │
│  - Return response                      │
└─────────────────────────────────────────┘
              ↓           ↑
┌─────────────────────────────────────────┐
│  API Mappers (Conversion Layer)         │
│  - API schemas ↔ Domain types           │
│  - Handle all type conversions          │
│  - Bidirectional transformations        │
└─────────────────────────────────────────┘
              ↓           ↑
┌─────────────────────────────────────────┐
│  Services (Business Logic Layer)        │
│  - Validate domain rules                │
│  - Orchestrate operations               │
│  - Call repositories                    │
│  - Return domain types                  │
└─────────────────────────────────────────┘
              ↓           ↑
┌─────────────────────────────────────────┐
│  Repositories (Data Access Layer)       │
│  - Database operations                  │
│  - Return domain types                  │
└─────────────────────────────────────────┘
```

### Reference Example: email_configs.py

**File:** `server-new/src/api/routers/email_configs.py:70-80`

```python
@router.post("", response_model=EmailConfig, status_code=status.HTTP_201_CREATED)
async def create_email_config(
    request: CreateEmailConfigRequest,
    config_service: EmailConfigService = Depends(
        lambda: ServiceContainer.get_email_config_service()
    )
) -> EmailConfig:
    """Create new email configuration"""
    config_create = create_request_to_domain(request)  # Mapper: API → Domain
    config = config_service.create_config(config_create)  # Service call
    return email_config_to_api(config)  # Mapper: Domain → API
```

**Key Principles:**
1. ✅ Router has NO business logic
2. ✅ Router does NO validation (Pydantic handles it automatically)
3. ✅ Router does NO data transformation (mappers handle it)
4. ✅ Router does NO direct repository access (services handle it)
5. ✅ Mappers are separate functions in `api/mappers/`
6. ✅ Service layer returns domain types, not API schemas
7. ✅ Response type explicitly declared with `response_model`

### File Organization Standard

```
api/
├── routers/
│   ├── email_configs.py      # HTTP endpoints only
│   ├── modules.py            # HTTP endpoints only
│   ├── pdf_files.py          # HTTP endpoints only
│   ├── pipelines.py          # HTTP endpoints only (needs cleanup)
│   └── pdf_templates.py      # HTTP endpoints only (needs major cleanup)
├── mappers/
│   ├── email_configs.py      # Domain ↔ API conversions
│   ├── modules.py            # Domain ↔ API conversions
│   ├── pdf_files.py          # Domain ↔ API conversions
│   ├── pipelines.py          # Domain ↔ API conversions (needs additions)
│   └── pdf_templates.py      # Domain ↔ API conversions (needs additions)
└── schemas/
    ├── email_configs.py      # Pydantic request/response models
    ├── modules.py            # Pydantic request/response models
    ├── pdf_files.py          # Pydantic request/response models
    ├── pipelines.py          # Pydantic request/response models
    └── pdf_templates.py      # Pydantic request/response models
```

---

## Analysis Results

### ✅ pdf_files.py - NO CHANGES NEEDED

**Status:** Already compliant with the standard

**Why it's correct:**
- All endpoints follow the mapper pattern
- Service injection is clean
- No business logic in router
- Response types properly specified

**Example of correct implementation:**
```python
# server-new/src/api/routers/pdf_files.py:33-42
@router.get("/{id}", response_model=GetPdfMetadataResponse)
async def get_pdf_metadata(
    id: int,
    pdf_service: PdfFilesService = Depends(
        lambda: ServiceContainer.get_pdf_files_service()
    )
) -> GetPdfMetadataResponse:
    """Get PDF file metadata (filename, size, page count, etc.)"""
    metadata = pdf_service.get_pdf_metadata(id)
    return convert_pdf_metadata(metadata)
```

**Conclusion:** This file can be used as a secondary reference example.

---

## Refactoring Tasks

### 🔴 HIGH PRIORITY: pipelines.py

#### Issue 1: Direct Repository Access in Router

**File:** `server-new/src/api/routers/pipelines.py:221-231`

**Current Code (WRONG):**
```python
# Load compiled steps
from shared.database.repositories import PipelineDefinitionStepRepository
step_repo = PipelineDefinitionStepRepository(
    connection_manager=ServiceContainer.get_connection_manager()
)
steps = step_repo.get_steps_by_plan_id(pipeline.compiled_plan_id)

if not steps:
    from shared.exceptions import ServiceError
    raise ServiceError(
        f"No compiled steps found for pipeline {id} (plan {pipeline.compiled_plan_id})"
    )
```

**Problem:** Router directly accesses repository layer, bypassing service layer

**Solution:**
1. Add method to `PipelineService` or `PipelineExecutionService`
2. Move the logic to service layer

**New Code:**

**In `features/pipelines/service.py` (add method):**
```python
def get_compiled_steps(self, pipeline_id: int) -> list[PipelineDefinitionStep]:
    """
    Get compiled execution steps for a pipeline.

    Args:
        pipeline_id: Pipeline definition ID

    Returns:
        List of compiled steps

    Raises:
        NotFoundError: Pipeline not found or not compiled
    """
    pipeline = self.get_pipeline_definition(pipeline_id)

    if pipeline.compiled_plan_id is None:
        raise ServiceError(
            f"Pipeline {pipeline_id} is not compiled. Cannot get steps for uncompiled pipeline."
        )

    step_repo = PipelineDefinitionStepRepository(
        connection_manager=self.connection_manager
    )
    steps = step_repo.get_steps_by_plan_id(pipeline.compiled_plan_id)

    if not steps:
        raise ServiceError(
            f"No compiled steps found for pipeline {pipeline_id} (plan {pipeline.compiled_plan_id})"
        )

    return steps
```

**In `api/routers/pipelines.py:168-259` (update execute_pipeline endpoint):**
```python
@router.post("/{id}/execute", response_model=ExecutePipelineResponse)
async def execute_pipeline(
    id: int,
    request: ExecutePipelineRequest,
    pipeline_service: PipelineService = Depends(
        lambda: ServiceContainer.get_pipeline_service()
    )
) -> ExecutePipelineResponse:
    """Execute a pipeline with provided entry values (SIMULATION MODE)."""

    # Get execution service
    from features.pipelines.service_execution import PipelineExecutionService
    execution_service = PipelineExecutionService(
        connection_manager=ServiceContainer.get_connection_manager(),
        services=ServiceContainer
    )

    # Load pipeline and compiled steps via service layer
    pipeline = pipeline_service.get_pipeline_definition(id)
    steps = pipeline_service.get_compiled_steps(id)  # NEW: Service method

    logger.info(f"Executing pipeline {id} with {len(steps)} steps")

    # Execute pipeline
    result = execution_service.execute_pipeline(
        steps=steps,
        entry_values_by_name=request.entry_values,
        pipeline_state=pipeline.pipeline_state
    )

    # Convert result using mapper
    return convert_execution_result_to_api(result)  # NEW: Use mapper
```

---

#### Issue 2: Inline DTO Construction in Router

**File:** `server-new/src/api/routers/pipelines.py:243-259`

**Current Code (WRONG):**
```python
# Convert result to API schema
step_dtos = [
    ExecutionStepResultDTO(
        module_instance_id=step.module_instance_id,
        step_number=step.step_number,
        inputs=step.inputs,
        outputs=step.outputs,
        error=step.error
    )
    for step in result.steps
]

return ExecutePipelineResponse(
    status=result.status,
    steps=step_dtos,
    executed_actions=result.executed_actions,
    error=result.error
)
```

**Problem:** Data transformation logic in router instead of mapper

**Solution:** Create mapper function

**New Code:**

**In `api/mappers/pipelines.py` (add new function):**
```python
from api.schemas.pipelines import (
    ExecutePipelineResponse,
    ExecutionStepResultDTO,
)

def convert_execution_result_to_api(result) -> ExecutePipelineResponse:
    """
    Convert domain execution result to API ExecutePipelineResponse.

    Args:
        result: Domain execution result object

    Returns:
        ExecutePipelineResponse for API
    """
    step_dtos = [
        ExecutionStepResultDTO(
            module_instance_id=step.module_instance_id,
            step_number=step.step_number,
            inputs=step.inputs,
            outputs=step.outputs,
            error=step.error
        )
        for step in result.steps
    ]

    return ExecutePipelineResponse(
        status=result.status,
        steps=step_dtos,
        executed_actions=result.executed_actions,
        error=result.error
    )
```

**In `api/routers/pipelines.py` (import at top):**
```python
from api.mappers.pipelines import (
    convert_pipeline_summary_list,
    convert_pipeline_detail,
    convert_create_request,
    convert_execution_result_to_api,  # NEW
)
```

---

#### Issue 3: Import Inside Function

**File:** `server-new/src/api/routers/pipelines.py:148`

**Current Code (NOT IDEAL):**
```python
async def validate_pipeline(
    request: ValidatePipelineRequest,
    ...
) -> ValidatePipelineResponse:
    # Convert API request to domain type
    from api.mappers.pipelines import convert_dto_to_pipeline_state  # WRONG: Import here
    pipeline_state = convert_dto_to_pipeline_state(request.pipeline_json)
    ...
```

**Solution:** Move import to top of file

**New Code:**

**In `api/routers/pipelines.py:23-28` (update imports):**
```python
from api.mappers.pipelines import (
    convert_pipeline_summary_list,
    convert_pipeline_detail,
    convert_create_request,
    convert_dto_to_pipeline_state,  # NEW: Move from line 148
    convert_execution_result_to_api,  # NEW: For Issue 2
)
```

**In `api/routers/pipelines.py:149` (remove local import):**
```python
async def validate_pipeline(
    request: ValidatePipelineRequest,
    ...
) -> ValidatePipelineResponse:
    # Convert API request to domain type
    pipeline_state = convert_dto_to_pipeline_state(request.pipeline_json)
    # ... rest of function
```

---

### 🔴 HIGH PRIORITY: pdf_templates.py

This router has multiple issues and needs comprehensive refactoring.

---

#### Issue 1: JSON Parsing Logic in Router

**File:** `server-new/src/api/routers/pdf_templates.py:132-138`

**Current Code (WRONG):**
```python
# Parse JSON fields
try:
    signature_objects_data = json.loads(signature_objects)
    extraction_fields_data = json.loads(extraction_fields)
    pipeline_state_data = json.loads(pipeline_state)
    visual_state_data = json.loads(visual_state)
except json.JSONDecodeError as e:
    raise ValidationError(f"Invalid JSON in request fields: {str(e)}")
```

**Problem:** Manual parsing and validation in router. This also appears at line 311-316 in simulate_template.

**Root Cause:** Using Form fields with JSON strings instead of proper request body

**Two Possible Solutions:**

**Option A: Keep Form Fields, Move Parsing to Helper**
- Create a helper function that handles all form parsing
- Still not ideal but cleaner than current state

**Option B: Split Endpoints (RECOMMENDED)**
- Create two separate endpoints: one for stored PDFs, one for uploads
- Allows proper JSON request bodies for stored PDF endpoint
- Only upload endpoint needs Form fields

**Recommended Solution: Option B**

**New Code:**

**In `api/routers/pdf_templates.py` (replace create_pdf_template):**

```python
@router.post("/from-stored", response_model=PdfTemplate, status_code=status.HTTP_201_CREATED)
async def create_pdf_template_from_stored(
    request: CreatePdfTemplateFromStoredRequest,  # NEW: Clean Pydantic model
    template_service: PdfTemplateService = Depends(lambda: ServiceContainer.get_pdf_template_service())
) -> PdfTemplate:
    """
    Create new PDF template using existing stored PDF.

    Uses standard JSON request body - no file upload needed.
    """
    # Convert to domain type (mapper handles all conversion)
    template_create_data = create_template_from_stored_request_to_domain(request)

    # Create via service
    template, version_num, pipeline_id = template_service.create_template(template_create_data)

    logger.info(f"Created template {template.id} (version {version_num}, pipeline {pipeline_id})")

    return convert_pdf_template(template)


@router.post("/from-upload", response_model=PdfTemplate, status_code=status.HTTP_201_CREATED)
async def create_pdf_template_from_upload(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    signature_objects: str = Form(...),
    extraction_fields: str = Form(...),
    pipeline_state: str = Form(...),
    visual_state: str = Form(...),
    pdf_file: UploadFile = File(...),
    template_service: PdfTemplateService = Depends(lambda: ServiceContainer.get_pdf_template_service()),
    pdf_service: PdfFilesService = Depends(lambda: ServiceContainer.get_pdf_files_service())
) -> PdfTemplate:
    """
    Create new PDF template with uploaded PDF file.

    Uses multipart/form-data for file upload.
    Business logic handled by mapper and service layers.
    """
    # Validate file
    if not pdf_file.filename or not pdf_file.filename.endswith('.pdf'):
        raise ValidationError("Invalid file type - must be a PDF")

    # Store PDF first
    pdf_bytes = await pdf_file.read()
    pdf_metadata = pdf_service.store_pdf(
        file_bytes=pdf_bytes,
        filename=pdf_file.filename,
        email_id=None
    )

    # Parse form data and convert to domain type (mapper handles parsing)
    template_create_data = create_template_from_upload_form_to_domain(
        name=name,
        description=description,
        signature_objects=signature_objects,
        extraction_fields=extraction_fields,
        pipeline_state=pipeline_state,
        visual_state=visual_state,
        source_pdf_id=pdf_metadata.id
    )

    # Create via service
    template, version_num, pipeline_id = template_service.create_template(template_create_data)

    logger.info(f"Created template {template.id} (version {version_num}, pipeline {pipeline_id})")

    return convert_pdf_template(template)
```

**In `api/schemas/pdf_templates.py` (add new schema):**

```python
class CreatePdfTemplateFromStoredRequest(BaseModel):
    """Request for creating template from existing stored PDF"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    source_pdf_id: int = Field(..., gt=0)
    signature_objects: dict[str, list[dict[str, Any]]]
    extraction_fields: list[ExtractionField]
    pipeline_state: PipelineStateDTO
    visual_state: VisualStateDTO
```

**In `api/mappers/pdf_templates.py` (add new functions):**

```python
def create_template_from_stored_request_to_domain(
    request: CreatePdfTemplateFromStoredRequest
) -> PdfTemplateCreate:
    """Convert API create request (stored PDF) to domain PdfTemplateCreate"""
    return PdfTemplateCreate(
        name=request.name,
        description=request.description,
        signature_objects=convert_pdf_objects_to_domain(request.signature_objects),
        extraction_fields=convert_extraction_fields_to_domain(request.extraction_fields),
        pipeline_state=request.pipeline_state.model_dump(),
        visual_state=request.visual_state.model_dump(),
        source_pdf_id=request.source_pdf_id
    )


def create_template_from_upload_form_to_domain(
    name: str,
    description: Optional[str],
    signature_objects: str,
    extraction_fields: str,
    pipeline_state: str,
    visual_state: str,
    source_pdf_id: int
) -> PdfTemplateCreate:
    """
    Parse form data and convert to domain PdfTemplateCreate.

    Handles JSON parsing and validation of form fields.
    """
    import json
    from api.schemas.pdf_templates import ExtractionField as ExtractionFieldSchema
    from api.schemas.pipelines import PipelineStateDTO, VisualStateDTO

    # Parse JSON fields
    try:
        signature_objects_data = json.loads(signature_objects)
        extraction_fields_data = json.loads(extraction_fields)
        pipeline_state_data = json.loads(pipeline_state)
        visual_state_data = json.loads(visual_state)
    except json.JSONDecodeError as e:
        from shared.exceptions.service import ValidationError
        raise ValidationError(f"Invalid JSON in request fields: {str(e)}")

    # Validate and parse extraction fields
    try:
        parsed_extraction_fields = [
            ExtractionFieldSchema(**field) for field in extraction_fields_data
        ]
    except Exception as e:
        from shared.exceptions.service import ValidationError
        raise ValidationError(f"Invalid extraction fields format: {str(e)}")

    # Validate pipeline and visual state
    pipeline_state_dto = PipelineStateDTO(**pipeline_state_data)
    visual_state_dto = VisualStateDTO(**visual_state_data)

    # Convert to domain type
    return PdfTemplateCreate(
        name=name,
        description=description,
        signature_objects=convert_pdf_objects_to_domain(signature_objects_data),
        extraction_fields=convert_extraction_fields_to_domain(parsed_extraction_fields),
        pipeline_state=pipeline_state_dto.model_dump(),
        visual_state=visual_state_dto.model_dump(),
        source_pdf_id=source_pdf_id
    )
```

**Benefits of this approach:**
- Clean separation: stored PDF endpoint uses JSON body, upload endpoint uses multipart
- Router stays thin - just handles HTTP concerns
- All parsing/validation logic moved to mapper
- Frontend can choose appropriate endpoint based on their workflow
- Better API design - single responsibility per endpoint

---

#### Issue 2: Inline DTO Construction in simulate_template

**File:** `server-new/src/api/routers/pdf_templates.py:361-400`

**Current Code (WRONG):**
```python
# Convert execution steps to API schema
from api.schemas.pdf_templates import PipelineStepSimulation, SimulatedAction

step_dtos = [
    PipelineStepSimulation(
        step_number=step.step_number,
        module_instance_id=step.module_instance_id,
        module_name="",
        inputs=step.inputs,
        outputs=step.outputs,
        error=step.error
    )
    for step in execution_result.steps
]

# Convert executed actions to API schema
action_dtos = [
    SimulatedAction(
        action_module_name=action_name,
        inputs=action_inputs,
        simulation_note="Action not executed in simulation mode"
    )
    for action_name, action_inputs in execution_result.executed_actions.items()
]

# Build response
return SimulateTemplateResponse(
    template_matching={
        "status": "success",
        "message": "Simulation mode - template matching skipped"
    },
    data_extraction=DataExtractionSimulation(
        status="success",
        extracted_data=extracted_data,
        validation_results=[]
    ),
    pipeline_execution=PipelineExecutionSimulation(
        status=execution_result.status,
        error_message=execution_result.error,
        steps=step_dtos,
        simulated_actions=action_dtos
    )
)
```

**Solution:** Create mapper function

**New Code:**

**In `api/mappers/pdf_templates.py` (add new function):**

```python
from api.schemas.pdf_templates import (
    SimulateTemplateResponse,
    DataExtractionSimulation,
    PipelineExecutionSimulation,
    PipelineStepSimulation,
    SimulatedAction,
)

def convert_simulation_result_to_api(
    extracted_data: dict[str, Any],
    execution_result
) -> SimulateTemplateResponse:
    """
    Convert simulation results to API response.

    Args:
        extracted_data: Dictionary of extracted field values
        execution_result: Domain execution result object

    Returns:
        SimulateTemplateResponse for API
    """
    # Convert execution steps
    step_dtos = [
        PipelineStepSimulation(
            step_number=step.step_number,
            module_instance_id=step.module_instance_id,
            module_name="",
            inputs=step.inputs,
            outputs=step.outputs,
            error=step.error
        )
        for step in execution_result.steps
    ]

    # Convert executed actions
    action_dtos = [
        SimulatedAction(
            action_module_name=action_name,
            inputs=action_inputs,
            simulation_note="Action not executed in simulation mode"
        )
        for action_name, action_inputs in execution_result.executed_actions.items()
    ]

    # Build complete response
    return SimulateTemplateResponse(
        template_matching={
            "status": "success",
            "message": "Simulation mode - template matching skipped"
        },
        data_extraction=DataExtractionSimulation(
            status="success",
            extracted_data=extracted_data,
            validation_results=[]
        ),
        pipeline_execution=PipelineExecutionSimulation(
            status=execution_result.status,
            error_message=execution_result.error,
            steps=step_dtos,
            simulated_actions=action_dtos
        )
    )
```

**In `api/routers/pdf_templates.py:273-400` (update simulate_template):**

```python
@router.post("/simulate", response_model=SimulateTemplateResponse, status_code=status.HTTP_200_OK)
async def simulate_template(
    pdf_source: str = Form(...),
    extraction_fields: str = Form(...),
    pipeline_state: str = Form(...),
    pdf_file_id: Optional[int] = Form(None),
    pdf_file: Optional[UploadFile] = File(None),
    template_service: PdfTemplateService = Depends(lambda: ServiceContainer.get_pdf_template_service()),
    pdf_service: 'PdfFilesService' = Depends(lambda: ServiceContainer.get_pdf_files_service())
) -> SimulateTemplateResponse:
    """Simulate template processing without persistence."""

    # Get PDF bytes based on source
    if pdf_source == "stored":
        if pdf_file_id is None:
            raise ValidationError("pdf_file_id is required when pdf_source is 'stored'")
        pdf_bytes, _ = pdf_service.get_pdf_file_bytes(pdf_file_id)
    elif pdf_source == "upload":
        if pdf_file is None:
            raise ValidationError("pdf_file is required when pdf_source is 'upload'")
        if not pdf_file.filename or not pdf_file.filename.endswith('.pdf'):
            raise ValidationError("Invalid file type - must be a PDF")
        pdf_bytes = await pdf_file.read()
    else:
        raise ValidationError(f"Invalid pdf_source: {pdf_source}. Must be 'stored' or 'upload'")

    # Parse form data and convert to domain types (mapper handles this)
    extraction_fields_domain, pipeline_state_domain = parse_simulation_form_data(
        extraction_fields=extraction_fields,
        pipeline_state=pipeline_state
    )

    # Call simulate service
    extracted_data, execution_result = template_service.simulate(
        pdf_bytes=pdf_bytes,
        extraction_fields=extraction_fields_domain,
        pipeline_state=pipeline_state_domain
    )

    # Convert result using mapper
    return convert_simulation_result_to_api(extracted_data, execution_result)
```

**In `api/mappers/pdf_templates.py` (add helper function):**

```python
def parse_simulation_form_data(
    extraction_fields: str,
    pipeline_state: str
) -> tuple[list[ExtractionFieldDomain], Any]:
    """
    Parse simulation form data into domain types.

    Args:
        extraction_fields: JSON string of extraction fields
        pipeline_state: JSON string of pipeline state

    Returns:
        Tuple of (extraction_fields_domain, pipeline_state_domain)

    Raises:
        ValidationError: If JSON parsing or validation fails
    """
    import json
    from api.schemas.pdf_templates import ExtractionField as ExtractionFieldSchema
    from api.schemas.pipelines import PipelineStateDTO
    from api.mappers.pipelines import convert_dto_to_pipeline_state

    # Parse JSON
    try:
        extraction_fields_data = json.loads(extraction_fields)
        pipeline_state_data = json.loads(pipeline_state)
    except json.JSONDecodeError as e:
        from shared.exceptions.service import ValidationError
        raise ValidationError(f"Invalid JSON in request fields: {str(e)}")

    # Validate extraction fields
    try:
        parsed_extraction_fields = [
            ExtractionFieldSchema(**field) for field in extraction_fields_data
        ]
    except Exception as e:
        from shared.exceptions.service import ValidationError
        raise ValidationError(f"Invalid extraction fields format: {str(e)}")

    # Convert to domain types
    extraction_fields_domain = convert_extraction_fields_to_domain(parsed_extraction_fields)

    pipeline_state_dto = PipelineStateDTO(**pipeline_state_data)
    pipeline_state_domain = convert_dto_to_pipeline_state(pipeline_state_dto)

    return extraction_fields_domain, pipeline_state_domain
```

---

## Implementation Plan

### Phase 1: pipelines.py (Estimated: 30-45 minutes)

1. **Add service method** (10 min)
   - File: `features/pipelines/service.py`
   - Add `get_compiled_steps()` method
   - Test: Verify method works correctly

2. **Create mapper function** (10 min)
   - File: `api/mappers/pipelines.py`
   - Add `convert_execution_result_to_api()` function
   - Test: Verify DTO construction works

3. **Update router** (15 min)
   - File: `api/routers/pipelines.py`
   - Move import from line 148 to top of file
   - Update `execute_pipeline` to use service method and mapper
   - Remove direct repository access
   - Test: Execute pipeline endpoint

4. **Integration test** (10 min)
   - Test `POST /api/pipelines/{id}/execute` endpoint
   - Verify response structure unchanged
   - Check logs for proper execution flow

### Phase 2: pdf_templates.py (Estimated: 1.5-2 hours)

1. **Create new schemas** (15 min)
   - File: `api/schemas/pdf_templates.py`
   - Add `CreatePdfTemplateFromStoredRequest`
   - Verify Pydantic validation works

2. **Create mapper functions** (30 min)
   - File: `api/mappers/pdf_templates.py`
   - Add `create_template_from_stored_request_to_domain()`
   - Add `create_template_from_upload_form_to_domain()`
   - Add `parse_simulation_form_data()`
   - Add `convert_simulation_result_to_api()`
   - Test each function individually

3. **Split create endpoint** (30 min)
   - File: `api/routers/pdf_templates.py`
   - Replace `create_pdf_template` with two endpoints:
     - `create_pdf_template_from_stored` (POST /from-stored)
     - `create_pdf_template_from_upload` (POST /from-upload)
   - Use new mappers
   - Test both endpoints

4. **Update simulate endpoint** (20 min)
   - File: `api/routers/pdf_templates.py`
   - Update `simulate_template` to use new mappers
   - Remove inline DTO construction
   - Test endpoint

5. **Update frontend calls** (15 min)
   - Find all frontend calls to `POST /api/pdf-templates`
   - Update to use correct endpoint based on PDF source
   - Test template creation flow

6. **Integration tests** (20 min)
   - Test template creation from stored PDF
   - Test template creation from upload
   - Test template simulation
   - Verify all responses match expected format

### Phase 3: Documentation & Cleanup (Estimated: 30 minutes)

1. **Update API documentation** (15 min)
   - Document new endpoints
   - Add examples for both create endpoints
   - Update any relevant README files

2. **Code cleanup** (10 min)
   - Remove any unused imports
   - Verify all error handling is consistent
   - Check logging statements

3. **Final review** (5 min)
   - Verify all routers follow the standard pattern
   - Check for any remaining inline logic
   - Ensure all mappers are in correct location

---

## Testing Checklist

### pipelines.py
- [ ] `GET /api/pipelines` - List pipelines
- [ ] `GET /api/pipelines/{id}` - Get pipeline detail
- [ ] `POST /api/pipelines` - Create pipeline
- [ ] `POST /api/pipelines/validate` - Validate pipeline
- [ ] `POST /api/pipelines/{id}/execute` - Execute pipeline (MAIN CHANGE)

### pdf_templates.py
- [ ] `GET /api/pdf-templates` - List templates
- [ ] `GET /api/pdf-templates/{id}` - Get template
- [ ] `GET /api/pdf-templates/{id}/versions` - Get version list
- [ ] `GET /api/pdf-templates/versions/{version_id}` - Get version detail
- [ ] `POST /api/pdf-templates/from-stored` - Create from stored PDF (NEW)
- [ ] `POST /api/pdf-templates/from-upload` - Create from upload (NEW)
- [ ] `PUT /api/pdf-templates/{id}` - Update template
- [ ] `POST /api/pdf-templates/{id}/activate` - Activate template
- [ ] `POST /api/pdf-templates/{id}/deactivate` - Deactivate template
- [ ] `POST /api/pdf-templates/simulate` - Simulate template (CHANGED)

---

## Success Criteria

All routers should meet these criteria:

- [ ] Router file contains only HTTP endpoint definitions
- [ ] No business logic in router functions
- [ ] No direct repository access in routers
- [ ] All data transformations use mapper functions
- [ ] All mappers in `api/mappers/` directory
- [ ] Service layer returns domain types only
- [ ] Response types explicitly declared with `response_model`
- [ ] All imports at top of file (no inline imports)
- [ ] Consistent error handling patterns
- [ ] No manual JSON parsing in routers (use Pydantic or mappers)

---

## Files to Modify

### Modify Existing Files

1. `server-new/src/api/routers/pipelines.py`
   - Lines 23-28: Update imports
   - Lines 148-149: Remove inline import
   - Lines 168-259: Refactor execute_pipeline endpoint

2. `server-new/src/api/mappers/pipelines.py`
   - Add: `convert_execution_result_to_api()` function

3. `server-new/src/features/pipelines/service.py`
   - Add: `get_compiled_steps()` method

4. `server-new/src/api/routers/pdf_templates.py`
   - Lines 96-204: Replace create_pdf_template with two new endpoints
   - Lines 273-400: Refactor simulate_template endpoint

5. `server-new/src/api/schemas/pdf_templates.py`
   - Add: `CreatePdfTemplateFromStoredRequest` class

6. `server-new/src/api/mappers/pdf_templates.py`
   - Add: `create_template_from_stored_request_to_domain()` function
   - Add: `create_template_from_upload_form_to_domain()` function
   - Add: `parse_simulation_form_data()` function
   - Add: `convert_simulation_result_to_api()` function

### No Changes Needed

- `server-new/src/api/routers/pdf_files.py` - Already compliant
- `server-new/src/api/routers/email_configs.py` - Reference standard
- `server-new/src/api/routers/modules.py` - Reference standard

---

## Notes & Gotchas

1. **Frontend Integration:** When splitting the pdf_templates create endpoint, you'll need to update the frontend to call the correct endpoint based on whether the user is uploading a file or using a stored PDF.

2. **Backward Compatibility:** The original `POST /api/pdf-templates` endpoint will be removed. If there are external clients, you may want to keep it temporarily with a deprecation warning.

3. **Form vs JSON:** The split endpoints approach means the stored PDF endpoint can use a clean JSON request body, while only the upload endpoint needs multipart/form-data. This is better API design.

4. **Error Messages:** Ensure all ValidationErrors have clear, actionable messages for the frontend to display.

5. **Testing Order:** Test pipelines.py changes first since they're simpler. This will validate the pattern before tackling the more complex pdf_templates.py changes.

6. **Service Layer Boundary:** If you find yourself wanting to add more logic to routers or mappers, it probably belongs in the service layer. Ask: "Is this HTTP/serialization concern or business logic?"

---

## Reference Files

**Standards to Follow:**
- `server-new/src/api/routers/email_configs.py`
- `server-new/src/api/routers/modules.py`
- `server-new/src/api/routers/pdf_files.py`

**Files with Good Patterns:**
- `server-new/src/api/mappers/email_configs.py` - Bidirectional conversions
- `server-new/src/api/mappers/modules.py` - Simple mapper with dataclass conversion
- `server-new/src/api/mappers/pipelines.py` - Complex nested object conversion

---

## Questions to Resolve

1. **Frontend Impact:** Do we have a comprehensive list of all frontend calls to the PDF templates create endpoint? Need to ensure no calls are missed when switching to the new endpoints.

2. **Deprecation Strategy:** Should we keep the old endpoint temporarily with a deprecation warning, or do a clean break?

3. **Additional Endpoints:** Are there other endpoints in pdf_templates.py that use the same Form-based pattern for simulate? (Answer: Yes - simulate_template, which is included in this refactor)

---

## Progress Tracking

- [x] Analysis complete
- [ ] Phase 1: pipelines.py refactoring
- [ ] Phase 2: pdf_templates.py refactoring
- [ ] Phase 3: Documentation & cleanup
- [ ] All tests passing
- [ ] Code review complete
- [ ] Frontend updated
- [ ] Deployed to dev environment

---

## Last Session Context

**Date:** 2025-10-27
**Branch:** server_unification
**Status:** Analysis complete, ready to begin implementation

**What We Did:**
1. Established email_configs and modules as the reference standard
2. Analyzed all API routers against this standard
3. Identified specific issues with line numbers
4. Created detailed refactoring plan with code examples

**Next Step:**
Begin Phase 1 - Refactor pipelines.py following the step-by-step plan above.

**Command to Start:**
```bash
# Ensure you're on the correct branch
git status

# Start with Phase 1, Step 1: Add service method
# Open: server-new/src/features/pipelines/service.py
```
