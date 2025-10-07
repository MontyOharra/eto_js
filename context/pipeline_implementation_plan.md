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
2. **Storage Strategy**: Use `pipeline_steps` table as compiled execution cache with checksum-based deduplication
3. **Validation Timing**: Triggers on pipeline_state changes (not visual_state)
4. **Module Kinds**: `transform`, `action`, `logic` (all three are valid)
5. **Action Detection**: Use `ModuleInstance.module_kind` field
6. **Type Variable Validation**: Backend validates type var unification (defense in depth)
7. **Dead Branch Warnings**: Deferred to v2
8. **Debouncing**: Frontend responsibility (~300-500ms after state changes)
9. **End-to-End Testing**: Build API infrastructure first, add validation rules incrementally
10. **Checksum Caching**: Pipelines with identical structure share compiled steps via ID-agnostic checksums

### Database Schema:
- `pipeline_definitions`: Stores source pipeline JSON + plan_checksum
- `pipeline_steps`: Stores compiled execution steps (grouped by plan_checksum, NOT by pipeline_id)
- `module_catalog`: Module templates for validation

### Dependencies:
- ✅ `networkx>=3.0` (installed)

---

## Implementation Steps

### Phase 1: Foundation ✅ COMPLETE

#### ✅ Step 1.1: Project Setup & Dependencies

**Tasks Completed**:
- [x] Add `networkx>=3.0` to requirements.txt
- [x] Install dependencies
- [x] Create directory structure

**Files Created**:
- Directory: `src/features/pipeline/validation/`
- Directory: `src/features/pipeline/compilation/`
- Directory: `src/features/pipeline/execution/`

---

#### ✅ Step 1.2: Error Models & Types

**Tasks Completed**:
- [x] Create `ValidationErrorCode` enum with all error types
- [x] Create `ValidationError` model
- [x] Create `ValidationResult` model

**Files Created**:
- `src/features/pipeline/validation/errors.py`

**Key Components**:
```python
class ValidationErrorCode(str, Enum):
    # Schema errors
    MISSING_FIELD = "MISSING_FIELD"
    INVALID_TYPE = "INVALID_TYPE"
    DUPLICATE_NODE_ID = "DUPLICATE_NODE_ID"

    # Edge errors
    MISSING_UPSTREAM = "MISSING_UPSTREAM"
    MULTIPLE_UPSTREAMS = "MULTIPLE_UPSTREAMS"
    EDGE_TYPE_MISMATCH = "EDGE_TYPE_MISMATCH"
    SELF_LOOP = "SELF_LOOP"

    # Graph errors
    CYCLE = "CYCLE"

    # Module errors
    MODULE_NOT_FOUND = "MODULE_NOT_FOUND"
    GROUP_CARDINALITY = "GROUP_CARDINALITY"
    TYPEVAR_MISMATCH = "TYPEVAR_MISMATCH"
    MISSING_CONFIG = "MISSING_CONFIG"

    # Reachability errors
    NO_ACTIONS = "NO_ACTIONS"
```

---

#### ✅ Step 1.3: Schema Validator

**Tasks Completed**:
- [x] Implement `SchemaValidator` class
- [x] Check node ID global uniqueness
- [x] Validate pin types (must be in: str, int, float, bool, datetime)
- [x] Validate module_ref format

**Files Created**:
- `src/features/pipeline/validation/schema_validator.py`

**Key Validations**:
1. Presence checks (entry_points, modules, connections arrays exist)
2. Module field validation (instance_id, ref, config, inputs, outputs)
3. Pin field validation (node_id, type, position_index, group_index)
4. Global node ID uniqueness across all pins and entry points

---

#### ✅ Step 1.4: Index Builder

**Tasks Completed**:
- [x] Create `PinInfo` Pydantic model
- [x] Create `PipelineIndices` class
- [x] Build all four indices:
  - `pin_by_id`: Fast pin lookup by node_id
  - `module_by_id`: Fast module lookup by instance_id
  - `input_to_upstream`: Input pin → upstream output pin mapping
  - `output_to_downstreams`: Output pin → list of downstream input pins

**Files Created**:
- `src/features/pipeline/validation/index_builder.py`

**Key Components**:
```python
class PinInfo(BaseModel):
    node_id: str
    type: str
    module_instance_id: Optional[str]  # None for entry points
    direction: str  # "in", "out", or "entry"

class PipelineIndices:
    pin_by_id: Dict[str, PinInfo]
    module_by_id: Dict[str, ModuleInstance]
    input_to_upstream: Dict[str, str]
    output_to_downstreams: Dict[str, List[str]]
```

---

### Phase 2: Validation System ✅ COMPLETE

#### ✅ Step 2.1: Validation Orchestrator (Minimal)

**Tasks Completed**:
- [x] Create `PipelineValidator` class in `src/features/pipeline/validation/validator.py`
- [x] Constructor accepts dependencies (ModuleCatalogRepository)
- [x] Implement `validate(pipeline_state: PipelineState) -> ValidationResult`
- [x] Run SchemaValidator
- [x] Build PipelineIndices
- [x] Design for easy addition of more validation stages

**Files Created**:
- `src/features/pipeline/validation/validator.py`
- `test_validator_step_2_1.py` (7 comprehensive tests, all passing)

**Architecture**:
- Modular design with separate validation stages
- Early exit on schema errors (no point validating structure if schema is broken)
- Passes indices between stages to avoid rebuilding

---

#### ✅ Step 2.2: Validation Service Method

**Tasks Completed**:
- [x] Update `src/features/pipeline/service.py`
- [x] Add `validate_pipeline(pipeline_state: PipelineState) -> ValidationResult`
- [x] Create PipelineValidator instance with dependencies
- [x] Call validator.validate()
- [x] Handle errors gracefully

**Files Updated**:
- `src/features/pipeline/service.py`
- `test_service_step_2_2.py` (4 tests, all passing)

**Integration**:
- Service layer properly injects ModuleCatalogRepository
- Error handling for invalid pipeline states
- Clean separation between service and validation logic

---

#### ✅ Step 2.3: Validation API Endpoint

**Tasks Completed**:
- [x] Update `src/api/routers/pipelines.py`
- [x] Add endpoint `POST /pipelines/validate`
- [x] Accept request body: `{"pipeline_json": <PipelineState>}`
- [x] Parse pipeline_json to PipelineState model
- [x] Call pipeline_service.validate_pipeline()
- [x] Return ValidationResult as JSON
- [x] Handle errors (400 for invalid JSON, 500 for internal errors)
- [x] Add "Validate Pipeline" button to frontend Create page

**Files Updated**:
- `src/api/routers/pipelines.py` - Added POST /pipelines/validate endpoint
- `client/src/renderer/routes/transformation_pipeline/create.tsx` - Added validation button

**Frontend Integration**:
- Purple "Validate Pipeline" button next to "Save Pipeline"
- Calls validation API with current pipeline state
- Logs validation result to console with formatted output
- Shows success/failure status clearly

**API Response Format**:
```json
{
  "valid": true,
  "errors": []
}
```

**MILESTONE**: 🎉 Working validation API endpoint with basic schema validation!

---

#### ✅ Step 2.4: Graph Builder + Cycle Detection

**Tasks Completed**:
- [x] Create `GraphBuilder` class
- [x] Implement `build_pin_graph(pipeline_state, indices) -> nx.DiGraph`
- [x] Add all pin node_ids as nodes with attributes
- [x] Add edges from connections
- [x] Add internal module edges (inputs → outputs within modules)
- [x] Update `PipelineValidator` to check for cycles
- [x] Use NetworkX `is_directed_acyclic_graph()` and `simple_cycles()`

**Files Created**:
- `src/features/pipeline/validation/graph_builder.py`

**Files Updated**:
- `src/features/pipeline/validation/validator.py`

**Key Implementation Details**:
- Graph includes both explicit connections AND internal module edges
- Internal edges represent data flow through module processing
- Cycle detection finds ALL cycles (not just first one)
- Error messages include full cycle path and length

**Graph Structure**:
- **Nodes**: All pin node_ids (entries, inputs, outputs)
- **Edges**: Connection edges + internal module edges
- **Node Attributes**: type, direction, module_instance_id

**Tests (All Passing)**:
1. Valid DAG with no cycles passes
2. Simple cycle A→B→A detected
3. Self-loop detected as cycle
4. Complex multi-node cycles detected
5. Branching DAG with fan-out is valid

---

#### ✅ Step 2.5: Edge Validator

**Tasks Completed**:
- [x] Create `EdgeValidator` class
- [x] Check each input has exactly one upstream
- [x] Check type equality for all connections
- [x] Check no self-loops
- [x] Update `PipelineValidator` to run EdgeValidator

**Files Created**:
- `src/features/pipeline/validation/edge_validator.py`

**Files Updated**:
- `src/features/pipeline/validation/validator.py`

**Validation Rules**:
1. **Input Cardinality**: Every input pin must have exactly one upstream
2. **Type Matching**: Connected pins must have identical types (no coercion)
3. **Self-Loop Prevention**: Pin cannot connect to itself
4. **Multiple Upstream Detection**: Input cannot have >1 upstream

**Error Details Provided**:
- Pin names and IDs
- Expected vs actual types
- Connection source and target
- Module context

**Tests (All Passing)**:
1. Valid connections with proper types pass
2. Missing upstream connection detected
3. Type mismatch (str→int) detected
4. Self-loop detected
5. Multiple type errors all reported
6. Partial connections detected
7. Complex multi-module pipeline validates correctly

---

#### ✅ Step 2.6: Module Validator

**Tasks Completed**:
- [x] Create `ModuleValidator` class
- [x] Fetch module templates from ModuleCatalogRepository
- [x] Validate group cardinalities (min/max pin counts)
- [x] Validate type variable unification
- [x] Validate config against schema (required fields)
- [x] Update `PipelineValidator` to run ModuleValidator

**Files Created**:
- `src/features/pipeline/validation/module_validator.py`

**Files Updated**:
- `src/features/pipeline/validation/validator.py`
- `src/features/pipeline/service.py`

**Validation Rules**:
1. **Template Lookup**: Module must exist in catalog
2. **Group Cardinality**: Pin counts must satisfy min_count ≤ count ≤ max_count
3. **Type Variables**: Type var T must resolve to single type across module
4. **Config Validation**: Required fields must be present (uses JSON Schema)

**Type Variable Unification Logic**:
- First occurrence of type var binds it to a concrete type
- All subsequent occurrences must match that type
- Checks against type_params domain (allowed types for that var)

**Error Details Provided**:
- Group labels and actual vs expected counts
- Type variable name and conflicting types
- Missing config field names
- Module reference that wasn't found

**Tests (All Passing)**:
1. Valid module with correct cardinality passes
2. Module not found in catalog detected
3. Too few pins in group detected
4. Too many pins in group detected
5. Type variable unification errors detected
6. Missing required config fields detected

---

#### ✅ Step 2.7: Reachability Analyzer

**Tasks Completed**:
- [x] Create `ReachabilityAnalyzer` class
- [x] Identify action modules (from module_kind field)
- [x] Return NO_ACTIONS error if no actions present
- [x] Reverse BFS from action inputs to find reachable modules
- [x] Update `PipelineValidator` to run ReachabilityAnalyzer
- [x] Store reachable_modules set for compilation

**Files Created**:
- `src/features/pipeline/validation/reachability_analyzer.py`

**Files Updated**:
- `src/features/pipeline/validation/validator.py`

**Algorithm**:
1. Find all action modules (module_kind == "action")
2. If no actions found, return NO_ACTIONS error
3. Collect all action input pins
4. Reverse BFS from action inputs through pin graph
5. Collect module_instance_ids of all visited pins
6. Return set of reachable module IDs

**Key Features**:
- Uses pin-level graph for traversal
- Traverses backward through connections
- Identifies dead branches (unreachable modules)
- Dead branches not errors (just informational)
- Reachable set used by compiler for pruning

**Tests (All Passing)**:
1. Pipeline with no actions returns NO_ACTIONS error
2. Pipeline with action is valid, modules are reachable
3. Dead branch correctly identified as unreachable
4. Multiple action branches all marked as reachable
5. Complex pipeline with chain correctly analyzed

**MILESTONE**: 🎉 Complete validation system working end-to-end via API!

---

### Phase 3: Compilation System (UPDATED)

#### ✅ Step 3.1: Graph Pruner (COMPLETE)
**Status**: Complete | **Files**: `graph_pruner.py`

**Completed**:
- [x] Prunes pipeline to action-reachable modules only
- [x] Filters connections to reachable pins
- [x] Returns pruned PipelineState

---

#### ✅ Step 3.2: Topological Sorter (COMPLETE)
**Status**: Complete | **Files**: `topological_sorter.py`

**Completed**:
- [x] Builds module-level dependency graph
- [x] Uses NetworkX `topological_generations()` to compute layers
- [x] Returns list of layers (each layer = list of module IDs)

---

#### ✅ Step 3.3: Checksum Calculator (COMPLETE)
**Status**: Complete | **Files**: `checksum_calculator.py`, `test_checksum_calculator.py`

**Completed**:
- [x] Computes ID-agnostic SHA-256 checksum of pipeline structure
- [x] Sorts nodes by structural properties (not by IDs)
- [x] Maps actual node IDs to canonical position IDs
- [x] Hashes normalized structure using position IDs
- [x] Comprehensive tests verifying ID-agnostic behavior

**Implementation Details**:
1. **Canonical Ordering**: Nodes sorted by structural properties
   - Entry points: sorted by name
   - Modules: sorted by (module_ref, module_kind, config, input count, output count)
   - Pins: sorted by (group_index, position_index)
   - Connections: sorted by position IDs after mapping

2. **Position Mapping**: Actual IDs mapped to positions
   - Entry points: `entry_0`, `entry_1`, ...
   - Modules: `mod_0`, `mod_1`, ...
   - Input pins: `mod_0_in_0`, `mod_0_in_1`, ...
   - Output pins: `mod_0_out_0`, `mod_0_out_1`, ...

3. **Normalization**: Structure rebuilt using position IDs only
   - Excludes: actual node IDs, UI data (labels, colors, positions)
   - Includes: module refs, configs, types, connection topology

4. **Deterministic Hashing**: JSON serialization with sorted keys

**Test Results (All Passing)**:
- [x] Two identical structures with different IDs → same checksum
- [x] Connection order irrelevant → same checksum
- [x] Different structure → different checksum
- [x] Different config → different checksum
- [x] Pin names don't affect checksum → same checksum

**Result**: Two pipelines with identical structure but different node IDs produce the **same checksum**.

---

#### ✅ Step 3.4: Update Database Models (COMPLETE)
**Status**: Complete | **Files**: `models.py`

**Completed**:
- [x] Removed `pipeline_id` FK constraint from PipelineStepModel
- [x] Removed `pipeline_definition` relationship from PipelineStepModel
- [x] Removed `pipeline_steps` relationship from PipelineDefinitionModel
- [x] Updated index to use only `plan_checksum` (not composite)
- [x] Updated docstrings to reflect many-to-many design

**Key Design Change**: Pipeline steps are now shared across pipelines via structural checksums. Multiple pipelines with identical structure share the same compiled steps, enabling true caching and deduplication.

**Many-to-Many Relationship via Checksum**:
- Multiple `PipelineDefinition` records can reference the same set of `PipelineStep` records
- The relationship is established through matching `plan_checksum` values (NOT through FK)
- Steps persist indefinitely as an immutable cache (pipelines are archived, not deleted)

**Schema Changes**:
- `PipelineStepModel.pipeline_id` → REMOVED (was FK)
- `PipelineStepModel.pipeline_definition` relationship → REMOVED
- `PipelineDefinitionModel.pipeline_steps` relationship → REMOVED
- Index `idx_pipeline_steps_pipeline_checksum` → Changed to `idx_pipeline_steps_checksum` (single column)

**Database Reset Required**: User will reset database manually in dev mode

**Schema Reference**:
```python
# PipelineStepModel - NO FK to pipeline
class PipelineStepModel(BaseModel):
    id: Mapped[int] = mapped_column(primary_key=True)
    plan_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    # ... module fields ...
    __table_args__ = (
        Index('idx_pipeline_steps_checksum', 'plan_checksum'),
    )

# PipelineDefinitionModel - Add checksum
class PipelineDefinitionModel(BaseModel):
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    plan_checksum: Mapped[Optional[str]] = mapped_column(String(64))
    # ... other fields ...
    __table_args__ = (
        Index('idx_pipeline_definitions_checksum', 'plan_checksum'),
    )
```

**Query Pattern After Change**:
```python
# Get steps for a pipeline
pipeline = get_pipeline(pipeline_id)
steps = db.query(PipelineStepModel).filter(
    PipelineStepModel.plan_checksum == pipeline.plan_checksum
).order_by(PipelineStepModel.step_number).all()
```

**Files to Update**:
- `src/shared/database/models.py`

---

#### ☐ Step 3.5: Pipeline Compiler
**Objective**: Orchestrate compilation with cache-check logic

**Tasks**:
- [ ] Create `PipelineCompiler` class
- [ ] Implement `compile(pipeline_state, reachable_modules, pipeline_id)`:
  - [ ] Prune to action-reachable (use GraphPruner)
  - [ ] Compute ID-agnostic checksum (use ChecksumCalculator)
  - [ ] Check if steps exist for checksum (repository query)
  - [ ] If cache hit: return (existing_steps, checksum)
  - [ ] If cache miss:
    - [ ] Compute topological layers (use TopologicalSorter)
    - [ ] Build input_field_mappings for each module
    - [ ] Build output_display_names for each module
    - [ ] Create PipelineStepModel instances
    - [ ] Return (new_steps, checksum)

**Helper Methods**:
- [ ] `_build_pin_to_module_lookup(pipeline) -> Dict[str, str]`
- [ ] `_build_input_mappings(module, connections, lookup) -> Dict[str, str]`
- [ ] `_build_output_names(module) -> Dict[str, str]`

**Files to Create**:
- `src/features/pipeline/compilation/compiler.py`

---

#### ☐ Step 3.6: Pipeline Repository Updates
**Objective**: Add methods for checksum-based step operations

**Tasks**:
- [ ] Add `get_steps_by_checksum(checksum: str) -> List[PipelineStepModel]`
  - Query steps WHERE plan_checksum = checksum
  - Order by step_number ASC
- [ ] Add `save_pipeline_steps(steps: List[PipelineStepModel])`
  - Bulk insert steps
  - Handle transaction properly
- [ ] Add `update_pipeline_checksum(pipeline_id: str, checksum: str)`
  - Update pipeline.plan_checksum field
- [ ] Add proper error handling

**Files to Update**:
- `src/shared/database/repositories/pipeline.py`

---

#### ☐ Step 3.7: Compilation Service Method
**Objective**: Add compilation logic to PipelineService

**Tasks**:
- [ ] Add `compile_pipeline(pipeline_id: str) -> CompilationResult`:
  - [ ] Load pipeline from database
  - [ ] Parse pipeline_json to PipelineState
  - [ ] Re-run validation (get reachable_modules)
  - [ ] Call PipelineCompiler.compile()
  - [ ] Check if checksum already exists (cache check)
  - [ ] If cache miss: save new steps via repository
  - [ ] Update pipeline.plan_checksum
  - [ ] Return metadata (checksum, step_count, cache_hit boolean)

**Return Model**:
```python
class CompilationResult(BaseModel):
    checksum: str
    step_count: int
    cache_hit: bool
    layers: int
```

**Files to Update**:
- `src/features/pipeline/service.py`

---

#### ☐ Step 3.8: Update Create Pipeline Endpoint
**Objective**: Integrate validation + compilation into POST /pipelines

**Tasks**:
- [ ] Update `POST /pipelines` endpoint:
  - [ ] Validate pipeline (existing logic)
  - [ ] If valid: compile pipeline (new logic)
  - [ ] Save pipeline definition
  - [ ] Return response with compilation metadata
- [ ] Handle errors gracefully
- [ ] Add proper HTTP status codes

**Response Format**:
```json
{
  "pipeline_id": "abc123",
  "name": "Email Processor",
  "compilation": {
    "checksum": "3d1a4f...",
    "step_count": 5,
    "cache_hit": false,
    "layers": 3
  }
}
```

**Files to Update**:
- `src/api/routers/pipelines.py`

**MILESTONE**: 🎉 Pipelines can be created with compiled execution plan and checksum-based caching!

---

### Phase 4: Execution System

#### ☐ Step 4.1: Execution Context
**Objective**: Create runtime value store for execution

**Tasks**:
- [ ] Create `ExecutionContext` class
- [ ] Initialize with entry_values dict
- [ ] Implement `set_value(pin_id, value)` method
- [ ] Implement `get_value(pin_id)` method
- [ ] Track execution metadata (start time, step timings)

**Files to Create**:
- `src/features/pipeline/execution/context.py`

---

#### ☐ Step 4.2: Module Resolver
**Objective**: Resolve module_ref to handler instance

**Tasks**:
- [ ] Create `ModuleResolver` class
- [ ] Use ModuleRegistry to lookup handlers
- [ ] Handle missing module errors
- [ ] Cache resolved handlers

**Files to Create**:
- `src/features/pipeline/execution/module_resolver.py`

---

#### ☐ Step 4.3: Pipeline Executor
**Objective**: Execute pipelines layer-by-layer from compiled steps

**Tasks**:
- [ ] Create `PipelineExecutor` class
- [ ] Implement `execute(pipeline_id, entry_values) -> ExecutionReport`:
  - [ ] Load pipeline from database
  - [ ] Get steps by checksum (via repository)
  - [ ] Initialize ExecutionContext with entry_values
  - [ ] Group steps by step_number (layers)
  - [ ] For each layer:
    - [ ] For each step in layer:
      - [ ] Build input dict from input_field_mappings
      - [ ] Resolve handler via ModuleResolver
      - [ ] Call handler.run(inputs, config)
      - [ ] Store outputs in ExecutionContext
      - [ ] Track action results
  - [ ] Return ExecutionReport

**Error Handling**:
- [ ] Fail-fast on handler errors
- [ ] Include module_instance_id in error report
- [ ] Capture stack traces for debugging

**Files to Create**:
- `src/features/pipeline/execution/executor.py`

---

#### ☐ Step 4.4: Execution API Endpoint
**Objective**: Add POST /pipelines/{id}/run endpoint

**Tasks**:
- [ ] Add `POST /pipelines/{pipeline_id}/run` endpoint
- [ ] Accept request body: `{"entry_values": {"entry_1": "value", ...}}`
- [ ] Call PipelineService.execute_pipeline()
- [ ] Return ExecutionReport as JSON
- [ ] Handle errors (400 for missing entries, 500 for runtime errors)

**Response Format**:
```json
{
  "status": "success",
  "started_at": "2025-10-06T12:00:00Z",
  "completed_at": "2025-10-06T12:00:05Z",
  "actions": [
    {
      "module_instance_id": "m_action",
      "result": {"order_id": "12345"}
    }
  ],
  "errors": []
}
```

**Files to Update**:
- `src/api/routers/pipelines.py`
- `src/features/pipeline/service.py`

**MILESTONE**: 🎉 Full pipeline execution working with checksum-based caching!

---

### Phase 5: Integration & Testing

#### ☐ Step 5.1: End-to-End Integration Tests
**Objective**: Test complete flow from creation to execution

**Test Scenarios**:
- [ ] Create pipeline → compile → execute → verify results
- [ ] Create identical pipeline → verify cache hit → execute
- [ ] Modify pipeline → verify new checksum → recompile → execute
- [ ] Multiple pipelines with same structure → verify shared steps
- [ ] Complex pipeline with branches → verify correct execution order

---

#### ☐ Step 5.2: Frontend Integration
**Objective**: Connect UI to execution and show results

**Tasks**:
- [ ] Add "Run Pipeline" button to View page
- [ ] Add entry value input form
- [ ] Display execution results
- [ ] Show compilation metadata (cache hit indicator)
- [ ] Handle errors in UI

---

#### ☐ Step 5.3: Documentation & Cleanup
**Objective**: Document the system and clean up code

**Tasks**:
- [ ] Update API documentation
- [ ] Document checksum algorithm
- [ ] Add inline code comments
- [ ] Create developer guide
- [ ] Review and refactor

---

## Progress Tracking

**Current Status**: Phase 3 - Compilation System

**Completed**:
- ✅ Phase 1: Foundation (Complete)
- ✅ Phase 2: Validation System (Complete)
- ✅ Phase 3: Compilation utilities (3/8 steps)
  - ✅ Step 3.1: Graph Pruner
  - ✅ Step 3.2: Topological Sorter
  - ✅ Step 3.3: Checksum Calculator (needs ID-agnostic refactor)

**Next Steps**:
1. **Immediate**: Update ChecksumCalculator to be ID-agnostic
2. **Then**: Create database migration for schema changes
3. **Then**: Implement PipelineCompiler with cache logic

---

## Key Metrics & Success Criteria

### Performance Targets
- **Cache Hit**: Compilation time < 10ms (just checksum lookup)
- **Cache Miss**: Compilation time < 500ms (full compilation)
- **Execution**: < 100ms per module (depends on handler)

### Success Criteria
- [x] Validation API working
- [ ] Pipelines compile to correct steps
- [ ] Identical structures produce same checksum
- [ ] Cache hits skip compilation
- [ ] Steps execute in correct order
- [ ] Action modules return results
- [ ] Errors handled gracefully
- [ ] End-to-end tests pass

---

## Breaking Changes

### Database Schema Changes (Development Mode)
Since we're in development, simply update the models and drop/recreate the database:

1. **PipelineStepModel**: Remove `pipeline_id` FK, keep `plan_checksum`
2. **PipelineDefinitionModel**: Add `plan_checksum` column
3. **Drop database and recreate** (no migration needed)

### API Changes
- `POST /pipelines` response now includes compilation metadata
- Step queries now use checksum instead of pipeline_id

### Benefits
- ✅ Massive performance improvement for duplicate structures
- ✅ Reduced storage for similar pipelines
- ✅ Simplified caching logic
- ✅ Natural deduplication at database level
