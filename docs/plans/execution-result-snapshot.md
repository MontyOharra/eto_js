# Execution Result Snapshot Plan

Store execution details (old/new values) on pending_action record so completed actions show what changed.

## Data Structure

```python
execution_result: {
    "action_type": "update",  # or "create"
    "executed_at": "2026-01-18T23:56:04Z",
    "approver_user_id": "Ethan_Harrah",
    "htc_order_number": 102694,  # For creates: newly created order #
    "fields_updated": ["mawb", "delivery_datetime", "delivery_notes"],
    "old_values": {  # null for creates
        "mawb": "OLD123",
        "delivery_datetime": "2026-01-15 09:00-17:00",
        "delivery_notes": "OLD NOTES"
    },
    "new_values": {
        "mawb": "NEW456",
        "delivery_datetime": "2026-01-20 10:00-18:00",
        "delivery_notes": "NEW NOTES"
    }
}
```

### For Order Creates
- `action_type`: "create"
- `old_values`: `null` (order didn't exist)
- `new_values`: All field values sent to HTC (pickup/delivery locations, datetimes, notes, etc.)
- `htc_order_number`: The newly created order number
- `fields_updated`: All fields that were populated

### For Order Updates
- `action_type`: "update"
- `old_values`: Previous HTC values before update
- `new_values`: New values after update
- `htc_order_number`: Existing order that was updated
- `fields_updated`: Only fields that were actually changed

## Implementation Steps

### 1. Database Schema
- [ ] Add `execution_result` column (NVARCHAR(MAX) / JSON) to `pending_actions` table
- File: Direct SQL or migration script

### 2. Backend Types (`shared/types/pending_actions.py`)
- [ ] Create `ExecutionResult` TypedDict or dataclass with fields:
  - `executed_at: str`
  - `approver_user_id: str | None`
  - `htc_order_number: float | None`
  - `fields_updated: list[str]`
  - `old_values: dict[str, Any]`
  - `new_values: dict[str, Any]`
- [ ] Add `execution_result: ExecutionResult | None` to `PendingAction` dataclass
- [ ] Add `execution_result` to `PendingActionUpdate` model

### 3. Database Model (`shared/database/models.py`)
- [ ] Add `execution_result = Column(NVARCHAR(None))` to `PendingActionModel`

### 4. Repository (`shared/database/repositories/pending_action.py`)
- [ ] Update `_model_to_domain` to parse JSON and include `execution_result`
- [ ] Update `update` to handle JSON serialization if needed

### 5. Service Layer (`features/order_management/service.py`)
- [ ] In `execute_action_unified`, after successful execution:
  - Capture the execution details from `_execute_update` or `_execute_create`
  - Build `ExecutionResult` dict
  - Store via `PendingActionUpdate(execution_result=...)`
- [ ] Modify `_execute_update` to return `ExecutionResult` dict:
  - `old_values` from HTC before update
  - `new_values` that were applied
  - `fields_updated` list
- [ ] Modify `_execute_create` to return `ExecutionResult` dict:
  - `old_values` = None
  - `new_values` = all fields sent to HTC (locations, datetimes, notes, dims, etc.)
  - `fields_updated` = all populated field names
  - `htc_order_number` = newly created order number

### 6. API Schema (`api/schemas/pending_actions.py`)
- [ ] Create `ExecutionResultSchema` Pydantic model
- [ ] Add `execution_result: ExecutionResultSchema | None` to `GetPendingActionDetailResponse`

### 7. Frontend Types (`client/.../types.ts`)
- [ ] Add `ExecutionResult` interface
- [ ] Add `execution_result: ExecutionResult | null` to `PendingActionDetail`

### 8. Frontend UI
- [ ] `PendingOrderDetailView`: For completed actions, show "Execution Summary" instead of editable fields
  - Display each field that changed with old → new values
  - Show executed_at timestamp and approver
- [ ] `PendingUpdateDetailView`: Same treatment

## Order of Implementation

1. Database schema + model (foundation)
2. Backend types (contracts)
3. Repository (persistence)
4. Service layer (populate on execution)
5. API schema (expose to frontend)
6. Frontend types (TypeScript contracts)
7. Frontend UI (display)
