# Feature: Field Processing Error Handling (Decoupled Architecture)

## Overview

Decouple field transformation errors from ETO sub-run success. Each output channel field should be processed independently, with failures recorded per-field rather than failing the entire sub-run or pending action.

## Current Architecture (Problem)

```
ETO Sub-Run
    ↓
Pipeline Execution → output_channel_values (raw data)
    ↓
_process_sub_run_output_execution()
    ↓
    ├─ Create EtoSubRunOutputExecution (stores raw data) ✓
    │
    └─ Call OrderManagementService.process_output_execution()
        ↓
        ├─ _transform_output_to_fields()
        ├─ _resolve_address_ids()  ← Address parsing here
        └─ If ANY exception → propagates up → SUB-RUN MARKED FAILED ✗
```

**Problem:** One field failing (e.g., address parsing) causes entire sub-run to fail, losing all other successfully extracted data.

## Desired Architecture

```
ETO Sub-Run
    ↓
Pipeline Execution → output_channel_values (raw data)
    ↓
_process_sub_run_output_execution()
    ↓
    ├─ Create EtoSubRunOutputExecution (stores raw data)
    ├─ Mark sub-run as SUCCESS ← Sub-run done here
    │
    └─ Call OrderManagementService.process_output_execution()
        ↓
        For EACH field independently:
        ├─ Try transform field
        │   ├─ Success → store with status="success"
        │   └─ Failure → try fallback (e.g., LLM for addresses)
        │       ├─ Fallback success → store with status="success"
        │       └─ Fallback failure → store with status="failed", error message
        │
        └─ Method NEVER raises - all errors handled internally
```

## Database Schema Changes

**File:** `server/src/shared/database/models.py`

Add to `PendingActionFieldModel`:

```python
class PendingActionFieldModel(BaseModel):
    # ... existing fields ...

    # New fields for processing status tracking
    processing_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="success"
    )  # "success" | "failed"

    processing_error: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )  # Error message if failed

    raw_value: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )  # Original value before transformation (for retry/manual fix)
```

**Types file:** `server/src/shared/types/pending_actions.py`

```python
class PendingActionField(BaseModel):
    # ... existing fields ...
    processing_status: Literal["success", "failed"] = "success"
    processing_error: str | None = None
    raw_value: str | None = None
```

## Backend Service Changes

### 1. ETO Service - Decouple Error Handling

**File:** `server/src/features/eto_runs/service.py`

**Method:** `_process_sub_run_output_execution()`

```python
def _process_sub_run_output_execution(
    self,
    sub_run_id: int,
    output_channel_values: dict[str, Any],
    customer_id: int,
) -> None:
    """Process output execution. Sub-run success is independent of order management."""

    # Extract HAWBs and create output execution records
    hawbs = self._extract_hawbs(output_channel_values)

    for hawb in hawbs:
        # Create EtoSubRunOutputExecution with raw data
        output_execution = self._create_output_execution(
            sub_run_id=sub_run_id,
            customer_id=customer_id,
            hawb=hawb,
            output_channel_data=output_channel_values,
        )

        # Call order management - errors handled internally, never raises
        result = self.order_management_service.process_output_execution(
            output_execution_id=output_execution.id
        )

        # Log result but don't fail sub-run based on it
        if result.has_failures:
            logger.warning(
                f"Some fields failed processing for output execution {output_execution.id}: "
                f"{result.failed_fields}"
            )

    # Sub-run is successful regardless of field processing outcomes
```

### 2. Order Management Service - Per-Field Error Isolation

**File:** `server/src/features/order_management/service.py`

**Method:** `process_output_execution()` - Refactor to never raise

```python
@dataclass
class FieldProcessingResult:
    field_name: str
    status: Literal["success", "failed"]
    error: str | None = None

@dataclass
class OutputProcessingResult:
    fields: list[FieldProcessingResult]

    @property
    def has_failures(self) -> bool:
        return any(f.status == "failed" for f in self.fields)

    @property
    def failed_fields(self) -> list[str]:
        return [f.field_name for f in self.fields if f.status == "failed"]


def process_output_execution(self, output_execution_id: int) -> OutputProcessingResult:
    """
    Process output execution into pending action fields.

    NEVER RAISES - all errors handled internally and recorded per-field.
    """
    results = []

    output_execution = self._get_output_execution(output_execution_id)
    output_data = output_execution.output_channel_data

    # Get or create pending action
    action = self._get_or_create_pending_action(
        customer_id=output_execution.customer_id,
        hawb=output_execution.hawb,
    )

    # Process each field independently
    for field_name, raw_value in output_data.items():
        result = self._process_single_field(
            action_id=action.id,
            output_execution_id=output_execution_id,
            field_name=field_name,
            raw_value=raw_value,
        )
        results.append(result)

    # Update action status based on field results
    self._update_action_status(action.id)

    return OutputProcessingResult(fields=results)


def _process_single_field(
    self,
    action_id: int,
    output_execution_id: int,
    field_name: str,
    raw_value: Any,
) -> FieldProcessingResult:
    """Process a single field with cascading fallback. Never raises."""

    try:
        # Attempt primary transformation
        transformed_value = self._transform_field(field_name, raw_value)

        # For location fields, resolve address ID
        if field_name in ("pickup_location", "delivery_location"):
            transformed_value = self._resolve_address_with_fallback(
                field_name, raw_value, transformed_value
            )

        # Store successful field
        self._store_field(
            action_id=action_id,
            output_execution_id=output_execution_id,
            field_name=field_name,
            value=transformed_value,
            raw_value=json.dumps(raw_value),
            processing_status="success",
        )

        return FieldProcessingResult(field_name=field_name, status="success")

    except Exception as e:
        logger.warning(f"Field {field_name} processing failed: {e}")

        # Store failed field with error info
        self._store_field(
            action_id=action_id,
            output_execution_id=output_execution_id,
            field_name=field_name,
            value=None,  # No transformed value
            raw_value=json.dumps(raw_value),
            processing_status="failed",
            processing_error=str(e),
        )

        return FieldProcessingResult(
            field_name=field_name,
            status="failed",
            error=str(e)
        )


def _resolve_address_with_fallback(
    self,
    field_name: str,
    raw_value: Any,
    initial_transform: Any,
) -> Any:
    """Resolve address with cascading fallback: usaddress → LLM."""

    # Try usaddress parsing (current approach)
    try:
        address_id = self._resolve_address_id(initial_transform)
        if address_id is not None:
            initial_transform["address_id"] = address_id
            return initial_transform
    except Exception as e:
        logger.warning(f"usaddress parsing failed for {field_name}: {e}")

    # Fallback: LLM-based address parsing
    try:
        llm_result = self._resolve_address_via_llm(raw_value)
        if llm_result:
            return llm_result
    except Exception as e:
        logger.warning(f"LLM address fallback failed for {field_name}: {e}")

    # All fallbacks failed - raise to be caught by caller
    raise ValueError(f"Could not resolve address for {field_name}")
```

### 3. LLM Address Fallback (New)

**File:** `server/src/features/order_management/service.py` (or separate utils file)

```python
def _resolve_address_via_llm(self, raw_address_data: Any) -> dict | None:
    """
    Use LLM to parse address when usaddress fails.

    Returns LocationValue-compatible dict or None if failed.
    """
    from openai import OpenAI

    address_string = self._extract_address_string(raw_address_data)
    if not address_string:
        return None

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": """Parse this address into components. Return JSON:
{
    "company_name": "string or null",
    "address": "street address",
    "city": "city name",
    "state": "2-letter state code",
    "zip_code": "ZIP code",
    "country": "country, default USA"
}"""
            },
            {"role": "user", "content": address_string}
        ],
        temperature=0.0,
        response_format={"type": "json_object"}
    )

    parsed = json.loads(response.choices[0].message.content)

    # Convert to LocationValue format
    return {
        "company_name": parsed.get("company_name"),
        "address": parsed.get("address"),
        "city": parsed.get("city"),
        "state": parsed.get("state"),
        "zip_code": parsed.get("zip_code"),
        "country": parsed.get("country", "USA"),
        "address_id": None,  # Will need to look up or create
    }
```

## API Changes

### Update PendingActionField Response Schema

**File:** `server/src/api/schemas/order_management.py`

```python
class PendingActionFieldResponse(BaseModel):
    id: int
    field_name: str
    value: Any | None
    is_selected: bool
    is_approved_for_update: bool
    # New fields
    processing_status: Literal["success", "failed"]
    processing_error: str | None
    raw_value: str | None  # For display/retry purposes
```

## Frontend Changes

### 1. Display Field Processing Errors

In pending action detail view, show which fields failed processing:

```tsx
{field.processing_status === "failed" && (
    <FieldErrorBadge>
        <WarningIcon />
        <span>Processing failed: {field.processing_error}</span>
        <span className="raw-value">Raw value: {field.raw_value}</span>
    </FieldErrorBadge>
)}
```

### 2. Allow Retry/Manual Fix

For failed fields, user options:
- **Retry**: Re-attempt transformation (maybe with different method)
- **Manual entry**: User provides the correct value (ties into manual field entry feature)

### 3. Conflict System Integration

Consider how failed fields interact with existing conflict resolution:
- Failed field = no value to compare, cannot conflict
- If user manually provides value, that becomes the selected value
- Failed fields should be clearly distinguished from conflicting fields

## Checklist

### Database
- [ ] Add `processing_status` column to `pending_action_fields`
- [ ] Add `processing_error` column to `pending_action_fields`
- [ ] Add `raw_value` column to `pending_action_fields`
- [ ] Create migration script
- [ ] Update types in `shared/types/pending_actions.py`

### Backend - ETO Service
- [ ] Update `_process_sub_run_output_execution()` to not fail sub-run on order management errors
- [ ] Mark sub-run successful after storing raw output data

### Backend - Order Management Service
- [ ] Create `FieldProcessingResult` and `OutputProcessingResult` types
- [ ] Refactor `process_output_execution()` to never raise
- [ ] Implement `_process_single_field()` with per-field error handling
- [ ] Implement `_resolve_address_with_fallback()` cascading logic
- [ ] Implement `_resolve_address_via_llm()` fallback

### API
- [ ] Update `PendingActionFieldResponse` schema with new fields
- [ ] Ensure API returns processing status and error info

### Frontend
- [ ] Display field processing status (success/failed badge)
- [ ] Show processing error message for failed fields
- [ ] Show raw value for failed fields
- [ ] Consider retry/manual fix UI (may tie into separate manual entry feature)
- [ ] Update conflict resolution UI to handle failed fields

### Testing
- [ ] Test field processing with valid data
- [ ] Test field processing with invalid address (usaddress fails)
- [ ] Test LLM fallback when usaddress fails
- [ ] Test multiple fields where some succeed and some fail
- [ ] Test sub-run succeeds even when field processing fails
- [ ] Test UI displays failed fields correctly
