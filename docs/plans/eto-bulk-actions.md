# Feature: ETO Bulk Actions

## Overview

Add bulk action functionality to the ETO page frontend. Backend already supports bulk operations (reprocess, skip, delete). This feature adds selection UI and action buttons to allow users to operate on multiple runs at once.

## Backend Support (Already Exists)

| Operation | Endpoint | Request | Restrictions |
|-----------|----------|---------|--------------|
| Reprocess | `POST /eto-runs/reprocess` | `{ run_ids: [int] }` | None - any status |
| Skip | `POST /eto-runs/skip` | `{ run_ids: [int] }` | Only `failure` or `needs_template` |
| Delete | `DELETE /eto-runs` | `{ run_ids: [int] }` | Only `skipped` |

All return 204 No Content. Validation errors returned if invalid status for operation.

## Frontend Design

### Selection UI

- Checkbox column on each run row (leftmost column)
- "Select all" checkbox in table header
- "Select all" selects only loaded/visible rows (IDs from current frontend data)
- Selection state managed in frontend component state

### Action Buttons

**Location:** Top of list table, next to the "Upload PDF" button

**Buttons:**
- Reprocess
- Skip
- Delete

**Behavior:**
- Buttons appear disabled/inactive when no runs selected
- Buttons become active when runs are selected
- If only SOME selected runs are valid for an action, button shows count: "Delete (3 of 5)"
- Clicking executes action on valid runs only

### Action Availability Rules

| Action | Valid When Run Status Is |
|--------|--------------------------|
| Reprocess | Any status |
| Skip | `failure` or `needs_template` |
| Delete | `skipped` |

### Button States

```
No selection:
  [Reprocess] (disabled)  [Skip] (disabled)  [Delete] (disabled)

5 runs selected (all failure):
  [Reprocess (5)] (active)  [Skip (5)] (active)  [Delete] (disabled - 0 valid)

5 runs selected (3 skipped, 2 failure):
  [Reprocess (5)] (active)  [Skip (2)] (active)  [Delete (3)] (active)
```

### Confirmation Dialogs

Show confirmation dialog for destructive actions:

**Skip Confirmation:**
```
Skip X run(s)?

Skipped runs will not be reprocessed automatically.
They can be reprocessed manually or deleted later.

[Cancel] [Skip]
```

**Delete Confirmation:**
```
Delete X run(s)?

This action cannot be undone. The PDF files will be preserved.

[Cancel] [Delete]
```

**Reprocess:** No confirmation needed (non-destructive, can be re-done)

### Post-Action Behavior

After bulk action completes:
- Clear selection
- Refresh/invalidate run list query
- Show success toast: "X run(s) reprocessed/skipped/deleted"
- SSE events will update UI in real-time for other users

### Email Grouping Integration (#11)

Once email grouping is implemented:
- No checkbox on email header rows
- Only individual run rows have checkboxes
- "Select all" selects all visible runs (not email headers)
- Email headers are purely visual grouping

## Implementation

### Frontend

#### 1. Selection State

**File:** `client/src/renderer/pages/dashboard/eto/index.tsx` or extract to hook

```typescript
const [selectedRunIds, setSelectedRunIds] = useState<Set<number>>(new Set());

// Derived state
const allVisibleRunIds = runs.map(r => r.id);
const allSelected = allVisibleRunIds.length > 0 &&
  allVisibleRunIds.every(id => selectedRunIds.has(id));

// Handlers
const toggleRunSelection = (runId: number) => { ... };
const toggleSelectAll = () => { ... };
const clearSelection = () => setSelectedRunIds(new Set());
```

#### 2. Table Checkbox Column

**File:** `client/src/renderer/features/eto/components/EtoRunsTable/EtoRunsTable.tsx`

- Add checkbox as first column
- Header: "Select all" checkbox with indeterminate state support
- Row: Checkbox bound to selection state

#### 3. Bulk Action Buttons

**Location:** Next to "Upload PDF" button in page header

```tsx
<div className="flex gap-2">
  <Button
    disabled={selectedRunIds.size === 0}
    onClick={handleBulkReprocess}
  >
    Reprocess {validReprocessCount > 0 && `(${validReprocessCount})`}
  </Button>
  <Button
    disabled={validSkipCount === 0}
    onClick={handleBulkSkip}
  >
    Skip {validSkipCount > 0 && `(${validSkipCount})`}
  </Button>
  <Button
    variant="destructive"
    disabled={validDeleteCount === 0}
    onClick={handleBulkDelete}
  >
    Delete {validDeleteCount > 0 && `(${validDeleteCount})`}
  </Button>
</div>
```

#### 4. Valid Count Calculation

```typescript
const selectedRuns = runs.filter(r => selectedRunIds.has(r.id));

const validReprocessCount = selectedRuns.length; // All valid

const validSkipCount = selectedRuns.filter(r =>
  r.status === 'failure' || r.status === 'needs_template'
).length;

const validDeleteCount = selectedRuns.filter(r =>
  r.status === 'skipped'
).length;
```

#### 5. Confirmation Dialogs

Use existing dialog/modal component pattern:

```tsx
const [confirmAction, setConfirmAction] = useState<'skip' | 'delete' | null>(null);

// On button click
const handleBulkSkip = () => setConfirmAction('skip');
const handleBulkDelete = () => setConfirmAction('delete');

// On confirm
const executeAction = async () => {
  if (confirmAction === 'skip') {
    await bulkSkip(validSkipIds);
  } else if (confirmAction === 'delete') {
    await bulkDelete(validDeleteIds);
  }
  clearSelection();
  setConfirmAction(null);
};
```

#### 6. API Hooks

**File:** `client/src/renderer/features/eto/api/hooks.ts`

```typescript
export function useBulkReprocess() {
  return useMutation({
    mutationFn: (runIds: number[]) =>
      api.post('/eto-runs/reprocess', { run_ids: runIds }),
    onSuccess: () => {
      queryClient.invalidateQueries(['eto-runs']);
      toast.success('Runs reprocessed');
    },
  });
}

export function useBulkSkip() { ... }
export function useBulkDelete() { ... }
```

## Checklist

### Frontend - Selection

- [ ] Add selection state management (Set of selected IDs)
- [ ] Add checkbox column to `EtoRunsTable`
- [ ] Implement row checkbox (toggle individual)
- [ ] Implement header checkbox (select all visible)
- [ ] Handle indeterminate state (some selected)
- [ ] Clear selection after page change or filter change

### Frontend - Action Buttons

- [ ] Add bulk action buttons next to "Upload PDF" button
- [ ] Calculate valid counts for each action based on selected run statuses
- [ ] Display counts on buttons when > 0 valid
- [ ] Disable buttons when no valid runs for that action

### Frontend - Confirmation & Execution

- [ ] Create confirmation dialog for Skip action
- [ ] Create confirmation dialog for Delete action
- [ ] Implement `useBulkReprocess` hook
- [ ] Implement `useBulkSkip` hook
- [ ] Implement `useBulkDelete` hook
- [ ] Clear selection after successful action
- [ ] Show success toast after action completes

### Testing

- [ ] Test selecting individual runs
- [ ] Test select all / deselect all
- [ ] Test action button states with mixed statuses
- [ ] Test reprocess action (no confirmation)
- [ ] Test skip action with confirmation
- [ ] Test delete action with confirmation
- [ ] Test that invalid runs are excluded from action
- [ ] Test selection clears after action
- [ ] Test with pagination (selection scope)
