# Feature: Create Template from Existing Template

## Overview

Allow users to copy signature objects, extraction fields, and pipeline from an existing template when building a new template. This is useful for similar forms with common elements (e.g., same header structure, different body content).

This is distinct from template versioning - this creates a fully separate, new template.

## User Flow

```
1. User uploads PDF in template builder
2. User selects pages for new template (step 1 complete)
3. User clicks "Copy from Existing Template" button
4. New modal opens (overlays template builder modal):
   ┌─────────────────────────────────────────────────────────────┐
   │  Copy Template Structure                              [X]   │
   ├─────────────────────────────────────────────────────────────┤
   │  ┌─────────────────┐  ┌───────────────────────────────────┐ │
   │  │ Template List   │  │  PDF Preview                      │ │
   │  │ (filterable)    │  │  - Signature objects overlaid     │ │
   │  │                 │  │  - Extraction fields overlaid     │ │
   │  │ [Template A]    │  │                                   │ │
   │  │ [Template B] ←  │  │  [Toggle: Source PDF / New PDF]   │ │
   │  │ [Template C]    │  │                                   │ │
   │  │ ...             │  │  [View Pipeline] button           │ │
   │  └─────────────────┘  └───────────────────────────────────┘ │
   │                                                             │
   │                              [Cancel]  [Copy Structure]     │
   └─────────────────────────────────────────────────────────────┘
5. User browses templates, views signature objects/fields/pipeline
6. User selects template and clicks "Copy Structure"
7. Modal closes, template builder state is updated:
   - Signature objects: objects that exist on new PDF are selected
   - Extraction fields: copied exactly as-is
   - Pipeline: copied exactly as-is
8. User continues normal template building (sets name, customer, etc.)
```

## UI Components

### 1. "Copy from Existing Template" Button

**Location:** Template builder, after step 1 (page selection) is complete

**Behavior:** Opens the template copy modal

### 2. Template Copy Modal

**Layout:**
- **Left panel**: Template list with filtering (similar to main templates page)
  - Search by name
  - Filter by customer
  - Filter by status (active only? or include inactive?)
  - Shows template name, customer, version count

- **Right panel**: Preview area
  - PDF viewer with overlaid signature objects and extraction fields
  - Toggle switch: "View Source PDF" / "View New PDF"
    - Source PDF: Shows the source template's PDF with its objects (what you're copying from)
    - New PDF: Shows the new PDF being built with preview of how objects would appear
  - "View Pipeline" button: Opens read-only pipeline viewer (could be expandable section or sub-modal)

- **Footer**: Cancel and "Copy Structure" buttons

### 3. PDF Preview Toggle

Two view modes:
- **Source PDF view**: Helps user understand what the source template looks like
- **New PDF view**: Shows how the copied objects would appear on their new PDF (useful for verifying alignment)

### 4. Read-Only Pipeline Viewer

Simple visualization of the pipeline structure:
- Entry points (input channels)
- Module connections
- Output channels

No editing capability - just for inspection.

## Backend Requirements

### API Endpoint

May need an endpoint to get template structure for preview:

```
GET /api/pdf-templates/{id}/current-version/structure
```

Returns:
```json
{
  "template_id": 123,
  "version_id": 456,
  "source_pdf_id": 789,
  "signature_objects": [...],
  "extraction_fields": [...],
  "pipeline_definition": {...}
}
```

Or this may already be available through existing template/version endpoints.

### Signature Object Matching

Use the **same matching logic** as ETO template matching to determine if a signature object exists on the new PDF.

For each signature object from the source template:
1. Check if it exists on the new PDF using existing matching logic
2. If match found: include in the "selected" objects for the new template
3. If no match: exclude (don't select)

**Note:** The PDF being built has already been processed by pdfplumber (step 1 complete), so we have the list of objects on the new PDF available.

## Frontend Implementation

### State Management

The template builder already manages state for:
- `selectedSignatureObjects`: which PDF objects are selected as signatures
- `extractionFields`: list of extraction field definitions
- `pipelineDefinition`: the transformation pipeline

When user clicks "Copy Structure":
1. Get source template's current version data
2. For each signature object in source:
   - Run matching logic against new PDF's objects
   - If match found, add to `selectedSignatureObjects`
3. Set `extractionFields` to source template's extraction fields (deep copy)
4. Set `pipelineDefinition` to source template's pipeline (deep copy)
5. Close modal

### Template List Component

Reuse or adapt existing template list components:
- `TemplateList` or similar from templates page
- Add click handler to select template for preview
- Highlight selected template

### Preview Component

Reuse existing PDF preview components:
- PDF viewer with object overlay capability
- Signature object visualization
- Extraction field visualization

Add toggle for source vs new PDF view.

## Edge Cases

1. **No signature objects match**:
   - Nice-to-have: Show warning "0 of N signature objects found on new PDF"
   - Still allow copy (user may want the extraction fields and pipeline)

2. **Template has no extraction fields or pipeline**:
   - Valid case - user might just want signature objects
   - Copy what's available

3. **New PDF has different dimensions**:
   - Extraction fields are position-based
   - May be misaligned - user will need to adjust
   - This is expected; extraction fields are easy to reposition

4. **Source template is a draft**:
   - Should drafts appear in the list? Probably not - only active templates
   - Or include with a "Draft" badge and let user decide

5. **User closes modal without copying**:
   - No changes to template builder state
   - User continues with their original work

## Checklist

### Backend
- [ ] Verify existing API provides all needed template structure data
- [ ] If needed, add endpoint for template structure (signature objects, fields, pipeline)
- [ ] Ensure signature object matching logic is accessible/reusable

### Frontend - Template Builder Integration
- [ ] Add "Copy from Existing Template" button after step 1
- [ ] Wire button to open copy modal
- [ ] Implement state update when copy is performed

### Frontend - Template Copy Modal
- [ ] Create modal component structure (left/right panels)
- [ ] Implement template list with filtering
- [ ] Implement template selection highlighting
- [ ] Implement PDF preview with object overlays
- [ ] Implement source/new PDF toggle
- [ ] Implement read-only pipeline viewer
- [ ] Implement "Copy Structure" action
- [ ] Implement signature object matching against new PDF

### Frontend - State Update Logic
- [ ] Implement signature object matching (reuse existing logic)
- [ ] Update selectedSignatureObjects based on matches
- [ ] Deep copy extraction fields from source
- [ ] Deep copy pipeline definition from source
- [ ] Close modal and return to builder

### Testing
- [ ] Test with template that has matching signature objects
- [ ] Test with template that has NO matching signature objects
- [ ] Test extraction field and pipeline copying
- [ ] Test toggle between source/new PDF views
- [ ] Test filtering and searching templates
- [ ] Test modal close without copying (no side effects)
- [ ] Test with templates of varying complexity
