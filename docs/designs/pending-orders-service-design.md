# PendingOrdersService Design

## Overview

The `PendingOrdersService` is responsible for processing output channel data from completed pipeline executions and routing it to either:
1. **Pending Orders** - For HAWBs not yet in HTC (aggregation until complete)
2. **Pending Updates** - For HAWBs already in HTC (queue for user approval)

## Service Interface

```python
class PendingOrdersService:
    """
    Service for processing pipeline output channel data into pending orders.

    Main entry point takes output channel values dict from pipeline execution
    and routes data appropriately based on HAWB existence in HTC.
    """

    def __init__(
        self,
        connection_manager: DatabaseConnectionManager,
        data_database_manager: DataDatabaseManager,  # For HTC Access DB
        database_name: str = "htc_300_db"
    ) -> None:
        """Initialize with database connections."""
        pass

    # ==================== Primary Entry Points ====================

    def process_output_channels(
        self,
        output_channel_values: Dict[str, Any],
        sub_run_id: int,
        eto_run_id: int,
        customer_id: int,
        pdf_filename: str,
        email_subject: Optional[str] = None,
    ) -> ProcessingResult:
        """
        Process output channel data for a single HAWB.

        This is the main entry point called after pipeline execution completes.

        Args:
            output_channel_values: Dict from pipeline execution containing field values.
                                   MUST contain 'hawb' key.
            sub_run_id: ID of the sub-run that produced this data
            eto_run_id: ID of the parent ETO run (for email reply, attachments)
            customer_id: Customer ID from the template
            pdf_filename: Original PDF filename for audit trail
            email_subject: Email subject if source was email (for audit trail)

        Returns:
            ProcessingResult with action taken and any created/updated records

        Raises:
            ValueError: If 'hawb' key is missing from output_channel_values
        """
        pass

    def process_output_channels_batch(
        self,
        output_channel_values: Dict[str, Any],
        sub_run_id: int,
        eto_run_id: int,
        customer_id: int,
        pdf_filename: str,
        email_subject: Optional[str] = None,
    ) -> List[ProcessingResult]:
        """
        Process output channel data that may contain multiple HAWBs.

        Handles the case where 'hawb' or 'hawbs' contains a list of HAWB values.
        Each HAWB is processed independently with the same field data.

        Args:
            output_channel_values: Dict that may contain:
                - 'hawb': str - Single HAWB
                - 'hawb': List[str] - Multiple HAWBs
                - 'hawbs': List[str] - Alternative key for multiple HAWBs
            sub_run_id: ID of the sub-run that produced this data
            eto_run_id: ID of the parent ETO run
            customer_id: Customer ID from the template
            pdf_filename: Original PDF filename
            email_subject: Email subject if from email

        Returns:
            List of ProcessingResult, one per HAWB processed

        Raises:
            ValueError: If neither 'hawb' nor 'hawbs' key is present
        """
        pass
```

## Data Flow

```
Pipeline Execution Completes
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  process_output_channels() or process_output_channels_batch()   │
│  - Extract HAWB(s) from output_channel_values                   │
│  - For batch: loop over each HAWB                               │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 1: Check if HAWB exists in HTC Access Database            │
│  - Query HTC orders table by HAWB                               │
└────────────────────────┬────────────────────────────────────────┘
                         │
         ┌───────────────┴───────────────┐
         │                               │
         ▼                               ▼
    HAWB IN HTC                    HAWB NOT IN HTC
         │                               │
         ▼                               ▼
┌─────────────────────┐    ┌─────────────────────────────────────┐
│  Step 2a:           │    │  Step 2b: Check pending_orders      │
│  Create pending_    │    │                                     │
│  updates records    │    │  ┌─────────────┴─────────────┐      │
│  (one per field)    │    │  │                           │      │
│                     │    │  ▼                           ▼      │
│  → Queue for user   │    │ EXISTS                  NOT EXISTS  │
│    approval         │    │  │                           │      │
└─────────────────────┘    │  ▼                           ▼      │
                           │ Step 3a:              Step 3b:      │
                           │ Add to history        Create new    │
                           │ for each field        pending_order │
                           │                       + history     │
                           └─────────────┬─────────────────┬─────┘
                                         │                 │
                                         └────────┬────────┘
                                                  │
                                                  ▼
                           ┌─────────────────────────────────────┐
                           │  Step 4: Check if order is ready    │
                           │  - All required fields non-null?    │
                           │  - No unresolved conflicts?         │
                           │                                     │
                           │  If ready → auto-create in HTC      │
                           │  If not ready → stay as pending     │
                           └─────────────────────────────────────┘
```

## Result Types

```python
@dataclass
class ProcessingResult:
    """Result of processing a single HAWB's output channel data."""

    hawb: str
    action: Literal['pending_order_created', 'pending_order_updated', 'pending_update_created', 'order_created']

    # Set when action involves pending_order
    pending_order_id: Optional[int] = None

    # Set when action='pending_update_created'
    pending_update_ids: Optional[List[int]] = None

    # Set when action='order_created'
    htc_order_number: Optional[float] = None

    # Fields that were added to history
    fields_contributed: List[str] = field(default_factory=list)

    # Any conflicts introduced by this contribution
    conflicts_introduced: List[str] = field(default_factory=list)
```

## Internal Methods

```python
class PendingOrdersService:
    # ... (public methods above)

    # ==================== HTC Access Database ====================

    def _lookup_hawb_in_htc(self, hawb: str) -> Optional[HtcOrderInfo]:
        """
        Check if HAWB exists in HTC Access database.

        Returns:
            HtcOrderInfo with order_number if found, None if not found
        """
        pass

    # ==================== Pending Orders ====================

    def _get_or_create_pending_order(
        self,
        hawb: str,
        customer_id: int
    ) -> Tuple[PendingOrder, bool]:
        """
        Get existing pending order or create new one.

        Returns:
            Tuple of (pending_order, was_created)
        """
        pass

    def _add_field_contributions(
        self,
        pending_order_id: int,
        field_data: Dict[str, Any],
        sub_run_id: int,
        pdf_filename: str,
        email_subject: Optional[str]
    ) -> Tuple[List[str], List[str]]:
        """
        Add field contributions to pending_order_history.

        For each field in field_data:
        1. Add history record
        2. Recalculate field state (set/conflict)
        3. Update pending_order field value accordingly

        Returns:
            Tuple of (fields_contributed, conflicts_introduced)
        """
        pass

    def _get_field_state(
        self,
        pending_order_id: int,
        field_name: str
    ) -> FieldState:
        """
        Compute field state from history records.

        Returns one of:
        - FieldState.EMPTY - No values received
        - FieldState.SET - Single value or all agree
        - FieldState.CONFIRMED - User explicitly selected
        - FieldState.CONFLICT - Multiple different values
        """
        pass

    def _check_and_create_order(self, pending_order_id: int) -> Optional[float]:
        """
        Check if pending order is ready and create in HTC if so.

        Conditions for ready:
        1. All required fields are non-null
        2. No fields in conflict state (all resolved)

        Returns:
            HTC order number if created, None if not ready
        """
        pass

    # ==================== Pending Updates ====================

    def _create_pending_updates(
        self,
        hawb: str,
        htc_order_number: float,
        field_data: Dict[str, Any],
        sub_run_id: int,
        pdf_filename: str,
        email_subject: Optional[str]
    ) -> List[int]:
        """
        Create pending_update records for each field.

        These queue proposed changes for user approval.

        Returns:
            List of created pending_update IDs
        """
        pass

    # ==================== Order Creation ====================

    def _create_order_in_htc(self, pending_order: PendingOrder) -> float:
        """
        Create order in HTC Access database.

        Steps:
        1. Reserve order number (collision-free via OIW table)
        2. Insert order record
        3. Finalize order number (update LON, remove OIW)
        4. Update pending_order status and htc_order_number

        Returns:
            The created HTC order number
        """
        pass
```

## Required Fields Configuration

```python
# Fields that must be non-null AND not in conflict for auto-creation
REQUIRED_FIELDS_FOR_CREATION = [
    'pickup_address',
    'pickup_time_start',
    'pickup_time_end',
    'delivery_address',
    'delivery_time_start',
    'delivery_time_end',
]

# Note: 'hawb' is always required but handled separately as the key
```

## Integration with EtoRunsService

The `EtoRunsService._process_sub_run_output_execution()` method will be updated to call this service:

```python
def _process_sub_run_output_execution(
    self,
    sub_run_id: int,
    output_channel_values: Dict[str, Any],  # Changed from output_module_id/inputs
) -> None:
    """
    Execute output processing for a sub-run's output channels.
    """
    # Get sub-run and parent run info
    sub_run = self.sub_run_repo.get_by_id(sub_run_id)
    parent_run = self.eto_run_repo.get_by_id(sub_run.eto_run_id)

    # Get template's customer_id
    template_version = self.pdf_template_service.get_version_by_id(sub_run.template_version_id)
    template = self.pdf_template_service.get_template(template_version.template_id)
    customer_id = template.customer_id

    # Get PDF filename and email subject for audit trail
    pdf_file = self.pdf_files_service.get_pdf_file(parent_run.pdf_file_id)
    email_subject = None
    if parent_run.source_email_id:
        email = self.email_repo.get_by_id(parent_run.source_email_id)
        email_subject = email.subject if email else None

    # Process through PendingOrdersService
    results = self.pending_orders_service.process_output_channels_batch(
        output_channel_values=output_channel_values,
        sub_run_id=sub_run_id,
        eto_run_id=parent_run.id,
        customer_id=customer_id,
        pdf_filename=pdf_file.original_filename,
        email_subject=email_subject,
    )

    # Record results in output_execution table
    # ...
```

## Database Tables Required

See `pending-orders-system-v2.md` for full schema. Summary:

1. **pending_orders** - Aggregated order state by HAWB
2. **pending_order_history** - All field contributions from sub-runs
3. **pending_updates** - Proposed changes for existing HTC orders

## Open Questions

1. **Customer ID source**: Should customer_id come from:
   - The template (current design)
   - The output channel values (if customer lookup is part of pipeline)
   - Both with conflict resolution?

2. **HAWB list format**: Should we support:
   - `hawb: "ABC,DEF,GHI"` (comma-separated string)
   - `hawb: ["ABC", "DEF", "GHI"]` (list)
   - `hawbs: ["ABC", "DEF", "GHI"]` (separate key)
   - All of the above?

3. **Email reply functionality**: The service needs access to `eto_run_id` for:
   - Sending email reply to customer
   - Adding attachments to attachments database
   - Is this in scope for the initial implementation?

4. **Transaction boundaries**: Should the entire batch be atomic, or each HAWB processed independently?
