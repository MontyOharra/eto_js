# Pipeline Validation, Compilation & Execution - Implementation Plan (REVISED)

## Document Purpose
This document serves as a step-by-step implementation guide for building the complete pipeline validation, compilation, and execution system. It should be followed sequentially, completing and testing each step before moving to the next.

**REVISION NOTE**: This plan has been restructured to enable end-to-end testing as we build. We now build the API infrastructure first, then incrementally add validation rules one at a time, testing the full stack after each addition.

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
9. **End-to-End Testing**: Build API infrastructure first, add validation rules incrementally

### Database Schema (Already Exists):
- `pipeline_definitions`: Stores source pipeline JSON
- `pipeline_steps`: Stores compiled execution steps (one row per module in action-reachable subgraph)
- `module_catalog`: Module templates for validation

### Dependencies:
- ✅ `networkx>=3.0` (installed)

---

## Implementation Steps

### Phase 1: Foundation (COMPLETED ✅)

#### ✅ Step 1.1: Project Setup & Dependencies
**Completed**: 2025-10-03 | **Time**: 15 minutes

- [x] Add `networkx>=3.0` to requirements.txt
- [x] Install dependencies
- [x] Create directory structure

---

#### ✅ Step 1.2: Error Models & Types
**Completed**: 2025-10-03 | **Time**: 30 minutes

- [x] Create `ValidationErrorCode` enum with all error types
- [x] Create `ValidationError` model
- [x] Create `ValidationResult` model

**Files Created**: `src/features/pipeline/validation/errors.py`

---

#### ✅ Step 1.3: Schema Validator
**Completed**: 2025-10-03 | **Time**: 1 hour

- [x] Implement `SchemaValidator` class
- [x] Check node ID global uniqueness
- [x] Validate pin types
- [x] Validate module_ref format

**Files Created**: `src/features/pipeline/validation/schema_validator.py`

---

#### ✅ Step 1.4: Index Builder
**Completed**: 2025-10-03 | **Time**: 1 hour

- [x] Create `PinInfo` Pydantic model
- [x] Create `PipelineIndices` class
- [x] Build all four indices (pin_by_id, module_by_id, input_to_upstream, output_to_downstreams)

**Files Created**: `src/features/pipeline/validation/index_builder.py`

---

### Phase 2: API Infrastructure & Incremental Validation

#### ✅ Step 2.1: Validation Orchestrator (Minimal)
**Completed**: 2025-10-03 | **Time**: 45 minutes

- [x] Create `PipelineValidator` class in `src/features/pipeline/validation/validator.py`
- [x] Constructor accepts dependencies (will need ModuleService later)
- [x] Implement `validate(pipeline_state: PipelineState) -> ValidationResult`:
  - [x] Run SchemaValidator
  - [x] Build PipelineIndices (for later use)
  - [x] Return ValidationResult
- [x] Design to easily add more validation stages later

**Files Created**:
- `src/features/pipeline/validation/validator.py`
- `test_validator_step_2_1.py` (7 comprehensive tests, all passing)

---

#### ✅ Step 2.2: Validation Service Method
**Completed**: 2025-10-03 | **Time**: 30 minutes

- [x] Update `src/features/pipeline/service.py`
- [x] Add `validate_pipeline(pipeline_state: PipelineState) -> ValidationResult`:
  - [x] Create PipelineValidator instance
  - [x] Call validator.validate()
  - [x] Return ValidationResult
- [x] Handle any errors gracefully

**Files Updated**:
- `src/features/pipeline/service.py`
- `test_service_step_2_2.py` (4 tests, all passing)

---

#### ✅ Step 2.3: Validation API Endpoint
**Completed**: 2025-10-03 | **Time**: 1 hour

- [x] Update `src/api/routers/pipelines.py`
- [x] Add endpoint `POST /pipelines/validate`
- [x] Accept request body: `{"pipeline_json": <PipelineState>}`
- [x] Parse pipeline_json to PipelineState model
- [x] Call pipeline_service.validate_pipeline()
- [x] Return ValidationResult as JSON: `{"valid": bool, "errors": [...]}`
- [x] Handle errors:
  - 400 for invalid JSON/Pydantic validation errors
  - 500 for internal errors
- [x] Add "Validate Pipeline" button to frontend Create page

**Files Updated**:
- `src/api/routers/pipelines.py` - Added POST /pipelines/validate endpoint
- `client/src/renderer/routes/transformation_pipeline/create.tsx` - Added validation button and handler

**Frontend Integration**:
- Purple "Validate Pipeline" button next to "Save Pipeline"
- Calls validation API with current pipeline state
- Logs validation result to console with formatted output

**MILESTONE**: 🎉 Working validation API endpoint with basic schema validation!

---

#### ✅ Step 2.4: Add Graph Builder + Cycle Detection
**Completed**: 2025-10-03 | **Time**: 2 hours

- [x] Create `GraphBuilder` class in `src/features/pipeline/validation/graph_builder.py`
- [x] Implement `build_pin_graph(pipeline_state, indices) -> nx.DiGraph`:
  - [x] Add all pin node_ids as nodes with attributes
  - [x] Add edges from connections
  - [x] Add internal module edges (inputs -> outputs within modules)
- [x] Update `PipelineValidator`:
  - [x] After building indices, build pin graph
  - [x] Check `nx.is_directed_acyclic_graph(pin_graph)`
  - [x] If cycle detected, use `nx.simple_cycles()` to find cycles
  - [x] Return CYCLE error if found

**Files Created**:
- `src/features/pipeline/validation/graph_builder.py`

**Files Updated**:
- `src/features/pipeline/validation/validator.py`

**Key Implementation Details**:
- Graph includes both explicit connections AND internal module edges (input pins -> output pins)
- This represents complete data flow including module processing
- Cycle detection uses NetworkX's `is_directed_acyclic_graph()` and `simple_cycles()`
- Errors include full cycle path and cycle length for debugging

**Tests (All Passing)**:
1. Valid DAG with no cycles passes
2. Simple cycle A->B->A detected
3. Self-loop detected as cycle
4. Complex multi-node cycles detected
5. Branching DAG with fan-out is valid

---

#### ✅ Step 2.5: Add Edge Validator
**Completed**: 2025-10-03 | **Time**: 1.5 hours

- [x] Create `EdgeValidator` class in `src/features/pipeline/validation/edge_validator.py`
- [x] Implement `validate(pipeline_state, indices) -> List[ValidationError]`:
  - [x] Check each input has exactly one upstream (use indices.input_to_upstream)
  - [x] Check type equality for all connections (use indices.pin_by_id)
  - [x] Check no self-loops
- [x] Update `PipelineValidator` to run EdgeValidator after graph validation

**Files Created**:
- `src/features/pipeline/validation/edge_validator.py`

**Files Updated**:
- `src/features/pipeline/validation/validator.py`

**Key Implementation Details**:
- Validates input pin cardinality (exactly one upstream)
- Checks for multiple upstreams (shouldn't happen but validated for safety)
- Ensures type matching between connected pins
- Detects self-loops (pin connecting to itself)
- Provides detailed error messages with pin names and types

**Tests (All Passing)**:
1. Valid connections with proper types pass
2. Missing upstream connection detected
3. Type mismatch (str->int) detected
4. Self-loop detected
5. Multiple type errors all reported
6. Partial connections detected
7. Complex multi-module pipeline validates correctly

---

#### ✅ Step 2.6: Add Module Validator
**Completed**: 2025-10-03 | **Time**: 3 hours

- [x] Create `ModuleValidator` class in `src/features/pipeline/validation/module_validator.py`
- [x] Constructor accepts ModuleCatalogRepository for template lookup
- [x] Implement `validate(pipeline_state, indices) -> List[ValidationError]`:
  - [x] For each module, fetch template from catalog
  - [x] Validate group cardinalities (min/max pin counts)
  - [x] Validate type variable unification
  - [x] Validate config against schema (required fields)
- [x] Update `PipelineValidator`:
  - [x] Pass ModuleCatalogRepository dependency through
  - [x] Run ModuleValidator after edge validation

**Files Created**:
- `src/features/pipeline/validation/module_validator.py`

**Files Updated**:
- `src/features/pipeline/validation/validator.py`
- `src/features/pipeline/service.py`

**Key Implementation Details**:
- Fetches module templates from catalog using module_ref (id:version)
- Validates pin group cardinalities against IOShape constraints
- Checks type variable unification (e.g., type var T must resolve to single type)
- Validates required config fields from JSON Schema
- Provides detailed error messages with group labels and counts

**Tests (All Passing)**:
1. Valid module with correct cardinality passes
2. Module not found in catalog detected
3. Too few pins in group detected
4. Too many pins in group detected
5. Type variable unification errors detected
6. Missing required config fields detected

---

#### ✅ Step 2.7: Add Reachability Analyzer
**Completed**: 2025-10-03 | **Time**: 2 hours

- [x] Create `ReachabilityAnalyzer` class in `src/features/pipeline/validation/reachability_analyzer.py`
- [x] Implement `analyze(pipeline_state, indices, pin_graph) -> Tuple[Set[str], List[ValidationError]]`:
  - [x] Identify action modules (from module_kind field)
  - [x] If no actions, return NO_ACTIONS error
  - [x] Reverse BFS from action inputs to find reachable modules
  - [x] Return (set of reachable module IDs, errors)
- [x] Update `PipelineValidator`:
  - [x] Run ReachabilityAnalyzer after all other validation
  - [x] Store reachable_modules set (will be used by compiler later)

**Files Created**:
- `src/features/pipeline/validation/reachability_analyzer.py`

**Files Updated**:
- `src/features/pipeline/validation/validator.py`

**Key Implementation Details**:
- Uses reverse BFS from action module inputs
- Traverses backward through pin graph to find all upstream modules
- Dead branches (unreachable from actions) are identified but not errors
- Stores reachable module set for compilation optimization

**Tests (All Passing)**:
1. Pipeline with no actions returns NO_ACTIONS error
2. Pipeline with action is valid, modules are reachable
3. Dead branch correctly identified as unreachable
4. Multiple action branches all marked as reachable
5. Complex pipeline with chain correctly analyzed

**MILESTONE**: 🎉 Complete validation system working end-to-end via API!

---

### Phase 3: Compilation System

#### ☐ Step 3.1: Graph Pruner
**Objective**: Prune pipeline to action-reachable modules only

**Tasks**:
- [ ] Create `GraphPruner` class
- [ ] Implement pruning logic using reachable_modules set
- [ ] Return pruned PipelineState

**Files to Create**:
- `src/features/pipeline/compilation/graph_pruner.py`

**Estimated Time**: 1-2 hours

---

#### ☐ Step 3.2: Topological Sorter
**Objective**: Compute execution layers using NetworkX

**Tasks**:
- [ ] Create `TopologicalSorter` class
- [ ] Use `nx.topological_generations()` to compute layers
- [ ] Return list of module ID lists per layer

**Files to Create**:
- `src/features/pipeline/compilation/topological_sorter.py`

**Estimated Time**: 1-2 hours

---

#### ☐ Step 3.3: Checksum Calculator
**Objective**: Compute stable SHA-256 checksum of compiled plan

**Tasks**:
- [ ] Create `ChecksumCalculator` class
- [ ] Normalize pipeline data and compute hash

**Files to Create**:
- `src/features/pipeline/compilation/checksum.py`

**Estimated Time**: 1-2 hours

---

#### ☐ Step 3.4: Pipeline Compiler
**Objective**: Orchestrate compilation to PipelineStepModel instances

**Tasks**:
- [ ] Create `PipelineCompiler` class
- [ ] Compile pipeline to list of PipelineStepModel
- [ ] Return steps + checksum

**Files to Create**:
- `src/features/pipeline/compilation/compiler.py`

**Estimated Time**: 3-4 hours

---

#### ☐ Step 3.5: Persist Compiled Steps
**Objective**: Save steps to pipeline_steps table

**Tasks**:
- [ ] Add `save_pipeline_steps()` to PipelineRepository
- [ ] Add `get_pipeline_steps()` to PipelineRepository
- [ ] Handle transactions properly

**Files to Update**:
- `src/shared/database/repositories/pipeline.py`

**Estimated Time**: 2-3 hours

---

#### ☐ Step 3.6: Update Create Pipeline Endpoint
**Objective**: Integrate validation + compilation into POST /pipelines

**Tasks**:
- [ ] Update POST /pipelines to validate + compile + save
- [ ] Return compilation metadata in response

**Files to Update**:
- `src/api/routers/pipelines.py`
- `src/features/pipeline/service.py`

**Estimated Time**: 2-3 hours

**MILESTONE**: 🎉 Pipelines can be created with compiled execution plan!

---

### Phase 4: Execution System

#### ☐ Step 4.1: Execution Context
**Objective**: Create runtime context for execution

**Tasks**:
- [ ] Create `ExecutionContext` class
- [ ] Manage value store, execution metadata

**Files to Create**:
- `src/features/pipeline/execution/context.py`

**Estimated Time**: 1 hour

---

#### ☐ Step 4.2: Module Resolver
**Objective**: Resolve module_ref to handler instance

**Tasks**:
- [ ] Create `ModuleResolver` class
- [ ] Use ModuleRegistry to get handlers

**Files to Create**:
- `src/features/pipeline/execution/module_resolver.py`

**Estimated Time**: 1-2 hours

---

#### ☐ Step 4.3: Pipeline Executor
**Objective**: Execute pipelines from compiled steps

**Tasks**:
- [ ] Create `PipelineExecutor` class
- [ ] Load steps from database
- [ ] Execute layer-by-layer
- [ ] Return execution report

**Files to Create**:
- `src/features/pipeline/execution/executor.py`

**Estimated Time**: 4-5 hours

---

#### ☐ Step 4.4: Execution API Endpoint
**Objective**: Add POST /pipelines/{id}/run endpoint

**Tasks**:
- [ ] Add execution endpoint
- [ ] Accept entry_values
- [ ] Return execution report

**Files to Update**:
- `src/api/routers/pipelines.py`
- `src/features/pipeline/service.py`

**Estimated Time**: 2-3 hours

**MILESTONE**: 🎉 Full pipeline execution working!

---

### Phase 5: Integration & Polish

#### ☐ Step 5.1: End-to-End Integration Tests
**Objective**: Comprehensive integration testing

**Estimated Time**: 4-6 hours

---

#### ☐ Step 5.2: Frontend Integration
**Objective**: Connect UI to validation and execution

**Estimated Time**: 3-4 hours

---

#### ☐ Step 5.3: Documentation & Cleanup
**Objective**: Document system and clean up code

**Estimated Time**: 2-3 hours

---

## Progress Tracking

**Current Step**: 🎉 PHASE 2 COMPLETE! 🎉

**Completed Steps**:
- ✅ **Phase 1: Foundation (COMPLETE)**
  - ✅ Step 1.1: Project Setup & Dependencies
  - ✅ Step 1.2: Error Models & Types
  - ✅ Step 1.3: Schema Validator
  - ✅ Step 1.4: Index Builder

- ✅ **Phase 2: API Infrastructure & Incremental Validation (COMPLETE)**
  - ✅ Step 2.1: Validation Orchestrator
  - ✅ Step 2.2: Validation Service Method
  - ✅ Step 2.3: Validation API Endpoint - **MILESTONE! 🎉**
  - ✅ Step 2.4: Graph Builder + Cycle Detection
  - ✅ Step 2.5: Edge Validator
  - ✅ Step 2.6: Module Validator
  - ✅ Step 2.7: Reachability Analyzer - **MILESTONE! 🎉**

**Next Phase**: Phase 3 - Compilation System

**Next Major Milestone**: Step 2.3 - Working validation API endpoint!

---

## Total Estimated Time (Revised)
- **Phase 1 (Foundation)**: ✅ COMPLETE (~3 hours)
- **Phase 2 (API + Incremental Validation)**: 12-17 hours
- **Phase 3 (Compilation)**: 13-18 hours
- **Phase 4 (Execution)**: 8-11 hours
- **Phase 5 (Integration)**: 9-13 hours
- **Total**: 45-62 hours (approximately 1-1.5 weeks of focused development)

---

## Success Criteria
- [ ] Validation API endpoint working and tested from frontend
- [ ] All validation error types detectable and reported correctly
- [ ] Pipelines compile to correct execution steps
- [ ] Steps execute in correct topological order
- [ ] Action modules execute and return results
- [ ] Errors handled gracefully with helpful messages
- [ ] End-to-end tests pass
- [ ] Documentation complete
