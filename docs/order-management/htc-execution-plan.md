# HTC Order Execution Implementation Plan

This document captures the full implementation plan for executing pending actions (creates and updates) against the HTC database.

## Overview

The Order Management system accumulates field values from PDF extractions into `pending_actions` and `pending_action_fields` tables. When a user approves an action, the system must execute it against the HTC Access database - either creating a new order or updating an existing one.

## Current State

### What's Been Implemented

- **API Schema**: `requires_review` and `review_reason` fields added to `ApproveActionResponse` and `ExecuteResult`
- **Frontend Alert**: `ReviewRequiredAlert` modal component shows when approval requires review
- **TOCTOU Protection**: Full implementation of time-of-check/time-of-use verification:
  - Type verification on detail view and approval (Create↔Update transitions)
  - Timestamp-based modification check for updates using HTC Orders Update History table
  - Frontend tracks `detailViewedAt` timestamp and passes to approve endpoint
- **Field Storage**: All contributed fields stored regardless of HTC match (changed fields auto-approved, unchanged fields stored but not auto-approved)
- **String Capitalization**: All string fields uppercased in transform layer for HTC compatibility
- **Dims Comparison**: Removed `dim_weight` from comparison/storage (calculated at HTC write time only)

### Relevant Services

1. **OrderManagementService** (`server/src/features/order_management/service.py`)
   - `approve_action()` - Implements TOCTOU checks, returns `requires_review` when state changed
   - `verify_and_update_action_type()` - Checks HTC for type changes (Create↔Update)
   - `_identify_changed_fields()` - Identifies which fields differ from HTC (all stored, changed ones auto-approved)
   - Handles field accumulation, conflict resolution, field approval toggles

2. **HtcIntegrationService** (`server/src/features/htc_integration/service.py`)
   - `create_order()` - Creates HTC order (accepts pre-resolved address IDs)
   - `update_order()` - Updates existing HTC order
   - `check_order_modified_since()` - TOCTOU check for update modifications
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
| `pickup_notes` | `string` | Plain string (UPPERCASED) |
| `delivery_notes` | `string` | Plain string (UPPERCASED) |
| `order_notes` | `string` | Plain string (UPPERCASED) |
| `mawb` | `string` | Plain string (UPPERCASED) |
| `dims` | `dims` | `[{length, width, height, qty, weight}, ...]` (dim_weight calculated at write time) |

---

## Complete Execution Flow

### Phase 0: Pre-Validation

```
1. Validate action is in approvable state
   - ONLY "ready" status is approvable
   - "failed" status can only be reprocessed (not approved directly)
2. Set status to "processing" immediately
```

### Phase 1: TOCTOU Check & Recalculation ✅ IMPLEMENTED

TOCTOU = Time of Check, Time of Use. The HTC state may have changed since the action was created.

**Implementation:**
- `verify_and_update_action_type()` handles Create↔Update transitions
- `check_order_modified_since()` queries HTC Orders Update History table
- Frontend passes `detail_viewed_at` timestamp to detect changes since user viewed detail

```
TOCTOU Check 1: Action Type Verification (on detail view AND approval)
─────────────────────────────────────────────────────────────────────
Get current HTC state: order_count = count_orders(customer_id, hawb)

CASE: action.action_type == "create"
├── order_count == 0 → Still a create, proceed normally
├── order_count == 1 → ORDER CREATED EXTERNALLY
│   ├── Get order_number from HTC
│   ├── Update action: action_type="update", htc_order_number=order_number
│   ├── Recalculate status
│   ├── Return: requires_review=true, reason="type_changed"
│   └── Frontend shows popup, user reviews updated detail view
└── order_count > 1 → AMBIGUOUS
    ├── Return: requires_review=true, reason="ambiguous"
    └── User must resolve manually in HTC

CASE: action.action_type == "update"
├── order_count == 0 → ORDER DELETED, convert to create
│   ├── Update action: action_type="create", htc_order_number=null
│   ├── Recalculate status (may need more required fields now)
│   ├── Return: requires_review=true, reason="type_changed"
│   └── User reviews as create, can approve or reject
├── order_count == 1 → Still update, proceed to TOCTOU Check 2
└── order_count > 1 → AMBIGUOUS
    ├── Return: requires_review=true, reason="ambiguous"
    └── User must resolve manually in HTC

TOCTOU Check 2: Update Modification Check (on approval only)
────────────────────────────────────────────────────────────
IF action_type == "update" AND detail_viewed_at is provided:
    Query HTC Orders Update History: COUNT(*) WHERE order_number AND updated_at > detail_viewed_at
    IF count > 0:
        ├── Return: requires_review=true, reason="htc_values_changed"
        └── Frontend shows popup, user reviews current HTC values
    ELSE:
        └── Proceed with execution
```

### Phase 2: Address Resolution ⏳ PENDING

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

### Phase 3: Execute Against HTC ⏳ PENDING

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

### Phase 4: Post-Execution ⏳ PENDING

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

## HtcIntegrationService Changes ✅ DONE

### `create_order()` Signature:

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

### `update_order()` Signature:

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

### `check_order_modified_since()` - NEW:

```python
def check_order_modified_since(
    self,
    order_number: float,
    since_datetime: datetime,
) -> bool:
    """Check if order was modified in HTC after the given datetime."""
    # Queries [htc300_g040_t030 Orders Update History] table
    # Converts UTC timestamp to CST for HTC comparison
```

---

## API Response Changes ✅ IMPLEMENTED

### `ApproveActionRequest` (Updated)

```python
class ApproveActionRequest(BaseModel):
    # For update actions: when user first viewed detail page
    # Used for TOCTOU check - warns if HTC modified after this time
    detail_viewed_at: datetime | None = None
```

### `ApproveActionResponse` (Updated)

```python
class ApproveActionResponse(BaseModel):
    pending_action_id: int
    success: bool
    action_type: str
    htc_order_number: float | None
    new_status: str
    message: str | None

    # For handling state changes that require user review
    requires_review: bool = False
    review_reason: str | None = None
```

**Possible `review_reason` values:**
- `"type_changed"` - Action type changed (Create↔Update transition)
- `"htc_values_changed"` - HTC order was modified since user viewed detail
- `"ambiguous"` - Multiple orders exist for this HAWB

---

## Frontend Handling ✅ IMPLEMENTED

**Component:** `ReviewRequiredAlert` (`client/src/renderer/features/order-management/components/ReviewRequiredAlert/`)

**TOCTOU Timestamp Tracking:**
- `detailViewedAt` state tracks when user opens detail view
- Passed to `useApprovePendingAction` mutation
- Cleared when returning to list view

When `requires_review=True`:

1. **Alert modal displays** with dynamic message based on action type and reason
2. User clicks OK to dismiss
3. Detail view refreshes (queries are invalidated on approval response)
4. User sees updated state and can approve again (or reject)

---

## OrderManagementService Changes

### Implemented Methods ✅

```python
def verify_and_update_action_type(self, pending_action_id: int) -> VerifyTypeResult:
    """
    TOCTOU Check 1: Verify action type matches current HTC state.
    Called on detail view AND approval.
    Updates action if type changed (Create↔Update).
    """

def _identify_changed_fields(
    self, order_fields: dict, htc_order_number: float
) -> tuple[dict, set[str]]:
    """
    Identify which fields differ from HTC values.
    Returns (all_fields, changed_field_names).
    All fields stored; changed ones get is_approved_for_update=True.
    """

def _filter_unchanged_fields(
    self, fields: dict, current_htc_values: dict
) -> dict:
    """
    Filter detail response for display.
    Multi-value fields always shown (user can change selection).
    Single-value fields only shown if different from HTC.
    """
```

### Pending Methods ⏳

```python
def _resolve_addresses_for_execution(
    self, fields_to_send: dict
) -> tuple[float | None, float | None]:
    """
    Create addresses for location fields where address_id is None.
    """

def _transform_fields_for_htc(
    self,
    selected_fields: dict,
    pickup_location_id: float | None,
    delivery_location_id: float | None
) -> dict:
    """
    Transform pending action field values to HTC input format.
    """

def _get_pdf_sources_for_action(
    self, pending_action_id: int
) -> list[PdfSource]:
    """
    Get PDF file info for all sub-runs that contributed to this action.
    """

def _send_confirmation_email(
    self, action: PendingAction, order_number: float
) -> None:
    """
    Send confirmation email after successful order creation.
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
| Create became update | requires_review, reason="type_changed" | Review as update, approve |
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

## Files Modified

| File | Changes | Status |
|------|---------|--------|
| `server/src/features/htc_integration/service.py` | Refactored `create_order()`, `update_order()` to accept address IDs; added `check_order_modified_since()` | ✅ Done |
| `server/src/features/htc_integration/lookup_utils.py` | Added `check_order_modified_since()` with UTC→CST conversion | ✅ Done |
| `server/src/features/order_management/service.py` | Added `verify_and_update_action_type()`, TOCTOU checks in `approve_action()`, `_identify_changed_fields()` | ✅ Done |
| `server/src/features/order_management/transformers.py` | String field uppercasing, removed dim_weight calculation | ✅ Done |
| `server/src/shared/types/pending_actions.py` | Added `VerifyTypeResult`, removed `dim_weight` from `DimObject` | ✅ Done |
| `server/src/api/schemas/pending_actions.py` | Added `detail_viewed_at` to request, `requires_review`/`review_reason` to response | ✅ Done |
| `server/src/api/routers/pending_actions.py` | Pass `detail_viewed_at` to service | ✅ Done |
| `client/.../pages/dashboard/orders/index.tsx` | Track `detailViewedAt`, pass to approve, unified detail view | ✅ Done |
| `client/.../components/ReviewRequiredAlert/` | Review popup component | ✅ Done |
| `client/.../api/hooks.ts` | Added `detailViewedAt` param, query invalidations | ✅ Done |

---

## Implementation Order

1. **Refactor HtcIntegrationService** ✅ Done
   - Updated `create_order()` signature to accept `pickup_location_id`, `delivery_location_id`
   - Updated `update_order()` signature similarly
   - Added `check_order_modified_since()` for TOCTOU Check 2
   - Removed internal `find_or_create_address()` calls from create/update
   - Removed dead code: `create_order_from_pending()`

2. **Update API schema** ✅ Done
   - Add `detail_viewed_at` to `ApproveActionRequest`
   - Add `requires_review` and `review_reason` to `ApproveActionResponse`
   - Add `requires_review` and `review_reason` to `ExecuteResult`

3. **Implement TOCTOU protection** ✅ Done
   - `verify_and_update_action_type()` for type changes
   - `check_order_modified_since()` for update modifications
   - Frontend timestamp tracking and passing

4. **Implement field storage improvements** ✅ Done
   - Store all fields regardless of HTC match
   - Track changed vs unchanged fields
   - Auto-approve changed fields only
   - Always show multi-value fields in response

5. **Update frontend** ✅ Done
   - Handle `requires_review` response
   - Show `ReviewRequiredAlert` popup with dynamic message
   - Track and pass `detailViewedAt` timestamp
   - Unified detail view for create/update
   - Proper query invalidation for field approval toggles

6. **Implement actual HTC execution** ⏳ NEXT
   - `_resolve_addresses_for_execution()`
   - `_transform_fields_for_htc()`
   - Wire `approve_action()` to actually call `htc_service.create_order()` / `update_order()`

7. **Implement post-execution** ⏳ Pending
   - Attachment processing
   - Email sending for creates

---

## Dims Strategy

**Confirmed:**
- `dim_weight` is NOT stored in pending action fields (removed from `DimObject`)
- `dim_weight` is calculated at HTC write time using formula: L*W*H/144
- For updates, use replace strategy - delete all existing dims and insert new ones (implemented in `replace_dims_records()`)

---

## Email Sending

After successful order creation:
- Find active email account in database (location TBD - check `email_accounts` or `system_settings`)
- Send confirmation to addresses that provided the order data
- Failure should log warning but not fail the overall operation
