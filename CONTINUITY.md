# Template Simulate Endpoint Integration Continuity Document

**Date**: 2025-10-26
**Branch**: server_unification
**Commit**: 0748ee9 - "Complete pipeline execution visualization with real-time data overlay"
**Session Context**: Attempted pipeline execution integration into template simulate endpoint, rolled back due to poor design

---

## Current State (After Rollback)

### What Works Independently ✅

1. **PDF Text Extraction** - Fully functional
   - `POST /api/pdf-templates/simulate` endpoint exists
   - Extracts text from PDFs using pdfplumber
   - Works with bounding box coordinates
   - Handles both stored PDFs (by ID) and uploaded PDFs (multipart)
   - Returns extracted data keyed by field name
   - **Location**: `server-new/src/features/pdf_templates/service.py::simulate_extraction()`
   - **Frontend**: ExtractionFieldsSidebar has "Simulate" button that calls this

2. **Pipeline Execution** - Fully functional
   - Pipeline compilation and validation works
   - Topological sort and layer assignment
   - Execution with entry values
   - Action module data collection
   - Visualization with ExecutedPipelineGraph
   - **Location**: `server-new/src/features/pipelines/service_execution.py::execute_pipeline()`
   - **Frontend**: ExecutePipelineModal provides manual testing UI

3. **Pipeline Builder in Template Builder** - Works
   - Users can build transformation pipelines in step 3 of template builder
   - Entry points auto-created from extraction fields
   - Modules can be placed and connected
   - State preserved when navigating between steps
   - **Location**: `client/src/renderer/features/templates/components/builder/steps/PipelineBuilderStep.tsx`

### What Was Attempted (Then Rolled Back) ❌

**Commits Removed:**
- `f0c2a60` - fix: Data duplicator empty allowed types and infinite reconstruction loop
- `2f7cde7` - fix: Preserve pipeline state when navigating between template builder steps
- `15ddee9` - feat: Display full pipeline execution results in template simulate
- `19279ee` - docs: Update CHANGELOG with pipeline execution integration
- `fce361e` - feat: Integrate pipeline execution into PDF template simulate endpoint

**What Went Wrong:**
1. **Schema Mismatches**: Created duplicate pipeline schemas in `pdf_templates` that didn't match `pipelines` schemas
   - `PipelineEntryPoint` had different fields (id/label/field_reference vs node_id/name)
   - `PipelineNodePin` had wrong type (List[str] vs str)
   - `PipelineModuleInstance` had wrong field names (instance_id/module_id vs module_instance_id/module_ref)

2. **Mapper Complexity**: Created complex mappers to convert between mismatched schemas
   - Added `convert_pipeline_state_to_domain()` in `pdf_templates/mappers.py`
   - Tried to add fields like `direction`, `label`, `allowed_types` to NodeInstance (they don't exist)
   - Had to build lookup dictionaries to get module_ref from module_instance_id

3. **Frontend/Backend Disconnect**:
   - Page numbering mismatch (frontend 0-indexed, backend 1-indexed)
   - Extraction field name vs entry point name mismatch
   - Had to create custom serializers on top of existing `serializePipelineData()`

4. **Poor Design**: Everything was "thrown together" rather than cleanly architected

**Why We Rolled Back:**
> "The work right now has kind of thrown stuff together in a manner that is not good design."

---

## System Architecture (Current)

### Backend Structure

**PDF Template Flow:**
```
POST /api/pdf-templates/simulate
  ↓
PdfTemplateService.simulate_extraction()
  ↓
PdfFilesService.extract_text_from_pdf()
  ↓
extract_data_from_pdf_objects() (utils)
  ↓
Returns: {"field_name": "extracted_text"}
```

**Pipeline Execution Flow:**
```
POST /api/pipelines/{id}/execute
  ↓
PipelineService.get_pipeline_by_id()
  ↓
PipelineExecutionService.execute_pipeline()
  ↓
Returns: PipelineExecutionResult with steps and actions
```

**Key Separation:**
- PDF templates service handles template matching and extraction
- Pipeline service handles pipeline CRUD and compilation
- Pipeline execution service handles runtime execution
- **These are currently separate domains**

### Frontend Structure

**Template Builder Flow:**
```
TemplateBuilderModal
  ├── Step 1: SignatureObjectsStep (PDF form matching)
  ├── Step 2: ExtractionFieldsStep (draw bboxes on PDF)
  │   └── Has "Simulate" button → calls extract endpoint
  ├── Step 3: PipelineBuilderStep (build transformation pipeline)
  │   └── Uses PipelineGraph component
  └── Step 4: TestingStep (shows mock results)
      └── Currently uses MOCK data, not real execution
```

**Pipeline Execution Flow:**
```
/dashboard/pipelines/{id} (detail page)
  └── ExecutePipelineModal
      ├── Manual entry point value input
      ├── Calls POST /api/pipelines/{id}/execute
      └── Shows ExecutedPipelineGraph with real results
```

### Data Type Mismatches

**Frontend Pipeline Types:**
- Location: `client/src/renderer/types/pipelineTypes.ts`
- Entry points: `{node_id, name, type}`
- Modules: Full `ModuleInstance` with all pin metadata
- Pins: Include `direction`, `label`, `type_var`, `allowed_types`

**Backend Domain Types:**
- Location: `server-new/src/shared/types/pipelines.py`
- Entry points: `{node_id, name}` (no type)
- Modules: `ModuleInstance` with minimal data
- Pins: Only `{node_id, type, name, position_index, group_index}`

**Serialization:**
- `serializePipelineData()` in `client/src/renderer/utils/pipelineSerializer.ts`
- Strips frontend-only fields before sending to backend
- This is the CORRECT way to convert (already working for pipeline create/execute)

---

## Key Issues Identified

### 1. Page Number Indexing Mismatch
- **Frontend**: React PDF viewer uses 0-indexed pages (0, 1, 2...)
- **Backend**: pdfplumber uses 1-indexed pages (1, 2, 3...)
- **Impact**: Extraction fields on page 0 won't match text words from page 1
- **Solution Needed**: Convert page numbers when sending extraction fields to backend

### 2. Extraction Field Name vs Entry Point Name
- **Frontend**: Creates entry points with `name: field.label` (e.g., "hawb")
- **Backend**: Expects extracted data keyed by entry point name
- **Current**: Extraction fields use `field_id` (e.g., "field_1234")
- **Solution Needed**: Extraction field `name` should be `field.label` to match entry point

### 3. Schema Duplication
- **Current**: `pdf_templates/schemas.py` has its own `PipelineState` schema
- **Problem**: Doesn't match `pipelines/schemas.py` schema
- **Solution Needed**: Either use the same schema or clearly document why they differ

### 4. Testing Flow Incomplete
- **Current**: TestingStep (step 4) shows mock data
- **Needed**: Should call real simulate endpoint with:
  - PDF (uploaded or stored)
  - Extraction fields (from step 2)
  - Pipeline state (from step 3)
- **Returns**: Combined results (extracted data + pipeline execution + actions)

---

## Recommended Next Steps

### Phase 1: Design Clean Integration (Planning) 🎯

**Goal**: Design how template simulate should work WITHOUT writing code first

**Questions to Answer:**
1. Should template simulate endpoint:
   - Option A: Do extraction only (current state)
   - Option B: Do extraction + pipeline execution (attempted)
   - Option C: Keep them separate, call two endpoints

2. If integrating (Option B):
   - Should we create a new endpoint `/api/pdf-templates/{id}/test` separate from `/simulate`?
   - Or expand existing `/simulate` endpoint?

3. Schema design:
   - Should `pdf_templates` API use the same pipeline schemas as `pipelines` API?
   - Or should they be different (template-specific vs pipeline-specific)?

4. Frontend flow:
   - Should TestingStep call one endpoint or multiple?
   - Where should the integration happen (frontend or backend)?

### Phase 2: Standardize Schemas (If Integrating) 📋

**If we decide to integrate:**

1. **Backend Schema Alignment**:
   - Decide: Use same schemas from `pipelines` or keep separate?
   - If separate: Document the differences and why
   - If same: Import from `pipelines/schemas.py` instead of duplicating

2. **Frontend Serialization**:
   - Use existing `serializePipelineData()` utility
   - Don't create custom mappers
   - Handle page number conversion (0-indexed → 1-indexed)
   - Handle field name mapping (field.label for entry points)

3. **Backend Mappers**:
   - Minimize or eliminate custom mapping code
   - Domain types should be shared between features
   - Don't add fields that don't exist in dataclasses

### Phase 3: Implement Clean Integration (If Proceeding) 🛠️

**Backend Changes:**

1. **Template Service** (`server-new/src/features/pdf_templates/service.py`):
   ```python
   def simulate_with_pipeline(
       self,
       pdf_bytes: bytes,
       extraction_fields: List[ExtractionField],
       pipeline_state: PipelineState  # From shared types
   ) -> TemplateSimulationResult:
       # 1. Extract data
       extracted_data = self.simulate_extraction(pdf_bytes, extraction_fields)

       # 2. Compile pipeline (in-memory, no DB save)
       compiled_steps, pruned_pipeline = self.pipeline_service.compile_for_simulation(
           pipeline_state
       )

       # 3. Execute pipeline with extracted data as entry values
       execution_result = self.pipeline_execution_service.execute_pipeline(
           steps=compiled_steps,
           entry_values_by_name=extracted_data,
           pipeline_state=pruned_pipeline
       )

       # 4. Return combined results
       return TemplateSimulationResult(
           extraction=extracted_data,
           execution=execution_result
       )
   ```

2. **Router** (`server-new/src/api/routers/pdf_templates.py`):
   - Keep extraction-only endpoint at `POST /simulate`
   - Add new endpoint `POST /simulate-with-pipeline` for full testing
   - Or: Add optional `pipeline_state` param to `/simulate`

**Frontend Changes:**

1. **TemplateBuilderModal** - Update `handleTest()`:
   ```typescript
   const handleTest = async () => {
     // Serialize pipeline (strips frontend-only fields)
     const serialized = serializePipelineData(pipelineState, visualState);

     // Convert extraction fields
     const fields = extractionFields.map(f => ({
       name: f.label,  // Matches entry point name
       bbox: f.bbox,
       page: f.page + 1,  // 0-indexed → 1-indexed
       description: f.label
     }));

     // Call simulate endpoint
     const result = await simulateWithPipeline({
       pdfSource: pdfFile ? 'upload' : 'stored',
       pdfFileId,
       pdfFile,
       extractionFields: fields,
       pipelineState: serialized.pipeline_state
     });

     // Display results in TestingStep
     setTestResults(result);
   };
   ```

2. **TestingStep** - Display real results instead of mock data

### Phase 4: Testing & Validation ✅

1. Test extraction-only flow (should still work)
2. Test pipeline-only flow (should still work)
3. Test combined flow (new functionality)
4. Test error cases (extraction fails, pipeline fails, etc.)

---

## Files Reference

### Currently Working (Don't Touch)

**Backend:**
- `server-new/src/features/pdf_files/service.py` - PDF extraction (✅ works)
- `server-new/src/features/pdf_files/utils/extraction.py` - Text extraction from bbox (✅ works)
- `server-new/src/features/pipelines/service.py` - Pipeline compilation/validation (✅ works)
- `server-new/src/features/pipelines/service_execution.py` - Pipeline execution (✅ works)

**Frontend:**
- `client/src/renderer/utils/pipelineSerializer.ts` - Pipeline serialization (✅ works)
- `client/src/renderer/features/pipelines/components/PipelineGraph.tsx` - Graph editor (✅ works)
- `client/src/renderer/features/pipelines/components/ExecutedPipelineGraph.tsx` - Visualization (✅ works)

### Needs Clean Implementation

**Backend:**
- `server-new/src/api/routers/pdf_templates.py` - Add pipeline execution integration
- `server-new/src/features/pdf_templates/service.py` - Add `simulate_with_pipeline()` method
- `server-new/src/api/schemas/pdf_templates.py` - Align or document pipeline schemas

**Frontend:**
- `client/src/renderer/features/templates/components/builder/TemplateBuilderModal.tsx` - Update `handleTest()`
- `client/src/renderer/features/templates/components/builder/steps/TestingStep.tsx` - Display real results
- `client/src/renderer/features/templates/hooks/useTemplatesApi.ts` - Add `simulateWithPipeline()` method

---

## Design Principles (Learned from Rollback)

1. **Don't Duplicate Schemas**: If two features need the same data structure, share it
2. **Use Existing Serialization**: Don't create custom mappers when standard ones exist
3. **Domain Types Are Canonical**: API schemas map to domain types, not the other way around
4. **Plan Before Coding**: Design the integration cleanly before implementing
5. **Keep Features Separate Until Integration Is Designed**: Working independently is better than broken together

---

## Questions for Next Session

1. **Do we want to integrate extraction + pipeline execution?**
   - If yes: Design the integration cleanly first
   - If no: Keep them separate, improve each independently

2. **What should the template "test" flow look like from a user perspective?**
   - What do they see in TestingStep?
   - What happens when they click "Test Template"?

3. **Should we create a new endpoint or expand existing one?**
   - `/api/pdf-templates/simulate` (current, extraction only)
   - `/api/pdf-templates/simulate-with-pipeline` (new, full testing)
   - `/api/pdf-templates/test` (new, combined flow)

4. **Schema strategy:**
   - Share schemas between `pdf_templates` and `pipelines`?
   - Or keep separate with clear documentation of differences?

---

## Git Status

**Branch**: server_unification
**HEAD**: 0748ee9 - "Complete pipeline execution visualization with real-time data overlay"
**Working Tree**: Clean (no uncommitted changes)
**Commits Ahead of Origin**: 32 commits

**Removed Commits** (rolled back):
- f0c2a60 through fce361e (integration attempts)

**Ready for**: Clean redesign and implementation

---

## Commands Reference

**Start Backend:**
```bash
cd server-new
python main.py
```

**Start Frontend:**
```bash
cd client
npm run dev
```

**Test Extraction (currently works):**
- Open template builder
- Go to step 2 (Extraction Fields)
- Click "Simulate" button
- Should see extracted text

**Test Pipeline Execution (currently works):**
- Open pipeline detail page
- Click "Execute Pipeline"
- Enter entry point values
- Should see execution results with visualization

**Test Template Testing (currently mock data):**
- Open template builder
- Complete steps 1-3
- Click "Test Template"
- Shows mock results (needs real integration)
