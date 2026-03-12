#!/bin/bash
# Test address parsing via the mock output endpoint
# Sends various addresses with extraneous text to verify parsing behavior

BASE_URL="http://localhost:8000/api/pending-actions/mock"

echo "=== Test 1: Clean addresses (baseline - should pass) ==="
curl -s -X POST "$BASE_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": 1,
    "hawb": "TEST-CLEAN-001-new",
    "output_channel_data": {
      "pickup_company_name": "Test Warehouse",
      "pickup_address": "123 Main St, Dallas, TX 75201",
      "delivery_company_name": "Acme Corp",
      "delivery_address": "456 Oak Ave, Houston, TX 77001"
    }
  }' | python -m json.tool
echo ""

echo "=== Test 2: Order number prepended to pickup address ==="
curl -s -X POST "$BASE_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": 1,
    "hawb": "TEST-ORDER-PREFIX-002-new",
    "output_channel_data": {
      "pickup_company_name": "Test Warehouse",
      "pickup_address": "ORDER #100045 123 Main St, Dallas, TX 75201",
      "delivery_company_name": "Acme Corp",
      "delivery_address": "456 Oak Ave, Houston, TX 77001"
    }
  }' | python -m json.tool
echo ""

echo "=== Test 3: Order number appended to pickup address ==="
curl -s -X POST "$BASE_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": 1,
    "hawb": "TEST-ORDER-SUFFIX-003-new",
    "output_channel_data": {
      "pickup_company_name": "Test Warehouse",
      "pickup_address": "123 Main St, Dallas, TX 75201 ORDER #100045",
      "delivery_company_name": "Acme Corp",
      "delivery_address": "456 Oak Ave, Houston, TX 77001"
    }
  }' | python -m json.tool
echo ""

echo "=== Test 4: REF number inline in pickup address ==="
curl -s -X POST "$BASE_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": 1,
    "hawb": "TEST-REF-INLINE-004-new",
    "output_channel_data": {
      "pickup_company_name": "Test Warehouse",
      "pickup_address": "REF 55443 789 Elm Blvd, Suite 200, Austin, TX 78701",
      "delivery_company_name": "Acme Corp",
      "delivery_address": "456 Oak Ave, Houston, TX 77001"
    }
  }' | python -m json.tool
echo ""

echo "=== Test 5: PO number in pickup address ==="
curl -s -X POST "$BASE_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": 1,
    "hawb": "TEST-PO-005-new",
    "output_channel_data": {
      "pickup_company_name": "Test Warehouse",
      "pickup_address": "PO 12345 321 Pine Rd, Fort Worth, TX 76102",
      "delivery_company_name": "Acme Corp",
      "delivery_address": "456 Oak Ave, Houston, TX 77001"
    }
  }' | python -m json.tool
echo ""

echo "=== Test 6: Both addresses have junk ==="
curl -s -X POST "$BASE_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": 1,
    "hawb": "TEST-BOTH-JUNK-006-new",
    "output_channel_data": {
      "pickup_company_name": "Test Warehouse",
      "pickup_address": "ORDER #99887 123 Main St, Dallas, TX 75201",
      "delivery_company_name": "Acme Corp",
      "delivery_address": "INVOICE 44556 456 Oak Ave, Houston, TX 77001"
    }
  }' | python -m json.tool
echo ""

echo "=== Test 7: UPS tracking number in pickup address ==="
curl -s -X POST "$BASE_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": 1,
    "hawb": "TEST-TRACKING-007-new",
    "output_channel_data": {
      "pickup_company_name": "Test Warehouse",
      "pickup_address": "1Z999AA10123456784 500 Commerce St, Dallas, TX 75202",
      "delivery_company_name": "Acme Corp",
      "delivery_address": "456 Oak Ave, Houston, TX 77001"
    }
  }' | python -m json.tool
echo ""

echo "=== Test 8: Multiple extraneous items in pickup address ==="
curl -s -X POST "$BASE_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": 1,
    "hawb": "TEST-MULTI-EXTRA-008-new",
    "output_channel_data": {
      "pickup_company_name": "Test Warehouse",
      "pickup_address": "CUSTOMER: JOHN DOE ORDER #12345 REF #ABC 900 Jackson St, Dallas, TX 75202",
      "delivery_company_name": "Acme Corp",
      "delivery_address": "456 Oak Ave, Houston, TX 77001"
    }
  }' | python -m json.tool
echo ""

echo "=== All tests complete ==="
echo ""
echo "To check results:"
echo "  curl -s http://localhost:8000/api/pending-actions/{id} | python -m json.tool"
