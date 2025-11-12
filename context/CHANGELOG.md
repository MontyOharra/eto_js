# Project Changelog

## [2025-11-11 19:30] — Services Parameter Separation Architecture

### Spec / Intent
- Separate services from execution context for cleaner separation of concerns
- Context should only contain I/O metadata (input/output pins)
- Services should be passed as explicit separate parameter
- Improves code clarity and makes dependencies explicit

### Changes Made
- Files: `shared/types/modules.py`, `shared/types/pipelines.py`, `features/pipeline_execution/service.py`, all 16 modules in `pipeline_modules/`
- Summary:
  - Updated `BaseModule.run()` signature: added `services: Optional[Any] = None` parameter
  - Removed `services` field from `ModuleExecutionContext` dataclass
  - Updated pipeline execution service to pass services separately to `run()`
  - Updated all 16 existing module signatures to accept services parameter
  - Modules using services (lookup_hawb, create_order) now access via `services` param instead of `context.services`

### Technical Details

**Before**:
```python
@dataclass
class ModuleExecutionContext:
    inputs: List[NodeInstance]
    outputs: List[NodeInstance]
    module_instance_id: str
    services: Optional[Any] = None  # ← Services mixed with I/O metadata

def run(self, inputs, cfg, context):
    db = context.services.get_connection('htc_db')  # ← Accessing via context
```

**After**:
```python
@dataclass
class ModuleExecutionContext:
    inputs: List[NodeInstance]  # Only I/O metadata
    outputs: List[NodeInstance]
    module_instance_id: str
    # services field removed

def run(self, inputs, cfg, context, services=None):
    db = services.get_connection('htc_db')  # ← Explicit services parameter
```

### Next Actions
- Implement SQL lookup database dropdown (see context/docs/sql_lookup_database_dropdown.md)
- Decide between dynamic schema generation or API endpoint approach
- Implement SQL lookup execution logic

### Notes
- All existing modules updated with new signature (backward compatible via default parameter)
- No breaking changes to module functionality
- Cleaner separation: context for I/O, services for dependencies

## [2025-11-11 18:45] — SQL Lookup Module (Schema Only)
### Spec / Intent
- Create generic database query module for SQL SELECT lookups
- Schema-only implementation (no execution logic yet)
- Variable input/output pins matched by name to SQL template
- Simple config: SQL text + database dropdown

### Changes Made
- Files: `server/src/pipeline_modules/transform/sql_lookup.py`
- Summary:
  - Created SqlLookup transform module with SqlLookupConfig Pydantic model
  - Variable-count NodeGroups: 0-20 input params, 1-20 output fields
  - Config fields: sql_template, database (env var), on_multiple_rows (error/first/last), on_no_rows (error/null)
  - run() method raises NotImplementedError - execution logic to be added later
  - Module will appear in frontend module selector after server restart + sync

### Design Decisions
- Schema-only for now - no database execution implemented
- Named placeholders {input_name} in SQL template will map to input pin names
- Output pins will map to column names or AS aliases from SELECT clause
- Simple text config instead of complex form builder

### Next Actions
- Restart server to auto-discover module
- Call POST /admin/sync-modules to sync module to database catalog
- Module will then appear in frontend
- Implement execution logic later

### Notes
- Module imports successfully
- Uses project's standard SQLAlchemy approach (not psycopg2)

## [2025-11-11 17:15] — TypeVar Synchronization Bug Fix
### Spec / Intent
- Fix TypeVar fields not updating together when one is changed
- Visual highlighting worked correctly, but only clicked pin updated in state
- All typevar siblings should update together when one changes

### Changes Made
- Files: `client/src/renderer/features/pipelines/utils/typeSystem.ts`
- Summary:
  - Fixed calculateTypePropagation() function (line 335)
  - Moved allUpdates.push(update) before type check
  - Previously, early continue when targetPin.type === update.newType skipped adding updates to allUpdates
  - Since synchronizeTypeVarUpdate already updated enriched state, all typevar siblings had matching types and were skipped
  - Updates still needed to be added to allUpdates to apply to raw state for persistence

### Root Cause Analysis
The bug occurred because:
1. synchronizeTypeVarUpdate correctly updates all typevar siblings in enriched module
2. calculateTypePropagation receives all 3 updates in initialUpdates
3. For each update, it checks if targetPin.type === update.newType
4. Since enriched state already updated, all 3 pins match the new type
5. Code did continue BEFORE pushing to allUpdates, so array stayed empty
6. Empty allUpdates meant raw state never got updated
7. Only the clicked pin was updated via the initial handleNodeTypeUpdate

### Technical Details
- Enriched state has metadata (type_var fields) from template enrichment
- Raw state is what gets persisted to backend
- synchronizeTypeVarUpdate works on enriched module
- calculateTypePropagation works on enriched state for propagation logic
- allUpdates must include updates even when already correct in enriched state
- Final updates applied to raw state via applyTypeUpdates

### Next Actions
- Monitor for any regressions in type propagation
- Consider refactoring to make enriched/raw state distinction clearer

### Notes
- Debug logging was added temporarily, then removed after fix confirmed
- User confirmed fix works: "Ok great that works now with both the front and backend"

## [2025-11-11 16:30] — BranchNotTaken Serialization Bug Fix
### Spec / Intent
- Fix Pydantic serialization error when BranchNotTaken sentinel is returned by if_branch module
- Ensure sentinel values (ExecutionCancelled, BranchNotTaken) are filtered out before serialization
- Maintain proper control flow for conditional branching without breaking pipeline execution

### Changes Made
- Files: `server/src/features/pipeline_execution/service.py`
- Summary:
  - Added sentinel filtering in `_serialize_io_for_audit()` to skip ExecutionCancelled and BranchNotTaken instances
  - Added sentinel filtering in `_serialize_inputs_for_audit()` for consistency
  - Added sentinel filtering in `_convert_to_upstream_named_inputs()` to prevent sentinels in action inputs
  - These sentinels are internal control flow markers and should never be serialized to JSON

### Root Cause Analysis
The bug occurred because:
1. `if_branch` module returns `BranchNotTaken` instances in its output dictionary for non-selected paths
2. These outputs were passed through serialization functions (`_serialize_io_for_audit`, `_serialize_inputs_for_audit`)
3. Pydantic tried to serialize the custom `BranchNotTaken` class instances and failed with: "Unable to serialize unknown type: <class 'features.pipeline_execution.service.BranchNotTaken'>"
4. The sentinel checks existed in `_run_module()` but occurred AFTER serialization had already been attempted

### Technical Details
- Sentinels (ExecutionCancelled, BranchNotTaken) are designed to propagate through the DAG to skip downstream modules
- They should be checked by modules receiving them as inputs (already implemented)
- They should NOT be serialized for audit trails or execution results
- The fix filters them out at serialization time, before Pydantic attempts to convert them to JSON

### Next Actions
- Test the fix with a pipeline containing if_branch modules
- Verify that conditional branching works correctly without serialization errors
- Monitor logs for any remaining issues

### Notes
- Similar pattern exists for ExecutionCancelled sentinel - both now handled consistently
- The if_branch module implementation in `server/src/pipeline_modules/logic/if_branch.py` is correct
- No changes needed to if_branch itself - the issue was in the serialization layer
