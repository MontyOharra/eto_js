# VBA Analysis: HTC_350C_Sub_2_of_2_CreateOrders

**File**: vba-code/HTC_350C_Sub_2_of_2_CreateOrders.vba
**Last Updated**: 2025-11-11

## Table of Contents
- [Function: GetOrderNo](#function-getorderno)

---

# Function: `GetOrderNo`

**Type**: Function
**File**: HTC_350C_Sub_2_of_2_CreateOrders.vba
**Analyzed**: 2025-11-11

## Signature
```vba
Function GetOrderNo(CID As Integer, HAWB As String) As Double
```

## Purpose & Overview

**Primary Purpose**: Searches for an existing order number associated with a specific customer ID and HAWB (House Air Waybill) value. This function performs a lookup to determine if an order has already been created for a given customer/HAWB combination.

**Input**:
- `CID` (Integer): Customer ID to search for
- `HAWB` (String): House Air Waybill number to match

**Output**: Returns a Double value representing the order number if found, or 0 if no matching customer/HAWB combination exists

**Side Effects**: None. This is a read-only function that queries the database but does not modify any data.

---

## Function Cross-References

### Functions in Same File
None - This function does not call any other functions within the same file.

### External Functions (NOT in this file)
None - This function only uses built-in VBA/Access functions.

### Built-in VBA/Access Functions
- `CurrentDb()` - Returns reference to current Access database
- `OpenRecordset()` - Opens a DAO recordset for database queries
- `MoveFirst()` - Moves to first record in recordset
- `EOF` - End-of-file property for recordset navigation

---

## Detailed Behavioral Breakdown

### Block 1: Variable Initialization and Database Setup
```vba
Dim Ans As Double: Ans = 0

Dim db As Database: Set db = CurrentDb

Dim HAWBs As Recordset
Set HAWBs = db.OpenRecordset("HTC200F_G020_Q010 Current HAWB values sorted", dbOpenDynaset)
```

**Explanation**:
- Initializes `Ans` to 0, which will be the default return value if no match is found
- Gets a reference to the current Access database using `CurrentDb()`
- Opens a dynaset recordset from the query "HTC200F_G020_Q010 Current HAWB values sorted"
- The query name indicates it contains current HAWB values that are pre-sorted, which is critical for the binary search algorithm that follows

### Block 2: Binary Search Loop Through HAWB Records
```vba
With HAWBs
    HAWBs.MoveFirst
    Do Until .EOF
        If !hawbcustomerid < CID Then
            .MoveNext
        ElseIf !hawbcustomerid > CID Then
            Exit Do
        Else
            If !existinghawbvalues < HAWB Then
                .MoveNext
            ElseIf !existinghawbvalues > HAWB Then
                Exit Do
            Else
                Ans = !hawborder
                Exit Do
            End If
        End If

    Loop
End With
```

**Explanation**:
- Moves to the first record in the sorted HAWB recordset
- Implements a binary search pattern that relies on the recordset being sorted by customer ID first, then HAWB value
- **First level comparison**: Compares `hawbcustomerid` with the target `CID`
  - If current customer ID is less than target: Move to next record
  - If current customer ID is greater than target: Exit loop (no match possible since data is sorted)
  - If customer ID matches: Proceed to HAWB comparison
- **Second level comparison**: Once customer ID matches, compares `existinghawbvalues` with target `HAWB`
  - If current HAWB is less than target: Move to next record
  - If current HAWB is greater than target: Exit loop (no match since data is sorted)
  - If HAWB matches: Store the order number in `Ans` and exit
- This two-level search is efficient because it exits early when it knows a match is impossible due to sorted order

### Block 3: Return Result
```vba
GetOrderNo = Ans
```

**Explanation**:
- Returns the found order number (stored in `Ans`), or 0 if no match was found
- The value 0 serves as a sentinel indicating "no existing order found"

---

## Dependencies

**Database Objects**:
- **Queries**: `HTC200F_G020_Q010 Current HAWB values sorted` - This query must return records sorted by `hawbcustomerid` first, then `existinghawbvalues` second
  - Fields used:
    - `hawbcustomerid` (Integer) - Customer ID
    - `existinghawbvalues` (String) - HAWB number
    - `hawborder` (Double) - Order number associated with this customer/HAWB

**External Dependencies**:
- None - This function is self-contained and relies only on database access

---

## Migration Notes

**Complexity**: Low

**Migration Strategy**: Replace with a simple database query using modern ORM or query builder

**Challenges**:
- The VBA code implements a manual binary search that relies on pre-sorted data from the query. This optimization is unnecessary in modern databases that can perform indexed lookups efficiently
- The function returns 0 to indicate "not found", which is not type-safe. Modern implementations should use nullable types or Option types
- The Double type for order numbers is unusual and suggests potential precision issues with large order numbers
- Direct field access using `!fieldname` syntax is VBA-specific

**Modern Equivalent**:
```python
# Python/SQLAlchemy example
def get_order_no(cid: int, hawb: str) -> Optional[float]:
    """
    Look up order number for customer ID and HAWB.
    Returns order number if found, None otherwise.
    """
    result = db.session.query(HAWBValues.hawb_order)\
        .filter(
            HAWBValues.hawb_customer_id == cid,
            HAWBValues.existing_hawb_values == hawb
        )\
        .first()

    return result[0] if result else None
```

Or in TypeScript/TypeORM:
```typescript
async function getOrderNo(cid: number, hawb: string): Promise<number | null> {
    const result = await hawbRepository.findOne({
        select: ['hawbOrder'],
        where: {
            hawbCustomerId: cid,
            existingHawbValues: hawb
        }
    });

    return result?.hawbOrder ?? null;
}
```

**Key improvements in modern version**:
- Database handles the search optimization automatically using indexes
- Type-safe nullable return (Optional/null) instead of 0 as sentinel value
- More readable query syntax
- Automatic connection management and query parameterization (SQL injection protection)
- No need for manual record navigation or EOF checking
