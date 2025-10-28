# PDF Templates API Refactoring Analysis

**Created:** 2025-10-28
**Status:** Analysis Complete - Ready for Implementation
**Scope:** Clean up pdf_templates schemas, remove duplication, align with pipelines pattern

---

## Current State Analysis

### 1. Schema Duplication Issues

**DUPLICATE: Pipeline State Types** (`api/schemas/pdf_templates.py:17-51`)

These types are **completely duplicated** from `api/schemas/pipelines.py` but with **different field names**:

```python
# pdf_templates.py (WRONG - outdated structure)
class PipelineEntryPoint(BaseModel):
    id: str                    # ❌ Should be: node_id
    label: str                 # ❌ Should be: name
    field_reference: str       # ❌ Doesn't exist in canonical type

class PipelineNodePin(BaseModel):
    node_id: str
    name: str
    type: List[str]            # ❌ Should be: str (single type)

class PipelineModuleInstance(BaseModel):
    instance_id: str           # ❌ Should be: module_instance_id
    module_id: str             # ❌ Should be: module_ref
    config: Dict[str, Any]
    inputs: List[PipelineNodePin]
    outputs: List[PipelineNodePin]

class PipelineConnection(BaseModel):
    from_node_id: str
    to_node_id: str

class PipelineState(BaseModel):
    entry_points: List[PipelineEntryPoint]
    modules: List[PipelineModuleInstance]
    connections: List[PipelineConnection]

class VisualState(BaseModel):
    positions: Dict[str, Dict[str, float]]  # ❌ Should be: Dict[str, Position]
```

**CANONICAL VERSION** (`api/schemas/pipelines.py:12-63`):
```python
# pipelines.py (CORRECT - canonical)
class Node(BaseModel):
    node_id: str
    type: str                  # ✅ Single type string
    name: str
    position_index: int
    group_index: int

class EntryPoint(BaseModel):
    node_id: str               # ✅ Consistent with Node
    name: str                  # ✅ Not "label"

class ModuleInstance(BaseModel):
    module_instance_id: str    # ✅ Consistent naming
    module_ref: str            # ✅ "module_ref" not "module_id"
    config: Dict[str, Any]
    inputs: List[Node]         # ✅ Full Node objects
    outputs: List[Node]        # ✅ Full Node objects

class NodeConnection(BaseModel):
    from_node_id: str
    to_node_id: str

class PipelineState(BaseModel):
    entry_points: List[EntryPoint]
    modules: List[ModuleInstance]
    connections: List[NodeConnection]

class Position(BaseModel):
    x: float
    y: float

class VisualState(BaseModel):
    modules: Dict[str, Position]      # ✅ Proper Position objects
    entry_points: Dict[str, Position]  # ✅ Separate EP positions
```

**IMPACT:**
- Templates use outdated, incompatible pipeline schemas
- Causes confusion and bugs when trying to use pipeline utilities
- Mappers have to convert between incompatible formats

---

### 2. Simulation Response Issues

**CURRENT:** Simulation returns complex nested structure with validation results

```python
# api/schemas/pdf_templates.py:139-180
class ValidationResult(BaseModel):              # ❌ Remove - validation confirmed working
    field_label: str
    required: bool
    has_value: bool
    regex_valid: Optional[bool] = None
    error: Optional[str] = None

class DataExtractionSimulation(BaseModel):
    status: Literal["success", "failure"]
    extracted_data: Optional[Dict[str, str]]    # ✅ Keep - need field values
    error_message: Optional[str]
    validation_results: List[ValidationResult]  # ❌ Remove

class PipelineStepSimulation(BaseModel):       # ❌ Duplicate of ExecutionStepResult
    step_number: int
    module_instance_id: str
    module_name: str                            # ❌ Not in canonical version
    inputs: Dict[str, Dict[str, Any]]
    outputs: Dict[str, Dict[str, Any]]
    error: Optional[Dict[str, Any]]

class SimulatedAction(BaseModel):              # ❌ Duplicate - different format
    action_module_name: str
    inputs: Dict[str, Any]
    simulation_note: str                        # ❌ Not needed

class PipelineExecutionSimulation(BaseModel):  # ❌ Duplicate of ExecutePipelineResponse
    status: Literal["success", "failure"]
    error_message: Optional[str]
    steps: List[PipelineStepSimulation]
    simulated_actions: List[SimulatedAction]

class SimulateTemplateResponse(BaseModel):
    template_matching: Dict[str, str]           # ❌ Remove - always skipped
    data_extraction: DataExtractionSimulation
    pipeline_execution: PipelineExecutionSimulation
```

**CANONICAL VERSION** (from pipelines):
```python
# api/schemas/pipelines.py:142-157
class ExecutionStepResult(BaseModel):          # ✅ Use this
    module_instance_id: str
    step_number: int
    inputs: Dict[str, Dict[str, Any]]
    outputs: Dict[str, Dict[str, Any]]
    error: Optional[str] = None                # ✅ Simple string, not dict

class ExecutePipelineResponse(BaseModel):      # ✅ Use this as base
    status: str  # "success" | "failed"
    steps: List[ExecutionStepResult]
    executed_actions: Dict[str, Dict[str, Any]]  # ✅ {module_instance_id: inputs}
    error: Optional[str] = None
```

---

### 3. What We Actually Need for Template Simulation

User wants the response to contain:

1. **Extraction Fields with Data** (bbox, name, extracted_value)
   - Need to show WHAT was extracted and WHERE (for visual display)
   - Currently: Only returns `{field_name: value}` dict
   - Need: List of `{name, bbox, page, extracted_value}`

2. **Pipeline Execution Results** (reuse from pipelines)
   - Steps executed with inputs/outputs
   - Actions that would be executed
   - Match format from `POST /pipelines/{id}/execute`

**NOT NEEDED:**
- ❌ Template matching simulation (always skipped in templates)
- ❌ Validation results (validation is working, confirmed)
- ❌ Separate "data extraction simulation" wrapper

---

## Proposed Solution

### Phase 1: Remove Duplicate Pipeline Schemas (30 minutes)

**Delete from `api/schemas/pdf_templates.py`:**
- Lines 17-51: All pipeline state types
  - `PipelineEntryPoint`
  - `PipelineNodePin`
  - `PipelineModuleInstance`
  - `PipelineConnection`
  - `PipelineState`
  - `VisualState`

**Replace with imports:**
```python
from api.schemas.pipelines import (
    PipelineState,
    VisualState,
)
```

**Update affected schemas** (lines 90-109):
```python
# CreatePdfTemplateRequest
class CreatePdfTemplateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    source_pdf_id: Optional[int] = None
    signature_objects: Dict[str, List[Dict[str, Any]]]
    extraction_fields: List[ExtractionField] = Field(..., min_length=1)
    pipeline_state: PipelineState  # ✅ Now using canonical type
    visual_state: VisualState      # ✅ Now using canonical type

# UpdatePdfTemplateRequest
class UpdatePdfTemplateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    signature_objects: Optional[Dict[str, List[Dict[str, Any]]]] = None
    extraction_fields: Optional[List[ExtractionField]] = None
    pipeline_state: Optional[PipelineState] = None  # ✅ Canonical
    visual_state: Optional[VisualState] = None      # ✅ Canonical
```

---

### Phase 2: Create New Simulation Response Schema (45 minutes)

**New schema for extracted field with data:**
```python
# api/schemas/pdf_templates.py

class ExtractedFieldResult(BaseModel):
    """Single extraction field result with bbox for visual display"""
    name: str
    description: Optional[str] = None
    bbox: Tuple[float, float, float, float]  # [x0, y0, x1, y1]
    page: int
    extracted_value: str  # The actual extracted text
```

**New simplified simulation response:**
```python
class SimulateTemplateResponse(BaseModel):
    """Response for POST /pdf-templates/simulate"""
    extraction_results: List[ExtractedFieldResult]  # Fields with extracted values
    pipeline_status: str  # "success" | "failed"
    pipeline_steps: List[ExecutionStepResult]  # Reuse from pipelines
    pipeline_actions: Dict[str, Dict[str, Any]]  # Reuse from pipelines
    pipeline_error: Optional[str] = None
```

**Import ExecutionStepResult:**
```python
from api.schemas.pipelines import (
    PipelineState,
    VisualState,
    ExecutionStepResult,  # ✅ Reuse canonical type
)
```

**Delete these types** (no longer needed):
- `ValidationResult` (lines 139-144)
- `DataExtractionSimulation` (lines 147-151)
- `PipelineStepSimulation` (lines 154-160) - replaced by `ExecutionStepResult`
- `SimulatedAction` (lines 163-166)
- `PipelineExecutionSimulation` (lines 169-173)
- Old `SimulateTemplateResponse` (lines 176-179)
- `SimulateTemplateRequestStored` (lines 125-129) - not needed with form
- `SimulateTemplateRequestUpload` (lines 132-136) - not needed with form

---

### Phase 3: Update Router to Use New Schema (30 minutes)

**In `api/routers/pdf_templates.py`:**

Update `simulate_template` endpoint (lines 273-400):

```python
@router.post("/simulate", response_model=SimulateTemplateResponse)
async def simulate_template(
    pdf_source: str = Form(...),
    extraction_fields: str = Form(...),
    pipeline_state: str = Form(...),
    pdf_file_id: Optional[int] = Form(None),
    pdf_file: Optional[UploadFile] = File(None),
    template_service: PdfTemplateService = Depends(...),
    pdf_service: PdfFilesService = Depends(...)
) -> SimulateTemplateResponse:
    """Simulate template extraction and pipeline execution"""

    # [Keep existing PDF bytes loading logic]
    # [Keep existing parsing logic - will clean up in separate refactor]

    # Call simulate service
    extracted_data, execution_result = template_service.simulate(
        pdf_bytes=pdf_bytes,
        extraction_fields=extraction_fields_domain,
        pipeline_state=pipeline_state_domain
    )

    # NEW: Build extraction results with bbox info
    extraction_results = [
        ExtractedFieldResult(
            name=field.name,
            description=field.description,
            bbox=field.bbox,
            page=field.page,
            extracted_value=extracted_data.get(field.name, "")
        )
        for field in extraction_fields_domain
    ]

    # NEW: Return simplified response using canonical ExecutionStepResult
    return SimulateTemplateResponse(
        extraction_results=extraction_results,
        pipeline_status=execution_result.status,
        pipeline_steps=execution_result.steps,  # Already ExecutionStepResult objects
        pipeline_actions=execution_result.executed_actions,
        pipeline_error=execution_result.error
    )
```

**Benefits:**
- ✅ No manual DTO construction in router
- ✅ Reuses canonical `ExecutionStepResult` from pipelines
- ✅ Provides bbox info for visual display
- ✅ Flat, simple structure (no nested "simulation" wrappers)
- ✅ Matches pattern from `POST /pipelines/{id}/execute`

---

### Phase 4: Update Mappers (if needed) (15 minutes)

**Check `api/mappers/pdf_templates.py`:**
- Remove any mappers for deleted types
- Ensure `convert_create_template_request` works with canonical `PipelineState`
- Ensure `convert_update_template_request` works with canonical `PipelineState`

**Check `api/mappers/pipelines.py`:**
- Verify `convert_dto_to_pipeline_state` is being used consistently
- No changes should be needed (already canonical)

---

## Summary of Changes

### Files to Modify:

**1. `api/schemas/pdf_templates.py`**
- ❌ Delete: Lines 17-51 (duplicate pipeline types)
- ❌ Delete: Lines 125-180 (old simulation types)
- ✅ Add: Import canonical types from `pipelines.py`
- ✅ Add: `ExtractedFieldResult` schema
- ✅ Add: New simplified `SimulateTemplateResponse`
- ✅ Update: `CreatePdfTemplateRequest` to use canonical `PipelineState`
- ✅ Update: `UpdatePdfTemplateRequest` to use canonical `PipelineState`

**Estimated reduction:** ~120 lines deleted, ~30 lines added = **-90 lines**

**2. `api/routers/pdf_templates.py`**
- ✅ Update: `simulate_template` endpoint (lines 273-400)
  - Build `extraction_results` with bbox info
  - Return new `SimulateTemplateResponse` format
  - Remove old DTO construction for steps/actions

**Estimated changes:** ~50 lines modified

**3. `api/mappers/pdf_templates.py`** (verify only)
- Check that mappers work with canonical `PipelineState`
- Remove any mappers for deleted types (if any)

**Estimated changes:** 0-20 lines

---

## Testing Checklist

After refactoring:

**Template Creation:**
- [ ] POST /pdf-templates (from stored PDF)
- [ ] POST /pdf-templates (from upload)
- [ ] Verify pipeline_state uses canonical format
- [ ] Verify visual_state uses canonical format

**Template Updates:**
- [ ] PUT /pdf-templates/{id} (metadata only)
- [ ] PUT /pdf-templates/{id} (with pipeline changes)
- [ ] Verify versioning logic still works

**Template Simulation:**
- [ ] POST /pdf-templates/simulate (stored PDF)
- [ ] POST /pdf-templates/simulate (upload)
- [ ] Verify extraction_results includes bbox, page, extracted_value
- [ ] Verify pipeline_steps matches format from pipeline execute
- [ ] Verify pipeline_actions matches format from pipeline execute
- [ ] Frontend can display extraction results visually
- [ ] Frontend can display pipeline execution trace

---

## Benefits

1. **Eliminates Duplication:**
   - Removes ~120 lines of duplicate code
   - Single source of truth for pipeline types
   - Easier to maintain and understand

2. **Consistency:**
   - Templates and Pipelines use identical schemas
   - Mappers work consistently across endpoints
   - Frontend has consistent response format

3. **Simplification:**
   - Removes unnecessary validation results
   - Removes unnecessary wrapper types
   - Flat, intuitive response structure

4. **Better Visual Display:**
   - `extraction_results` includes bbox for drawing on PDF
   - Can highlight extraction regions visually
   - Shows what was extracted and where

5. **Alignment with Pipelines:**
   - Simulation response matches pipeline execution response
   - Can reuse frontend components for both
   - Consistent error handling

---

## Implementation Order

1. **Phase 1:** Remove duplicate pipeline schemas (30 min)
2. **Phase 2:** Create new simulation response schema (45 min)
3. **Phase 3:** Update router endpoint (30 min)
4. **Phase 4:** Verify/update mappers (15 min)
5. **Testing:** Run full test suite (30 min)

**Total Estimated Time:** 2.5 hours

---

## Next Steps

After completing this refactoring:

1. Consider splitting create endpoint into `/from-stored` and `/from-upload` (from API_ARCHITECTURE_REFACTORING_PLAN.md)
2. Move JSON parsing logic from router to mappers
3. Consider adding validation endpoint like pipelines has
4. Add comprehensive tests for template simulation

---

## Notes

- Service layer (`PdfTemplateService.simulate`) already returns correct data structure
- No service layer changes needed
- Router is just reformatting the response incorrectly
- Frontend will need updates to handle new response format
