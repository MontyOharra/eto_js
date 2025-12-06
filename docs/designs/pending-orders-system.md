# Pending Orders System - Design Document

## Overview

The Pending Orders System handles the compilation of order data from multiple ETO runs into complete orders that can be created in the HTC Access database. This addresses the core challenge that order information often arrives across multiple forms/PDFs, and the system needs to aggregate this data intelligently.

## Problem Statement

### Current Challenge
- Order data arrives via email PDFs in random order
- A single order's data may be spread across multiple forms (e.g., routing info on one form, MAWB on another)
- Forms may arrive minutes, hours, or days apart
- Customers sometimes send updated forms that should overwrite previous data
- Customers sometimes send outdated forms that should NOT overwrite current data
- Manual order creation in Access must coexist with automated ETO processing

### Requirements
1. **Aggregate data from multiple runs** into a single order
2. **Auto-create orders** when all required fields are present
3. **Prevent automatic updates** to existing orders (require user approval)
4. **Handle conflicts** when multiple forms provide different values for the same field
5. **Maintain audit trail** of which runs contributed which data
6. **Coordinate with VBA/Access** for order number generation (no collisions)

## Architecture

### Data Flow

```
PDF Arrives → ETO Run → Pipeline Execution → Output Channels
                                                    ↓
                                          ┌─────────────────┐
                                          │ Output Executor │
                                          └────────┬────────┘
                                                   ↓
                              ┌────────────────────┴────────────────────┐
                              ↓                                         ↓
                    Order exists in HTC?                      Pending order exists?
                              ↓                                         ↓
                    ┌────YES──┴──NO────┐                    ┌────YES───┴───NO────┐
                    ↓                  ↓                    ↓                    ↓
            Queue as pending     Check pending         Merge fields        Create pending
            update (review)      orders table          into pending        order record
                                                            ↓
                                                   Has all required fields?
                                                            ↓
                                                   ┌───YES──┴──NO───┐
                                                   ↓                ↓
                                            Create in HTC      Wait for
                                            Mark complete      more data
```

### Key Concepts

#### 1. HAWB as Primary Key
- HAWB (House Air Waybill) is the unique identifier for an order
- All data aggregation happens by HAWB
- One HAWB = one pending order = one HTC order

#### 2. Output Channels (not Output Modules)
Instead of designing modules for every combination of form fields, we use individual output channels per field:

```
Pipeline: "SOS Routing Form"
┌─────────────────────────────────────────────────────────────┐
│  [Extract] → [Transform] → ┬→ [HAWBOutput]      (required)  │
│                            ├→ [MAWBOutput]                  │
│                            ├→ [PickupTimeOutput]            │
│                            ├→ [PickupAddrOutput]            │
│                            ├→ [DeliveryTimeOutput]          │
│                            └→ [DeliveryAddrOutput]          │
└─────────────────────────────────────────────────────────────┘
```

**Validation Rule:** Pipeline must have exactly one HAWB output + at least one other field.

**HAWB Output Flexibility:** Can accept single string or array of strings (for forms that update multiple HAWBs with same MAWB).

#### 3. Order States

| State | Description |
|-------|-------------|
| `incomplete` | Missing one or more required fields |
| `ready` | Has all required fields, can be created in HTC |
| `created` | Successfully created in HTC database |

#### 4. Update States

| State | Description |
|-------|-------------|
| `pending` | Awaiting user review |
| `approved` | User approved, applied to HTC |
| `rejected` | User rejected the change |
| `superseded` | Another update for same field was approved |

### Required vs Optional Fields

**Required for order creation:**
- `hawb` - House Air Waybill number
- `customer_id` - Customer identifier (from template config)
- `pickup_address_id` or `pickup_address_text`
- `pickup_time_start`
- `pickup_time_end`
- `delivery_address_id` or `delivery_address_text`
- `delivery_time_start`
- `delivery_time_end`

**Optional fields:**
- `mawb` - Master Air Waybill
- `pickup_notes`
- `delivery_notes`
- `order_notes`
- `pieces`
- `weight`
- `dims`

### Conflict Handling

#### Pre-Creation Conflicts (during pending order accumulation)
When two runs provide different values for the same field before the order is created:

**Decision: Last Write Wins + History Tracking**
- The pending order stores the latest value
- A history table tracks all overwrites
- User can see "Field X was overwritten (old → new)" in the order history
- Visual indicator (⚠️) draws attention without blocking

#### Post-Creation Conflicts (updates to existing HTC orders)
When a run provides data for an order that already exists in HTC:

**Decision: Queue for User Review**
- All proposed changes go to a pending updates queue
- User must approve or reject each change
- Multiple updates to the same field are kept (user picks which one)
- When one is approved, others are marked `superseded`

## Database Schema

### Pending Orders Table (ETO Database)

```sql
CREATE TABLE pending_orders (
    id INTEGER PRIMARY KEY,
    hawb VARCHAR(50) UNIQUE NOT NULL,
    customer_id INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'incomplete',  -- incomplete, ready, created
    htc_order_number DOUBLE NULL,  -- Set when created in HTC

    -- Field values (all nullable until provided)
    mawb VARCHAR(50) NULL,
    pickup_address_id INTEGER NULL,
    pickup_address_text TEXT NULL,
    pickup_time_start DATETIME NULL,
    pickup_time_end DATETIME NULL,
    pickup_notes TEXT NULL,
    delivery_address_id INTEGER NULL,
    delivery_address_text TEXT NULL,
    delivery_time_start DATETIME NULL,
    delivery_time_end DATETIME NULL,
    delivery_notes TEXT NULL,
    order_notes TEXT NULL,
    pieces INTEGER NULL,
    weight DECIMAL(10,2) NULL,

    -- Timestamps
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    htc_created_at DATETIME NULL
);
```

### Pending Order Contributions Table

```sql
CREATE TABLE pending_order_contributions (
    id INTEGER PRIMARY KEY,
    pending_order_id INTEGER NOT NULL REFERENCES pending_orders(id),
    eto_run_id INTEGER NOT NULL,
    eto_sub_run_id INTEGER NOT NULL,

    contribution_type VARCHAR(30) NOT NULL,  -- created_pending, added_fields, overwrote_fields, triggered_creation
    fields_contributed JSON NOT NULL,  -- ["mawb", "pickup_time_start", ...]
    previous_values JSON NULL,  -- For overwrites: {"field": "old_value", ...}
    new_values JSON NOT NULL,

    contributed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### Pending Updates Table

```sql
CREATE TABLE pending_updates (
    id INTEGER PRIMARY KEY,
    htc_order_number DOUBLE NOT NULL,
    hawb VARCHAR(50) NOT NULL,

    field_name VARCHAR(50) NOT NULL,
    field_label VARCHAR(100) NOT NULL,  -- Human-readable
    current_value TEXT NULL,
    proposed_value TEXT NOT NULL,

    source_run_id INTEGER NOT NULL,
    source_sub_run_id INTEGER NOT NULL,

    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending, approved, rejected, superseded
    proposed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reviewed_by VARCHAR(100) NULL,
    reviewed_at DATETIME NULL
);
```

## Order Number Generation (HTC Access)

### The Problem
Multiple sources can create orders simultaneously:
- Manual creation via Access/VBA forms
- Python ETO system
- Potentially multiple ETO workers

### The Solution
Use the existing `Orders In Work` (OIW) table's unique constraint as an atomic lock:

```python
def reserve_order_number(co_id: int, br_id: int) -> int:
    while True:
        # 1. Read current LON (Last Order Number)
        candidate = get_last_order_number(co_id, br_id) + 1

        # 2. Try to claim via INSERT (atomic due to unique constraint)
        try:
            insert_into_oiw(co_id, br_id, candidate)
            return candidate  # Success!
        except IntegrityError:
            # Someone else claimed it, try next
            candidate += 1
            continue

def finalize_order(co_id: int, br_id: int, order_no: int):
    # After order created successfully:
    update_lon(co_id, br_id, order_no)  # Update last order number
    delete_from_oiw(co_id, br_id, order_no)  # Remove reservation
```

**Key Insight:** The OIW table has a unique constraint on `(oiw_coid, oiw_brid, oiw_orderno)`, making the INSERT atomic. If two processes try to claim the same number, one will fail and retry.

**No VBA Changes Required:** This approach uses the same tables and flow as the existing VBA code.

## Frontend Design

### Views Needed

1. **Pending Orders View**
   - Shows orders waiting for more data or ready to create
   - Emphasizes what's missing
   - Should support taking action (manual completion?)

2. **Pending Updates View**
   - Decision queue for approving/rejecting changes
   - Grouped by order for context
   - Bulk actions for efficiency
   - Clear before/after comparison

3. **Order History View**
   - Timeline of how an order was built
   - Shows which runs contributed which fields
   - Highlights overwrites and conflicts

### Design Questions (Unresolved)

1. **What should the primary view emphasize?**
   - Incomplete orders needing attention?
   - Updates requiring decisions?
   - Recently created orders?

2. **Card vs Table layout for pending orders?**
   - Cards could show field completion visually
   - Tables are more compact for scanning

3. **How to handle the approval workflow?**
   - One-by-one review?
   - Batch approval with exceptions?
   - Auto-approve under certain conditions?

4. **What's the typical HAWB format?**
   - Needed for realistic mock data
   - Affects search/filter design

## API Endpoints

```
GET  /api/order-management/pending-orders
GET  /api/order-management/pending-orders/{id}
GET  /api/order-management/pending-updates
GET  /api/order-management/pending-updates?group_by_order=true
POST /api/order-management/pending-updates/{id}/approve
POST /api/order-management/pending-updates/{id}/reject
POST /api/order-management/pending-updates/bulk-approve
POST /api/order-management/pending-updates/bulk-reject
GET  /api/order-management/orders/{hawb}/history
```

## Implementation Status

### Completed
- [x] Design document (this file)
- [x] Frontend feature structure (`features/order-management/`)
- [x] TypeScript types for domain and API
- [x] TanStack Query hooks for API calls
- [x] Basic component structure (tables, headers, detail views)
- [x] Dashboard tab added ("Orders")
- [x] Order number generation logic designed (collision-free)

### Not Started
- [ ] Mock data for frontend testing
- [ ] Backend database models
- [ ] Backend API endpoints
- [ ] Output channel modules
- [ ] Output execution service refactor
- [ ] Integration with existing ETO pipeline

## Open Questions

1. Should there be a way to manually complete a pending order (fill in missing fields via UI)?
2. What happens to a pending order if the HAWB was wrong? Delete? Edit?
3. Should auto-creation happen immediately when ready, or batch at intervals?
4. How long should pending orders be kept if never completed?
5. Should there be notifications when orders are ready or updates are pending?
