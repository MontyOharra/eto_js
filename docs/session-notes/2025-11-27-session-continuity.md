# Session Continuity Document - November 27, 2025

## Overview

This document provides context for continuing development on the ETO (Email-to-Output) application. The session focused on two main areas:
1. Fixing an email ingestion timezone bug
2. Creating a comprehensive TODO list and beginning frontend improvements

---

## Project Structure

- **Backend**: Python FastAPI server at `server/`
- **Frontend**: React + Electron app at `client/`
- **Stack**: TanStack Query, TanStack Router, TanStack Table (newly added), Tailwind CSS

---

## What Was Accomplished This Session

### 1. Email Ingestion Timezone Fix

**Problem**: Emails were not being picked up because the IMAP SINCE search used UTC dates, which could be "tomorrow" relative to the email server's local timezone.

**Fix Applied**: Added a 1-day buffer to the IMAP SINCE date query in:
- `server/src/features/email_ingestion/integrations/imap_integration.py` (lines 407-420)

The fix subtracts 1 day from the search date to ensure emails aren't missed due to timezone mismatches. The existing time-based filtering in the fetch loop (lines 445-468) prevents duplicate processing.

**Research Notes**: We researched RFC 5032 WITHIN extension (YOUNGER/OLDER commands) which would provide second-precision filtering, but major providers (Gmail, Office 365) don't support it. The 1-day buffer is the most portable solution.

### 2. TODO List Created

A comprehensive TODO list was created at:
- **`docs/TODO.md`** - Contains 15 items with priority/difficulty ratings

**Read this file first** - it contains the full breakdown of pending work.

### 3. TanStack Table Integration

**Problem**: The ETO runs list table had misaligned columns between header and body due to:
- Scrollbar width difference (body has 12px scrollbar, header doesn't)
- CSS Grid with `auto` columns sizing differently based on content

**Solution**: Replaced custom grid-based table with TanStack Table using proper HTML `<table>` structure.

**New Files Created**:
- `client/src/renderer/features/eto/components/EtoRunsTable/EtoRunsTable.tsx`
- `client/src/renderer/features/eto/components/EtoRunsTable/index.ts`

**Files Modified**:
- `client/src/renderer/pages/dashboard/eto/index.tsx` - Now uses `EtoRunsTable`
- `client/src/renderer/features/eto/components/index.ts` - Added export
- `client/package.json` - Added `@tanstack/react-table` dependency

---

## Files to Read for Context

### Essential Documentation
1. `docs/TODO.md` - **READ FIRST** - Full list of pending items with priorities
2. `docs/session-notes/CHANGELOG.md` - Session history
3. `CLAUDE.md` - Project conventions and rules

### Key Code Files
4. `client/src/renderer/features/eto/components/EtoRunsTable/EtoRunsTable.tsx` - New table component
5. `client/src/renderer/pages/dashboard/eto/index.tsx` - Main ETO list page
6. `client/src/renderer/features/eto/components/EtoRunRow/EtoRunRow.tsx` - Old row component (may be deprecated)
7. `server/src/features/email_ingestion/integrations/imap_integration.py` - Email ingestion with timezone fix

---

## What's Left to Do

From `docs/TODO.md`, prioritized by importance:

### High Priority (Priority 4-5)
1. **#15 - Sub-Runs Not Displaying** (Priority 5) - Some detail pages don't show sub-runs. Needs investigation.
2. **#7 - SSE Fallback Polling** (Priority 4) - Add periodic API polling as backup to SSE
3. **#1 - Skipped Status/Deletion** (Priority 4) - When all sub-runs skipped, enable delete

### Medium Priority (Priority 3)
4. **#3 - "Received" Column** - Shows hyphen instead of date
5. **#4 - Reset Read Status** - Mark as unread when run is updated
6. **#5 - Stabilize Row Position** - Don't update timestamp during processing
7. **#9 - Pagination Controls** - Restore pagination UI
8. **#11 - Preserve List State** - Keep filters/scroll when navigating

### Lower Priority (Priority 2)
9. **#2 - Table Header Alignment** - MAY BE FIXED by TanStack Table integration (needs testing)
10. **#6 - Sorting Controls** - Add UI for sorting
11. **#8 - Clean Up Logging** - Backend log cleanup
12. **#10 - Multiple PDF Uploads** - Support batch uploads
13. **#12 - Rethink Column Content** - Improve what's shown in list view
14. **#13 - Read/Unread Styling** - Make distinction more visible
15. **#14 - Filename Overflow** - Fix long filenames in detail page

---

## Immediate Next Steps

1. **Test the TanStack Table** - Verify header/body columns now align
2. **If aligned**: Mark TODO #2 as complete, move to #15 (sub-runs bug)
3. **If not aligned**: Debug further - the table uses `table-fixed` layout which should force alignment

---

## Git Status

The following files have uncommitted changes:
- Email ingestion timezone fix
- TanStack Table integration
- TODO.md creation
- Various cleanup (removed debug borders)

A commit should be made with these changes before continuing.

---

## Commands to Run

```bash
# Check recent git history
git log --oneline -10

# Run the dev server (user handles this, but for reference)
# Backend: cd server && python -m uvicorn src.main:app --reload
# Frontend: cd client && npm run dev

# Type-check frontend
cd client && npx tsc --noEmit
```
