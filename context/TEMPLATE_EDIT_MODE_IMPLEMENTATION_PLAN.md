# Template Edit Mode Implementation Plan

## Executive Summary

**Objective**: Enable editing existing templates by opening a TemplateBuilderModal pre-populated with template version data.

**Approach**: Option 2 - Modify `TemplateBuilderModal` to accept initial state and operate in two modes: `create` or `edit`.

**Backend Status**: ✅ **READY** - All required endpoints exist
**Estimated Time**: 4-6 hours (frontend only)

---

## Backend API Analysis

### Existing Endpoints - COMPLETE ✅

#### 1. Get Template Version Data
```
GET /pdf_templates/{template_id}/versions/{version_id}
Response: PdfTemplateVersion
  - id: number
  - pdf_template_id: number
  - version_num: number
  - source_pdf_id: number
  - signature_objects: PdfObjects (nested structure)
  - extraction_fields: ExtractionField[]
  - pipeline_state: PipelineState
  - visual_state: VisualState
  - signature_object_count: number
  - created_at: string
  - last_used_at: string | null
```

#### 2. Create New Template Version
```
POST /pdf_templates/{template_id}/versions
Request Body: PdfTemplateVersionCreateRequest
  - signature_objects: PdfObjects
  - extraction_fields: ExtractionField[]
  - signature_object_count: number

Response: PdfTemplateVersion
```

**Note**: The current endpoint does NOT accept `pipeline_state` or `visual_state`. See "Backend Gaps" section below.

### Backend Gaps - NEEDS FIXING ⚠️

**CRITICAL ISSUE**: The `PdfTemplateVersionCreateRequest` schema is missing pipeline fields!

**Current Schema** (`server/src/api/schemas/pdf_templates.py` lines 10-14):
```python
class PdfTemplateVersionCreateRequest(BaseModel):
    signature_objects: PdfObjects
    extraction_fields: List[ExtractionField]
    signature_object_count: int
```

**Required Schema** (needs to be added):
```python
class PdfTemplateVersionCreateRequest(BaseModel):
    signature_objects: PdfObjects
    extraction_fields: List[ExtractionField]
    signature_object_count: int
    pipeline_state: Optional[PipelineState] = None  # ADD THIS
    visual_state: Optional[VisualState] = None      # ADD THIS
```

**Also Update**: `server/src/shared/types/pdf_templates.py`
```python
@dataclass
class PdfTemplateVersionCreate:
    pdf_template_id: int
    signature_objects: PdfObjects
    extraction_fields: List[ExtractionField]
    pipeline_state: Optional[PipelineState] = None  # ADD THIS
    visual_state: Optional[VisualState] = None      # ADD THIS
```

**Repository Update**: `server/src/shared/database/repositories/pdf_template_version.py`
- Update `create()` method to handle `pipeline_state` and `visual_state` fields
- Store them in `pipeline_state_json` and `visual_state_json` columns

---

## Implementation Plan

### Phase 1: Backend Updates (30 minutes)

#### Step 1.1: Update API Schema
**File**: `server/src/api/schemas/pdf_templates.py`

```python
from typing import Optional
from shared.types import PipelineState, VisualState

class PdfTemplateVersionCreateRequest(BaseModel):
    """Request to create a new template version"""
    signature_objects: PdfObjects = Field(..., min_length=1, description="Objects for template matching")
    extraction_fields: List[ExtractionField] = Field(default_factory=list, description="Fields to extract")
    signature_object_count: int = Field(..., ge=1, description="Count of signature objects")
    pipeline_state: Optional[PipelineState] = Field(None, description="Pipeline configuration for this version")
    visual_state: Optional[VisualState] = Field(None, description="Visual layout for pipeline nodes")
```

#### Step 1.2: Update Domain Type
**File**: `server/src/shared/types/pdf_templates.py`

```python
@dataclass
class PdfTemplateVersionCreate:
    pdf_template_id: int
    signature_objects: PdfObjects
    extraction_fields: List[ExtractionField]
    pipeline_state: Optional[PipelineState] = None
    visual_state: Optional[VisualState] = None
```

#### Step 1.3: Update Router Mapper
**File**: `server/src/api/routers/pdf_templates.py` (line 126-130)

```python
# Create domain model, adding pdf_template_id from URL parameter
version_create = PdfTemplateVersionCreate(
    pdf_template_id=template_id,
    signature_objects=request_data.signature_objects,
    extraction_fields=request_data.extraction_fields,
    pipeline_state=request_data.pipeline_state,  # ADD THIS
    visual_state=request_data.visual_state        # ADD THIS
)
```

#### Step 1.4: Update Repository
**File**: `server/src/shared/database/repositories/pdf_template_version.py`

Update `create()` method to serialize and store pipeline states:

```python
def create(self, version_create: PdfTemplateVersionCreate) -> PdfTemplateVersion:
    # ... existing code ...

    # Serialize pipeline states to JSON
    pipeline_state_json = None
    if version_create.pipeline_state:
        pipeline_state_json = json.dumps({
            'entry_points': [asdict(ep) for ep in version_create.pipeline_state.entry_points],
            'modules': [asdict(m) for m in version_create.pipeline_state.modules],
            'connections': [asdict(c) for c in version_create.pipeline_state.connections]
        })

    visual_state_json = None
    if version_create.visual_state:
        visual_state_json = json.dumps(version_create.visual_state)

    # Create database record
    new_version = PdfTemplateVersionModel(
        # ... existing fields ...
        pipeline_state_json=pipeline_state_json,
        visual_state_json=visual_state_json,
        # ... rest of fields ...
    )
```

**Test**:
```bash
# After changes, test endpoint
curl -X POST http://localhost:8090/pdf_templates/1/versions \
  -H "Content-Type: application/json" \
  -d '{
    "signature_objects": {...},
    "extraction_fields": [...],
    "signature_object_count": 5,
    "pipeline_state": {...},
    "visual_state": {...}
  }'
```

---

### Phase 2: Frontend TemplateBuilderModal Updates (2-3 hours)

#### Step 2.1: Add Mode and Initial State Props
**File**: `client/src/renderer/features/templates/components/builder/TemplateBuilderModal.tsx`

**Changes to interface** (lines 17-34):
```typescript
interface TemplateBuilderModalProps {
  isOpen: boolean;
  pdfFileId: number | null;
  pdfFile: File | null;
  onClose: () => void;
  onSave: (templateData: TemplateData) => Promise<void>;

  // NEW: Edit mode support
  mode?: 'create' | 'edit';
  templateId?: number;
  templateVersionId?: number;
  initialTemplateName?: string;
  initialTemplateDescription?: string;
  initialSignatureObjects?: {
    text_words: any[];
    text_lines: any[];
    graphic_rects: any[];
    graphic_lines: any[];
    graphic_curves: any[];
    images: any[];
    tables: any[];
  };
  initialExtractionFields?: ExtractionField[];
  initialPipelineState?: PipelineState;
  initialVisualState?: VisualState;
}
```

**Add default props** (in function signature):
```typescript
export function TemplateBuilderModal({
  isOpen,
  pdfFileId,
  pdfFile,
  onClose,
  onSave,
  mode = 'create',  // Default to create mode
  templateId,
  templateVersionId,
  initialTemplateName = '',
  initialTemplateDescription = '',
  initialSignatureObjects,
  initialExtractionFields,
  initialPipelineState,
  initialVisualState,
}: TemplateBuilderModalProps) {
  // ... component body
}
```

#### Step 2.2: Initialize State from Props
**File**: Same file, update state initialization (lines 46-75)

```typescript
// Initialize from props (for edit mode) or empty (for create mode)
const [templateName, setTemplateName] = useState(initialTemplateName);
const [templateDescription, setTemplateDescription] = useState(initialTemplateDescription);
const [signatureObjects, setSignatureObjects] = useState(
  initialSignatureObjects || {
    text_words: [],
    text_lines: [],
    graphic_rects: [],
    graphic_lines: [],
    graphic_curves: [],
    images: [],
    tables: [],
  }
);
const [extractionFields, setExtractionFields] = useState<ExtractionField[]>(
  initialExtractionFields || []
);
const [pipelineState, setPipelineState] = useState<PipelineState>(
  initialPipelineState || {
    entry_points: [],
    modules: [],
    connections: [],
  }
);
const [visualState, setVisualStateInternal] = useState<VisualState>(
  initialVisualState || {
    modules: {},
    entryPoints: {},
  }
);

// Reset state when modal opens/closes or initial data changes
useEffect(() => {
  if (isOpen) {
    setTemplateName(initialTemplateName || '');
    setTemplateDescription(initialTemplateDescription || '');
    setSignatureObjects(initialSignatureObjects || {
      text_words: [],
      text_lines: [],
      graphic_rects: [],
      graphic_lines: [],
      graphic_curves: [],
      images: [],
      tables: [],
    });
    setExtractionFields(initialExtractionFields || []);
    setPipelineState(initialPipelineState || {
      entry_points: [],
      modules: [],
      connections: [],
    });
    setVisualStateInternal(initialVisualState || {
      modules: {},
      entryPoints: {},
    });
  }
}, [isOpen, initialTemplateName, initialTemplateDescription, initialSignatureObjects, initialExtractionFields, initialPipelineState, initialVisualState]);
```

#### Step 2.3: Update Header to Show Mode
**File**: `client/src/renderer/features/templates/components/builder/components/TemplateBuilderHeader.tsx`

Add mode prop and update title:

```typescript
interface TemplateBuilderHeaderProps {
  templateName: string;
  onTemplateNameChange: (name: string) => void;
  onClose: () => void;
  mode?: 'create' | 'edit';
}

export function TemplateBuilderHeader({
  templateName,
  onTemplateNameChange,
  onClose,
  mode = 'create',
}: TemplateBuilderHeaderProps) {
  const title = mode === 'edit' ? 'Edit Template' : 'Create Template';

  return (
    <div className="...">
      <h2>{title}</h2>
      {/* ... rest of component */}
    </div>
  );
}
```

#### Step 2.4: Update Save Logic to Handle Edit Mode
**File**: `client/src/renderer/features/templates/components/builder/TemplateBuilderModal.tsx`

Find the save handler and update it to differentiate between create and edit:

```typescript
const handleSave = async () => {
  setIsSaving(true);
  try {
    const templateData: TemplateData = {
      name: templateName,
      description: templateDescription,
      source_pdf_id: pdfFileId,
      pdf_file: pdfFile,
      signature_objects: Object.values(signatureObjects).flat(),
      extraction_fields: extractionFields,
      pipeline_state: pipelineState,
      visual_state: visualState,
    };

    // NEW: Add mode information
    const dataWithMode = {
      ...templateData,
      mode,
      templateId,
      templateVersionId,
    };

    await onSave(dataWithMode);
    onClose();
  } catch (error) {
    console.error('Failed to save template:', error);
    alert(`Failed to save template: ${error instanceof Error ? error.message : 'Unknown error'}`);
  } finally {
    setIsSaving(false);
  }
};
```

**Note**: The actual API call will be handled by the parent component.

---

### Phase 3: TemplateDetailModal Integration (1-2 hours)

#### Step 3.1: Add State for Edit Mode
**File**: `client/src/renderer/features/templates/components/modals/TemplateDetailModal.tsx`

```typescript
export function TemplateDetailModal({
  isOpen,
  templateId,
  onClose,
  onEdit,
}: TemplateDetailModalProps) {
  // ... existing state ...

  // NEW: Edit mode state
  const [isEditMode, setIsEditMode] = useState(false);

  // ... rest of component
}
```

#### Step 3.2: Create Edit Handler
**File**: Same file

```typescript
const handleEditClick = () => {
  if (!template || !versionDetail) {
    console.error('No template or version data available for editing');
    return;
  }

  setIsEditMode(true);
};

const handleEditClose = () => {
  setIsEditMode(false);
  // Optionally refresh template data
  if (templateId) {
    fetchTemplateData(templateId);
  }
};

const handleEditSave = async (templateData: any) => {
  if (!template || !templateId) return;

  try {
    // Call API to create new version
    await createTemplateVersion(templateId, {
      signature_objects: templateData.signature_objects,
      extraction_fields: templateData.extraction_fields,
      signature_object_count: templateData.signature_objects.length,
      pipeline_state: templateData.pipeline_state,
      visual_state: templateData.visual_state,
    });

    // Close edit modal and refresh
    setIsEditMode(false);
    fetchTemplateData(templateId);

    alert('New template version created successfully!');
  } catch (error) {
    console.error('Failed to create template version:', error);
    throw error; // Let TemplateBuilderModal handle the error
  }
};
```

#### Step 3.3: Update Edit Button
**File**: Same file, find the Edit button (around line 200-250)

```typescript
<button
  onClick={handleEditClick}
  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors"
>
  Edit
</button>
```

#### Step 3.4: Render TemplateBuilderModal Conditionally
**File**: Same file, add at the end of return statement (before the final closing div)

```typescript
return (
  <>
    {!isOpen && <div>...</div> /* Existing modal content */}

    {/* Edit Mode: Render TemplateBuilderModal */}
    {isEditMode && versionDetail && (
      <TemplateBuilderModal
        isOpen={isEditMode}
        pdfFileId={versionDetail.source_pdf_id}
        pdfFile={null}
        onClose={handleEditClose}
        onSave={handleEditSave}
        mode="edit"
        templateId={template?.id}
        templateVersionId={versionDetail.id}
        initialTemplateName={template?.name || ''}
        initialTemplateDescription={template?.description || ''}
        initialSignatureObjects={versionDetail.signature_objects}
        initialExtractionFields={versionDetail.extraction_fields}
        initialPipelineState={versionDetail.pipeline_state}
        initialVisualState={versionDetail.visual_state}
      />
    )}
  </>
);
```

---

### Phase 4: API Hook Updates (30 minutes)

#### Step 4.1: Add Create Version Method
**File**: `client/src/renderer/features/templates/hooks/useTemplatesApi.ts`

```typescript
const createTemplateVersion = async (
  templateId: number,
  versionData: {
    signature_objects: any;
    extraction_fields: ExtractionField[];
    signature_object_count: number;
    pipeline_state?: PipelineState;
    visual_state?: VisualState;
  }
) => {
  setIsLoading(true);
  setError(null);

  try {
    const response = await apiClient.post(
      `${API_CONFIG.ENDPOINTS.TEMPLATES}/${templateId}/versions`,
      versionData
    );
    return response.data;
  } catch (err) {
    const errorMessage = err instanceof Error ? err.message : 'Failed to create template version';
    setError(errorMessage);
    throw err;
  } finally {
    setIsLoading(false);
  }
};

// Export it
return {
  // ... existing exports
  createTemplateVersion,
};
```

---

### Phase 5: Type Definitions (15 minutes)

#### Step 5.1: Update TemplateData Type
**File**: `client/src/renderer/features/templates/components/builder/TemplateBuilderModal.tsx`

```typescript
export interface TemplateData {
  name: string;
  description: string;
  source_pdf_id?: number | null;
  pdf_file?: File | null;
  signature_objects: SignatureObject[];
  extraction_fields: ExtractionField[];
  pipeline_state: PipelineState;
  visual_state: VisualState;

  // NEW: Edit mode metadata
  mode?: 'create' | 'edit';
  templateId?: number;
  templateVersionId?: number;
}
```

---

### Phase 6: Edge Cases & Polish (1 hour)

#### Step 6.1: Handle Step 1 Pre-selection
When in edit mode, Step 1 (Signature Objects) should show the existing signature objects as already selected.

**File**: `client/src/renderer/features/templates/components/builder/steps/SignatureObjectsStep.tsx`

- Accept `initialSelectedObjects` prop
- Initialize `selectedObjects` state from this prop
- Mark pre-selected objects as selected in the UI

#### Step 6.2: Prevent Accidental Data Loss
Add confirmation dialog when closing edit mode with unsaved changes:

```typescript
const handleEditClose = () => {
  const hasChanges = /* detect if any state has changed */;

  if (hasChanges) {
    const confirm = window.confirm(
      'You have unsaved changes. Are you sure you want to close?'
    );
    if (!confirm) return;
  }

  setIsEditMode(false);
};
```

#### Step 6.3: Success/Error Feedback
- Show success toast/alert when new version created
- Update version list to show the new version
- Auto-select the newly created version

#### Step 6.4: Disable Edit Button When Needed
Disable edit button if:
- Template is inactive
- Version data is still loading
- User doesn't have permission (future)

---

## Testing Plan

### Backend Tests

1. **Test creating template version without pipeline data**
   ```bash
   POST /pdf_templates/1/versions
   Body: { signature_objects: {...}, extraction_fields: [...], signature_object_count: 5 }
   Expected: 201 Created, pipeline_state and visual_state should be null
   ```

2. **Test creating template version with pipeline data**
   ```bash
   POST /pdf_templates/1/versions
   Body: {
     signature_objects: {...},
     extraction_fields: [...],
     signature_object_count: 5,
     pipeline_state: {...},
     visual_state: {...}
   }
   Expected: 201 Created, all fields stored correctly
   ```

3. **Test GET version returns pipeline data**
   ```bash
   GET /pdf_templates/1/versions/2
   Expected: Response includes pipeline_state and visual_state
   ```

### Frontend Tests

1. **Create Mode (existing functionality)**
   - Open template builder with no initial data
   - All fields should be empty
   - Save creates new template

2. **Edit Mode - Load Data**
   - Click "Edit" on a template version
   - Template builder should open with:
     - Template name and description pre-filled
     - Signature objects pre-selected in Step 1
     - Extraction fields visible in Step 2
     - Pipeline pre-built in Step 3
     - Visual state positions preserved

3. **Edit Mode - Modify Data**
   - Change template name → should persist
   - Add/remove signature objects → should update
   - Add/remove extraction fields → should update
   - Modify pipeline → should update
   - Save → should create new version

4. **Edit Mode - Save**
   - Save edited template
   - Verify new version appears in version list
   - Verify new version has incremented version_num
   - Verify original version is unchanged

5. **Edge Cases**
   - Close without saving → data should be discarded
   - Edit template with no pipeline → should handle gracefully
   - Edit template with complex pipeline → all nodes should restore

---

## Data Flow Diagrams

### Create Mode (Existing)
```
User → TemplateBuilderModal (empty state)
  → User fills data
  → Save
  → POST /pdf_templates
  → Creates template + version 1
```

### Edit Mode (New)
```
User → TemplateDetailModal (viewing version 5)
  → Click "Edit"
  → TemplateBuilderModal (pre-filled with version 5 data)
  → User modifies data
  → Save
  → POST /pdf_templates/{id}/versions
  → Creates version 6
  → TemplateDetailModal refreshes, shows version 6
```

---

## Risks & Mitigation

### Risk 1: Pipeline State Deserialization Issues
**Problem**: PipelineState might not deserialize correctly from JSON
**Mitigation**: Add validation and error handling when loading initial state

### Risk 2: Large Signature Object Sets
**Problem**: Templates with 100+ signature objects might be slow to render
**Mitigation**: Use pagination or virtualization in Step 1

### Risk 3: Concurrent Edits
**Problem**: Two users editing the same template simultaneously
**Mitigation**: Version-based system already handles this - both edits create separate versions

### Risk 4: PDF File Not Available
**Problem**: Original PDF file might be deleted from storage
**Mitigation**: Check if `source_pdf_id` is valid before opening edit mode

---

## Summary Checklist

### Backend ✅
- [x] Analyze existing endpoints → **All endpoints exist**
- [ ] Add `pipeline_state` and `visual_state` to `PdfTemplateVersionCreateRequest`
- [ ] Add `pipeline_state` and `visual_state` to `PdfTemplateVersionCreate` domain type
- [ ] Update repository to serialize/deserialize pipeline states
- [ ] Test endpoint with and without pipeline data

### Frontend
- [ ] Add mode prop to `TemplateBuilderModal`
- [ ] Add initial state props for all fields
- [ ] Initialize state from props
- [ ] Update header to show "Edit Template"
- [ ] Update save logic to call correct endpoint
- [ ] Add edit button handler in `TemplateDetailModal`
- [ ] Render `TemplateBuilderModal` conditionally
- [ ] Add `createTemplateVersion` to API hook
- [ ] Test create mode (should work unchanged)
- [ ] Test edit mode with various templates
- [ ] Add unsaved changes confirmation
- [ ] Add success/error feedback
- [ ] Handle edge cases (missing data, etc.)

---

## Estimated Timeline

| Phase | Task | Time |
|-------|------|------|
| 1 | Backend schema updates | 30 min |
| 2 | TemplateBuilderModal props & state | 2-3 hours |
| 3 | TemplateDetailModal integration | 1-2 hours |
| 4 | API hook updates | 30 min |
| 5 | Type definitions | 15 min |
| 6 | Edge cases & polish | 1 hour |
| **Total** | | **4-6 hours** |

---

## Next Steps

1. **Wait for user confirmation** to proceed with implementation
2. **Start with Phase 1** (backend updates) - this is critical
3. **Test backend changes** before moving to frontend
4. **Implement frontend phases incrementally** - test after each phase
5. **User testing** - have user test edit workflow thoroughly
