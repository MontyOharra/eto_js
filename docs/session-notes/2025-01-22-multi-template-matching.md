# Session 2025-01-22: Multi-Template Matching Algorithm Design

<!-- QUICK START INSTRUCTIONS FOR NEXT SESSION:

After restarting PC, simply say:
"Read the multi-template-matching-implementation.md file"

Claude will automatically:
1. Read the implementation guide
2. Apply all code changes to the correct files
3. Verify syntax and imports
4. Report completion status

That's it! The implementation file has embedded instructions for Claude.

-->

## Session Overview

Designed and implemented a new multi-template matching algorithm to replace the current single-template matching system. The new algorithm enables multi-template support where a single PDF can match multiple different templates across different page ranges.

---

## What We Accomplished

### 1. **Comprehensive Codebase Analysis**

Performed deep exploration of the ETO system to understand:
- **Current template matching flow**: PDF upload → Object extraction → ETO Run creation → Template matching → Data extraction → Pipeline execution
- **Existing algorithm**: Single template per PDF, exact page count match required, binary match/no-match
- **Code architecture**: Service layer pattern, repository pattern, domain types
- **Current limitations**: Cannot handle multi-page PDFs with different document types

**Key Files Analyzed:**
- `server/src/features/eto_runs/service.py` - ETO orchestration
- `server/src/features/pdf_templates/service.py` - Template matching logic
- `server/src/features/pdf_files/service.py` - PDF object extraction
- `server/src/shared/types/pdf_templates.py` - Domain types

### 2. **Algorithm Requirements Clarification**

**User Requirements:**
- Process PDF page-by-page instead of whole document
- Template signature objects must be **complete subset** of PDF objects (if template has object X but PDF doesn't → not a match)
- Support multi-page templates (e.g., 2-page invoice template must match consecutive pages)
- Greedy page consumption: once pages are matched, they're consumed (no overlap)
- Return two arrays:
  - **Matches**: Array of `TemplateMatch` (template_id, version_id, matched_pages)
  - **Unmatched pages**: Single array of all pages that didn't match any template (can be non-consecutive)

**Design Decisions:**
1. ✅ Remove page count restriction (old algorithm required exact match)
2. ✅ Use all objects for matching (no shortcuts - accuracy first)
3. ✅ All signature objects must match across all template pages
4. ✅ First match wins with greedy consumption (no overlapping matches)
5. ✅ Keep old `match_template()` method for backward compatibility
6. ✅ One unmatched sub-run (not one per unmatched page)
7. ✅ Implement in same `service.py` file (not separate service)

### 3. **New Data Structures Designed**

Created new domain types in `server/src/shared/types/pdf_templates.py`:

```python
@dataclass(frozen=True)
class TemplateMatch:
    """Single template match for consecutive page range"""
    template_id: int
    version_id: int
    matched_pages: list[int]  # Always consecutive, e.g., [1, 2, 3]

@dataclass(frozen=True)
class TemplateMatchingResult:
    """Complete multi-template matching result"""
    matches: list[TemplateMatch]  # Ordered by page appearance
    unmatched_pages: list[int]  # Can be non-consecutive
```

### 4. **New Algorithm Implementation**

**Created 4 new methods for `PdfTemplateService`:**

1. **`_filter_objects_by_page(pdf_objects, page_num) → PdfObjects`**
   - Extract objects for specific page from PdfObjects
   - Filters all object types (text, graphics, images, tables)

2. **`_group_objects_by_page(pdf_objects) → dict[int, PdfObjects]`**
   - Group PDF objects by page number
   - Returns mapping: page_num → PdfObjects for that page

3. **`_is_complete_multi_page_match(pdf_file, start_page, template_version, template_page_count) → bool`**
   - Core multi-page verification logic
   - Groups template objects by page
   - Checks each template page against corresponding PDF page
   - Reuses existing `_is_complete_subset_match()` method

4. **`match_templates_multi_page(pdf_file) → TemplateMatchingResult`**
   - Main entry point for new algorithm
   - Page-by-page processing with greedy consumption
   - Returns matches + unmatched_pages
   - Reuses existing ranking logic (`_find_best_match()`)

**Algorithm Flow:**
```
current_page = 1
while current_page <= total_pages:
    candidates = find_templates_that_match_starting_at(current_page)

    if no candidates:
        add current_page to unmatched_pages
        current_page += 1
    else:
        best_match = find_best_match(candidates)
        add match to matches array
        current_page += matched_page_count  # Greedy consumption
```

---

## Implementation Status

### ✅ **Completed:**
1. ✅ Designed new data structures (`TemplateMatch`, `TemplateMatchingResult`)
2. ✅ Implemented helper functions (`_filter_objects_by_page`, `_group_objects_by_page`)
3. ✅ Implemented multi-page match verification (`_is_complete_multi_page_match`)
4. ✅ Implemented main algorithm (`match_templates_multi_page`)
5. ✅ Created comprehensive documentation in `docs/multi-template-matching-implementation.md`

### ⏸️ **Blocked (File Write Issues):**
- Could not write code to actual Python files due to file lock issues
- All code is documented in markdown file ready to be applied
- Need to restart PC to clear file locks

### ❌ **Not Started:**
1. ❌ Add new data structures to `pdf_templates.py`
2. ❌ Add new methods to `PdfTemplateService` class
3. ❌ Update `EtoRunsService._process_template_matching()` to use new algorithm
4. ❌ Create EtoSubRuns based on `TemplateMatchingResult`
5. ❌ Write unit tests
6. ❌ Integration testing with real PDFs

---

## Next Steps (When Resuming)

### **Step 1: Apply Code Changes**

After restarting PC, apply the code from `docs/multi-template-matching-implementation.md`:

1. **Add to `server/src/shared/types/pdf_templates.py`:**
   - Add `TemplateMatch` dataclass
   - Add `TemplateMatchingResult` dataclass

2. **Add to `server/src/features/pdf_templates/service.py`:**
   - Import new types: `from shared.types.pdf_templates import TemplateMatch, TemplateMatchingResult`
   - Import `PdfFile`: `from shared.types.pdf_files import PdfFile`
   - Add `_filter_objects_by_page()` method
   - Add `_group_objects_by_page()` method
   - Add `_is_complete_multi_page_match()` method
   - Add `match_templates_multi_page()` method

### **Step 2: Integration with EtoRunsService**

Update `server/src/features/eto_runs/service.py`:

**Current code (line ~702):**
```python
def _process_template_matching(self, run_id: int) -> tuple[int, int] | None:
    # ... existing code ...

    # OLD: Single template matching
    match_result = self.pdf_template_service.match_template(
        pdf_objects=pdf_objects,
        pdf_page_count=pdf_page_count
    )
    # Returns: (template_id, version_id) OR None
```

**New code (to implement):**
```python
def _process_template_matching(self, run_id: int) -> TemplateMatchingResult:
    # ... existing setup code ...

    # NEW: Multi-template matching
    matching_result = self.pdf_template_service.match_templates_multi_page(
        pdf_file=pdf_file
    )
    # Returns: TemplateMatchingResult

    # Create EtoSubRuns based on matching_result
    for match in matching_result.matches:
        self._create_sub_run(
            eto_run_id=run_id,
            matched_pages=match.matched_pages,
            template_version_id=match.version_id,
            is_unmatched_group=False
        )

    # Create single unmatched sub-run if there are unmatched pages
    if matching_result.unmatched_pages:
        self._create_sub_run(
            eto_run_id=run_id,
            matched_pages=matching_result.unmatched_pages,
            template_version_id=None,
            is_unmatched_group=True
        )

    return matching_result
```

**NOTE:** Need to create `_create_sub_run()` helper method or use sub-run repository directly.

### **Step 3: Database Schema Verification**

Verify `eto_sub_runs` table has required columns:
- `eto_run_id` (FK to eto_runs)
- `matched_pages` (JSON array)
- `template_version_id` (nullable FK to pdf_template_versions)
- `is_unmatched_group` (boolean)
- `status` (enum)
- `sequence` (int for ordering)

### **Step 4: Update Return Type**

Change `_process_template_matching()` return type and update all call sites:
- Update method signature
- Update `process_run()` to handle new return type
- Update error handling logic

### **Step 5: Testing Strategy**

1. **Unit Tests:**
   - Test `_filter_objects_by_page()` with various object types
   - Test `_group_objects_by_page()` with multi-page PDFs
   - Test `_is_complete_multi_page_match()` with:
     - Single-page templates
     - Multi-page templates
     - Partial matches (should fail)
   - Test `match_templates_multi_page()` with:
     - All pages match one template
     - Multiple templates across pages
     - Some unmatched pages
     - All unmatched pages

2. **Integration Tests:**
   - Upload PDF with multiple document types (invoice + receipt)
   - Verify correct sub-runs created
   - Verify extraction runs for each sub-run
   - Verify pipeline execution per sub-run

3. **Real-World Scenarios:**
   - 5-page PDF: pages 1-2 = invoice, pages 3-4 = receipt, page 5 = unmatched
   - 10-page PDF: all same template
   - 3-page PDF: all unmatched

---

## Key Design Principles Followed

1. **Accuracy over performance** - No shortcuts, check all objects
2. **Reuse existing code** - Leveraged `_is_complete_subset_match()`, `_find_best_match()`, all `_match_*()` methods
3. **Backward compatibility** - Kept old `match_template()` method
4. **Greedy consumption** - Prevents overlapping matches, simplifies logic
5. **Single unmatched sub-run** - Cleaner than one per page
6. **Immutable domain types** - `@dataclass(frozen=True)` for all new types

---

## Important Code Patterns to Maintain

### **Service Layer Pattern:**
```python
# Services return domain types, never ORM models
def match_templates_multi_page(self, pdf_file: PdfFile) -> TemplateMatchingResult:
    # Business logic here
    return TemplateMatchingResult(matches=..., unmatched_pages=...)
```

### **Repository Usage:**
```python
# Always use repositories for data access
active_templates = self.template_repository.list_templates(status="active")
current_version = self.version_repository.get_by_id(template.current_version_id)
```

### **Error Handling:**
```python
try:
    # Template matching logic
except Exception as e:
    logger.error(f"Error in multi-page template matching: {e}", exc_info=True)
    # Return safe default (all pages unmatched)
    return TemplateMatchingResult(matches=[], unmatched_pages=list(range(1, total_pages + 1)))
```

### **Logging:**
```python
logger.info(f"Starting multi-page template matching for PDF {pdf_file.id}")
logger.debug(f"Template {template.id}: MATCH for pages {start_page}-{end_page}")
logger.warning(f"Template {template.id} source PDF has no page_count, skipping")
logger.monitor(f"Match recorded: Template {template.id} for pages {matched_pages}")
```

---

## Files Modified/Created

### **Created:**
- `docs/multi-template-matching-implementation.md` - Complete implementation guide
- `docs/session-notes/2025-01-22-multi-template-matching.md` - This document

### **To Modify (Next Session):**
- `server/src/shared/types/pdf_templates.py` - Add new dataclasses
- `server/src/features/pdf_templates/service.py` - Add new methods
- `server/src/features/eto_runs/service.py` - Update to use new algorithm

### **Reference Files (Read Only):**
- `server/src/features/eto_runs/service.py` - Current implementation
- `server/src/features/pdf_files/service.py` - PDF extraction logic
- `server/src/shared/types/pdf_files.py` - PdfObjects definition

---

## Critical Context for Next Session

### **Why File Writes Failed:**
- File lock issues prevented writing to Python files
- Likely caused by VS Code language server, Python processes, or FastAPI dev server
- Created markdown documentation instead as workaround
- **Solution:** Restart PC, then apply code from markdown file

### **Algorithm Correctness Validation:**
- User confirmed: Template objects must be **subset** of PDF objects (not vice versa)
- User confirmed: Greedy consumption with best-match selection
- User confirmed: Single unmatched sub-run (not one per page)
- User confirmed: Remove page count restriction

### **Integration Points:**
- `EtoRunsService._process_template_matching()` needs major refactor
- Need to create EtoSubRuns instead of single run status
- Each sub-run gets own extraction + pipeline execution
- Unmatched sub-run should have `status='needs_template'`

### **Testing Priority:**
- Start with unit tests for helper functions
- Test multi-page matching with 2-page template
- Test with real PDF that has multiple document types
- Verify sub-run creation logic

---

## Questions to Address Next Session

1. **Sub-Run Creation:**
   - Does `EtoSubRunRepository` already exist?
   - What's the create method signature?
   - Do we need to manually set `sequence` field?

2. **Extraction & Pipeline:**
   - Does extraction automatically run for each sub-run?
   - Do we need to update extraction logic to handle page ranges?
   - How does pipeline execution work with sub-runs?

3. **Status Aggregation:**
   - How is parent `EtoRun.status` calculated from sub-runs?
   - If one sub-run fails, does entire run fail?
   - How do we handle `needs_template` sub-runs?

4. **Frontend Impact:**
   - Does UI already support sub-runs?
   - Do we need to update API responses?
   - Are there any breaking changes to consider?

---

## Estimated Work Remaining

- **Code Application:** 30 minutes (copy from markdown, test imports)
- **EtoRunsService Integration:** 1-2 hours (sub-run creation, status handling)
- **Unit Tests:** 2-3 hours (comprehensive test coverage)
- **Integration Testing:** 1-2 hours (real PDFs, end-to-end flow)
- **Bug Fixes & Refinement:** 1-2 hours (edge cases, error handling)

**Total:** ~6-10 hours of focused development work

---

## Success Criteria

The implementation will be complete when:

1. ✅ All code from markdown file successfully applied to Python files
2. ✅ No import errors or syntax errors
3. ✅ Unit tests pass for all new methods
4. ✅ Integration test: Upload multi-document PDF, verify sub-runs created
5. ✅ Integration test: Each sub-run has correct extraction results
6. ✅ Integration test: Each sub-run executes correct pipeline
7. ✅ Integration test: Unmatched pages create `needs_template` sub-run
8. ✅ Old `match_template()` still works (backward compatibility)
9. ✅ No regressions in existing single-template matching

---

## References

- **Implementation Guide:** `docs/multi-template-matching-implementation.md`
- **Database Schema:** `docs/new-full-database-design.md`
- **API Design:** `docs/api-design-eto-multi-template.md`
- **Database Redesign:** `docs/database-redesign-multi-template-matching.md`
- **Session History:** `docs/session-notes/CHANGELOG.md`

---

## Notes for Future Optimization

**Current Algorithm is O(T × P) where:**
- T = number of active templates
- P = number of PDF pages

**Potential Optimizations (defer until after working implementation):**
1. Cache `_group_objects_by_page()` result per PDF
2. Early rejection by checking first page before multi-page verification
3. Index templates by signature object types for faster filtering
4. Parallel template matching (if bottleneck identified)

**Remember: Accuracy first, performance second.**

---

## End of Session

**Status:** Ready to resume after PC restart
**Next Action:** Apply code from `docs/multi-template-matching-implementation.md` to actual Python files
**Blocker:** File lock issues (resolved by PC restart)
