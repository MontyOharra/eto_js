# Feature: ETO Page - Group Runs by Email

## Overview

Restructure the ETO page list view to visually group runs by their source email. Each email with multiple PDFs gets a header row, with child run rows indented beneath it. Single-run emails and manual uploads display as standalone rows (no header). This is primarily a visual/query change - no data model modifications.

## Current Behavior

- Each row = one ETO run (one PDF)
- Runs display independently with no visual indication of email relationships
- Filtering returns only matching runs
- Pagination by run count

## Desired Behavior

- Multi-run emails: Header row + indented child run rows
- Single-run emails: Standalone row (no header)
- Manual uploads: Standalone row (no header)
- Filtering returns matching runs AND all sibling runs from the same email
- Pagination by source count (each email = 1, each manual upload = 1)

## Visual Design

### Multi-Run Email Group
```
┌─────────────────────────────────────────────────────────────────────┐
│ 📧 shipper@logistics.com | "March Shipments" | Mar 15 | 3 PDFs      │  ← Header row
├─────────────────────────────────────────────────────────────────────┤
│   📄 BOL-001.pdf    | shipper@... | Mar 15 | Mar 15 2:30pm | ● ● ●  │  ← Run row (slight indent)
│   📄 Invoice.pdf    | shipper@... | Mar 15 | Mar 15 2:31pm | ●      │
│   📄 POD-001.pdf    | shipper@... | Mar 15 | Mar 15 2:32pm | ●      │
└─────────────────────────────────────────────────────────────────────┘
```

### Single-Run Email / Manual Upload
```
┌─────────────────────────────────────────────────────────────────────┐
│ 📄 Report.pdf       | warehouse@co | Mar 14 | Mar 14 1:00pm | ●     │  ← No header, just run row
└─────────────────────────────────────────────────────────────────────┘
```

### Key Visual Points
- Run rows look exactly the same as today (all fields preserved)
- Slight left padding on run rows within multi-run groups
- Header row is non-interactive (no click behavior)
- Always expanded (no collapse functionality)
- Run rows retain all existing info even if redundant with header

## Implementation

### Backend Changes

#### 1. Update List Query Logic

**File:** `server/src/shared/database/repositories/eto_run.py`

Current behavior:
```python
# Returns only runs matching filters
query.filter(...).limit(limit).offset(offset)
```

New behavior:
```python
# 1. Find runs matching filters
# 2. Get source_email_ids from matching runs
# 3. Return ALL runs with those source_email_ids (plus manual uploads that matched)
```

#### 2. Update Pagination

- Count by unique sources, not by runs
- A source = one `source_email_id` OR one manual upload (NULL source_email_id)
- Page of 20 = 20 sources (could be 20 runs or 100 runs depending on PDFs per email)

#### 3. Update Sorting

**Remove:** `pdf_filename` sort option (doesn't make sense at email level)

**Time-based sorts** (`last_processed_at`, `created_at`, `started_at`, `completed_at`):
- Use MAX of runs in the group to determine email group position
- Runs within group always sorted by `last_processed_at` DESC

**`received_at` sort:**
- All runs in email group share the same received date
- Manual uploads use `created_at`

#### 4. Update API Response

**File:** `server/src/api/schemas/eto_runs.py`

Add grouping information to response:
```python
class EtoRunListItem:
    # ... existing fields ...
    source_email_id: int | None  # For frontend grouping
    email_run_count: int  # Total runs from this email (for header display)
```

Response structure stays flat (list of runs), frontend handles grouping.

### Frontend Changes

#### 1. Group Runs by Email

**File:** `client/src/renderer/features/eto/components/EtoRunsTable/EtoRunsTable.tsx`

- Group runs by `source_email_id` (null = standalone)
- For groups with count > 1: render header row + run rows
- For groups with count = 1: render run row only

#### 2. Email Header Row Component

**New component:** `EtoEmailHeaderRow.tsx`

Display:
- Sender email
- Subject (truncated if needed)
- Received date
- PDF count (e.g., "3 PDFs")

Styling:
- Distinct background (subtle gray or similar)
- No hover/click behavior
- No status indicators (status stays on run rows)

#### 3. Run Row Indentation

- Add slight left padding (`pl-4` or similar) for runs within multi-run groups
- Single-run and manual uploads: no indent

#### 4. Update Pagination Display

- "Showing 1-20 of 150 sources" instead of "runs"
- Or keep it simple: "Showing 1-20 of 150"

## Edge Cases

1. **Filter matches one run in multi-run email**: Return all runs from that email, display full group

2. **Manual upload matches filter**: Return just that run (no siblings to fetch)

3. **Email with 50 PDFs**: All 50 display as one group. Consider if this becomes a UX issue in practice.

4. **Mixed sources on one page**: Some email groups, some standalone manual uploads - all intermixed based on sort order

5. **Empty search results**: Standard empty state, no special handling

## What Stays the Same

- Run row appearance and all fields
- Read/unread per-run (no aggregation)
- Status indicators per-run
- Run detail view (no changes)
- All run-level actions (reprocess, skip, etc.)
- Data model / database schema
- SSE updates (still per-run)

## Checklist

### Backend
- [ ] Update `EtoRunRepository.list()` to return sibling runs from matching emails
- [ ] Add `source_email_id` and `email_run_count` to `EtoRunListView`
- [ ] Update pagination to count by source instead of by run
- [ ] Update sorting to use MAX for time-based fields at email level
- [ ] Remove `pdf_filename` sort option
- [ ] Ensure runs within groups sorted by `last_processed_at` DESC
- [ ] Update API schema with new fields

### Frontend
- [ ] Create `EtoEmailHeaderRow` component
- [ ] Update `EtoRunsTable` to group runs by `source_email_id`
- [ ] Render header + indented runs for multi-run groups
- [ ] Render standalone row for single-run groups
- [ ] Add left padding to grouped run rows
- [ ] Update pagination display text

### Testing
- [ ] Test email with single PDF (no header)
- [ ] Test email with multiple PDFs (header + grouped runs)
- [ ] Test manual upload (no header)
- [ ] Test filtering - verify sibling runs included
- [ ] Test pagination by source count
- [ ] Test all sort options
- [ ] Test mixed page (emails + manual uploads)
