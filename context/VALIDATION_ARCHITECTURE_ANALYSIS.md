# Validation Architecture Analysis

**Issue**: Endpoint contains business logic that should be in the service layer

---

## Current Architecture

### ✅ What's Correct

**PipelineValidator** (`server-new/src/features/pipelines/utils/validation.py`):
- Comprehensive 5-stage validation:
  1. **Schema validation** - Node IDs, types, format
  2. **Index building** - Preprocessing
  3. **Module validation** - Catalog, groups, type vars, config
  4. **Edge validation** - Connections, types, cardinality
  5. **Graph validation** - Cycles, DAG

**PipelineService.validate_pipeline()** (`server-new/src/features/pipelines/service.py` lines 718-748):
```python
def validate_pipeline(self, pipeline_state: PipelineState) -> Dict[str, Any]:
    """
    Returns:
        Dict with:
            - valid: bool (True if no errors)
            - error: Error dict (code, message, where) if validation failed
    """
    try:
        self._validate_pipeline(pipeline_state)  # Calls PipelineValidator
        return {"valid": True}
    except PipelineValidationError as e:
        return {
            "valid": False,
            "error": {
                "code": e.code,
                "message": str(e),
                "where": e.where
            }
        }
```

---

### ❌ What's Wrong

**Endpoint** (`server-new/src/api/routers/pipelines.py` lines 126-223):

**Lines 154-163**: Converts service result to DTO
```python
error_dtos = []
if not validation_result["valid"] and "error" in validation_result:
    error_dtos = [
        ValidationErrorDTO(
            code=validation_result["error"]["code"],
            message=validation_result["error"]["message"],
            where=validation_result["error"].get("where")
        )
    ]
```
✅ This is fine - just DTO conversion

**Lines 165-215**: DUPLICATES validation logic ❌
```python
# Validate module configurations (even if structure validation failed)
from shared.utils.registry import get_registry
from pydantic import ValidationError

module_registry = get_registry()

for module_instance in pipeline_state.modules:
    # Extract module_id from module_ref (format: "module_id:version")
    module_id = module_instance.module_ref.split(":")[0] if ":" in module_instance.module_ref else module_instance.module_ref

    # Get module handler from registry  ❌ DUPLICATE - Validator already does catalog lookup
    handler = module_registry.get(module_id)
    if not handler:
        error_dtos.append(
            ValidationErrorDTO(
                code="module_not_found",
                message=f"Module '{module_id}' not found in registry",
                where={"module_instance_id": module_instance.module_instance_id}
            )
        )
        continue

    # Validate config against module's Pydantic schema  ❌ BUSINESS LOGIC IN ENDPOINT
    try:
        ConfigModel = handler.config_class()
        ConfigModel(**module_instance.config)
    except ValidationError as e:
        # Pydantic validation failed - extract errors
        for error in e.errors():
            field_path = " -> ".join(str(loc) for loc in error["loc"])
            error_dtos.append(
                ValidationErrorDTO(
                    code="invalid_config",
                    message=f"Module {module_instance.module_instance_id}: {field_path}: {error['msg']}",
                    where={
                        "module_instance_id": module_instance.module_instance_id,
                        "field": field_path,
                        "type": error["type"]
                    }
                )
            )
```

---

## Problems Identified

### 1. **Duplication** - Endpoint re-implements module catalog lookup
- PipelineValidator already checks module exists in catalog (line 276-285)
- Endpoint checks again using registry (lines 176-185)
- Same validation, different implementation

### 2. **Business Logic in Endpoint** - Pydantic config validation
- Endpoint validates config using Pydantic (lines 187-206)
- This is business logic that should be in validator
- Endpoint should only handle HTTP concerns (request/response)

### 3. **Two Sources of Truth** - Registry vs Repository
- PipelineValidator uses `module_catalog_repo` (database)
- Endpoint uses `get_registry()` (in-memory module handlers)
- Should use one consistent approach

### 4. **Config Validation Gap** - Validator only checks required fields
- PipelineValidator checks required fields exist (line 489-499)
- But doesn't validate field types, formats, constraints
- Endpoint fills this gap, but it should be in validator

---

## Current Validation Comparison

| Check | PipelineValidator | Endpoint | Notes |
|-------|------------------|----------|-------|
| Schema validation | ✅ Yes | ❌ No | Correct |
| Module exists in catalog | ✅ Yes (repo) | ✅ Yes (registry) | ❌ Duplicate |
| Config required fields | ✅ Yes | ❌ No | Correct |
| Config types/formats | ❌ No | ✅ Yes | ❌ Should be in validator |
| Group cardinality | ✅ Yes | ❌ No | Correct |
| Type variables | ✅ Yes | ❌ No | Correct |
| Edge validation | ✅ Yes | ❌ No | Correct |
| Cycle detection | ✅ Yes | ❌ No | Correct |

---

## Correct Architecture

### Principle: Thin Endpoints, Fat Services

**Endpoint should only**:
1. Parse request
2. Call service method
3. Convert result to DTO
4. Return response

**Service/Validator should**:
1. Contain all business logic
2. Perform all validation
3. Return domain objects

---

## Solution Plan

### Option A: Move Pydantic Validation to Validator (Recommended)

**1. Update PipelineValidator** - Add full config validation:

```python
def _check_config(self, module, template) -> None:
    """
    Validate module config against schema using Pydantic.
    Checks required fields AND validates types/formats/constraints.
    """
    config_schema = template.config_schema

    # Get module handler from registry for Pydantic validation
    from shared.utils.registry import get_registry
    module_registry = get_registry()

    module_id, _ = self._parse_module_ref(module.module_ref)
    handler = module_registry.get(module_id)

    if handler:
        # Validate config using Pydantic model
        try:
            ConfigModel = handler.config_class()
            ConfigModel(**module.config)
        except ValidationError as e:
            # Take first error only (fail fast)
            first_error = e.errors()[0]
            field_path = " -> ".join(str(loc) for loc in first_error["loc"])
            raise ModuleValidationError(
                message=f"Config field '{field_path}': {first_error['msg']}",
                code="invalid_config",
                where={
                    "module_instance_id": module.module_instance_id,
                    "field": field_path,
                    "type": first_error["type"]
                }
            )
    else:
        # Fallback: Check required fields only (current behavior)
        if "required" in config_schema:
            for required_field in config_schema["required"]:
                if required_field not in module.config:
                    raise ModuleValidationError(
                        message=f"Required config field '{required_field}' missing",
                        code="missing_required_config",
                        where={
                            "module_instance_id": module.module_instance_id,
                            "missing_field": required_field,
                        }
                    )
```

**2. Simplify Endpoint** - Remove all business logic:

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
    """
    # Convert API request to domain type
    from api.mappers.pipelines import convert_dto_to_pipeline_state
    pipeline_state = convert_dto_to_pipeline_state(request.pipeline_json)

    # Call service - all validation happens here
    validation_result = pipeline_service.validate_pipeline(pipeline_state)

    # Convert service result to API response
    if validation_result["valid"]:
        return ValidatePipelineResponse(valid=True, error=None)
    else:
        return ValidatePipelineResponse(
            valid=False,
            error=ValidationErrorDTO(
                code=validation_result["error"]["code"],
                message=validation_result["error"]["message"],
                where=validation_result["error"].get("where")
            )
        )
```

**Lines of Code**:
- Before: ~100 lines (endpoint has business logic)
- After: ~20 lines (endpoint just calls service)

---

### Option B: Create Separate Config Validation Method (Alternative)

If Pydantic validation shouldn't be in the main validator, create a separate service method:

```python
# In PipelineService
def validate_pipeline_with_config(self, pipeline_state: PipelineState) -> Dict[str, Any]:
    """
    Validate pipeline structure AND module configs using Pydantic.
    """
    # First validate structure
    try:
        self._validate_pipeline(pipeline_state)
    except PipelineValidationError as e:
        return {"valid": False, "error": {...}}

    # Then validate configs
    try:
        self._validate_configs(pipeline_state)
        return {"valid": True}
    except PipelineValidationError as e:
        return {"valid": False, "error": {...}}

def _validate_configs(self, pipeline_state: PipelineState) -> None:
    """Validate all module configs using Pydantic"""
    from shared.utils.registry import get_registry
    module_registry = get_registry()

    for module_instance in pipeline_state.modules:
        # ... Pydantic validation logic ...
```

Then endpoint just calls `validate_pipeline_with_config()`.

---

## Recommended Changes

### Step 1: Enhance PipelineValidator
- Add Pydantic config validation to `_check_config()` method
- Use registry for handler lookup (already available)
- Fail fast on first config error

### Step 2: Simplify Endpoint
- Remove lines 165-215 (all business logic)
- Keep only: request parsing → service call → response conversion
- Reduce endpoint to ~20 lines

### Step 3: Update Schema (for errors array → error object)
- Change `errors: List[]` to `error: Optional`
- Update ValidatePipelineResponse schema
- This is separate from architecture fix but can be done together

---

## Benefits

1. **Separation of Concerns** - Endpoint only handles HTTP, service handles business logic
2. **Reusability** - Validation logic can be called from anywhere (not just endpoint)
3. **Testability** - Can test validation without HTTP layer
4. **Single Source of Truth** - All validation in one place
5. **Maintainability** - Easier to find and update validation rules
6. **Consistency** - Same validation rules everywhere

---

## Testing After Changes

- [ ] Valid pipeline passes all checks
- [ ] Invalid module ref caught by validator
- [ ] Module not in catalog caught by validator
- [ ] Missing required config field caught by validator
- [ ] Invalid config type/format caught by validator (NEW)
- [ ] Type mismatch caught by validator
- [ ] Cycle detection works
- [ ] Endpoint is thin (no business logic)

---

## Files to Change

### Backend (2 files):
1. **`server-new/src/features/pipelines/utils/validation.py`**
   - Enhance `_check_config()` method
   - Add Pydantic validation

2. **`server-new/src/api/routers/pipelines.py`**
   - Remove lines 165-215 (business logic)
   - Simplify to: parse → call service → convert response

### Frontend (0 files):
- No changes needed if we also fix errors array → error object
- Or minimal changes to handle single error (see VALIDATION_ERROR_REFACTOR_PLAN.md)

---

## Priority

**High Priority** - This is an architectural issue that violates separation of concerns.

The endpoint should be fixed before adding more validation logic, otherwise the duplication will get worse.
