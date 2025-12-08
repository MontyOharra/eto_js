# Pending Orders System - Design Document v2

## Overview

The Pending Orders System handles the compilation of order data from multiple ETO runs into complete orders that can be created in the HTC Access database. Data arrives via PDF attachments in emails, processed through the ETO pipeline with output channels that feed into this system.

## Prerequisites

**Output Channel System** must be implemented first. The current output module system needs to be refactored to support individual field-level output channels instead of monolithic form-based modules.

---

## Architecture

### Data Flow

```
Email PDF → ETO Pipeline → Output Channels → Pending Orders System
                                                      │
                                    ┌─────────────────┴─────────────────┐
                                    ▼                                   ▼
                            Order NOT in HTC                     Order EXISTS in HTC
                                    │                                   │
                                    ▼                                   ▼
                            Add to pending_order              Create pending_update
                            + pending_order_history           (queue for review)
                                    │
                                    ▼
                            Check for conflicts
                            (multiple values for same field)
                                    │
                        ┌───────────┴───────────┐
                        ▼                       ▼
                   No conflict              Conflict exists
                   (auto-set field)         (set field to NULL)
                        │                       │
                        └───────────┬───────────┘
                                    ▼
                            All required fields set?
                                    │
                        ┌───────────┴───────────┐
                        ▼                       ▼
                       YES                      NO
                   (status=ready)          (status=incomplete)
                        │                       │
                        ▼                       ▼
                   AUTO-CREATE              Wait for
                   in HTC immediately       more data
                        │
                        ▼
                   status=created
```

---

## Database Schema

### pending_orders

Primary table storing the compiled order state.

```sql
CREATE TABLE pending_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hawb VARCHAR(50) UNIQUE NOT NULL,
    customer_id INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'incomplete',  -- incomplete, ready, created
    htc_order_number DOUBLE NULL,          -- Set when created in HTC
    htc_created_at DATETIME NULL,          -- Set when created in HTC

    -- Required fields (must all be non-null for status=ready)
    pickup_address TEXT NULL,
    pickup_time_start VARCHAR(20) NULL,
    pickup_time_end VARCHAR(20) NULL,
    delivery_address TEXT NULL,
    delivery_time_start VARCHAR(20) NULL,
    delivery_time_end VARCHAR(20) NULL,

    -- Optional fields
    mawb VARCHAR(50) NULL,
    pickup_notes TEXT NULL,
    delivery_notes TEXT NULL,
    order_notes TEXT NULL,
    pieces INTEGER NULL,
    weight DECIMAL(10,2) NULL,

    -- Timestamps
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_pending_orders_status ON pending_orders(status);
CREATE INDEX idx_pending_orders_hawb ON pending_orders(hawb);
```

### pending_order_history

Tracks all field contributions from sub-runs. Used to compute conflicts and provide audit trail.

```sql
CREATE TABLE pending_order_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pending_order_id INTEGER NOT NULL REFERENCES pending_orders(id) ON DELETE CASCADE,
    sub_run_id INTEGER NOT NULL,
    pdf_filename VARCHAR(255) NOT NULL,
    email_subject VARCHAR(500) NULL,
    field_name VARCHAR(50) NOT NULL,
    value TEXT NOT NULL,
    selected BOOLEAN NOT NULL DEFAULT FALSE,  -- TRUE if user chose this value
    contributed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_poh_pending_order ON pending_order_history(pending_order_id);
CREATE INDEX idx_poh_field ON pending_order_history(pending_order_id, field_name);
CREATE INDEX idx_poh_sub_run ON pending_order_history(sub_run_id);
```

### pending_updates

Queues proposed changes for orders that already exist in HTC.

```sql
CREATE TABLE pending_updates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hawb VARCHAR(50) NOT NULL,
    htc_order_number DOUBLE NOT NULL,
    sub_run_id INTEGER NOT NULL,
    pdf_filename VARCHAR(255) NOT NULL,
    email_subject VARCHAR(500) NULL,
    field_name VARCHAR(50) NOT NULL,
    proposed_value TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending, approved, rejected
    proposed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reviewed_at DATETIME NULL
);

CREATE INDEX idx_pending_updates_status ON pending_updates(status);
CREATE INDEX idx_pending_updates_hawb ON pending_updates(hawb);
CREATE INDEX idx_pending_updates_order ON pending_updates(htc_order_number);
```

---

## Required Fields

Hardcoded list of fields that must be non-null for auto-creation:

```python
REQUIRED_FIELDS = [
    'pickup_address',
    'pickup_time_start',
    'pickup_time_end',
    'delivery_address',
    'delivery_time_start',
    'delivery_time_end',
]
```

---

## Core Logic

### Field State Calculation

Field state is computed from history, not stored directly:

```python
def get_field_state(pending_order_id: int, field_name: str) -> dict:
    """
    Returns one of:
    - {'state': 'empty'} - No values received yet
    - {'state': 'set', 'value': '...', 'source': {...}} - Single value or all agree, auto-set
    - {'state': 'confirmed', 'value': '...', 'source': {...}} - User explicitly selected
    - {'state': 'conflict', 'options': [...]} - Multiple different values, needs resolution
    """
    history = get_history_for_field(pending_order_id, field_name)

    if len(history) == 0:
        return {'state': 'empty'}

    # Check if user already selected a value
    selected = [h for h in history if h.selected]
    if selected:
        return {
            'state': 'confirmed',
            'value': selected[0].value,
            'source': {
                'sub_run_id': selected[0].sub_run_id,
                'pdf_filename': selected[0].pdf_filename,
                'email_subject': selected[0].email_subject,
            }
        }

    # Get unique values from all contributions
    unique_values = {h.value for h in history}

    if len(unique_values) == 1:
        # All sources agree - auto-set
        return {
            'state': 'set',
            'value': history[0].value,
            'source': {
                'sub_run_id': history[0].sub_run_id,
                'pdf_filename': history[0].pdf_filename,
                'email_subject': history[0].email_subject,
            }
        }
    else:
        # Conflict - multiple different values
        return {
            'state': 'conflict',
            'options': [
                {
                    'value': h.value,
                    'sub_run_id': h.sub_run_id,
                    'pdf_filename': h.pdf_filename,
                    'email_subject': h.email_subject,
                    'contributed_at': h.contributed_at,
                }
                for h in history
            ]
        }
```

### Adding Field Contributions

When a new value arrives from a sub-run:

```python
def add_field_contribution(
    pending_order_id: int,
    field_name: str,
    value: str,
    sub_run_id: int,
    pdf_filename: str,
    email_subject: str
):
    # 1. Add to history
    create_history_entry(
        pending_order_id=pending_order_id,
        sub_run_id=sub_run_id,
        pdf_filename=pdf_filename,
        email_subject=email_subject,
        field_name=field_name,
        value=value,
        selected=False
    )

    # 2. Recalculate field state
    state = get_field_state(pending_order_id, field_name)

    if state['state'] == 'set':
        # Single value (or all sources agree) - set the field
        set_pending_order_field(pending_order_id, field_name, state['value'])
    elif state['state'] == 'conflict':
        # Conflict introduced - clear the field, user must decide
        set_pending_order_field(pending_order_id, field_name, None)
        # Clear any previous selection
        clear_selected_for_field(pending_order_id, field_name)

    # 3. Recalculate order status
    update_order_status(pending_order_id)
```

### Resolving Conflicts

When user selects a value from conflict options:

```python
def resolve_conflict(pending_order_id: int, field_name: str, history_id: int):
    # 1. Clear any previous selection for this field
    clear_selected_for_field(pending_order_id, field_name)

    # 2. Mark the chosen history entry as selected
    mark_history_selected(history_id)

    # 3. Get the selected value and set it on the order
    history_entry = get_history_entry(history_id)
    set_pending_order_field(pending_order_id, field_name, history_entry.value)

    # 4. Recalculate order status
    update_order_status(pending_order_id)
```

### Order Status Calculation

```python
REQUIRED_FIELDS = [
    'pickup_address',
    'pickup_time_start',
    'pickup_time_end',
    'delivery_address',
    'delivery_time_start',
    'delivery_time_end',
]

def update_order_status(pending_order_id: int):
    pending_order = get_pending_order(pending_order_id)

    if pending_order.status == 'created':
        return  # Already created, no change

    # Check if all required fields are set (non-null)
    all_required_set = all(
        getattr(pending_order, field) is not None
        for field in REQUIRED_FIELDS
    )

    if all_required_set:
        pending_order.status = 'ready'
        save_pending_order(pending_order)
        # Trigger immediate auto-creation
        create_order_in_htc(pending_order_id)
    else:
        pending_order.status = 'incomplete'
        save_pending_order(pending_order)
```

### Handling Output Channel Data

Main entry point when pipeline outputs data:

```python
def handle_output_channels(
    hawb: str,
    field_data: dict,          # {'pickup_address': '123 Main St', 'mawb': '999-123', ...}
    sub_run_id: int,
    pdf_filename: str,
    email_subject: str,
    customer_id: int
):
    # 1. Check if order already exists in HTC
    htc_order = lookup_htc_order_by_hawb(hawb)

    if htc_order:
        # Order already created - queue updates for review
        for field_name, value in field_data.items():
            if field_name == 'hawb':
                continue  # Don't create update for HAWB itself
            create_pending_update(
                hawb=hawb,
                htc_order_number=htc_order.order_number,
                sub_run_id=sub_run_id,
                pdf_filename=pdf_filename,
                email_subject=email_subject,
                field_name=field_name,
                proposed_value=value
            )
        return

    # 2. Find or create pending order
    pending_order = get_pending_order_by_hawb(hawb)
    if not pending_order:
        pending_order = create_pending_order(hawb=hawb, customer_id=customer_id)

    # 3. Add each field contribution
    for field_name, value in field_data.items():
        if field_name == 'hawb':
            continue  # HAWB is the key, not a field to track
        add_field_contribution(
            pending_order_id=pending_order.id,
            field_name=field_name,
            value=value,
            sub_run_id=sub_run_id,
            pdf_filename=pdf_filename,
            email_subject=email_subject
        )
```

---

## HTC Order Creation

When status becomes 'ready', immediately create in HTC:

```python
def create_order_in_htc(pending_order_id: int):
    pending_order = get_pending_order(pending_order_id)

    if pending_order.status != 'ready':
        return  # Not ready yet

    # 1. Reserve order number (collision-free via OIW table)
    order_number = reserve_order_number(co_id=1, br_id=1)

    try:
        # 2. Create order in HTC Access database
        create_htc_order(
            order_number=order_number,
            hawb=pending_order.hawb,
            pickup_address=pending_order.pickup_address,
            pickup_time_start=pending_order.pickup_time_start,
            pickup_time_end=pending_order.pickup_time_end,
            delivery_address=pending_order.delivery_address,
            delivery_time_start=pending_order.delivery_time_start,
            delivery_time_end=pending_order.delivery_time_end,
            mawb=pending_order.mawb,
            pieces=pending_order.pieces,
            weight=pending_order.weight,
            # ... other fields
        )

        # 3. Update pending order status
        pending_order.status = 'created'
        pending_order.htc_order_number = order_number
        pending_order.htc_created_at = datetime.now()
        save_pending_order(pending_order)

        # 4. Finalize order number (update LON, remove OIW reservation)
        finalize_order_number(co_id=1, br_id=1, order_number=order_number)

    except Exception as e:
        # Release reservation on failure
        release_order_reservation(co_id=1, br_id=1, order_number=order_number)
        raise
```

---

## Pending Updates (Post-Creation)

### Fetching Current Values

Current values come from HTC, not our database:

```python
def get_pending_update_with_current_value(update_id: int) -> dict:
    update = get_pending_update(update_id)

    # Fetch current value from HTC
    htc_order = get_htc_order(update.htc_order_number)
    current_value = get_htc_field_value(htc_order, update.field_name)

    return {
        'id': update.id,
        'hawb': update.hawb,
        'htc_order_number': update.htc_order_number,
        'field_name': update.field_name,
        'current_value': current_value,  # From HTC
        'proposed_value': update.proposed_value,
        'pdf_filename': update.pdf_filename,
        'email_subject': update.email_subject,
        'proposed_at': update.proposed_at,
    }
```

### Approving Updates

```python
def approve_pending_update(update_id: int):
    update = get_pending_update(update_id)

    # 1. Update HTC directly
    update_htc_order_field(
        order_number=update.htc_order_number,
        field_name=update.field_name,
        value=update.proposed_value
    )

    # 2. Mark as approved
    update.status = 'approved'
    update.reviewed_at = datetime.now()
    save_pending_update(update)
```

### Rejecting Updates

```python
def reject_pending_update(update_id: int):
    update = get_pending_update(update_id)

    # Just mark as rejected, no HTC change
    update.status = 'rejected'
    update.reviewed_at = datetime.now()
    save_pending_update(update)
```

---

## API Endpoints

### Pending Orders

```
GET  /api/pending-orders
     Query params: status, search, sort_by, sort_order, limit, offset
     Returns: List of pending orders with computed field states

GET  /api/pending-orders/{id}
     Returns: Full pending order with all field states and history

POST /api/pending-orders/{id}/resolve-conflict
     Body: { field_name: string, history_id: int }
     Resolves a conflict by selecting a specific history entry
```

### Pending Updates

```
GET  /api/pending-updates
     Query params: status, hawb, sort_by, sort_order
     Returns: List of pending updates (current_value fetched from HTC)

POST /api/pending-updates/{id}/approve
     Approves update and applies to HTC

POST /api/pending-updates/{id}/reject
     Rejects update (no HTC change)

POST /api/pending-updates/bulk-approve
     Body: { update_ids: int[] }
     Bulk approve multiple updates

POST /api/pending-updates/bulk-reject
     Body: { update_ids: int[] }
     Bulk reject multiple updates
```

### PDF Viewing

```
GET  /api/pending-orders/{id}/pdfs
     Returns: List of all PDFs that contributed to this order

GET  /api/sub-runs/{id}/pdf
     Returns: The PDF file for a specific sub-run
```

---

## Frontend Components

### Pending Order Detail View (Layout A)

Located at: `client/src/renderer/pages/dashboard/orders/layout-a.tsx`

Features:
- Header with HAWB, Customer, and status badge
- Two-column layout:
  - Left: Field list with values/conflicts
  - Right: Source PDFs panel with "View All PDFs" button
- Conflict resolution via dropdown
- Compact rows showing: status icon, label, value, source PDF

### Pending Orders List

Located at: `client/src/renderer/pages/dashboard/orders/index.tsx`

Features:
- Toggle between "Pending Orders" and "Pending Updates" views
- Filtering by status, search
- Pagination
- Click row to view detail

### Pending Updates View

Features:
- Grouped by order
- Shows current value (from HTC) vs proposed value
- Approve/Reject buttons per update
- Bulk approve/reject actions

---

## Implementation Order

### Phase 1: Output Channel System (PREREQUISITE)
1. Design output channel architecture
2. Refactor pipeline execution to support channels
3. Implement channel-based output modules
4. Update existing pipelines to use channels

### Phase 2: Database & Backend
1. Create database migrations for new tables
2. Implement pending order service
3. Implement field state calculation logic
4. Implement conflict resolution
5. Implement auto-creation trigger
6. Implement HTC integration (create order, update order)
7. Implement pending updates service
8. Create API endpoints

### Phase 3: Frontend Integration
1. Connect pending orders list to real API
2. Connect detail view to real API
3. Implement conflict resolution UI actions
4. Implement pending updates list
5. Implement approve/reject actions
6. Implement PDF viewing

### Phase 4: Testing & Polish
1. End-to-end testing with real PDFs
2. Error handling and edge cases
3. Performance optimization
4. Dispatcher feedback and refinements

---

## Open Questions (Resolved)

| Question | Decision |
|----------|----------|
| Auto vs manual creation? | Auto-create immediately when ready |
| Conflict storage? | Computed from history table, not stored |
| Required fields configurable? | Hardcoded list |
| Track who approved updates? | No, not needed |
| Re-read from HTC? | Yes, pending updates show current value from HTC |
