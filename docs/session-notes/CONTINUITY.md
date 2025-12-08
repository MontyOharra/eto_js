# Session Continuity Document

## Current Status (2025-12-08)

### Session Summary

This session completed the **customer_id integration for templates** and analyzed the **output channel processing architecture** for crash resilience.

---

## Recently Completed

### 1. Customer ID Feature (Complete & Pushed)

Added full customer_id support to templates with name display across the application.

**Backend Changes:**
- `GET /api/pdf-templates/customers` - Fetch customers from Access DB
- `customer_name` field added to template API responses (list and detail)
- `customer_name` added to ETO sub-run API responses
- `_get_customer_name()` and `_get_customer_names()` helper methods in PdfTemplateService
- `template_customer_id` added to `EtoSubRunDetailView` domain type
- Repository joins to get customer_id from pdf_templates table

**Frontend Changes:**
- `CustomerSelect` dropdown component for template builder
- `useCustomers` hook for fetching customer list
- Fixed customer_id not being saved (was missing from 3 API call locations)
- Customer name displayed on: template cards, detail modal, ETO sub-run sections

**Commit:** `2fb6b0b` - "feat: Add customer name display and selection for templates"

### 2. Output Channel Processing Design Analysis

Analyzed how the two design documents fit together:
- `pipeline-result-service-design.md` - Per-sub-run execution tracking
- `pending-orders-system-v2.md` - Order aggregation by HAWB

**Key Insight:** Crash resilience is achieved via `eto_sub_run_output_executions` table:
1. Pipeline completes → Create execution record (status='pending')
2. Store output_channel_values in input_data_json
3. If crash → Record survives in database
4. On recovery → Query pending records and resume

**Updated:** `docs/designs/pending-orders-system-v2.md` with System Integration section.

---

## Architecture Notes

### Two-System Integration for Output Processing

```
Pipeline Execution Completes
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  eto_sub_run_output_executions (status=pending)                  │
│  - Stores output_channel_values in input_data_json              │
│  - CRASH-SAFE: Record persists before processing begins         │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  Check HAWB in HTC Access Database                              │
│                                                                  │
│  HAWB exists → Create pending_updates (queue for review)        │
│  HAWB not found → Add to pending_order + pending_order_history  │
│       └── If all required fields → Auto-create in HTC           │
└─────────────────────────────────────────────────────────────────┘
```

### Customer Name Lookup Pattern

Customer names come from Access DB, not SQLite. Pattern used:
1. Repository joins get `customer_id` from pdf_templates
2. Router calls `service._get_customer_names([ids])` to batch-fetch names
3. Mapper receives customer_names dict and includes in API response

---

## Important Files Reference

### Customer Feature (This Session)
```
# Backend
server/src/api/routers/pdf_templates.py          # /customers endpoint, name lookup
server/src/api/routers/eto_runs.py               # Customer names for sub-runs
server/src/features/pdf_templates/service.py     # _get_customer_name methods
server/src/shared/database/repositories/eto_sub_run.py  # Join for customer_id

# Frontend
client/src/renderer/features/templates/components/TemplateBuilder/CustomerSelect.tsx
client/src/renderer/features/templates/api/hooks.ts  # useCustomers hook
```

### Output Processing Design
```
docs/designs/pending-orders-system-v2.md         # Updated with integration section
docs/pipeline-result-service-design.md           # Original execution service design
```

---

## Next Session Priorities

### High Priority: Implement Pending Orders Backend

1. **Database Tables** - Create SQLite tables:
   ```sql
   pending_orders           -- Order state aggregation
   pending_order_history    -- Field contribution tracking
   pending_updates          -- Proposed changes for existing orders
   ```

2. **PendingOrdersService** - Core logic:
   - `handle_output_channels()` - Main entry point
   - `add_field_contribution()` - Add data to pending order
   - `get_field_state()` - Compute field state from history
   - `create_order_in_htc()` - Auto-create when ready

3. **Integration Point** - Call after pipeline execution:
   ```python
   if execution_result.output_channel_values:
       execution = output_execution_repo.create(...)  # Crash-safe record
       pending_orders_service.handle_output_channels(...)
   ```

4. **Crash Recovery** - On server startup:
   ```python
   pending = output_execution_repo.get_by_status(['pending', 'processing'])
   for execution in pending:
       process_output_execution(execution)
   ```

### Medium Priority

5. **API Endpoints**:
   - `GET/POST /api/pending-orders/*`
   - `GET/POST /api/pending-updates/*`

6. **Frontend Connection** - Orders page exists but needs real API

---

## Implementation Status

| Layer | Status | Notes |
|-------|--------|-------|
| Output channels in pipeline | ✅ Done | `output_channel_values` collected |
| Customer ID on templates | ✅ Done | Full CRUD + display |
| Customer name in ETO sub-runs | ✅ Done | Shown in matched templates |
| `eto_sub_run_output_executions` table | ⚠️ Exists | May need fields for pending orders |
| `pending_orders` table | ❌ Not created | New SQLite table needed |
| `pending_order_history` table | ❌ Not created | New SQLite table needed |
| `pending_updates` table | ❌ Not created | New SQLite table needed |
| PendingOrdersService | ❌ Not implemented | Bridges pipeline → pending orders |
| Crash recovery on startup | ❌ Not implemented | Query and resume pending |

---

## Testing Commands

```bash
# Verify customer dropdown works
curl http://localhost:8000/api/pdf-templates/customers

# Check template includes customer_name
curl http://localhost:8000/api/pdf-templates/1

# View design doc
cat docs/designs/pending-orders-system-v2.md
```

---

## Open Questions for Next Session

1. **Required fields for auto-creation** - Is this list correct?
   ```python
   REQUIRED_FIELDS = [
       'pickup_address', 'pickup_time_start', 'pickup_time_end',
       'delivery_address', 'delivery_time_start', 'delivery_time_end',
   ]
   ```

2. **HAWB format** - What do real HAWBs look like for test data?

3. **PendingOrdersService vs PipelineResultService** - Keep separate or merge?

---

**Last Updated:** 2025-12-08
**Next Session:** Implement pending orders database tables and service layer

**Key Commits This Session:**
- `2fb6b0b` - feat: Add customer name display and selection for templates
