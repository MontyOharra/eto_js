# Session Continuity Document

## Current Status (2025-11-10)

### ✅ Recently Completed
- **TemplateBuilder Testing Step** - Fully implemented fourth step with simulation, PDF overlay, and pipeline execution visualization
- **Code Cleanup** - All TemplateBuilder components now pass ESLint and TypeScript checks with zero errors
- **UX Improvements** - Moved testing controls to footer, immediate test trigger from pipeline step, PDF auto-fit on resize

### Template Builder - Feature Complete
All 4 steps of the template builder are now fully functional:
1. **Signature Objects** - Select PDF objects for template matching ✅
2. **Extraction Fields** - Draw bboxes and define fields ✅
3. **Pipeline** - Build transformation pipeline with validation ✅
4. **Testing** - Simulate execution and view results ✅

## Next Goal: Template Versioning & Viewer

### Overview
Implement a complete template versioning system and build out the template viewer functionality. This will allow users to:
- Create new versions of existing templates
- View detailed information about templates and their versions
- Track version history and changes
- Switch between versions
- Understand what changed between versions

### Key Components to Implement

#### 1. Template Versioning System
**API Integration:**
- `PUT /pdf-templates/{id}` - Update template (creates new version)
  - Optional metadata updates (name, description)
  - Optional version data (signature_objects, extraction_fields, pipeline_state, visual_state)
  - Returns updated TemplateDetail with new version

**Version Management:**
- Create new version when template definition changes
- Preserve all previous versions (immutable history)
- Track version numbers and creation timestamps
- Link versions to parent template

#### 2. Template Detail Viewer
**Location:** `client/src/renderer/features/templates/components/TemplateDetail/`

**Core Features:**
- Display template metadata (name, description, status, usage count)
- Show current active version details
- List all versions with metadata (version number, created date)
- Display signature objects, extraction fields, and pipeline for selected version
- Visual diff between versions (future enhancement)

**UI Structure:**
```
TemplateDetailModal
  ├─ TemplateDetailHeader (name, status, actions)
  ├─ TemplateDetailSidebar (version list, metadata)
  ├─ VersionDetailPanel (signature objects, fields, pipeline)
  └─ TemplateDetailFooter (close, edit buttons)
```

#### 3. Version Creation Flow
**From Dashboard:**
1. User selects template → Opens detail modal
2. User clicks "Create New Version" or "Edit Template"
3. Opens TemplateBuilder in edit mode with current version data
4. User makes changes to any step
5. User saves → Creates new version via `PUT /pdf-templates/{id}`
6. New version becomes active version
7. Previous version preserved in history

**Version Data Flow:**
```typescript
// Fetch current version for editing
GET /pdf-templates/versions/{versionId}
  → Returns TemplateVersionDetail

// Edit in TemplateBuilder
TemplateBuilder (edit mode)
  - Pre-populate with version data
  - Allow changes to any step
  - Validate before save

// Save creates new version
PUT /pdf-templates/{templateId}
  - Body: { signature_objects, extraction_fields, pipeline_state, visual_state }
  - Backend creates new version
  - Returns updated template with new version
```

### Implementation Steps

#### Phase 1: Template Detail Viewer (Priority)
1. **Create base modal component**
   - TemplateDetailModal.tsx
   - Layout with header, sidebar, content area, footer
   - Modal open/close state management

2. **Header component**
   - Display name, status badge, usage count
   - Action buttons: Edit, Activate/Deactivate, Delete
   - Breadcrumb or close button

3. **Sidebar component**
   - List all versions (version number, date, "active" badge)
   - Click to select version
   - Highlight selected version
   - Show metadata (created date, created by if available)

4. **Version detail panel**
   - Tab or section-based layout
   - **Signature Objects** tab: Display selected objects with counts
   - **Extraction Fields** tab: List fields with bbox coordinates
   - **Pipeline** tab: Show pipeline graph (read-only ExecutedPipelineGraph or PipelineGraph)
   - **Metadata** section: Version-specific info

5. **Integration with dashboard**
   - Add onClick handler to TemplateCard
   - Pass templateId to detail modal
   - Fetch template detail via `useTemplateDetail(templateId)`
   - Fetch version detail via `useTemplateVersionDetail(versionId)`

#### Phase 2: Version Creation
1. **Edit button integration**
   - From detail modal, click "Edit" or "Create New Version"
   - Opens TemplateBuilder with existing data
   - Pass `initialData` prop with current version data

2. **Update API integration**
   - Use `useUpdateTemplate()` mutation
   - Pass templateId and updated fields
   - Backend creates new version automatically
   - Frontend refetches template detail

3. **Version comparison (future)**
   - Side-by-side diff of two versions
   - Highlight changes in signature objects, fields, pipeline
   - Visual indicators for additions/removals

### API Endpoints Reference

```typescript
// Template operations
GET /pdf-templates                    // List all templates
GET /pdf-templates/{id}               // Get template detail (with version IDs)
GET /pdf-templates/versions/{id}      // Get specific version detail
PUT /pdf-templates/{id}               // Update template (creates new version)
POST /pdf-templates/{id}/activate     // Activate template
POST /pdf-templates/{id}/deactivate   // Deactivate template
DELETE /pdf-templates/{id}            // Delete template (all versions)

// Already implemented
POST /pdf-templates                   // Create new template
POST /pdf-templates/simulate          // Test template execution
```

### File Structure to Create

```
client/src/renderer/features/templates/components/
├─ TemplateDetail/
│  ├─ TemplateDetailModal.tsx         // Main modal container
│  ├─ TemplateDetailHeader.tsx        // Header with actions
│  ├─ TemplateDetailSidebar.tsx       // Version list sidebar
│  ├─ VersionDetailPanel.tsx          // Version content display
│  ├─ SignatureObjectsView.tsx        // Read-only signature objects display
│  ├─ ExtractionFieldsView.tsx        // Read-only fields list
│  ├─ PipelineView.tsx                // Read-only pipeline graph
│  └─ index.ts                        // Exports
└─ TemplateBuilder/                   // Already exists
   └─ (all builder components)
```

### Data Types Reference

```typescript
// From templates/types.ts
interface TemplateDetail {
  template_id: number;
  name: string;
  description: string | null;
  status: TemplateStatus;
  source_pdf_id: number;
  usage_count: number;
  created_at: string;
  updated_at: string;
  versions: number[];              // Array of version IDs
  active_version_id: number | null;
}

interface TemplateVersionDetail {
  version_id: number;
  template_id: number;
  version_number: number;
  signature_objects: PdfObjects;
  extraction_fields: ExtractionField[];
  pipeline_state: PipelineState;
  visual_state: VisualState;
  created_at: string;
}
```

### Testing Checklist

**Template Detail Viewer:**
- [ ] Opens modal when clicking template card
- [ ] Displays correct template metadata
- [ ] Lists all versions in sidebar
- [ ] Selects version and displays detail
- [ ] Shows signature objects, fields, and pipeline
- [ ] Highlights active version
- [ ] Close button works
- [ ] Edit button opens TemplateBuilder

**Version Creation:**
- [ ] Edit button loads current version data
- [ ] TemplateBuilder pre-populates correctly
- [ ] Changes can be made to any step
- [ ] Save creates new version (not update existing)
- [ ] New version appears in version list
- [ ] New version becomes active
- [ ] Previous version still accessible

**Edge Cases:**
- [ ] Template with only one version
- [ ] Template with many versions (10+)
- [ ] Viewing old version while editing
- [ ] Switching versions mid-view
- [ ] Deleting template with multiple versions

### Current State of Code

**What Works:**
- TemplateBuilder fully functional (create new templates)
- Template list/grid display on dashboard
- Template status management (activate/deactivate)
- Template deletion
- Simulation API integration

**What Needs Work:**
- Template detail modal (doesn't exist yet)
- Version viewing (no UI for this)
- Version creation (edit flow not implemented)
- TemplateBuilder edit mode (create mode works, edit mode needs testing)

### Priority Order

1. **High Priority:** Template detail modal with version list and viewing
2. **Medium Priority:** Edit button integration with TemplateBuilder
3. **Low Priority:** Version comparison and advanced features

### Notes

- The backend API for versioning already exists (`PUT /pdf-templates/{id}`)
- All necessary API hooks are defined in `templates/api/hooks.ts`
- TemplateBuilder can be reused for editing (pass `initialData` prop)
- Focus on read-only viewing first, then add editing functionality
- Keep UI consistent with existing TemplateBuilder styling

### References

**Key Files:**
- `client/src/renderer/features/templates/api/hooks.ts` - API hooks
- `client/src/renderer/features/templates/types.ts` - Type definitions
- `client/src/renderer/features/templates/api/types.ts` - API request/response types
- `client/src/renderer/features/templates/components/TemplateBuilder/` - Builder components
- `client/src/renderer/pages/dashboard/pdf-templates/index.tsx` - Dashboard page

**Similar Patterns:**
- Look at ETO detail viewer (`features/eto/components/EtoRunDetail/`) for modal patterns
- Look at pipeline viewer (`features/pipelines/components/`) for graph display patterns
- Look at execution results display for read-only views

---

**Last Updated:** 2025-11-10 Evening
**Next Session:** Start with TemplateDetailModal component creation
