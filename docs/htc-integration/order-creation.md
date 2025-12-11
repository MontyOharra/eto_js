# HTC Order Creation Specification

This document defines how order records are created in the HTC system from pending order data.

## Target Table

`HTC300_G040_T010A Open Orders` (75 columns)

## Input Fields

These are the fields passed into the order creation process:

| Input Field | Description |
|-------------|-------------|
| ordertype | Order classification (1-10) |
| customerid | FK to Customers table |
| hawb | House Air Waybill number |
| mawb | Master Air Waybill number |
| ordernotes | General order notes |
| pickupdatestart | Pickup date + start time |
| pickupdateend | Pickup end time |
| pickupaddressid | FK to Addresses table |
| pickupnotes | Pickup-specific notes |
| deliverydatestart | Delivery date + start time |
| deliverydateend | Delivery end time |
| deliveryaddressid | FK to Addresses table |
| deliverynotes | Delivery-specific notes |

## Field Mapping

### Direct Input Fields

| Column | Source | Type | Notes |
|--------|--------|------|-------|
| M_OrderType | INPUT: ordertype | SMALLINT | 1-10 classification |
| M_CustomerID | INPUT: customerid | SMALLINT | FK to Customers |
| M_HAWB | INPUT: hawb | VARCHAR(125) | |
| M_MAWB | INPUT: mawb | VARCHAR(125) | |
| M_OrderNotes | INPUT: ordernotes | LONGCHAR | |
| M_PUDate | INPUT: pickupdatestart | VARCHAR(10) | Date portion only (MM/DD/YYYY) |
| M_PUTimeStart | INPUT: pickupdatestart | VARCHAR(11) | Time portion only (HH:MM) |
| M_PUTimeEnd | INPUT: pickupdateend | VARCHAR(11) | Time portion only (HH:MM) |
| M_PUID | INPUT: pickupaddressid | DOUBLE | FK to Addresses |
| M_PUNotes | INPUT: pickupnotes | LONGCHAR | |
| M_DelDate | INPUT: deliverydatestart | VARCHAR(10) | Date portion only |
| M_DelTimeStart | INPUT: deliverydatestart | VARCHAR(11) | Time portion only |
| M_DelTimeEnd | INPUT: deliverydateend | VARCHAR(11) | Time portion only |
| M_DelID | INPUT: deliveryaddressid | DOUBLE | FK to Addresses |
| M_DelNotes | INPUT: deliverynotes | LONGCHAR | |

### System Generated Fields

| Column | Source | Type | Notes |
|--------|--------|------|-------|
| M_CoID | 1 | SMALLINT | Always 1 |
| M_BrID | 1 | SMALLINT | Always 1 |
| M_OrderNo | `_generate_next_order_number()` | DOUBLE | Auto-generated |

### Customer Lookup Fields

Looked up from `HTC300_G030_T010 Customers` table using M_CustomerID:

| Column | Source Field | Type | Notes |
|--------|--------------|------|-------|
| m_Customer | CustName | VARCHAR(255) | Customer display name |
| M_CustAssessorials | CustAssessorials | VARCHAR(100) | 100-char assessorial flags |
| M_Tariff | CustTariff | VARCHAR(50) | Pricing tariff name |
| M_QBCustomerListID | QBListID | VARCHAR(38) | QuickBooks integration |
| M_QBCustFullName | QBFullName | VARCHAR(255) | QuickBooks integration |
| M_CustAgent | **null** | SMALLINT | **DEFERRED** - needs DB schema update |

> **Note:** M_CustAgent is set to null for now. The VBA system used a hardcoded default of 159 (SOS agent), but the HTC database needs a proper default agent definition added before we can populate this field.

### Pickup Address Lookup Fields

Looked up from `HTC300_G060_T010 Addresses` table using M_PUID:

| Column | Source Field | Type | Notes |
|--------|--------------|------|-------|
| M_PUCo | FavCompany | VARCHAR(125) | Company name |
| M_PULocn | *formatted* | VARCHAR(255) | See format below |
| M_PUZip | FavZip | VARCHAR(10) | |
| M_PULatitude | FavLatitude | VARCHAR(13) | |
| M_PULongitude | FavLongitude | VARCHAR(13) | |
| M_PUACI | *ACI lookup* | VARCHAR(1) | Single letter from ACI table |
| M_PUAssessorials | FavAssessorials | VARCHAR(100) | |
| M_PUCarrierYN | FavCarrierYN | BIT | |
| M_PUCarrierGroundYN | FavCarrierGroundYN | BIT | |
| M_PUIntlYN | FavInternational | BIT | |
| M_PULocalYN | FavLocalYN | BIT | |
| M_PUBranchYN | FavBranchAddressYN | BIT | |
| M_PUContactName | "" | VARCHAR(50) | Empty string |
| M_PUContactMeans | "" | VARCHAR(50) | Empty string |

**M_PULocn Format:**
```
{AddrLn1}, {AddrLn2}, {City}, {State}, {Country}
```
If AddrLn2 is empty, omit it: `{AddrLn1}, {City}, {State}, {Country}`

**M_PUACI Lookup:**
1. Get FavACIID from Address record
2. Look up in `HTC300_G010_T010 DFW_ACI_Data` by ID
3. Return the ACI zone letter (A, B, C, D, etc.)

### Delivery Address Lookup Fields

Same pattern as pickup, using M_DelID:

| Column | Source Field | Type |
|--------|--------------|------|
| M_DelCo | FavCompany | VARCHAR(125) |
| M_DelLocn | *formatted* | VARCHAR(255) |
| M_DelZip | FavZip | VARCHAR(10) |
| M_DelLatitude | FavLatitude | VARCHAR(13) |
| M_DelLongitude | FavLongitude | VARCHAR(13) |
| M_DelACI | *ACI lookup* | VARCHAR(1) |
| M_Del_Assessorials | FavAssessorials | VARCHAR(100) |
| M_DelCarrierYN | FavCarrierYN | BIT |
| M_DelCarrierGroundYN | FavCarrierGroundYN | BIT |
| M_DelIntlYN | FavInternational | BIT |
| M_DelLocalYN | FavLocalYN | BIT |
| M_DelBranchYN | FavBranchAddressYN | BIT |
| M_DelContactName | "" | VARCHAR(50) |
| M_DelContactMeans | "" | VARCHAR(50) |

### Status Fields (Defaults)

| Column | Value | Type | Notes |
|--------|-------|------|-------|
| M_Status | "ETO Generated" | VARCHAR(25) | Initial status |
| m_StatSeq | 35 | SMALLINT | Status sequence number |

### Financial Fields (All Zero)

| Column | Value | Type |
|--------|-------|------|
| M_Rate | 0 | CURRENCY |
| M_FSC | 0 | CURRENCY |
| M_Services | 0 | CURRENCY |
| M_Charges | 0 | CURRENCY |
| M_Costs | 0 | CURRENCY |
| M_StorageChgs | 0 | CURRENCY |
| M_Adjustments | 0 | CURRENCY |
| M_DeclaredValue | 0 | CURRENCY |

### Boolean Flags (Defaults)

| Column | Value | Type |
|--------|-------|------|
| M_AutoAssessYN | False | BIT |
| M_WgtChgsCalcYN | False | BIT |
| M_PUSpecificYN | False | BIT |
| M_DelSpecificYN | False | BIT |

### Empty/Null Fields

These fields are populated later in the order lifecycle:

| Column | Value | Type | When Populated |
|--------|-------|------|----------------|
| M_ProNbr | "" | VARCHAR(50) | Manual entry |
| M_Driver | "" | VARCHAR(30) | When dispatched |
| M_PODSig | "" | VARCHAR(125) | Proof of delivery |
| M_PODDate | "" | VARCHAR(10) | Proof of delivery |
| M_PODTime | "" | VARCHAR(11) | Proof of delivery |
| M_PODNotes | "" | LONGCHAR | Proof of delivery |
| M_RatingNotes | "" | LONGCHAR | When rated |
| M_QBInvoiceRefNumber | "" | VARCHAR(11) | When invoiced |
| M_QBInvoiceLineSeqNo | null | SMALLINT | When invoiced |

## Order Type Classification

Order types are determined by pickup/delivery location characteristics:

| Type | Name | Description |
|------|------|-------------|
| 1 | Recovery | From carrier to non-carrier |
| 2 | Drop | To carrier (standard or carrier-to-carrier) |
| 3 | Point-to-Point | Customer to customer (no branches/carriers) |
| 4 | Hot Shot | Either location outside local ACI range |
| 5 | Dock Transfer | Branch to branch |
| 6 | Services | *(not auto-assigned)* |
| 7 | Storage | *(not auto-assigned)* |
| 8 | Transfer | Branch to carrier (both within local ACI) |
| 9 | Pickup | To branch |
| 10 | Delivery | From branch to customer |

See `docs/vba-analysis/HTC_350C_Sub_2_of_2_CreateOrders/HTC200F_SetOrderType.md` for detailed classification logic.

## Related Tables

Order creation also writes to these tables:

| Table | Purpose |
|-------|---------|
| `HTC300_G040_T012A Open Order Dims` | Package dimensions |
| `HTC300_G040_T040 HAWB Values` | HAWB tracking |
| `HTC300_G040_T030 Orders Update History` | Audit trail |
| `HTC300_G040_T000 Last OrderNo Assigned` | Track last assigned order number |
| `HTC300_G040_T005 Orders In Work` | Lock table for concurrent order creation |

---

## Order Creation Flow

```
create_order_from_pending(pending_order)
│
│  ╔═══════════════════════════════════════════════════════════════════╗
│  ║  PHASE 1: DATA GATHERING                                          ║
│  ╚═══════════════════════════════════════════════════════════════════╝
│
├── 1. Resolve pickup address (find existing or create new)
│   └── find_or_create_address(pickup_address_string, pickup_company_name)
│       → Returns: pickup_address_id (FavID)
│
├── 2. Resolve delivery address (find existing or create new)
│   └── find_or_create_address(delivery_address_string, delivery_company_name)
│       → Returns: delivery_address_id (FavID)
│
├── 3. Look up full pickup address info
│   ├── get_address_info(pickup_address_id)
│   └── get_aci_letter(pu_addr.aci_id)
│
├── 4. Look up full delivery address info
│   ├── get_address_info(delivery_address_id)
│   └── get_aci_letter(del_addr.aci_id)
│
├── 5. Look up customer info
│   └── get_customer_info(customer_id)
│
├── 6. Determine order type
│   └── determine_order_type(pu_aci, pu_branch, pu_carrier, del_aci, del_branch, del_carrier)
│
├── 7. Prepare all 75 field values for Open Orders INSERT
│
├── 8. Prepare dimension record data
│
│  ╔═══════════════════════════════════════════════════════════════════╗
│  ║  PHASE 2: ORDER CREATION (DB writes)                              ║
│  ╚═══════════════════════════════════════════════════════════════════╝
│
├── 9. Reserve order number
│   └── _generate_next_order_number()  → adds to OIW (locks the number)
│
├── 10. INSERT order record
│    └── _create_order_record(order_number, prepared_data)
│
├── 11. INSERT dimension record
│    └── _create_dimension_record(order_number, dim_data)
│
├── 12. On success - finalize:
│    ├── _update_lon(order_number)           → update Last Order Number
│    ├── remove_from_orders_in_work()        → release the lock
│    ├── save_hawb_association()             → track customer/HAWB
│    └── _create_order_history()             → audit trail
│
└── 13. Return order_number
```

### Order Number Management

The OIW (Orders In Work) table acts as a lock mechanism:

| When | LON Table | OIW Table |
|------|-----------|-----------|
| Before order creation | Last assigned number | Other in-progress orders |
| After reserving number | Unchanged | New number added (locked) |
| After successful creation | Updated to new number | New number removed (unlocked) |

This prevents concurrent processes from using the same order number.

---

## Implementation Status

| Component | Status | Notes |
|-----------|--------|-------|
| Order number generation | ✅ Done | `_generate_next_order_number()` - adds to OIW only |
| LON update | ✅ Done | `_update_lon()` - called after order creation |
| Address resolution | ✅ Done | `find_or_create_address()` |
| Address lookup | ✅ Done | `get_address_info()` returns `AddressInfo` dataclass |
| Customer lookup | ✅ Done | `get_customer_info()` returns `CustomerInfo` dataclass |
| ACI letter lookup | ✅ Done | `get_aci_letter()` converts ACI ID to zone letter |
| Order type classification | ✅ Done | `determine_order_type()` - returns 1-11 |
| Order record creation | ✅ Done | `_create_order_record()` - 75 field INSERT |
| Dimension record | ✅ Done | `_create_dimension_record()` |
| HAWB association | ✅ Done | `save_hawb_association()` |
| Order history | ✅ Done | `_create_order_history()` |
| **Main orchestrator** | ✅ Done | `create_order_from_pending()` |

## Deferred Items

- **M_CustAgent**: Requires database schema update to define default agent. Set to null until resolved.

---

**Last Updated:** 2025-12-10
