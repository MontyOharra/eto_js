# PipelineResultService Design Document

## Overview

This document captures the complete design for the **PipelineResultService** - the service responsible for executing output modules with full ETO context after pipeline execution completes.

## Background & Context

### The Problem
After the recent refactoring that removed action modules and introduced output modules, we separated concerns:
- **Pipeline execution** = Pure data transformation (DAG execution, no side effects)
- **Output execution** = Side effects with full ETO context (separate stage)

Pipeline execution now returns:
- `output_module_id`: The ID of the output module in the pipeline
- `output_module_inputs`: The collected input data for that module

We need a service to take this data and actually execute the output module with full ETO context (customer data, email source, database connections, etc.).

### Naming Decision
After considering many options (OutputFulfillmentService, DispatchService, FinalizationService, etc.), we settled on:

**`PipelineResultService`**

This name clearly indicates it handles the results from pipeline execution without using the word "output" or "executor".

---

## Requirements

Output modules need access to two main categories of functionality:

### 1. Email Confirmation to Sender
- **Purpose**: Send confirmation email to original sender acknowledging receipt
- **Needs**:
  - Email integration (IMAP/SMTP server configuration)
  - ETO run data to get source email address
  - Email templates/formatting
- **Context Chain**: Sub run → ETO run → original email source

### 2. Order Creation in Access Database
- **Purpose**: Create orders in customer's Access database
- **Needs**:
  - Access database connection (via ConnectionManager)
  - Order number generation
  - HAWB existence check (prevent duplicates)
  - Order data validation and insertion
- **Context Chain**: Sub run → ETO run → Customer → Access DB path

---

## Design Options Considered

### Option 1: Methods in ABC (Rejected)
```python
class OutputModule(ABC):
    def generate_order_number(self) -> str:
        # Complex logic here
        pass

    def send_email(self, ...):
        # Complex logic here
        pass
```

**Pros:**
- Simple inheritance model
- Modules just call inherited methods

**Cons:**
- ABC becomes bloated with business logic
- Tight coupling
- Violates single responsibility principle
- Hard to test in isolation
- **REJECTED** - Bad practice to put complex logic in ABC

---

### Option 2: Service Locator Pattern (Rejected)
```python
def run(self, inputs, cfg, services: ServiceContainer):
    order_num = services.get_order_service().generate_number()
    # ...
```

**Pros:**
- Modules can access anything they need
- Simple to implement

**Cons:**
- **Hidden dependencies** - can't tell what a module needs
- **Tight coupling** to entire container
- **Hard to test** - need to mock entire container
- **Service locator is an anti-pattern**
- **REJECTED** - Poor design practice

---

### Option 3: Typed Context Object + Helper Classes (CHOSEN)
```python
@dataclass
class OutputExecutionContext:
    sub_run: EtoSubRun
    eto_run: EtoRun
    order_helpers: OrderHelpers
    email_helpers: EmailHelpers
    # ...

class OutputModule(ABC):
    def run(self, inputs, cfg, context: OutputExecutionContext):
        pass
```

**Pros:**
- **Typed** - IDE autocomplete, type checking
- **Explicit** - can see exactly what's available
- **Testable** - mock context in tests, test helpers separately
- **Single responsibility** - helpers handle specific concerns
- **Extensible** - easy to add new helpers

**Cons:**
- Context object will grow over time (manageable)
- Modules coupled to context structure (acceptable trade-off)

**VERDICT: CHOSEN** - Best balance of explicitness, testability, and maintainability

---

## Detailed Architecture Design

### 1. Helper Classes

Helper classes encapsulate reusable business logic and provide stateless utilities.

#### OrderHelpers
```python
class OrderHelpers:
    """
    Utilities for order operations in Access database.
    Handles order number generation, HAWB checks, and order creation.
    """

    def __init__(self, connection_manager: ConnectionManager):
        self.conn_manager = connection_manager

    def generate_next_order_number(self, db_path: str) -> str:
        """
        Generate next available order number from Access DB.

        Args:
            db_path: Path to customer's Access database

        Returns:
            Next order number (format varies by customer)
        """
        with self.conn_manager.get_access_connection(db_path) as conn:
            cursor = conn.cursor()
            # Query for max order number, increment according to format
            # Handle different order number formats per customer
            # Example: "ORD-2024-00001" -> "ORD-2024-00002"
            ...
            return next_order_num

    def check_order_exists_by_hawb(self, db_path: str, hawb: str) -> bool:
        """
        Check if order with given HAWB already exists.
        Prevents duplicate order creation.

        Args:
            db_path: Path to customer's Access database
            hawb: House Air Waybill number

        Returns:
            True if order exists, False otherwise
        """
        with self.conn_manager.get_access_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM orders WHERE hawb = ?", (hawb,))
            count = cursor.fetchone()[0]
            return count > 0

    def create_order(
        self,
        db_path: str,
        order_data: Dict[str, Any]
    ) -> str:
        """
        Create order in Access DB with all validations.

        Args:
            db_path: Path to customer's Access database
            order_data: Order fields (hawb, shipper, consignee, etc.)

        Returns:
            Generated order number

        Raises:
            ValidationError: If order data is invalid
            DuplicateOrderError: If HAWB already exists
        """
        # Validate order data
        self._validate_order_data(order_data)

        # Check for duplicates
        if self.check_order_exists_by_hawb(db_path, order_data['hawb']):
            raise DuplicateOrderError(f"Order with HAWB {order_data['hawb']} already exists")

        # Generate order number
        order_num = self.generate_next_order_number(db_path)

        # Insert order
        with self.conn_manager.get_access_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO orders (order_number, hawb, shipper, consignee, ...)
                VALUES (?, ?, ?, ?, ...)
            """, (order_num, order_data['hawb'], ...))
            conn.commit()

        return order_num

    def _validate_order_data(self, order_data: Dict[str, Any]) -> None:
        """Validate order data before insertion"""
        required_fields = ['hawb', 'shipper', 'consignee']
        for field in required_fields:
            if field not in order_data or not order_data[field]:
                raise ValidationError(f"Missing required field: {field}")
```

#### EmailHelpers
```python
class EmailHelpers:
    """
    Utilities for sending emails via configured integrations.
    Handles SMTP connections and email formatting.
    """

    def __init__(self, email_config_repo: EmailConfigRepository):
        self.email_config_repo = email_config_repo

    def send_confirmation_email(
        self,
        to_address: str,
        subject: str,
        body: str,
        integration_id: int,
        attachments: Optional[List[str]] = None
    ) -> None:
        """
        Send email via configured SMTP integration.

        Args:
            to_address: Recipient email address
            subject: Email subject line
            body: Email body (plain text or HTML)
            integration_id: ID of email integration config
            attachments: Optional list of file paths to attach

        Raises:
            EmailConfigError: If integration config not found
            EmailSendError: If email sending fails
        """
        # Load email configuration
        config = self.email_config_repo.get_by_id(integration_id)
        if not config:
            raise EmailConfigError(f"Email integration {integration_id} not found")

        # Connect to SMTP server
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        msg = MIMEMultipart()
        msg['From'] = config.from_address
        msg['To'] = to_address
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        # Add attachments if provided
        if attachments:
            for filepath in attachments:
                # Attach file...
                pass

        try:
            with smtplib.SMTP(config.smtp_host, config.smtp_port) as server:
                if config.use_tls:
                    server.starttls()
                if config.smtp_username:
                    server.login(config.smtp_username, config.smtp_password)
                server.send_message(msg)
        except Exception as e:
            raise EmailSendError(f"Failed to send email: {str(e)}")

    def send_order_confirmation(
        self,
        to_address: str,
        order_number: str,
        hawb: str,
        integration_id: int
    ) -> None:
        """
        Send order confirmation email with standardized template.

        Convenience method for common use case.
        """
        subject = f"Order {order_number} Received"
        body = f"""
Dear Customer,

We have received your order for HAWB {hawb}.
Your order number is: {order_number}

Thank you for your business.

Best regards,
Automated Order Processing System
        """.strip()

        self.send_confirmation_email(to_address, subject, body, integration_id)
```

---

### 2. Context Object

The context object contains everything an output module needs during execution.

```python
from dataclasses import dataclass
from typing import Optional
from shared.types.eto_runs import EtoRun
from shared.types.eto_sub_runs import EtoSubRun

@dataclass
class OutputExecutionContext:
    """
    Context provided to output modules during execution.

    Contains all services, helpers, and ETO-specific data needed
    for output module execution.

    Attributes:
        sub_run: Current ETO sub-run being processed
        eto_run: Parent ETO run (has email source, customer info)
        connection_manager: Database connection manager
        order_helpers: Utilities for order operations
        email_helpers: Utilities for email operations
        customer_repo: Repository for customer lookups
        address_repo: Repository for address lookups
    """

    # ETO domain data
    sub_run: EtoSubRun
    eto_run: EtoRun

    # Database access
    connection_manager: ConnectionManager

    # Helper services
    order_helpers: OrderHelpers
    email_helpers: EmailHelpers

    # Repositories (for lookups during execution)
    customer_repo: CustomerRepository
    address_repo: AddressRepository

    # Could add more as needed:
    # carrier_repo: CarrierRepository
    # template_repo: TemplateRepository
    # etc.
```

---

### 3. Output Module ABC

The abstract base class remains minimal - just the interface definition.

```python
from abc import ABC, abstractmethod
from typing import Dict, Any
from pydantic import BaseModel

class OutputModule(ABC):
    """
    Base class for output modules (terminal pipeline nodes).

    Output modules execute side effects with full ETO context.
    They are the final stage after pipeline execution completes.

    Attributes:
        id: Unique module identifier
        version: Module version (semver)
        title: Human-readable title
        description: Module description
        kind: Always ModuleKind.OUTPUT
        ConfigModel: Pydantic model for module configuration
    """

    id: str
    version: str
    title: str
    description: str
    kind = ModuleKind.OUTPUT
    ConfigModel: type[BaseModel]

    @classmethod
    @abstractmethod
    def meta(cls) -> ModuleMeta:
        """Define I/O shape (inputs only, no outputs for terminal nodes)"""
        pass

    @abstractmethod
    def run(
        self,
        inputs: Dict[str, Any],
        cfg: BaseModel,
        context: OutputExecutionContext
    ) -> Dict[str, Any]:
        """
        Execute output module with full ETO context.

        Args:
            inputs: Collected inputs from pipeline execution
                   Format: {node_id: value, ...}
            cfg: Module configuration (instance of ConfigModel)
            context: Full execution context with services/helpers

        Returns:
            Result dict containing execution outcome.
            Structure varies by module but typically includes:
            - status: "success" | "failure" | "duplicate" | etc.
            - Additional fields specific to the module

        Raises:
            Various exceptions depending on module implementation
        """
        pass
```

---

### 4. Example Output Module Implementation

```python
from pydantic import BaseModel
from shared.types.modules import OutputModule, ModuleMeta, IOShape, IOSideShape, NodeGroup, NodeTypeRule
from features.modules.utils.decorators import register

class BasicOrderOutputConfig(BaseModel):
    """Configuration for basic order output (currently empty)"""
    pass

@register
class BasicOrderOutput(OutputModule):
    """
    Creates a basic freight forwarding order in customer's Access database.
    Sends confirmation email to sender.

    Required inputs:
    - hawb: House Air Waybill number
    - shipper: Shipper name/address
    - consignee: Consignee name/address
    - pieces: Number of pieces
    - weight: Total weight
    """

    id = "basic_order_output"
    version = "1.0.0"
    title = "Basic Order Output"
    description = "Create basic order and send confirmation email"
    ConfigModel = BasicOrderOutputConfig

    @classmethod
    def meta(cls) -> ModuleMeta:
        """Define required inputs"""
        return ModuleMeta(
            io_shape=IOShape(
                inputs=IOSideShape(
                    nodes=[
                        NodeGroup(
                            typing=NodeTypeRule(allowed_types=["str"]),
                            label="hawb",
                            min_count=1,
                            max_count=1
                        ),
                        NodeGroup(
                            typing=NodeTypeRule(allowed_types=["str"]),
                            label="shipper",
                            min_count=1,
                            max_count=1
                        ),
                        NodeGroup(
                            typing=NodeTypeRule(allowed_types=["str"]),
                            label="consignee",
                            min_count=1,
                            max_count=1
                        ),
                        NodeGroup(
                            typing=NodeTypeRule(allowed_types=["int"]),
                            label="pieces",
                            min_count=1,
                            max_count=1
                        ),
                        NodeGroup(
                            typing=NodeTypeRule(allowed_types=["float"]),
                            label="weight",
                            min_count=1,
                            max_count=1
                        ),
                    ]
                ),
                outputs=IOSideShape(nodes=[])  # Output modules have no outputs
            )
        )

    def run(
        self,
        inputs: Dict[str, Any],
        cfg: BasicOrderOutputConfig,
        context: OutputExecutionContext
    ) -> Dict[str, Any]:
        """
        Create order in Access DB and send confirmation email.

        Returns:
            {
                "status": "success" | "duplicate" | "failure",
                "order_number": str (if success),
                "hawb": str,
                "error": str (if failure)
            }
        """
        try:
            # Get customer's Access DB path
            customer = context.customer_repo.get_by_id(context.eto_run.customer_id)
            if not customer:
                return {
                    'status': 'failure',
                    'error': f'Customer {context.eto_run.customer_id} not found'
                }

            db_path = customer.access_db_path

            # Extract inputs (pipeline collected these)
            hawb = inputs.get('hawb')
            shipper = inputs.get('shipper')
            consignee = inputs.get('consignee')
            pieces = inputs.get('pieces')
            weight = inputs.get('weight')

            # Check if order already exists
            if context.order_helpers.check_order_exists_by_hawb(db_path, hawb):
                return {
                    'status': 'duplicate',
                    'hawb': hawb,
                    'message': f'Order with HAWB {hawb} already exists'
                }

            # Create order
            order_data = {
                'hawb': hawb,
                'shipper': shipper,
                'consignee': consignee,
                'pieces': pieces,
                'weight': weight,
            }

            order_num = context.order_helpers.create_order(db_path, order_data)

            # Send confirmation email
            context.email_helpers.send_order_confirmation(
                to_address=context.eto_run.source_email,  # Original sender
                order_number=order_num,
                hawb=hawb,
                integration_id=customer.email_integration_id
            )

            return {
                'status': 'success',
                'order_number': order_num,
                'hawb': hawb
            }

        except Exception as e:
            return {
                'status': 'failure',
                'error': str(e),
                'hawb': inputs.get('hawb')
            }
```

---

### 5. PipelineResultService Implementation

The main service that orchestrates output module execution.

```python
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from shared.database.repositories import (
    EtoSubRunOutputExecutionRepository,
    EtoSubRunRepository,
    EtoRunRepository,
    CustomerRepository,
    AddressRepository,
    EmailConfigRepository
)
from shared.services.connection_manager import ConnectionManager
from features.modules.catalog import ModuleCatalog
from shared.types.eto_sub_run_output_executions import (
    EtoSubRunOutputExecutionCreate,
    EtoSubRunOutputExecutionUpdate
)

logger = logging.getLogger(__name__)

class PipelineResultService:
    """
    Service for executing output modules with full ETO context.

    Orchestrates the output execution stage which happens after pipeline
    execution completes. Loads ETO context, builds execution context with
    all helpers/services, executes the output module, and tracks execution
    status in the database.

    Responsibilities:
    - Load ETO context (sub-run, parent run, customer data)
    - Build OutputExecutionContext with all helpers
    - Execute output module
    - Track execution status in eto_sub_run_output_executions table
    - Handle errors and retries
    """

    def __init__(
        self,
        connection_manager: ConnectionManager,
        output_execution_repo: EtoSubRunOutputExecutionRepository,
        sub_run_repo: EtoSubRunRepository,
        eto_run_repo: EtoRunRepository,
        customer_repo: CustomerRepository,
        address_repo: AddressRepository,
        email_config_repo: EmailConfigRepository,
        module_catalog: ModuleCatalog
    ):
        self.connection_manager = connection_manager
        self.output_execution_repo = output_execution_repo
        self.sub_run_repo = sub_run_repo
        self.eto_run_repo = eto_run_repo
        self.customer_repo = customer_repo
        self.address_repo = address_repo
        self.module_catalog = module_catalog

        # Initialize helpers (stateless utilities)
        self.order_helpers = OrderHelpers(connection_manager)
        self.email_helpers = EmailHelpers(email_config_repo)

    def execute_output(
        self,
        sub_run_id: int,
        module_id: str,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute output module with full ETO context.

        This is the main entry point called by the ETO orchestration layer
        after pipeline execution completes.

        Args:
            sub_run_id: ETO sub-run ID
            module_id: Output module ID to execute (e.g., "basic_order_output")
            input_data: Inputs collected from pipeline execution
                       Format: {input_name: value, ...}

        Returns:
            Execution result from the module
            Format varies by module but typically:
            {
                "status": "success" | "failure" | "duplicate",
                ... module-specific fields
            }

        Raises:
            ServiceError: If execution fails catastrophically
        """
        logger.info(f"Executing output module {module_id} for sub-run {sub_run_id}")

        # Create execution record (status = "pending")
        execution = self.output_execution_repo.create(
            EtoSubRunOutputExecutionCreate(
                sub_run_id=sub_run_id,
                module_id=module_id,
                input_data=input_data
            )
        )

        try:
            # Update status to "processing"
            self.output_execution_repo.update(
                execution.id,
                EtoSubRunOutputExecutionUpdate(
                    status="processing",
                    started_at=datetime.utcnow()
                )
            )

            # Load ETO context
            sub_run = self.sub_run_repo.get_by_id(sub_run_id)
            if not sub_run:
                raise ServiceError(f"Sub-run {sub_run_id} not found")

            eto_run = self.eto_run_repo.get_by_id(sub_run.eto_run_id)
            if not eto_run:
                raise ServiceError(f"ETO run {sub_run.eto_run_id} not found")

            # Get module
            module = self.module_catalog.get_module(module_id)
            if not module:
                raise ServiceError(f"Module {module_id} not found in catalog")

            # Build execution context
            context = OutputExecutionContext(
                sub_run=sub_run,
                eto_run=eto_run,
                connection_manager=self.connection_manager,
                order_helpers=self.order_helpers,
                email_helpers=self.email_helpers,
                customer_repo=self.customer_repo,
                address_repo=self.address_repo
            )

            # Execute module
            logger.info(f"Running module {module_id}.run() with inputs: {input_data}")
            result = module.run(
                inputs=input_data,
                cfg=module.ConfigModel(),
                context=context
            )

            # Update execution record (success)
            self.output_execution_repo.update(
                execution.id,
                EtoSubRunOutputExecutionUpdate(
                    status="success",
                    result=result,
                    completed_at=datetime.utcnow()
                )
            )

            logger.info(f"Output execution {execution.id} completed successfully")
            return result

        except Exception as e:
            logger.error(f"Output execution {execution.id} failed: {str(e)}", exc_info=True)

            # Update execution record (failure)
            self.output_execution_repo.update(
                execution.id,
                EtoSubRunOutputExecutionUpdate(
                    status="failure",
                    error_message=str(e),
                    error_type=type(e).__name__,
                    completed_at=datetime.utcnow()
                )
            )

            # Re-raise to let caller handle
            raise

    def retry_failed_execution(self, execution_id: int) -> Dict[str, Any]:
        """
        Retry a failed output execution.

        Args:
            execution_id: ID of failed execution to retry

        Returns:
            Execution result
        """
        # Load failed execution
        execution = self.output_execution_repo.get_by_id(execution_id)
        if not execution:
            raise ServiceError(f"Execution {execution_id} not found")

        if execution.status != "failure":
            raise ServiceError(f"Can only retry failed executions (status={execution.status})")

        # Retry using original input data
        return self.execute_output(
            sub_run_id=execution.sub_run_id,
            module_id=execution.module_id,
            input_data=execution.input_data
        )

    def get_pending_executions(self, limit: int = 100) -> list:
        """
        Get pending output executions for processing.

        Used by background workers to pick up pending executions.

        Args:
            limit: Max number of pending executions to return

        Returns:
            List of pending EtoSubRunOutputExecution records
        """
        return self.output_execution_repo.get_pending(limit=limit)
```

---

## Integration with ETO Orchestration

The PipelineResultService is called by the ETO service after pipeline execution completes:

```python
# In ETO service (features/eto_runs/service.py)

def process_sub_run(self, sub_run_id: int):
    """Process a single ETO sub-run"""

    # ... existing logic ...

    # Execute pipeline
    pipeline_result = self.pipeline_execution_service.execute_pipeline(
        steps=compiled_steps,
        entry_values=entry_values,
        pipeline_state=pipeline_state
    )

    # If pipeline succeeded and has output module, execute it
    if pipeline_result.status == "success" and pipeline_result.output_module_id:
        try:
            # Execute output module with full ETO context
            output_result = self.pipeline_result_service.execute_output(
                sub_run_id=sub_run_id,
                module_id=pipeline_result.output_module_id,
                input_data=pipeline_result.output_module_inputs
            )

            logger.info(f"Output execution completed: {output_result}")

        except Exception as e:
            logger.error(f"Output execution failed: {str(e)}")
            # Handle error (mark sub-run as failed, etc.)
```

---

## Open Questions & Considerations

### 1. Database Path Logic
**Question**: Is the Access database path always `customer.access_db_path`?

**Considerations**:
- Might vary per customer
- Could be configured per template
- Might need fallback logic

**Proposed Solution**: Keep it simple for now (customer.access_db_path), make it configurable later if needed.

---

### 2. Email Integration ID
**Question**: How do we determine which email integration to use?

**Current Assumption**: `customer.email_integration_id` exists

**Considerations**:
- Customer might have multiple email integrations
- Might want different integration per template
- Might need to match integration based on original email source

**Proposed Solution**: Add `email_integration_id` to Customer model, make it required for now.

---

### 3. Transaction Management
**Question**: What happens if order creation succeeds but email sending fails?

**Considerations**:
- Order is already in database (committed)
- Email fails (network issue, config error, etc.)
- Should we roll back the order?
- Should we retry email separately?

**Options**:
1. **Accept partial success** - Order created, email failed (log error, allow retry)
2. **Rollback on email failure** - Delete order if email fails (complex, not atomic)
3. **Two-phase commit** - Create order in temp state, commit only if email succeeds (complex)

**Recommended Approach**: Accept partial success for now. Log email failures and allow manual retry or notification to operations team. Most important thing is the order was created.

---

### 4. Helper Initialization
**Question**: Should helpers be stateless singletons in ServiceContainer?

**Current**: Created in PipelineResultService constructor

**Alternative**:
```python
# In ServiceContainer
@staticmethod
def get_order_helpers():
    return OrderHelpers(ServiceContainer.get_connection_manager())
```

**Trade-offs**:
- ServiceContainer approach: More centralized, easier to inject
- Current approach: Simpler, fewer dependencies

**Recommendation**: Keep current approach for now, refactor to ServiceContainer if we need helpers in multiple services.

---

### 5. Configuration vs Hard-coded Logic
**Question**: Should order creation logic be configurable or hard-coded?

**Considerations**:
- Different customers might have different Access DB schemas
- Field mappings might vary
- Validation rules might differ

**Options**:
1. **Hard-code for now** - One schema, refactor when we hit second customer
2. **Configuration-driven** - Define schema mappings in customer config
3. **Adapter pattern** - Customer-specific adapters for different schemas

**Recommendation**: Start with option 1 (hard-code for initial customer), add abstraction layer when we onboard second customer with different schema.

---

### 6. Error Handling & Retries
**Question**: How should we handle retries for transient failures?

**Considerations**:
- Network failures (email send, DB connection)
- Temporary resource exhaustion
- Duplicate detection (HAWB already exists)

**Proposed Approach**:
- Track execution status in database (pending → processing → success/failure)
- Provide `retry_failed_execution()` method
- Could add background worker to auto-retry transient failures
- Permanent failures (duplicate HAWB) should not retry

---

### 7. Input Data Format
**Question**: What format does `input_data` arrive in from pipeline execution?

**Current Assumption**: `{input_name: value, ...}`

**Need to Verify**:
- Pipeline execution currently returns `output_module_inputs: Dict[str, Any]`
- Does this match what modules expect?
- Might need transformation layer

---

## Next Steps

1. **Implement Core Service**
   - Create `server/src/features/pipeline_results/service.py`
   - Implement PipelineResultService with execute_output method
   - Add to ServiceContainer

2. **Implement Helper Classes**
   - Create `server/src/features/pipeline_results/helpers/order_helpers.py`
   - Create `server/src/features/pipeline_results/helpers/email_helpers.py`
   - Implement methods described in this document

3. **Create Context Type**
   - Add `OutputExecutionContext` to `server/src/shared/types/pipeline_results.py`
   - Ensure all necessary fields are included

4. **Update OutputModule ABC**
   - Modify `server/src/shared/types/modules.py`
   - Update `run()` signature to accept `OutputExecutionContext`

5. **Test with BasicOrderOutput**
   - Update existing BasicOrderOutput module to use new context
   - Test end-to-end with real ETO run

6. **Integrate with ETO Service**
   - Update `server/src/features/eto_runs/service.py`
   - Call PipelineResultService after pipeline execution
   - Handle errors appropriately

7. **Add Error Handling**
   - Define custom exceptions (DuplicateOrderError, EmailSendError, etc.)
   - Implement retry logic
   - Add logging throughout

8. **Documentation**
   - Add docstrings to all methods
   - Create usage examples
   - Document error scenarios

---

## File Structure

```
server/src/features/pipeline_results/
├── __init__.py
├── service.py                    # PipelineResultService
├── context.py                    # OutputExecutionContext dataclass
├── helpers/
│   ├── __init__.py
│   ├── order_helpers.py          # OrderHelpers class
│   └── email_helpers.py          # EmailHelpers class
└── exceptions.py                 # Custom exceptions

server/src/shared/types/
└── pipeline_results.py           # Types for pipeline results
```

---

## Summary

The **PipelineResultService** provides a clean architecture for executing output modules:

- **Separation of concerns**: Helpers handle specific logic, service orchestrates, modules implement business rules
- **Explicit dependencies**: Context object makes all dependencies visible
- **Testable**: Each component can be tested independently
- **Extensible**: Easy to add new helpers or context fields
- **Type-safe**: Typed context provides IDE support and compile-time checks

The design balances simplicity (for initial implementation) with flexibility (for future requirements).
