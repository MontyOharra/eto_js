# TODO - Feature Implementation Checklist

This document tracks planned features with implementation checklists. Each feature has a detailed plan document in `docs/plans/`.

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

## 3. Address Parsing Error Handling (Bug Fix)

**Summary:** Address parsing errors (e.g., usaddress library finds ambiguous data like two cities) currently fail the entire sub-run, making all extracted data unprocessable. Should handle errors gracefully so other fields remain usable and the user doesn't have to manually rebuild everything.

- [ ] Identify where address parsing failures cause sub-run failure
- [ ] Implement graceful error handling for address parsing
- [ ] Allow sub-run to continue with other fields when address parsing fails
- [ ] Surface address parsing errors to user for manual resolution
- [ ] Test with malformed/ambiguous address inputs

---

## 4. Address Matching with Company Name Tiebreaker

**Summary:** When matching output address channels to database addresses, multiple similar addresses may exist. Currently picks the first match arbitrarily. Should use company name matching as a tiebreaker to select the best address when multiple candidates exist.

- [ ] Identify address matching logic in HTC integration
- [ ] Add company name comparison when multiple address matches found
- [ ] Implement scoring/ranking for address + company name similarity
- [ ] Select best match based on combined address + company score
- [ ] Test with multiple similar addresses and varying company names

---

## 5. Extraction Field Rename Syncs to Pipeline (Bug Fix)

**Summary:** In the template builder, renaming an extraction field doesn't update the pipeline entry points that reference that field name. This breaks the pipeline. Renaming should propagate to pipeline entry points automatically.

- [ ] Identify where extraction field renames occur in template builder
- [ ] Identify pipeline entry point data structure (references field names)
- [ ] Implement rename propagation from extraction fields to pipeline entry points
- [ ] Test renaming fields and verifying pipeline remains valid

---

## 6. Browse Template Matches and Set New Base PDF

**Summary:** Template viewing page should allow browsing PDFs that have matched to that template. If a more complete example is found (e.g., a form with 3 piece/weight rows instead of 1), user can set it as the new base PDF and create a new template version from it. Helps handle discovering more complete form variants through actual usage.

- [ ] Add UI to browse PDFs matched to a template (query by template_version_id)
- [ ] Display match thumbnails/previews for quick comparison
- [ ] Add "Use as new base" action on a matched PDF
- [ ] Flow: selecting new base opens template builder with that PDF pre-loaded
- [ ] Create new template version with updated extraction fields/pipeline

---

## 7. Conditional Error/Halt Module

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

- [ ] Review current summary page layout and identify pain points
- [ ] Design improved layout for better readability
- [ ] Implement updated summary view in sub run viewer
- [ ] Implement updated summary view in template testing step
- [ ] Ensure consistency between both views

---

## 10. Extraction Field Popup Overflow Fix

**Summary:** In the executed pipeline viewer, hovering over extraction fields shows a popup with extracted text. Long text gets cut off at the PDF edge. Fix by either (A) wrapping text at PDF boundary, or (B) rendering popup as higher-level overlay in component tree so it can extend beyond PDF bounds.

- [ ] Identify extraction field popup component
- [ ] Choose approach: text wrap vs higher-level overlay
- [ ] Implement fix so long text is fully visible
- [ ] Test with various text lengths and field positions (edge cases near PDF borders)

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

## 13. Improved Attachment Handling for Non-Data Forms

**Summary:** Some forms need to be attached to orders even if they don't contain useful processing data. Two approaches:

**(A) Quick approach - Email-based attachments:**
Instead of attaching only PDFs from contributing sub-runs, get all unique source emails from those sub-runs and attach ALL PDFs from those emails. Catches forms that didn't contribute data but were part of the same email.

**(B) Robust approach - Attachment-only templates:**
New template type for forms that have no extractable data but contain a HAWB. These would match to pending actions by HAWB for attachment purposes only, without contributing field data.

**Checklist (A - Email-based):**
- [ ] Modify attachment logic to collect unique source emails from contributing sub-runs
- [ ] Query all PDFs associated with those emails
- [ ] Attach all PDFs (not just contributing ones)

**Checklist (B - Attachment-only templates):**
- [ ] Add new template type/flag for "attachment-only"
- [ ] Define minimal extraction (HAWB only) for matching
- [ ] Link matched attachment-only sub-runs to pending actions
- [ ] Include in attachment processing without contributing field data

---

## 14. Email Filter Rules: Add NOT/Negation Option

**Summary:** Email ingestion config filter rules currently only support positive matching (e.g., "sender contains X"). Add negation option for each filter field so users can exclude emails matching certain criteria (e.g., "sender does NOT contain X").

- [ ] Update filter rule data structure to include negation flag
- [ ] Update filter rule UI to toggle between "contains" / "does not contain" (or similar)
- [ ] Update filter evaluation logic to handle negated rules
- [ ] Apply to all filter fields (sender, subject, etc.)
- [ ] Test combined positive and negative filters

---

## 15. Create New Template from Existing Template

**Summary:** Allow creating a new template using an existing template as a starting point (distinct from versioning - this creates a fully separate template). Useful for similar forms with common elements (e.g., same header, different body).

**Behavior when loading source template onto new PDF:**
- **Signature objects**: Check if each object exists on the new PDF. Keep if found, discard if not.
- **Extraction fields**: Load exactly as-is from source template
- **Pipeline**: Load exactly as-is from source template

- [ ] Add UI to select source template when building new template
- [ ] Implement signature object matching between source template and new PDF
- [ ] Keep matched signature objects, discard unmatched
- [ ] Load extraction fields from source template
- [ ] Load pipeline definition from source template
- [ ] Handle edge cases (no matching objects, all objects match, etc.)
- [ ] User proceeds with normal template building flow from there

---

## 16. HTC Access Database Time Format Parsing (Bug Fix)

**Summary:** The HTC Access database stores times in multiple inconsistent formats/regex styles. This causes errors when displaying old times or comparing them to new times in update-type pending actions. Need robust time parsing that handles all Access time format variations.

- [ ] Identify where HTC time values are read/parsed
- [ ] Catalog the various time formats found in Access database
- [ ] Implement flexible time parser that handles all known formats
- [ ] Add fallback/error handling for unknown formats
- [ ] Test with various time format samples from production data

---

## 17. Sub-Run Modal: View Matched Template Button

**Summary:** Add a button in the sub-run detail modal to navigate to the template it was matched to. Makes it easy to view or edit the template when issues are found.

- [ ] Add "View Template" button to sub-run detail modal
- [ ] Navigate to template detail/edit page
- [ ] Handle case where template was deleted or sub-run has no matched template

---

