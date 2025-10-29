# Backend Plan: Verify Pipeline Definition Endpoint for Template Editing

## Architecture Decision

**Lazy Loading Approach**: Template version responses do NOT include pipeline data. Frontend makes separate API call when needed.

### Current GET Version Response (CORRECT - Keep as is)
```json
GET /pdf-templates/versions/{version_id}
{
  "version_id": 123,
  "template_id": 456,
  "signature_objects": {...},
  "extraction_fields": [...],
  "pipeline_definition_id": 789  // ← Frontend uses this to fetch pipeline separately
}
```

### Frontend Flow for Template Editing
```
1. User clicks "Edit" on template
2. GET /pdf-templates/versions/{version_id}
   → Returns signature_objects, extraction_fields, pipeline_definition_id
3. GET /pipelines/{pipeline_definition_id}
   → Returns pipeline_state, visual_state
4. Open TemplateBuilderModal with all initial data
```

---

## What We Need to Verify

### Does the Pipeline Endpoint Already Exist?

We need an endpoint that returns pipeline definition details by ID:
```
GET /pipelines/{pipeline_definition_id}
```

**Returns:**
```json
{
  "id": 789,
  "name": "Template Pipeline",
  "pipeline_state": {
    "entry_points": [...],
    "modules": [...],
    "connections": [...]
  },
  "visual_state": {
    "modules": {...},
    "entry_points": {...}
  }
}
```

---

## Investigation: Check Existing Pipeline Router

**File to examine**: `server-new/src/api/routers/pipelines.py`

### What to look for:
1. ✅ Does `GET /pipelines/{id}` endpoint exist?
2. ✅ Does it return `pipeline_state` and `visual_state`?
3. ✅ Is the response format suitable for the template builder?

---

## Expected Findings

### Scenario A: Endpoint Exists ✅
If `GET /pipelines/{id}` already exists and returns the needed data:

**Action**: ✅ **NO BACKEND CHANGES NEEDED**

Just document the endpoint for frontend to use:
```typescript
// Frontend: Fetch pipeline data when editing template
const versionResponse = await fetch(`/api/pdf-templates/versions/${versionId}`);
const { pipeline_definition_id } = await versionResponse.json();

const pipelineResponse = await fetch(`/api/pipelines/${pipeline_definition_id}`);
const { pipeline_state, visual_state } = await pipelineResponse.json();

// Open template builder with initial data
<TemplateBuilderModal
  mode="edit"
  initialSignatureObjects={versionData.signature_objects}
  initialExtractionFields={versionData.extraction_fields}
  initialPipelineState={pipeline_state}
  initialVisualState={visual_state}
/>
```

---

### Scenario B: Endpoint Missing or Incomplete ⚠️
If endpoint doesn't exist or doesn't return the needed data:

**Required Changes:**

#### 1. Add/Update Pipeline GET Endpoint (if needed)

**File**: `server-new/src/api/routers/pipelines.py`

```python
@router.get("/{id}", response_model=PipelineDefinitionResponse)
async def get_pipeline_definition(
    id: int,
    service: PipelineService = Depends(lambda: ServiceContainer.get_pipeline_service())
) -> PipelineDefinitionResponse:
    """
    Get pipeline definition by ID.

    Used by:
    - Template editor to load existing pipeline for editing
    - Pipeline viewer
    """
    pipeline = service.get_pipeline_definition(id)
    return convert_pipeline_to_api(pipeline)
```

#### 2. Create Response Schema (if needed)

**File**: `server-new/src/api/schemas/pipelines.py`

```python
class PipelineDefinitionResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    pipeline_state: PipelineState
    visual_state: VisualState
    is_active: bool
    created_at: datetime
```

#### 3. Add Service Method (if needed)

**File**: `server-new/src/features/pipelines/service.py`

```python
def get_pipeline_definition(self, pipeline_id: int) -> PipelineDefinition:
    """Get pipeline definition by ID"""
    pipeline = self.pipeline_repository.get_by_id(pipeline_id)
    if not pipeline:
        raise ObjectNotFoundError(f"Pipeline definition {pipeline_id} not found")
    return pipeline
```

---

## Verification Steps

### Step 1: Check if Pipeline Router Exists
```bash
# Look for pipelines router
ls server-new/src/api/routers/pipelines.py
```

### Step 2: Check Existing Endpoints
```bash
# Search for GET endpoints in pipeline router
grep -n "router.get" server-new/src/api/routers/pipelines.py
```

### Step 3: Test Endpoint (if exists)
```bash
# Create a template to get a pipeline_definition_id
curl -X POST http://localhost:8090/api/pdf-templates \
  -H "Content-Type: application/json" \
  -d '{...template data...}'

# Extract pipeline_definition_id from response
# Then test the pipeline endpoint
curl http://localhost:8090/api/pipelines/{pipeline_definition_id}

# Check if response includes:
# - pipeline_state
# - visual_state
```

---

## Implementation Checklist

### Phase 1: Investigation ✅
- [ ] Check if `server-new/src/api/routers/pipelines.py` exists
- [ ] Check if `GET /pipelines/{id}` endpoint exists
- [ ] Check if response includes `pipeline_state` and `visual_state`
- [ ] Test endpoint with existing pipeline_definition_id

### Phase 2: Implementation (Only if needed) ⚠️
- [ ] Add `GET /pipelines/{id}` endpoint (if missing)
- [ ] Add response schema (if missing)
- [ ] Add service method (if missing)
- [ ] Add mapper (if needed)
- [ ] Test endpoint returns correct data

### Phase 3: Documentation ✅
- [ ] Document the two-call pattern for template editing
- [ ] Update frontend plan to use separate API calls
- [ ] Add example code for fetching pipeline data

---

## Frontend Integration Pattern

```typescript
// In TemplateDetailModal.tsx

const handleEditClick = async () => {
  if (!template || !versionDetail) return;

  // Step 1: Already have version data (signature objects, extraction fields)
  // versionDetail contains: signature_objects, extraction_fields, pipeline_definition_id

  // Step 2: Fetch pipeline data separately
  try {
    const pipelineResponse = await fetch(
      `${API_CONFIG.ENDPOINTS.PIPELINES}/${versionDetail.pipeline_definition_id}`
    );
    const pipelineData = await pipelineResponse.json();

    // Step 3: Open template builder with all data
    setIsEditMode(true);
    setEditInitialData({
      signatureObjects: versionDetail.signature_objects,
      extractionFields: versionDetail.extraction_fields,
      pipelineState: pipelineData.pipeline_state,
      visualState: pipelineData.visual_state,
    });
  } catch (error) {
    console.error('Failed to load pipeline data:', error);
    alert('Failed to load pipeline data for editing');
  }
};
```

---

## Benefits of Lazy Loading Approach

### Performance ✅
- Template version list loads faster (no pipeline data)
- Pipeline data only fetched when actually needed (editing/viewing)
- Smaller JSON payloads for version browsing

### Separation of Concerns ✅
- Version endpoint focuses on template-specific data
- Pipeline endpoint focuses on pipeline-specific data
- Clean API boundaries

### Caching ✅
- Can cache version data separately from pipeline data
- Pipeline definitions shared across templates can be cached once

### Flexibility ✅
- Same pipeline endpoint used by pipeline viewer AND template editor
- Easy to add pagination/filtering to version list without affecting pipeline data

---

## Estimated Time

### If Pipeline Endpoint Exists: 0 minutes
Just use the existing endpoint!

### If Pipeline Endpoint Needs Updates: 15-20 minutes
- Add endpoint: 5 min
- Add schema: 5 min
- Add service method: 5 min
- Testing: 5-10 min

---

## Next Steps

1. **Investigate**: Check if `GET /pipelines/{id}` endpoint exists
2. **Test**: Verify it returns `pipeline_state` and `visual_state`
3. **Document**: Record the endpoint details for frontend team
4. **Implement** (only if needed): Add missing pieces

Would you like me to investigate the existing pipeline router now?
