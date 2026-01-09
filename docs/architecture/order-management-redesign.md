# Order Management Redesign

## Overview

This document describes the redesigned architecture for order management, unifying the previously separate `pending_orders` and `pending_updates` systems into a single `pending_actions` system.

## Problems with Current Design

### TOCTOU (Time-of-Check to Time-of-Use)

1. `OutputProcessingService` determines if HAWB exists in HTC at processing time
2. Creates `pending_order` (create) or `pending_update` based on that check
3. Time passes - user doesn't look at system
4. Someone manually creates the order in HTC
5. User approves in ETO system → **duplicate order created**

### Duplicated Logic

- Identical `_dims_are_equal()` in both services (~70 lines each)
- Field comparison logic duplicated (address ID comparison, string comparison)
- Two different code paths to create pending_updates
- Conflict resolution logic duplicated

### Structural Duplication

- `pending_orders` and `pending_updates` tables have nearly identical schemas
- `pending_order_history` and `pending_update_history` are identical
- `unified_actions_view` exists because UI treats them the same anyway

---

## New Architecture

### Core Insight

The `action_type` (create vs update) should be determined at **execution time**, not at accumulation time. Data accumulates the same way regardless of whether it will become a create or update.

### Database Schema

#### `pending_actions` (Main Record - Lightweight)

```sql
pending_actions
├── id: int PK
├── customer_id: int NOT NULL
├── hawb: str NOT NULL
├── htc_order_number: float NULL  -- set for updates, set after create succeeds
├── action_type: enum('create', 'update', 'ambiguous')
├── status: enum('accumulating', 'incomplete', 'conflict', 'ambiguous', 'ready', 'processing', 'completed', 'failed', 'rejected')
├── required_fields_present: int  -- denormalized count
├── conflict_count: int  -- denormalized count
├── error_message: text NULL
├── error_at: datetime NULL
├── is_read: bool
├── created_at: datetime
├── updated_at: datetime
├── last_processed_at: datetime
│
└── UNIQUE(customer_id, hawb) WHERE status NOT IN ('completed', 'rejected', 'failed')
```

#### `pending_action_fields` (Field Values + History Combined)

```sql
pending_action_fields
├── id: int PK
├── pending_action_id: int FK
├── sub_run_id: int FK NULL       -- NULL = user-provided value (manual entry)
├── field_name: str               -- validated against ORDER_FIELDS constant
├── value: JSON                   -- string, object, array depending on field type
├── is_selected: bool             -- TRUE = this is the chosen value for this field
├── is_approved_for_update: bool  -- TRUE = include this field in HTC update (updates only)
│
└── INDEX(pending_action_id, field_name, is_selected)
```

**Key Design Decisions**:

1. **Single table for values + history**: Instead of hardcoding 13+ field columns on the main record plus a separate history table, we use one table that serves both purposes. The "current value" for a field is simply `WHERE is_selected = TRUE`.

2. **User-provided values**: When `sub_run_id = NULL`, the value was manually entered by the user (not extracted from a document). This allows users to override extracted data with their own values.

3. **Partial updates**: The `is_approved_for_update` flag allows users to cherry-pick which fields to include when executing an update. For creates, all selected fields are sent. For updates, only fields where `is_selected = TRUE AND is_approved_for_update = TRUE` are sent to HTC.

**Field Selection Logic**:
- `is_selected = TRUE` → This value is chosen for conflict resolution
- `is_approved_for_update = TRUE` → User wants this field included in the HTC update

**Execution Logic**:
- `action_type = 'create'`: Send all fields where `is_selected = TRUE`
- `action_type = 'update'`: Send only fields where `is_selected = TRUE AND is_approved_for_update = TRUE`

---

## Order Fields vs Output Channels

These are two distinct concepts that should remain separate:

### Output Channels (Pipeline Output)

What the pipeline produces - raw extracted/transformed data. Defined in the module/pipeline system.

```
Examples:
- pickup_company_name
- pickup_address
- dims
- hawb (used for routing, not stored as field)
```

### Order Fields (Business/HTC Data)

What we store and send to HTC. Defined in code constants.

```
Examples:
- pickup_location (combined from pickup_company_name + pickup_address)
- dims (validated with calculated dim_weight)
- mawb
```

### Field Mapping Layer

A mapping layer transforms output channels into order fields:

```python
@dataclass
class OrderFieldDef:
    name: str
    label: str
    data_type: Literal['string', 'json', 'location', 'dims']
    required: bool
    source_channels: list[str]  # which output channels feed this field


ORDER_FIELDS = {
    # Simple string fields (1:1 mapping)
    "mawb": OrderFieldDef("mawb", "MAWB", "string", False, ["mawb"]),
    "pickup_time_start": OrderFieldDef("pickup_time_start", "Pickup Start", "string", True, ["pickup_time_start"]),
    "pickup_time_end": OrderFieldDef("pickup_time_end", "Pickup End", "string", True, ["pickup_time_end"]),
    "delivery_time_start": OrderFieldDef("delivery_time_start", "Delivery Start", "string", True, ["delivery_time_start"]),
    "delivery_time_end": OrderFieldDef("delivery_time_end", "Delivery End", "string", True, ["delivery_time_end"]),
    "pickup_notes": OrderFieldDef("pickup_notes", "Pickup Notes", "string", False, ["pickup_notes"]),
    "delivery_notes": OrderFieldDef("delivery_notes", "Delivery Notes", "string", False, ["delivery_notes"]),
    "order_notes": OrderFieldDef("order_notes", "Order Notes", "string", False, ["order_notes"]),

    # Complex fields (multiple channels → one field)
    "pickup_location": OrderFieldDef(
        "pickup_location", "Pickup Location", "location", True,
        ["pickup_company_name", "pickup_address"]
    ),
    "delivery_location": OrderFieldDef(
        "delivery_location", "Delivery Location", "location", True,
        ["delivery_company_name", "delivery_address"]
    ),
    "dims": OrderFieldDef("dims", "Dimensions", "dims", False, ["dims"]),
}

REQUIRED_FIELDS = [f.name for f in ORDER_FIELDS.values() if f.required]
```

---

## Complex Field Types

### Location Fields (`pickup_location`, `delivery_location`)

**Problem**: Addresses require lookup/creation in HTC addresses table. User needs visibility into whether address will match or be created.

**Solution**: Resolve at accumulation time, re-verify at execution time.

**Stored JSON Structure**:
```json
{
    "address_id": 12345,      // int if matched, null if new
    "name": "ACME CORP",      // from company_name channel
    "address": "123 MAIN ST, CHICAGO, IL 60601"  // from address channel
}
```

**Frontend Display**:
```
Matched:   ACME CORP (12345): 123 MAIN ST, CHICAGO, IL
New:       NEW COMPANY (NEW): 456 OAK AVE, DALLAS, TX
```

**Resolution Process** (`resolve_location()`):
1. Parse address text using `usaddress` library
2. Search HTC addresses table for match
3. If found: `address_id = match.id`
4. If not found: `address_id = null`
5. Return `{address_id, name, address}`

**At Execution Time**:
- Re-verify address still exists/matches
- If `address_id` is null, create new address in HTC
- Use resolved or newly created `address_id` for order

### Dims Field

**Stored JSON Structure**:
```json
[
    {
        "length": 10,
        "width": 10,
        "height": 10,
        "qty": 2,
        "weight": 50,
        "dim_weight": 6.94  // calculated: L*W*H/144
    }
]
```

**Resolution Process** (`resolve_dims()`):
1. Validate structure of each dim object
2. Calculate `dim_weight` for each
3. Return validated list

---

## Processing Flow

### Accumulation Flow (Sub-Run → Pending Action)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 1: EXTRACT ROUTING INFO                                               │
│                                                                             │
│  - Extract hawb from output channels                                        │
│  - Extract customer_id (from template or output channel)                    │
│                                                                             │
│  Output: (customer_id, hawb)                                                │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 2: DETERMINE ACTION TYPE                                              │
│                                                                             │
│  Query HTC: How many orders exist for (customer_id, hawb)?                  │
│                                                                             │
│  count = 0  ──────► action_type = 'create'                                  │
│  count = 1  ──────► action_type = 'update', htc_order_number = found        │
│  count > 1  ──────► action_type = 'ambiguous', htc_order_number = null      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 3: PROCESS OUTPUT CHANNELS → ORDER FIELDS                             │
│                                                                             │
│  Simple 1:1 mappings:                                                       │
│    mawb ──────────────────────────────► mawb                                │
│    pickup_time_start ─────────────────► pickup_time_start                   │
│    pickup_time_end ───────────────────► pickup_time_end                     │
│    delivery_time_start ───────────────► delivery_time_start                 │
│    delivery_time_end ─────────────────► delivery_time_end                   │
│    pickup_notes ──────────────────────► pickup_notes                        │
│    delivery_notes ────────────────────► delivery_notes                      │
│    order_notes ───────────────────────► order_notes                         │
│                                                                             │
│  Complex mappings:                                                          │
│    pickup_company_name ─┬─► resolve_location() ──► pickup_location          │
│    pickup_address ──────┘                                                   │
│                                                                             │
│    delivery_company_name ─┬─► resolve_location() ──► delivery_location      │
│    delivery_address ──────┘                                                 │
│                                                                             │
│    dims ──────────────────► resolve_dims() ──────► dims                     │
│                                                                             │
│  Output: dict[field_name, processed_value]                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 4: GET OR CREATE PENDING ACTION                                       │
│                                                                             │
│  Look for existing active pending_action for (customer_id, hawb)            │
│                                                                             │
│  If not exists:                                                             │
│    - Create new pending_action record                                       │
│    - Set action_type, customer_id, hawb, htc_order_number                   │
│    - Set status = 'accumulating'                                            │
│                                                                             │
│  If exists:                                                                 │
│    - Verify action_type still matches (could have changed!)                 │
│    - If mismatch: update action_type and htc_order_number                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 5: POPULATE FIELD VALUES                                              │
│                                                                             │
│  For each processed field:                                                  │
│                                                                             │
│    INSERT INTO pending_action_fields (                                      │
│        pending_action_id,                                                   │
│        sub_run_id,                                                          │
│        field_name,                                                          │
│        value,                    -- JSON                                    │
│        is_selected,              -- determined in next step                 │
│        is_approved_for_update    -- default TRUE for new values             │
│    )                                                                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 6: CONFLICT RESOLUTION (is_selected determination)                    │
│                                                                             │
│  For each field_name in this pending_action:                                │
│                                                                             │
│    existing_values = get all rows for (pending_action_id, field_name)       │
│                                                                             │
│    If count = 1 (first value for this field):                               │
│      - Set is_selected = TRUE                                               │
│                                                                             │
│    If count > 1 (additional value):                                         │
│      - Compare new value to currently selected value                        │
│      - If SAME: is_selected = FALSE (duplicate, keep existing selection)    │
│      - If DIFFERENT:                                                        │
│          - Set ALL is_selected = FALSE for this field (conflict!)           │
│          - User must manually resolve                                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 7: UPDATE STATUS                                                      │
│                                                                             │
│  Evaluate pending_action state:                                             │
│                                                                             │
│  If action_type = 'ambiguous':                                              │
│    status = 'ambiguous'  (user must manually specify HTC order)             │
│                                                                             │
│  Else if any field has conflict (multiple values, none selected):           │
│    status = 'conflict'                                                      │
│                                                                             │
│  Else if any required field missing (no selected value):                    │
│    status = 'incomplete'                                                    │
│                                                                             │
│  Else:                                                                      │
│    status = 'ready'                                                         │
│                                                                             │
│  Also update denormalized counts:                                           │
│    - required_fields_present                                                │
│    - conflict_count                                                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Execution Flow (User Approves or Auto-Create)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP E1: RE-CHECK HTC STATE (TOCTOU protection)                            │
│                                                                             │
│  Query HTC again for (customer_id, hawb)                                    │
│                                                                             │
│  If state changed from what we recorded:                                    │
│    - Update action_type and htc_order_number                                │
│    - Re-resolve location fields if needed (address matching may differ)     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP E2: EXECUTE BASED ON ACTION TYPE                                      │
│                                                                             │
│  If action_type = 'create':                                                 │
│    - Get all fields WHERE is_selected = TRUE                                │
│    - For each location field: create address if address_id is null          │
│    - Create dims records in HTC                                             │
│    - Create order in HTC with all selected field values                     │
│    - Attach PDFs                                                            │
│    - Send notification emails                                               │
│                                                                             │
│  If action_type = 'update':                                                 │
│    - Get fields WHERE is_selected = TRUE AND is_approved_for_update = TRUE  │
│    - Compare approved values to current HTC values                          │
│    - Only update fields that differ AND are approved                        │
│    - Handle address/dims updates appropriately                              │
│    - Send notification emails                                               │
│                                                                             │
│  If action_type = 'ambiguous':                                              │
│    - Should not reach here (status blocks execution)                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP E3: UPDATE STATUS TO FINAL STATE                                      │
│                                                                             │
│  On success: status = 'completed', set htc_order_number if was create       │
│  On failure: status = 'failed', set error_message                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Status Flow Diagram

```
                    ┌─────────────────────────────────────────────┐
                    │                                             │
  sub_run data      │                                             ▼
  ──────────────►  accumulating  ──────────────────────────►   ready
                    │  (missing required fields                   │
                    │   or has conflicts)                         │
                    │                                             │
                    ├──► incomplete (missing required fields)     │
                    │                                             │
                    ├──► conflict (conflicting values)            │
                    │                                             │
                    ├──► ambiguous (multiple HTC orders)          │
                    │                                     [user approves OR
                    │                                      auto-create enabled]
                    │                                             │
                    │                                             ▼
                    │                                        processing
                    │                                             │
                    │                              ┌──────────────┼──────────────┐
                    │                              │              │              │
                    │                              ▼              ▼              ▼
                    │                          completed       failed       rejected
                    │                                             │
                    │                                             │ [retry]
                    │                                             └──────► ready
                    │
                    └──────────────────────────────────────────────────► rejected
                                                            [user rejects early]
```

---

## Service Interface

```python
class OrderManagementService:
    """
    Single service handling all pending action processing.

    Replaces:
    - OutputProcessingService
    - OrderManagementService (old)
    """

    def process_sub_run_output(
        self,
        sub_run_id: int,
        customer_id: int,
        output_channel_data: dict[str, Any]
    ) -> int:
        """
        Main entry point - called by EtoRunsService after pipeline execution.

        Accumulates data into pending_action. Does NOT execute against HTC.

        Returns pending_action_id.
        """
        ...

    def execute_action(self, pending_action_id: int) -> ExecuteResult:
        """
        Execute the pending action (create or update in HTC).

        Called by:
        - User approval (manual)
        - Auto-create worker (automatic)

        Re-checks HTC state before executing (TOCTOU protection).
        """
        ...

    def resolve_conflict(
        self,
        pending_action_id: int,
        field_name: str,
        selected_field_id: int
    ) -> None:
        """
        User selects which value to use for a conflicting field.
        Sets is_selected = TRUE for the chosen value, FALSE for others.
        """
        ...

    def set_user_value(
        self,
        pending_action_id: int,
        field_name: str,
        value: Any
    ) -> int:
        """
        User provides their own value for a field (overriding extracted data).

        Creates a new pending_action_fields row with sub_run_id = NULL.
        Sets is_selected = TRUE for this value, FALSE for all others.

        Returns the new field_id.
        """
        ...

    def set_field_approval(
        self,
        pending_action_id: int,
        field_name: str,
        is_approved: bool
    ) -> None:
        """
        User toggles whether a field should be included in an update.

        Sets is_approved_for_update on the currently selected value.
        Only relevant for action_type = 'update'.
        """
        ...

    def reject_action(self, pending_action_id: int, reason: str | None = None) -> None:
        """
        User rejects the pending action (will not be executed).
        """
        ...

    def retry_failed_action(self, pending_action_id: int) -> None:
        """
        Re-attempt execution of a failed action.

        Preserves all field values and user modifications.
        Just retries the HTC write - no data re-extraction.

        Status: 'failed' → 'ready' (worker picks up) or 'processing' (immediate)
        """
        ...

    def cleanup_sub_run_contributions(self, sub_run_id: int) -> CleanupResult:
        """
        Remove all field contributions from a sub_run being deleted/reprocessed.

        Called by EtoRunsService when a sub-run is reprocessed or deleted.

        Steps:
        1. Delete all pending_action_fields WHERE sub_run_id = ?
        2. For each affected pending_action:
           a. Check if any extracted fields remain (sub_run_id IS NOT NULL)
           b. If NO extracted fields remain: delete the entire pending_action
              (user-provided values without document source don't make sense to keep)
           c. If extracted fields remain: recalculate status

        Returns CleanupResult with affected action IDs and whether they were deleted.
        """
        ...
```

---

## Sub-Run Reprocessing & Retry

### Two Types of "Retry"

There are two distinct scenarios that users might call "retry":

#### 1. Retry Execution (HTC write failed)

The field data is fine, but the HTC write failed (network error, database locked, etc.).

**Solution:** Call `retry_failed_action()` - just re-attempt execution without touching field values.

- Preserves all user modifications (manual values, selections, approvals)
- Status: `failed` → `ready` → `processing` → `completed`/`failed`
- Available from the Orders page detail view

#### 2. Reprocess from Source (data was wrong)

User realizes extracted data was wrong and wants to re-extract from the source documents.

**Solution:** Reprocess the sub-run(s) via ETO Runs page, which triggers `cleanup_sub_run_contributions()`.

- This is a "rebuild" not a "retry"
- Clears field contributions from the reprocessed sub-run(s)
- Re-runs pipeline execution on the sub-run(s)
- New field values accumulate into the pending action

### Reprocessing Scenarios

**Scenario A: Single sub-run contributes to action**

```
pending_action (customer=123, hawb="ABC")
└── pending_action_fields
    ├── pickup_time (sub_run_id=5)
    ├── delivery_time (sub_run_id=5)
    └── manual_note (sub_run_id=NULL, user-provided)
```

User reprocesses sub-run 5:
1. `cleanup_sub_run_contributions(5)` called
2. All fields from sub_run_id=5 deleted
3. No extracted fields remain → **entire pending_action deleted** (including user-provided manual_note)
4. Sub-run 5 re-executes, creates new pending_action with fresh data

**Scenario B: Multiple sub-runs from same ETO run**

```
pending_action (customer=123, hawb="ABC")
└── pending_action_fields
    ├── pickup_time (sub_run_id=5, eto_run=100)
    ├── delivery_time (sub_run_id=6, eto_run=100)
    └── dims (sub_run_id=6, eto_run=100)
```

User reprocesses entire ETO run 100:
1. All sub-runs (5, 6) are reprocessed
2. `cleanup_sub_run_contributions()` called for each
3. All fields removed → pending_action deleted
4. Sub-runs re-execute, create new pending_action

**Scenario C: Multiple ETO runs contribute**

```
pending_action (customer=123, hawb="ABC")
└── pending_action_fields
    ├── pickup_time (sub_run_id=5, eto_run=100)
    ├── delivery_time (sub_run_id=10, eto_run=200)
    └── dims (sub_run_id=10, eto_run=200)
```

User reprocesses only ETO run 100:
1. `cleanup_sub_run_contributions(5)` called
2. pickup_time field deleted
3. Extracted fields from sub_run_id=10 still remain
4. Status recalculated (may become `incomplete` if pickup_time was required)
5. Sub-run 5 re-executes, new pickup_time value accumulates

### Key Design Decision

**User-provided values do NOT survive when all extracted values are removed.**

Rationale: User-provided values are meant to augment or override extracted data, not to exist independently. If there's no document source, there's no context for the manual entry. The user can re-enter manual values after reprocessing if needed.

---

## User Interaction Capabilities

### 1. Conflict Resolution

When multiple sub-runs contribute different values for the same field, a conflict occurs (`is_selected = FALSE` for all values). User must pick one:

```
Field: pickup_time_start
├── Value: "08:00" (from sub-run 123) [○ not selected]
├── Value: "09:00" (from sub-run 456) [○ not selected]
└── [User clicks to select one]
```

After selection, the chosen value gets `is_selected = TRUE`.

### 2. Manual Value Entry

User can override any field with their own value:

```
Field: pickup_time_start
├── Value: "08:00" (from sub-run 123) [○ not selected]
├── Value: "09:00" (from sub-run 456) [○ not selected]
└── Value: "10:00" (user-provided)    [● selected]
```

User-provided values have `sub_run_id = NULL` to distinguish them from extracted values.

### 3. Partial Update Approval (Updates Only)

For updates, user can choose which fields to actually send to HTC:

```
Action Type: UPDATE (Order #12345)

Fields to update:
☑ pickup_time_start: "08:00" → "09:00"  [will be sent]
☐ pickup_notes: "" → "Call ahead"        [will NOT be sent]
☑ dims: [...] → [...]                    [will be sent]
```

Only fields with `is_approved_for_update = TRUE` are included in the HTC update.

### 4. Source Visibility

UI can show where each value came from:

- **Extracted**: `sub_run_id IS NOT NULL` - "From document (sub-run #123)"
- **Manual**: `sub_run_id IS NULL` - "Manually entered"

---

## Migration Path

1. Create new `pending_actions` and `pending_action_fields` tables
2. Migrate data from `pending_orders` + `pending_order_history`
3. Migrate data from `pending_updates` + `pending_update_history`
4. Update `OrderManagementService` to new architecture
5. Remove `OutputProcessingService` (merged into `OrderManagementService`)
6. Update `EtoRunsService` to call new service method
7. Drop old tables: `pending_orders`, `pending_order_history`, `pending_updates`, `pending_update_history`
8. Drop `unified_actions_view` (no longer needed)

---

## What Gets Deleted

- `features/output_processing/` - entire directory
- `pending_orders` table
- `pending_updates` table
- `pending_order_history` table
- `pending_update_history` table
- `unified_actions_view`
- All duplicated comparison logic (`_dims_are_equal()`, address comparison, etc.)
- Repositories: `PendingOrderRepository`, `PendingOrderHistoryRepository`, `PendingUpdateRepository`, `PendingUpdateHistoryRepository`, `UnifiedActionsRepository`

---

## Benefits

1. **TOCTOU solved**: `action_type` determined at execution time, not accumulation time
2. **Single code path**: All field comparison, conflict resolution, history management in one place
3. **No duplication**: One `_dims_are_equal()`, one `_compare_fields()`, one status update logic
4. **Simpler mental model**: Just "pending actions" - system figures out create vs update
5. **Extensible**: Adding new order fields doesn't require schema migration
6. **Cleaner EtoRunsService**: Just calls `order_service.process_sub_run_output()` and is done
7. **No separate history table**: Field values table IS the history
