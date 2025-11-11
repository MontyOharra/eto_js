# Project Changelog

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
