# Template Versioning Implementation Plan

## Executive Summary

Add template ID prop to TemplateBuilder to differentiate between:
- **Create Mode**: Building a brand new template (no template ID)
- **Version Mode**: Creating a new version of an existing template (has template ID)

## Current State Analysis

### 1. API Endpoints Structure

#### Create Template
```
POST /api/pdf-templates
Body: CreatePdfTemplateRequest
Returns: PdfTemplate (with version 1)
```

#### Update Template (Creates New Version)
```
PUT /api/pdf-templates/{id}
Body: UpdatePdfTemplateRequest
Returns: PdfTemplate (with new version)
```

**Key Insight from API Documentation (Line 112-138 in router):**
```python
"""
Update template with smart versioning logic.

Flow:
1. Simple Case: Only name/description → Update metadata only (no new version)
2. Version Case: signature_objects or extraction_fields → Create new version
3. Complex Case: Pipeline fields → Validate/compile/create pipeline → Create new version

All updates are atomic using unit-of-work pattern.

Errors:
- 404: Template not found
- 409: Template is active (deactivate first to update wizard data)
- 400: Pipeline validation fails
"""
```

**Backend auto-increments version numbers** - frontend only needs to pass the data.

### 2. Current TemplateBuilder Usage Points

#### A. PDF Templates Page (`client/src/renderer/pages/dashboard/pdf-templates/index.tsx`)

**Line 121-181: `handleEditFromDetail` - Edit existing template (NEEDS FIX)**
```typescript
const handleEditFromDetail = async (templateId: number, versionId: number) => {
  // Loads existing template data
  // Opens builder with initialData
  // Currently has TODO at line 274: "Need template ID from somewhere"
}
```

**Line 201-239: `handleCreateTemplate` - Create new from uploaded PDF**
```typescript
const handleCreateTemplate = async () => {
  // User uploads PDF
  // Opens builder with local file
  // No template ID (create mode)
}
```

**Line 248-298: `handleSaveTemplate` - Save handler (NEEDS UPDATE)**
```typescript
const handleSaveTemplate = async (templateData: TemplateBuilderData) => {
  // Line 270-276: Determines if edit mode via builderInitialData
  // Line 275: TODO comment about needing template ID
  // Currently always calls createTemplate.mutateAsync
}
```

#### B. ETO Page (`client/src/renderer/pages/dashboard/eto/index.tsx`)

**Line 155-193: `handleSaveTemplate` - Always creates new template**
```typescript
const handleSaveTemplate = async (templateData: any) => {
  // Always creates new template (from "needs_template" runs)
  // No edit functionality needed here
}
```

### 3. Existing API Hooks

**`useCreateTemplate()` - Line 100-118 in hooks.ts**
```typescript
mutationFn: async (request: CreateTemplateRequest): Promise<TemplateDetail> => {
  const response = await apiClient.post<TemplateDetail>(baseUrl, request);
  return response.data;
}
```

**`useUpdateTemplate()` - Line 124-147 in hooks.ts**
```typescript
mutationFn: async ({
  templateId,
  request,
}: {
  templateId: number;
  request: UpdateTemplateRequest;
}): Promise<TemplateDetail> => {
  const response = await apiClient.put<TemplateDetail>(
    `${baseUrl}/${templateId}`,
    request
  );
  return response.data;
}
```

## Problem Statement

Currently, when editing a template from the detail view:
1. TemplateBuilder opens with previous version data
2. User makes changes
3. **Save always calls CREATE endpoint** (creates duplicate template)
4. Should call UPDATE endpoint to create new version on existing template

## Solution Design

Add optional `templateId` prop to TemplateBuilder:
- **`templateId=undefined`**: Create mode → call POST `/api/pdf-templates`
- **`templateId=123`**: Version mode → call PUT `/api/pdf-templates/123`

### Why This Design?

✅ **Explicit and type-safe** - Template ID presence clearly indicates mode
✅ **Matches API structure** - Update endpoint requires template ID in URL
✅ **Minimal changes** - Only add one prop, no breaking changes
✅ **Backend handles versioning** - Frontend just passes data, backend increments version
✅ **Single responsibility** - TemplateBuilder doesn't decide mode, parent does

## Implementation Plan

### Step 1: Update TemplateBuilder Props Interface

**File:** `client/src/renderer/features/templates/components/TemplateBuilder/TemplateBuilder.tsx`

**Line 24-33: Update interface**

```typescript
interface TemplateBuilderProps {
  isOpen: boolean;
  pdfFile: File | null;          // For create mode (local file)
  pdfFileId: number | null;       // For edit mode (existing PDF)
  pdfMetadata: PdfFileMetadata | null;
  templateId?: number;            // NEW: If provided, creating new version of existing template
  onClose: () => void;
  onSave: (data: TemplateBuilderData, templateId?: number) => Promise<void>;  // UPDATED
  initialData?: Partial<TemplateBuilderData>;
}
```

**Line 46-54: Accept prop**

```typescript
export function TemplateBuilder({
  isOpen,
  pdfFile,
  pdfFileId,
  pdfMetadata,
  templateId,  // NEW: Accept templateId
  onClose,
  onSave,
  initialData,
}: TemplateBuilderProps) {
```

**Line 212-220: Update save handler to pass templateId**

```typescript
const handleSave = async () => {
  if (!validateTemplate()) return;

  setIsSaving(true);
  try {
    await onSave(getTemplateData(), templateId);  // PASS templateId
    // Success - modal will close via parent
  } catch (err) {
    console.error('Save failed:', err);
    alert(`Failed to save template: ${err instanceof Error ? err.message : 'Unknown error'}`);
  } finally {
    setIsSaving(false);
  }
};
```

### Step 2: Update TemplateBuilderHeader for UI Clarity

**File:** `client/src/renderer/features/templates/components/TemplateBuilder/TemplateBuilderHeader.tsx`

**Add props interface:**

```typescript
interface TemplateBuilderHeaderProps {
  templateName: string;
  templateDescription: string;
  onTemplateNameChange: (name: string) => void;
  onTemplateDescriptionChange: (description: string) => void;
  onClose: () => void;
  mode: 'create' | 'version';  // NEW: Indicates mode
}
```

**Update header title based on mode:**

```typescript
<h2 className="text-xl font-semibold text-white">
  {mode === 'create' ? 'Create New Template' : 'Create Template Version'}
</h2>
```

**Update TemplateBuilder to pass mode:**

```typescript
<TemplateBuilderHeader
  templateName={templateName}
  templateDescription={templateDescription}
  onTemplateNameChange={setTemplateName}
  onTemplateDescriptionChange={setTemplateDescription}
  onClose={onClose}
  mode={templateId ? 'version' : 'create'}  // NEW
/>
```

### Step 3: Update PDF Templates Page Save Handler

**File:** `client/src/renderer/pages/dashboard/pdf-templates/index.tsx`

**Line 42-47: Add state for template ID**

```typescript
// Template Builder Modal State
const [isBuilderOpen, setIsBuilderOpen] = useState(false);
const [builderPdfFile, setBuilderPdfFile] = useState<File | null>(null);
const [builderPdfFileId, setBuilderPdfFileId] = useState<number | null>(null);
const [builderTemplateId, setBuilderTemplateId] = useState<number | null>(null);  // NEW
const [builderInitialData, setBuilderInitialData] = useState<Partial<TemplateBuilderData> | undefined>(undefined);
const [builderKey, setBuilderKey] = useState(0);
```

**Line 121-181: Update handleEditFromDetail to store template ID**

```typescript
const handleEditFromDetail = async (templateId: number, versionId: number) => {
  try {
    // Close detail modal
    setIsDetailOpen(false);
    setDetailTemplateId(null);

    // Fetch template detail and version detail
    const templateDetail = await queryClient.fetchQuery({
      queryKey: ['template', templateId],
      staleTime: 0,
    });

    const [versionDetail, pipelineData] = await Promise.all([
      queryClient.fetchQuery({
        queryKey: ['template-version', versionId],
        queryFn: async () => {
          const response = await apiClient.get(
            `${API_CONFIG.ENDPOINTS.TEMPLATES}/versions/${versionId}`
          );
          return response.data;
        },
        staleTime: 0,
      }),
      (async () => {
        const versionData = await queryClient.fetchQuery({
          queryKey: ['template-version', versionId],
          queryFn: async () => {
            const response = await apiClient.get(
              `${API_CONFIG.ENDPOINTS.TEMPLATES}/versions/${versionId}`
            );
            return response.data;
          },
          staleTime: 0,
        });
        return getPipeline(versionData.pipeline_definition_id);
      })()
    ]);

    // Build initialData for the builder modal
    const initialData: Partial<TemplateBuilderData> = {
      name: templateDetail.name,
      description: templateDetail.description || '',
      signature_objects: versionDetail.signature_objects,
      extraction_fields: versionDetail.extraction_fields,
      pipeline_state: pipelineData.pipeline_state,
      visual_state: pipelineData.visual_state,
    };

    // Open builder with initial data AND template ID
    setBuilderInitialData(initialData);
    setBuilderPdfFileId(versionDetail.source_pdf_id);
    setBuilderTemplateId(templateId);  // NEW: Store template ID
    setBuilderKey(prev => prev + 1);
    setIsBuilderOpen(true);
  } catch (err) {
    console.error('Failed to load template for editing:', err);
    alert(`Failed to load template: ${err instanceof Error ? err.message : 'Unknown error'}`);
  }
};
```

**Line 201-239: Update handleCreateTemplate to clear template ID**

```typescript
const handleCreateTemplate = async () => {
  const input = document.createElement('input');
  input.type = 'file';
  input.accept = 'application/pdf';

  input.onchange = async (e: Event) => {
    const target = e.target as HTMLInputElement;
    const file = target.files?.[0];

    if (file) {
      if (file.type !== 'application/pdf') {
        alert('Please select a PDF file');
        return;
      }

      try {
        console.log('Processing PDF objects...');
        const processedData = await processObjects(file);
        console.log('PDF objects extracted:', processedData);

        // Open builder with local file (no PDF ID or template ID yet)
        setBuilderPdfFile(file);
        setBuilderPdfFileId(null);
        setBuilderTemplateId(null);  // NEW: No template ID for create
        setBuilderInitialData(undefined);
        setBuilderKey(prev => prev + 1);
        setIsBuilderOpen(true);
      } catch (err) {
        console.error('Failed to process PDF:', err);
        alert(`Failed to process PDF: ${err instanceof Error ? err.message : 'Unknown error'}`);
      }
    }
  };

  input.click();
};
```

**Line 241-246: Update handleCloseBuilder**

```typescript
const handleCloseBuilder = () => {
  setIsBuilderOpen(false);
  setBuilderInitialData(undefined);
  setBuilderPdfFile(null);
  setBuilderPdfFileId(null);
  setBuilderTemplateId(null);  // NEW: Clear template ID
};
```

**Line 248-298: REPLACE handleSaveTemplate with new implementation**

```typescript
const handleSaveTemplate = async (templateData: TemplateBuilderData, templateId?: number) => {
  try {
    let pdfId: number;

    // Create mode: Upload PDF file first to get ID
    if (builderPdfFile) {
      console.log('Uploading PDF file...');
      const uploadedPdf = await uploadPdf(builderPdfFile);
      pdfId = uploadedPdf.id;
      console.log('PDF uploaded, ID:', pdfId);
    }
    // Edit mode: Use existing PDF ID
    else if (builderPdfFileId) {
      pdfId = builderPdfFileId;
      console.log('Using existing PDF ID:', pdfId);
    }
    // Error: No PDF file or ID
    else {
      throw new Error('No PDF file or ID available');
    }

    if (templateId) {
      // VERSION MODE: Update existing template (creates new version)
      console.log('Creating new version for template:', templateId);
      await updateTemplate.mutateAsync({
        templateId,
        request: {
          name: templateData.name,
          description: templateData.description,
          signature_objects: templateData.signature_objects,
          extraction_fields: templateData.extraction_fields,
          pipeline_state: templateData.pipeline_state,
          visual_state: templateData.visual_state,
        },
      });
      console.log('Template version created successfully');
    } else {
      // CREATE MODE: Create new template
      console.log('Creating new template');
      await createTemplate.mutateAsync({
        name: templateData.name,
        description: templateData.description,
        source_pdf_id: pdfId,
        signature_objects: templateData.signature_objects,
        extraction_fields: templateData.extraction_fields,
        pipeline_state: templateData.pipeline_state,
        visual_state: templateData.visual_state,
      } as any);
      console.log('Template created successfully');
    }

    // Close modal on success
    handleCloseBuilder();
    // TanStack Query auto-invalidates and refetches on success
  } catch (err) {
    console.error('Failed to save template:', err);
    throw err; // Re-throw to let modal handle error
  }
};
```

**Line 477-486: Pass templateId to TemplateBuilder**

```typescript
<TemplateBuilder
  key={`builder-${builderKey}`}
  isOpen={isBuilderOpen}
  pdfFile={builderPdfFile}
  pdfFileId={builderPdfFileId}
  pdfMetadata={pdfMetadata || null}
  templateId={builderTemplateId}  // NEW: Pass template ID
  initialData={builderInitialData}
  onClose={handleCloseBuilder}
  onSave={handleSaveTemplate}
/>
```

### Step 4: Verify ETO Page (No Changes Needed)

**File:** `client/src/renderer/pages/dashboard/eto/index.tsx`

The ETO page only creates new templates from processed PDFs without templates. No changes needed because:
- Never edits existing templates
- Always creates new templates
- No template ID to pass

**Verify existing code (Line 155-193) works as-is:**

```typescript
const handleSaveTemplate = async (templateData: any) => {
  // This signature now matches: (data, templateId?) => Promise<void>
  // templateId will be undefined, which is correct for create mode

  const createdTemplate = await createTemplate.mutateAsync({
    name: templateData.name,
    description: templateData.description,
    source_pdf_id: templateData.source_pdf_id!,
    signature_objects: templateData.signature_objects,
    extraction_fields: templateData.extraction_fields,
    pipeline_state: templateData.pipeline_state,
    visual_state: templateData.visual_state,
  } as any);

  // ... rest of logic
};
```

## Testing Checklist

### Test Case 1: Create New Template (PDF Templates Page)
1. Click "Create Template" button
2. Upload PDF
3. Complete template builder wizard
4. Click Save
5. **Expected**: Calls POST `/api/pdf-templates`, creates new template
6. **Verify**: New template appears in list, version 1

### Test Case 2: Create Template Version (PDF Templates Page)
1. Click "View" on existing template
2. Click "Edit" button in detail modal
3. Modal loads with existing data
4. Modify signature objects or fields
5. Click Save
6. **Expected**: Calls PUT `/api/pdf-templates/{id}`, creates new version
7. **Verify**: Template updated, version incremented, still same template

### Test Case 3: Create Template from ETO Run
1. Navigate to ETO page
2. Find run with "needs_template" status
3. Click "Build Template"
4. Complete wizard
5. Click Save
6. **Expected**: Calls POST `/api/pdf-templates`, creates new template, activates it
7. **Verify**: Template created, run reprocessed

### Test Case 4: Header Display
1. Open builder in create mode
2. **Verify**: Header shows "Create New Template"
3. Open builder in edit mode
4. **Verify**: Header shows "Create Template Version"

### Test Case 5: Error Handling
1. Try editing an active template
2. **Expected**: Backend returns 409 error
3. **Verify**: User sees clear error message

## Migration Notes

### Breaking Changes
**None** - This is a backward-compatible change. Existing code that doesn't pass `templateId` will default to create mode.

### API Compatibility
- POST `/api/pdf-templates` - No changes required
- PUT `/api/pdf-templates/{id}` - Already expects UpdatePdfTemplateRequest
- Both endpoints return `PdfTemplate` with version list

### Type Safety
All changes maintain TypeScript type safety:
- `templateId?: number` is optional
- `onSave` signature updated to accept optional second parameter
- All call sites explicitly handle both modes

## Future Enhancements

### Version Indicator in Builder
Add badge/indicator in builder UI showing:
- "Creating Version 5 of Template XYZ"
- Previous version number

### Version Diff View
Before saving new version:
- Show what changed from previous version
- Allow user to add version notes

### Prevent Unnecessary Versions
If user opens edit mode but changes nothing:
- Detect no actual changes
- Skip calling update endpoint
- Just close modal

## Rollback Plan

If issues arise:
1. Revert `TemplateBuilder.tsx` props interface
2. Revert `handleSaveTemplate` in pdf-templates/index.tsx
3. Revert `handleEditFromDetail` template ID storage
4. Feature will fall back to always creating new templates

## Success Metrics

✅ Can create new templates from custom PDFs
✅ Can create new templates from ETO runs
✅ Can edit existing templates to create new versions
✅ Backend increments version numbers automatically
✅ No duplicate templates created
✅ UI clearly indicates create vs version mode
✅ All three usage points working correctly

## Timeline Estimate

- **Step 1 (TemplateBuilder props)**: 15 minutes
- **Step 2 (Header UI update)**: 10 minutes
- **Step 3 (PDF Templates page)**: 30 minutes
- **Step 4 (Verify ETO page)**: 5 minutes
- **Testing**: 30 minutes
- **Total**: ~90 minutes

## Conclusion

This implementation provides a clean, type-safe solution for differentiating between creating new templates and creating new versions. The backend handles all versioning complexity, while the frontend simply passes the template ID when updating an existing template.
