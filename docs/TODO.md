# ETO Project - TODO List

> Tracking items that need to be fixed or improved.

---

## Summary Table

| # | Item | Layer | Priority | Difficulty |
|---|------|-------|----------|------------|
| 15 | Sub-Runs Not Displaying on Some Detail Pages | TBD | 5 | 3 |
| 1 | Skipped ETO Run Status and Deletion | Both | 4 | 3 |
| 7 | Add Fallback Polling for SSE Reliability | Frontend | 4 | 2 |
| 3 | "Received" Column Shows Hyphen | Both | 3 | 2 |
| 4 | Reset Read Status When Run is Updated | Backend | 3 | 2 |
| 5 | Stabilize Row Position During Processing | Backend | 3 | 3 |
| 9 | Fix Pagination/Offset Controls | Frontend | 3 | 2 |
| 11 | Preserve List View State When Navigating | Frontend | 3 | 4 |
| 2 | Table Header/Column Misalignment | Frontend | 2 | 1 |
| 6 | Add Table Sorting Controls | Frontend | 2 | 2 |
| 8 | Clean Up Backend Logging | Backend | 2 | 2 |
| 10 | Support Multiple PDF Uploads | Frontend | 2 | 2 |
| 12 | Rethink List View Column Content | Both | 2 | 3 |
| 13 | Improve Read vs Unread Row Styling | Frontend | 2 | 1 |
| 14 | Fix Long PDF Filename Overflow | Frontend | 2 | 1 |

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

### 2. Table Header/Column Misalignment

| Layer | Priority | Difficulty |
|-------|----------|------------|
| Frontend | 2 | 1 |

**Problem:** The header columns in the ETO runs list view are visually misaligned with the data columns below them.

**Requirements:**
- Fix the grid/column alignment so headers match their corresponding data cells

**Why this rating:**
- Priority 2: Visual polish, doesn't affect functionality
- Difficulty 1: Simple CSS/grid adjustment

---

### 3. "Received" Column Shows Hyphen on All Rows

| Layer | Priority | Difficulty |
|-------|----------|------------|
| Both | 3 | 2 |

**Problem:** The "Received" column in the ETO runs list view displays a hyphen (-) on all rows instead of the actual received date/time.

**Requirements:**
- Investigate why the received date is not being displayed
- Fix the data binding or API response to show the correct received timestamp

**Why this rating:**
- Priority 3: Missing useful information, but not blocking core functionality
- Difficulty 2: Need to trace data flow - could be missing from API response or frontend binding issue

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

### 7. Add Fallback Polling for SSE Reliability

| Layer | Priority | Difficulty |
|-------|----------|------------|
| Frontend | 4 | 2 |

**Problem:** Sometimes SSE (Server-Sent Events) doesn't work properly, causing rows to get stuck in "processing" status in the frontend until the user manually refreshes the page.

**Requirements:**
- Add a background polling mechanism as a fallback/supplement to SSE
- Periodically refresh the table data via the API (e.g., every 30-60 seconds)
- This ensures the UI eventually syncs even if SSE events are missed

**Why this rating:**
- Priority 4: Reliability issue that causes stale/incorrect UI state
- Difficulty 2: Add interval-based query invalidation/refetch

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

### 9. Fix Pagination/Offset Controls

| Layer | Priority | Difficulty |
|-------|----------|------------|
| Frontend | 3 | 2 |

**Problem:** The pagination offset is not currently working. Previously, the table had pagination controls (similar to Gmail's style) that allowed users to navigate through pages of results.

**Requirements:**
- Restore pagination controls to the table header
- Display current range (e.g., "1-50 of 127")
- Add previous/next buttons to navigate pages
- Wire up to the `offset` and `limit` query parameters

**Why this rating:**
- Priority 3: Important for navigating large datasets
- Difficulty 2: Restore/add UI components, backend already supports it

---

### 10. Support Multiple PDF Uploads

| Layer | Priority | Difficulty |
|-------|----------|------------|
| Frontend | 2 | 2 |

**Problem:** The "Upload PDF" button currently only allows uploading one file at a time.

**Requirements:**
- Enable multiple file selection in the file picker (`multiple` attribute)
- Process each selected PDF and create an ETO run for each
- Show progress/status for batch uploads

**Why this rating:**
- Priority 2: Convenience feature, single upload works
- Difficulty 2: Add multiple attribute, loop through files with progress tracking

---

### 11. Preserve List View State When Navigating to/from Detail Page

| Layer | Priority | Difficulty |
|-------|----------|------------|
| Frontend | 3 | 4 |

**Problem:** When navigating back from the ETO run detail page to the list view, the entire view resets:
- Filter selections (search query, status filter, read filter) are reset to defaults
- Scroll position is lost

**Requirements:**
- Preserve the entire list view state when navigating to detail page and back
- This includes: filters, scroll position, pagination offset
- Navigating back should feel like nothing changed in the list view
- **Recommended approach:** Keep the list view mounted in the DOM but hidden when viewing detail page (don't unmount it)
- Alternative options:
  - Store state in URL query parameters
  - Use state management solution (context, zustand, etc.)
  - Use browser history state with scroll restoration

**Why this rating:**
- Priority 3: Important UX improvement, currently frustrating
- Difficulty 4: May require routing/architecture changes to keep component mounted

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

### 13. Improve Read vs Unread Row Styling

| Layer | Priority | Difficulty |
|-------|----------|------------|
| Frontend | 2 | 1 |

**Problem:** The visual distinction between read and unread rows is too subtle. Currently, read rows just have slightly grayed-out text, which is hard to notice especially when looking at the action buttons.

**Requirements:**
- Make read/unread status more visually distinct
- Options:
  - Background color difference (e.g., unread rows have subtle highlight)
  - Bold text for unread rows
  - Unread indicator dot/icon
  - Different opacity for entire row (not just text)
- Ensure buttons and other elements also reflect the read state

**Why this rating:**
- Priority 2: Visual improvement
- Difficulty 1: CSS changes only

---

### 14. Fix Long PDF Filename Overflow in Detail Page

| Layer | Priority | Difficulty |
|-------|----------|------------|
| Frontend | 2 | 1 |

**Problem:** In the detail page, long PDF filenames push all other components to the right instead of wrapping or truncating. This breaks the layout.

**Requirements:**
- PDF filename should wrap to multiple lines or truncate with ellipsis
- Layout should remain static regardless of filename length
- Consider showing full filename on hover (tooltip) if truncated

**Why this rating:**
- Priority 2: Layout issue, doesn't break functionality
- Difficulty 1: CSS overflow/text-wrap fix

---

### 15. Sub-Runs Not Displaying on Some Detail Pages

| Layer | Priority | Difficulty |
|-------|----------|------------|
| TBD (needs investigation) | 5 | 3 |

**Problem:** Some ETO runs are not showing their sub-runs properly on the detail page, even though the list view displays them correctly. Cause unknown.

**Requirements:**
- Investigate why sub-runs are missing on certain detail pages
- Compare the list view API response vs detail view API response
- Check if it's a frontend rendering issue or backend data issue
- Fix the root cause so all sub-runs display consistently

**Why this rating:**
- Priority 5: Critical bug - core functionality broken for affected runs
- Difficulty 3: Unknown cause, needs investigation first

---

## Completed Items

<!-- Move items here once resolved -->
