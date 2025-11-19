# Page Segment Template Matching System Design

**Date**: 2025-01-18
**Status**: Design Phase
**Purpose**: Replace single-PDF template matching with per-page-segment matching to handle multi-document PDFs

---

## Problem Statement

**Current System**:
- One ETO run = one PDF = one template match
- Either entire PDF matches a template or it doesn't
- Cannot handle multi-document PDFs (e.g., pages 1-3 are BOL, pages 4-6 are Routing)

**New Requirements**:
- Match different page ranges within same PDF to different templates
- Use sliding window algorithm to find all possible matches
- Process each matched segment through separate extraction and transformation flows
- **Critical UX Challenge**: Display both matched and unmatched page segments to users

---

## Database Schema Changes

### New Table: `eto_run_page_segments`

Represents a contiguous range of pages that either matched a template or didn't.

```sql
CREATE TABLE eto_run_page_segments (
    id INT PRIMARY KEY IDENTITY(1,1),
    eto_run_id INT NOT NULL FOREIGN KEY REFERENCES eto_runs(id),

    -- Page range
    start_page INT NOT NULL,  -- 1-indexed
    end_page INT NOT NULL,    -- 1-indexed, inclusive

    -- Match result
    matched_template_version_id INT NULL FOREIGN KEY REFERENCES template_versions(id),
    match_confidence DECIMAL(5,4) NULL,  -- 0.0000 to 1.0000

    -- Status tracking
    status VARCHAR(50) NOT NULL,  -- 'matched', 'unmatched', 'manually_assigned', 'ignored'

    -- Timestamps
    created_at DATETIME2 NOT NULL DEFAULT GETDATE(),

    -- Constraints
    CONSTRAINT chk_page_range CHECK (end_page >= start_page),
    CONSTRAINT chk_match_confidence CHECK (match_confidence IS NULL OR (match_confidence >= 0 AND match_confidence <= 1))
)

CREATE INDEX idx_eto_run_page_segments_run_id ON eto_run_page_segments(eto_run_id);
CREATE INDEX idx_eto_run_page_segments_template ON eto_run_page_segments(matched_template_version_id);
```

**Status Values**:
- `matched` - Automatically matched by sliding window algorithm
- `unmatched` - No template matched this segment
- `manually_assigned` - User manually assigned a template to this segment
- `ignored` - User marked this segment to be ignored (e.g., cover page, blank pages)

### Remove Table: `eto_run_template_matchings`

This table becomes obsolete - template matching now happens at the page segment level.

### Update Table: `eto_run_extractions`

Change from linking to `eto_run_id` to linking to `page_segment_id`.

```sql
ALTER TABLE eto_run_extractions
ADD page_segment_id INT NULL FOREIGN KEY REFERENCES eto_run_page_segments(id);

-- Migration strategy: populate page_segment_id based on existing eto_run_id
-- Then make it NOT NULL and drop eto_run_id foreign key
```

### Update Table: `eto_run_pipeline_executions`

Change from linking to `eto_run_id` to linking to `page_segment_id`.

```sql
ALTER TABLE eto_run_pipeline_executions
ADD page_segment_id INT NULL FOREIGN KEY REFERENCES eto_run_page_segments(id);

-- Migration strategy: populate page_segment_id based on existing eto_run_id
-- Then make it NOT NULL and drop eto_run_id foreign key
```

### Updated `eto_runs` Table Relationship

```python
class EtoRunModel(Base):
    # ... existing fields ...

    # NEW: One-to-many relationship with page segments
    page_segments = relationship(
        "EtoRunPageSegmentModel",
        back_populates="eto_run",
        cascade="all, delete-orphan"
    )

    # DEPRECATED: Remove this relationship
    # template_matching = relationship("EtoRunTemplateMatchingModel", ...)
```

---

## Sliding Window Algorithm

### Algorithm Description

For a PDF with N pages and available templates of lengths 1, 2, 3, ..., M pages:

```python
def find_all_template_matches(pdf_pages: list, templates: list) -> list[Match]:
    """
    Find all possible template matches using sliding window approach.

    Returns list of Match objects sorted by:
    1. Confidence (descending)
    2. Page coverage (prefer larger segments)
    3. Start page (ascending)
    """
    matches = []

    # Group templates by page length
    templates_by_length = group_by(templates, key=lambda t: t.page_count)

    # For each possible window size (from largest to smallest)
    for window_size in sorted(templates_by_length.keys(), reverse=True):
        templates_for_size = templates_by_length[window_size]

        # Slide window across PDF
        for start_page in range(1, len(pdf_pages) - window_size + 2):
            end_page = start_page + window_size - 1

            # Extract page segment
            segment_pages = pdf_pages[start_page-1:end_page]

            # Try matching against all templates of this size
            for template in templates_for_size:
                confidence = calculate_match_confidence(segment_pages, template)

                if confidence >= CONFIDENCE_THRESHOLD:  # e.g., 0.75
                    matches.append(Match(
                        start_page=start_page,
                        end_page=end_page,
                        template_version_id=template.version_id,
                        confidence=confidence
                    ))

    return matches
```

### Overlap Resolution Strategy

When multiple matches overlap, we need to decide which to keep:

**Strategy 1: Greedy High Confidence** (Recommended)
```python
def resolve_overlaps(matches: list[Match]) -> list[Match]:
    """
    Select non-overlapping matches prioritizing:
    1. Highest confidence
    2. Largest page coverage
    3. Earliest start page
    """
    # Sort by confidence (desc), then coverage (desc), then start_page (asc)
    sorted_matches = sorted(
        matches,
        key=lambda m: (-m.confidence, -(m.end_page - m.start_page), m.start_page)
    )

    selected = []
    covered_pages = set()

    for match in sorted_matches:
        match_pages = set(range(match.start_page, match.end_page + 1))

        # If no overlap with already selected matches
        if not match_pages.intersection(covered_pages):
            selected.append(match)
            covered_pages.update(match_pages)

    return sorted(selected, key=lambda m: m.start_page)
```

**Strategy 2: Let User Choose** (Future Enhancement)
- Show all possible matches with overlaps highlighted
- Let user select which segments to keep
- Useful for ambiguous cases

### Unmatched Page Detection

After selecting non-overlapping matches, identify gaps:

```python
def find_unmatched_segments(total_pages: int, matched_segments: list[Match]) -> list[UnmatchedSegment]:
    """Find contiguous page ranges that didn't match any template."""
    unmatched = []
    covered_pages = set()

    for match in matched_segments:
        covered_pages.update(range(match.start_page, match.end_page + 1))

    # Find gaps
    current_gap_start = None
    for page in range(1, total_pages + 1):
        if page not in covered_pages:
            if current_gap_start is None:
                current_gap_start = page
        else:
            if current_gap_start is not None:
                unmatched.append(UnmatchedSegment(
                    start_page=current_gap_start,
                    end_page=page - 1
                ))
                current_gap_start = None

    # Handle trailing gap
    if current_gap_start is not None:
        unmatched.append(UnmatchedSegment(
            start_page=current_gap_start,
            end_page=total_pages
        ))

    return unmatched
```

---

## User Interface Design

### Current UI Structure

**EtoRunDetailViewer** (lines 1-131 in EtoRunDetailViewer.tsx):
- Split panel layout (left: execution details, right: PDF viewer)
- Header shows: status, source, **single template**, duration
- Two view modes: "Summary" and "Detail"

**Key UI Components**:
- `EtoRunDetailHeader` - Shows matched template (currently assumes one template)
- `PdfViewerPanel` - Displays PDF with optional field overlays
- `SummarySuccessView` / `SummaryErrorView` - Shows execution results
- `DetailPipelineView` - Shows pipeline execution graph

### Proposed UI Changes

#### 1. Header Enhancement - Template Segment Summary

**Current** (EtoRunDetailHeader.tsx lines 70-78):
```tsx
{runDetail.matched_template && (
  <div className="text-sm text-gray-300 border-l border-gray-600 pl-4">
    <span className="text-gray-400">Template:</span>{" "}
    {runDetail.matched_template.template_name}{" "}
    <span className="text-gray-500">
      (v{runDetail.matched_template.version_num})
    </span>
  </div>
)}
```

**Proposed** - Multi-segment status badge:
```tsx
{runDetail.page_segments && runDetail.page_segments.length > 0 && (
  <div className="text-sm text-gray-300 border-l border-gray-600 pl-4">
    <span className="text-gray-400">Templates:</span>{" "}
    <SegmentStatusSummary segments={runDetail.page_segments} />
  </div>
)}
```

**SegmentStatusSummary Component**:
```tsx
interface SegmentStatusSummaryProps {
  segments: PageSegment[];
}

function SegmentStatusSummary({ segments }: SegmentStatusSummaryProps) {
  const matched = segments.filter(s => s.status === 'matched' || s.status === 'manually_assigned');
  const unmatched = segments.filter(s => s.status === 'unmatched');
  const ignored = segments.filter(s => s.status === 'ignored');

  const totalPages = segments.reduce((sum, s) => sum + (s.end_page - s.start_page + 1), 0);
  const matchedPages = matched.reduce((sum, s) => sum + (s.end_page - s.start_page + 1), 0);
  const unmatchedPages = unmatched.reduce((sum, s) => sum + (s.end_page - s.start_page + 1), 0);

  return (
    <div className="inline-flex items-center space-x-2">
      <span className="font-mono text-green-400">
        {matchedPages}/{totalPages} pages matched
      </span>

      {unmatchedPages > 0 && (
        <span className="font-mono text-yellow-400">
          ({unmatchedPages} unmatched)
        </span>
      )}

      {ignored.length > 0 && (
        <span className="font-mono text-gray-500">
          ({ignored.length} ignored)
        </span>
      )}
    </div>
  );
}
```

#### 2. New Component: PageSegmentTimeline

A visual timeline showing which pages belong to which segments, displayed above the PDF viewer.

```tsx
interface PageSegmentTimelineProps {
  segments: PageSegment[];
  totalPages: number;
  currentPage: number;  // From PDF viewer
  onPageClick: (page: number) => void;  // Navigate PDF viewer
  onSegmentClick: (segment: PageSegment) => void;  // Show segment details
}

function PageSegmentTimeline({
  segments,
  totalPages,
  currentPage,
  onPageClick,
  onSegmentClick
}: PageSegmentTimelineProps) {
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg p-3 mb-3">
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-sm font-semibold text-gray-300">Page Segments</h4>
        <div className="text-xs text-gray-400">
          {totalPages} pages total
        </div>
      </div>

      <div className="flex space-x-1">
        {segments.map((segment, idx) => {
          const pageCount = segment.end_page - segment.start_page + 1;
          const widthPercent = (pageCount / totalPages) * 100;

          return (
            <button
              key={idx}
              onClick={() => onSegmentClick(segment)}
              className={`
                relative group h-12 rounded transition-all
                ${getSegmentColor(segment.status)}
                ${segment.start_page <= currentPage && currentPage <= segment.end_page
                  ? 'ring-2 ring-blue-400'
                  : ''
                }
              `}
              style={{ width: `${widthPercent}%` }}
            >
              {/* Segment label */}
              <div className="absolute inset-0 flex flex-col items-center justify-center text-xs">
                <div className="font-semibold text-white">
                  {segment.status === 'matched' || segment.status === 'manually_assigned'
                    ? `${segment.matched_template_name}`
                    : segment.status === 'unmatched'
                    ? 'No Match'
                    : 'Ignored'
                  }
                </div>
                <div className="text-gray-300 text-[10px]">
                  pp. {segment.start_page}-{segment.end_page}
                </div>
              </div>

              {/* Hover tooltip */}
              <div className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 hidden group-hover:block z-10">
                <div className="bg-gray-900 border border-gray-600 rounded px-2 py-1 text-xs whitespace-nowrap">
                  <SegmentTooltip segment={segment} />
                </div>
              </div>
            </button>
          );
        })}
      </div>

      {/* Individual page markers */}
      <div className="flex space-x-1 mt-1">
        {Array.from({ length: totalPages }, (_, i) => i + 1).map(page => (
          <button
            key={page}
            onClick={() => onPageClick(page)}
            className={`
              h-2 rounded-sm transition-all
              ${page === currentPage ? 'bg-blue-400' : 'bg-gray-600 hover:bg-gray-500'}
            `}
            style={{ width: `${(1 / totalPages) * 100}%` }}
            title={`Page ${page}`}
          />
        ))}
      </div>
    </div>
  );
}

function getSegmentColor(status: string): string {
  switch (status) {
    case 'matched':
      return 'bg-green-600 hover:bg-green-500';
    case 'manually_assigned':
      return 'bg-blue-600 hover:bg-blue-500';
    case 'unmatched':
      return 'bg-yellow-600 hover:bg-yellow-500';
    case 'ignored':
      return 'bg-gray-600 hover:bg-gray-500';
    default:
      return 'bg-gray-700';
  }
}

function SegmentTooltip({ segment }: { segment: PageSegment }) {
  const pageCount = segment.end_page - segment.start_page + 1;

  return (
    <div className="space-y-1">
      <div className="font-semibold">
        Pages {segment.start_page}-{segment.end_page} ({pageCount} page{pageCount > 1 ? 's' : ''})
      </div>

      {segment.status === 'matched' && (
        <>
          <div className="text-gray-300">
            Template: {segment.matched_template_name} v{segment.matched_version_number}
          </div>
          <div className="text-gray-400">
            Confidence: {(segment.match_confidence * 100).toFixed(1)}%
          </div>
        </>
      )}

      {segment.status === 'unmatched' && (
        <div className="text-yellow-300">No template matched</div>
      )}

      {segment.status === 'manually_assigned' && (
        <div className="text-blue-300">Manually assigned by user</div>
      )}

      {segment.status === 'ignored' && (
        <div className="text-gray-400">Ignored by user</div>
      )}
    </div>
  );
}
```

**Visual Example**:
```
┌────────────────────────────────────────────────────────────────────────┐
│ Page Segments                                          15 pages total   │
├────────────────────────────────────────────────────────────────────────┤
│ ┌─────────────────┐ ┌──────────┐ ┌────────────┐ ┌──────────────────┐ │
│ │  BOL Template   │ │ No Match │ │  Routing   │ │     Ignored      │ │
│ │   pp. 1-5       │ │ pp. 6-7  │ │ pp. 8-12   │ │    pp. 13-15     │ │
│ └─────────────────┘ └──────────┘ └────────────┘ └──────────────────┘ │
│ ▓▓▓▓▓░░▓▓▓▓▓░░░░░                  (page markers)                     │
└────────────────────────────────────────────────────────────────────────┘
```

#### 3. Unmatched Segment Actions Panel

When user clicks on an unmatched segment, show action panel:

```tsx
interface UnmatchedSegmentActionPanelProps {
  segment: PageSegment;
  availableTemplates: Template[];
  onAssignTemplate: (segmentId: number, templateVersionId: number) => void;
  onIgnore: (segmentId: number) => void;
  onCreateTemplate: (segmentId: number) => void;
}

function UnmatchedSegmentActionPanel({
  segment,
  availableTemplates,
  onAssignTemplate,
  onIgnore,
  onCreateTemplate
}: UnmatchedSegmentActionPanelProps) {
  const [selectedTemplateId, setSelectedTemplateId] = useState<number | null>(null);

  return (
    <div className="bg-gray-800 border border-yellow-600 rounded-lg p-4 mb-3">
      <div className="flex items-start justify-between mb-3">
        <div>
          <h4 className="text-sm font-semibold text-yellow-300">
            Unmatched Pages {segment.start_page}-{segment.end_page}
          </h4>
          <p className="text-xs text-gray-400 mt-1">
            No template automatically matched this section. Choose an action:
          </p>
        </div>
        <button className="text-gray-400 hover:text-gray-200">
          <XIcon className="w-5 h-5" />
        </button>
      </div>

      <div className="space-y-3">
        {/* Option 1: Manually assign template */}
        <div className="bg-gray-900 rounded p-3">
          <label className="text-sm font-medium text-gray-300 block mb-2">
            Manually Assign Template
          </label>
          <div className="flex space-x-2">
            <select
              value={selectedTemplateId || ''}
              onChange={(e) => setSelectedTemplateId(Number(e.target.value))}
              className="flex-1 bg-gray-800 border border-gray-600 rounded px-3 py-2 text-sm"
            >
              <option value="">Select template...</option>
              {availableTemplates
                .filter(t => t.page_count === (segment.end_page - segment.start_page + 1))
                .map(t => (
                  <option key={t.version_id} value={t.version_id}>
                    {t.name} v{t.version_num} ({t.page_count} pages)
                  </option>
                ))
              }
            </select>
            <button
              onClick={() => selectedTemplateId && onAssignTemplate(segment.id, selectedTemplateId)}
              disabled={!selectedTemplateId}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:text-gray-500 rounded text-sm font-medium"
            >
              Assign
            </button>
          </div>
        </div>

        {/* Option 2: Create new template */}
        <div className="bg-gray-900 rounded p-3">
          <label className="text-sm font-medium text-gray-300 block mb-2">
            Create New Template
          </label>
          <p className="text-xs text-gray-400 mb-2">
            Use these pages as the basis for a new template that can be reused for future PDFs.
          </p>
          <button
            onClick={() => onCreateTemplate(segment.id)}
            className="px-4 py-2 bg-green-600 hover:bg-green-700 rounded text-sm font-medium"
          >
            Create Template from Pages {segment.start_page}-{segment.end_page}
          </button>
        </div>

        {/* Option 3: Ignore */}
        <div className="bg-gray-900 rounded p-3">
          <label className="text-sm font-medium text-gray-300 block mb-2">
            Ignore Pages
          </label>
          <p className="text-xs text-gray-400 mb-2">
            Mark these pages as not needing processing (e.g., cover pages, blank pages).
          </p>
          <button
            onClick={() => onIgnore(segment.id)}
            className="px-4 py-2 bg-gray-600 hover:bg-gray-700 rounded text-sm font-medium"
          >
            Ignore These Pages
          </button>
        </div>
      </div>
    </div>
  );
}
```

#### 4. Segment-Specific Execution Details

Update the left panel to show execution results per segment:

```tsx
interface SegmentExecutionListProps {
  segments: PageSegment[];
  onSegmentSelect: (segmentId: number) => void;
}

function SegmentExecutionList({ segments, onSegmentSelect }: SegmentExecutionListProps) {
  return (
    <div className="space-y-2">
      {segments.map(segment => (
        <button
          key={segment.id}
          onClick={() => onSegmentSelect(segment.id)}
          className={`
            w-full text-left bg-gray-900 hover:bg-gray-800 rounded-lg p-3
            border-l-4 transition-all
            ${getSegmentBorderColor(segment.status)}
          `}
        >
          <div className="flex items-center justify-between mb-1">
            <div className="text-sm font-semibold text-white">
              Pages {segment.start_page}-{segment.end_page}
            </div>
            <SegmentStatusBadge status={segment.status} />
          </div>

          {segment.matched_template_name && (
            <div className="text-xs text-gray-400 mb-1">
              Template: {segment.matched_template_name} v{segment.matched_version_number}
            </div>
          )}

          {segment.extraction && (
            <div className="text-xs text-green-400">
              ✓ {segment.extraction.field_count} fields extracted
            </div>
          )}

          {segment.pipeline_execution && (
            <div className="text-xs">
              {segment.pipeline_execution.status === 'success' ? (
                <span className="text-green-400">✓ Pipeline executed</span>
              ) : (
                <span className="text-red-400">✗ Pipeline failed</span>
              )}
            </div>
          )}

          {segment.status === 'unmatched' && (
            <div className="text-xs text-yellow-400">
              ⚠ No template matched - action needed
            </div>
          )}
        </button>
      ))}
    </div>
  );
}
```

### Complete UI Flow Example

**Scenario**: User uploads 15-page PDF containing BOL (pages 1-5), cover letter (pages 6-7), and Routing form (pages 8-12), with blank pages at the end (13-15).

**Step 1: Initial Processing**
- Sliding window algorithm runs
- Finds:
  - Pages 1-5 match "BOL Template v3" (95% confidence)
  - Pages 8-12 match "Routing Template v2" (88% confidence)
  - Pages 6-7: No match
  - Pages 13-15: No match

**Step 2: Results Display**

Header shows:
```
Templates: 10/15 pages matched (5 unmatched)
```

Timeline shows:
```
[BOL 1-5] [No Match 6-7] [Routing 8-12] [No Match 13-15]
```

Execution list shows:
```
✓ Pages 1-5    BOL Template v3     ✓ 12 fields extracted  ✓ Pipeline executed
⚠ Pages 6-7    No template matched - action needed
✓ Pages 8-12   Routing Template v2 ✓ 8 fields extracted   ✓ Pipeline executed
⚠ Pages 13-15  No template matched - action needed
```

**Step 3: User Actions**

User clicks on "Pages 6-7" → Shows action panel:
- Manually assign to existing template
- Create new "Cover Letter" template
- Ignore (mark as non-processable)

User clicks "Ignore These Pages"

User clicks on "Pages 13-15" → Shows action panel

User clicks "Ignore These Pages"

**Step 4: Final State**

Header shows:
```
Templates: 10/15 pages matched (5 ignored)
```

Timeline shows:
```
[BOL 1-5] [Ignored 6-7] [Routing 8-12] [Ignored 13-15]
```

All segments now have a resolution → Overall ETO run status can be "success"

---

## API Changes

### New Types (TypeScript)

```typescript
export interface PageSegment {
  id: number;
  eto_run_id: number;
  start_page: number;
  end_page: number;

  // Match info
  matched_template_version_id: number | null;
  matched_template_name: string | null;
  matched_version_number: number | null;
  match_confidence: number | null;  // 0.0 to 1.0

  // Status
  status: 'matched' | 'unmatched' | 'manually_assigned' | 'ignored';

  // Related data (populated when available)
  extraction?: {
    id: number;
    status: string;
    field_count: number;
  };
  pipeline_execution?: {
    id: number;
    status: string;
    executed_actions: Record<string, any> | null;
  };

  created_at: string;
}

export interface EtoRunDetail {
  // ... existing fields ...

  // NEW: Replace single template match with segment list
  page_segments: PageSegment[];

  // DEPRECATED: Remove these
  // matched_template: EtoMatchedTemplate | null;
  // stage_template_matching: EtoStageTemplateMatching | null;
}
```

### New Endpoints

```python
# Get segment details with execution info
GET /api/eto-runs/{run_id}/segments/{segment_id}

# Manually assign template to segment
POST /api/eto-runs/{run_id}/segments/{segment_id}/assign-template
Body: { "template_version_id": 123 }

# Mark segment as ignored
POST /api/eto-runs/{run_id}/segments/{segment_id}/ignore

# Create new template from segment pages
POST /api/eto-runs/{run_id}/segments/{segment_id}/create-template
Body: { "template_name": "Cover Letter" }

# Re-run matching for entire PDF (after creating new templates)
POST /api/eto-runs/{run_id}/rematch
```

---

## Migration Strategy

### Phase 1: Database Migration (Backward Compatible)

1. Create `eto_run_page_segments` table
2. Add `page_segment_id` columns to `eto_run_extractions` and `eto_run_pipeline_executions` (nullable)
3. Migrate existing data:
   ```python
   # For each existing eto_run:
   #   If it has a template match:
   #     Create single page_segment covering all pages (1 to page_count)
   #     Link extraction and pipeline_execution to this segment
   #   If no template match:
   #     Create single unmatched segment covering all pages
   ```
4. Keep `eto_run_template_matchings` table temporarily for rollback

### Phase 2: Backend Implementation

1. Implement sliding window matching algorithm
2. Update `EtoRunService` to create page segments instead of single template match
3. Update repositories to query by `page_segment_id`
4. Add new segment management endpoints

### Phase 3: Frontend Updates

1. Update types to include `page_segments`
2. Create new UI components (PageSegmentTimeline, UnmatchedSegmentActionPanel, etc.)
3. Update EtoRunDetailViewer to show segment-based view
4. Handle backward compatibility (show old single-match runs gracefully)

### Phase 4: Cleanup

1. Make `page_segment_id` NOT NULL in extractions and pipeline_executions
2. Drop `eto_run_id` foreign keys from these tables
3. Drop `eto_run_template_matchings` table
4. Remove old API response fields

---

## Open Questions

1. **Confidence Threshold**: What confidence score should trigger automatic matching?
   - Recommendation: 0.75 (75%) for auto-match, show 0.50-0.75 as "low confidence" suggestions

2. **Page Overlap Handling**: Should we ever allow overlapping segments?
   - Recommendation: No overlap in final selected segments, but show potential overlaps to user for manual resolution

3. **Performance**: How to handle very large PDFs (100+ pages)?
   - Recommendation:
     - Run matching asynchronously
     - Show progress indicator
     - Cache intermediate matching results
     - Limit max template size to reasonable value (e.g., 10 pages)

4. **Template Creation from Unmatched**: Should this be instant or require admin approval?
   - Recommendation: Allow instant creation but mark as "draft" until admin reviews

5. **Re-matching**: If user creates new template, should we auto-rematch entire PDF?
   - Recommendation: Prompt user "Would you like to re-scan this PDF with the new template?" after creation

---

## Success Metrics

**Before (Current System)**:
- 1 PDF = 1 template match attempt
- Multi-document PDFs fail completely or only process first document

**After (New System)**:
- 1 PDF = N segments with independent template matches
- Success = all segments either matched or explicitly handled (ignored/manually assigned)
- Metrics to track:
  - % of PDFs with 100% matched pages (fully automatic)
  - % of PDFs with partial matches requiring user action
  - % of unmatched segments that get resolved (vs. ignored)
  - Average time for users to resolve unmatched segments

---

## Future Enhancements

1. **ML-Based Confidence Improvement**
   - Train model on user corrections (manual assignments)
   - Suggest templates for unmatched segments based on content similarity

2. **Batch Processing**
   - "Apply this template to all similar unmatched segments in my recent PDFs"

3. **Template Variants**
   - Support slight variations of same template (different logos, layouts)
   - Auto-group related templates

4. **Smart Segmentation**
   - Use page breaks, content analysis to suggest segment boundaries
   - "This looks like 3 separate documents, should we split them?"
