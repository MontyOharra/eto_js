# ETO System - TODO List

This document tracks outstanding issues and features to be implemented. Each item will be expanded with detailed requirements as we work through them.

---

## 1. Pipeline Execution Error Display

**Status:** COMPLETED

**Issue:** Errors are not being displayed on modules within the executed pipeline viewer in the ETO sub-run detail view, even though client-side support exists and works correctly in simulation mode.

**Root Cause Identified:**
Mismatch between error save format and retrieve format:

1. **Saving** (`eto_runs/service.py:1013`): Error is saved as a plain string
   ```python
   error=step_result.error  # "ValueError: some message"
   ```
   **Confirmed:** Errors ARE being saved to DB correctly as strings (verified in database query)

2. **Retrieving** (`api/mappers/eto_runs.py:340-342`): Mapper expects a dict
   ```python
   error_data = PipelineExecutionStepError(
       type=error.get("type", ""),     # Fails: string has no .get()
       message=error.get("message", ""),
       details=error.get("details"),
   )
   ```
   This raises `AttributeError` which is silently caught, resulting in `error: null` in API response.

**Solution Options:**
1. **Fix on save**: Serialize error as JSON dict `{"type": "ExceptionType", "message": "error message"}` before saving
2. **Fix on retrieve**: Handle string format in the mapper (parse "ExceptionType: message" into type/message)

**Recommended:** Option 2 - Fix on retrieve side since errors are already saved correctly as strings. Parse the string format `"ExceptionType: message"` into `{type, message}` structure.

**Files Modified:**
- `server/src/api/mappers/eto_runs.py` - Parse string error into PipelineExecutionStepError object
- `server/src/features/eto_runs/service.py` - Fixed silent error discarding in `get_sub_run_detail()` where `json.loads()` was failing on plain string errors

**Fix Applied:** Both the mapper and service now handle string error format correctly. The service preserves the original string when JSON parsing fails, and the mapper parses "ExceptionType: message" format into structured error objects.

---

## 2. Pipeline Output Visibility in ETO Details

**Status:** COMPLETED

**Issue:** Need to display pipeline output data from the list view in the ETO details page for successful sub-runs.

**Solution Applied:** Display output channel data in a 2-column grid below successful sub-runs.

**Files Modified:**
1. `server/src/shared/types/eto_sub_runs.py`
   - Added `output_channel_data: Optional[Dict[str, Any]]` field to `EtoSubRunDetailView`

2. `server/src/shared/database/repositories/eto_sub_run.py`
   - Updated `get_detail_view()` to fetch output channel data from `eto_sub_run_output_executions` table

3. `server/src/api/mappers/eto_runs.py`
   - Updated `eto_sub_run_detail_to_api()` to convert output channel data to `TransformResult` objects
   - HAWB is always displayed first, followed by other fields with proper labels

4. `client/src/renderer/features/eto/components/EtoRunDetailView/MatchedSubRunsSection.tsx`
   - Updated styling for transform results display (2-column grid with proper formatting)

---

## 3. Pending Order Conflict Resolution & Auto-Creation

**Status:** COMPLETED

**Issue:** Users need to be able to resolve field conflicts before orders auto-create in HTC.

### Current Data Model

**PendingOrderModel** - The actual order state:
- Field values (pickup_address, etc.) - NULL if no selected value (conflict)
- Status: `incomplete` → `ready` → `processing` → `created` / `failed`

**PendingOrderHistoryModel** - Audit trail:
- Each value contribution from a sub-run
- `is_selected: bool` - TRUE if this is the chosen value
- When new conflicting value arrives → existing selected gets `is_selected=FALSE`, field in pending_order set to NULL

### Status Flow

```
┌────────────┐   ┌─────────┐   ┌────────────┐   ┌─────────┐
│ incomplete │──▶│  ready  │──▶│ processing │──▶│ created │
└────────────┘   └─────────┘   └────────────┘   └─────────┘
                                     │
                                     ▼
                               ┌─────────┐
                               │ failed  │ (retryable → back to ready)
                               └─────────┘
```

**Status meanings:**
- `incomplete` - Missing required fields OR has unresolved conflicts (on ANY field)
- `ready` - All required fields present AND no unresolved conflicts → worker auto-picks up
- `processing` - Worker creating in HTC
- `created` - Done
- `failed` - HTC error, can retry

### Conflict Resolution Logic

```
1. Sub-run A contributes pickup_time="9:00"
   → History: [pickup_time="9:00", is_selected=TRUE]
   → PendingOrder: pickup_time="9:00"

2. Sub-run B contributes pickup_time="10:00" (different!)
   → History: [pickup_time="9:00", is_selected=FALSE],
              [pickup_time="10:00", is_selected=FALSE]
   → PendingOrder: pickup_time=NULL (CONFLICT!)

3. User selects "9:00" from dropdown, confirms
   → History: [pickup_time="9:00", is_selected=TRUE],
              [pickup_time="10:00", is_selected=FALSE]
   → PendingOrder: pickup_time="9:00"

4. Sub-run C contributes pickup_time="9:00" (same as selected)
   → No change, already matches selected value

5. Sub-run D contributes pickup_time="11:00" (different from selected!)
   → Conflict again! User must re-resolve
```

### Ready Status Criteria

An order transitions to `ready` (auto-create) when:
1. All **required** fields have a value (not NULL in pending_order)
2. No **unresolved conflicts** exist on ANY field (required or optional)

Conflict detection: Field has conflict if multiple history entries exist AND none have `is_selected=TRUE`

### Implementation Tasks

**Backend:**
1. Add conflict detection helper - query history to find fields with unresolved conflicts
2. Update status transition logic - after any field update, re-evaluate if order should be `ready` (check both required fields AND conflicts)
3. Add user confirmation endpoint:
   - `POST /pending-orders/{id}/confirm-field`
   - Sets `is_selected=TRUE` on chosen history entry
   - Updates field value in pending_order
   - Re-evaluates status
   - **Guard**: Reject if status is `processing`, `created`, or `failed` (race condition protection)
4. Add retry endpoint for failed orders - moves status back to `ready`

**Frontend:**
1. Update pending order detail view:
   - Show fields with their current values
   - For fields with conflicts: show dropdown with all history values
   - "Confirm" button to lock in selection
   - Dropdown remains visible after confirmation (user can change mind)
   - Disable editing if order is `processing`/`created`/`failed`
2. Handle race condition errors - if user tries to confirm but order already created, show appropriate message

### Future Consideration: Manual Approval Mode

Currently implementing auto-creation mode only. Future enhancement could add configurable manual approval mode where:
- `incomplete` → `pending_review` → `ready` (requires explicit user approval)
- Would add `pending_review` and `rejected` statuses

### Implementation Summary

**Backend:**
- `server/src/api/routers/order_management.py` - Added endpoints:
  - `GET /pending-orders` - List with conflict counts
  - `GET /pending-orders/{id}` - Detail with field history and conflict options
  - `POST /pending-orders/{id}/confirm-field` - Resolve conflicts by selecting a value
  - `POST /pending-orders/{id}/retry` - Retry failed orders
  - `POST /mock/process-output` - Mock endpoint for testing
- `server/src/api/schemas/order_management.py` - Request/response schemas
- `server/src/api/mappers/order_management.py` - Domain to API mapping with conflict options
- `server/src/features/order_management/service.py` - Business logic for conflict resolution

**Frontend:**
- `client/src/renderer/features/order-management/components/PendingOrderDetailView/` - Two-column detail view with:
  - Field list with conflict dropdowns
  - Dropdown persists after confirmation (user can change selection)
  - Confirm button appears for conflicts or when user changes confirmed value
  - Human-readable datetime formatting for time fields
  - Contributing sources panel showing PDFs that contributed data
- `client/src/renderer/pages/dashboard/orders/index.tsx` - Orders page with list/detail navigation
- `client/src/renderer/features/order-management/api/hooks.ts` - React Query hooks

---

## 4. Order Update Functionality

**Status:** COMPLETED

**Issue:** Update functionality for existing orders has not been built out.

**Details:**
- pending_updates table exists but UI workflow is incomplete
- Need UI to review proposed updates
- Approve/reject workflow for field changes
- Apply approved updates to HTC database

### Implementation Summary

**Backend:**
- `server/src/api/routers/order_management.py`:
  - `GET /pending-updates` - List pending updates with pagination and status filter
  - `GET /pending-updates/{id}` - Detail view with current HTC values vs proposed changes
  - `POST /pending-updates/{id}/approve` - Approve update (rudimentary print for now)
  - `POST /pending-updates/{id}/reject` - Reject update
  - `POST /pending-updates/{id}/confirm-field` - Resolve conflicts by selecting a value
  - Updated `/mock/process-output` to create pending updates for existing HTC orders
- `server/src/api/schemas/order_management.py` - Added schemas for pending update list/detail/actions
- `server/src/features/htc_integration/lookup_utils.py` - Added `get_order_fields()` method and `HtcOrderFields` dataclass
- `server/src/features/htc_integration/service.py` - Exposed `get_order_fields()` method

**Frontend:**
- `client/src/renderer/features/order-management/components/PendingUpdatesListTable/` - Flat list table for pending updates
- `client/src/renderer/features/order-management/components/PendingUpdateDetailView/` - Two-column detail view with:
  - Current HTC value vs Proposed value comparison
  - Conflict resolution with dropdown (persists after confirmation for re-selection)
  - Approve/Reject buttons
  - Contributing sources panel
- `client/src/renderer/features/order-management/types.ts` - Added `PendingUpdateFieldDetail` with `current_value`
- `client/src/renderer/features/order-management/api/hooks.ts` - Added hooks for pending updates
- `client/src/renderer/pages/dashboard/orders/index.tsx` - Integrated pending updates list and detail view

---

## 5. Templates Page Improvements

**Status:** COMPLETED

**Issue:** Templates page uses frontend filtering instead of backend SQL filtering, and cards are too wide.

### Implementation Summary

**Backend:**
- Added `customer_id`, `autoskip_filter`, `limit`, `offset` query params to `GET /pdf-templates`
- Added `PaginatedTemplateListResponse` schema with `items`, `total`, `limit`, `offset`
- Updated repository to filter by customer, autoskip, and apply pagination
- Returns total count for infinite scroll detection

**Frontend:**
- Implemented infinite scroll using TanStack Query's `useInfiniteQuery`
- Added autoskip filter dropdown (All Types / Processable / Auto-Skip)
- Added "Clear filters" button when filters are active
- Updated grid to 4 columns on extra-large screens (`xl:grid-cols-4`)
- URL state for filters using TanStack Router's `validateSearch`
- Removed client-side `useMemo` filtering - now handled by backend

### Previous State (for reference)
- Frontend fetches ALL templates, filters/sorts in memory with `useMemo`
- Backend already supports `status_filter`, `sort_by`, `sort_order` - but frontend doesn't use them
- Customer filter exists on frontend but backend has no customer filter support
- No pagination - loads all templates at once

### Requirements

**Backend Filtering (SQL-level):**
- Move all filtering from frontend to backend
- Add customer filter support to backend endpoint
- Add autoskip filter support to backend endpoint
- Add pagination support

**Filter Controls:**
- Status: dropdown (All / Active / Inactive) - already exists
- Customer: dropdown - already exists, needs backend support
- Autoskip: dropdown (All / Autoskip Only / Non-Autoskip)
- Sort: alphabetical by name

**Pagination:**
- Add limit/offset to backend endpoint
- Add pagination controls to frontend

**Card Layout:**
- Make cards narrower so 3 fit per row instead of 2
- Keep card view (no list/table view needed for now)

### Implementation Tasks

**Backend:**
1. Update `GET /pdf-templates` endpoint to add:
   - `customer_id` query parameter for customer filtering
   - `autoskip_filter` query parameter ("all" | "autoskip" | "non_autoskip")
   - `limit` and `offset` for pagination
   - Return total count for pagination UI
2. Update repository `list_templates()` to support new filters
3. Update service layer accordingly

**Frontend:**
1. Update `useTemplates()` hook to pass filter parameters to API
2. Remove `useMemo` filtering logic - let backend handle it
3. Add autoskip filter dropdown to page
4. Add pagination component and controls
5. Adjust card CSS to fit 3 per row (reduce max-width)

### Files to Modify

**Backend:**
- `server/src/api/routers/pdf_templates.py` - Add query parameters
- `server/src/api/schemas/pdf_templates.py` - Add response with total count
- `server/src/features/pdf_templates/service.py` - Pass new filters
- `server/src/shared/database/repositories/pdf_template.py` - SQL filtering

**Frontend:**
- `client/src/renderer/pages/dashboard/pdf-templates/index.tsx` - Remove frontend filtering, add pagination
- `client/src/renderer/features/templates/api/hooks.ts` - Pass params to API
- `client/src/renderer/features/templates/api/types.ts` - Update query params type
- `client/src/renderer/features/templates/components/TemplateCard/TemplateCard.tsx` - Adjust width

---

## 6. Pending Orders Page Improvements

**Status:** COMPLETED

**Issue:** Pending orders page needs a unified view showing both creates and updates in a single list.

### Background: Data Model

**Pending Order (Create)**
- One per unique HAWB + Customer ID combo
- Lifecycle: `incomplete` → `ready` → `processing` → `created`/`failed`
- Once `created`, this record is "done"

**Pending Update**
- One active per HAWB + Customer ID combo at a time
- Created when ETO outputs data for a combo that already exists in HTC
- Multiple field changes accumulate into the same pending update record
- When user approves/rejects → that record closes, next ETO output creates NEW pending update
- Lifecycle: `pending` → `approved`/`rejected`

**Key Constraint**: Creates and updates are mutually exclusive per combo - updates only start after create completes (or if order pre-existed in HTC).

### Design Decisions

#### Unified List View

Single list showing both creates and updates as separate rows (not tabbed):

```
| [Icon] | Type   | HAWB      | Customer | HTC Order # | Status/Fields Info              | Updated  |
|--------|--------|-----------|----------|-------------|----------------------------------|----------|
| 🟡     | CREATE | 11111111  | ABC Co   | -           | incomplete, 3/5 Req, 2 Conflicts | 5m ago   |
| 🔵     | CREATE | 22222222  | XYZ Inc  | -           | ready, 5/5 Required              | 10m ago  |
| ✓      | CREATE | 33333333  | DEF Ltd  | 54321       | created, 5/5 Required            | 1h ago   |
| 🟡     | UPDATE | 93203188  | ABC Co   | 12345       | Pending, pickup_time, addr       | 2m ago   |
| ✓      | UPDATE | 87654321  | XYZ Inc  | 67890       | Approved                         | 1h ago   |
| 🔴     | CREATE | 44444444  | GHI Inc  | -           | failed                           | 30m ago  |
```

#### Column Structure

**Common columns (both types):**
- Icon indicator (far left)
- Type (CREATE / UPDATE)
- HAWB
- Customer
- HTC Order # (shows `-` for creates until created)
- Status/Info (type-specific content)
- Last Updated
- Actions (View Details, View History)

**Create-specific info:**
- Status: incomplete / ready / processing / created / failed
- Field progress: "X/Y Required"
- Conflict count if any

**Update-specific info:**
- Decision status: Pending / Approved / Rejected
- Field names being changed (e.g., "pickup_time, delivery_addr")

#### Icon/Indicator States

| Icon | Color | Meaning | Used When |
|------|-------|---------|-----------|
| ● | Yellow | Needs user action | Conflicts to resolve, pending decision |
| ● | Red | Failure/Error | Create failed, system error |
| ● | Blue | Unread, no action needed | New data arrived, waiting for auto-process |
| ✓ | Green | Completed successfully | Order created, update approved |
| ✗ | Gray | Completed (rejected) | Update rejected |
| (none) | - | Read, no action needed | User has seen it |

#### Read/Unread Tracking

- Add `is_read` field to both `pending_orders` and `pending_updates` tables
- Marked as read when user clicks into detail view
- User can manually toggle read/unread status

#### Data Architecture

**Approach: Separate Tables + Unified Backend Endpoint**

Keep existing tables:
- `pending_orders` - add `is_read` boolean field
- `pending_updates` - add `is_read` boolean field

Create unified backend endpoint:
- `GET /api/order-management/unified-actions`
- Returns union of both tables for list display
- Supports filtering by type, status, read/unread
- Supports unified sorting across both types

### Implementation Tasks

**Backend:**

1. Add `is_read` field to `pending_orders` table
2. Add `is_read` field to `pending_updates` table
3. Create unified list endpoint that unions both tables:
   - Query params: type filter, status filter, is_read filter, sort, pagination
   - Returns normalized rows with common + type-specific fields
4. Add endpoint to mark items as read: `POST /api/order-management/mark-read`
   - Accepts: `{ type: 'create' | 'update', id: number, is_read: boolean }`
5. Update detail endpoints to auto-mark as read when fetched

**Frontend:**

1. Create new unified `OrderActionsTable` component
2. Create row components for each type with appropriate styling
3. Create icon indicator component based on state logic
4. Update hooks to use unified endpoint
5. Add read/unread toggle functionality
6. Remove old tabbed interface (PendingOrdersHeader, PendingUpdatesHeader tabs)
7. Update filters for unified view (type, status, read/unread)

### Files to Modify

**Backend:**
- `server/src/shared/database/models.py` - Add is_read fields
- `server/src/api/routers/order_management.py` - Add unified endpoint
- `server/src/api/schemas/order_management.py` - Add unified response schema
- `server/src/features/order_management/service.py` - Add unified query logic

**Frontend:**
- `client/src/renderer/pages/dashboard/orders/index.tsx` - Replace tabbed view
- `client/src/renderer/features/order-management/components/` - New unified components
- `client/src/renderer/features/order-management/api/hooks.ts` - New unified hooks
- `client/src/renderer/features/order-management/types.ts` - Unified types

### Dependencies

- **Prerequisite**: Pending Updates core system must be built and tested first
- Item 13 (SSE real-time updates) can be added after this redesign

---

## 7. Remove Pipelines Page

**Status:** COMPLETED

**Issue:** The standalone pipelines page can be removed.

**Details:**
- Pipeline management is done through template builder
- Remove route and page component
- Clean up any dead navigation links

**Implementation Summary:**
- Removed "Pipelines" tab from dashboard navigation (`route.tsx`)
- Deleted `pages/dashboard/pipelines/` directory
- Deleted unused components only used by pipelines page:
  - `PipelineCard/`
  - `PipelineViewerModal/`
  - `ExecutePipelineModal/`
- Updated `features/pipelines/components/index.ts` to remove deleted exports
- Kept components used elsewhere: PipelineGraph, PipelineEditor, PipelineBuilderModal, ExecutedPipelineGraph

---

## 8. Email Sending for Order Management

**Status:** COMPLETED

**Issue:** Need email notifications as part of order management process.

**Details:**
- Send emails on order creation
- Send emails on order updates
- Make email functionality configurable via settings page
- Consider: recipients, templates, enable/disable toggle

**Implementation Summary:**

**Architecture Changes:**
- Moved `HtcOrderWorker` from `HtcIntegrationService` to `OrderManagementService`
- Added `EmailService` dependency to `OrderManagementService`
- `HtcIntegrationService` now focuses purely on HTC database operations

**Backend Changes:**
- `server/src/features/order_management/service.py`:
  - Added worker lifecycle methods (`startup`, `shutdown`, `get_worker_status`)
  - Added worker callback methods for pending order processing
  - Added `_get_contributing_email_addresses()` - traces sub_run → eto_run → email to find sender addresses
  - Added `_get_contributing_email_addresses_for_update()` - same for pending updates
  - Added `_build_order_created_email()` - builds subject/body for create notifications
  - Added `_build_order_updated_email()` - builds subject/body for update notifications
  - Added `_send_order_notification()` - sends email using system settings sender account
  - Integrated email notifications into `_mark_pending_order_created()` callback
  - Integrated email notifications into `approve_pending_update()` method
- `server/src/features/htc_integration/service.py`:
  - Removed worker initialization, lifecycle methods, and callback methods
  - Kept HTC database operations (lookup, create, update, address management)
- `server/src/shared/services/service_container.py`:
  - Updated `order_management` service definition to include `email` service dependency
- `server/src/app.py`:
  - Changed worker startup/shutdown calls from `htc_integration_service` to `order_management_service`

**Email Notification Flow:**
1. When HTC order is created (by worker), personalized emails are sent to each sender address from contributing PDFs
2. When user approves a pending update, personalized emails are sent to each sender address from contributing PDFs
3. Each recipient receives a personalized email with their specific email received date
4. Email content:
   - Opening: "An order has been created/updated from your email sent at {date-time}. Thank you for your business."
   - Order details: HTC order number, HAWB, MAWB (if present), pickup/delivery info
   - Footer: "This is an automated notification from the Harrah Email-To-Order system."
5. Uses `email.default_sender_account_id` system setting for sender account
6. Email failures are logged but don't block order processing

---

## 9. User Activity Tracking & Audit Log

**Status:** COMPLETED

**Priority:** 1

**Design Spec:** [docs/designs/user-authentication-design.md](designs/user-authentication-design.md)

**Issue:** Need to track user actions for support and auditing purposes.

**Scope (Simplified):**
- Track only **pending update approvals** (not full audit log)
- Record `Staff_EmpID` when user approves an update
- Purpose: Update order history in main HTC system with who approved

**Authentication Approach:**
1. **Auto-auth (primary):** Check `HTC000 WhosLoggedIn` table for matching `PCName` + `PCLid`
2. **Manual login (fallback):** Username/password against `HTC000_G090_T010 Staff` table
3. **Session:** In-memory only (React Context), re-auth on each app startup
4. **Logout:** Removed - session tied to app lifecycle (auto-reauth on startup if logged into HTC)

**Key Tables (Access DB: HTC000_Data_Staff.accdb):**
- `HTC000 WhosLoggedIn` - Active sessions (read-only)
- `HTC000_G090_T010 Staff` - User credentials

**Implementation Summary:**
- Backend: Auth router (`/api/auth/auto-login`, `/api/auth/login`), Auth service with auto-login and manual login
- Frontend: Auth context with session state, Login page with auto-login attempt on mount
- Electron: IPC handler for `getMachineInfo()` returning `pcName` and `pcLid`
- Fixed nested cursor deadlock in auth service by restructuring to match HTC integration pattern
- Removed logout button (counterproductive with auto-auth)

---

## 10. Pending Update History Tracking

**Status:** COMPLETED

**Priority:** 2

**Issue:** When pending updates are approved/applied, the changes are not recorded in the order history like creations are.

**Details:**
- Order creations add records to pending_order_history tracking the data source
- Pending update approvals should similarly track which fields were updated and from what source
- Need audit trail showing: what changed, when, what was the source data

**Implementation Summary:**

**Backend Changes:**
- `AuthenticatedUser` dataclass now includes `username` (Staff_Login) for audit trail
- Auth router returns `username` in response for both auto-login and manual login
- `approve_pending_update` endpoint:
  - Accepts `approver_username` in request body
  - Fetches current HTC values before update for old/new comparison
  - Passes approver info and old/new values to HTC service
- `HtcIntegrationService.update_order()` accepts `approver_username`, `old_values`, `new_values`
- `HtcOrderUtils.create_update_history()` rewritten to:
  - Accept `updated_fields`, `old_values`, `new_values`, `user_lid` parameters
  - Use approver's username for `Orders_UpdtLID` column (falls back to `ETO_SYSTEM`)
  - Build detailed change description in format:
    ```
    Update request approved from ETO System:
    {Field Label} changed from {old_value} to {new_value},
    {Field Label} changed from {old_value} to {new_value}
    ```

**Frontend Changes:**
- `AuthUser` interface includes `username`
- Auth context stores `username` from login response
- `useApprovePendingUpdate` hook accepts `approverUsername` parameter
- Orders page passes `session.user.username` when approving updates

---

## 11. Sync Modules and Output Channels on Startup

**Status:** COMPLETED

**Priority:** 3

**Issue:** Modules and output channels need to be synced on initial server startup automatically.

**Implementation Summary:**

Added automatic sync calls in `app.py` after all services are initialized:

```python
# Sync modules and output channels to database
modules_service.sync_registry_to_database()
modules_service.sync_output_channel_types()
```

- Syncs happen after database connections and services are established
- Errors are logged but don't crash the server (graceful degradation)
- Runs before workers start, ensuring catalog is up-to-date for pipeline execution

---

## 12. Service Container Completeness Check

**Status:** COMPLETED

**Priority:** 4

**Issue:** Need to ensure all services are properly initialized and the service container is correctly built out.

**Verification Summary:**

All 12 registered services are properly initialized in `app.py`'s `initialize_services()` in correct dependency order:

| Service | Dependencies | Initialized At |
|---------|--------------|----------------|
| storage_config | (none) | Line 279 |
| modules | connection_manager | Line 286 |
| pdf_files | connection_manager, storage_config | Line 294 |
| pipeline_execution | connection_manager, data_database_manager | Line 300 |
| pipelines | connection_manager, pipeline_execution, modules, data_database_manager | Line 306 |
| pdf_templates | connection_manager, pipelines, pdf_files, pipeline_execution, data_database_manager | Line 312 |
| email | connection_manager, pdf_files, eto_runs | Line 319 |
| htc_integration | data_database_manager, connection_manager | Line 330 |
| output_processing | connection_manager, htc_integration | Line 337 |
| eto_runs | connection_manager, pdf_templates, pdf_files, pipeline_execution, output_processing | Line 344 |
| order_management | connection_manager, htc_integration, email | Line 351 |
| auth | data_database_manager | Line 358 |

**Cleanup Applied:**
- Removed redundant `_eager_load_services()` method from ServiceContainer
- Services are eagerly initialized in `app.py` before any workers start, making the separate eager loading unnecessary

---

## 14. IDE / Syntax Error Cleanup

**Status:** Not Started

**Priority:** 6

**Issue:** General cleanup of IDE warnings and syntax errors across codebase.

**Details:**
- Review TypeScript errors/warnings
- Review Python linting issues
- Fix any type mismatches
- Remove unused imports/variables

---

## 16. Access Database Concurrent Query Errors (ODBC Function Sequence Error)

**Status:** COMPLETED

**Issue:** When multiple pipeline modules attempt to query the Access database simultaneously during batch processing, ODBC "Function Sequence Error" occurs.

**Error from logs:**
```
pyodbc.Error: ('HY010', '[HY010] [Microsoft][ODBC Driver Manager] Function sequence error (0) (SQLRowCount)')
```

**Root Cause:**
- Access databases via pyodbc do not handle concurrent queries well on a shared connection
- When Dask executes multiple pipeline modules in parallel, they all try to use the same Access connection
- This causes cursor conflicts and "function sequence errors"

**Solution Applied:** Serialize Access DB queries using threading lock

**Files Modified:**
1. `server/src/shared/database/access_connection.py`
   - Added `with self._lock:` around cursor operations in the `cursor()` context manager
   - All Access DB operations are now serialized to prevent concurrent access errors

2. `server/src/shared/database/data_database_manager.py`
   - Changed `get_connection()` to return `AccessConnectionManager` instance instead of raw pyodbc connection
   - Ensures pipeline modules use the thread-safe `cursor()` method

---

## 17. Pending Orders Page Real-Time Updates & Navigation Preservation

**Status:** COMPLETED

**Issue:** The pending orders page does not receive real-time updates when the ETO system modifies pending orders, and navigation between list/detail views resets state.

### Current ETO Page Pattern (Reference Implementation)

The ETO page (`client/src/renderer/pages/dashboard/eto/index.tsx`) implements two key patterns that the pending orders page should follow:

#### 1. SSE (Server-Sent Events) for Real-Time Updates

**Hook:** `useEtoEvents` (`client/src/renderer/features/eto/hooks/useEtoEvents.ts`)

- Connects to SSE endpoint `/api/eto-runs/events`
- Automatically reconnects on connection loss (3-second delay)
- Handles event types: `run_created`, `run_updated`, `run_deleted`, `sub_run_updated`, etc.
- Invalidates TanStack Query caches when events received, triggering automatic refetch
- Fallback polling interval (default 10 seconds) in case SSE events are missed
- Disables fallback polling when in detail view (list is hidden anyway)

**Backend:** SSE endpoint broadcasts events when:
- New runs/sub-runs are created
- Run/sub-run status changes
- Runs are deleted

#### 2. Navigation State Preservation

**Pattern:** List view is kept mounted but hidden when detail view is open

```tsx
{/* Detail view - shown when a run is selected */}
{selectedRunId && (
  <EtoRunDetailViewWrapper runId={selectedRunId} onBack={handleBackToList} />
)}

{/* List view - kept mounted but hidden when detail view is open to preserve scroll position */}
<div className={`h-full flex flex-col overflow-hidden ${selectedRunId ? 'hidden' : ''}`}>
  {/* ... list content ... */}
</div>
```

This approach:
- Preserves scroll position in the list when returning from detail
- Keeps filter/pagination state intact
- Avoids re-fetching list data when navigating back
- Uses CSS `hidden` class rather than conditional rendering

### Implementation Tasks for Pending Orders

**Backend:**

1. Create SSE endpoint for pending orders: `GET /api/order-management/events`
   - Event types needed:
     - `pending_order_created` - New pending order created
     - `pending_order_updated` - Status change, field update, conflict resolution
     - `pending_order_deleted` - Order removed
     - `pending_update_created` - New pending update for existing HTC order
     - `pending_update_resolved` - Update approved/rejected

2. Emit events from relevant services:
   - `OutputProcessingService` - when processing creates/updates pending orders
   - `OrderManagementService` - when user confirms fields, resolves conflicts
   - `HtcIntegrationService` - when HTC order creation succeeds/fails
   - Background worker - when auto-creating orders

**Frontend:**

1. Create `usePendingOrderEvents` hook (similar to `useEtoEvents`):
   - Connect to SSE endpoint
   - Handle reconnection logic
   - Invalidate `pendingOrdersQueryKeys` on relevant events
   - Support fallback polling
   - Export from `features/order-management/hooks/index.ts`

2. Update query keys structure in `features/order-management/api/hooks.ts`:
   - Ensure proper key hierarchy for granular invalidation
   - `pendingOrdersQueryKeys.lists()` - for list invalidation
   - `pendingOrdersQueryKeys.detail(id)` - for detail invalidation

3. Update `pages/dashboard/orders/index.tsx`:
   - Add `usePendingOrderEvents` hook
   - Change detail/list rendering to use hidden pattern instead of conditional rendering
   - Preserve scroll position and filter state

### Files to Create

- `server/src/api/routers/order_management_events.py` - SSE endpoint
- `client/src/renderer/features/order-management/hooks/usePendingOrderEvents.ts` - SSE hook

### Files to Modify

**Backend:**
- `server/src/features/output_processing/service.py` - Emit events on pending order changes
- `server/src/features/order_management/service.py` - Emit events on user actions
- `server/src/features/htc_integration/service.py` - Emit events on HTC operations
- `server/src/api/routers/__init__.py` - Register new events router

**Frontend:**
- `client/src/renderer/features/order-management/api/hooks.ts` - Add/update query keys
- `client/src/renderer/features/order-management/hooks/index.ts` - Export new hook
- `client/src/renderer/features/order-management/index.ts` - Re-export hook
- `client/src/renderer/pages/dashboard/orders/index.tsx` - Integrate SSE and fix navigation

---

## 18. Attachment Processing

**Status:** COMPLETED

**Priority:** TBD

**Issue:** Need to store PDF attachments in HTC database and create records linking PDFs to orders.

**Details:**
- Store full PDF files (all pages, not just matched pages) associated with sub-runs that contributed to an order
- Create records in the PDF-to-order relationship table in HTC database
- Get all PDF files from sub-runs that contributed to the pending order/update

**Implementation:**
- Created `AttachmentManager` class in `server/src/features/htc_integration/attachment_utils.py`
- Builds HTC attachment path: `{HTC_APPS_DIR}/HTCAttach-{CoID}-{BrID}/Co{CoID}Br{BrID}/Cust{CustID}/Order_{OrderNo}/`
- Builds attachment filename: `{original}.{hawb}.{MM-DD-YYYY}_{HH-MM-SS}.pdf`
- Copies PDFs from ETO storage to HTC attachment storage
- Creates records in `HTC300_G040_T014A Open Order Attachments` table
- Integrated into order creation flow via `_mark_pending_order_created()`
- Added `_get_contributing_pdf_files()` to trace PDF sources from pending order history

---

## 19. Multi-HAWB Support (List Types in Pipelines)

**Status:** COMPLETED

**Issue:** Need ability for a single PDF to create/update multiple orders when it contains multiple HAWBs.

**Implementation Summary:**

**Server-Side:**
- Added `list[str]` to `AllowedNodeType` and `ALLOWED_PIN_TYPES`
- Added `list[str]` to `OutputChannelDataType` and API schemas
- Added `hawb_list` output channel (list[str] type) as alternative to `hawb`
- Updated `_extract_hawbs()` to check both `hawb` and `hawb_list` channels with deduplication
- Updated pipeline validation to require at least one HAWB channel (either `hawb` or `hawb_list`)
- Created Text Splitter module that splits text by delimiter into `list[str]`
  - Supports escape sequences (`\n`, `\t`, `\r`)
  - Options: strip_parts, remove_empty

**Client-Side:**
- Added amber color for `list[str]` type to `TYPE_COLORS`
- Added `list[str]` to TypeIndicator fallback types

**Usage:**
1. Use Text Splitter module to split multi-HAWB text by newline or comma
2. Connect Text Splitter output to `hawb_list` output channel
3. Each HAWB creates a separate output execution and order

---

## 20. Manual Order Creation Mode (Auto-Creation Toggle)

**Status:** COMPLETED

**Priority:** TBD

**Issue:** Need ability to disable automatic order creation via a settings toggle.

**Implementation Summary:**

**Backend:**
- Added `order_management.auto_create_enabled` setting key
- Added `GET /api/settings/order-management` endpoint
- Added `PUT /api/settings/order-management` endpoint
- Added `is_auto_create_enabled_callback` to HTC order worker
- Worker checks setting before processing each batch

**Frontend:**
- Added "Order Processing" section to Settings page
- Toggle switch for "Automatic Order Creation"
- Immediate save on toggle with success/error feedback
- Status indicator shows current mode

**Behavior:**
- Default: Auto-create **enabled** (backwards compatible)
- When disabled: Orders stay in "ready" status, worker skips processing
- When enabled: Normal automatic order creation

**Note:** Manual "Create Order" button for individual orders not yet implemented - orders remain in ready status until setting is re-enabled. Consider adding a bulk "Create All Ready Orders" action in the future.

---

## 21. Dimensions Table Handling

**Status:** COMPLETED (basic implementation)

**Priority:** TBD

**Issue:** Dimensions (pieces, weight, dims) need proper handling via the HTC dims table.

**Phase 1 - Cleanup (COMPLETED):**
Removed placeholder pieces/weight fields that were incorrectly implemented:
- Removed from database models (PendingOrderModel, PendingUpdateModel)
- Removed from types (PendingOrder, PendingUpdate, PendingOrderUpdate, etc.)
- Removed from HTC integration (create_order, update_order, get_order_fields)
- Removed create_dimension_record and update_dimension_record methods
- Removed from API schemas and email notifications

**Phase 2 - Proper Dims System (COMPLETED):**
Implemented basic dims handling with full replacement strategy:

**Backend:**
- Added `dims` field to `PendingOrderModel` and `PendingUpdateModel` (JSON text)
- Added `DimObject` TypedDict and `dims` to pending order/update types
- Added `dims` to `VALID_FIELD_NAMES` for field validation
- `HtcOrderUtils`: Added `create_dims_records()`, `delete_dims_records()`, `replace_dims_records()`
- `HtcLookupUtils`: Added `dims` field to `HtcOrderFields`, updated `get_order_fields()` to query dims table
- `HtcIntegrationService`: Updated `create_order()` and `update_order()` to handle dims
- `OutputProcessingService`: Added JSON serialization for dims in `_extract_valid_fields()`
- Order update history: Human-readable dims format ("Removed Dim #1: 2 - 10x12x8 @ 25lbs. Added Dim #1: ...")

**Frontend:**
- Added dims formatting to `PendingOrderDetailView` and `PendingUpdateDetailView`
- Added dims formatting to `MatchedSubRunsSection` and `SummarySuccessView`
- Format: `qty - HxLxW @ weightlbs` (e.g., "2 - 10x12x8 @ 25lbs")

**New Pipeline Modules (untracked):**
- `dim_builder.py` - Builds a single dim object from height/length/width/qty/weight
- `dim_list_collector.py` - Collects multiple dim objects into a list

**Current Behavior:**
- Dims are stored as JSON array in pending orders/updates
- On order creation: dims records are inserted into HTC dims table
- On order update: existing dims are deleted and replaced with new dims (full replacement)
- Conflicts work the same as other fields (dropdown selection)

**Future Improvements:**
- More granular dim updates (add/remove individual dims instead of full replacement)
- Dim-level conflict resolution
- Support for partial dim updates

---

## 23. Individual Field Approvals for Updates

**Status:** Not Started

**Priority:** TBD

**Issue:** Currently pending updates are all-or-nothing (approve or reject entire update). Users need ability to accept or reject individual field changes within an update.

**Details:**
- Allow user to approve/reject individual fields within a pending update
- Partial approvals - accept some field changes, reject others
- Only approved fields get written to HTC
- Rejected fields are discarded but update can still complete with approved subset

---

## 24. Manual Approval Mode for Order Creation

**Status:** In Progress

**Priority:** TBD

**Issue:** Manual approval mode exists but UI needs improvement.

**Current State:**
- Backend supports manual approval/rejection of pending orders
- Basic UI exists but needs refinement

**UI Improvements Needed:**
- TBD (exploring current implementation)

---

## 25. Auto-Approve Setting for Updates

**Status:** Not Started

**Priority:** TBD

**Issue:** Need ability to auto-approve pending updates similar to how auto-create works for new orders.

**Details:**
- Add `order_management.auto_approve_updates` setting
- When enabled, pending updates are automatically approved and applied to HTC
- When disabled, updates require manual user approval (current behavior)
- Worker checks setting before processing updates
- Symmetry with order creation auto/manual modes

---

## 22. Email Recovery When WiFi Disconnects

**Status:** COMPLETED

**Issue:** When the server loses WiFi connectivity, email fetching fails and needs to recover gracefully when connection is restored.

**Implementation Summary:**
- Added `TransientEmailError` and `PermanentEmailError` exception classes
- Connection errors (socket/SSL) trigger reconnection on next poll cycle
- Transient errors no longer count toward deactivation - just log and retry
- Keepalive sets `self._imap = None` when NOOP fails
- Added `_is_connection_error()` and `_handle_connection_error()` helpers
- Deactivation only happens for permanent errors (auth failure, folder doesn't exist)

---

## 26. Order Management SSE Stream & Polling Improvements

**Status:** Not Started

**Priority:** TBD

**Issue:** The SSE event stream for the order management page is unreliable - some backend functions don't properly broadcast events to update the stream.

**Details:**

**SSE Broadcast Gaps:**
- Some service methods that modify pending orders/updates don't emit SSE events
- Need to audit all order management service methods to ensure proper event broadcasting
- Compare with ETO runs SSE implementation for consistency

**Frontend Polling Fallback:**
- Add regular polling to order management page (like ETO runs page does)
- ETO page uses fallback polling interval (default 10 seconds) in case SSE events are missed
- Order management page should implement the same pattern for reliability
- Disable polling when in detail view (list is hidden anyway)

**Files to Audit:**
- `server/src/features/order_management/service.py` - Check all methods that modify state
- `server/src/features/output_processing/service.py` - Check pending order/update creation
- `server/src/api/routers/order_management.py` - Check endpoint event emissions
- `client/src/renderer/features/order-management/hooks/usePendingOrderEvents.ts` - Add polling fallback

---

## 27. Retry Failed Order Creation from Orders Page

**Status:** Not Started

**Priority:** TBD

**Issue:** When a pending order is in the `failed` state, users must go to the ETO runs page, reprocess from there, and then retry order creation. This is cumbersome.

**Details:**
- Add a "Retry" button on the pending order detail view when status is `failed`
- Allow immediate retry of order creation without navigating to ETO runs page
- Should call the same logic as the existing retry mechanism but from the orders page context

---

## 28. DateTime Extractor Module - Always Output Both Values

**Status:** COMPLETED

**Priority:** TBD

**Issue:** The datetime extractor module should always output both datetime values on every run, using defaults when it cannot determine the correct value.

**Solution:**
- Updated the LLM prompt to never return null values
- Added rule: "NEVER return null. Always provide a best guess for date, start_time, and end_time."
- Added fallback: "Date missing: use today's date"
- Removed contradicting "Use null if unknown" instruction

---

## 29. Template Builder Test Summary - Show Output Values

**Status:** Not Started

**Priority:** TBD

**Issue:** The summary section of the testing step in the template builder needs to display the extracted values in the left pane, similar to how the ETO sub-run modal displays results.

**Details:**
- Update the template builder test summary view
- Show output values in the left pane during testing
- Match the presentation style of the ETO sub-run detail modal
- Helps users verify extraction results during template development

---

## 30. View Email Account Connection Details in Settings

**Status:** Not Started

**Priority:** TBD

**Issue:** Need ability to view email account connection details (IMAP/SMTP host, port, etc.) from the frontend settings page.

**Details:**
- Click on an email account in the Settings page to view its connection details
- Display IMAP host, port, SMTP host, port, email address, SSL settings
- Read-only view of current configuration
- Helps with debugging connection issues

---

## Priority Notes

_To be determined as we review each item._

---

## Completed Items

_Items will be moved here as they are completed._
