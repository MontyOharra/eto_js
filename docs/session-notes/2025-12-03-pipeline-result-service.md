# Session Notes: 2025-12-03 — PipelineResultService Foundation

## Context

Continuing work on the PipelineResultService design from the previous session. The design document (`docs/pipeline-result-service-design.md`) was created previously, outlining the two-phase pipeline model where Phase 1 (pipeline execution) is pure data transformation and Phase 2 (output execution) handles side effects like order creation and emails.

## Work Completed This Session

### 1. Client-Side Cleanup (Pre-requisite)

Removed old `executed_actions` / `pipeline_actions` references from client code to align with the new `output_module_id` + `output_module_inputs` API structure:

**Files Modified:**
- `client/src/renderer/features/templates/api/types.ts` - Changed `SimulateTemplateResponse` from `pipeline_actions` to `output_module_id` + `output_module_inputs`
- `client/src/renderer/features/templates/components/TemplateBuilder/TestingStep.tsx` - Updated to display output module data
- `client/src/renderer/features/eto/types.ts` - Removed `executed_actions` from `EtoSubRunPipelineExecutionDetail`
- `client/src/renderer/features/eto/components/EtoSubRunDetail/SummarySuccessView.tsx` - Simplified to show success message
- `client/src/renderer/features/eto/components/EtoSubRunDetail/EtoSubRunDetailViewer.tsx` - Removed `executed_actions` prop passing
- `client/src/renderer/features/eto/components/EtoSubRunDetail/DetailPipelineView.tsx` - Removed `executed_actions` fallback
- `client/src/renderer/features/pipelines/api/types.ts` - Changed `ExecutePipelineResponse` to use output module fields

### 2. Server-Side Cleanup

Removed legacy types from server:

**Files Modified:**
- `server/src/shared/types/pipeline_execution.py` - Removed `PipelineExecutionRun`, `PipelineExecutionRunCreate`, `ActionExecutionData`
- `server/src/shared/types/__init__.py` - Removed exports of deleted types

### 3. Database & Domain Types for Output Execution

Updated the output execution table to support the create/update approval flow:

**Files Modified:**
- `server/src/shared/database/models.py`:
  - Updated `ETO_OUTPUT_STATUS` enum: `pending`, `processing`, `awaiting_approval`, `success`, `rejected`, `error`
  - Added `ETO_OUTPUT_ACTION_TYPE` enum: `create`, `update`
  - Added new columns to `EtoSubRunOutputExecutionModel`:
    - `hawb` (VARCHAR) - For easy querying
    - `action_type` - Create or update
    - `existing_order_number` - For updates
    - `existing_order_data_json` - Snapshot for comparison UI

- `server/src/shared/types/eto_sub_run_output_executions.py`:
  - Added `OutputExecutionStatus` and `ActionType` Literal types
  - Updated `EtoSubRunOutputExecutionCreate` to include `hawb`
  - Updated `EtoSubRunOutputExecutionUpdate` with new fields
  - Updated `EtoSubRunOutputExecution` dataclass with all new fields

- `server/src/shared/database/repositories/eto_sub_run_output_execution.py`:
  - Updated `_model_to_domain()` for new fields
  - Updated `create()` to include `hawb`
  - Updated `update()` to handle `existing_order_data` JSON serialization
  - Added `get_awaiting_approval()` method for approval queue

### 4. Exception Class

**Files Created:**
- `server/src/shared/exceptions/output_execution.py` - `OutputExecutionError` exception

**Files Modified:**
- `server/src/shared/exceptions/__init__.py` - Export `OutputExecutionError`

### 5. PipelineResultService Foundation

**Files Created:**
- `server/src/features/pipeline_results/__init__.py`
- `server/src/features/pipeline_results/output_definitions/__init__.py`
- `server/src/features/pipeline_results/output_definitions/base.py` - Abstract base class with:
  - Email template class attributes
  - `create_order(input_data, helpers)` abstract method
  - `update_order(input_data, existing_order_number, helpers)` abstract method
- `server/src/features/pipeline_results/service.py` - `PipelineResultService` with:
  - `register_definition(module_id, definition)` - Register output definitions
  - `check_hawb(hawb)` - Check HAWB existence, returns `{count, existing_order, error}`
  - `create_order(module_id, input_data, source_email)` - Execute creation
  - `update_order(module_id, input_data, existing_order_number, source_email)` - Execute update

## Architecture Clarification

During this session, we clarified the architecture:

1. **`BasicOrderOutput`** in `pipeline_modules/output/` is a **pipeline module** - it only defines inputs and collects data during pipeline execution. Its `run()` method returns empty.

2. **Output Definitions** in `features/pipeline_results/output_definitions/` contain the actual business logic for order creation/update. These are separate from pipeline modules.

3. **PipelineResultService** is a processor service. It:
   - Takes `module_id`, `input_data`, `source_email`
   - Looks up the output definition
   - Calls the definition's `create_order()` or `update_order()`
   - Sends confirmation emails
   - Returns results

4. **EtoRunsService** remains the orchestrator. It:
   - Creates/updates `eto_sub_run_output_executions` records
   - Calls `PipelineResultService` methods
   - Handles the approval state machine
   - Updates ETO database records based on results

## Flow Design

### Create Flow (Immediate)
```
Pipeline completes → EtoRunsService._process_sub_run_output()
    → check_hawb() returns count=0
    → create output_execution record
    → call service.create_order()
    → update record with result
```

### Update Flow (Approval Required)
```
Pipeline completes → EtoRunsService._process_sub_run_output()
    → check_hawb() returns count=1
    → create output_execution record with status=awaiting_approval
    → store existing_order_data for comparison UI
    → return (sub-run stays in processing state)

User approves via API → EtoRunsService.process_approved_update(execution_id)
    → call service.update_order()
    → update record with result
```

## Remaining Work

### Phase 3 (continued):
- [ ] Implement helper classes (OrderHelpers, AddressHelpers, EmailHelpers) - need to resolve circular dependency concerns
- [ ] Implement `BasicOrderDefinition` in `output_definitions/`

### Phase 4:
- [ ] Add `_process_sub_run_output()` to EtoRunsService
- [ ] Add `process_approved_update()` to EtoRunsService

### Phase 5:
- [ ] Create API router for output executions
- [ ] Register router in FastAPI app

## Open Questions

1. **Helper Dependencies**: The helpers need access to the Access database (for orders) and email config. Need to determine best way to inject these without circular dependencies.

2. **ServiceContainer Registration**: How to wire up `PipelineResultService` with its dependencies.

## Files Changed Summary

```
# Client
client/src/renderer/features/templates/api/types.ts
client/src/renderer/features/templates/components/TemplateBuilder/TestingStep.tsx
client/src/renderer/features/eto/types.ts
client/src/renderer/features/eto/components/EtoSubRunDetail/SummarySuccessView.tsx
client/src/renderer/features/eto/components/EtoSubRunDetail/EtoSubRunDetailViewer.tsx
client/src/renderer/features/eto/components/EtoSubRunDetail/DetailPipelineView.tsx
client/src/renderer/features/pipelines/api/types.ts

# Server - Types & Database
server/src/shared/types/pipeline_execution.py
server/src/shared/types/__init__.py
server/src/shared/types/eto_sub_run_output_executions.py
server/src/shared/database/models.py
server/src/shared/database/repositories/eto_sub_run_output_execution.py

# Server - Exceptions
server/src/shared/exceptions/output_execution.py
server/src/shared/exceptions/__init__.py

# Server - New Service (created)
server/src/features/pipeline_results/__init__.py
server/src/features/pipeline_results/service.py
server/src/features/pipeline_results/output_definitions/__init__.py
server/src/features/pipeline_results/output_definitions/base.py
```
