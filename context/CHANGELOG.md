# Project Changelog

## [2025-11-11 18:45] — SQL Lookup Module Implementation
### Spec / Intent
- Create generic database query module for SQL SELECT lookups
- Support named placeholders {input_name} for query parameters
- Support AS keyword for column aliases in SELECT clause
- Variable input/output pins matched by name to SQL template
- Simple config: SQL text + database dropdown (no fancy UI)
- Return single row with configurable handling of multiple/zero results

### Changes Made
- Files: `server/src/pipeline_modules/transform/sql_lookup.py`
- Summary:
  - Created SqlLookup transform module with SqlLookupConfig Pydantic model
  - Variable-count NodeGroups: 0-20 input params, 1-20 output fields
  - Config fields: sql_template, database (env var), on_multiple_rows (error/first/last), on_no_rows (error/null)
  - validate_wiring() parses SQL template to extract {placeholders} and SELECT columns, validates pin names match
  - run() method gets connection from env, parameterizes SQL (converts {name} to $1, $2), executes with psycopg2
  - Helper methods: _parameterize_sql() for PostgreSQL parameterized queries, _parse_select_columns() for AS keyword support
  - Uses RealDictCursor for column name access in results

### Design Decisions
- Named placeholders match pin names (self-documenting queries)
- Parameterized queries prevent SQL injection
- AS keyword allows renaming columns: SELECT customer_name AS cust
- Simple text config instead of complex form builder
- Database selection via env var names (e.g., DATABASE_ETO)

### Next Actions
- Test sql_lookup module with sample database connection
- Verify pin name matching in validate_wiring()
- Test AS keyword support
- Test error handling (multiple rows, no rows)
- Verify frontend integration

### Notes
- Module uses PostgreSQL psycopg2 driver
- Could be extended to support other databases in future
- Error messages show available columns when mismatch occurs

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
