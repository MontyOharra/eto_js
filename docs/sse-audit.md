# SSE Event Stream Audit - Order Management

This document tracks the audit of SSE (Server-Sent Events) broadcasts for pending orders and pending updates. The goal is to identify all functions that modify pending orders/updates and ensure they properly broadcast events to the event stream.

## Related TODO Item

**#26 - Order Management SSE Stream & Polling Improvements**

## Services to Audit

### 1. Order Management Service
| File | Status |
|------|--------|
| `server/src/features/order_management/service.py` | Not Started |

### 2. ETO Runs Service
| File | Status |
|------|--------|
| `server/src/features/eto_runs/service.py` | Not Started |
| `server/src/features/eto_runs/utils/eto_worker.py` | Not Started |
| `server/src/features/eto_runs/utils/extraction.py` | Not Started |

### 3. Output Processing Service
| File | Status |
|------|--------|
| `server/src/features/output_processing/service.py` | Not Started |

---

## Audit Results

### order_management/service.py

#### Functions that SHOULD broadcast SSE events (modify pending orders/updates)

| Function | Modifies | Currently Broadcasts? | Event Type |
|----------|----------|----------------------|------------|
| `resolve_conflicts` | pending_order status/fields | ✅ YES | `pending_order_updated` |
| `approve_pending_order` | pending_order status → 'created' | ❌ NO | - |
| `reject_pending_order` | pending_order status → 'rejected' | ✅ YES | `pending_order_resolved` |
| `create_pending_order_now` | pending_order (calls mark_* methods) | ✅ (via callbacks) | - |
| `_update_pending_order_status` | pending_order status | ❌ NO | - |
| `approve_pending_update` | pending_update status → 'applied' | ❌ NO | - |
| `reject_pending_update` | pending_update status → 'rejected' | ✅ YES | `pending_update_resolved` |
| `_mark_pending_order_processing` | pending_order status → 'processing' | ❌ NO | - |
| `_mark_pending_order_created` | pending_order status → 'created' | ✅ YES | `pending_order_updated` |
| `_mark_pending_order_failed` | pending_order status → 'failed' | ✅ YES | `pending_order_updated` |
| `_convert_pending_order_to_update` | creates pending_update | ✅ YES | `pending_update_created` |
| `retry_pending_order` | pending_order status → 'ready' | ❌ NO | - |

#### Functions that do NOT need SSE broadcasts (read-only, helpers, lifecycle)

| Function | Reason |
|----------|--------|
| `__init__` | Initialization only |
| `_is_auto_create_enabled` | Read-only (settings check) |
| `get_pending_orders` | Read-only (list query) |
| `get_pending_order_detail` | Read-only (detail query) |
| `_build_contributing_sources` | Helper (builds data structure) |
| `_build_fields_with_options` | Helper (builds data structure) |
| `_build_htc_order_data` | Helper (builds data structure) |
| `_has_unresolved_conflicts` | Read-only (conflict check) |
| `get_pending_updates` | Read-only (list query) |
| `startup` | Worker lifecycle |
| `shutdown` | Worker lifecycle |
| `get_worker_status` | Read-only (status check) |
| `_get_ready_pending_orders` | Read-only (worker callback) |
| `_create_htc_order_by_id` | Orchestrator (calls other methods that broadcast) |
| `_dims_are_equal` | Helper (comparison logic) |
| `_get_contributing_email_details` | Read-only (email lookup) |
| `_get_contributing_email_details_for_update` | Read-only (email lookup) |
| `_get_contributing_pdf_files` | Read-only (PDF lookup) |
| `_build_order_created_email` | Helper (builds email content) |
| `_build_order_updated_email` | Helper (builds email content) |
| `_send_order_notification` | Side effect (email sending, not order state) |
| `_send_order_created_notification` | Side effect (email sending, not order state) |
| `_send_order_updated_notification` | Side effect (email sending, not order state) |

#### Summary - Missing Broadcasts

| Function | Missing Event | Suggested Event Type |
|----------|---------------|---------------------|
| `approve_pending_order` | Status change to 'created' | `pending_order_resolved` |
| `_update_pending_order_status` | Status change (ready/incomplete) | `pending_order_updated` |
| `approve_pending_update` | Status change to 'applied' | `pending_update_resolved` |
| `_mark_pending_order_processing` | Status change to 'processing' | `pending_order_updated` |
| `retry_pending_order` | Status change to 'ready' | `pending_order_updated` |

---

### eto_runs/service.py

**Functions:**
_(To be populated)_

---

### eto_runs/utils/eto_worker.py

**Functions:**
_(To be populated)_

---

### eto_runs/utils/extraction.py

**Functions:**
_(To be populated)_

---

### output_processing/service.py

**Functions:**
_(To be populated)_

---

## Summary

| Service | Functions Audited | Broadcasts Missing | Fixed |
|---------|-------------------|-------------------|-------|
| order_management/service.py | 0 | 0 | 0 |
| eto_runs/service.py | 0 | 0 | 0 |
| eto_runs/utils/eto_worker.py | 0 | 0 | 0 |
| eto_runs/utils/extraction.py | 0 | 0 | 0 |
| output_processing/service.py | 0 | 0 | 0 |
| **Total** | 0 | 0 | 0 |
