# Feature: Template Draft Saving

## Overview

Allow users to save in-progress templates as drafts, close the builder modal, and return later to complete them.

## Requirements Summary

- **Storage**: Add `draft` status to existing `PdfTemplateStatus` enum (not a separate table)
- **Draft access**: Drafts appear in main template list with a "Draft" badge
- **Save trigger**: Popup on modal close without save, offering "Save as Draft" option
- **Minimum draft data**: name + source_pdf_id (PDF must be uploaded)
- **Page selection**: Locked after step 1, source_pdf_id is immutable once set
- **Draft limits**: None, not user-scoped (system is user-agnostic)
- **Active templates**: Keep current behavior (edits create new versions immediately)
- **Publish flow**: Delete draft, create fresh template via normal `create_template()` logic

---

## Backend Implementation

### 1. Type Changes

**File: `server/src/shared/types/pdf_templates.py`**

```python
# Update the status literal type
PdfTemplateStatus = Literal["draft", "active", "inactive"]
```

### 2. Database Model Changes

**File: `server/src/shared/database/models.py`**

```python
# Update the enum definition
PDF_TEMPLATE_STATUS = SAEnum(
    'draft', 'active', 'inactive',
    name='pdf_template_status',
    native_enum=False,
    validate_strings=True
)
```

Note: Since `native_enum=False`, no database migration is required - the column stores strings.

### 3. Service Methods

**File: `server/src/features/pdf_templates/service.py`**

#### 3.1 `save_draft()`

Creates or updates a draft template with minimal validation.

```python
def save_draft(
    self,
    name: str,
    source_pdf_id: int,
    description: str | None = None,
    customer_id: int | None = None,
    is_autoskip: bool = False,
    signature_objects: list[PdfObject] | None = None,
    extraction_fields: list[ExtractionField] | None = None,
    pipeline_state: dict | None = None,
    visual_state: dict | None = None,
    existing_draft_id: int | None = None,  # For updating existing draft
) -> PdfTemplate:
    """
    Create or update a draft template.

    Draft storage:
    - pdf_templates: name, description, customer_id, source_pdf_id, is_autoskip, status='draft'
    - pipeline_definitions: pipeline_state, visual_state (NO compiled steps)
    - pdf_template_versions: signature_objects, extraction_fields, pipeline_definition_id

    Args:
        name: Template name (required)
        source_pdf_id: PDF file ID (required, immutable after creation)
        description: Optional description
        customer_id: Optional customer reference
        is_autoskip: Whether template auto-skips processing
        signature_objects: PDF objects for template matching (optional for draft)
        extraction_fields: Fields to extract (optional for draft)
        pipeline_state: Raw pipeline state JSON (optional for draft)
        visual_state: Pipeline visual layout JSON (optional for draft)
        existing_draft_id: If provided, update existing draft instead of creating new

    Returns:
        Created or updated draft template

    Raises:
        NotFoundError: If existing_draft_id provided but not found
        ConflictError: If existing_draft_id exists but is not a draft
    """
```

**Implementation details:**
1. If `existing_draft_id` provided:
   - Verify template exists and `status='draft'`
   - Verify `source_pdf_id` matches (immutable)
   - Update template metadata
   - Update or create pipeline_definition (raw state only, no step compilation)
   - Update or create version with signature_objects, extraction_fields
2. If creating new:
   - Verify source_pdf_id exists
   - Create pipeline_definition with raw pipeline_state/visual_state (no steps)
   - Create template with status='draft'
   - Create version 1

#### 3.2 `discard_draft()`

Deletes a draft template and all related records.

```python
def discard_draft(self, template_id: int) -> None:
    """
    Delete a draft template.

    Only allowed for templates with status='draft'. Normal templates
    cannot be deleted (only deactivated).

    Cascades to:
    - pdf_template_versions (via FK cascade)
    - pipeline_definitions (needs explicit delete - version references it)

    Args:
        template_id: ID of draft template to delete

    Raises:
        NotFoundError: If template not found
        ConflictError: If template status is not 'draft'
    """
```

**Implementation details:**
1. Get template by ID
2. Verify `status='draft'`
3. Get version's `pipeline_definition_id` (for cleanup)
4. Delete template (cascades to versions)
5. Delete orphaned pipeline_definition

#### 3.3 `publish_draft()`

Converts a draft to an active template using normal creation logic.

```python
def publish_draft(
    self,
    draft_template_id: int,
    # Same params as create_template():
    name: str,
    source_pdf_id: int,
    signature_objects: list[PdfObject],
    extraction_fields: list[ExtractionField],
    pipeline_state: PipelineState,
    visual_state: dict,
    description: str | None = None,
    customer_id: int | None = None,
    is_autoskip: bool = False,
) -> PdfTemplate:
    """
    Publish a draft template.

    Flow:
    1. Verify draft_template_id exists and status='draft'
    2. Delete draft template (cascades to version, pipeline_definition)
    3. Call create_template() with provided data
    4. Return new active template (different ID than draft)

    The frontend sends all current builder state, which may have changed
    since the draft was loaded. This ensures the published template
    reflects exactly what the user sees in the builder.

    Args:
        draft_template_id: ID of draft to publish (will be deleted)
        name: Template name
        source_pdf_id: PDF file ID
        signature_objects: PDF objects for template matching
        extraction_fields: Fields to extract
        pipeline_state: Pipeline definition state
        visual_state: Pipeline visual layout
        description: Optional description
        customer_id: Optional customer reference
        is_autoskip: Whether template auto-skips processing

    Returns:
        New active template (different ID than draft)

    Raises:
        NotFoundError: If draft not found
        ConflictError: If template status is not 'draft'
        ValidationError: If template data is invalid (from create_template)
    """
```

**Implementation details:**
1. Get template by ID, verify `status='draft'`
2. Call `discard_draft()` to clean up draft records
3. Call existing `create_template()` with all provided data
4. Return new template

### 4. API Endpoints

**File: `server/src/api/routers/pdf_templates.py`**

#### 4.1 Create Draft

```
POST /api/pdf-templates/draft

Request Body:
{
    "name": "My Template",                    // required
    "source_pdf_id": 123,                     // required
    "description": "Work in progress",        // optional
    "customer_id": 456,                       // optional
    "is_autoskip": false,                     // optional, default false
    "signature_objects": [...],               // optional
    "extraction_fields": [...],               // optional
    "pipeline_state": {...},                  // optional
    "visual_state": {...}                     // optional
}

Response: 201 Created
{
    "id": 789,
    "name": "My Template",
    "status": "draft",
    "source_pdf_id": 123,
    ...
}
```

#### 4.2 Update Draft

```
PUT /api/pdf-templates/{id}/draft

Request Body:
{
    // All fields optional except immutable source_pdf_id
    "name": "Updated Name",
    "description": "Updated description",
    "signature_objects": [...],
    "extraction_fields": [...],
    "pipeline_state": {...},
    "visual_state": {...}
}

Response: 200 OK
{
    "id": 789,
    "name": "Updated Name",
    "status": "draft",
    ...
}

Errors:
- 404: Template not found
- 409: Template is not a draft (cannot update non-draft via this endpoint)
```

#### 4.3 Discard Draft

```
DELETE /api/pdf-templates/{id}/draft

Response: 204 No Content

Errors:
- 404: Template not found
- 409: Template is not a draft (cannot delete non-draft templates)
```

#### 4.4 Publish Draft

```
POST /api/pdf-templates/{id}/publish

Request Body:
{
    // Same as POST /api/pdf-templates (create template)
    "name": "My Template",                    // required
    "source_pdf_id": 123,                     // required
    "signature_objects": [...],               // required
    "extraction_fields": [...],               // required (unless autoskip)
    "pipeline_state": {...},                  // required (unless autoskip)
    "visual_state": {...},                    // required
    "description": "Final description",       // optional
    "customer_id": 456,                       // optional
    "is_autoskip": false                      // optional
}

Response: 201 Created
{
    "id": 790,  // NEW ID - draft was deleted
    "name": "My Template",
    "status": "active",
    ...
}

Errors:
- 404: Draft template not found
- 409: Template is not a draft
- 422: Validation error (missing required fields, invalid pipeline, etc.)
```

### 5. API Schemas

**File: `server/src/api/schemas/pdf_templates.py`**

```python
class CreateDraftRequest(BaseModel):
    """Request schema for creating a draft template."""
    name: str = Field(..., min_length=1, max_length=255)
    source_pdf_id: int
    description: str | None = Field(None, max_length=1000)
    customer_id: int | None = None
    is_autoskip: bool = False
    signature_objects: list[PdfObject] | None = None
    extraction_fields: list[ExtractionField] | None = None
    pipeline_state: dict | None = None
    visual_state: dict | None = None


class UpdateDraftRequest(BaseModel):
    """Request schema for updating a draft template."""
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)
    customer_id: int | None = None
    is_autoskip: bool | None = None
    signature_objects: list[PdfObject] | None = None
    extraction_fields: list[ExtractionField] | None = None
    pipeline_state: dict | None = None
    visual_state: dict | None = None


class PublishDraftRequest(BaseModel):
    """Request schema for publishing a draft template.

    Same fields as CreatePdfTemplateRequest - full template data required.
    """
    name: str = Field(..., min_length=1, max_length=255)
    source_pdf_id: int
    description: str | None = Field(None, max_length=1000)
    customer_id: int | None = None
    is_autoskip: bool = False
    signature_objects: list[PdfObject]
    extraction_fields: list[ExtractionField]
    pipeline_state: PipelineState
    visual_state: dict
```

### 6. ETO Matching Verification

**File: `server/src/features/pdf_templates/service.py` (or matching service)**

Verify that template matching queries filter by `status='active'`:

```python
# Should already be filtering, but verify:
templates = self.template_repo.get_active_templates()
# or
templates = self.template_repo.find_all(status="active")
```

---

## Frontend Implementation

### 1. Template List - Draft Badge

**File: `client/src/renderer/features/templates/components/TemplateList/`**

- Check template `status` field
- If `status === 'draft'`, render "Draft" badge (e.g., gray/yellow chip)
- Clicking a draft template opens builder in edit mode

```tsx
{template.status === 'draft' && (
    <Badge variant="outline" color="yellow">Draft</Badge>
)}
```

### 2. Save as Draft Confirmation Popup

**File: `client/src/renderer/features/templates/components/TemplateBuilder/`**

When user closes modal without saving:

```tsx
// On modal close attempt
const handleCloseAttempt = () => {
    if (hasUnsavedChanges) {
        setShowSaveDraftConfirmation(true);
    } else {
        onClose();
    }
};

// Confirmation dialog
<ConfirmationDialog
    open={showSaveDraftConfirmation}
    title="Save as Draft?"
    message="You have unsaved changes. Would you like to save your progress as a draft?"
    confirmLabel="Save Draft"
    cancelLabel="Discard"
    onConfirm={handleSaveAsDraft}
    onCancel={handleDiscardAndClose}
/>
```

**Save as Draft handler:**
```tsx
const handleSaveAsDraft = async () => {
    // If PDF not yet uploaded, upload it first
    let pdfId = sourcePdfId;
    if (!pdfId && selectedPdfFile) {
        const uploaded = await uploadPdf(selectedPdfFile);
        pdfId = uploaded.id;
    }

    // Save draft
    await saveDraft({
        name: templateName,
        source_pdf_id: pdfId,
        description,
        customer_id: customerId,
        is_autoskip: isAutoskip,
        signature_objects: signatureObjects,
        extraction_fields: extractionFields,
        pipeline_state: pipelineState,
        visual_state: visualState,
    });

    onClose();
};
```

### 3. Load Draft Data into Builder

When opening a draft template:

```tsx
// Detect if opening a draft
const isDraft = template?.status === 'draft';

// Load all draft data into builder state
useEffect(() => {
    if (template && isDraft) {
        setTemplateName(template.name);
        setDescription(template.description);
        setCustomerId(template.customer_id);
        setIsAutoskip(template.is_autoskip);
        setSourcePdfId(template.source_pdf_id);

        // Load version data
        if (template.current_version) {
            setSignatureObjects(template.current_version.signature_objects);
            setExtractionFields(template.current_version.extraction_fields);

            // Load pipeline data
            if (template.current_version.pipeline_definition) {
                setPipelineState(template.current_version.pipeline_definition.pipeline_state);
                setVisualState(template.current_version.pipeline_definition.visual_state);
            }
        }
    }
}, [template]);
```

### 4. Lock Step 1 for Drafts

When editing a draft, page selection (step 1) should be locked:

```tsx
// In page selection step
const isPageSelectionLocked = isDraft && sourcePdfId != null;

{isPageSelectionLocked ? (
    <LockedStepIndicator
        message="Page selection is locked for this draft"
        pdfInfo={sourcePdfInfo}
    />
) : (
    <PageSelectionStep ... />
)}
```

### 5. Publish Flow

When saving a draft (completing all steps and clicking Save):

```tsx
const handleSave = async () => {
    if (isDraft && draftTemplateId) {
        // Publish draft - sends all current data
        const newTemplate = await publishDraft(draftTemplateId, {
            name: templateName,
            source_pdf_id: sourcePdfId,
            signature_objects: signatureObjects,
            extraction_fields: extractionFields,
            pipeline_state: pipelineState,
            visual_state: visualState,
            description,
            customer_id: customerId,
            is_autoskip: isAutoskip,
        });

        // Note: newTemplate has different ID than draft
        onSaveSuccess(newTemplate);
    } else {
        // Normal create flow
        await createTemplate(...);
    }
};
```

### 6. API Hooks

**File: `client/src/renderer/features/templates/api/`**

```tsx
// New mutations
export const useSaveDraft = () => useMutation({
    mutationFn: (data: CreateDraftRequest) =>
        api.post('/pdf-templates/draft', data),
});

export const useUpdateDraft = () => useMutation({
    mutationFn: ({ id, data }: { id: number; data: UpdateDraftRequest }) =>
        api.put(`/pdf-templates/${id}/draft`, data),
});

export const useDiscardDraft = () => useMutation({
    mutationFn: (id: number) =>
        api.delete(`/pdf-templates/${id}/draft`),
});

export const usePublishDraft = () => useMutation({
    mutationFn: ({ id, data }: { id: number; data: PublishDraftRequest }) =>
        api.post(`/pdf-templates/${id}/publish`, data),
});
```

---

## Data Flow Diagrams

### Creating a Draft

```
User builds template (steps 1-N) → closes modal
                ↓
        "Save as Draft?" popup
                ↓ Yes
        Upload PDF (if needed)
                ↓
        POST /api/pdf-templates/draft
                ↓
        Backend creates:
        ├─ pipeline_definitions (raw state, no steps)
        ├─ pdf_templates (status='draft')
        └─ pdf_template_versions
                ↓
        Draft saved, modal closes
```

### Resuming a Draft

```
User clicks draft in template list
                ↓
        GET /api/pdf-templates/{id}
        GET /api/pdf-templates/versions/{version_id}
                ↓
        Load data into builder state
                ↓
        Step 1 locked (PDF already selected)
        User continues from step 2+
```

### Publishing a Draft

```
User completes all steps → clicks Save
                ↓
        POST /api/pdf-templates/{draft_id}/publish
        Body: all current builder state
                ↓
        Backend:
        1. Verify draft exists, status='draft'
        2. Delete draft (cascade to version, pipeline_definition)
        3. create_template() with provided data
        4. Return new active template
                ↓
        Frontend receives new template (different ID)
        Modal closes, list refreshes
```

### Discarding a Draft

```
User clicks "Delete" on draft in list
        (or explicit discard action)
                ↓
        DELETE /api/pdf-templates/{id}/draft
                ↓
        Backend deletes:
        ├─ pdf_templates
        ├─ pdf_template_versions (cascade)
        └─ pipeline_definitions (explicit)
                ↓
        List refreshes, draft gone
```

---

## Validation Rules

| Scenario | Required Fields |
|----------|-----------------|
| Save Draft | name, source_pdf_id |
| Update Draft | (any fields, source_pdf_id immutable) |
| Publish Draft | name, source_pdf_id, signature_objects, extraction_fields*, pipeline_state*, visual_state |

*extraction_fields and pipeline_state not required if is_autoskip=true

---

## Edge Cases

1. **User closes browser mid-draft**: Data lost if not explicitly saved. No auto-save.

2. **Draft PDF deleted**: source_pdf_id points to deleted pdf_file. Handle gracefully:
   - Show error when trying to open draft
   - Allow discarding the broken draft

3. **Concurrent edits**: Not user-scoped, so multiple users could edit same draft.
   - Last write wins (simple approach)
   - No locking mechanism needed for MVP

4. **Draft with same name as active template**: Allowed. Names don't need to be unique.

5. **Publish validation fails**: Draft is NOT deleted. User sees validation error,
   can fix issues and try again.

---

## Testing Checklist

### Backend
- [ ] Create draft with minimum fields (name + source_pdf_id)
- [ ] Create draft with all fields
- [ ] Update existing draft
- [ ] Cannot update non-draft template via draft endpoint
- [ ] Discard draft successfully deletes all related records
- [ ] Cannot discard non-draft template
- [ ] Publish draft creates new active template
- [ ] Publish draft deletes old draft records
- [ ] Publish validation fails gracefully (draft preserved)
- [ ] ETO matching excludes draft templates

### Frontend
- [ ] Draft badge shows in template list
- [ ] Close modal triggers "Save as Draft?" popup
- [ ] Save as Draft uploads PDF and creates draft
- [ ] Opening draft loads all saved data
- [ ] Page selection step locked for drafts
- [ ] Completing draft and saving publishes correctly
- [ ] Discard draft removes from list
