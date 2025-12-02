# Output Module Implementation - Session Continuity

**Date:** 2025-12-02
**Status:** In Progress

---

## What We're Building

A new **Output Module** system that separates pipeline data transformation from order creation side effects.

### Architecture Overview

```
Pipeline Execution
    ↓
Output Module (collects data, no side effects)
    ↓
OutputExecutionService (has full context: ETO run, PDF file, email service, HTC database)
    ↓
- Create/update orders
- Transfer PDF to HTC storage
- Create attachment records
- Send confirmation emails
```

### Why This Design?

1. Pipeline modules don't have access to ETO run context, PDF files, or external services
2. Order creation needs to: check if HAWB exists, transfer PDF attachments, send emails
3. Output modules act as "exit points" that collect transformed data
4. A separate service executes the actual side effects with full system access

---

## Completed Work

### 1. Design Decisions Made

- Output modules extend `OutputModule` base class (new `ModuleKind.OUTPUT`)
- Output modules define inputs but have no outputs (terminal nodes)
- `OutputExecutionService` handles all side effects with handlers per module type
- Service has shared utilities: `_find_order_by_hawb`, `_create_order`, `_transfer_pdf_to_htc`, etc.

### 2. Files Created

| File | Status | Description |
|------|--------|-------------|
| `server/src/pipeline_modules/output/__init__.py` | ✅ Created | Output modules package |
| `server/src/pipeline_modules/output/basic_order_output.py` | ✅ Created | First output module |
| `docs/output-module-implementation.md` | ✅ Created | Implementation guide with copy/paste code |

### 3. Files Modified

| File | Status | Change |
|------|--------|--------|
| `server/src/shared/types/modules.py` | ✅ Done | Added `OUTPUT = "output"` to `ModuleKind` enum |
| `server/src/shared/types/modules.py` | ❌ Pending | Add `OutputModule` base class |
| `server/src/shared/types/__init__.py` | ❌ Pending | Export `OutputModule` |

---

## Where to Pick Up

### Immediate Next Steps

1. **Add `OutputModule` base class to `modules.py`**
   - See `docs/output-module-implementation.md` section 1 for the code
   - Insert after `MiscModule` class, before `ModuleCreate` dataclass

2. **Update `shared/types/__init__.py`** to export `OutputModule`

3. **Verify the module loads** by running the server

### Then Build the Service

4. **Create `OutputExecutionService`** at `server/src/features/output_execution/service.py`
   - Shared utilities for order operations
   - Handler for `basic_order_output` module
   - Integration with ETO run processing

5. **Modify pipeline execution** to collect output module data instead of executing them

---

## BasicOrderOutput Schema

**Required Inputs:**
- `customer_id` (int)
- `hawb` (str)
- `pickup_date` (date)
- `pickup_time_start` (time)
- `pickup_time_end` (time)
- `pickup_address_id` (int, optional) OR `pickup_address_text` (str, optional)
- `delivery_date` (date)
- `delivery_time_start` (time)
- `delivery_time_end` (time)
- `delivery_address_id` (int, optional) OR `delivery_address_text` (str, optional)

**Optional Inputs:**
- `mawb` (str)
- `pickup_notes` (str)
- `delivery_notes` (str)
- `order_notes` (str)

**Address Resolution:**
- If `*_address_id` provided → use existing address
- If `*_address_text` provided → parse and create new address
- XOR validation happens in the service handler

---

## Key Files to Reference

- `docs/output-module-implementation.md` - Copy/paste code for implementation
- `server/src/pipeline_modules/output/basic_order_output.py` - The output module
- `server/src/shared/types/modules.py` - Base classes and `ModuleKind` enum
- `server/src/features/pipeline_execution/service.py` - Where output collection will happen

---

## Future Output Modules (Planned)

| Module | Purpose |
|--------|---------|
| `mawb_hawb_linker` | Links multiple HAWBs to a single MAWB |
| `dims_order_output` | Order with dimension records (after array types added) |
