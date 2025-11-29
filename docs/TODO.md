# ETO Project - TODO List

> Tracking items that need to be fixed or improved.

---

## Summary Table

| # | Item | Layer | Priority | Difficulty | Status |
|---|------|-------|----------|------------|--------|
| 1 | Skipped ETO Run Status and Deletion | Both | 4 | 3 | Pending (needs backend) |
| 4 | Reset Read Status When Run is Updated | Backend | 3 | 2 | Pending |
| 5 | Stabilize Row Position During Processing | Backend | 3 | 3 | Pending |
| 6 | Add More Table Sorting Fields | Frontend | 2 | 2 | Partial (basic sorting works) |
| 8 | Clean Up Backend Logging | Backend | 2 | 2 | Pending |
| 12 | Rethink List View Column Content | Both | 2 | 3 | Pending |

**Priority:** 5 = Critical functionality broken, 1 = Nice-to-have polish
**Difficulty:** 5 = Major restructuring/DB changes, 1 = Simple CSS/config fix

---

## Pending Items

### 1. Skipped ETO Run Status and Deletion

| Layer | Priority | Difficulty |
|-------|----------|------------|
| Both | 4 | 3 |

**Problem:** When all sub-runs of an ETO run are in "skipped" status, the overall run status should reflect this, and the run should become deletable.

**Requirements:**
- When all pages/sub-runs are skipped, the overall ETO run status should be "skipped"
- When overall status is "skipped", the run should be deletable:
  - **List view:** The "Skip" button should change to "Delete", with its callback triggering deletion of the ETO run
  - **Detail view:** The "Delete" button should be activated/enabled in the actions panel

**Why this rating:**
- Priority 4: Affects core workflow - users can't properly manage/delete completed runs
- Difficulty 3: Backend needs status aggregation logic, frontend needs conditional button rendering

---

### 14. Fix Long PDF Filename Overflow ✅

| Layer | Priority | Difficulty |
|-------|----------|------------|
| Frontend | 2 | 1 |

**Problem:** In the detail page, long PDF filenames (especially those without spaces) pushed all other components to the right instead of wrapping, breaking the layout.

**Solution Implemented:**
- ✅ Changed `break-words` to `break-all` (forces breaks at any character, not just word boundaries)
- ✅ Added `overflow-hidden` to parent containers to prevent overflow
- ✅ Changed `items-center` to `items-start` so back button aligns to top when title wraps
- ✅ Added `title` attribute for full filename tooltip on hover

**Changes:**
- `client/src/renderer/features/eto/components/EtoRunDetailView/EtoRunDetailHeader.tsx` - Fixed filename overflow with `break-all` CSS

**Completed:** 2025-11-29 (re-fixed)

---

### 13. Improve Read vs Unread Row Styling ✅

| Layer | Priority | Difficulty |
|-------|----------|------------|
| Frontend | 2 | 1 |

**Problem:** The visual distinction between read and unread rows was too subtle (just slightly grayed-out text).

**Solution Implemented:**
- ✅ Added background color distinction:
  - **Unread rows:** `bg-blue-900/10` (subtle blue tint)
  - **Read rows:** Default/transparent background
  - **Failure rows:** `bg-red-900/10` with red border (takes priority)
- ✅ Clear visual hierarchy matching email client patterns (Gmail, etc.)

**Changes:**
- `client/src/renderer/features/eto/components/EtoRunsTable/EtoRunsTable.tsx` - Added conditional background color based on read status

**Completed:** 2025-11-27

---


### 4. Reset Read Status When Run is Updated

| Layer | Priority | Difficulty |
|-------|----------|------------|
| Backend | 3 | 2 |

**Problem:** When an ETO run is updated (its sub-runs are altered in some manner), the run should be reset to "unread" if it is currently marked as "read".

**Requirements:**
- When sub-runs are reprocessed, skipped, or otherwise modified, reset the parent run's `is_read` to `false`
- This ensures users are notified of changes to runs they've already reviewed

**Why this rating:**
- Priority 3: Important for notification workflow but not breaking
- Difficulty 2: Add logic in service layer when sub-runs are modified

---

### 5. Stabilize Row Position During Processing

| Layer | Priority | Difficulty |
|-------|----------|------------|
| Backend | 3 | 3 |

**Problem:** When an ETO run is being processed, the `last_updated` timestamp changes frequently, causing the row to jump around in the sorted list view. This is disorienting for users.

**Requirements:**
- The `last_updated` (or `last_processed_at`) time should only update when processing is complete (not during intermediate states)
- While a run has sub-runs in "processing" status, it should maintain its current position in the list
- This prevents rows from constantly reordering while work is in progress

**Why this rating:**
- Priority 3: UX issue that can be disorienting but not breaking
- Difficulty 3: Need to rethink when `last_processed_at` is set, may affect multiple code paths

---

### 6. Add Table Sorting Controls

| Layer | Priority | Difficulty |
|-------|----------|------------|
| Frontend | 2 | 2 |

**Problem:** There is no way for users to sort the ETO runs table by different columns.

**Requirements:**
- Add sorting functionality to the frontend table
- Options:
  - Clickable column headers with sort indicators (asc/desc arrows)
  - OR a dedicated sorting dropdown/button in the page header
- Backend already supports `sort_by` and `sort_order` parameters

**Why this rating:**
- Priority 2: Nice-to-have feature, default sorting works
- Difficulty 2: Add UI controls and wire to existing backend params

---


### 8. Clean Up Backend Logging

| Layer | Priority | Difficulty |
|-------|----------|------------|
| Backend | 2 | 2 |

**Problem:** There are excessive debugging artifacts and verbose log statements throughout the backend, making it difficult to see actual meaningful logs.

**Requirements:**
- Audit and clean up logging across the backend codebase
- Remove or reduce verbosity of debug-level log statements
- Ensure appropriate log levels are used (DEBUG vs INFO vs WARNING)
- Keep logs focused on meaningful events and errors

**Why this rating:**
- Priority 2: Developer experience, not user-facing
- Difficulty 2: Tedious audit but not complex

---



### 12. Rethink List View Column Content

| Layer | Priority | Difficulty |
|-------|----------|------------|
| Both | 2 | 3 |

**Problem:** Some columns in the list view don't provide useful information:
- **Pages section:** Current display may not be helpful
- **Status section:** Basically only ever shows "processing" or "success", not very informative

**Requirements:**
- Evaluate what information is most useful to show at a glance
- Consider alternatives for the pages column (e.g., page count, sub-run breakdown)
- Consider alternatives for status (e.g., sub-run status summary like "2 success, 1 failed")
- Design should help users quickly identify runs that need attention

**Why this rating:**
- Priority 2: UX improvement, current display works
- Difficulty 3: Need to design new columns, possibly add backend aggregation

---

### 11. Preserve List View Scroll Position ✅

| Layer | Priority | Difficulty |
|-------|----------|------------|
| Frontend | 3 | 2 |

**Problem:** When navigating back from the detail view to the list view, the scroll position was reset even though filters were preserved.

**Root Cause:**
The list view was conditionally rendered (`{selectedRunId ? <Detail> : <List>}`), which unmounted the list component when viewing details, losing scroll position.

**Solution Implemented:**
- ✅ Changed from conditional rendering to show/hide approach
- ✅ List view is always mounted in the DOM
- ✅ Uses `hidden` CSS class to hide list when detail view is open
- ✅ Scroll position and all state preserved when returning from detail view

**Changes:**
- `client/src/renderer/pages/dashboard/eto/index.tsx` - Keep list mounted, use CSS to show/hide

**Completed:** 2025-11-29

---

### 7. Add Fallback Polling for SSE Reliability ✅

| Layer | Priority | Difficulty |
|-------|----------|------------|
| Frontend | 4 | 2 |

**Problem:** Sometimes SSE (Server-Sent Events) doesn't work properly, causing rows to get stuck in "processing" status in the frontend until the user manually refreshes the page.

**Solution Implemented:**
- ✅ Added `fallbackPollingInterval` option to `useEtoEvents` hook (default: 10 seconds)
- ✅ Periodically invalidates ETO runs list queries as backup
- ✅ Can be disabled by setting `fallbackPollingInterval: 0`
- ✅ Only logs in development mode to avoid console spam

**Changes:**
- `client/src/renderer/features/eto/hooks/useEtoEvents.ts` - Added fallback polling interval

**Completed:** 2025-11-29

---

### 15. Sub-Runs Not Displaying on Some Detail Pages ✅

| Layer | Priority | Difficulty |
|-------|----------|------------|
| Backend | 5 | 3 |

**Problem:** Some ETO runs were not showing their sub-runs on the detail page, even though the list view displayed them correctly.

**Root Cause:**
Bug in `server/src/shared/database/repositories/eto_sub_run.py` line 364. The SQL join was:
```python
.join(PdfFileModel, EtoSubRunModel.eto_run_id == PdfFileModel.id)  # WRONG!
```
This incorrectly joined `eto_run_id` (the parent ETO run ID) directly to `PdfFileModel.id`. This only worked when the ETO run ID coincidentally matched a PDF file ID.

**Solution Implemented:**
- ✅ Fixed the join to properly traverse: SubRun → EtoRun → PdfFile
- ✅ Added `EtoRunModel` to imports
- ✅ Changed join to:
  1. First join `EtoSubRunModel.eto_run_id → EtoRunModel.id`
  2. Then join `EtoRunModel.pdf_file_id → PdfFileModel.id`

**Changes:**
- `server/src/shared/database/repositories/eto_sub_run.py` - Fixed SQL join in `get_detail_view()` method

**Completed:** 2025-11-29

---

## Completed Items

### 3. "Received" Column Shows Hyphen ✅

| Layer | Priority | Difficulty |
|-------|----------|------------|
| Both | 3 | 2 |

**Problem:** The "Received" column in the ETO runs list view displayed a hyphen (-) on all rows instead of the actual received date/time.

**Solution Implemented:**
- ✅ Fixed `getSourceDate()` in EtoRunsTable to use `source.received_at` for emails
- ✅ Return `source.created_at` for manual uploads instead of null
- ✅ Moved source tracking from `pdf_files.email_id` to `eto_runs.source_type` + `source_email_id`
- ✅ Updated API mapper to use `source_type` field for discriminated union

**Changes:**
- `client/src/renderer/features/eto/components/EtoRunsTable/EtoRunsTable.tsx` - Fixed `getSourceDate()` function
- `server/src/api/mappers/eto_runs.py` - Use `source_type` instead of checking `email_id`
- Multiple backend files for source tracking refactor

**Completed:** 2025-11-29

---

### 9. Fix Pagination/Offset Controls ✅

| Layer | Priority | Difficulty |
|-------|----------|------------|
| Frontend | 3 | 2 |

**Problem:** The pagination offset was not working. Table needed pagination controls similar to Gmail's style.

**Solution Implemented:**
- ✅ Added `currentPage` state with 20 items per page
- ✅ Gmail-style display showing "1-20 of 127"
- ✅ Previous/next buttons with disabled states
- ✅ Wired up to `offset` and `limit` query parameters
- ✅ Page resets to 1 when filters change

**Changes:**
- `client/src/renderer/pages/dashboard/eto/index.tsx` - Added pagination state and UI

**Note:** May need UX refinement (e.g., reset page when sort changes). Defer testing until other items complete.

**Completed:** 2025-11-29

---

### 10. Support Multiple PDF Uploads ✅

| Layer | Priority | Difficulty |
|-------|----------|------------|
| Frontend | 2 | 2 |

**Problem:** The "Upload PDF" button currently only allows uploading one file at a time.

**Solution Implemented:**
- ✅ Added `multiple` attribute to file input
- ✅ Sequential upload loop with progress tracking
- ✅ Per-file error handling (failures don't stop the batch)
- ✅ Progress displayed in button: "Uploading 2/5..."
- ✅ Summary report if any files fail

**Changes:**
- `client/src/renderer/pages/dashboard/eto/index.tsx` - Updated `handleUploadPdf` function and upload button

**Completed:** 2025-11-27

---

### 2. Table Header/Column Misalignment ✅

| Layer | Priority | Difficulty |
|-------|----------|------------|
| Frontend | 2 | 1 |

**Problem:** The header columns in the ETO runs list view were visually misaligned with the data columns below them.

**Solution Implemented:**
- ✅ Fixed percentage-based column widths using TanStack Table
- ✅ Added invisible scrollbar to header (12px) to match body scrollbar width
- ✅ Converted pixel widths to percentages for proper `table-fixed` layout
- ✅ Adjusted column proportions: PDF Filename (24.6%), Source (19.2%), Received (10%), Status (5.4%), Pages (10%), Last Updated (9.2%), Actions (21.5%)
- ✅ Implemented responsive action buttons (icon+text on wide screens, icon-only on narrow)
- ✅ Added text wrapping with line-clamp (up to 5 lines before ellipsis)

**Changes:**
- `client/src/renderer/features/eto/components/EtoRunsTable/EtoRunsTable.tsx` - Complete table rewrite with proper column sizing, scrollbar compensation, and responsive buttons

**Completed:** 2025-11-27
