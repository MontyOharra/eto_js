# Pending Actions Mock Endpoint Test Commands

This document contains curl commands for testing the pending actions system via the mock endpoint.

## Test Data Reference

Existing orders in the system:
- Customer ID: 195, HAWB: 00455367, MAWB: 94618349
- Customer ID: 195, HAWB: 00455432, MAWB: 35179491
- Customer ID: 18, HAWB: 2725971, MAWB: null

---

## UPDATES - Existing Orders

### 1. Update Without Conflicts - Single field change
Customer 195, HAWB 00455367

```bash
curl -X POST "http://localhost:8000/api/pending-actions/mock" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": 195,
    "hawb": "00455367",
    "output_channel_data": {
      "pickup_notes": "Please call ahead 30 minutes before arrival"
    },
    "pdf_filename": "update_single_field.pdf"
  }'
```

### 2. Update With Conflicts - Two different values for same field
Customer 195, HAWB 00455432 (run both to create conflict)

```bash
# First value
curl -X POST "http://localhost:8000/api/pending-actions/mock" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": 195,
    "hawb": "00455432",
    "output_channel_data": {
      "delivery_notes": "Dock 5 - Loading bay B"
    },
    "pdf_filename": "update_conflict_1.pdf"
  }'

# Second conflicting value (different source)
curl -X POST "http://localhost:8000/api/pending-actions/mock" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": 195,
    "hawb": "00455432",
    "output_channel_data": {
      "delivery_notes": "Use rear entrance - Dock 3"
    },
    "pdf_filename": "update_conflict_2.pdf"
  }'
```

### 3. Update With Same Values as HTC - Should be filtered out in detail view
Customer 18, HAWB 2725971

```bash
curl -X POST "http://localhost:8000/api/pending-actions/mock" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": 18,
    "hawb": "2725971",
    "output_channel_data": {
      "mawb": null
    },
    "pdf_filename": "update_same_value.pdf"
  }'
```

### 4. Update With Multiple Fields (no conflicts)
Customer 195, HAWB 00455367

```bash
curl -X POST "http://localhost:8000/api/pending-actions/mock" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": 195,
    "hawb": "00455367",
    "output_channel_data": {
      "order_notes": "Priority shipment - handle with care",
      "delivery_notes": "Security clearance required"
    },
    "pdf_filename": "update_multiple_fields.pdf"
  }'
```

---

## CREATES - New Orders

### 5. Create With Full Required Fields - Single pass complete
New HAWB TEST-FULL-001

```bash
curl -X POST "http://localhost:8000/api/pending-actions/mock" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": 195,
    "hawb": "TEST-FULL-001",
    "output_channel_data": {
      "pickup_company_name": "ABC Logistics Warehouse",
      "pickup_address": "123 Industrial Blvd, Newark, NJ 07102",
      "pickup_time_start": "2024-02-15 09:00:00",
      "pickup_time_end": "2024-02-15 12:00:00",
      "delivery_company_name": "XYZ Distribution Center",
      "delivery_address": "456 Commerce Way, Edison, NJ 08817",
      "delivery_time_start": "2024-02-15 14:00:00",
      "delivery_time_end": "2024-02-15 17:00:00"
    },
    "pdf_filename": "create_full_required.pdf"
  }'
```

### 6. Create With Full Required + Optional Fields
New HAWB TEST-FULL-OPT-001

```bash
curl -X POST "http://localhost:8000/api/pending-actions/mock" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": 195,
    "hawb": "TEST-FULL-OPT-001",
    "output_channel_data": {
      "pickup_company_name": "Global Freight Inc",
      "pickup_address": "789 Airport Road, Newark, NJ 07114",
      "pickup_time_start": "2024-02-16 08:00:00",
      "pickup_time_end": "2024-02-16 10:00:00",
      "pickup_notes": "Ask for Mike at receiving",
      "delivery_company_name": "Metro Retail Hub",
      "delivery_address": "321 Main Street, New York, NY 10001",
      "delivery_time_start": "2024-02-16 13:00:00",
      "delivery_time_end": "2024-02-16 16:00:00",
      "delivery_notes": "Freight elevator access code: 4521",
      "mawb": "MAWB-98765432",
      "order_notes": "Fragile electronics - no stacking",
      "dims": [
        {"length": 24, "width": 18, "height": 12, "qty": 2, "weight": 45},
        {"length": 36, "width": 24, "height": 24, "qty": 1, "weight": 120}
      ]
    },
    "pdf_filename": "create_full_with_optional.pdf"
  }'
```

### 7. Create Requiring Multiple Passes - Partial data first
New HAWB TEST-PARTIAL-001

```bash
# First pass - only pickup info
curl -X POST "http://localhost:8000/api/pending-actions/mock" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": 195,
    "hawb": "TEST-PARTIAL-001",
    "output_channel_data": {
      "pickup_company_name": "First Source Warehouse",
      "pickup_address": "100 First Ave, Jersey City, NJ 07302",
      "pickup_time_start": "2024-02-17 10:00:00",
      "pickup_time_end": "2024-02-17 12:00:00"
    },
    "pdf_filename": "create_partial_pass1.pdf"
  }'

# Second pass - add delivery info (completes the order)
curl -X POST "http://localhost:8000/api/pending-actions/mock" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": 195,
    "hawb": "TEST-PARTIAL-001",
    "output_channel_data": {
      "delivery_company_name": "Final Destination Corp",
      "delivery_address": "200 Second St, Hoboken, NJ 07030",
      "delivery_time_start": "2024-02-17 14:00:00",
      "delivery_time_end": "2024-02-17 17:00:00"
    },
    "pdf_filename": "create_partial_pass2.pdf"
  }'
```

### 8. Create With Multiple Conflicts - Same fields, different values
New HAWB TEST-CONFLICT-001

```bash
# First source - one set of values
curl -X POST "http://localhost:8000/api/pending-actions/mock" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": 18,
    "hawb": "TEST-CONFLICT-001",
    "output_channel_data": {
      "pickup_company_name": "Warehouse Alpha",
      "pickup_address": "111 Alpha Way, Newark, NJ 07101",
      "pickup_time_start": "2024-02-18 08:00:00",
      "pickup_time_end": "2024-02-18 10:00:00",
      "delivery_company_name": "Destination One",
      "delivery_address": "222 Beta Blvd, Trenton, NJ 08601",
      "delivery_time_start": "2024-02-18 14:00:00",
      "delivery_time_end": "2024-02-18 16:00:00"
    },
    "pdf_filename": "create_conflict_source1.pdf"
  }'

# Second source - conflicting pickup location
curl -X POST "http://localhost:8000/api/pending-actions/mock" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": 18,
    "hawb": "TEST-CONFLICT-001",
    "output_channel_data": {
      "pickup_company_name": "Warehouse Beta",
      "pickup_address": "333 Gamma Drive, Elizabeth, NJ 07201"
    },
    "pdf_filename": "create_conflict_source2.pdf"
  }'

# Third source - conflicting delivery location
curl -X POST "http://localhost:8000/api/pending-actions/mock" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": 18,
    "hawb": "TEST-CONFLICT-001",
    "output_channel_data": {
      "delivery_company_name": "Destination Two",
      "delivery_address": "444 Delta Lane, Princeton, NJ 08540"
    },
    "pdf_filename": "create_conflict_source3.pdf"
  }'
```

### 9. Create With Only Optional Fields (will be incomplete - missing required)
New HAWB TEST-OPTIONAL-ONLY-001

```bash
curl -X POST "http://localhost:8000/api/pending-actions/mock" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": 195,
    "hawb": "TEST-OPTIONAL-ONLY-001",
    "output_channel_data": {
      "mawb": "MAWB-ONLY-12345",
      "order_notes": "This order only has optional fields so far",
      "dims": [
        {"length": 12, "width": 12, "height": 12, "qty": 5, "weight": 25}
      ]
    },
    "pdf_filename": "create_optional_only.pdf"
  }'
```

### 10. Create With Dims Only (incomplete, but tests dims handling)
New HAWB TEST-DIMS-001

```bash
curl -X POST "http://localhost:8000/api/pending-actions/mock" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": 18,
    "hawb": "TEST-DIMS-001",
    "output_channel_data": {
      "dims": [
        {"length": 48, "width": 40, "height": 36, "qty": 1, "weight": 500},
        {"length": 24, "width": 24, "height": 24, "qty": 4, "weight": 75},
        {"length": 12, "width": 10, "height": 8, "qty": 10, "weight": 15}
      ]
    },
    "pdf_filename": "create_dims_only.pdf"
  }'
```

---

## LIST AND DETAIL ENDPOINTS - Verify results

```bash
# List all pending actions
curl -X GET "http://localhost:8000/api/pending-actions" | jq

# List only creates
curl -X GET "http://localhost:8000/api/pending-actions?action_type=create" | jq

# List only updates
curl -X GET "http://localhost:8000/api/pending-actions?action_type=update" | jq

# List with status filter
curl -X GET "http://localhost:8000/api/pending-actions?status=incomplete" | jq
curl -X GET "http://localhost:8000/api/pending-actions?status=conflict" | jq
curl -X GET "http://localhost:8000/api/pending-actions?status=ready" | jq

# Get detail for a specific action (replace {id} with actual ID from list)
curl -X GET "http://localhost:8000/api/pending-actions/{id}" | jq
```

---

## Test Scenarios Summary

| # | HAWB | Type | Description |
|---|------|------|-------------|
| 1 | 00455367 | Update | Single field, no conflict |
| 2 | 00455432 | Update | Conflicting delivery_notes |
| 3 | 2725971 | Update | Same value as HTC (filtered) |
| 4 | 00455367 | Update | Multiple fields, no conflict |
| 5 | TEST-FULL-001 | Create | All required in one pass |
| 6 | TEST-FULL-OPT-001 | Create | All required + all optional |
| 7 | TEST-PARTIAL-001 | Create | Two passes to complete |
| 8 | TEST-CONFLICT-001 | Create | Multiple conflicts |
| 9 | TEST-OPTIONAL-ONLY-001 | Create | Only optional (incomplete) |
| 10 | TEST-DIMS-001 | Create | Dims testing |
