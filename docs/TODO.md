# ETO Project - TODO List

> Tracking items that need to be fixed or improved.

---

## Summary Table

| # | Item | Layer | Priority | Difficulty | Status |
|---|------|-------|----------|------------|--------|
| 16 | Email Ingestion IMAP Connection Resilience | Backend | 4 | 4 | Pending |

**Priority:** 5 = Critical functionality broken, 1 = Nice-to-have polish
**Difficulty:** 5 = Major restructuring/DB changes, 1 = Simple CSS/config fix

---

## Pending Items

### 17. Template Builder PDF Subset Creation Fails ✅

| Layer | Priority | Difficulty |
|-------|----------|------------|
| Both | 5 | 2 |

**Problem:** When trying to build a template from a sub-run that needs a template, the following error appears:

> "Failed to prepare PDF for template builder. Failed to create PDF subset: 'indices' must be of type 'Array', but was actually of type 'number'."

**Root Cause:**
- `NeedsTemplateSection.tsx` was passing `subRun.id` (a number) instead of `subRun.matched_pages` (an array)
- Type mismatch between child component (`onBuildTemplate: (subRunId: number)`) and parent handler (`handleBuildTemplate(pageIndexes: number[])`)

**Solution Implemented:**
- ✅ Fixed `NeedsTemplateSection.tsx` to pass `subRun.matched_pages` instead of `subRun.id`
- ✅ Updated type signature to `onBuildTemplate: (pageNumbers: number[]) => void`
- ✅ Added conversion from 1-indexed page numbers to 0-indexed indices in `handleBuildTemplate`

**Changes:**
- `client/src/renderer/features/eto/components/EtoRunDetailView/NeedsTemplateSection.tsx` - Pass `matched_pages` array, update type
- `client/src/renderer/features/eto/components/EtoRunDetailView/EtoRunDetailViewWrapper.tsx` - Convert page numbers to indices

**Completed:** 2025-11-29

---

### 1. Skipped ETO Run Status and Deletion ✅

| Layer | Priority | Difficulty |
|-------|----------|------------|
| Both | 4 | 3 |

**Problem:** When all sub-runs of an ETO run are in "skipped" status, the overall run status should reflect this, and the run should become deletable.

**Solution Implemented:**
- ✅ Added "skipped" to `ETO_MASTER_STATUS` enum (parent run status)
- ✅ Updated `_update_parent_run_status()` to detect when ALL sub-runs are skipped
- ✅ When all sub-runs are skipped, parent run status is set to "skipped"
- ✅ The existing `delete_runs()` method already checks for "skipped" status, so deletion now works

**Changes:**
- `server/src/shared/database/models.py` - Added 'skipped' to ETO_MASTER_STATUS enum
- `server/src/features/eto_runs/service.py` - Updated `_update_parent_run_status()` logic

**Note:** Frontend already has conditional button rendering logic. Once parent status is "skipped", the delete functionality will be available.

**Completed:** 2025-11-29

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


### 4. Reset Read Status When Run is Updated ✅

| Layer | Priority | Difficulty |
|-------|----------|------------|
| Backend | 3 | 2 |

**Problem:** When an ETO run is updated (its sub-runs are altered in some manner), the run should be reset to "unread" if it is currently marked as "read".

**Solution Implemented:**
- ✅ When `_update_parent_run_status()` changes the run's status, it now also resets `is_read` to `False`
- ✅ This is triggered whenever sub-runs complete processing, are skipped, or are reprocessed
- ✅ Users will see the run appear as "unread" again after any status change

**Changes:**
- `server/src/features/eto_runs/service.py` - Added `is_read` reset in `_update_parent_run_status()` when status changes

**Completed:** 2025-11-29

---

### 16. Email Ingestion IMAP Connection Resilience

| Layer | Priority | Difficulty |
|-------|----------|------------|
| Backend | 4 | 4 |

**Problem:** The email ingestion system sometimes stops working and cannot connect to the IMAP configuration. When this happens, the entire server shuts down, which is a critical failure mode.

**Requirements:**
- On IMAP connection failure, the email config listener should attempt to reconnect with exponential backoff
- Connection failures should NOT cause the entire server to crash
- Graceful degradation: if one email config fails, others should continue working
- Clear error logging and status reporting for failed connections
- Consider adding health check endpoint or status indicator for email configs

**Technical Notes:**
- Current implementation: `EmailListenerThread` in `server/src/features/email_ingestion/utils/email_listener_thread.py`
- Has `max_errors` (5) and `critical_failure_callback` but may not be handling all failure modes
- Need to investigate what causes server shutdown - likely unhandled exception bubbling up

**Why this rating:**
- Priority 4: Server crashes are critical, but workaround exists (restart server)
- Difficulty 4: Need to understand current failure modes, add robust error handling, possibly restructure connection management

---

### 5. Stabilize Row Position During Processing ✅

| Layer | Priority | Difficulty |
|-------|----------|------------|
| Backend | 3 | 3 |

**Problem:** When an ETO run is being processed, the `last_updated` timestamp changes frequently, causing the row to jump around in the sorted list view. This is disorienting for users.

**Solution Implemented:**
- ✅ Added explicit `last_processed_at` column to `eto_runs` table
- ✅ Column is only updated when run reaches terminal state (success/skipped/failure)
- ✅ Removed computed subquery that was calculating `MAX(sub_run.updated_at)`
- ✅ Repository now uses the stable column for sorting instead of live computation

**Changes:**
- `server/src/shared/database/models.py` - Added `last_processed_at` column to `EtoRunModel`
- `server/src/shared/types/eto_runs.py` - Added field to `EtoRun`, `EtoRunUpdate`, updated `EtoRunListView`
- `server/src/shared/database/repositories/eto_run.py` - Removed computed subquery, use column directly
- `server/src/features/eto_runs/service.py` - Set `last_processed_at` in `_update_parent_run_status()`

**Completed:** 2025-11-29

---
### 6. Add Table Sorting Controls ✅

| Layer | Priority | Difficulty |
|-------|----------|------------|
| Frontend | 2 | 2 |

**Problem:** There is no way for users to sort the ETO runs table by different columns.

**Solution:**
- Added `pdf_filename` and `received_at` sort options to backend API
- Backend repository handles sorting by joined table fields (COALESCE for received_at)
- Enabled sort dropdown in page header with 6 options:
  - Last Updated (Newest/Oldest)
  - Received (Newest/Oldest) - uses email received_date or created_at for manual uploads
  - Filename (A-Z/Z-A)

**Completed:** 2025-12-01

---

---





### 12. Rethink List View Column Content ✅

| Layer | Priority | Difficulty |
|-------|----------|------------|
| Both | 2 | 3 |

**Problem:** Some columns in the list view don't provide useful information:
- **Pages section:** Current display may not be helpful
- **Status section:** Basically only ever shows "processing" or "success", not very informative

**Solution Implemented:**
- ✅ Removed old "Status" column (was just showing "success" for 99% of rows)
- ✅ Removed old "Pages" column (matched/unmatched count wasn't useful)
- ✅ Created new combined "Status" column with smart display:
  - **Processing**: Spinner + "Processing" text
  - **Failure**: "Failed" text in red
  - **Complete**: Page counts with colored dots (🟢 success pages, 🟡 needs_template pages, 🔴 failure pages)
  - Only shows non-zero counts (no wasted space)
  - Calculates actual page counts from sub_runs array
- ✅ Animated ping effect on dots for unread rows
- ✅ Simplified filename cell (removed redundant indicators)

**Changes:**
- `client/src/renderer/features/eto/components/EtoRunsTable/EtoRunsTable.tsx` - Complete column restructure

**Completed:** 2025-12-01

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

### 8. Clean Up Backend Logging ✅

| Layer | Priority | Difficulty |
|-------|----------|------------|
| Backend | 2 | 1 |

**Problem:** Too many verbose logs at INFO level were cluttering the console during normal operation, including:
- Template matching details
- SSE connection/disconnection events
- Worker batch processing status
- Email polling when no emails found

**Solution Implemented:**
- ✅ Moved SSE connection/disconnection logs from INFO to DEBUG
- ✅ Moved "List ETO runs" query logs to DEBUG
- ✅ Moved template matching process logs to DEBUG
- ✅ Moved worker batch processing logs to DEBUG
- ✅ Moved "Updated email config" to DEBUG
- ✅ Made "Found N emails" conditional: DEBUG when 0, INFO when > 0
- ✅ Moved email attachment caching logs to DEBUG

**Changes:**
- `server/src/api/routers/eto_runs.py` - SSE and list query logs → DEBUG
- `server/src/features/pdf_templates/service.py` - Template matching logs → DEBUG
- `server/src/features/eto_runs/utils/eto_worker.py` - Batch processing logs → DEBUG
- `server/src/shared/database/repositories/email_config.py` - Update log → DEBUG
- `server/src/features/email_ingestion/utils/email_listener_thread.py` - Email polling logs → conditional/DEBUG

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
