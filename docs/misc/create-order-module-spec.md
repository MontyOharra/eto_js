# Create Order Module Specification

**Module ID**: `create_order`
**Type**: Action Module
**Category**: Database
**Version**: 1.0.0
**Purpose**: Create a new shipping order with all related database records

---

## Fixed Inputs (by index)

1. **customer_id** (int) - The customer placing the order
2. **hawb** (str) - House Air Waybill (8 characters)
3. **mawb** (str) - Master Air Waybill (optional, can be empty string)
4. **pickup_address_id** (int) - Pickup location ID (from address_lookup module)
5. **pickup_date** (str) - Pickup date (will be validated and defaulted if invalid)
6. **pickup_time_start** (str) - Pickup window start time, format "HH:MM"
7. **pickup_time_end** (str) - Pickup window end time, format "HH:MM"
8. **pickup_notes** (str) - **OPTIONAL** - Special pickup instructions
9. **delivery_address_id** (int) - Delivery location ID (from address_lookup module)
10. **delivery_date** (str) - Delivery date (will be validated and defaulted if invalid)
11. **delivery_time_start** (str) - Delivery window start time, format "HH:MM"
12. **delivery_time_end** (str) - Delivery window end time, format "HH:MM"
13. **delivery_notes** (str) - **OPTIONAL** - Special delivery instructions
14. **pieces** (int) - Number of pieces/units in shipment
15. **weight** (int) - Total weight of shipment
16. **order_notes** (str) - **OPTIONAL** - General order notes/HAWB notes

---

## Configuration

- **database** (str) - Database connection name (default: "htc_db")

**Hardcoded Values**:
- `company_id` = 1
- `branch_id` = 1
- `default_agent_id` = 159 (SOS default agent - **TODO**: Replace with customer-specific agent lookup once agent system is built)

---

## Fixed Outputs (by index)

1. **order_number** (int) - The created order number

**Note**: Success/failure is determined by whether the module throws an exception, not by output fields.

---

## Internal Operations

The module performs the following operations in order:

### 1. Get Next Order Number (Internal Helper)
- Query `HTC300_G040_T000 Last OrderNo Assigned` table
- Increment the last order number
- Check against `HTC300_G040_T005 Orders In Work` for conflicts
- Keep incrementing until unique order number found
- Update Last Order Number table
- Update Orders In Work table

### 2. Get Customer Info (Internal Helper)
**Query**: `HTC300_G030_T010 Customers` table
**Returns**:
- Customer name
- Tariff
- QuickBooks ID
- QuickBooks Name
- Assessorials

### 3. Get Pickup Address Info (Internal Helper)
**Query**: `HTC300_G060_T010 Addresses` table (join with ACI tables as needed)
**Returns**:
- Full address string (formatted)
- Company name
- Address line 1
- Address line 2
- City
- State
- Zip code
- Country
- Latitude
- Longitude
- ACI ID (Area Control Identifier)
- Is carrier flag
- Is international flag
- Is local flag
- Is branch flag
- Assessorials

### 4. Get Delivery Address Info (Internal Helper)
Same as pickup address info query

### 5. Determine Order Type (Internal Helper)
**Logic**: Based on VBA lines 1818-1882
**Inputs**:
- Pickup ACI area code
- Pickup is_branch flag
- Pickup is_carrier flag
- Delivery ACI area code
- Delivery is_branch flag
- Delivery is_carrier flag
- Branch low/high ACI range (from `HTC300_G000_T020 Branch Info`)

**Order Type Codes**:
1. Recovery
2. Drop
3. Point-to-Point
4. Hot Shot
5. Dock Transfer
6. Services
7. Storage
8. Transfer
9. Pickup
10. Delivery

**Complex Conditional Logic**:
```
IF pickup_is_branch AND NOT pickup_is_carrier AND NOT delivery_is_branch AND delivery_is_carrier
   AND (pickup_aci IN branch_range AND delivery_aci IN branch_range)
   THEN order_type = 8 (Transfer)

ELSE IF pickup_aci NOT IN branch_range OR delivery_aci NOT IN branch_range
   THEN order_type = 4 (Hot Shot)

ELSE IF NOT pickup_is_branch AND pickup_is_carrier AND NOT delivery_is_carrier
   THEN order_type = 1 (Recovery)

ELSE IF NOT pickup_is_branch AND NOT pickup_is_carrier AND NOT delivery_is_branch AND delivery_is_carrier
   THEN order_type = 2 (Drop)

ELSE IF NOT pickup_is_branch AND pickup_is_carrier AND NOT delivery_is_branch AND delivery_is_carrier
   THEN order_type = 2 (Drop - carrier to carrier priced like drop)

ELSE IF NOT pickup_is_branch AND NOT pickup_is_carrier AND NOT delivery_is_branch AND NOT delivery_is_carrier
   THEN order_type = 3 (Point-to-Point)

ELSE IF pickup_is_branch AND NOT pickup_is_carrier AND delivery_is_branch AND NOT delivery_is_carrier
   THEN order_type = 5 (Dock Transfer)

ELSE IF NOT pickup_is_branch AND delivery_is_branch AND NOT delivery_is_carrier
   THEN order_type = 9 (Pickup)

ELSE IF pickup_is_branch AND NOT pickup_is_carrier AND NOT delivery_is_branch AND NOT delivery_is_carrier
   THEN order_type = 10 (Delivery)
```

### 6. Validate and Default Date/Time Fields
**VBA Reference**: Lines 1301-1375

**Pickup Date Validation**:
- If not a valid date → Default to tomorrow (`DateAdd("d", 1, Date)`)

**Pickup Time Validation**:
- Must be format "HH:MM" (length 5, positions 1-2 numeric, position 3 is ":", positions 4-5 numeric)
- If invalid start time → Default to "09:00"
- If invalid end time → Default to "17:00"

**Delivery Date Validation**:
- If not a valid date → Default to day after pickup date

**Delivery Time Validation**:
- Same validation as pickup times
- Defaults: "09:00" to "17:00"

**Note**: All validation errors should be logged but NOT fail the order creation - use defaults instead

### 7. Insert into Orders Table
**Table**: `HTC300_G040_T010A Open Orders`
**VBA Reference**: Lines 1382-1462

**Key Fields** (~80 total):
- `M_COID` = 1 (hardcoded company ID)
- `M_BrID` = 1 (hardcoded branch ID)
- `m_Orderno` = generated order number
- `M_OrderType` = calculated order type (1-10)
- `m_customerid` = customer_id input
- `m_customer` = customer name (from lookup)
- `M_CustAgent` = 159 (default agent - TODO: make customer-specific)
- `m_Tariff` = customer tariff (from lookup)
- `M_CustAssessorials` = customer assessorials (from lookup)
- `M_HAWB` = hawb input (trimmed)
- `M_MAWB` = mawb input
- `M_ProNbr` = "" (empty)
- `M_OrderNotes` = order_notes input
- **Pickup fields**:
  - `M_PUDate` = validated pickup_date
  - `M_PUTimeStart` = validated pickup_time_start
  - `M_PUTimeEnd` = validated pickup_time_end
  - `M_PUID` = pickup_address_id
  - `M_PUCo` = pickup company name
  - `M_PULocn` = formatted pickup address
  - `M_PUZip` = pickup zip
  - `m_pulatitude` = pickup latitude
  - `m_pulongitude` = pickup longitude
  - `M_PUACI` = pickup ACI (first character only)
  - `M_PUAssessorials` = pickup assessorials
  - `M_PUContactName` = "" (empty)
  - `M_PUContactMeans` = "" (empty)
  - `M_PUNotes` = pickup_notes input
  - `M_PUCarrierYN` = pickup is_carrier flag
  - `M_PUIntlYN` = pickup is_international flag
  - `M_PULocalYN` = pickup is_local flag
  - `M_PUBranchYN` = pickup is_branch flag
- **Delivery fields**:
  - `M_DelDate` = validated delivery_date
  - `M_DelTimeStart` = validated delivery_time_start
  - `M_DelTimeEnd` = validated delivery_time_end
  - `M_DelID` = delivery_address_id
  - `M_DelCo` = delivery company name
  - `M_DelLocn` = formatted delivery address
  - `M_DelZip` = delivery zip
  - `m_dellatitude` = delivery latitude
  - `m_dellongitude` = delivery longitude
  - `M_DelACI` = delivery ACI (first character only)
  - `M_Del_Assessorials` = 0 (not used)
  - `M_DelContactName` = "" (empty)
  - `M_DelContactMeans` = "" (empty)
  - `M_DelNotes` = delivery_notes input
  - `M_DelCarrierYN` = delivery is_carrier flag
  - `M_DelIntlYN` = delivery is_international flag
  - `M_DelLocalYN` = delivery is_local flag
  - `M_DelBranchYN` = delivery is_branch flag
- **POD fields** (all empty):
  - `M_PODSig` = ""
  - `M_PODDate` = ""
  - `M_PODTime` = ""
  - `M_PODNotes` = ""
- **Status**:
  - `m_status` = "ETO Generated"
  - `m_statseq` = 35
- **Charges** (all 0):
  - `m_rate` = 0
  - `m_fsc` = 0
  - `m_services` = 0
  - `m_StorageChgs` = 0
  - `m_adjustments` = 0
  - `M_RatingNotes` = 0
  - `M_Charges` = 0 (sum of above)
  - `M_Costs` = 0
- **QuickBooks**:
  - `M_QBCustomerListID` = customer QB ID
  - `M_QBCustFullName` = customer QB name
  - `M_QBInvoiceRefNumber` = "" (empty)
- **Flags**:
  - `M_AutoAssessYN` = False
  - `M_WgtChgsCalcYN` = False
- `M_DeclaredValue` = 0

### 8. Insert into Dimensions Table
**Table**: `HTC300_G040_T012A Open Order Dims`
**VBA Reference**: Lines 1466-1481

**Fields**:
- `od_coid` = 1
- `od_brid` = 1
- `od_orderno` = order_number
- `od_dimid` = 1 (single dimension record)
- `od_unittype` = "EA" (each)
- `od_unitqty` = pieces input
- `od_unitheight` = 1
- `od_unitlength` = 1
- `od_Unitwidth` = 1
- `od_unitweight` = weight input
- `od_unitdimweight` = 0

### 9. Insert into HAWB Values Table
**Table**: `HTC300_G040_T040 HAWB Values`
**VBA Reference**: Lines 1543-1560

**Purpose**: Track customer+HAWB combinations to prevent duplicates (but duplicates are sometimes OK - use try/catch)

**Fields**:
- `existinghawbvalues` = hawb input
- `hawbcoid` = 1
- `hawbbrid` = 1
- `hawbcustomerid` = customer_id
- `hawborder` = order_number

**Error Handling**: Use try/except - if insert fails (duplicate key), continue anyway

### 10. Insert into History Table
**Table**: `HTC300_G040_T030 Orders Update History`
**VBA Reference**: Lines 1566-1581

**Fields**:
- `Orders_UpdtDate` = NOW()
- `Orders_UpdtLID` = "ETO Automation" (or similar identifier)
- `Orders_CoID` = 1
- `Orders_BrID` = 1
- `Orders_OrderNbr` = order_number
- `Orders_Changes` = Formatted string:
  ```
  Order #{order_number} Customer: {customer_name} (#{customer_id}) Created with 1 Dim,
  0 Assessorials, 0 Drivers, and 0 Attachments, assigned $0.00 using the {tariff} tariff;
  Status = ETO Generated(35)
  ```

### 11. Update Last Order Number
**Table**: `HTC300_G040_T000 Last OrderNo Assigned`
**VBA Reference**: Line 1533 - `Call HTC200_PosttoLON`

**Operation**: Update the last order number to the newly created order number

### 12. Update Orders In Work
**Table**: `HTC300_G040_T005 Orders In Work`
**VBA Reference**: Line 1534 - `Call HTC200_RemoveOIW`

**Operation**: Remove the order number from Orders In Work table (if it exists)

---

## Error Handling Strategy

**VBA Reference**: Lines 1604-1720

The VBA code tracks success flags for each operation:
- `OrderCreated` - Main order record inserted
- `DimCreated` - Dimension record inserted
- `HistCreated` - History record inserted
- `CustHAWBCreated` - HAWB tracking record inserted
- `LonUpdated` - Last Order Number updated
- `OIWUpdated` - Orders In Work updated

**For Initial Implementation**:
- If main order insert fails → Raise exception with error details
- If any supplementary operation fails (Dim, History, HAWB, LON, OIW) → Log warning but continue
- Return the order_number as output if order was created

**For Future Enhancement**:
- Track exactly which operations succeeded/failed
- Log detailed results to ETOLog table
- Implement rollback logic if critical operations fail

---

## Database Transaction Strategy

**Recommended Approach**:
1. Start database transaction
2. Get next order number (with updates)
3. Get all lookup data (customer, addresses)
4. Validate all inputs
5. Insert Orders record (CRITICAL - if this fails, rollback)
6. Insert Dimensions record (if fails, log but continue)
7. Insert HAWB Values record (if fails due to duplicate, continue)
8. Insert History record (if fails, log but continue)
9. Commit transaction
10. Return order_number

---

## Future Enhancements

### 1. Customer Agent Lookup
**Current**: Hardcoded to agent ID 159
**Future**: Query customer table for assigned agent, fall back to default if not set

**Implementation TODO**:
- Add agent_id field to Customers table (or customer agents mapping table)
- Query for customer's assigned agent
- Use default (159) if no agent assigned

### 2. Email Sending
**Skipped for now** - Will be implemented as separate email action modules:
- `send_customer_confirmation_email` - Send order confirmation to customer
- `send_dispatch_notification_email` - Send batch notification to dispatch

### 3. Attachment Handling
**Skipped for now** - Will be implemented as separate file action module:
- `copy_order_attachment` - Copy PDF files to document storage and link to order

### 4. Detailed Error Logging
**Future**: Log all operations to `HTC350_G800_T010 ETOLog` table with detailed success/failure tracking

---

## Module Implementation Notes

**Language**: Python
**Category**: Action Module (has side effects - database inserts)
**Atomicity**: Should use database transactions to ensure consistency
**Idempotency**: NOT idempotent - creates new order each time (check with get_order_number first)

**Testing Considerations**:
- Test with invalid dates/times to verify defaulting logic
- Test with missing optional fields (notes)
- Test order type determination logic with various address combinations
- Test HAWB duplicate handling (should not fail on duplicate)
- Test transaction rollback on critical failures
