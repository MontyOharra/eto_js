# Pipeline Validation Auto-Validation Continuity Document

**Date**: 2025-10-24
**Branch**: server_unification
**Session Context**: Fixed auto-validation to use onChange callback pattern with debouncing

## Current State

### What Was Completed

1. **Backend Validation Infrastructure** ✅
   - Created comprehensive exception hierarchy in `server-new/src/shared/exceptions/pipeline_validation.py`
   - Exception classes: `PipelineValidationError` (base), `SchemaValidationError`, `ModuleValidationError`, `EdgeValidationError`, `GraphValidationError`
   - All exceptions use fail-fast single-error approach (not error lists)

2. **Validation Orchestrator** ✅
   - Created `server-new/src/features/pipelines/utils/validation.py`
   - Implements 5-stage validation pipeline:
     1. Schema validation (node IDs, types, format)
     2. Index building (preprocessing)
     3. Module validation (catalog, groups, type vars, config)
     4. Edge validation (connections, types, cardinality)
     5. Graph validation (cycles, DAG)
   - Currently all stages are skeletons (pass without validation)
   - **IMPORTANT**: Line 85 has a test exception that was added during debugging - needs removal

3. **API Endpoint** ✅
   - Added POST `/api/pipelines/validate` endpoint in `server-new/src/api/routers/pipelines.py`
   - Converts DTO to domain types
   - Returns single error (not list) when validation fails
   - Non-validation errors bubble up as 500 responses

4. **Service Layer Integration** ✅
   - Updated `PipelineService.validate_pipeline()` in `server-new/src/features/pipelines/service.py`
   - Catches only `PipelineValidationError`, lets other exceptions propagate
   - Returns `{"valid": True}` or `{"valid": False, "error": {...}}`

5. **Frontend Auto-Validation** ✅
   - Created `usePipelineValidation` hook in `client/src/renderer/features/pipelines/hooks/usePipelineValidation.ts`
   - Implements debounced validation (500ms)
   - **FIXED**: Changed from polling to onChange callback pattern
   - Updates `create.tsx` to disable save button when invalid/validating

6. **Fixed Validation Pattern** ✅ (Current Session)
   - **Problem**: Originally implemented polling (checking state every 500ms regardless of changes)
   - **User Request**: Validation should trigger on state changes, but debounced to prevent rapid API calls
   - **Solution**:
     - Added `onChange?: (state: PipelineState) => void` prop to PipelineGraph
     - Added useEffect in PipelineGraph to call onChange when nodes/edges change
     - Removed polling interval from create.tsx
     - PipelineGraph now notifies parent of state changes via callback
     - usePipelineValidation hook receives updated state and debounces validation calls
   - **Result**: Validation triggers on actual changes, debounced to 500ms, no unnecessary polling

### Current Issues

1. **500 Error from Validation Endpoint** ❌
   - Test calls to `/api/pipelines/validate` return 500 Internal Server Error
   - CORS is configured correctly (`allow_origins=["*"]` in `server-new/src/app.py`)
   - Server is running on port 8000
   - Issue is NOT CORS-related despite initial investigation
   - **ROOT CAUSE UNKNOWN** - needs debugging with server logs

2. **Test Exception in Validation** ⚠️
   - `server-new/src/features/pipelines/utils/validation.py` line 85 has:
     ```python
     raise SchemaValidationError("test", "Schema validation not implemented")
     ```
   - This was added during debugging and should be removed
   - Should just be `pass` to skip validation for now

### Files Modified

**Backend:**
- `server-new/src/shared/exceptions/pipeline_validation.py` - NEW (exception classes)
- `server-new/src/features/pipelines/utils/validation.py` - NEW (PipelineValidator)
- `server-new/src/features/pipelines/utils/__init__.py` - Updated (export PipelineValidator)
- `server-new/src/features/pipelines/service.py` - Updated (uses PipelineValidator)
- `server-new/src/api/schemas/pipelines.py` - Updated (validation request/response schemas)
- `server-new/src/api/routers/pipelines.py` - Updated (POST /validate endpoint, fixed error handling)

**Frontend (Previous Session):**
- `client/src/renderer/features/pipelines/hooks/usePipelineValidation.ts` - NEW
- `client/src/renderer/features/pipelines/hooks/usePipelinesApi.ts` - Updated (validatePipeline method)
- `client/src/renderer/features/pipelines/hooks/index.ts` - Updated (export usePipelineValidation)
- `client/src/renderer/features/pipelines/types.ts` - Updated (validation types)
- `client/src/renderer/pages/dashboard/pipelines/create.tsx` - Updated (polling → removed in current session)

**Frontend (Current Session - Fixed Pattern):**
- `client/src/renderer/features/pipelines/components/PipelineGraph.tsx` - Updated (added onChange prop and useEffect)
- `client/src/renderer/pages/dashboard/pipelines/create.tsx` - Updated (removed polling, added onChange callback)

### Key Design Decisions

1. **Fail-Fast Validation**: Each validation stage throws on first error, does not collect multiple errors
2. **Single Error Response**: API returns one error at a time, not a list
3. **onChange Callback Pattern**: PipelineGraph notifies parent of state changes via callback (maintains state ownership in graph)
4. **Debouncing**: Validation calls triggered on state change but debounced by 500ms to avoid rapid API calls during editing
5. **Exception Hierarchy**: `ServiceError (500) → ValidationError (400) → PipelineValidationError → Stage-specific errors`

## Next Steps

### Immediate Priority

1. **Debug 500 Error** 🔴
   - Remove test exception from `validation.py:85`
   - Check server logs for actual error
   - Test validation endpoint with curl:
     ```bash
     curl -X POST http://localhost:8000/api/pipelines/validate \
       -H "Content-Type: application/json" \
       -d '{"pipeline_json":{"entry_points":[],"modules":[],"connections":[]}}'
     ```
   - Expected response: `{"valid": true, "errors": []}`

2. **Test Frontend Integration** 🟡
   - Once backend is working, open pipeline builder in browser
   - Verify auto-validation is working (save button disabled on invalid state)
   - Check browser console for validation errors

3. **Implement Validation Stages** 🟢
   - Schema validation (node ID uniqueness, pin types, module ref format)
   - Module validation (catalog lookups, type checking)
   - Edge validation (connection validity, type compatibility)
   - Graph validation (cycle detection - can reuse `_check_for_cycles` from service.py)

### Implementation Notes

**Validation Skeleton Locations:**
- `_validate_schema()` - Line 71-85 in validation.py
- `_build_indices()` - Line 87-106 (returns empty indices)
- `_validate_modules()` - Line 108-128
- `_validate_edges()` - Line 130-148
- `_validate_graph()` - Line 150-166

**Testing Strategy:**
1. Test with empty pipeline (should pass all validation)
2. Test with single module (should pass if module exists in catalog)
3. Test with invalid connections (should fail edge validation)
4. Test with cycle (should fail graph validation)

## Important Context

### Exception Design Evolution

The exception design went through multiple iterations based on user feedback:

**Iteration 1** (Wrong): Exceptions collected lists of errors
```python
def __init__(self, errors: List[Dict[str, Any]]):
    self.errors = errors
```

**Iteration 2** (Wrong): Still too complex with separate error objects
```python
def __init__(self, errors: List[ValidationErrorDetail]):
    self.errors = errors
```

**Final Design** (Correct): Single error, fail-fast
```python
def __init__(self, message: str, code: str, where: Optional[Dict[str, Any]] = None):
    self.code = code
    self.where = where
    super().__init__(message)
```

### User Preferences

- **No migration scripts ever** - User explicitly stated this
- **Fail-fast validation** - Return first error only
- **500 for non-validation errors** - Don't catch generic exceptions in validation endpoint
- **PipelineGraph owns state** - Parent polls via ref rather than lifting state up

### Related Code Locations

**Module Catalog:**
- Sync CLI: `server-new/src/cli/sync_modules.py`
- Service: `server-new/src/features/modules/service.py`
- API: `server-new/src/api/routers/modules.py`

**Pipeline State Types:**
- Domain: `server-new/src/shared/types/pipelines.py`
- DTO: `server-new/src/api/schemas/pipelines.py`
- Frontend: `client/src/renderer/features/pipelines/types.ts`

## Debugging Checklist

If validation endpoint still returns 500:

1. ✅ Check CORS configuration (already verified correct)
2. ⬜ Remove test exception from validation.py:85
3. ⬜ Check server logs for actual error
4. ⬜ Verify DTO → domain type conversion in convert_dto_to_pipeline_state
5. ⬜ Check PipelineState dataclass imports
6. ⬜ Verify PipelineIndices type definition
7. ⬜ Test with minimal pipeline JSON

## Commands Reference

**Start Backend:**
```bash
cd server-new
python main.py
```

**Test Validation Endpoint:**
```bash
curl -X POST http://localhost:8000/api/pipelines/validate \
  -H "Content-Type: application/json" \
  -d '{"pipeline_json":{"entry_points":[],"modules":[],"connections":[]}}'
```

**Sync Modules to Database:**
```bash
cd server-new
python src/cli/sync_modules.py
```

## Git Status

**Branch**: server_unification
**Modified Files:**
- Backend: 6 files (exceptions, validation, service, schemas, router, __init__)
- Frontend: 5 files (new hook, types, api hook, create page, index)

**Untracked Files:**
- `client-new/src/renderer/routeTree.gen.ts`
- `client-new/src/renderer/src/rendererrouteTree.gen.ts`
- `client-new/src/renderer/src/rerouteTree.gen.ts`
- `client-new/src/renderer/src/renderer/routeTree.gen.ts`

These are auto-generated router files and should likely be gitignored.
