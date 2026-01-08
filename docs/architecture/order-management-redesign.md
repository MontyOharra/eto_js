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
├── sub_run_id: int FK NULL
├── field_name: str  -- validated against ORDER_FIELDS constant
├── value: JSON  -- string, object, array depending on field type
├── is_selected: bool
├── contributed_at: datetime
│
└── INDEX(pending_action_id, field_name, is_selected)
```

**Key Design Decision**: Instead of hardcoding 13+ field columns on the main record plus a separate history table, we use one table that serves both purposes. The "current value" for a field is simply `WHERE is_selected = TRUE`.

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
│        value,           -- JSON                                             │
│        is_selected,     -- determined in next step                          │
│        contributed_at                                                       │
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
│    - For each location field: create address if address_id is null          │
│    - Create dims records in HTC                                             │
│    - Create order in HTC with all field values                              │
│    - Attach PDFs                                                            │
│    - Send notification emails                                               │
│                                                                             │
│  If action_type = 'update':                                                 │
│    - Compare selected values to current HTC values                          │
│    - Only update fields that differ                                         │
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
        """
        ...

    def reject_action(self, pending_action_id: int, reason: str | None = None) -> None:
        """
        User rejects the pending action (will not be executed).
        """
        ...

    def retry_failed_action(self, pending_action_id: int) -> None:
        """
        Reset a failed action to 'ready' status for retry.
        """
        ...

    def cleanup_sub_run_contributions(self, sub_run_id: int) -> dict:
        """
        Remove all field contributions from a sub_run being deleted/reprocessed.
        Recalculates field selections and status.
        """
        ...
```

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
