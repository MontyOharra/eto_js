# Multi-Template Matching Implementation

<!-- INSTRUCTIONS FOR CLAUDE CODE ASSISTANT:

When the user says "read the multi-template-matching-implementation.md file", you should:

1. Read this entire document to understand the implementation
2. Apply the code changes in the following order:
   a. Add new dataclasses to server/src/shared/types/pdf_templates.py (Section 1)
   b. Add imports to server/src/features/pdf_templates/service.py (Section 5)
   c. Add helper methods to PdfTemplateService class (Section 2)
   d. Add core matching method to PdfTemplateService class (Section 3)
   e. Add main algorithm method to PdfTemplateService class (Section 4)
3. After applying code, verify:
   - No syntax errors
   - All imports resolve correctly
   - Methods are properly indented within the PdfTemplateService class
4. Report completion status and any issues encountered

DO NOT:
- Modify any existing methods unless explicitly specified
- Change the old match_template() method - keep it for backward compatibility
- Add unit tests yet - that comes in a later phase
- Update EtoRunsService yet - that's a separate integration task

This is purely about adding the new multi-template matching code to the codebase.

-->

This document contains the new code for the multi-template matching algorithm.

## 1. New Data Structures

Add these to `server/src/shared/types/pdf_templates.py`:

```python
# ========== Multi-Template Matching Dataclasses ==========

@dataclass(frozen=True)
class TemplateMatch:
    """
    Single template match for a consecutive page range.

    Represents pages that matched a specific template version.
    matched_pages is always consecutive (e.g., [1, 2, 3] or [5, 6]).
    """
    template_id: int
    version_id: int
    matched_pages: list[int]  # Consecutive pages, 1-indexed


@dataclass(frozen=True)
class TemplateMatchingResult:
    """
    Complete multi-template matching result for entire PDF.

    Contains all matched template ranges and any unmatched pages.
    Used to create EtoSubRuns after template matching stage.

    matches: Ordered by page appearance (first match has lowest page numbers)
    unmatched_pages: All pages that didn't match any template (can be non-consecutive)
    """
    matches: list[TemplateMatch]
    unmatched_pages: list[int]  # Can be non-consecutive, 1-indexed
```

## 2. Helper Functions

Add these to `server/src/features/pdf_templates/service.py` (in the `PdfTemplateService` class):

```python
def _filter_objects_by_page(self, pdf_objects: PdfObjects, page_num: int) -> PdfObjects:
    """
    Extract objects for a specific page from PdfObjects.

    Args:
        pdf_objects: Complete PdfObjects with all pages
        page_num: Page number to filter (1-indexed)

    Returns:
        PdfObjects containing only objects from the specified page
    """
    return PdfObjects(
        text_words=[obj for obj in pdf_objects.text_words if obj.page == page_num],
        graphic_rects=[obj for obj in pdf_objects.graphic_rects if obj.page == page_num],
        graphic_lines=[obj for obj in pdf_objects.graphic_lines if obj.page == page_num],
        graphic_curves=[obj for obj in pdf_objects.graphic_curves if obj.page == page_num],
        images=[obj for obj in pdf_objects.images if obj.page == page_num],
        tables=[obj for obj in pdf_objects.tables if obj.page == page_num]
    )


def _group_objects_by_page(self, pdf_objects: PdfObjects) -> dict[int, PdfObjects]:
    """
    Group PDF objects by page number.

    Args:
        pdf_objects: Complete PdfObjects with all pages

    Returns:
        Dictionary mapping page_num -> PdfObjects for that page
    """
    # Find all unique page numbers across all object types
    all_pages: set[int] = set()

    for obj in pdf_objects.text_words:
        all_pages.add(obj.page)
    for obj in pdf_objects.graphic_rects:
        all_pages.add(obj.page)
    for obj in pdf_objects.graphic_lines:
        all_pages.add(obj.page)
    for obj in pdf_objects.graphic_curves:
        all_pages.add(obj.page)
    for obj in pdf_objects.images:
        all_pages.add(obj.page)
    for obj in pdf_objects.tables:
        all_pages.add(obj.page)

    # Build dictionary
    result: dict[int, PdfObjects] = {}
    for page_num in sorted(all_pages):
        result[page_num] = self._filter_objects_by_page(pdf_objects, page_num)

    return result
```

## 3. Core Multi-Page Matching Function

Add this to `server/src/features/pdf_templates/service.py` (in the `PdfTemplateService` class):

```python
def _is_complete_multi_page_match(
    self,
    pdf_file: PdfFile,
    start_page: int,
    template_version: PdfTemplateVersion,
    template_page_count: int
) -> bool:
    """
    Check if ALL template signature objects exist in PDF pages for multi-page template.

    For multi-page templates:
    - Template page 1 objects must exist in PDF page start_page
    - Template page 2 objects must exist in PDF page start_page + 1
    - etc.

    Args:
        pdf_file: Complete PDF file with extracted objects
        start_page: Starting page in PDF to match against (1-indexed)
        template_version: Template version with signature objects
        template_page_count: Number of pages in template

    Returns:
        True if ALL template signature objects match across all pages
    """
    # Group template signature objects by page
    template_objects_by_page = self._group_objects_by_page(template_version.signature_objects)

    # Group PDF objects by page (cache for efficiency)
    pdf_objects_by_page = self._group_objects_by_page(pdf_file.extracted_objects)

    # Check each template page against corresponding PDF page
    for template_page_num in range(1, template_page_count + 1):
        pdf_page_num = start_page + template_page_num - 1

        # Get objects for this specific page
        template_page_objects = template_objects_by_page.get(template_page_num, PdfObjects(
            text_words=[], graphic_rects=[], graphic_lines=[],
            graphic_curves=[], images=[], tables=[]
        ))
        pdf_page_objects = pdf_objects_by_page.get(pdf_page_num, PdfObjects(
            text_words=[], graphic_rects=[], graphic_lines=[],
            graphic_curves=[], images=[], tables=[]
        ))

        # Check if ALL template objects on this page exist in PDF page
        # Uses existing _is_complete_subset_match method
        if not self._is_complete_subset_match(pdf_page_objects, template_page_objects):
            logger.debug(
                f"Template page {template_page_num} objects not found in PDF page {pdf_page_num}"
            )
            return False

    logger.debug(f"All {template_page_count} template pages matched starting at PDF page {start_page}")
    return True
```

## 4. Main Multi-Template Matching Algorithm

Add this to `server/src/features/pdf_templates/service.py` (in the `PdfTemplateService` class):

```python
def match_templates_multi_page(self, pdf_file: PdfFile) -> TemplateMatchingResult:
    """
    Match templates page-by-page with multi-template support.

    NEW ALGORITHM (replacing match_template for multi-template matching):
    - Processes PDF page by page
    - Each page can match a different template
    - Matches are consecutive page ranges
    - Greedy approach: once pages are matched, they're consumed

    Args:
        pdf_file: Complete PDF file with extracted objects and page_count

    Returns:
        TemplateMatchingResult with all matches and unmatched pages
    """
    from shared.types.pdf_templates import TemplateMatch, TemplateMatchingResult

    logger.info(f"Starting multi-page template matching for PDF {pdf_file.id} ({pdf_file.page_count} pages)")

    try:
        # Get all active templates
        active_templates = self.template_repository.list_templates(status="active")

        if not active_templates:
            logger.info("No active templates found for matching")
            # All pages are unmatched
            return TemplateMatchingResult(
                matches=[],
                unmatched_pages=list(range(1, pdf_file.page_count + 1))
            )

        matches: list[TemplateMatch] = []
        unmatched_pages: list[int] = []

        current_page = 1
        total_pages = pdf_file.page_count

        # Process each page (or page range)
        while current_page <= total_pages:
            logger.debug(f"Processing PDF page {current_page}")

            # Find all templates that could match starting at current_page
            candidate_templates: list[tuple[PdfTemplateListView, PdfTemplateVersion, int]] = []

            for template in active_templates:
                try:
                    # Skip if no current version
                    if template.current_version_id is None:
                        logger.debug(f"Template {template.id} has no current version, skipping")
                        continue

                    # Get the current version
                    current_version = self.version_repository.get_by_id(template.current_version_id)
                    if not current_version:
                        logger.debug(f"Template {template.id} current version not found, skipping")
                        continue

                    # Get template page count from source PDF
                    source_pdf = self.pdf_files_service.get_pdf_file(template.source_pdf_id)
                    template_page_count = source_pdf.page_count

                    if template_page_count is None:
                        logger.warning(f"Template {template.id} source PDF has no page_count, skipping")
                        continue

                    # Check if template can fit (enough remaining pages)
                    if current_page + template_page_count - 1 > total_pages:
                        logger.debug(
                            f"Template {template.id}: Not enough pages left "
                            f"(needs {template_page_count}, have {total_pages - current_page + 1})"
                        )
                        continue

                    # Check if ALL template signature objects exist in PDF pages
                    if self._is_complete_multi_page_match(
                        pdf_file=pdf_file,
                        start_page=current_page,
                        template_version=current_version,
                        template_page_count=template_page_count
                    ):
                        candidate_templates.append((template, current_version, template_page_count))
                        logger.debug(
                            f"Template {template.id} (version {current_version.version_number}): "
                            f"MATCH for pages {current_page}-{current_page + template_page_count - 1}"
                        )
                    else:
                        logger.debug(
                            f"Template {template.id} (version {current_version.version_number}): "
                            f"No match starting at page {current_page}"
                        )

                except Exception as e:
                    logger.warning(f"Error checking template {template.id}: {e}")
                    continue

            if not candidate_templates:
                # No match for this page
                logger.debug(f"Page {current_page}: No template match")
                unmatched_pages.append(current_page)
                current_page += 1
                continue

            # Find best match among candidates
            # Convert to format expected by existing _find_best_match
            # Need to calculate total object count for ranking
            candidates_with_count = []
            for template, version, page_count in candidate_templates:
                total_count = self._count_total_objects(version.signature_objects)
                candidates_with_count.append((template, version, total_count))

            try:
                best_template, best_version, total_count = self._find_best_match(candidates_with_count)
                # Get the page count for the best match
                best_page_count = None
                for template, version, page_count in candidate_templates:
                    if template.id == best_template.id and version.id == best_version.id:
                        best_page_count = page_count
                        break

                if best_page_count is None:
                    raise ValueError("Could not find page count for best match")

            except ValueError as e:
                logger.error(f"Error finding best match: {e}")
                unmatched_pages.append(current_page)
                current_page += 1
                continue

            # Record match
            matched_page_range = list(range(current_page, current_page + best_page_count))
            matches.append(TemplateMatch(
                template_id=best_template.id,
                version_id=best_version.id,
                matched_pages=matched_page_range
            ))

            # Update version usage statistics
            self.version_repository.increment_usage_count(best_version.id)

            logger.info(
                f"Match recorded: Template {best_template.id} (version {best_version.version_number}) "
                f"for pages {matched_page_range}"
            )

            # Skip past matched pages (greedy consumption)
            current_page += best_page_count

        logger.info(
            f"Multi-page matching complete: {len(matches)} matches, "
            f"{len(unmatched_pages)} unmatched pages"
        )

        return TemplateMatchingResult(
            matches=matches,
            unmatched_pages=unmatched_pages
        )

    except Exception as e:
        logger.error(f"Error in multi-page template matching: {e}", exc_info=True)
        # Return all pages as unmatched on error
        return TemplateMatchingResult(
            matches=[],
            unmatched_pages=list(range(1, pdf_file.page_count + 1))
        )
```

## 5. Import Statements

Add these imports to the top of `server/src/features/pdf_templates/service.py`:

```python
from shared.types.pdf_templates import (
    # ... existing imports ...
    TemplateMatch,
    TemplateMatchingResult,
)
from shared.types.pdf_files import PdfFile  # If not already imported
```

## 6. Implementation Notes

### Key Differences from Old Algorithm:

1. **Input**: Takes `PdfFile` object instead of just `pdf_objects` and `pdf_page_count`
   - Need access to full PDF file for page-by-page processing

2. **Output**: Returns `TemplateMatchingResult` instead of `Optional[tuple[int, int]]`
   - Contains multiple matches + unmatched pages

3. **Page Count Restriction**: REMOVED
   - Old algorithm required exact page count match
   - New algorithm allows any page range to match

4. **Greedy Consumption**: Once pages are matched, they're skipped
   - No overlap between matches

5. **Reuses Existing Logic**:
   - `_is_complete_subset_match()` for object matching
   - `_find_best_match()` for ranking
   - All `_match_*()` methods for type-specific matching

### Performance Considerations:

- Groups objects by page once per template check (cached)
- Early rejection if not enough pages remaining
- Reuses existing tolerance and similarity calculations

### Next Steps:

After adding this code, we'll need to:
1. Update `EtoRunsService._process_template_matching()` to use new algorithm
2. Create EtoSubRuns based on matching result
3. Handle unmatched pages as single sub-run with `is_unmatched_group=True`
