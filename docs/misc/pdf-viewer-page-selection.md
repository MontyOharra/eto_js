# PDF Viewer Page Selection Feature

**Date**: 2025-11-19
**Feature**: Virtual page subset display in PdfViewer component

---

## Overview

The PdfViewer component now supports displaying a subset of pages from a PDF as a "virtual" document with remapped page numbers.

## Use Case

When creating templates from multi-page PDFs, users may want to select only specific pages (e.g., pages 2-4 and 7 from a 10-page document). The viewer should:
- Show only the selected pages
- Display page numbers relative to the selection (not the full PDF)
- Navigate only through selected pages

## Implementation

### New Prop: `selectedPages`

```typescript
interface PdfViewerProps {
  // ... existing props ...

  /**
   * Optional array of 0-indexed page numbers to display as a virtual subset.
   * Example: [1, 2, 3, 6] means show only PDF pages 2, 3, 4, and 7 (0-indexed).
   * Page numbers displayed to user will be remapped: 2→1, 3→2, 4→3, 7→4
   * If not provided, all pages are shown.
   */
  selectedPages?: number[];
}
```

### Example Usage

**Scenario**: 10-page PDF, user selects pages 2, 3, 4, and 7 (0-indexed: 1, 2, 3, 6)

```tsx
<PdfViewer
  pdfUrl={pdfUrl}
  selectedPages={[1, 2, 3, 6]} // 0-indexed page numbers
>
  <PdfViewer.Canvas pdfUrl={pdfUrl}>
    {/* overlays */}
  </PdfViewer.Canvas>
  <PdfViewer.ControlsSidebar />
</PdfViewer>
```

**User Experience**:
- Total pages shown: **4** (not 10)
- Page navigation: 1, 2, 3, 4 (not 1, 2, 3, 4, 5, 6, 7, 8, 9, 10)
- Page 1 displays PDF page 2
- Page 2 displays PDF page 3
- Page 3 displays PDF page 4
- Page 4 displays PDF page 7

### Page Mapping Logic

**Virtual Mode** (when `selectedPages` is provided):

1. **Sort selected pages**: `[1, 2, 3, 6]` → already sorted
2. **Virtual page count**: `numPages = selectedPages.length` (4 pages)
3. **Virtual to Actual mapping**:
   ```typescript
   virtualToActualPage(1) → 2  // Virtual page 1 = PDF page 2 (0-indexed 1 + 1)
   virtualToActualPage(2) → 3  // Virtual page 2 = PDF page 3 (0-indexed 2 + 1)
   virtualToActualPage(3) → 4  // Virtual page 3 = PDF page 4 (0-indexed 3 + 1)
   virtualToActualPage(4) → 7  // Virtual page 4 = PDF page 7 (0-indexed 6 + 1)
   ```

**Normal Mode** (no `selectedPages`):
- Show all pages
- No page mapping (virtual page = actual page)

### Context Updates

**PdfViewerContext** now includes:

```typescript
interface PdfViewerContextValue {
  currentPage: number;      // Virtual page number shown to user (1-indexed)
  actualPdfPage: number;    // Actual PDF page being rendered (1-indexed)
  numPages: number | null;  // Virtual page count (or total if no selection)
  // ... rest of context ...
}
```

**Key Points**:
- `currentPage`: What the user sees (1, 2, 3, 4)
- `actualPdfPage`: What gets rendered from the PDF (2, 3, 4, 7)
- `numPages`: Count of virtual pages (4)

### Component Updates

**PdfViewer.tsx**:
- Added `selectedPages` prop
- Implemented `virtualToActualPage()` and `actualToVirtualPage()` mapping functions
- Changed `numPages` state to `totalPagesInPdf`
- Computed `numPages` based on virtual mode
- Computed `actualPdfPage` for rendering

**PdfCanvas.tsx**:
- Uses `actualPdfPage` instead of `currentPage` for `<Page pageNumber={...}>`
- Mouse event handlers pass `actualPdfPage` to callbacks

**PdfControlsSidebar.tsx**:
- No changes needed! Uses `currentPage` and `numPages` from context
- Automatically shows virtual page numbers

### Edge Cases Handled

1. **Empty selection**: If `selectedPages` is empty array, treated as normal mode
2. **Out of range pages**: Mapping functions return fallback (page 1)
3. **Unsorted selection**: Array is automatically sorted
4. **Duplicate pages**: Not explicitly handled (duplicates would be shown multiple times)

### Integration with Template Builder

In `PageSelectionStep`:
- User selects pages: `[0, 1, 2, 3]` (pages 1-4 in UI)
- Pass to PdfViewer: `selectedPages={selectedPages}`
- Viewer shows only those 4 pages with page numbers 1-4

In subsequent steps (signature objects, extraction fields):
- Pass same `selectedPages` to PdfViewer
- User works with virtual page numbers
- Objects/fields stored with actual PDF page numbers (handled by overlay logic)

---

## Benefits

1. **Clean UX**: User sees simple page numbering (1, 2, 3, 4) instead of confusing gaps
2. **Consistent navigation**: Next/Previous work correctly within selection
3. **No confusion**: Total page count matches what user selected
4. **Backend simplicity**: Actual PDF page numbers preserved in signature objects/extraction fields

---

## Future Enhancements

1. **Page range support**: Allow ranges like `{start: 1, end: 5}` instead of array
2. **Non-contiguous highlighting**: Visual indicator showing original page numbers
3. **Jump to original page**: Keyboard shortcut to see actual PDF page number
4. **Validation**: Warn if selected pages exceed PDF page count
