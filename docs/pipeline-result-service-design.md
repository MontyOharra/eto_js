# PipelineResultService Design Document

## Overview

This document captures the complete design for the **PipelineResultService** - the service responsible for executing output modules with full ETO context after pipeline execution completes.

---

## Table of Contents

1. [Background & Problem Statement](#1-background--problem-statement)
2. [Architecture Overview](#2-architecture-overview)
3. [State Flow](#3-state-flow)
4. [Database Schema](#4-database-schema)
5. [Core Components](#5-core-components)
6. [Output Module Contract](#6-output-module-contract)
7. [Service Implementation](#7-service-implementation)
8. [Helper Classes](#8-helper-classes)
9. [Email System](#9-email-system)
10. [Integration Points](#10-integration-points)
11. [Data Flow](#11-data-flow)
12. [File Structure](#12-file-structure)
13. [Implementation Sequence](#13-implementation-sequence)

---

## 1. Background & Problem Statement

### The Two-Phase Model

The system separates pipeline execution into two distinct phases:

| Phase | Responsibility | Side Effects |
|-------|---------------|--------------|
| **Phase 1: Pipeline Execution** | Pure data transformation (DAG execution) | None |
| **Phase 2: Output Execution** | Side effects with full ETO context | Orders, emails, file transfers |

### Why This Separation?

- Pipeline modules are **stateless** and **testable in isolation**
- Output modules need **database connections**, **customer data**, **email configs**
- Clean separation of concerns enables better testing and maintenance

### Current State

After pipeline execution completes, it returns:
- `output_module_id`: The ID of the output module (e.g., `"basic_order_output"`)
- `output_module_inputs`: Collected input data `{field_name: value, ...}`

**The Gap:** Currently nothing happens with this data. The PipelineResultService bridges this gap.

### Order Create vs Update Logic

A critical business requirement: orders are identified by HAWB (House Air Waybill). When processing:
- **HAWB not found** → Auto-create new order
- **HAWB found once** → Queue for user approval before updating
- **HAWB found multiple times** → Error, manual entry required

---

## 2. Architecture Overview

### Chosen Pattern: Typed Context Object + Helper Classes

```
┌─────────────────────────────────────────────────────────────────────┐
│                        EtoRunsService                                │
│  (Orchestrator - calls PipelineResultService after pipeline)        │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     PipelineResultService                            │
│  - Creates output execution record                                  │
│  - Checks HAWB existence                                            │
│  - Routes to create/update/error flow                               │
│  - Handles user approval for updates                                │
│  - Sends confirmation emails                                        │
│  - Stores final result for frontend                                 │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
            ┌───────────┐   ┌───────────┐   ┌───────────────┐
            │OrderHelpers│   │EmailHelpers│   │AddressHelpers│
            └───────────┘   └───────────┘   └───────────────┘
                    │               │               │
                    └───────────────┼───────────────┘
                                    ▼
                        ┌───────────────────┐
                        │ OutputModule      │
                        │ .create_order()   │
                        │ .update_order()   │
                        └───────────────────┘
```

### Why This Pattern?

| Option | Description | Verdict |
|--------|-------------|---------|
| **Option 1: Methods in ABC** | Put helpers as methods on OutputModule base class | ❌ REJECTED - ABC becomes bloated, tight coupling |
| **Option 2: Service Locator** | Pass `ServiceContainer` to modules | ❌ REJECTED - Hidden dependencies, anti-pattern |
| **Option 3: Typed Context** | Pass typed `OutputExecutionContext` dataclass | ✅ CHOSEN - Explicit, testable, extensible |

---

## 3. State Flow

### Output Execution States

```
┌─────────────────────────────────────────────────────────────────┐
│                    OUTPUT EXECUTION STATES                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  pending              → Record created, not yet started         │
│       │                                                          │
│       ▼                                                          │
│  processing           → Checking HAWB, executing action         │
│       │                                                          │
│       ├──→ HAWB not found ──────────────────→ (create order)    │
│       │                                              │           │
│       │                                              ▼           │
│       │                                          success         │
│       │                                                          │
│       ├──→ HAWB found once ──→ awaiting_approval                │
│       │                              │                           │
│       │                              ├──→ User approves          │
│       │                              │         │                 │
│       │                              │         ▼                 │
│       │                              │    processing (update)    │
│       │                              │         │                 │
│       │                              │         ▼                 │
│       │                              │     success               │
│       │                              │                           │
│       │                              └──→ User rejects ──→ rejected
│       │                                                          │
│       └──→ HAWB found multiple ──→ error                        │
│                                                                  │
│  (processing can also → error if DB/email fails)                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Status Values

```python
OUTPUT_EXECUTION_STATUS = Literal[
    "pending",            # Record created, not yet started
    "processing",         # Actively checking HAWB or executing create/update
    "awaiting_approval",  # HAWB found once, needs user approval for update
    "success",            # Completed successfully (order created or updated)
    "rejected",           # User rejected the update
    "error",              # Failed (multiple HAWBs, DB error, etc.) - terminal state
]
```

### State Transitions

| From | To | Trigger |
|------|-----|---------|
| `pending` | `processing` | Service starts processing |
| `processing` | `success` | Order created successfully |
| `processing` | `awaiting_approval` | HAWB found once |
| `processing` | `error` | Multiple HAWBs or DB error |
| `awaiting_approval` | `processing` | User approves update |
| `awaiting_approval` | `rejected` | User rejects update |
| `processing` (after approval) | `success` | Order updated successfully |
| `processing` (after approval) | `error` | Update failed |

---

## 4. Database Schema

### Extended `eto_sub_run_output_executions` Table

```sql
-- Existing fields
id SERIAL PRIMARY KEY,
sub_run_id INTEGER NOT NULL REFERENCES eto_sub_runs(id),
module_id VARCHAR NOT NULL,
input_data_json TEXT NOT NULL,           -- Pipeline output data (stored as JSON)
status VARCHAR NOT NULL DEFAULT 'pending',
result_json TEXT,                         -- Final result for frontend display
error_message TEXT,
error_type VARCHAR,
started_at TIMESTAMP WITH TIME ZONE,
completed_at TIMESTAMP WITH TIME ZONE,
created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

-- New fields for create/update flow
action_type VARCHAR,                      -- 'create' | 'update' | NULL (before HAWB check)
hawb VARCHAR,                             -- Extracted from input_data for easy querying
existing_order_number INTEGER,            -- If update, the order being updated (NULL for creates)
existing_order_data_json TEXT,            -- Snapshot of current order for comparison UI (NULL for creates)

-- Indexes
CREATE INDEX idx_output_exec_status ON eto_sub_run_output_executions(status);
CREATE INDEX idx_output_exec_hawb ON eto_sub_run_output_executions(hawb);
CREATE INDEX idx_output_exec_awaiting ON eto_sub_run_output_executions(status) WHERE status = 'awaiting_approval';
```

### Domain Types

**Location:** `server/src/shared/types/eto_sub_run_output_executions.py`

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Literal, Optional, TypedDict

OutputExecutionStatus = Literal[
    "pending",
    "processing",
    "awaiting_approval",
    "success",
    "rejected",
    "error",
]

ActionType = Literal["create", "update"]


@dataclass
class EtoSubRunOutputExecutionCreate:
    """Data required to create a new output execution record."""
    sub_run_id: int
    module_id: str
    input_data: Dict[str, Any]
    hawb: str  # Extracted from input_data


class EtoSubRunOutputExecutionUpdate(TypedDict, total=False):
    """Dict for updating an output execution record."""
    status: OutputExecutionStatus
    action_type: ActionType | None
    input_data: Dict[str, Any] | None
    result: Dict[str, Any] | None
    error_message: str | None
    error_type: str | None
    existing_order_number: int | None
    existing_order_data: Dict[str, Any] | None
    started_at: datetime | None
    completed_at: datetime | None


@dataclass
class EtoSubRunOutputExecution:
    """Complete output execution record from database."""
    id: int
    sub_run_id: int
    module_id: str
    input_data: Dict[str, Any]
    status: OutputExecutionStatus
    action_type: Optional[ActionType]
    hawb: str
    existing_order_number: Optional[int]
    existing_order_data: Optional[Dict[str, Any]]
    result: Optional[Dict[str, Any]]
    error_message: Optional[str]
    error_type: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
```

### Result JSON Structure

The `result_json` field stores the final outcome for frontend display:

**For successful create:**
```json
{
  "action": "create",
  "order_number": 12345,
  "hawb": "ABC123",
  "customer_id": 5,
  "email_sent": true,
  "email_recipient": "sender@example.com"
}
```

**For successful update:**
```json
{
  "action": "update",
  "order_number": 12345,
  "hawb": "ABC123",
  "fields_updated": ["pickup_time_start", "pickup_time_end", "delivery_notes"],
  "email_sent": true,
  "email_recipient": "sender@example.com"
}
```

### Error Types

| Error Type | Description |
|------------|-------------|
| `multiple_hawb` | HAWB found multiple times in database |
| `create_failed` | Order creation failed (DB error, validation, etc.) |
| `update_failed` | Order update failed (DB error, validation, etc.) |
| `email_failed` | Order succeeded but email sending failed |
| `user_rejected` | User rejected the update |
| `module_not_found` | Output module ID not in catalog |
| `context_error` | Failed to load ETO context (sub-run, eto-run, etc.) |

---

## 5. Core Components

### 5.1 OutputExecutionContext

**Location:** `server/src/features/pipeline_results/context.py`

```python
from dataclasses import dataclass
from typing import TYPE_CHECKING

from shared.types.eto_runs import EtoRun
from shared.types.eto_sub_runs import EtoSubRun

if TYPE_CHECKING:
    from features.pipeline_results.helpers.order_helpers import OrderHelpers
    from features.pipeline_results.helpers.email_helpers import EmailHelpers
    from features.pipeline_results.helpers.address_helpers import AddressHelpers


@dataclass
class OutputExecutionContext:
    """
    Context provided to output modules during execution.

    Contains all services, helpers, and ETO-specific data needed
    for output module execution.
    """
    # ETO domain data
    sub_run: EtoSubRun
    eto_run: EtoRun

    # Helpers (stateless utilities with connection access)
    order_helpers: 'OrderHelpers'
    email_helpers: 'EmailHelpers'
    address_helpers: 'AddressHelpers'

    # PDF info (for file transfer operations)
    pdf_file_id: int
    pdf_storage_path: str

    # Source email info (for sending confirmations)
    source_email_address: str | None  # None if manual upload
    email_integration_id: int | None  # SMTP config to use
```

---

## 6. Output Module Contract

### Updated OutputModule ABC

**Location:** `server/src/shared/types/modules.py`

```python
from abc import ABC, abstractmethod
from typing import Dict, Any
from pydantic import BaseModel


class OutputModule(BaseModule):
    """
    Base class for Output modules - pipeline exit points for order processing.

    Output modules:
    1. Define inputs via meta() - must include 'hawb' input
    2. Define email templates for create/update confirmations
    3. Implement create_order() for new orders
    4. Implement update_order() for existing orders

    The PipelineResultService handles:
    - HAWB existence checking
    - Routing to create vs update
    - User approval flow for updates
    - Email sending using module's templates
    """
    kind = ModuleKind.OUTPUT

    # Email templates - must be defined by each module
    email_subject_create: str  # e.g., "Order {order_number} Created - HAWB {hawb}"
    email_subject_update: str  # e.g., "Order {order_number} Updated - HAWB {hawb}"
    email_body_create: str     # Template with {placeholders}
    email_body_update: str     # Template with {placeholders}

    def run(self, inputs: Dict[str, Any], cfg: Any,
            context: Any = None, services: Any = None) -> Dict[str, Any]:
        """
        Legacy run method - not used for output modules.
        Output modules use create_order() and update_order() instead.
        """
        return {}

    @abstractmethod
    def create_order(
        self,
        inputs: Dict[str, Any],
        context: 'OutputExecutionContext'
    ) -> Dict[str, Any]:
        """
        Create a new order from the input data.

        Args:
            inputs: Transformed data from pipeline execution
            context: Full ETO context with helpers

        Returns:
            Result dict with at minimum:
            {
                "order_number": int,
                "hawb": str,
                ... additional fields for result display
            }

        Raises:
            Exception: If order creation fails
        """
        pass

    @abstractmethod
    def update_order(
        self,
        inputs: Dict[str, Any],
        existing_order_number: int,
        context: 'OutputExecutionContext'
    ) -> Dict[str, Any]:
        """
        Update an existing order with the input data.

        Args:
            inputs: Transformed data from pipeline execution
            existing_order_number: The order number to update
            context: Full ETO context with helpers

        Returns:
            Result dict with at minimum:
            {
                "order_number": int,
                "hawb": str,
                "fields_updated": list[str],  # Which fields were changed
                ... additional fields for result display
            }

        Raises:
            Exception: If order update fails
        """
        pass
```

### HAWB Input Requirement

Every output module MUST define a `hawb` input in its `meta()`:

```python
@classmethod
def meta(cls) -> ModuleMeta:
    return ModuleMeta(
        io_shape=IOShape(
            inputs=IOSideShape(nodes=[
                # HAWB is REQUIRED for all output modules
                NodeGroup(
                    label="hawb",
                    min_count=1,
                    max_count=1,
                    typing=NodeTypeRule(allowed_types=["str"])
                ),
                # ... other inputs
            ]),
            outputs=IOSideShape(nodes=[])  # No outputs - terminal node
        )
    )
```

---

## 7. Service Implementation

### PipelineResultService

**Location:** `server/src/features/pipeline_results/service.py`

```python
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

from shared.database.repositories.eto_sub_run_output_execution import EtoSubRunOutputExecutionRepository
from shared.database.repositories.eto_sub_run import EtoSubRunRepository
from shared.database.repositories.eto_run import EtoRunRepository
from shared.database.repositories.email import EmailRepository
from shared.database.repositories.email_config import EmailConfigRepository
from shared.types.eto_sub_run_output_executions import (
    EtoSubRunOutputExecution,
    EtoSubRunOutputExecutionCreate,
    EtoSubRunOutputExecutionUpdate,
)
from features.modules.catalog import ModuleCatalog
from features.pipeline_results.context import OutputExecutionContext
from features.pipeline_results.helpers.order_helpers import OrderHelpers
from features.pipeline_results.helpers.email_helpers import EmailHelpers
from features.pipeline_results.helpers.address_helpers import AddressHelpers
from features.pipeline_results.exceptions import (
    OutputExecutionError,
    InvalidStateError,
    ModuleNotFoundError,
)

logger = logging.getLogger(__name__)


class PipelineResultService:
    """
    Service for executing output modules with full ETO context.

    Handles the complete output execution flow:
    1. Creates execution record
    2. Checks HAWB existence
    3. Routes to create (auto) or update (approval) flow
    4. Executes the appropriate module method
    5. Sends confirmation emails
    6. Stores final result for frontend display
    """

    def __init__(
        self,
        output_execution_repo: EtoSubRunOutputExecutionRepository,
        sub_run_repo: EtoSubRunRepository,
        eto_run_repo: EtoRunRepository,
        email_repo: EmailRepository,
        email_config_repo: EmailConfigRepository,
        module_catalog: ModuleCatalog,
        data_database_manager: Any,
        pdf_storage_path: str,
    ):
        self.output_execution_repo = output_execution_repo
        self.sub_run_repo = sub_run_repo
        self.eto_run_repo = eto_run_repo
        self.email_repo = email_repo
        self.module_catalog = module_catalog
        self.pdf_storage_path = pdf_storage_path

        # Initialize helpers
        self.order_helpers = OrderHelpers(data_database_manager)
        self.email_helpers = EmailHelpers(email_config_repo)
        self.address_helpers = AddressHelpers(data_database_manager)

    # ==================== Main Entry Point ====================

    def execute_output(
        self,
        sub_run_id: int,
        module_id: str,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Main entry point from ETO processing after pipeline completes.

        Step 0: Pipeline passed data here
        Step 1: Create execution record
        Step 2: Check HAWB existence
        Step 3: Branch based on result

        Args:
            sub_run_id: ETO sub-run ID
            module_id: Output module ID (e.g., "basic_order_output")
            input_data: Inputs collected from pipeline execution {name: value}

        Returns:
            Result dict with status and relevant data
        """
        logger.info(f"Executing output module {module_id} for sub-run {sub_run_id}")

        # Validate HAWB is present
        hawb = input_data.get("hawb")
        if not hawb:
            raise OutputExecutionError("HAWB is required in output module inputs")

        # Step 1: Create execution record
        execution = self.output_execution_repo.create(
            EtoSubRunOutputExecutionCreate(
                sub_run_id=sub_run_id,
                module_id=module_id,
                input_data=input_data,
                hawb=hawb,
            )
        )
        logger.debug(f"Created output execution record {execution.id}")

        # Update to processing
        self._update_status(execution.id, "processing")

        try:
            # Step 2: Check HAWB existence
            hawb_matches = self.order_helpers.find_orders_by_hawb(hawb)
            logger.debug(f"HAWB {hawb} found {len(hawb_matches)} times")

            # Step 3: Branch based on count
            if len(hawb_matches) == 0:
                # No existing order - auto create
                return self._execute_create(execution, input_data)

            elif len(hawb_matches) == 1:
                # One existing order - queue for approval
                return self._queue_for_approval(execution, input_data, hawb_matches[0])

            else:
                # Multiple matches - error, manual entry required
                return self._set_error(
                    execution,
                    error_type="multiple_hawb",
                    error_message=f"HAWB {hawb} found {len(hawb_matches)} times in database. Manual entry required."
                )

        except Exception as e:
            logger.error(f"Output execution {execution.id} failed: {e}", exc_info=True)
            return self._set_error(execution, "execution_error", str(e))

    # ==================== Create Flow ====================

    def _execute_create(
        self,
        execution: EtoSubRunOutputExecution,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute order creation."""
        logger.info(f"Executing create for execution {execution.id}")

        try:
            # Get module
            module = self._get_module(execution.module_id)

            # Build context
            context = self._build_context(execution)

            # Update action type
            self.output_execution_repo.update(execution.id, {"action_type": "create"})

            # Call module's create method
            result = module.create_order(input_data, context)

            # Send confirmation email
            email_sent = self._send_email(execution, module, "create", result, context)
            result["email_sent"] = email_sent
            if context.source_email_address:
                result["email_recipient"] = context.source_email_address

            # Update record with success
            self.output_execution_repo.update(execution.id, {
                "status": "success",
                "result": result,
                "completed_at": datetime.now(timezone.utc)
            })

            logger.info(f"Execution {execution.id} completed: created order {result.get('order_number')}")
            return {"status": "success", **result}

        except Exception as e:
            logger.error(f"Create failed for execution {execution.id}: {e}", exc_info=True)
            return self._set_error(execution, "create_failed", str(e))

    # ==================== Update Flow ====================

    def _queue_for_approval(
        self,
        execution: EtoSubRunOutputExecution,
        input_data: Dict[str, Any],
        existing_order: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Queue for user approval before updating."""
        logger.info(f"Queueing execution {execution.id} for approval (order {existing_order['order_number']})")

        # Get current order data for comparison
        existing_order_data = self.order_helpers.get_order_details(existing_order["order_number"])

        self.output_execution_repo.update(execution.id, {
            "status": "awaiting_approval",
            "action_type": "update",
            "existing_order_number": existing_order["order_number"],
            "existing_order_data": existing_order_data,
        })

        return {
            "status": "awaiting_approval",
            "execution_id": execution.id,
            "existing_order_number": existing_order["order_number"],
            "hawb": input_data.get("hawb"),
        }

    def approve_update(self, execution_id: int) -> Dict[str, Any]:
        """
        User approved the update - execute it.

        Called from API endpoint when user confirms the update.

        Args:
            execution_id: Output execution ID

        Returns:
            Result dict with status and order data
        """
        execution = self.output_execution_repo.get_by_id(execution_id)
        if not execution:
            raise OutputExecutionError(f"Execution {execution_id} not found")

        if execution.status != "awaiting_approval":
            raise InvalidStateError(
                f"Cannot approve execution in '{execution.status}' state. "
                f"Expected 'awaiting_approval'."
            )

        logger.info(f"User approved update for execution {execution_id}")

        # Set back to processing
        self._update_status(execution_id, "processing")

        try:
            # Get module
            module = self._get_module(execution.module_id)

            # Build context
            context = self._build_context(execution)

            # Call module's update method
            result = module.update_order(
                execution.input_data,
                execution.existing_order_number,
                context
            )

            # Send confirmation email
            email_sent = self._send_email(execution, module, "update", result, context)
            result["email_sent"] = email_sent
            if context.source_email_address:
                result["email_recipient"] = context.source_email_address

            # Update record with success
            self.output_execution_repo.update(execution_id, {
                "status": "success",
                "result": result,
                "completed_at": datetime.now(timezone.utc)
            })

            logger.info(f"Execution {execution_id} completed: updated order {result.get('order_number')}")
            return {"status": "success", **result}

        except Exception as e:
            logger.error(f"Update failed for execution {execution_id}: {e}", exc_info=True)
            return self._set_error(execution, "update_failed", str(e))

    def reject_update(self, execution_id: int) -> Dict[str, Any]:
        """
        User rejected the update.

        Called from API endpoint when user rejects the update.

        Args:
            execution_id: Output execution ID

        Returns:
            Result dict confirming rejection
        """
        execution = self.output_execution_repo.get_by_id(execution_id)
        if not execution:
            raise OutputExecutionError(f"Execution {execution_id} not found")

        if execution.status != "awaiting_approval":
            raise InvalidStateError(
                f"Cannot reject execution in '{execution.status}' state. "
                f"Expected 'awaiting_approval'."
            )

        logger.info(f"User rejected update for execution {execution_id}")

        self.output_execution_repo.update(execution_id, {
            "status": "rejected",
            "error_type": "user_rejected",
            "error_message": "Update rejected by user",
            "completed_at": datetime.now(timezone.utc)
        })

        return {
            "status": "rejected",
            "execution_id": execution_id,
            "hawb": execution.hawb,
        }

    # ==================== Query Methods ====================

    def get_pending_approvals(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List[EtoSubRunOutputExecution]:
        """
        Get output executions awaiting user approval.

        Used by frontend to display approval queue.
        """
        return self.output_execution_repo.get_by_status(
            "awaiting_approval",
            limit=limit
        )

    def get_execution_detail(self, execution_id: int) -> Optional[EtoSubRunOutputExecution]:
        """
        Get full execution details for approval UI.

        Returns execution with existing_order_data for comparison display.
        """
        return self.output_execution_repo.get_by_id(execution_id)

    # ==================== Helper Methods ====================

    def _update_status(self, execution_id: int, status: str) -> None:
        """Update execution status with timestamp."""
        updates = {"status": status}
        if status == "processing":
            updates["started_at"] = datetime.now(timezone.utc)
        self.output_execution_repo.update(execution_id, updates)

    def _set_error(
        self,
        execution: EtoSubRunOutputExecution,
        error_type: str,
        error_message: str
    ) -> Dict[str, Any]:
        """Set execution to error state."""
        self.output_execution_repo.update(execution.id, {
            "status": "error",
            "error_type": error_type,
            "error_message": error_message,
            "completed_at": datetime.now(timezone.utc)
        })

        logger.error(f"Execution {execution.id} error: [{error_type}] {error_message}")

        return {
            "status": "error",
            "execution_id": execution.id,
            "error_type": error_type,
            "error_message": error_message,
        }

    def _get_module(self, module_id: str):
        """Get output module from catalog."""
        module = self.module_catalog.get_module(module_id)
        if not module:
            raise ModuleNotFoundError(f"Output module '{module_id}' not found in catalog")
        return module

    def _build_context(self, execution: EtoSubRunOutputExecution) -> OutputExecutionContext:
        """Build execution context with all required data."""
        # Load sub-run
        sub_run = self.sub_run_repo.get_by_id(execution.sub_run_id)
        if not sub_run:
            raise OutputExecutionError(f"Sub-run {execution.sub_run_id} not found")

        # Load parent ETO run
        eto_run = self.eto_run_repo.get_by_id(sub_run.eto_run_id)
        if not eto_run:
            raise OutputExecutionError(f"ETO run {sub_run.eto_run_id} not found")

        # Get source email address if email-sourced
        source_email_address = None
        email_integration_id = None

        if eto_run.source_type == "email" and eto_run.source_email_id:
            email = self.email_repo.get_by_id(eto_run.source_email_id)
            if email:
                source_email_address = email.sender_email
            # TODO: Get email_integration_id from customer config

        return OutputExecutionContext(
            sub_run=sub_run,
            eto_run=eto_run,
            order_helpers=self.order_helpers,
            email_helpers=self.email_helpers,
            address_helpers=self.address_helpers,
            pdf_file_id=eto_run.pdf_file_id,
            pdf_storage_path=self.pdf_storage_path,
            source_email_address=source_email_address,
            email_integration_id=email_integration_id,
        )

    def _send_email(
        self,
        execution: EtoSubRunOutputExecution,
        module: Any,
        action_type: str,
        result: Dict[str, Any],
        context: OutputExecutionContext
    ) -> bool:
        """
        Send confirmation email based on action type.

        Returns True if email sent, False if skipped or failed.
        """
        if not context.source_email_address:
            logger.debug(f"No source email for execution {execution.id}, skipping email")
            return False

        if not context.email_integration_id:
            logger.warning(f"No email integration configured for execution {execution.id}")
            return False

        try:
            # Select template based on action
            if action_type == "create":
                subject_template = module.email_subject_create
                body_template = module.email_body_create
            else:
                subject_template = module.email_subject_update
                body_template = module.email_body_update

            # Build template context
            template_vars = {
                **execution.input_data,
                **result,
                "action_type": action_type,
            }

            subject = subject_template.format(**template_vars)
            body = body_template.format(**template_vars)

            # Send via email helpers
            self.email_helpers.send_email(
                to_address=context.source_email_address,
                subject=subject,
                body=body,
                integration_id=context.email_integration_id
            )

            logger.info(f"Sent {action_type} confirmation email to {context.source_email_address}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email for execution {execution.id}: {e}")
            # Don't fail the execution, just log the error
            return False
```

---

## 8. Helper Classes

### 8.1 OrderHelpers

**Location:** `server/src/features/pipeline_results/helpers/order_helpers.py`

```python
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class OrderHelpers:
    """
    Utilities for order operations in Access database.
    Handles HAWB lookups, order number generation, and order CRUD.
    """

    def __init__(self, data_database_manager):
        self.db_manager = data_database_manager

    def find_orders_by_hawb(self, hawb: str) -> List[Dict[str, Any]]:
        """
        Find all orders with the given HAWB.

        Args:
            hawb: House Air Waybill number

        Returns:
            List of order dicts with at minimum {"order_number": int}
            Empty list if no matches.
        """
        connection = self.db_manager.get_connection("htc_300_db")

        sql = """
            SELECT OrderNumber, HAWB, CustomerID
            FROM [HTC300_G040_T010A Open Orders]
            WHERE HAWB = ?
        """

        with connection.cursor() as cursor:
            cursor.execute(sql, (hawb,))
            rows = cursor.fetchall()

            return [
                {
                    "order_number": row.OrderNumber,
                    "hawb": row.HAWB,
                    "customer_id": row.CustomerID,
                }
                for row in rows
            ]

    def get_order_details(self, order_number: int) -> Dict[str, Any]:
        """
        Get full order details for comparison display.

        Args:
            order_number: The order number to fetch

        Returns:
            Complete order data dict
        """
        connection = self.db_manager.get_connection("htc_300_db")

        sql = """
            SELECT *
            FROM [HTC300_G040_T010A Open Orders]
            WHERE OrderNumber = ?
        """

        with connection.cursor() as cursor:
            cursor.execute(sql, (order_number,))
            row = cursor.fetchone()

            if not row:
                return {}

            # Convert row to dict
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, row))

    def generate_next_order_number(self) -> int:
        """
        Generate next available order number.

        Returns:
            Next order number (integer)
        """
        connection = self.db_manager.get_connection("htc_300_db")

        sql = """
            SELECT MAX(OrderNumber) as max_order
            FROM [HTC300_G040_T010A Open Orders]
        """

        with connection.cursor() as cursor:
            cursor.execute(sql)
            row = cursor.fetchone()
            max_order = row.max_order if row and row.max_order else 0
            return max_order + 1

    def create_order(self, order_data: Dict[str, Any]) -> int:
        """
        Create a new order in the database.

        Args:
            order_data: Complete order data

        Returns:
            Generated order number
        """
        # Implementation depends on actual table schema
        # This is a placeholder structure
        order_number = self.generate_next_order_number()

        connection = self.db_manager.get_connection("htc_300_db")

        # TODO: Implement actual insert based on schema
        # sql = "INSERT INTO [HTC300_G040_T010A Open Orders] (...) VALUES (...)"

        logger.info(f"Created order {order_number}")
        return order_number

    def update_order(
        self,
        order_number: int,
        update_data: Dict[str, Any]
    ) -> List[str]:
        """
        Update an existing order.

        Args:
            order_number: Order to update
            update_data: Fields to update

        Returns:
            List of field names that were updated
        """
        # Implementation depends on actual table schema
        # This is a placeholder structure

        connection = self.db_manager.get_connection("htc_300_db")

        # TODO: Implement actual update based on schema
        # Compare current values to update_data, only update changed fields

        fields_updated = list(update_data.keys())
        logger.info(f"Updated order {order_number}: {fields_updated}")
        return fields_updated
```

### 8.2 EmailHelpers

**Location:** `server/src/features/pipeline_results/helpers/email_helpers.py`

```python
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List
import logging

from shared.database.repositories.email_config import EmailConfigRepository
from features.pipeline_results.exceptions import EmailConfigError, EmailSendError

logger = logging.getLogger(__name__)


class EmailHelpers:
    """
    Utilities for sending emails via configured SMTP.
    """

    def __init__(self, email_config_repo: EmailConfigRepository):
        self.email_config_repo = email_config_repo

    def send_email(
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
            to_address: Recipient email
            subject: Email subject
            body: Email body (plain text)
            integration_id: Email config ID for SMTP settings
            attachments: Optional file paths to attach

        Raises:
            EmailConfigError: If integration not found
            EmailSendError: If sending fails
        """
        # Load config
        config = self.email_config_repo.get_by_id(integration_id)
        if not config:
            raise EmailConfigError(f"Email integration {integration_id} not found")

        # Build message
        msg = MIMEMultipart()
        msg['From'] = config.from_address
        msg['To'] = to_address
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        # Add attachments if provided
        if attachments:
            for filepath in attachments:
                # TODO: Implement attachment handling
                pass

        # Send
        try:
            with smtplib.SMTP(config.smtp_host, config.smtp_port) as server:
                if config.use_tls:
                    server.starttls()
                if config.smtp_username:
                    server.login(config.smtp_username, config.smtp_password)
                server.send_message(msg)

            logger.info(f"Email sent to {to_address}: {subject}")

        except Exception as e:
            raise EmailSendError(f"Failed to send email: {str(e)}")
```

### 8.3 AddressHelpers

**Location:** `server/src/features/pipeline_results/helpers/address_helpers.py`

```python
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class AddressHelpers:
    """
    Utilities for address lookup and creation.
    """

    def __init__(self, data_database_manager):
        self.db_manager = data_database_manager

    def get_address_by_id(self, address_id: int) -> Optional[Dict[str, Any]]:
        """
        Get address record by ID.

        Returns:
            Address dict or None if not found
        """
        # TODO: Implement based on actual address table schema
        pass

    def create_address_from_text(
        self,
        address_text: str,
        customer_id: int
    ) -> int:
        """
        Parse address text and create new address record.

        Args:
            address_text: Full address string to parse
            customer_id: Customer ID for the address

        Returns:
            New address ID
        """
        # TODO: Implement address parsing and creation
        pass

    def resolve_address(
        self,
        address_id: Optional[int],
        address_text: Optional[str],
        customer_id: int
    ) -> int:
        """
        Resolve address to an ID (lookup existing or create new).

        Args:
            address_id: Existing address ID (if provided)
            address_text: Address text to parse (if no ID)
            customer_id: Customer for new address creation

        Returns:
            Address ID (existing or newly created)

        Raises:
            ValidationError: If neither ID nor text provided
        """
        if address_id:
            # Verify it exists
            address = self.get_address_by_id(address_id)
            if not address:
                raise ValueError(f"Address {address_id} not found")
            return address_id

        if address_text:
            return self.create_address_from_text(address_text, customer_id)

        raise ValueError("Either address_id or address_text must be provided")
```

---

## 9. Email System

### Email Template Definition

Each output module defines email templates with placeholders:

```python
class BasicOrderOutput(OutputModule):
    # ... other fields ...

    email_subject_create = "Order {order_number} Created - HAWB {hawb}"
    email_subject_update = "Order {order_number} Updated - HAWB {hawb}"

    email_body_create = """
Dear Customer,

Your order has been successfully created.

Order Details:
- Order Number: {order_number}
- HAWB: {hawb}
- Customer ID: {customer_id}

Pickup: {pickup_time_start} - {pickup_time_end}
Delivery: {delivery_time_start} - {delivery_time_end}

Thank you for your business.

Best regards,
Automated Order Processing System
    """.strip()

    email_body_update = """
Dear Customer,

Your order has been updated.

Order Details:
- Order Number: {order_number}
- HAWB: {hawb}

Updated Fields: {fields_updated}

Thank you for your business.

Best regards,
Automated Order Processing System
    """.strip()
```

### Template Variables

Templates have access to:
- All fields from `input_data` (pipeline output)
- All fields from module's `result` dict
- `action_type`: "create" or "update"

---

## 10. Integration Points

### 10.1 Where to Call PipelineResultService

**File:** `server/src/features/eto_runs/service.py`
**Method:** `_process_sub_run_pipeline()`
**After line:** ~994 (after pipeline execution completes successfully)

```python
def _process_sub_run_pipeline(self, sub_run_id: int, extracted_data: list) -> None:
    # ... existing code through line 994 ...

    logger.monitor(f"Sub-run {sub_run_id}: Pipeline execution completed successfully")

    # NEW: Execute output module if present
    if execution_result.output_module_id and execution_result.output_module_inputs:
        logger.info(
            f"Sub-run {sub_run_id}: Executing output module "
            f"{execution_result.output_module_id}"
        )

        output_result = self.pipeline_result_service.execute_output(
            sub_run_id=sub_run_id,
            module_id=execution_result.output_module_id,
            input_data=execution_result.output_module_inputs
        )

        logger.info(f"Sub-run {sub_run_id}: Output execution result: {output_result}")

        # If awaiting approval, the sub-run stays in processing state
        # until user approves/rejects via API
        if output_result.get("status") == "awaiting_approval":
            logger.info(
                f"Sub-run {sub_run_id}: Awaiting user approval for order update"
            )
            # Don't mark sub-run as complete yet
            return

        # If error, the sub-run should be marked as failed
        if output_result.get("status") == "error":
            raise ServiceError(
                f"Output execution failed: {output_result.get('error_message')}"
            )
```

### 10.2 API Endpoints

**File:** `server/src/api/routers/output_executions.py` (new)

```python
from fastapi import APIRouter, HTTPException
from shared.services.service_container import ServiceContainer

router = APIRouter(prefix="/output-executions", tags=["output-executions"])


@router.get("/pending-approvals")
def get_pending_approvals(limit: int = 100, offset: int = 0):
    """Get output executions awaiting user approval."""
    service = ServiceContainer.get_pipeline_result_service()
    executions = service.get_pending_approvals(limit=limit, offset=offset)
    return {"executions": executions}


@router.get("/{execution_id}")
def get_execution_detail(execution_id: int):
    """Get full execution details for approval UI."""
    service = ServiceContainer.get_pipeline_result_service()
    execution = service.get_execution_detail(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    return execution


@router.post("/{execution_id}/approve")
def approve_update(execution_id: int):
    """Approve an order update."""
    service = ServiceContainer.get_pipeline_result_service()
    try:
        result = service.approve_update(execution_id)
        return result
    except InvalidStateError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{execution_id}/reject")
def reject_update(execution_id: int):
    """Reject an order update."""
    service = ServiceContainer.get_pipeline_result_service()
    try:
        result = service.reject_update(execution_id)
        return result
    except InvalidStateError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

### 10.3 ServiceContainer Registration

**File:** `server/src/shared/services/service_container.py`

```python
from features.pipeline_results.service import PipelineResultService

class ServiceContainer:
    _pipeline_result_service: Optional[PipelineResultService] = None

    @classmethod
    def initialize(cls, ...):
        # ... existing initialization ...

        # Initialize PipelineResultService
        cls._pipeline_result_service = PipelineResultService(
            output_execution_repo=EtoSubRunOutputExecutionRepository(connection_manager),
            sub_run_repo=EtoSubRunRepository(connection_manager),
            eto_run_repo=EtoRunRepository(connection_manager),
            email_repo=EmailRepository(connection_manager),
            email_config_repo=EmailConfigRepository(connection_manager),
            module_catalog=cls.get_modules_service().catalog,
            data_database_manager=database_manager,
            pdf_storage_path=pdf_storage_path,
        )

    @classmethod
    def get_pipeline_result_service(cls) -> PipelineResultService:
        if cls._pipeline_result_service is None:
            raise RuntimeError("ServiceContainer not initialized")
        return cls._pipeline_result_service
```

---

## 11. Data Flow

### Complete Flow Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           EMAIL INGESTION                                 │
│   1. Email received → PDF extracted → ETO run created                    │
└───────────────────────────────────┬──────────────────────────────────────┘
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         TEMPLATE MATCHING                                 │
│   2. Pages analyzed → Sub-runs created (one per template match)          │
└───────────────────────────────────┬──────────────────────────────────────┘
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                            EXTRACTION                                     │
│   3. Template fields → bbox extraction → extracted_data list             │
└───────────────────────────────────┬──────────────────────────────────────┘
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                       PIPELINE EXECUTION                                  │
│   4. Transform modules execute → Data flows through DAG                   │
│   5. Output module collects inputs (no side effects)                      │
│   6. Returns: output_module_id + output_module_inputs                     │
└───────────────────────────────────┬──────────────────────────────────────┘
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                      OUTPUT EXECUTION                                     │
│   7. PipelineResultService.execute_output() called                        │
│   8. Creates eto_sub_run_output_execution record (status=pending)         │
│   9. Checks HAWB existence in database                                    │
│                                                                           │
│   Branch A: HAWB not found (CREATE)                                       │
│   10a. Calls module.create_order()                                        │
│   11a. Sends create confirmation email                                    │
│   12a. Updates record (status=success, result=...)                        │
│                                                                           │
│   Branch B: HAWB found once (UPDATE - needs approval)                     │
│   10b. Fetches existing order data for comparison                         │
│   11b. Updates record (status=awaiting_approval, existing_order_data=...) │
│   12b. Frontend displays approval UI                                      │
│   13b. User approves → calls approve_update()                             │
│   14b. Calls module.update_order()                                        │
│   15b. Sends update confirmation email                                    │
│   16b. Updates record (status=success, result=...)                        │
│   OR                                                                      │
│   13b. User rejects → calls reject_update()                               │
│   14b. Updates record (status=rejected, error_message=...)                │
│                                                                           │
│   Branch C: HAWB found multiple times (ERROR)                             │
│   10c. Updates record (status=error, error_type=multiple_hawb)            │
└───────────────────────────────────┬──────────────────────────────────────┘
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         COMPLETION                                        │
│   Sub-run marked as success/failure based on output execution result     │
│   Parent run status updated (aggregates sub-run statuses)                │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 12. File Structure

```
server/src/features/pipeline_results/
├── __init__.py
├── service.py                    # PipelineResultService
├── context.py                    # OutputExecutionContext dataclass
├── exceptions.py                 # Custom exceptions
└── helpers/
    ├── __init__.py
    ├── order_helpers.py          # OrderHelpers class
    ├── email_helpers.py          # EmailHelpers class
    └── address_helpers.py        # AddressHelpers class

server/src/api/routers/
└── output_executions.py          # API endpoints (new)
```

### Exceptions

**File:** `server/src/features/pipeline_results/exceptions.py`

```python
class OutputExecutionError(Exception):
    """Base exception for output execution errors"""
    pass


class InvalidStateError(OutputExecutionError):
    """Operation not valid for current execution state"""
    pass


class ModuleNotFoundError(OutputExecutionError):
    """Output module not found in catalog"""
    pass


class EmailConfigError(OutputExecutionError):
    """Email integration configuration not found or invalid"""
    pass


class EmailSendError(OutputExecutionError):
    """Failed to send email"""
    pass
```

---

## 13. Implementation Sequence

### Phase 1: Database & Types
1. Add new columns to `eto_sub_run_output_executions` table:
   - `action_type`
   - `hawb`
   - `existing_order_number`
   - `existing_order_data_json`
2. Update `EtoSubRunOutputExecution` dataclass with new fields
3. Update repository with new field handling

### Phase 2: Core Infrastructure
4. Create `server/src/features/pipeline_results/` directory structure
5. Implement `OutputExecutionContext` dataclass
6. Implement exceptions module
7. Implement `PipelineResultService` skeleton

### Phase 3: Helper Classes
8. Implement `OrderHelpers`:
   - `find_orders_by_hawb()`
   - `get_order_details()`
   - `generate_next_order_number()`
   - `create_order()` (basic)
   - `update_order()` (basic)
9. Implement `EmailHelpers`:
   - `send_email()`
10. Implement `AddressHelpers`:
    - `get_address_by_id()`
    - `resolve_address()`

### Phase 4: Output Module Updates
11. Update `OutputModule` ABC:
    - Add email template fields
    - Add `create_order()` abstract method
    - Add `update_order()` abstract method
12. Update `BasicOrderOutput`:
    - Define email templates
    - Implement `create_order()`
    - Implement `update_order()`

### Phase 5: Service Integration
13. Complete `PipelineResultService` implementation
14. Register in `ServiceContainer`
15. Update `EtoRunsService._process_sub_run_pipeline()` to call service

### Phase 6: API Layer
16. Create `output_executions` router with endpoints:
    - `GET /pending-approvals`
    - `GET /{id}`
    - `POST /{id}/approve`
    - `POST /{id}/reject`
17. Register router in FastAPI app

### Phase 7: Testing
18. Unit tests for helpers
19. Integration tests for service
20. End-to-end test with real ETO run

---

## Summary

The **PipelineResultService** provides a complete solution for executing output modules with full ETO context:

- **Single table** - All output execution state in `eto_sub_run_output_executions`
- **Clear state machine** - `pending` → `processing` → `success`/`error`/`awaiting_approval`
- **User approval flow** - Updates require confirmation, displayed with before/after comparison
- **Module contract** - Each output module implements `create_order()` and `update_order()`
- **Email templates** - Module-defined templates for create and update confirmations
- **Result storage** - JSON result stored for frontend display
- **Error handling** - Comprehensive error types and terminal error state

The design balances simplicity with the business requirements for order create/update flows with user confirmation.
