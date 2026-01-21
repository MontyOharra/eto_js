# TODO - Feature Implementation Checklist

This document tracks planned features with implementation checklists. Each feature has a detailed plan document in `docs/plans/`.

## Progress Tracker

| # | Item | Priority | Complexity | Plan | Implement | Test |
|---|------|:--------:|:----------:|:----:|:---------:|:----:|
| 3 | Field Processing Error Handling (Decoupled) | 1 | 4 | [x] | [ ] | [ ] |
| 13 | Improved Attachment Handling | 1 | 3 | [x] | [ ] | [ ] |
| 15 | Create Template from Existing | 1 | 4 | [x] | [ ] | [ ] |
| 19 | Merge Adjacent PDF Text Boxes | 1 | 2 | [x] | [ ] | [ ] |
| 9 | Summary Page Rework | 2 | 3 | [x] | [ ] | [ ] |
| 11 | ETO Page: Group Runs by Email | 2 | 5 | [ ] | [ ] | [ ] |
| 12 | Navigate from Order Management to ETO | 2 | 1 | [x] | [ ] | [ ] |
| 16 | HTC Time Format Parsing | 2 | 2 | [x] | [ ] | [ ] |
| 18 | Manual Field Entry for Pending Actions | 2 | 3 | [ ] | [ ] | [ ] |
| 1 | Template Draft Saving | 3 | 4 | [x] | [ ] | [ ] |
| 6 | Browse Template Matches / Set New Base | 3 | 3 | [x] | [ ] | [ ] |
| 14 | Email Filter Rules: NOT/Negation | 3 | 2 | [x] | [ ] | [ ] |
| 17 | Sub-Run Modal: View Template Button | 4 | 1 | [x] | [ ] | [ ] |
| 2 | New Pipeline Modules (Math + LLM) | 5 | 3 | [x] | [ ] | [ ] |
| 4 | Address Matching with Company Name | 5 | 3 | [x] | [ ] | [ ] |
| 5 | Extraction Field Rename Syncs to Pipeline | 5 | 2 | [x] | [ ] | [ ] |
| 7 | Conditional Error/Halt Module | 5 | 2 | [x] | [ ] | [ ] |
| 8 | Extraction Field ↔ Pipeline Hover Highlighting | 5 | 2 | [x] | [ ] | [ ] |
| 10 | Extraction Field Popup Overflow Fix | 5 | 1 | [x] | [ ] | [ ] |

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

- [ ] Create `math_add.py` - sum all inputs
- [ ] Create `math_subtract.py` - subtract inputs in order
- [ ] Create `math_multiply.py` - product of all inputs
- [ ] Create `math_divide.py` - divide inputs in order (with zero-check)
- [ ] All modules: 2-unlimited inputs, 1 float output
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
- [ ] Add `processing_status`, `processing_error`, `raw_value` columns to `pending_action_fields`
- [ ] Create migration, update types

**Backend:**
- [ ] Update ETO service to not fail sub-run on order management errors
- [ ] Refactor `process_output_execution()` to never raise, handle per-field
- [ ] Implement cascading address resolution (usaddress → LLM fallback)

**API/Frontend:**
- [ ] Update API schemas with processing status fields
- [ ] Display field processing errors in UI
- [ ] Consider retry/manual fix UI for failed fields

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

- [ ] Identify components: PDF extraction field overlay + pipeline entry points
- [ ] Add hover state that links extraction field name to entry point name
- [ ] Highlight corresponding entry point when hovering extraction field on PDF
- [ ] Highlight corresponding extraction field when hovering pipeline entry point
- [ ] Apply to both sub run viewer and template testing confirmation step

---

## 9. Sub Run Viewer / Template Testing Summary Page Rework

**Summary:** Rework the summary page layout in sub run viewer and template testing step to improve readability and make the information presentation clearer.

**Main issues:**
- Output channel display order is alphabetical (e.g., delivery_end before delivery_start) - should be logical/custom order
- Field colors don't have consistent meaning or rhyme/reason
- Specifics to be worked out during implementation

- [ ] Define logical display order for output channels (group by category: identification, pickup, delivery, cargo, etc.)
- [ ] Define consistent color scheme with meaning
- [ ] Implement custom ordering in summary view
- [ ] Apply to both sub run viewer and template testing step
- [ ] Ensure consistency between both views

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
- [ ] Identify extraction field popup component
- [ ] Implement text wrapping within popup
- [ ] Implement edge detection and auto-shift logic
- [ ] Test with various text lengths and field positions near all edges
- [ ] If (A) insufficient, evaluate (B) approach

---

## 11. ETO Page: Group Runs by Email (Major Rework)

**Summary:** Restructure the main ETO page to group runs by source email. Each row represents an email (with summary info), expandable to show all PDF runs from that email. Allows users to easily see "all these sub-runs came from one email." This is a significant change affecting filtering, dashboard layout, and data presentation.

**Considerations for detailed planning:**
- Current: each row = one ETO run (one PDF)
- Proposed: each row = one email, expandable to show child runs
- How to handle manual/non-email runs (no email source)?
- Filtering changes: filter by email metadata vs run metadata
- Dashboard stats: aggregate by email or by run?
- Status rollup: how to show email-level status when runs have mixed statuses?

**Checklist:**
- [ ] Design new data structure/API for email-grouped view
- [ ] Handle non-email runs (manual uploads, etc.)
- [ ] Implement email row with summary info (sender, subject, date, run count, status rollup)
- [ ] Implement expandable section showing child runs
- [ ] Rework filtering to support email-level and run-level filters
- [ ] Update dashboard/stats presentation
- [ ] Ensure performance with large email/run counts

---

## 12. Navigate from Order Management Sub-Run Modal to ETO Page

**Summary:** From the order management page, users can view details of contributing sub-runs in a modal. Add navigation from this modal to the full ETO run page for that sub-run, allowing users to see other associated data (sibling sub-runs, email source, etc.).

- [ ] Add "View in ETO" link/button to sub-run detail modal
- [ ] Navigate to ETO run page with sub-run highlighted/expanded
- [ ] Handle modal close / navigation flow

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
- [ ] Verify existing API provides template structure data (sig objects, fields, pipeline)
- [ ] If needed, add endpoint for template structure
- [ ] Ensure signature object matching logic is accessible/reusable

### Frontend - Template Builder Integration
- [ ] Add "Copy from Existing Template" button after step 1 (page selection)
- [ ] Wire button to open copy modal
- [ ] Implement state update when copy is performed

### Frontend - Template Copy Modal
- [ ] Create modal component (left/right panel layout)
- [ ] Implement template list with filtering (like main templates page)
- [ ] Implement PDF preview with signature object + extraction field overlays
- [ ] Implement source/new PDF toggle
- [ ] Implement read-only pipeline viewer
- [ ] Implement "Copy Structure" action

### Frontend - State Update Logic
- [ ] Implement signature object matching against new PDF
- [ ] Update selectedSignatureObjects based on matches
- [ ] Deep copy extraction fields from source template
- [ ] Deep copy pipeline definition from source template

### Testing
- [ ] Test with template that has matching signature objects
- [ ] Test with template that has NO matching signature objects
- [ ] Test extraction field and pipeline copying
- [ ] Test toggle between source/new PDF views
- [ ] Test modal close without copying (no side effects)

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

- [ ] Add "View Template" button to sub-run detail modal
- [ ] Navigate to template detail/edit page
- [ ] Handle case where template was deleted or sub-run has no matched template

---

## 18. Manual Field Entry for Pending Actions

**Summary:** Allow users to manually add or edit field values on pending actions. Useful for correcting extraction errors, filling in missing data, or providing values when automated processing fails. The database schema already supports user-provided values (`output_execution_id = NULL`), but the service layer and frontend need to be built out.

**Use Cases:**
- Fix incorrect extracted data
- Provide value when field processing failed
- Add data that wasn't on the original form
- Override automated values with manual corrections

- [ ] Implement service method for setting user-provided field values
- [ ] Add API endpoint for manual field entry
- [ ] Build frontend UI for adding/editing field values
- [ ] Integrate with existing conflict resolution system
- [ ] Handle validation of manually entered values
- [ ] Test manual entry alongside automated extraction

---

## 19. Merge Adjacent PDF Text Boxes (Bug Fix)

**Summary:** Some PDFs have text fragmented into multiple adjacent boxes (e.g., `[O][r][de][r]` instead of `[Order]`) due to how the sender built the PDF. If text boxes share a horizontal border (are touching), they should be merged into a single continuous text box during PDF object extraction.

**Detection:** Two text boxes should merge if they share a horizontal border (right edge of box A touches left edge of box B, and vertical positions overlap).

- [ ] Identify where PDF objects are extracted (likely pdfplumber processing)
- [ ] Implement horizontal adjacency detection for text boxes
- [ ] Merge adjacent boxes: combine text, extend bbox to cover both
- [ ] Handle chains of multiple adjacent boxes (A-B-C should become one)
- [ ] Test with PDFs that have fragmented text objects

---

