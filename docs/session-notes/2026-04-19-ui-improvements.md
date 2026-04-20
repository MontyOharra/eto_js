# UI Improvements Session — 2026-04-19

## Task List

### 1. Rename "View in ETO" button
- [x] Change text to "View PDF Details Page"
- File: `client/src/renderer/features/eto/components/EtoSubRunDetail/EtoSubRunDetailFooter.tsx` (line 89)

### 2. Rework ETO detail overview section
- [x] Remove: templates matched, processing time, total pages
- [x] Keep: source, time (user timezone), processing status
- [x] Format time as human-readable in user's timezone (not raw ISO)
- [x] Update sidebar "Received" to show human-readable time
- [x] ~~Add "Reply to Sender" / "Open Email" button~~ — dropped; Outlook Desktop deep-link requires COM automation, deemed too complex

### 3. Make PDFs downloadable
- [x] Add Download PDF button to File Information section (replaces Received field)

### 4. Richer processing error summaries
- [ ] Replace generic "{X} of {X} pipeline modules failed" with per-module human-readable messages
- [ ] Special case: nameswap failures should suggest visiting ETO Info to add carrier nickname
