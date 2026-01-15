# HTC Order Execution Implementation Plan

This document captures the full implementation plan for executing pending actions (creates and updates) against the HTC database.

## Overview

The Order Management system accumulates field values from PDF extractions into `pending_actions` and `pending_action_fields` tables. When a user approves an action, the system must execute it against the HTC Access database - either creating a new order or updating an existing one.

## Current State

### Relevant Services

1. **OrderManagementService** (`server/src/features/order_management/service.py`)
   - `approve_action()` - Currently a mock that logs and sets status to `completed`
   - Handles field accumulation, conflict resolution, field approval toggles

2. **HtcIntegrationService** (`server/src/features/htc_integration/service.py`)
   - `create_order()` - Creates HTC order (currently accepts address strings, needs refactor)
   - `update_order()` - Updates existing HTC order (same refactor needed)
   - `find_or_create_address()` - Resolves or creates addresses
   - `process_attachments()` - Copies PDFs to HTC attachment storage

### Field Structure in Pending Actions

Fields are stored in `pending_action_fields` with JSON values:

| Field Name | Data Type | Stored Structure |
|------------|-----------|------------------|
| `pickup_location` | `location` | `{address_id: int\|null, name: str, address: str}` |
| `delivery_location` | `location` | `{address_id: int\|null, name: str, address: str}` |
| `pickup_datetime` | `datetime_range` | `{date: "YYYY-MM-DD", time_start: "HH:MM", time_end: "HH:MM"}` |
| `delivery_datetime` | `datetime_range` | `{date: "YYYY-MM-DD", time_start: "HH:MM", time_end: "HH:MM"}` |
| `pickup_notes` | `string` | Plain string |
| `delivery_notes` | `string` | Plain string |
| `order_notes` | `string` | Plain string |
| `mawb` | `string` | Plain string |
| `dims` | `dims` | `[{length, width, height, qty, weight, dim_weight}, ...]` |

---

## Complete Execution Flow

### Phase 0: Pre-Validation

```
1. Validate action is in approvable state
   - ONLY "ready" status is approvable
   - "failed" status can only be reprocessed (not approved directly)
2. Set status to "processing" immediately
```

### Phase 1: TOCTOU Check & Recalculation

TOCTOU = Time of Check, Time of Use. The HTC state may have changed since the action was created.

```
Get current HTC state: order_count = count_orders(customer_id, hawb)

CASE: action.action_type == "create"
├── order_count == 0 → Still a create, proceed normally
├── order_count == 1 → ORDER CREATED EXTERNALLY
│   ├── Get order_number from HTC
│   ├── Get current HTC field values
│   ├── Compare pending fields against HTC values
│   ├── Filter out fields that now match HTC (they're not "changes" anymore)
│   ├── Update action: action_type="update", htc_order_number=order_number
│   ├── Recalculate status
│   ├── Return: requires_review=true, reason="order_created_externally"
│   └── Frontend shows popup, user reviews updated detail view
└── order_count > 1 → AMBIGUOUS
    ├── Return: requires_review=true, reason="ambiguous"
    └── User must resolve manually in HTC

CASE: action.action_type == "update"
├── order_count == 0 → ORDER DELETED, convert to create
│   ├── Update action: action_type="create", htc_order_number=null
│   ├── Recalculate status (may need more required fields now)
│   ├── Return: requires_review=true, reason="order_deleted_converting_to_create"
│   └── User reviews as create, can approve or reject
├── order_count == 1 → Still update, but check for HTC changes
│   ├── Get current HTC field values
│   ├── Compare selected+approved fields against CURRENT HTC values
│   ├── original_fields = fields user selected
│   ├── still_different = fields that still differ from HTC now
│   ├── IF still_different != original_fields:
│   │   ├── Return: requires_review=true, reason="htc_values_changed"
│   │   └── Frontend shows popup, user reviews
│   ├── IF still_different is empty:
│   │   ├── Return: requires_review=true, reason="no_changes_remaining"
│   │   └── Nothing to update anymore
│   └── ELSE: Proceed with execution
└── order_count > 1 → AMBIGUOUS
    ├── Return: requires_review=true, reason="ambiguous"
    └── User must resolve manually in HTC
```

### Phase 2: Address Resolution

Address creation is separated from order creation. If address creation fails, the action is marked as failed (retryable).

```
FOR each location field (pickup_location, delivery_location):
    IF field is selected AND address_id is NULL:
        TRY:
            new_id = htc_service.find_or_create_address(
                address_string=field.value["address"],
                company_name=field.value["name"]
            )
            resolved_pickup_location_id = new_id  (or resolved_delivery_location_id)
        CATCH:
            Set action status = "failed"
            Set error_message = "Failed to create address: {details}"
            Return failure response
            (User can retry after fixing address data or reprocessing)
    ELSE:
        Use existing address_id from field.value["address_id"]
```

### Phase 3: Execute Against HTC

```
IF action_type == "create":
    order_number = htc_service.create_order(
        customer_id=...,
        hawb=...,
        pickup_location_id=resolved_pickup_location_id,
        delivery_location_id=resolved_delivery_location_id,
        pickup_time_start="{date} {time_start}",  # Reconstructed from datetime_range
        pickup_time_end="{date} {time_end}",
        delivery_time_start="{date} {time_start}",
        delivery_time_end="{date} {time_end}",
        mawb=...,
        pickup_notes=...,
        delivery_notes=...,
        order_notes=...,
        dims=...
    )
ELSE:  # update
    htc_service.update_order(
        order_number=action.htc_order_number,
        pickup_location_id=...,     # Only if that field is being updated
        delivery_location_id=...,   # Only if that field is being updated
        ...other fields that are selected AND approved
    )
```

### Phase 4: Post-Execution

```
1. Process attachments
   - Get PDF sources from sub-runs that contributed to this action
   - Copy to HTC storage via process_attachments()

2. For creates only: Send confirmation email
   - Use active email account from database
   - Send to addresses that provided the order data

3. Update pending action
   - Set status = "completed"
   - Set htc_order_number = order_number (for creates)

4. Broadcast SSE event for UI update
```

---

## HtcIntegrationService Changes

### Current `create_order()` Signature (NEEDS REFACTOR):

```python
def create_order(
    self,
    customer_id: int,
    hawb: str,
    pickup_company_name: str,      # String - internally calls find_or_create
    pickup_address: str,            # String - internally calls find_or_create
    pickup_time_start: str,
    pickup_time_end: str,
    delivery_company_name: str,     # String - internally calls find_or_create
    delivery_address: str,          # String - internally calls find_or_create
    delivery_time_start: str,
    delivery_time_end: str,
    ...
) -> float:
```

### New Signature (AFTER REFACTOR):

```python
def create_order(
    self,
    customer_id: int,
    hawb: str,
    pickup_location_id: float,      # Pre-resolved address ID
    delivery_location_id: float,    # Pre-resolved address ID
    pickup_time_start: str,
    pickup_time_end: str,
    delivery_time_start: str,
    delivery_time_end: str,
    mawb: str | None = None,
    pickup_notes: str | None = None,
    delivery_notes: str | None = None,
    order_notes: str | None = None,
    dims: list[dict] | None = None,
) -> float:
```

**Internal changes:**
- Remove `find_or_create_address()` calls from create_order
- Keep `get_address_info(address_id)` calls to populate order fields from address data
- Keep all order type determination, field population, order number generation, etc.

### Same Pattern for `update_order()`:

```python
def update_order(
    self,
    order_number: float,
    pickup_location_id: float | None = None,    # Pre-resolved, not string
    delivery_location_id: float | None = None,
    pickup_time_start: str | None = None,
    pickup_time_end: str | None = None,
    delivery_time_start: str | None = None,
    delivery_time_end: str | None = None,
    mawb: str | None = None,
    pickup_notes: str | None = None,
    delivery_notes: str | None = None,
    order_notes: str | None = None,
    dims: list[dict] | None = None,
) -> list[str]:
```

---

## API Response Changes

### Current `ApproveActionResponse`:

```python
class ApproveActionResponse(BaseModel):
    pending_action_id: int
    success: bool
    action_type: str
    htc_order_number: float | None
    new_status: str
    message: str | None
```

### New `ApproveActionResponse`:

```python
class ApproveActionResponse(BaseModel):
    pending_action_id: int
    success: bool
    action_type: str
    htc_order_number: float | None
    new_status: str
    message: str | None

    # NEW - for handling state changes
    requires_review: bool = False
    review_reason: str | None = None
```

**Possible `review_reason` values:**
- `"order_created_externally"` - Create became update (order exists now)
- `"order_deleted_converting_to_create"` - Update became create (order was deleted)
- `"htc_values_changed"` - Update fields changed in HTC
- `"no_changes_remaining"` - All fields now match HTC, nothing to update
- `"ambiguous"` - Multiple orders exist for this HAWB

---

## Frontend Handling

When `requires_review=True`:

1. Show popup/modal with message based on `review_reason`:
   - `"order_created_externally"`: "This order was created externally. Please review the update fields."
   - `"order_deleted_converting_to_create"`: "The order was deleted. This has been converted to a create. Please review."
   - `"htc_values_changed"`: "The order was modified in HTC. Please review the updated fields."
   - `"no_changes_remaining"`: "All proposed changes now match the current order. Nothing to update."
   - `"ambiguous"`: "Multiple orders exist for this HAWB. Please resolve manually in HTC."

2. User clicks OK

3. Detail view refreshes (SSE event already broadcast)

4. User sees updated state and can approve again (or reject)

---

## OrderManagementService Changes

### New/Modified Methods

```python
def approve_action(self, pending_action_id: int) -> ApproveActionResponse:
    """Main approval flow - complete rewrite."""

def _verify_htc_state_and_recalculate(
    self, action: PendingAction, selected_fields: dict
) -> tuple[bool, str | None, dict]:
    """
    Check HTC state and recalculate if needed.

    Returns:
        (requires_review, review_reason, fields_to_send)
    """

def _resolve_addresses_for_execution(
    self, fields_to_send: dict
) -> tuple[float | None, float | None]:
    """
    Create addresses for location fields where address_id is None.

    Returns:
        (pickup_location_id, delivery_location_id)

    Raises:
        OutputExecutionError if address creation fails (sets action to failed)
    """

def _transform_fields_for_htc(
    self,
    selected_fields: dict,
    pickup_location_id: float | None,
    delivery_location_id: float | None
) -> dict:
    """
    Transform pending action field values to HTC input format.

    - LocationValue → use resolved pickup_location_id/delivery_location_id
    - DatetimeRangeValue → "{date} {time_start}", "{date} {time_end}"
    - String fields → pass through
    - Dims → pass through as list
    """

def _compare_fields_to_current_htc(
    self, fields: dict, htc_order_number: float
) -> dict:
    """
    Filter fields to only those that differ from current HTC values.
    Used for TOCTOU recalculation.
    """

def _get_pdf_sources_for_action(
    self, pending_action_id: int
) -> list[PdfSource]:
    """
    Get PDF file info for all sub-runs that contributed to this action.
    For attachment processing.
    """

def _send_confirmation_email(
    self, action: PendingAction, order_number: float
) -> None:
    """
    Send confirmation email after successful order creation.
    Uses active email account from database.
    """
```

---

## Error Handling

| Error | Result | User Action |
|-------|--------|-------------|
| Address creation fails | status="failed", error_message set | Retry or reprocess sub-runs |
| Order creation fails | status="failed", error_message set | Retry |
| Order deleted (was update) | requires_review, converts to create | Review as create, approve or reject |
| Ambiguous (multiple orders) | requires_review, reason="ambiguous" | Manual intervention in HTC |
| HTC values changed | requires_review, reason="htc_values_changed" | Review updated fields, re-approve |
| Create became update | requires_review, reason="order_created_externally" | Review as update, approve |
| No changes remaining | requires_review, reason="no_changes_remaining" | Nothing to do, reject or close |
| Attachment processing fails | Log warning, continue | Attachments may be missing |
| Email sending fails | Log warning, continue | Email not sent |

---

## Status Transitions

```
                                    ┌─────────────────────────────────────┐
                                    │                                     │
                                    ▼                                     │
incomplete ──┬──> conflict ──> ready ──> processing ──> completed        │
             │                   │           │                            │
             └──> ready ─────────┘           └──> failed ─────────────────┘
                                                    │        (reprocess sub-runs)
                                                    │
                                                    └──> User can reprocess sub-runs
                                                         to get back to ready state
```

**Approvable states:** `ready` only
**Retryable states:** `failed` (via reprocessing, not direct approval)
**Terminal states:** `completed`, `rejected`

---

## Files to Modify

| File | Changes |
|------|---------|
| `server/src/features/htc_integration/service.py` | Refactor `create_order()` and `update_order()` to accept `pickup_location_id` and `delivery_location_id` instead of strings |
| `server/src/features/order_management/service.py` | Complete rewrite of `approve_action()`, add helper methods |
| `server/src/api/schemas/pending_actions.py` | Add `requires_review` and `review_reason` to `ApproveActionResponse` |
| `client/.../pages/dashboard/orders/index.tsx` | Handle `requires_review` response, show popup |
| `client/.../components/...` | Potentially add review popup component |

---

## Implementation Order

1. **Refactor HtcIntegrationService**
   - Update `create_order()` signature to accept `pickup_location_id`, `delivery_location_id`
   - Update `update_order()` signature similarly
   - Remove internal `find_or_create_address()` calls
   - Keep `get_address_info()` calls for populating order fields

2. **Update API schema**
   - Add `requires_review` and `review_reason` to `ApproveActionResponse`

3. **Implement OrderManagementService helpers**
   - `_resolve_addresses_for_execution()`
   - `_transform_fields_for_htc()`
   - `_compare_fields_to_current_htc()`
   - `_verify_htc_state_and_recalculate()`

4. **Rewrite `approve_action()`**
   - Wire everything together
   - Handle all TOCTOU cases
   - Handle success and failure states

5. **Update frontend**
   - Handle `requires_review` response
   - Show appropriate popup messages
   - Refresh detail view

6. **Implement email sending**
   - Find active email account in database
   - Send confirmation after successful creates

---

## Dims Strategy

**Confirmed:** For updates, use replace strategy - delete all existing dims and insert new ones. This is already implemented in `replace_dims_records()`.

---

## Email Sending

After successful order creation:
- Find active email account in database (location TBD - check `email_accounts` or `system_settings`)
- Send confirmation to addresses that provided the order data
- Failure should log warning but not fail the overall operation
