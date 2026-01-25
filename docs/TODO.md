# TODO - Feature Implementation Checklist

This document tracks planned features with implementation checklists. Each feature has a detailed plan document in `docs/plans/`.

---

## Quick Start - Feature Development Workflow

### 1. Branch Setup

Before starting any feature work:

1. **Ensure you are on `dev` branch:** `git checkout dev && git pull`
2. **Create feature branch:** `git checkout -b feature/{feature-name}`
3. **Push to remote:** `git push -u origin feature/{feature-name}`

**Merge strategy:**
- Feature branch → `dev`: After implementation AND testing complete
- `dev` can accumulate multiple completed feature branches
- `dev` → `master`: Only after all features in dev are conflict-free and pass final integration testing
- Single feature shortcut: If only one feature in dev, can merge directly to master after testing

### 2. Before Writing Code

For each feature, review in order:

1. **Summary** - Quick overview in the Progress Tracker section below
2. **Detailed checklist** - Full breakdown in the numbered section for the feature
3. **Plan document** - Referenced at top of each feature section (e.g., `docs/plans/{feature}.md`)

Then **discuss the plan** before implementation begins.

### 3. Complexity Considerations

**Simple features:** Everything is fully planned with specific code references. Can proceed after brief review.

**Complex features:** Require detailed discussion before implementation.

### 4. Database & Type Changes

**Avoid if possible:** Changes to database schema or persistence-level types should be avoided when feasible.

**If changes are necessary, discuss:**
- Data integrity implications
- Migration strategy for existing data
- For complex JSON columns (e.g., `pipeline_state` with deeply nested structures tied to backend typing):
  - Option A: Migrate existing data to new format
  - Option B: Implement backward compatibility in code
- Test migration on copy of production data before applying

---

## Progress Tracker

| # | Item | Priority | Complexity | Plan | Implement | Test |
|---|------|:--------:|:----------:|:----:|:---------:|:----:|
| 3 | Field Processing Error Handling (Decoupled) | 1 | 4 | [x] | [x] | [x] |
| 13 | Improved Attachment Handling | 1 | 3 | [x] | [x] | [x] |
| 15 | Create Template from Existing | 1 | 4 | [x] | [x] | [x] |
| 19 | Merge Adjacent PDF Text Boxes | 1 | 2 | [x] | [x] | [x] |
| 9 | Summary Page Rework | 2 | 3 | [x] | [x] | [x] |
| 12 | Navigate from Order Management to ETO | 2 | 1 | [x] | [x] | [x] |
| 16 | HTC Time Format Parsing | 2 | 2 | [x] | [ ] | [ ] |
| 18 | Manual Field Entry for Pending Actions | 2 | 3 | [x] | [ ] | [ ] |
| 1 | Template Draft Saving | 3 | 4 | [x] | [ ] | [ ] |
| 6 | Browse Template Matches / Set New Base | 3 | 3 | [x] | [ ] | [ ] |
| 14 | Email Filter Rules: NOT/Negation | 3 | 2 | [x] | [ ] | [ ] |
| 17 | Sub-Run Modal: View Template Button | 4 | 1 | [x] | [x] | [x] |
| 2 | New Pipeline Modules (Math + LLM) | 5 | 3 | [x] | [ ] | [ ] |
| 4 | Address Matching with Company Name | 5 | 3 | [x] | [ ] | [ ] |
| 5 | Extraction Field Rename Syncs to Pipeline | 5 | 2 | [x] | [ ] | [ ] |
| 7 | Conditional Error/Halt Module | 5 | 2 | [x] | [ ] | [ ] |
| 8 | Extraction Field ↔ Pipeline Hover Highlighting | 5 | 2 | [x] | [x] | [x] |
| 10 | Extraction Field Popup Overflow Fix | 5 | 1 | [x] | [x] | [x] |
| 20 | ETO Bulk Actions | 3 | 2 | [x] | [ ] | [ ] |

**Priority:** 1 = Critical, 2 = High, 3 = Medium, 4 = Low, 5 = Nice to have
**Complexity:** 1 = Quick fix, 2 = Simple, 3 = Medium, 4 = Complex, 5 = Major rework

---

## 1. Template Draft Saving

**Plan:** [`docs/plans/template-draft-saving.md`](./plans/template-draft-saving.md)

**Summary:** Allow users to save in-progress templates as drafts, close the builder modal, and return later to complete them.

### Backend

- [ ] Add `draft` to `PdfTemplateStatus` enum in `shared/types/pdf_templates.py`
- [ ] Add `draft` to `PDF_TEMPLATE_STATUS` enum in `shared/database/models.py`
- [ ] Create `save_draft()` method in `PdfTemplateService`
- [ ] Create `discard_draft()` method in `PdfTemplateService`
- [ ] Create `publish_draft()` method in `PdfTemplateService`
- [ ] Add `POST /api/pdf-templates/draft` endpoint
- [ ] Add `PUT /api/pdf-templates/{id}/draft` endpoint
- [ ] Add `DELETE /api/pdf-templates/{id}/draft` endpoint
- [ ] Add `POST /api/pdf-templates/{id}/publish` endpoint
- [ ] Add API schemas for draft endpoints (`CreateDraftRequest`, `UpdateDraftRequest`, `PublishDraftRequest`)
- [ ] Verify ETO matching only uses `status='active'` templates

### Frontend

- [ ] Add "Draft" badge to template list items
- [ ] Add "Save as Draft" confirmation popup on modal close
- [ ] Implement draft save flow (upload PDF + create draft)
- [ ] Load draft data into builder when opening draft template
- [ ] Lock step 1 (page selection) when editing draft
- [ ] Wire up publish flow for draft templates
- [ ] Add API hooks (`useSaveDraft`, `useUpdateDraft`, `useDiscardDraft`, `usePublishDraft`)

### Testing

- [ ] Backend: Create/update/discard/publish draft operations
- [ ] Backend: Validation and error handling
- [ ] Frontend: Full user flow from create to publish
- [ ] Integration: ETO matching excludes drafts

---

## 2. New Pipeline Modules

**Plan:** [`docs/plans/new-modules.md`](./plans/new-modules.md)

**Summary:** Add math operation modules (Add, Subtract, Multiply, Divide) with 2-unlimited inputs, and a general-purpose LLM module with configurable prompt templates and structured JSON output.

### Math Modules (Add, Subtract, Multiply, Divide)

- [x] Create `math_add.py` - sum all inputs
- [x] Create `math_subtract.py` - subtract inputs in order
- [x] Create `math_multiply.py` - product of all inputs
- [x] Create `math_divide.py` - divide inputs in order (with zero-check)
- [x] All modules: 2-unlimited inputs, 1 float output
- [ ] Test with various input counts and types

### LLM Processor Module

- [ ] Create `llm_processor.py` module
- [ ] Config: `prompt_template` with `${variable}` injection
- [ ] Config: `output_schema` defining JSON structure
- [ ] Config: `model`, `temperature`, `system_context`
- [ ] Implement variable injection into prompt
- [ ] Implement validation: prompt vars ↔ inputs match
- [ ] Implement validation: output schema ↔ outputs match
- [ ] Implement LLM execution with JSON mode
- [ ] Handle LLM errors gracefully
- [ ] Test single and multiple input/output scenarios

---

## 3. Field Processing Error Handling (Decoupled Architecture)

**Plan:** [`docs/plans/field-processing-error-handling.md`](./plans/field-processing-error-handling.md)

**Summary:** Decouple field transformation from ETO sub-run success. Process each output channel field independently - failures recorded per-field rather than failing the entire sub-run. Includes cascading fallback (usaddress → LLM) for address parsing.

**Key Changes:**
- ETO sub-run succeeds once raw output data is stored
- Order management processes each field independently (never raises)
- Failed fields stored with status="failed" and error message
- LLM fallback for address parsing when usaddress fails

**Database:**
- [x] Add `processing_status`, `processing_error`, `raw_value` columns to `pending_action_fields`
- [x] Create migration, update types

**Backend:**
- [x] Update ETO service to not fail sub-run on order management errors
- [x] Refactor `process_output_execution()` to never raise, handle per-field
- [x] Implement cascading address resolution (usaddress → LLM fallback stub)

**API/Frontend:**
- [x] Update API schemas with processing status fields
- [x] Display field processing errors in UI
- [x] Error fields don't count toward required_fields_present
- [x] Hide error badges for completed/rejected actions

---

## 4. Address Matching with Company Name Tiebreaker

**Summary:** When matching output address channels to database addresses, multiple similar addresses may exist. Currently picks the first match arbitrarily. Should use company name matching as a tiebreaker to select the best address when multiple candidates exist.

**Current flow:**
- `find_address_by_text(street, city, state, zip)` queries by location, returns first street match
- `company_name` available at `find_or_create_address()` but not passed down
- Database has `FavCompany` field on address records

**Fix approach:**
- Pass `company_name` down to matching function
- When multiple street matches found: use fuzzy/similarity algorithm on company names
- Return address with highest company name similarity score
- If only one match or no company provided: current behavior unchanged

- [ ] Add `company_name: str | None` parameter to `find_address_by_text()`
- [ ] Implement fuzzy string similarity for company name matching (e.g., Levenshtein, token set ratio)
- [ ] When multiple matches: score each by company similarity, return best
- [ ] Pass company_name through from `find_or_create_address()`
- [ ] Test with multiple addresses at same location, different companies

---

## 5. Extraction Field Rename Syncs to Pipeline (Bug Fix)

**Summary:** In the template builder, renaming an extraction field doesn't update the pipeline entry points that reference that field name. This breaks the pipeline. Currently requires deleting and recreating the field with the new name, which is annoying.

**Fix:** When extraction field is renamed, propagate the name change to corresponding pipeline entry point.

- [ ] Find where extraction field rename occurs in frontend
- [ ] Find pipeline entry point data structure that references field names
- [ ] On rename: update pipeline state to use new field name
- [ ] Test renaming fields and verify pipeline remains connected

---

## 6. Browse Template Matches and Set New Base PDF

**Summary:** Template viewing page should allow browsing PDFs that have matched to that template. If a more complete example is found (e.g., a form with 3 piece/weight rows instead of 1), user can set it as the new base PDF and create a new template version from it. Helps handle discovering more complete form variants through actual usage.

**Data available:** `EtoSubRunModel.template_version_id` links matches to templates. Can query all PDFs that matched a template version with their extracted data, status, etc.

**"Use as new base" workflow:**
- PDF matched because signature objects are compatible
- Opens template builder with: new PDF as workspace + current version's signature objects, extraction fields, pipeline as starting point
- User adds new extraction fields for extra data, extends pipeline if needed
- Saves as new template version

**Backend:**
- [ ] Add repository method `get_by_template_version_id()` in EtoSubRunRepository
- [ ] Add service method to get matched PDFs with metadata
- [ ] Add API endpoint `GET /pdf-templates/versions/{id}/matched-pdfs`

**Frontend:**
- [ ] Add "Matched PDFs" section/tab to template detail page
- [ ] Display thumbnails/previews with match date, status, extracted data summary
- [ ] Add "Use as new base" button on each matched PDF
- [ ] Open template builder with selected PDF + current template data loaded
- [ ] Save flow creates new version with new source_pdf_id

---

## 7. Conditional Error/Halt Module

**Plan:** [`docs/plans/conditional-error-module.md`](./plans/conditional-error-module.md)

**Summary:** New pipeline module that conditionally throws an error to halt sub-run processing. Takes a boolean input - if true, throws an error with a configurable message from the config. No outputs. Acts as a guard to prevent data from being sent out when something is wrong.

- [ ] Create `conditional_error.py` module (or similar name)
- [ ] Input: single boolean
- [ ] Config: error message string
- [ ] Output: none (module kind may need special handling)
- [ ] If input is true, raise exception with configured message
- [ ] If input is false, pass through silently (no-op)
- [ ] Test error propagation and sub-run failure behavior

---

## 8. Extraction Field ↔ Pipeline Entry Point Hover Highlighting

**Summary:** In the viewer modal for completed sub runs and template testing step, hovering over an extraction field on the PDF should highlight the corresponding pipeline entry point, and vice versa. Improves visual connection between extracted data and pipeline inputs.

- [x] Identify components: PDF extraction field overlay + pipeline entry points
- [x] Add hover state that links extraction field name to entry point name (FieldHighlightContext)
- [x] Highlight corresponding entry point when hovering extraction field on PDF
- [x] Highlight corresponding extraction field when hovering pipeline entry point
- [x] Apply to both sub run viewer and template testing confirmation step

---

## 9. Sub Run Viewer / Template Testing Summary Page Rework

**Summary:** Rework the summary page layout in sub run viewer and template testing step to improve readability and make the information presentation clearer.

**Main issues:**
- Output channel display order is alphabetical (e.g., delivery_end before delivery_start) - should be logical/custom order
- Field colors don't have consistent meaning or rhyme/reason
- Specifics to be worked out during implementation

- [x] Define logical display order for output channels (group by category: identification, pickup, delivery, other)
- [x] Define consistent color scheme with meaning (unified blue styling for simplicity)
- [x] Implement custom ordering in summary view
- [x] Apply to both sub run viewer and template testing step
- [x] Ensure consistency between both views (shared utilities in `eto/utils/outputChannelFormatters.ts`)

---

## 10. Extraction Field Popup Overflow Fix

**Summary:** In the executed pipeline viewer, hovering over extraction fields shows a popup with extracted text. Long text gets cut off at the PDF edge.

**Approach Options:**

**(A) Text wrapping + auto-shift (Recommended start):**
- Wrap text at PDF boundary
- Auto-shift popup position when too close to edge (e.g., if field is pixels from right edge, shift popup left so text has room to wrap reasonably instead of one letter per line)
- Simpler to implement

**(B) Higher-level overlay:**
- Render popup as higher-level component in tree so it can extend beyond PDF bounds
- More complicated, may be harder to solve properly
- Consider as fallback if (A) doesn't work well

**Checklist:**
- [x] Identify extraction field popup component
- [x] Implement text wrapping within popup
- [x] Implement edge detection and auto-shift logic
- [x] Test with various text lengths and field positions near all edges
- [ ] If (A) insufficient, evaluate (B) approach

---

## 12. Navigate from Order Management Sub-Run Modal to ETO Page

**Summary:** From the order management page, users can view details of contributing sub-runs in a modal. Add navigation from this modal to the full ETO run page for that sub-run, allowing users to see other associated data (sibling sub-runs, email source, etc.).

- [x] Add "View in ETO" link/button to sub-run detail modal
- [x] Navigate to ETO run page with sub-run highlighted/expanded
- [x] Handle modal close / navigation flow

---

## 13. Improved Attachment Handling

**Plan:** [`docs/plans/improved-attachment-handling.md`](./plans/improved-attachment-handling.md)

**Summary:** Change attachment logic to capture ALL PDFs from source emails, not just the ones that contributed extracted data. This ensures forms like BOLs, PODs, and commercial invoices get attached even if they didn't have data extracted.

**Key Change:** Instead of tracing `pending_action_fields → output_execution → sub_run → run → pdf_file`, trace to the `source_email_id` and collect ALL PDFs from that email.

### Backend

- [ ] Add `get_by_source_email_id()` method to `EtoRunRepository`
- [ ] Update `_get_pdf_sources_for_action()` to collect all PDFs from source emails
- [ ] Add fallback for manual uploads (no source_email_id)
- [ ] Update logging to show email count + PDF count

### Testing

- [ ] Test with email that has 1 PDF (baseline)
- [ ] Test with email that has multiple PDFs, only some matched templates
- [ ] Test with manual upload (should work as before)
- [ ] Test with multiple emails contributing to same action
- [ ] Verify HTC receives all expected attachments

---

## 14. Email Filter Rules: Add NOT/Negation Option

**Summary:** Email ingestion config filter rules currently only support positive matching (e.g., "sender contains X"). Add negation option for each filter field so users can exclude emails matching certain criteria (e.g., "sender does NOT contain X").

**Approach:** Add `negate: bool = False` toggle to FilterRule type (not new operations like "not_contains"). Cleaner, backwards compatible, applies to all operations.

**Note:** Current OR logic means negated rules work for simple exclusion but not complex "include X but not Y" scenarios. AND logic could be future enhancement.

**Backend:**
- [ ] Add `negate: bool = False` to FilterRule in `shared/types/email_ingestion_configs.py`
- [ ] Update `check_filter_rule()` in `features/email/utils/filter_rules.py` to invert result when negate=True

**Frontend:**
- [ ] Add negate toggle to filter rule UI
- [ ] Display "does not contain" / "does not equal" etc. when negated
- [ ] Test with various positive and negative filter combinations

---

## 15. Create New Template from Existing Template

**Plan:** [`docs/plans/create-template-from-existing.md`](./plans/create-template-from-existing.md)

**Summary:** Allow creating a new template using an existing template as a starting point (distinct from versioning - this creates a fully separate template). Opens a separate modal over the template builder where users can browse templates, preview their structure, and copy over signature objects, extraction fields, and pipeline.

**Key Points:**
- Separate modal overlays template builder (not embedded in builder flow)
- Left panel: filterable template list; Right panel: PDF preview with objects overlaid
- Toggle to view source PDF or new PDF with applied objects
- Read-only pipeline viewer
- Uses each template's current version
- Signature objects: only selected if they exist on new PDF (uses existing matching logic)
- Extraction fields and pipeline: copied exactly as-is

### Backend
- [x] Verify existing API provides template structure data (sig objects, fields, pipeline)
- [x] If needed, add endpoint for template structure
- [x] Ensure signature object matching logic is accessible/reusable
- [x] Add page_count to template list API response

### Frontend - Template Builder Integration
- [x] Add "Copy from Existing Template" button after step 1 (page selection)
- [x] Wire button to open copy modal
- [x] Implement state update when copy is performed

### Frontend - Template Copy Modal
- [x] Create modal component (left/right panel layout)
- [x] Implement template list with filtering (like main templates page)
- [x] Implement PDF preview with signature object + extraction field overlays
- [ ] Implement source/new PDF toggle (deferred - not needed for MVP)
- [ ] Implement read-only pipeline viewer (deferred - not needed for MVP)
- [x] Implement "Copy Structure" action

### Frontend - State Update Logic
- [x] Implement signature object matching against new PDF
- [x] Update selectedSignatureObjects based on matches
- [x] Deep copy extraction fields from source template
- [x] Deep copy pipeline definition from source template

### Testing
- [x] Test with template that has matching signature objects
- [x] Test with template that has NO matching signature objects
- [x] Test extraction field and pipeline copying
- [ ] Test toggle between source/new PDF views (deferred)
- [x] Test modal close without copying (no side effects)

---

## 16. HTC Access Database Time Format Parsing (Bug Fix)

**Summary:** The HTC Access database stores times in multiple inconsistent formats/regex styles. This causes errors when displaying old times or comparing them to new times in update-type pending actions. Need robust time parsing that handles all Access time format variations.

**Note:** Specific formats to be cataloged during implementation by examining production database.

- [ ] Identify where HTC time values are read/parsed
- [ ] Query production database to catalog all time format variations
- [ ] Implement flexible time parser that handles all discovered formats
- [ ] Add fallback/error handling for unknown formats
- [ ] Test with various time format samples from production data

---

## 17. Sub-Run Modal: View Matched Template Button

**Summary:** Add a button in the sub-run detail modal to navigate to the template it was matched to. Makes it easy to view or edit the template when issues are found.

- [x] Add "View Template" button to sub-run detail modal
- [x] Navigate to template detail/edit page
- [x] Handle case where template was deleted or sub-run has no matched template (button hidden when no template)

---

## 18. Manual Field Entry for Pending Actions

**Plan:** [`docs/plans/manual-field-entry.md`](./plans/manual-field-entry.md)

**Summary:** Allow users to manually add field values to pending actions. Manual entries are treated identically to extracted values - they create a new field option, trigger conflict resolution if values already exist, and become auto-selected. Works for any order field on any action type (create/update).

**Key Decisions:**
- Manual entry = another extraction source (same conflict behavior)
- User-provided values stored with `output_execution_id = NULL`
- "Add Field" button → field picker (all fields) → type-specific input UI
- Field types: simple text (inline), address (modal with HTC search + create), datetime (date + start/end time), dims (variable rows form)
- Design must be extensible for future field types
- `customer_id` and `hawb` not editable (from templates)

### Backend

- [ ] Implement `set_user_value()` in `OrderManagementService`
- [ ] Add field type validation logic
- [ ] Add `POST /pending-actions/{id}/fields` endpoint
- [ ] Add request/response schemas
- [ ] Handle address creation in HTC (for new addresses)
- [ ] Test conflict behavior with existing values
- [ ] Test status recalculation after adding field

### Frontend - Core

- [ ] Add "Add Field" button to pending action detail view
- [ ] Create `AddFieldModal` component (field picker showing all fields)
- [ ] Implement field type → input component mapping (extensible)
- [ ] Create `useAddFieldValue` API hook
- [ ] Wire up submit flow to invalidate/refresh pending action data

### Frontend - Input Components

- [ ] Create `TextFieldInput` component
- [ ] Create `DateTimeFieldInput` component (date + start/end time, same day)
- [ ] Create `AddressSelectionModal` component
  - [ ] HTC address search
  - [ ] Results display
  - [ ] Create new address form
- [ ] Create `DimsEntryForm` component
  - [ ] Dynamic row add/remove
  - [ ] Row inputs: qty, length, width, height, weight
  - [ ] Validation (at least one row)

### Testing

- [ ] Test adding field to action with no existing values
- [ ] Test adding field that already has values (conflict behavior)
- [ ] Test each field type input
- [ ] Test address search and creation
- [ ] Test dims form with multiple rows
- [ ] Test status transitions (incomplete → ready)
- [ ] Test with both create and update action types

---

## 19. Merge Adjacent PDF Text Boxes (Bug Fix)

**Summary:** Some PDFs have text fragmented into multiple adjacent boxes (e.g., `[O][r][de][r]` instead of `[Order]`) due to how the sender built the PDF. If text boxes share a horizontal border (are touching), they should be merged into a single continuous text box during PDF object extraction.

**Detection:** Two text boxes should merge if they share a horizontal border (right edge of box A touches left edge of box B, and vertical positions overlap).

- [x] Identify where PDF objects are extracted (likely pdfplumber processing)
- [x] Implement horizontal adjacency detection for text boxes
- [x] Merge adjacent boxes: combine text, extend bbox to cover both
- [x] Handle chains of multiple adjacent boxes (A-B-C should become one)
- [x] Test with PDFs that have fragmented text objects

---

## 20. ETO Bulk Actions

**Plan:** [`docs/plans/eto-bulk-actions.md`](./plans/eto-bulk-actions.md)

**Summary:** Add bulk action UI to the ETO page. Backend already supports bulk reprocess, skip, and delete operations. Frontend needs selection UI and action buttons.

**Key Decisions:**
- Checkbox on each row + "Select all" checkbox in header
- Action buttons at top of list, next to "Upload PDF" button
- Buttons become active when runs selected, show valid count (e.g., "Delete (3 of 5)")
- "Select all" selects only loaded/visible rows
- Confirmation dialogs for skip and delete (not reprocess)
- No checkbox on email headers (after #11) - only individual runs

**Backend (Already Exists):**
- `POST /eto-runs/reprocess` - any status
- `POST /eto-runs/skip` - only failure/needs_template
- `DELETE /eto-runs` - only skipped

### Frontend - Selection

- [ ] Add selection state management (Set of selected IDs)
- [ ] Add checkbox column to `EtoRunsTable`
- [ ] Implement row checkbox (toggle individual)
- [ ] Implement header checkbox (select all visible)
- [ ] Handle indeterminate state (some selected)
- [ ] Clear selection after page change or filter change

### Frontend - Action Buttons

- [ ] Add bulk action buttons next to "Upload PDF" button
- [ ] Calculate valid counts for each action based on selected run statuses
- [ ] Display counts on buttons when > 0 valid
- [ ] Disable buttons when no valid runs for that action

### Frontend - Confirmation & Execution

- [ ] Create confirmation dialog for Skip action
- [ ] Create confirmation dialog for Delete action
- [ ] Implement `useBulkReprocess` hook
- [ ] Implement `useBulkSkip` hook
- [ ] Implement `useBulkDelete` hook
- [ ] Clear selection after successful action
- [ ] Show success toast after action completes

### Testing

- [ ] Test selecting individual runs
- [ ] Test select all / deselect all
- [ ] Test action button states with mixed statuses
- [ ] Test reprocess action (no confirmation)
- [ ] Test skip action with confirmation
- [ ] Test delete action with confirmation
- [ ] Test that invalid runs are excluded from action
- [ ] Test selection clears after action

---

