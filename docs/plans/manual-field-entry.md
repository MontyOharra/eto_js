# Feature: Manual Field Entry for Pending Actions

## Overview

Allow users to manually add field values to pending actions. Manual entries are treated identically to extracted values - they create a new field option, trigger conflict resolution if values already exist, and become auto-selected. Works for any order field on any action type (create/update).

## Core Concept

**Manual entry = another extraction source.** The system treats user-provided values the same as sub-run output:
- Creates a new `pending_action_field` row with `output_execution_id = NULL`
- If field already has values: triggers conflict logic (all others deselected, new value selected)
- If field doesn't exist: creates with `is_selected = TRUE`
- Status recalculates automatically (existing logic handles this)

## Use Cases

- Fill in missing required fields on incomplete creates
- Provide alternative value when extraction was incorrect
- Add optional fields that weren't extracted
- Override any field value with user knowledge

## Field Types & Input UI

Design must be **extensible** for future field types. Each type has its own input component.

| Type | Input UI | Notes |
|------|----------|-------|
| Simple text | Inline text input | MAWB, reference numbers, etc. |
| Address/Location | Dedicated modal | Search HTC addresses + create new option |
| DateTime Range | Date + start/end time | Same day assumed |
| Dims | Dedicated form | Variable rows: qty, L, W, H, weight |

### Simple Text Fields
- Inline text input within field picker modal
- Submit adds value immediately

### Address Modal
- Search existing HTC database addresses
- Display results with company, street, city, state, zip
- Select existing OR create new
- "Create New" opens address creation form:
  - Company name
  - Street address
  - City, State, Zip
  - Country (if applicable)
- On submit: creates address in HTC, returns ID for field value

### DateTime Range Input
- Single date picker
- Start time input
- End time input
- Same day assumed (no multi-day ranges)

### Dims Form
- Variable number of rows (add/remove buttons)
- Each row contains:
  - Quantity (integer)
  - Length (number)
  - Width (number)
  - Height (number)
  - Weight (number)
- At least one row required
- "Add Row" / "Remove Row" controls

## User Flow

1. User views pending action detail
2. Clicks "Add Field" button
3. Field picker opens showing ALL order fields
4. User selects a field
5. Appropriate input UI appears based on field type:
   - Simple text: inline input in same modal
   - Address: address modal opens
   - DateTime: datetime form appears
   - Dims: dims form opens
6. User enters value and submits
7. Backend creates field with `output_execution_id = NULL`, auto-selected
8. UI updates to show new field value
9. Status recalculates (may transition from incomplete → ready)

## Restrictions

- `customer_id` and `hawb` are NOT order fields - determined by templates
- All fields in `ORDER_FIELDS` can be manually set
- No visual distinction for manual vs extracted values (source visible in contributions panel)

## Implementation

### Backend

#### 1. Implement `set_user_value()` Method

**File:** `server/src/features/order_management/service.py`

Currently a stub raising `NotImplementedError`. Implement to:
```python
def set_user_value(
    self,
    pending_action_id: int,
    field_name: str,
    value: Any,
) -> PendingActionField:
    """
    Add a user-provided field value to a pending action.

    Behaves identically to automated extraction:
    - Creates new field with output_execution_id = NULL
    - If field exists: clears all selections, new value selected
    - If field doesn't exist: creates with is_selected = TRUE
    - Recalculates action status
    """
    # Validate field_name exists in ORDER_FIELDS
    # Validate value format based on field type
    # Create pending_action_field record
    # Handle conflict logic (same as _add_fields_to_action)
    # Recalculate status
    # Return created field
```

#### 2. Add API Endpoint

**File:** `server/src/api/routers/pending_actions.py`

```python
@router.post("/{pending_action_id}/fields")
def add_field_value(
    pending_action_id: int,
    request: AddFieldValueRequest,
) -> PendingActionFieldResponse:
    """Add a user-provided field value."""
```

#### 3. Add Request/Response Schemas

**File:** `server/src/api/schemas/pending_actions.py`

```python
class AddFieldValueRequest(BaseModel):
    field_name: str
    value: Any  # Type depends on field

class PendingActionFieldResponse(BaseModel):
    id: int
    field_name: str
    value: Any
    is_selected: bool
    output_execution_id: int | None  # NULL for user-provided
```

#### 4. Validation by Field Type

Implement validation based on `ORDER_FIELDS` definitions:
- Text fields: string, max length
- Address fields: valid address structure or address ID
- DateTime fields: valid date + start/end times
- Dims fields: array of rows with qty, L, W, H, weight

### Frontend

#### 1. Add Field Button

**Location:** Pending action detail view

- "Add Field" button in header or field section
- Opens field picker modal

#### 2. Field Picker Modal

**Component:** `AddFieldModal.tsx`

- List all fields from `ORDER_FIELDS`
- Search/filter capability
- Group by category (identification, pickup, delivery, cargo, etc.)
- On field select: show appropriate input UI

#### 3. Field Type Input Components

Design as pluggable components:

```typescript
interface FieldInputProps {
  fieldName: string;
  fieldDefinition: OrderFieldDefinition;
  onSubmit: (value: any) => void;
  onCancel: () => void;
}

// Implementations
TextFieldInput: React.FC<FieldInputProps>
AddressFieldInput: React.FC<FieldInputProps>  // Opens address modal
DateTimeFieldInput: React.FC<FieldInputProps>
DimsFieldInput: React.FC<FieldInputProps>
```

#### 4. Address Modal

**Component:** `AddressSelectionModal.tsx`

- Search input for HTC address lookup
- Results list with address details
- "Create New Address" button
- Address creation form (inline or sub-modal):
  - Company name
  - Street
  - City, State, Zip
- On select/create: returns address data for field value

#### 5. Dims Form

**Component:** `DimsEntryForm.tsx`

- Dynamic row list
- Each row: qty, length, width, height, weight inputs
- "Add Row" button
- "Remove" button per row (except if only one row)
- Validation: at least one row, all fields filled

#### 6. API Hook

**File:** `client/src/renderer/features/order-management/api/hooks.ts`

```typescript
useAddFieldValue(): UseMutationResult<
  PendingActionFieldResponse,
  Error,
  { pendingActionId: number; fieldName: string; value: any }
>
```

### Extensibility Notes

- Field type → input component mapping should be configurable
- New field types only require:
  1. Add type to `ORDER_FIELDS` definition
  2. Create input component implementing `FieldInputProps`
  3. Register in field type → component mapping
- Modal architecture should support nesting (address modal over field picker)

## Checklist

### Backend

- [ ] Implement `set_user_value()` in `OrderManagementService`
- [ ] Add field type validation logic
- [ ] Add `POST /pending-actions/{id}/fields` endpoint
- [ ] Add request/response schemas
- [ ] Handle address creation in HTC (for new addresses)
- [ ] Test conflict behavior with existing values
- [ ] Test status recalculation after adding field

### Frontend - Core

- [ ] Add "Add Field" button to pending action detail view
- [ ] Create `AddFieldModal` component (field picker)
- [ ] Implement field type → input component mapping
- [ ] Create `useAddFieldValue` API hook
- [ ] Wire up submit flow to invalidate/refresh pending action data

### Frontend - Input Components

- [ ] Create `TextFieldInput` component
- [ ] Create `DateTimeFieldInput` component (date + start/end time)
- [ ] Create `AddressSelectionModal` component
  - [ ] HTC address search
  - [ ] Results display
  - [ ] Create new address form
- [ ] Create `DimsEntryForm` component
  - [ ] Dynamic row add/remove
  - [ ] Row inputs: qty, length, width, height, weight
  - [ ] Validation

### Testing

- [ ] Test adding field to action with no existing values
- [ ] Test adding field that already has values (conflict behavior)
- [ ] Test each field type input
- [ ] Test address search and creation
- [ ] Test dims form with multiple rows
- [ ] Test status transitions (incomplete → ready)
- [ ] Test with both create and update action types
