# Backend Analysis: Creating New Template Versions

## Summary: Backend is COMPLETE ✅

The `PUT /pdf-templates/{id}` endpoint handles creating new template versions when editing.

---

## How It Works

### Endpoint
```
PUT /pdf-templates/{id}
```

**File**: `server-new/src/api/routers/pdf_templates.py` (lines 112-138)

### Request Schema ✅

**File**: `server-new/src/api/schemas/pdf_templates.py` (lines 68-76)

```python
class UpdatePdfTemplateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    signature_objects: Optional[PdfObjects] = None          # ✅
    extraction_fields: Optional[List[ExtractionField]] = None  # ✅
    pipeline_state: Optional[PipelineState] = None          # ✅
    visual_state: Optional[VisualState] = None              # ✅
```

**Status**: ✅ **All fields we need are already supported**

---

## Smart Versioning Logic

**File**: `server-new/src/features/pdf_templates/service.py` (lines 166-265)

The `update_template()` service method has intelligent branching:

### Case 1: Metadata Only
```python
# Only name or description changed
→ Update template record (no new version)
→ Return existing version_num and pipeline_id
```

### Case 2: Wizard Data Changed
```python
# signature_objects OR extraction_fields OR pipeline_state/visual_state changed
→ Create new pipeline definition (if pipeline changed)
→ Create new template version
→ Update template.current_version_id
→ Return new version_num and pipeline_id
```

**Rules**:
- ✅ Can only update wizard data if template is **inactive**
- ✅ If `pipeline_state` is provided, `visual_state` MUST also be provided (and vice versa)
- ✅ All changes are atomic (uses unit-of-work pattern)

---

## Frontend Usage: Template Edit Flow

### Step 1: User Opens Template for Editing

```typescript
// GET version data
const versionResponse = await fetch(`/api/pdf-templates/versions/${versionId}`);
const versionData = await versionResponse.json();
// Returns: signature_objects, extraction_fields, pipeline_definition_id

// GET pipeline data
const pipelineResponse = await fetch(`/api/pipelines/${versionData.pipeline_definition_id}`);
const pipelineData = await pipelineResponse.json();
// Returns: pipeline_state, visual_state

// Open TemplateBuilderModal
<TemplateBuilderModal
  mode="edit"
  templateId={templateId}
  initialSignatureObjects={versionData.signature_objects}
  initialExtractionFields={versionData.extraction_fields}
  initialPipelineState={pipelineData.pipeline_state}
  initialVisualState={pipelineData.visual_state}
/>
```

### Step 2: User Edits and Saves

```typescript
const handleSave = async (editedData) => {
  try {
    // PUT to update template (creates new version automatically)
    const response = await fetch(`/api/pdf-templates/${templateId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        // Include ALL wizard data fields (even if unchanged)
        signature_objects: editedData.signature_objects,
        extraction_fields: editedData.extraction_fields,
        pipeline_state: editedData.pipeline_state,
        visual_state: editedData.visual_state,
      }),
    });

    if (!response.ok) {
      throw new Error('Failed to save template');
    }

    const updatedTemplate = await response.json();

    // Success! New version created
    console.log('New version created:', updatedTemplate.current_version.version_num);

    // Close modal and refresh
    onClose();
    refreshTemplateData();

  } catch (error) {
    console.error('Failed to save:', error);
    alert('Failed to save template');
  }
};
```

---

## Important Notes

### 1. Template Must Be Inactive ⚠️

**Rule**: Cannot update wizard data (signature_objects, extraction_fields, pipeline) if template status is "active".

**Error Response**:
```json
{
  "status": 409,
  "detail": "Template 123 is active. Deactivate first before updating wizard data."
}
```

**Frontend Handling**:
```typescript
// Before allowing edit, check template status
if (template.status === 'active') {
  // Option A: Show warning and require deactivation
  alert('This template is active. Deactivate it first to edit.');

  // Option B: Auto-deactivate with confirmation
  if (confirm('This template is active. Deactivate to edit?')) {
    await fetch(`/api/pdf-templates/${templateId}/deactivate`, { method: 'POST' });
    // Then proceed with edit
  }
}
```

### 2. Pipeline Fields Must Be Together ⚠️

**Rule**: If you provide `pipeline_state`, you MUST also provide `visual_state` (and vice versa).

**Error Response**:
```json
{
  "status": 400,
  "detail": "Both pipeline_state and visual_state must be provided when updating pipeline"
}
```

**Frontend Handling**:
```typescript
// Always include BOTH pipeline fields when saving
const updatePayload = {
  signature_objects: editedData.signature_objects,
  extraction_fields: editedData.extraction_fields,
  pipeline_state: editedData.pipeline_state,    // ✅ Both
  visual_state: editedData.visual_state,        // ✅ Both
};
```

### 3. Only Send Changed Fields (Optional Optimization)

You CAN send only the fields that changed:

```typescript
// Minimal update (only pipeline changed)
const updatePayload = {
  pipeline_state: editedData.pipeline_state,
  visual_state: editedData.visual_state,
};

// This creates new version with NEW pipeline, but SAME signature_objects and extraction_fields
```

**However**, for template editing, it's **safer and simpler** to always send all wizard data fields to ensure consistency.

---

## API Request Examples

### Example 1: Edit All Fields

```bash
PUT /api/pdf-templates/123
Content-Type: application/json

{
  "signature_objects": {
    "text_words": [
      {"page": 1, "bbox": [100, 200, 300, 220], "text": "INVOICE", ...}
    ],
    "text_lines": [],
    ...
  },
  "extraction_fields": [
    {
      "name": "invoice_number",
      "description": "Invoice ID",
      "bbox": [100, 250, 200, 270],
      "page": 1
    }
  ],
  "pipeline_state": {
    "entry_points": [{"node_id": "ep1", "name": "Invoice Data"}],
    "modules": [...],
    "connections": [...]
  },
  "visual_state": {
    "modules": {"mod1": {"x": 300, "y": 200}},
    "entry_points": {"ep1": {"x": 100, "y": 200}}
  }
}
```

**Response** (200 OK):
```json
{
  "id": 123,
  "name": "Invoice Template",
  "status": "inactive",
  "current_version_id": 456,  // ← NEW version created
  "versions": [
    {"version_id": 456, "version_number": 4},  // ← NEW
    {"version_id": 455, "version_number": 3},
    {"version_id": 454, "version_number": 2},
    {"version_id": 453, "version_number": 1}
  ]
}
```

### Example 2: Only Update Metadata (No New Version)

```bash
PUT /api/pdf-templates/123
Content-Type: application/json

{
  "name": "Updated Invoice Template Name",
  "description": "New description"
}
```

**Response**: Same template, same version (no new version created)

---

## Error Handling

### 404: Template Not Found
```json
{
  "status": 404,
  "detail": "Template 123 not found"
}
```

### 409: Template is Active
```json
{
  "status": 409,
  "detail": "Template 123 is active. Deactivate first before updating wizard data."
}
```

### 400: Incomplete Pipeline Data
```json
{
  "status": 400,
  "detail": "Both pipeline_state and visual_state must be provided when updating pipeline"
}
```

### 400: Pipeline Validation Failed
```json
{
  "status": 400,
  "detail": "Pipeline validation failed: Missing required input on module mod_1"
}
```

---

## Database Operations (Under the Hood)

When you `PUT` with wizard data changes, the service:

1. **Validates** template exists and is inactive
2. **Detects** what changed (pipeline vs signature vs extraction)
3. **If pipeline changed**:
   - Validates pipeline structure
   - Compiles pipeline
   - Creates `pipeline_definitions` record
   - Gets `pipeline_definition_id`
4. **Creates new version**:
   - Inserts into `pdf_template_versions` table
   - Auto-increments `version_num`
   - Links to `pipeline_definition_id`
5. **Updates template**:
   - Sets `current_version_id` to new version
   - Commits transaction atomically

All operations use **unit-of-work pattern** (atomic transaction).

---

## Testing the Endpoint

```bash
# Step 1: Create a template
curl -X POST http://localhost:8090/api/pdf-templates \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Template",
    "description": "Test",
    "source_pdf_id": 1,
    "signature_objects": {...},
    "extraction_fields": [...],
    "pipeline_state": {...},
    "visual_state": {...}
  }'

# Response includes template.id (e.g., 123)
# And current_version_id (e.g., 456)
# Version 1 is created automatically

# Step 2: Deactivate template (if it's active)
curl -X POST http://localhost:8090/api/pdf-templates/123/deactivate

# Step 3: Edit template (creates version 2)
curl -X PUT http://localhost:8090/api/pdf-templates/123 \
  -H "Content-Type: application/json" \
  -d '{
    "signature_objects": {...},  // Modified
    "extraction_fields": [...],  // Modified
    "pipeline_state": {...},     // Modified
    "visual_state": {...}        // Modified
  }'

# Response includes new current_version_id (e.g., 457)
# Version 2 is now created

# Step 4: Verify new version exists
curl http://localhost:8090/api/pdf-templates/versions/457

# Should return the new version data
```

---

## Conclusion

✅ **Backend is 100% ready** - No changes needed

**The endpoint already supports:**
- ✅ Accepting edited signature_objects
- ✅ Accepting edited extraction_fields
- ✅ Accepting edited pipeline_state
- ✅ Accepting edited visual_state
- ✅ Creating new template version automatically
- ✅ Creating new pipeline definition
- ✅ Validating pipeline before creation
- ✅ Atomic transactions (all-or-nothing)
- ✅ Proper error handling

**Frontend just needs to:**
1. Call `PUT /pdf-templates/{id}` with edited data
2. Handle success (new version created)
3. Handle errors (template active, validation failed, etc.)

**Estimated frontend implementation**: 4-6 hours (as per original plan)
