# Validation Error Refactor Plan: Array → Single Object

**Goal**: Change validation endpoint from returning `errors: []` (array) to `error: {}` (single object)

**Current Behavior**: Backend can return multiple validation errors in an array
**Desired Behavior**: Backend returns only the first validation error as a single object

---

## Backend Changes Required

### 1. **API Schema** - `server-new/src/api/schemas/pipelines.py`

**Current** (lines 137-140):
```python
class ValidatePipelineResponse(BaseModel):
    """Response for POST /pipelines/validate"""
    valid: bool
    errors: List[ValidationErrorDTO] = []
```

**Change To**:
```python
class ValidatePipelineResponse(BaseModel):
    """Response for POST /pipelines/validate"""
    valid: bool
    error: Optional[ValidationErrorDTO] = None  # Single error or None
```

**Impact**: This is the main schema change that defines the API contract.

---

### 2. **Router** - `server-new/src/api/routers/pipelines.py`

**Current Logic** (lines 154-223):
1. Creates `error_dtos = []` (empty array)
2. Appends structural validation error if exists
3. Loops through modules, appends multiple errors:
   - Module not found errors
   - Config validation errors (can be many per module)
   - Unexpected validation errors
4. Returns all errors: `ValidatePipelineResponse(valid=is_valid, errors=error_dtos)`

**Change To**:
```python
@router.post("/validate", response_model=ValidatePipelineResponse)
async def validate_pipeline(
    request: ValidatePipelineRequest,
    pipeline_service: PipelineService = Depends(
        lambda: ServiceContainer.get_pipeline_service()
    )
) -> ValidatePipelineResponse:
    """
    Validate pipeline structure and module configurations without saving.

    Returns the FIRST validation error encountered, or valid=True if no errors.
    """
    # Convert API request to domain type
    from api.mappers.pipelines import convert_dto_to_pipeline_state
    pipeline_state = convert_dto_to_pipeline_state(request.pipeline_json)

    # Validate pipeline structure
    validation_result = pipeline_service.validate_pipeline(pipeline_state)

    # Check if structural validation failed (return immediately)
    if not validation_result["valid"] and "error" in validation_result:
        return ValidatePipelineResponse(
            valid=False,
            error=ValidationErrorDTO(
                code=validation_result["error"]["code"],
                message=validation_result["error"]["message"],
                where=validation_result["error"].get("where")
            )
        )

    # Validate module configurations
    from shared.utils.registry import get_registry
    from pydantic import ValidationError

    module_registry = get_registry()

    for module_instance in pipeline_state.modules:
        # Extract module_id from module_ref
        module_id = module_instance.module_ref.split(":")[0] if ":" in module_instance.module_ref else module_instance.module_ref

        # Get module handler from registry
        handler = module_registry.get(module_id)
        if not handler:
            # Return immediately on first error
            return ValidatePipelineResponse(
                valid=False,
                error=ValidationErrorDTO(
                    code="module_not_found",
                    message=f"Module '{module_id}' not found in registry",
                    where={"module_instance_id": module_instance.module_instance_id}
                )
            )

        # Validate config against module's Pydantic schema
        try:
            ConfigModel = handler.config_class()
            ConfigModel(**module_instance.config)
        except ValidationError as e:
            # Return first Pydantic validation error
            first_error = e.errors()[0]
            field_path = " -> ".join(str(loc) for loc in first_error["loc"])
            return ValidatePipelineResponse(
                valid=False,
                error=ValidationErrorDTO(
                    code="invalid_config",
                    message=f"Module {module_instance.module_instance_id}: {field_path}: {first_error['msg']}",
                    where={
                        "module_instance_id": module_instance.module_instance_id,
                        "field": field_path,
                        "type": first_error["type"]
                    }
                )
            )
        except Exception as e:
            # Unexpected error during config validation
            return ValidatePipelineResponse(
                valid=False,
                error=ValidationErrorDTO(
                    code="config_validation_error",
                    message=f"Module {module_instance.module_instance_id}: {str(e)}",
                    where={"module_instance_id": module_instance.module_instance_id}
                )
            )

    # No errors found - valid pipeline
    return ValidatePipelineResponse(
        valid=True,
        error=None
    )
```

**Key Changes**:
- Remove `error_dtos = []` array
- Return immediately on first error encountered
- Use early returns instead of collecting errors
- Return `error=None` when valid

---

### 3. **Service** - `server-new/src/features/pipelines/service.py`

**Current** (lines 718-748):
```python
def validate_pipeline(self, pipeline_state: PipelineState) -> Dict[str, Any]:
    """
    Returns:
        Dict with:
            - valid: bool (True if no errors)
            - error: Error dict (code, message, where) if validation failed
    """
```

**No Change Needed** ✅
- Service already returns single `error: {}` object (not array)
- This is correct as-is

---

### 4. **Private Validation** - `server-new/src/features/pipelines/service.py`

**Current**: `_validate_pipeline()` raises `PipelineValidationError` on first error
**No Change Needed** ✅
- Already stops at first error (doesn't collect multiple)

---

## Frontend Changes Required

### 1. **API Types** - `client/src/renderer/features/pipelines/api/types.ts`

**Current** (lines 162-165):
```typescript
export interface ValidatePipelineResponseDTO {
  valid: boolean;
  errors: ValidationErrorDTO[];
}
```

**Change To**:
```typescript
export interface ValidatePipelineResponseDTO {
  valid: boolean;
  error: ValidationErrorDTO | null;
}
```

---

### 2. **Domain Types** - `client/src/renderer/features/pipelines/types.ts`

**Current** (lines 203-206):
```typescript
export interface ValidatePipelineResponse {
  valid: boolean;
  errors: ValidationError[];
}
```

**Change To**:
```typescript
export interface ValidatePipelineResponse {
  valid: boolean;
  error: ValidationError | null;
}
```

---

### 3. **Validation Hook** - `client/src/renderer/features/pipelines/hooks/usePipelineValidation.ts`

**Current** (line 71):
```typescript
setError(result.error || null);
```

**No Change Needed** ✅
- Already expects `result.error` (single object)
- This is correct as-is

---

### 4. **Pipeline Create Page** - `client/src/renderer/pages/dashboard/pipelines/create.tsx`

**Current** (lines 96-101):
```typescript
if (validationResult.valid) {
  alert('✅ Pipeline is valid!');
} else {
  console.error('❌ Pipeline validation failed:');
  validationResult.errors.forEach((error) => {
    console.error(`  - [${error.code}] ${error.message}`, error.where);
  });
  alert(`❌ Pipeline validation failed with ${validationResult.errors.length} error(s).\n\nCheck the browser console for details.`);
}
```

**Change To**:
```typescript
if (validationResult.valid) {
  alert('✅ Pipeline is valid!');
} else {
  const error = validationResult.error;
  if (error) {
    console.error(`❌ Pipeline validation failed: [${error.code}] ${error.message}`, error.where);
    alert(`❌ Pipeline validation failed:\n\n[${error.code}] ${error.message}\n\nCheck the browser console for details.`);
  } else {
    alert('❌ Pipeline validation failed with unknown error.');
  }
}
```

---

### 5. **Template Builder** - `client/src/renderer/features/templates/components/builder/TemplateBuilderModal.tsx`

**Current**: Already uses single `pipelineValidationError` correctly
**No Change Needed** ✅

---

## Summary of Changes

### Backend (3 files):
1. ✅ **Schema** - Change `errors: List[]` to `error: Optional`
2. ✅ **Router** - Remove array, use early returns, return first error only
3. ✅ **Service** - No changes (already correct)

### Frontend (4 files):
1. ✅ **API Types** - Change `errors: []` to `error: null`
2. ✅ **Domain Types** - Change `errors: []` to `error: null`
3. ✅ **Validation Hook** - No changes (already correct)
4. ✅ **Create Page** - Change from `errors.forEach()` to single `error`
5. ✅ **Template Builder** - No changes (already correct)

---

## Benefits of This Change

1. **Simpler API Contract**: Single error object is easier to consume
2. **Better UX**: Shows most important error first (structural issues before config issues)
3. **Performance**: Early return on first error (no need to validate everything)
4. **Consistency**: Template builder already expects single error
5. **Clearer Error Hierarchy**:
   - Structural errors (cycles, type mismatches) are fatal
   - Config errors come after structural validation passes

---

## Testing Checklist

After implementing changes, test these scenarios:

- [ ] Valid pipeline → `{ valid: true, error: null }`
- [ ] Empty pipeline → `{ valid: false, error: { code: 'empty_pipeline', ... } }`
- [ ] Type mismatch → `{ valid: false, error: { code: 'type_mismatch', ... } }`
- [ ] Cycle detected → `{ valid: false, error: { code: 'cycle_detected', ... } }`
- [ ] Unconnected input → `{ valid: false, error: { code: 'unconnected_input', ... } }`
- [ ] Module not found → `{ valid: false, error: { code: 'module_not_found', ... } }`
- [ ] Invalid config → `{ valid: false, error: { code: 'invalid_config', ... } }`
- [ ] Multiple errors → Returns first error only, not all

---

## Backward Compatibility

⚠️ **Breaking Change**: This is a breaking API change. If any other code consumes the validation endpoint:
- Must be updated to use `error` instead of `errors`
- Must handle single object instead of array
- Must not expect multiple errors

Currently known consumers:
1. Pipeline create page - Needs update
2. Template builder - Already correct
3. Validation hook - Already correct
