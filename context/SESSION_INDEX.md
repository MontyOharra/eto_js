# Multi-Session Continuity Index

**Project:** ETO (Email-to-Order) Processing System
**Branch:** server_unification
**Last Updated:** 2025-10-29

---

## Active Sessions

### Main Session - SSE & Performance Analysis
**File:** `SESSION_CONTINUITY_MAIN.md`
**Focus:** Real-time updates, performance optimization
**Status:** Active
**Key Work:**
- Implemented SSE (Server-Sent Events) for real-time ETO run updates
- Fixed repository enum conversion errors
- Diagnosed performance issue with connection dragging (excessive re-renders)
- Identified intermittent edge rendering issue in Electron

---

### Session 2
**File:** `SESSION_CONTINUITY_SESSION_2.md`
**Focus:** [To be filled]
**Status:** [To be filled]
**Key Work:** [To be filled]

---

### Session 3
**File:** `SESSION_CONTINUITY_SESSION_3.md`
**Focus:** [To be filled]
**Status:** [To be filled]
**Key Work:** [To be filled]

---

## Coordination Guidelines

### Before Starting Work:
1. **Read all session continuity files** to understand what others are working on
2. **Check git status** - branch has diverged from origin
3. **Communicate through continuity docs** to avoid conflicts
4. **Update your session file** as you make progress

### Before Committing:
1. **Check other session files** for uncommitted changes
2. **Pull latest changes** if working on same files
3. **Update your continuity doc** with what you committed
4. **Note any conflicts** or coordination needs

### File Ownership (Avoid Conflicts):
- **Main Session:** Currently modifying SSE files, ETO frontend, repository files
- **Session 2:** [Claim files you're working on]
- **Session 3:** [Claim files you're working on]

---

## Git Branch Status

**Branch:** server_unification
**Divergence:** 4 local commits, 1 remote commit
**Action Needed:** Merge or rebase before pushing

---

## Critical Shared Context

### Uncommitted Changes (Main Session):
- Frontend: SSE hooks, ETO page updates, template builder
- Backend: ETO repositories, event system

### Pending Issues:
1. Performance issue in PipelineGraph.tsx (needs fix)
2. Intermittent edge rendering in Electron (investigating)

### Recent Fixes:
1. Repository enum conversions
2. Template matching create/update pattern
3. SSE implementation complete

---

## Quick Reference

- **CHANGELOG.md** - Historical session log (last 10 entries)
- **SESSION_CONTINUITY_MAIN.md** - Main session detailed work
- **SESSION_CONTINUITY_SESSION_2.md** - Session 2 work
- **SESSION_CONTINUITY_SESSION_3.md** - Session 3 work

---

**How to Use:**
1. Each session updates their own continuity file
2. Read index + all session files before starting work
3. Update your file as you make progress
4. Check coordination section before committing
