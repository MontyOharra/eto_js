# Order Management Session - January 13, 2026

## Overview

This session focused on the Order Management (Pending Actions) system, specifically:
- Backend fixes for field processing and SSE updates
- Frontend styling and UX improvements for the list view and detail views
- Establishing clear color semantics for status indicators

## Current System State

### Backend - Fully Functional

**SSE (Server-Sent Events) for Real-Time Updates:**
- Endpoint: `GET /api/pending-actions/events`
- Located in: `server/src/api/routers/pending_actions.py`
- Event types: `pending_action_created`, `pending_action_updated`, `pending_action_deleted`
- Broadcasts from `OrderManagementService.process_output_execution()`

**Field Processing:**
- Address ID resolution via `_resolve_address_ids()` method using HTC lookup
- Duplicate field values are skipped (not stored) to avoid false conflicts
- Location field comparison uses `address_id` only for update detection
- String normalization (`.strip()`) for MAWB comparison
- `last_processed_at` timestamp updated on actual processing (not read status changes)

**Cleanup on Reprocessing:**
- `cleanup_sub_run_contributions(sub_run_id)` - removes field contributions when reprocessing
- `cleanup_output_execution_contributions(output_execution_id)` - removes by output execution
- Wired up in `EtoRunsService.reprocess_sub_run()` and `skip_sub_run()`

**Sorting:**
- Default sort changed from `updated_at` to `last_processed_at`
- Read status changes no longer affect sort order

### Frontend - List View Complete

**Files:**
- `client/src/renderer/features/order-management/components/UnifiedActionsTable/UnifiedActionsTable.tsx`
- `client/src/renderer/features/order-management/constants.ts` (shared status colors)

**Color Semantics for Indicator Circles:**
| Color  | Status | Meaning |
|--------|--------|---------|
| Red    | failed, ambiguous | Error - something's wrong |
| Yellow | conflict | Needs user decision |
| Orange | incomplete | Still building/accumulating |
| Blue   | ready, unread | Needs approval or attention |
| Green  | completed | Successfully created/updated |
| Gray   | rejected | User rejected the action |

**Type Badges (Create/Update):**
- Now neutral/muted gray styling (not competing with status colors)
- Create: lighter slate with + icon
- Update: slightly darker slate with refresh (↻) icon
- Ambiguous: red with ? icon (error state)

**Status Info Column Order:**
1. Status badge
2. Conflict count (if any) - moved to be right after status
3. Required fields progress (blue when complete, orange when incomplete)
4. Optional fields progress (gray)

**Animations:**
- Unread items have pinging indicator circles (sync-ping animation)
- Matches ETO runs page behavior

**Ambiguous Handling:**
- Clicking shows alert popup
- Marks as read after popup closes

### Frontend - Detail Views

**Header Layout (both PendingOrderDetailView and PendingUpdateDetailView):**
- Row 1: Back button (left) | Action Type label (center) | Status badge (right)
- Row 2: Customer/HAWB/HTC# with labels above values (left) | Action buttons (right)

**Shared Constants:**
- `client/src/renderer/features/order-management/constants.ts`
- `STATUS_COLORS` - shared status color definitions
- `getStatusColorClasses()` - helper function

**Source Card Highlighting:**
- Hovering source cards highlights both the card itself and associated field rows

## What's NOT Yet Implemented

### 1. User Interactions (Priority: High)

**Field Selection/Conflict Resolution:**
- UI exists but selection logic not wired up
- Need: `selectFieldValue(fieldId: number)` API endpoint
- Need: Service method to update `is_selected` flag and recalculate status

**Approve/Reject Actions:**
- Buttons exist in detail views
- Need: Wire up to backend `execute_action()` and rejection logic
- Need: Handle success/error states and navigation

**Manual Field Entry:**
- Need: UI for user to manually enter/override field values
- Need: `setUserValue(actionId, fieldName, value)` API endpoint
- Need: Service method to create field with `output_execution_id = NULL`

### 2. Update Comparison View (Priority: High)

**Current vs New Value Display:**
- PendingUpdateDetailView shows fields but needs:
  - Fetch current HTC values for comparison
  - Display side-by-side (Current → New)
  - Allow user to approve individual field updates

**Update Approval Flow:**
- `is_approved_for_update` flag exists on fields
- Need: UI to toggle which fields should be included in update
- Need: Only approved fields sent to HTC on execute

### 3. Order Creation Logic (Priority: High)

**Execute Create:**
- `execute_action()` method exists but needs:
  - Build order payload from selected field values
  - Call HTC API to create order
  - Update pending action status to `completed` or `failed`
  - Set `htc_order_number` on success

### 4. Order Update Logic (Priority: High)

**Execute Update:**
- Similar to create but:
  - Only send fields where `is_approved_for_update = True`
  - Call HTC API to update existing order
  - Handle partial update failures

### 5. Error Handling & Recovery (Priority: Medium)

- Display error messages in detail view
- Allow retry of failed actions
- Clear error state on retry

## Key Files Reference

### Backend
```
server/src/api/routers/pending_actions.py      # REST endpoints + SSE
server/src/api/schemas/pending_actions.py      # Request/response schemas
server/src/features/order_management/service.py # Core business logic
server/src/features/order_management/transformers.py # Field transformations
server/src/shared/database/models.py           # PendingActionModel, PendingActionFieldModel
server/src/shared/database/repositories/pending_action.py
server/src/shared/database/repositories/pending_action_field.py
server/src/shared/types/pending_actions.py     # Domain types
```

### Frontend
```
client/src/renderer/features/order-management/
├── api/
│   ├── hooks.ts                    # TanStack Query hooks
│   └── types.ts                    # API response types
├── components/
│   ├── UnifiedActionsTable/        # Main list view
│   ├── PendingOrderDetailView/     # Create detail view
│   └── PendingUpdateDetailView/    # Update detail view
├── hooks/
│   └── useOrderEvents.ts           # SSE connection hook
├── constants.ts                    # Shared status colors
└── types.ts                        # Frontend types
```

## Suggested Next Steps

### Session Start Checklist
1. `git log --oneline -10` to review recent commits
2. `git status` to see current changes
3. Review this document

### Implementation Order

**Phase 1: Field Selection (enables conflict resolution)**
1. Add `PATCH /api/pending-actions/{id}/fields/{fieldId}/select` endpoint
2. Implement `select_field_value()` in service
3. Wire up click handler in detail view field rows
4. Test conflict resolution flow

**Phase 2: Approve/Reject Flow**
1. Add `POST /api/pending-actions/{id}/approve` endpoint
2. Add `POST /api/pending-actions/{id}/reject` endpoint
3. Implement in service (rejection just sets status)
4. Wire up buttons in detail views
5. Add loading states and success/error handling

**Phase 3: Manual Field Entry**
1. Design UI for manual input (inline edit? modal?)
2. Add `PUT /api/pending-actions/{id}/fields/{fieldName}` endpoint
3. Implement `set_user_value()` in service
4. Handle field type validation

**Phase 4: HTC Integration**
1. Implement `execute_create()` - build payload, call HTC, update status
2. Implement `execute_update()` - similar but only approved fields
3. Add proper error handling and retry logic

## Testing

**Mock Output Endpoint:**
```bash
curl -X POST http://localhost:8000/api/pending-actions/mock \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": 1,
    "hawb": "TEST-HAWB-001",
    "output_channel_data": {
      "pickup_time_start": "2024-01-15 09:00",
      "pickup_time_end": "2024-01-15 12:00",
      "pickup_company_name": "Acme Corp",
      "mawb": "123-45678901"
    }
  }'
```

**SSE Testing:**
```bash
curl -N http://localhost:8000/api/pending-actions/events
```

## Notes

- The system uses a unified `pending_actions` table for both creates and updates
- Action type (create vs update) is determined at accumulation time based on HTC lookup
- Field conflicts occur when different values are received for the same field
- The `is_selected` flag determines which value is used (only one per field)
- User-provided values have `output_execution_id = NULL`
