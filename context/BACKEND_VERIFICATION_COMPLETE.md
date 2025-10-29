# Backend Verification: COMPLETE ✅

## Summary: NO BACKEND CHANGES NEEDED

All required endpoints exist and return the correct data for template editing functionality.

---

## Verified Endpoints

### 1. GET Template Version ✅
**Endpoint**: `GET /pdf-templates/versions/{version_id}`

**File**: `server-new/src/api/routers/pdf_templates.py` (lines 167-184)

**Response** (`GetTemplateVersionResponse`):
```json
{
  "version_id": 123,
  "template_id": 456,
  "version_num": 2,
  "source_pdf_id": 789,
  "is_current": true,
  "signature_objects": {
    "text_words": [...],
    "text_lines": [...],
    ...
  },
  "extraction_fields": [
    {
      "name": "invoice_number",
      "bbox": [100, 200, 300, 220],
      "page": 1
    }
  ],
  "pipeline_definition_id": 999  // ← Use this to fetch pipeline separately
}
```

**Status**: ✅ Works perfectly

---

### 2. GET Pipeline Definition ✅
**Endpoint**: `GET /pipelines/{id}`

**File**: `server-new/src/api/routers/pipelines.py` (lines 84-98)

**Code**:
```python
@router.get("/{id}", response_model=PipelineDetail)
async def get_pipeline(
    id: int,
    pipeline_service: PipelineService = Depends(
        lambda: ServiceContainer.get_pipeline_service()
    )
) -> PipelineDetail:
    """
    Get complete pipeline definition including pipeline_state and visual_state.

    Returns full pipeline data for visualization/editing.
    """
    pipeline = pipeline_service.get_pipeline_definition(id)
    return convert_pipeline_detail(pipeline)
```

**Response** (`PipelineDetail` - lines 83-88 in `api/schemas/pipelines.py`):
```json
{
  "id": 999,
  "compiled_plan_id": 12,
  "pipeline_state": {
    "entry_points": [
      {
        "node_id": "ep_1",
        "name": "Invoice Data"
      }
    ],
    "modules": [
      {
        "module_instance_id": "mod_1",
        "module_ref": "text_cleaner:1.0.0",
        "config": {...},
        "inputs": [...],
        "outputs": [...]
      }
    ],
    "connections": [
      {
        "from_node_id": "ep_1",
        "to_node_id": "mod_1_in_0"
      }
    ]
  },
  "visual_state": {
    "modules": {
      "mod_1": {"x": 300, "y": 200}
    },
    "entry_points": {
      "ep_1": {"x": 100, "y": 200}
    }
  }
}
```

**Status**: ✅ Works perfectly - Returns exactly what we need!

---

## Frontend Integration Pattern

### Template Edit Flow

```typescript
// In TemplateDetailModal.tsx

const handleEditClick = async () => {
  if (!template || !versionDetail) return;

  try {
    // Step 1: Version data already loaded (includes pipeline_definition_id)
    const { signature_objects, extraction_fields, pipeline_definition_id } = versionDetail;

    // Step 2: Fetch pipeline data separately
    const pipelineResponse = await fetch(
      `${API_CONFIG.ENDPOINTS.PIPELINES}/${pipeline_definition_id}`
    );

    if (!pipelineResponse.ok) {
      throw new Error('Failed to load pipeline data');
    }

    const pipelineData = await pipelineResponse.json();

    // Step 3: Open template builder with all initial data
    setIsEditMode(true);
    setEditInitialData({
      signatureObjects: signature_objects,
      extractionFields: extraction_fields,
      pipelineState: pipelineData.pipeline_state,
      visualState: pipelineData.visual_state,
    });

  } catch (error) {
    console.error('Failed to load template edit data:', error);
    alert('Failed to load template data for editing');
  }
};
```

### API Hook Example

```typescript
// In useTemplatesApi.ts

const loadTemplateForEditing = async (versionId: number) => {
  // Fetch version data
  const versionResponse = await apiClient.get(
    `${API_CONFIG.ENDPOINTS.TEMPLATES}/versions/${versionId}`
  );
  const versionData = versionResponse.data;

  // Fetch pipeline data
  const pipelineResponse = await apiClient.get(
    `${API_CONFIG.ENDPOINTS.PIPELINES}/${versionData.pipeline_definition_id}`
  );
  const pipelineData = pipelineResponse.data;

  return {
    signatureObjects: versionData.signature_objects,
    extractionFields: versionData.extraction_fields,
    pipelineState: pipelineData.pipeline_state,
    visualState: pipelineData.visual_state,
    sourcePdfId: versionData.source_pdf_id,
  };
};
```

---

## Endpoint URLs

### Development
```
GET http://localhost:8090/api/pdf-templates/versions/{version_id}
GET http://localhost:8090/api/pipelines/{pipeline_definition_id}
```

### Production
```
GET https://api.yourapp.com/api/pdf-templates/versions/{version_id}
GET https://api.yourapp.com/api/pipelines/{pipeline_definition_id}
```

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     Template Edit Flow                           │
└─────────────────────────────────────────────────────────────────┘

User clicks "Edit" button
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ GET /pdf-templates/versions/{version_id}                        │
│                                                                   │
│ Returns:                                                          │
│   - signature_objects                                            │
│   - extraction_fields                                            │
│   - pipeline_definition_id = 999                                │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ GET /pipelines/999                                               │
│                                                                   │
│ Returns:                                                          │
│   - pipeline_state (entry_points, modules, connections)         │
│   - visual_state (module positions, entry point positions)      │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ Open TemplateBuilderModal                                        │
│                                                                   │
│ Props:                                                            │
│   - mode="edit"                                                  │
│   - initialSignatureObjects={signature_objects}                 │
│   - initialExtractionFields={extraction_fields}                 │
│   - initialPipelineState={pipeline_state}                       │
│   - initialVisualState={visual_state}                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Benefits of This Architecture

### 1. Performance ✅
- Template version list loads fast (no heavy pipeline data)
- Pipeline data only fetched when user clicks "Edit"
- Can paginate version list without affecting performance

### 2. Separation of Concerns ✅
- `/pdf-templates/versions` → Template-specific data
- `/pipelines` → Pipeline-specific data
- Clean API boundaries

### 3. Reusability ✅
- Same `/pipelines/{id}` endpoint used by:
  - Template editor
  - Standalone pipeline viewer
  - Pipeline debugging tools

### 4. Caching ✅
- Version data can be cached separately
- Pipeline definitions shared across templates cached once
- Reduces duplicate data transfer

### 5. Flexibility ✅
- Easy to add more version fields without affecting pipeline API
- Easy to add more pipeline fields without affecting version API
- Independent versioning of both APIs

---

## Testing Checklist

### ✅ Backend Verification Complete
- [x] Verify `GET /pdf-templates/versions/{version_id}` exists
- [x] Verify response includes `pipeline_definition_id`
- [x] Verify `GET /pipelines/{id}` exists
- [x] Verify response includes `pipeline_state`
- [x] Verify response includes `visual_state`
- [x] Confirm data structure matches requirements

### 🎯 Frontend Implementation (Next Steps)
- [ ] Add pipeline fetch logic to template detail modal
- [ ] Update TemplateBuilderModal to accept initial pipeline state
- [ ] Handle loading states during data fetch
- [ ] Handle errors gracefully
- [ ] Test full edit flow end-to-end

---

## Example: Complete API Calls

```bash
# Step 1: Get template version
curl http://localhost:8090/api/pdf-templates/versions/5

# Response:
{
  "version_id": 5,
  "template_id": 2,
  "version_num": 3,
  "source_pdf_id": 7,
  "is_current": true,
  "signature_objects": {...},
  "extraction_fields": [...],
  "pipeline_definition_id": 12  // ← Use this
}

# Step 2: Get pipeline definition
curl http://localhost:8090/api/pipelines/12

# Response:
{
  "id": 12,
  "compiled_plan_id": 8,
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

## Conclusion

✅ **Backend is 100% ready for template editing feature**

**No changes needed**. All required endpoints exist and return the correct data.

**Next step**: Implement frontend changes to:
1. Fetch pipeline data when user clicks "Edit"
2. Pass initial data to TemplateBuilderModal
3. Handle the two-step API call pattern

Estimated frontend implementation time: **4-6 hours** (as per original plan)
