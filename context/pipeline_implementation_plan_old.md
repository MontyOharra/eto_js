# Pipeline Validation, Compilation & Execution - Implementation Plan

## Document Purpose
This document serves as a step-by-step implementation guide for building the complete pipeline validation, compilation, and execution system. It should be followed sequentially, completing and testing each step before moving to the next.

---

## Instructions for Implementation

### Working Through Steps:
1. **One Step at a Time**: Only work on the current unchecked step
2. **Plan First**: For each step, create a detailed plan and discuss with user before coding
3. **Get Confirmation**: Wait for user approval of the plan before implementing
4. **Build Draft**: Implement the step after plan is approved
5. **Test Thoroughly**: Use the provided test strategy to verify the step works
6. **Debug Together**: Work with user to fix any issues
7. **Check Off**: Only mark step complete after user confirms it works
8. **Move Forward**: Proceed to next step only after current step is checked off

### Communication Style:
- Focus ONLY on the current step being worked on
- Don't reference future steps or ask questions about them yet
- Keep context tight and focused on the task at hand
- Provide clear, testable outputs for each step

---

## Project Context

### Key Design Decisions:
1. **Entry Points**: Always type `str`, no need to store type field
2. **Storage Strategy**: Use `pipeline_steps` table as compiled execution cache
3. **Validation Timing**: Triggers on pipeline_state changes (not visual_state)
4. **Module Kinds**: `transform`, `action`, `logic` (all three are valid)
5. **Action Detection**: Use `ModuleInstance.module_kind` field
6. **Type Variable Validation**: Backend validates type var unification (defense in depth)
7. **Dead Branch Warnings**: Deferred to v2
8. **Debouncing**: Frontend responsibility (~300-500ms after state changes)

### Database Schema (Already Exists):
- `pipeline_definitions`: Stores source pipeline JSON
- `pipeline_steps`: Stores compiled execution steps (one row per module in action-reachable subgraph)
- `module_catalog`: Module templates for validation

### Dependencies Needed:
- `networkx>=3.0` (for graph operations)

---

## Implementation Steps

### Phase 1: Foundation & Validation System

#### ✅ Step 1.1: Project Setup & Dependencies
**Objective**: Set up directory structure and install dependencies

**Tasks**:
- [x] Add `networkx>=3.0` to requirements.txt
- [x] Install dependencies
- [x] Create directory structure:
  ```
  src/features/pipeline/
  ├── validation/
  │   └── __init__.py
  ├── compilation/
  │   └── __init__.py
  └── execution/
      └── __init__.py
  ```

**Testing**:
- ✅ NetworkX 3.5 installed and imports successfully
- ✅ All `__init__.py` files created (empty)
- ✅ Basic NetworkX functionality verified (DAG check works)

**Completed**: 2025-10-03
**Actual Time**: 15 minutes

---

#### ✅ Step 1.2: Error Models & Types
**Objective**: Define validation error codes, error models, and result types

**Tasks**:
- [x] Create `ValidationErrorCode` enum with all error types from spec
- [x] Create `ValidationError` model with code, message, where fields
- [x] Create `ValidationResult` model with valid flag and errors list
- [x] Add comprehensive docstrings

**Files Created**:
- `src/features/pipeline/validation/errors.py`

**Testing**:
- ✅ All 14 error codes instantiate correctly
- ✅ Pydantic validation works on error models
- ✅ JSON serialization works correctly
- ✅ All error codes verified in test

**Completed**: 2025-10-03
**Actual Time**: 30 minutes

---

#### ✅ Step 1.3: Schema Validator
**Objective**: Validate basic schema and presence requirements (§2.1 from spec)

**Tasks**:
- [x] Implement `SchemaValidator` class
- [x] Validate all required fields present in pipeline_state (relies on Pydantic)
- [x] Check node ID global uniqueness across entry points and all pins
- [x] Validate pin types are in allowed set: `["str", "int", "float", "bool", "datetime"]`
- [x] Validate module_ref format (basic check: contains ":")
- [x] Return list of ValidationError objects

**Files Created**:
- `src/features/pipeline/validation/schema_validator.py`

**Testing**:
- ✅ Valid pipeline passes with no errors
- ✅ Duplicate node IDs detected (entry points, within module, cross module, entry-module)
- ✅ Invalid pin types detected
- ✅ Multiple invalid types detected
- ✅ Invalid module ref format detected
- ✅ Multiple different errors detected correctly
- ✅ All valid types accepted

**Completed**: 2025-10-03
**Actual Time**: 1 hour

---


#### ☐ Step 1.4: Index Builder
**Objective**: Build lookup indices for efficient validation (§2.2 from spec)

**Tasks**:
- [ ] Create `IndexBuilder` class or utility functions
- [ ] Build `pin_by_id` index: `Dict[node_id, PinInfo]` where PinInfo includes:
  - `node_id`, `type`, `module_instance_id` (None for entry points), `direction` (in/out/entry)
- [ ] Build `module_by_id` index: `Dict[module_instance_id, ModuleInstance]`
- [ ] Build `input_to_upstream` index: `Dict[input_pin_id, output_pin_id]` from connections
- [ ] Build `output_to_downstreams` index: `Dict[output_pin_id, List[input_pin_id]]`

**Files to Create**:
- `src/features/pipeline/validation/index_builder.py`

**Testing Strategy**:
- Create test pipeline with 2 entry points, 3 modules, 5 connections
- Verify all indices have correct number of entries
- Verify lookup correctness for specific node_ids
- Test edge case: entry point connecting to module (should be in input_to_upstream)
- Test edge case: module with no outputs (should be in module_by_id but not output_to_downstreams)

**Estimated Time**: 1-2 hours

---

#### ☐ Step 1.5: Graph Builder (NetworkX)
**Objective**: Build pin-level and module-level directed graphs (§2.4 from spec)

**Tasks**:
- [ ] Create `GraphBuilder` class
- [ ] Implement `build_pin_graph()`:
  - Add all pin node_ids as nodes (entry points + module pins)
  - Add node attributes: type, module_id, pin_type
  - Add edges from connections (from_node_id -> to_node_id)
  - Return NetworkX DiGraph
- [ ] Implement `build_module_graph()`:
  - Takes reachable_modules set as input
  - Add only reachable modules as nodes
  - Add edge A->B if any output of A connects to any input of B
  - Return NetworkX DiGraph

**Files to Create**:
- `src/features/pipeline/validation/graph_builder.py`

**Testing Strategy**:
- Create test pipeline, build pin graph
- Verify node count matches (entry points + all pins)
- Verify edge count matches connections count
- Test `nx.is_directed_acyclic_graph()` on valid pipeline (should be True)
- Create pipeline with cycle, verify cycle detection works
- Build module graph, verify module count and edges correct
- Test topological sort: `list(nx.topological_sort(module_graph))`

**Estimated Time**: 2-3 hours

---

#### ☐ Step 1.6: Edge Validator
**Objective**: Validate edge cardinality and type matching (§2.3 from spec)

**Tasks**:
- [ ] Create `EdgeValidator` class
- [ ] Validate each input pin has exactly one upstream:
  - 0 upstreams -> MISSING_UPSTREAM error
  - >1 upstreams -> MULTIPLE_UPSTREAMS error
- [ ] Validate type equality: `type(from_pin) == type(to_pin)` for every connection
  - Mismatch -> EDGE_TYPE_MISMATCH error
- [ ] Validate no self-loops: `from_node_id != to_node_id`
  - Self-loop -> SELF_LOOP error
- [ ] Use indices from IndexBuilder for efficient lookups

**Files to Create**:
- `src/features/pipeline/validation/edge_validator.py`

**Testing Strategy**:
- **Valid edges**: All inputs have one upstream, all types match -> no errors
- **Missing upstream**: Input pin not in connections -> MISSING_UPSTREAM error
- **Multiple upstreams**: Two connections to same input -> MULTIPLE_UPSTREAMS error
- **Type mismatch**: Connect str output to int input -> EDGE_TYPE_MISMATCH error
- **Self-loop**: Connection from pin to itself -> SELF_LOOP error
- **Entry point to module**: Entry (str) to module input (str) -> valid

**Estimated Time**: 1-2 hours

---

#### ☐ Step 1.7: Module Validator
**Objective**: Validate module-level invariants (§2.5 from spec)

**Tasks**:
- [ ] Create `ModuleValidator` class
- [ ] For each module instance:
  - [ ] Fetch template from module catalog
  - [ ] Validate group cardinalities:
    - For each NodeGroup in template, count pins with that group_index
    - Verify `min_count <= actual_count <= max_count`
  - [ ] Validate typing rules:
    - For pins with `allowed_types`, verify concrete type is in list
    - For pins with `type_var`, unify within module:
      - First occurrence of type_var binds the type
      - All other pins with same type_var must match
      - Check type is in type_params domain
  - [ ] Validate config against module's config_schema (Pydantic validation)
- [ ] Return list of ValidationError objects

**Files to Create**:
- `src/features/pipeline/validation/module_validator.py`

**Testing Strategy**:
- **Valid module**: Module matches template constraints -> no errors
- **Group cardinality**: Module has too many/few pins in group -> GROUP_CARDINALITY error
- **Type var unification**: Module has type_var T with conflicting types -> TYPEVAR_MISMATCH error
- **Invalid config**: Module config fails Pydantic validation -> INVALID_CONFIG error
- **Module not found**: Reference to non-existent module -> MODULE_NOT_FOUND error
- Test with dynamic group (variable count) vs static group (fixed count)

**Estimated Time**: 3-4 hours

---

#### ☐ Step 1.8: Reachability Analyzer
**Objective**: Compute action-reachable set and validate action presence (§2.6 from spec)

**Tasks**:
- [ ] Create `ReachabilityAnalyzer` class
- [ ] Identify Action modules:
  - Query module catalog for each module_ref
  - Filter where `module_kind == "action"`
- [ ] If no actions found, return NO_ACTIONS error
- [ ] Compute reachable set `R`:
  - Start from all Action module input pins
  - Perform reverse BFS/DFS on pin graph to find all upstream pins
  - Collect owning modules of those pins
- [ ] Return set of reachable module_instance_ids and any errors

**Files to Create**:
- `src/features/pipeline/validation/reachability_analyzer.py`

**Testing Strategy**:
- **No actions**: Pipeline with only transform modules -> NO_ACTIONS error
- **All reachable**: Linear pipeline entry->transform->action -> all modules reachable
- **Dead branch**: Pipeline with branch not leading to action -> only action branch reachable
- **Multiple actions**: Pipeline with 2 actions -> both branches reachable
- **Disconnected action**: Action with no inputs -> action itself reachable, upstreams not
- Verify reverse traversal correctly follows edges backward

**Estimated Time**: 2-3 hours

---

#### ☐ Step 1.9: Main Validator Orchestrator
**Objective**: Coordinate all validation stages and return consolidated result

**Tasks**:
- [ ] Create `PipelineValidator` class
- [ ] Implement `validate(pipeline_state: PipelineState) -> ValidationResult`:
  - [ ] Run schema validation (§2.1)
  - [ ] If errors, return early with ValidationResult
  - [ ] Build indices (§2.2)
  - [ ] Build pin graph (§2.4)
  - [ ] Check for cycles using `nx.is_directed_acyclic_graph()`
  - [ ] If cycle, find cycles using `nx.simple_cycles()`, return CYCLE error
  - [ ] Run edge validation (§2.3)
  - [ ] Run module validation (§2.5)
  - [ ] Run reachability analysis (§2.6)
  - [ ] Collect all errors from all stages
  - [ ] Return ValidationResult with valid=True if no errors
- [ ] Constructor takes ModuleService dependency for template lookup

**Files to Create**:
- `src/features/pipeline/validation/validator.py`

**Testing Strategy**:
- **Fully valid pipeline**: Complete pipeline with entry->transform->action -> valid=True, errors=[]
- **Multiple errors**: Pipeline with several issues -> all errors returned
- **Early exit**: Schema error prevents later stages -> only schema errors returned
- **Complex pipeline**: 10+ modules, multiple branches, multiple actions -> validates correctly
- **Integration test**: Use real module templates from database
- Test error scoping: each error has correct `where` information

**Estimated Time**: 2-3 hours

---

#### ☐ Step 1.10: Validation API Endpoint
**Objective**: Add POST /pipelines/validate endpoint

**Tasks**:
- [ ] Update `src/api/routers/pipelines.py`
- [ ] Add endpoint `POST /pipelines/validate`
- [ ] Accept request body: `{"pipeline_json": {...}}`
- [ ] Parse to PipelineState model
- [ ] Call PipelineValidator.validate()
- [ ] Return ValidationResult as JSON
- [ ] Handle errors gracefully (400 for invalid JSON, 500 for internal errors)

**Files to Update**:
- `src/api/routers/pipelines.py`
- `src/features/pipeline/service.py` (add validate_pipeline method)

**Testing Strategy**:
- **Manual API test**: Use curl or Postman to send validation request
- **Valid pipeline**: Send valid pipeline JSON -> `{"valid": true, "errors": []}`
- **Invalid pipeline**: Send pipeline with errors -> `{"valid": false, "errors": [...]}`
- **Malformed JSON**: Send invalid JSON -> 400 error
- **Missing field**: Send pipeline without required field -> validation error
- Test from frontend: integrate with Create page, verify console logging works
- Verify debouncing works (frontend responsibility, but test it triggers correctly)

**Estimated Time**: 1-2 hours

---

### Phase 2: Compilation System

#### ☐ Step 2.1: Graph Pruner
**Objective**: Prune pipeline to only action-reachable modules (§3.1 from spec)

**Tasks**:
- [ ] Create `GraphPruner` class
- [ ] Implement `prune_to_action_reachable()`:
  - [ ] Take PipelineState and reachable_modules set (from validation)
  - [ ] Filter modules to only those in reachable set
  - [ ] Filter connections to only those between reachable modules
  - [ ] Keep all entry points (they're always reachable if any module uses them)
  - [ ] Return pruned PipelineState
- [ ] Maintain all pin information for pruned modules

**Files to Create**:
- `src/features/pipeline/compilation/graph_pruner.py`

**Testing Strategy**:
- **No pruning needed**: All modules reachable -> pruned = original
- **Dead branch removed**: Pipeline with dead branch -> pruned excludes dead modules
- **Connections pruned**: Dead branch connections removed from pruned graph
- **Entry points preserved**: Unused entry points kept (or removed if truly unused)
- **Complex graph**: Multi-branch pipeline -> only action-reaching branches kept
- Verify pruned graph still valid (can build NetworkX graph from it)

**Estimated Time**: 1-2 hours

---

#### ☐ Step 2.2: Topological Sorter
**Objective**: Compute topological layers for parallel execution (§3.2 from spec)

**Tasks**:
- [ ] Create `TopologicalSorter` class
- [ ] Implement `compute_layers()`:
  - [ ] Build module-level graph from pruned pipeline
  - [ ] Use `nx.topological_generations()` to get layers
  - [ ] Return list of lists: `[[layer0_modules], [layer1_modules], ...]`
  - [ ] Layer 0 = modules with no dependencies (only entry points as inputs)
  - [ ] Each subsequent layer depends only on previous layers
- [ ] Handle edge case: isolated action with no inputs

**Files to Create**:
- `src/features/pipeline/compilation/topological_sorter.py`

**Testing Strategy**:
- **Linear pipeline**: entry->A->B->C -> layers = [[A], [B], [C]]
- **Parallel branches**: entry->A,B->C -> layers = [[A,B], [C]]
- **Diamond pattern**: entry->A,B->C->D (A,B independent) -> verify correct layering
- **Multiple entry points**: 2 entries feeding different modules -> verify layer 0 correct
- **Complex DAG**: 10 modules with various dependencies -> verify all layers correct
- Verify no module appears in multiple layers
- Verify execution order respects dependencies

**Estimated Time**: 1-2 hours

---

#### ☐ Step 2.3: Checksum Calculator
**Objective**: Compute stable plan checksum for cache validation (§3.4 from spec)

**Tasks**:
- [ ] Create `ChecksumCalculator` class
- [ ] Implement `compute_plan_checksum()`:
  - [ ] Create normalized representation of pruned pipeline:
    - Sorted list of modules (by module_instance_id)
    - For each module: module_ref, module_kind, config, sorted inputs/outputs
    - Sorted list of connections
    - Computed layer assignments
  - [ ] Serialize to stable JSON (sorted keys, no whitespace)
  - [ ] Compute SHA-256 hash
  - [ ] Return hex digest string
- [ ] Ensure checksum is deterministic (same pipeline = same checksum)

**Files to Create**:
- `src/features/pipeline/compilation/checksum.py`

**Testing Strategy**:
- **Determinism**: Compute checksum twice for same pipeline -> identical
- **Visual changes ignored**: Change visual_json only -> checksum unchanged
- **Config change detected**: Change module config -> checksum changes
- **Connection change detected**: Add/remove connection -> checksum changes
- **Module rename**: Change module_instance_id -> checksum changes (expected)
- **Type change**: Change pin type -> checksum changes
- Test with multiple pipelines, verify uniqueness

**Estimated Time**: 1-2 hours

---

#### ☐ Step 2.4: Main Compiler
**Objective**: Orchestrate compilation to PipelineStepModel instances (§3 from spec)

**Tasks**:
- [ ] Create `PipelineCompiler` class
- [ ] Implement `compile()` method:
  - [ ] Take pipeline_id and validated PipelineState
  - [ ] Run validation to get reachable_modules set
  - [ ] Prune to action-reachable subgraph
  - [ ] Compute topological layers
  - [ ] For each module in each layer:
    - [ ] Build input_field_mappings: `{input_pin_id: upstream_output_pin_id}`
    - [ ] Build output_display_names: `{output_pin_id: user_name}`
    - [ ] Create PipelineStepModel instance with:
      - pipeline_id, module_instance_id, module_ref, module_kind
      - module_config (JSON), input_field_mappings (JSON)
      - output_display_names (JSON), step_number
  - [ ] Compute plan_checksum
  - [ ] Set plan_checksum on all steps
  - [ ] Return (List[PipelineStepModel], checksum)
- [ ] Handle entry points in input mappings

**Files to Create**:
- `src/features/pipeline/compilation/compiler.py`

**Testing Strategy**:
- **Simple pipeline**: entry->transform->action -> 2 steps (step 0, step 1)
- **Parallel modules**: entry->A,B->action -> A,B both step 0, action step 1
- **Input mappings**: Verify each step's input_field_mappings correct
- **Entry point mapping**: Module fed by entry point -> input maps to entry node_id
- **Output names**: Verify output_display_names contains all output pins
- **Checksum**: Verify all steps have same checksum
- **No steps for dead branch**: Dead modules not in step list
- Complex pipeline: 5+ modules -> verify step count and ordering

**Estimated Time**: 3-4 hours

---

#### ☐ Step 2.5: Persist Compiled Steps to Database
**Objective**: Save compiled steps to pipeline_steps table

**Tasks**:
- [ ] Update `PipelineRepository` class
- [ ] Add method `save_pipeline_steps(steps: List[PipelineStepModel])`:
  - [ ] Delete existing steps for same pipeline_id + old plan_checksum (optional: keep history)
  - [ ] Insert new steps in bulk
  - [ ] Use transaction for atomicity
- [ ] Add method `get_pipeline_steps(pipeline_id: str, plan_checksum: Optional[str])`:
  - [ ] If checksum provided, filter by it
  - [ ] Else, get latest checksum from pipeline_definitions and use that
  - [ ] Order by step_number ASC, id ASC
  - [ ] Return list of PipelineStepModel

**Files to Update**:
- `src/shared/database/repositories/pipeline.py`

**Testing Strategy**:
- **Insert steps**: Compile pipeline, save steps -> verify rows in database
- **Query steps back**: Retrieve steps -> verify correct count and order
- **Checksum filtering**: Save 2 versions with different checksums -> query each correctly
- **Step ordering**: Verify steps returned in correct execution order
- **Bulk insert**: Large pipeline (20 steps) -> all inserted correctly
- **Transaction rollback**: Simulate error during insert -> no partial data
- Integration: Compile -> save -> retrieve -> verify data integrity

**Estimated Time**: 2-3 hours

---

#### ☐ Step 2.6: Update Pipeline Create Endpoint
**Objective**: Integrate validation + compilation into POST /pipelines

**Tasks**:
- [ ] Update `POST /pipelines` endpoint in `src/api/routers/pipelines.py`
- [ ] Flow:
  - [ ] Parse PipelineCreate request
  - [ ] Extract pipeline_json from request
  - [ ] Run full validation (re-validate even if FE validated)
  - [ ] If validation fails, return 400 with errors
  - [ ] If valid, compile to steps
  - [ ] Save pipeline to pipeline_definitions
  - [ ] Save compiled steps to pipeline_steps
  - [ ] Update pipeline_definitions with plan_checksum and compiled_at
  - [ ] Return created Pipeline with compilation metadata
- [ ] Add compilation metadata to response:
  - `layers`: number of execution layers
  - `modules`: number of modules in compiled plan
  - `actions`: number of action modules

**Files to Update**:
- `src/api/routers/pipelines.py`
- `src/features/pipeline/service.py`

**Testing Strategy**:
- **Valid pipeline**: Create pipeline -> verify saved with compiled steps
- **Invalid pipeline**: Send invalid pipeline -> 400 error with validation errors
- **Checksum stored**: Verify plan_checksum saved to pipeline_definitions
- **Compiled_at timestamp**: Verify compiled_at set correctly
- **Steps saved**: Query pipeline_steps table -> verify all steps present
- **Response metadata**: Verify response includes layers, modules, actions counts
- **Idempotence**: Create same pipeline twice -> different IDs but same checksum
- End-to-end: Create via API -> retrieve via API -> verify complete data

**Estimated Time**: 2-3 hours

---

### Phase 3: Execution System

#### ☐ Step 3.1: Execution Context
**Objective**: Create execution context for runtime state management

**Tasks**:
- [ ] Create `ExecutionContext` class in `src/features/pipeline/execution/context.py`
- [ ] Fields:
  - [ ] `values: Dict[node_id, Any]` - runtime value store
  - [ ] `execution_id: str` - UUID for this execution
  - [ ] `started_at: datetime` - execution start time
  - [ ] `module_instance_id: Optional[str]` - currently executing module
  - [ ] `output_pins: List[str]` - expected output node_ids (for dynamic outputs)
- [ ] Methods:
  - [ ] `__init__(entry_values: Dict[str, Any])` - initialize with entry point values
  - [ ] `get_value(node_id: str) -> Any` - retrieve value from store
  - [ ] `set_values(outputs: Dict[str, Any])` - store module outputs
  - [ ] `set_current_module(module_id: str, output_pins: List[str])` - set context for module execution
  - [ ] `get_current_time() -> datetime` - utility for timestamps

**Files to Create**:
- `src/features/pipeline/execution/context.py`

**Testing Strategy**:
- **Initialization**: Create context with entry values -> values dict populated
- **Get value**: Store value, retrieve it -> correct value returned
- **Set values**: Set multiple outputs -> all stored correctly
- **Module context**: Set current module -> accessible in context
- **Execution ID**: Verify UUID generated and stored
- **Missing value**: Try to get non-existent value -> appropriate error

**Estimated Time**: 1 hour

---

#### ☐ Step 3.2: Module Resolver
**Objective**: Resolve module_ref to handler instance

**Tasks**:
- [ ] Create `ModuleResolver` class in `src/features/pipeline/execution/module_resolver.py`
- [ ] Use existing ModuleRegistry to look up handlers
- [ ] Implement `resolve_handler(module_ref: str) -> CommonCore`:
  - [ ] Parse module_ref: "module_id:version"
  - [ ] Look up in module registry
  - [ ] Instantiate handler class
  - [ ] Return handler instance
  - [ ] Raise clear error if not found

**Files to Create**:
- `src/features/pipeline/execution/module_resolver.py`

**Testing Strategy**:
- **Valid module**: Resolve existing module -> handler instance returned
- **Invalid module**: Resolve non-existent module -> clear error
- **Version mismatch**: Resolve wrong version -> error with version info
- **Handler instantiation**: Verify handler is proper instance of CommonCore
- **Multiple resolves**: Resolve same module twice -> verify caching if implemented
- Integration: Resolve all modules used in test pipelines

**Estimated Time**: 1-2 hours

---

#### ☐ Step 3.3: Main Executor
**Objective**: Execute pipelines using compiled steps (§4 from spec)

**Tasks**:
- [ ] Create `PipelineExecutor` class in `src/features/pipeline/execution/executor.py`
- [ ] Implement `execute(pipeline_id: str, entry_values: Dict[str, Any])`:
  - [ ] Load compiled steps from database (ordered by step_number)
  - [ ] Validate entry_values (check all required entry points provided)
  - [ ] Initialize ExecutionContext with entry values
  - [ ] Group steps by step_number (layers)
  - [ ] For each layer (sequentially):
    - [ ] For each step in layer (sequentially for v1):
      - [ ] Resolve handler from module_ref
      - [ ] Build inputs dict from input_field_mappings and context.values
      - [ ] Parse module_config JSON
      - [ ] Set current module in context (with output_pins)
      - [ ] Call `handler.run(inputs, config, context)`
      - [ ] Store outputs in context.values
      - [ ] If module_kind == "action", collect result for report
      - [ ] If error, fail-fast and return error report
  - [ ] Return execution report with status, actions, errors, timing
- [ ] Handle errors gracefully with proper error scoping

**Files to Create**:
- `src/features/pipeline/execution/executor.py`

**Testing Strategy**:
- **Simple execution**: entry->transform->action -> verify action executes, result returned
- **Data flow**: Verify data flows correctly through pipeline (check intermediate values)
- **Action results**: Verify action results collected in report
- **Missing entry value**: Don't provide required entry -> error before execution
- **Runtime error**: Module throws error -> fail-fast with error in report
- **Multiple layers**: Pipeline with 3 layers -> executes in correct order
- **Parallel layer**: Two independent modules in same layer -> both execute
- **Execution report**: Verify report has status, actions, errors, timestamps
- **Context passing**: Verify context passed to handlers correctly
- End-to-end: Create pipeline, compile, execute -> verify complete flow

**Estimated Time**: 4-5 hours

---

#### ☐ Step 3.4: Execution API Endpoint
**Objective**: Add POST /pipelines/{pipeline_id}/run endpoint

**Tasks**:
- [ ] Add endpoint `POST /pipelines/{pipeline_id}/run` in `src/api/routers/pipelines.py`
- [ ] Accept request body: `{"entry_values": {"entry_node_id": "value", ...}}`
- [ ] Call PipelineExecutor.execute()
- [ ] Return execution report as JSON
- [ ] Handle errors:
  - [ ] 404 if pipeline not found
  - [ ] 400 if entry_values invalid
  - [ ] 500 for internal errors
  - [ ] 200 with status="failed" for runtime errors

**Files to Update**:
- `src/api/routers/pipelines.py`
- `src/features/pipeline/service.py` (add execute_pipeline method)

**Testing Strategy**:
- **Successful execution**: Send valid entry values -> status="success", actions populated
- **Failed execution**: Trigger runtime error -> status="failed", error in report
- **Missing entry value**: Omit required entry -> 400 error
- **Pipeline not found**: Execute non-existent pipeline -> 404 error
- **Invalid pipeline_id**: Malformed ID -> 404 error
- **Multiple actions**: Pipeline with 2 actions -> both in actions array
- **Execution timing**: Verify started_at and completed_at timestamps
- **Large payload**: Execute with large entry values -> handles correctly
- End-to-end integration: Create, compile, execute from API -> full flow works

**Estimated Time**: 2-3 hours

---

### Phase 4: Integration & Testing

#### ☐ Step 4.1: End-to-End Integration Tests
**Objective**: Verify complete pipeline flow from creation to execution

**Tasks**:
- [ ] Create integration test file
- [ ] Test scenario 1: Simple linear pipeline
  - Create pipeline (entry->cleaner->action)
  - Verify validation passes
  - Verify compilation creates correct steps
  - Execute with test data
  - Verify action executes and results correct
- [ ] Test scenario 2: Parallel branches
  - Pipeline with diamond pattern
  - Verify topological layers correct
  - Execute and verify both branches process
- [ ] Test scenario 3: Complex multi-action pipeline
  - Multiple actions in different layers
  - Verify all actions execute
  - Verify execution order correct
- [ ] Test scenario 4: Error handling
  - Invalid pipeline -> validation fails
  - Runtime error -> execution fails gracefully
  - Missing entry value -> execution fails with clear error

**Files to Create**:
- `tests/integration/test_pipeline_e2e.py`

**Testing Strategy**:
- Run all integration tests
- Verify no database corruption
- Verify proper cleanup between tests
- Test with real module implementations
- Verify error messages are helpful
- Test performance with larger pipelines (50+ modules)

**Estimated Time**: 4-6 hours

---

#### ☐ Step 4.2: Frontend Integration
**Objective**: Connect frontend validation and execution to new backend

**Tasks**:
- [ ] Update Create page to call `/pipelines/validate` endpoint
- [ ] Debounce validation calls (300-500ms after pipeline_state changes)
- [ ] Display validation errors in console
- [ ] Disable "Create Pipeline" button when validation fails
- [ ] Update pipeline creation flow to handle new response format
- [ ] Add execution UI (if not already exists)
- [ ] Test end-to-end from UI

**Files to Update**:
- `client/src/renderer/routes/transformation_pipeline/create.tsx`
- Create validation hook if needed

**Testing Strategy**:
- **Manual testing**: Build pipeline in UI, verify validation triggers
- **Invalid pipeline**: Create invalid connections, verify errors shown
- **Create pipeline**: Build valid pipeline, click Create, verify success
- **Execute pipeline**: Execute created pipeline, verify results displayed
- **Debouncing**: Rapidly edit pipeline, verify validation doesn't spam
- **Error display**: Trigger each error type, verify message is helpful

**Estimated Time**: 3-4 hours

---

#### ☐ Step 4.3: Documentation & Cleanup
**Objective**: Document the system and clean up code

**Tasks**:
- [ ] Add docstrings to all classes and methods
- [ ] Create API documentation for new endpoints
- [ ] Update CHANGELOG.md with implementation details
- [ ] Add inline comments for complex logic
- [ ] Code cleanup: remove dead code, fix TODOs
- [ ] Update type hints for clarity
- [ ] Create developer documentation for extending system

**Files to Update**:
- All implementation files
- `context/CHANGELOG.md`
- Create `context/docs/pipeline_execution_developer_guide.md`

**Testing Strategy**:
- Verify all docstrings present and accurate
- Run type checker (mypy) if available
- Review code for clarity and consistency
- Verify documentation matches implementation

**Estimated Time**: 2-3 hours

---

## Progress Tracking

**Current Step**: Step 1.4 (Index Builder)

**Completed Steps**:
- ✅ Step 1.1: Project Setup & Dependencies (2025-10-03)
- ✅ Step 1.2: Error Models & Types (2025-10-03)
- ✅ Step 1.3: Schema Validator (2025-10-03)

**Next Step After Current**: Step 1.5 (Graph Builder - NetworkX)

---

## Notes & Decisions Log

### Context Object Contents (Question 7):
**Decision Pending**: Need to finalize what goes in execution context:
- ✅ module_instance_id (for error reporting)
- ✅ execution_id (UUID for this run)
- ✅ output_pins (list of expected output node_ids for dynamic outputs)
- ✅ values dict (for accessing computed values if needed)
- ❓ Anything else needed?

### NetworkX Installation:
**Decision Pending**: Install now or wait for Step 1.1?

---

## Total Estimated Time
- **Phase 1 (Validation)**: 20-25 hours
- **Phase 2 (Compilation)**: 13-18 hours
- **Phase 3 (Execution)**: 8-11 hours
- **Phase 4 (Integration)**: 9-13 hours
- **Total**: 50-67 hours (approximately 1.5-2 weeks of focused development)

---

## Success Criteria
- [ ] All validation error types detectable and reported correctly
- [ ] Pipelines compile to correct execution steps
- [ ] Steps execute in correct topological order
- [ ] Action modules execute and return results
- [ ] Errors handled gracefully with helpful messages
- [ ] Frontend integration complete and working
- [ ] End-to-end tests pass
- [ ] Documentation complete
