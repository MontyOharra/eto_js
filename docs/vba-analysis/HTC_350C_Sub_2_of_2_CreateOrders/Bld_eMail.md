# VBA Analysis: HTC_350C_Sub_2_of_2_CreateOrders.vba

**File**: vba-code\HTC_350C_Sub_2_of_2_CreateOrders.vba
**Last Updated**: 2025-11-11

## Table of Contents
- [Function: Bld_eMail](#function-bld_email)

---

# Function: `Bld_eMail`

**Type**: Sub
**File**: HTC_350C_Sub_2_of_2_CreateOrders.vba
**Analyzed**: 2025-11-11

## Signature
```vba
Sub Bld_eMail(ELThisRun As Date, ELThisLineNo As Integer)
```

## Purpose & Overview

**Primary Purpose**: Builds and sends an automated email notification to HTC dispatchers summarizing all orders that have been processed from parsed email data. The function creates a formatted email body with three distinct sections: newly created orders, existing orders that were updated, and orders that could not be created due to insufficient information.

**Input**:
- `ELThisRun As Date` - The date/time stamp identifying this processing run
- `ELThisLineNo As Integer` - Line number counter for logging purposes (passed by reference, incremented during processing)

**Output**:
- No direct return value (Sub procedure)
- Populates the `HTC200F_G020_T020 Outlook Body` table with formatted email message lines
- Sends email via `EmailDispatcher` function

**Side Effects**:
- Empties and repopulates the `HTC200F_G020_T020 Outlook Body` table
- Creates new orders via `CreateNewOrder` sub
- Sends email notifications to dispatcher(s) and potentially to the original sender
- Modifies the `ELThisLineNo` parameter (passed by reference)

## Function Cross-References

### Functions in Same File
- `CreateNewOrder()` - Creates new orders in the HTC system when `ThisOrderType = 10`
- `GetOrderNo()` - Not directly called but referenced via `NewOrderNo` variable from calling context
- `EmailDispatcher()` - Sends the constructed email message to dispatcher(s)

### External Functions (NOT in this file)
- `HTC200F_Custinfo()` - **⚠️ EXTERNAL** - Returns formatted customer information string for display
- `HTC200F_AddrInfo()` - **⚠️ EXTERNAL** - Retrieves detailed address information for pickup/delivery locations
- `HTC200F_SetLineLength()` - **⚠️ EXTERNAL** - Calculates optimal line break position for text wrapping
- `HTC350C_SendEmail()` - **⚠️ EXTERNAL** - Sends email notification to the original sender

### Built-in VBA/Access Functions
- `CurrentDb()` - Opens current Access database
- `OpenRecordset()` - Opens database recordsets
- `IsNull()` - Checks for null values
- `Trim()`, `Left()`, `Right()`, `Replace()`, `Space()`, `String()` - String manipulation
- `Len()` - String length
- `IIf()` - Inline conditional
- `Now()` - Current date/time
- `Environ()` - Reads environment variables

## Detailed Behavioral Breakdown

### Block 1: Error Handling Setup and Database Initialization
```vba
On Error GoTo Bld_eMail_Error

Dim db As Database: Set db = CurrentDb

Dim EmailInfo As Recordset
Set EmailInfo = db.OpenRecordset("HTC200F_G020_Q010 Suggested Orders Sorted", dbOpenDynaset)

Dim eMailBody As Recordset
Set eMailBody = db.OpenRecordset("HTC200F_G020_T020 Outlook Body", dbOpenTable)
```
**Explanation**:
- Establishes error handling that jumps to `Bld_eMail_Error` label on any error
- Opens the current Access database connection
- Opens two critical recordsets:
  - `EmailInfo` - Contains suggested orders to be processed (dynaset allows sorting/filtering)
  - `eMailBody` - Destination table for building email message lines (table mode for direct manipulation)

### Block 2: Variable Declarations
```vba
Dim LineNo As Integer: LineNo = 0
Dim NewOrderHdrCreated As Boolean: NewOrderHdrCreated = False
Dim ExistingOrderHdrCreated As Boolean: ExistingOrderHdrCreated = False
Dim InsufficientInfoHdrCreated As Boolean: InsufficientInfoHdrCreated = False

Dim NewOrderNo As Double
Dim PkupNoteLines(5) As String
Dim DelNoteLines(5) As String
Dim OrdNoteLines(5) As String
Dim wrkNotes As String
Dim wrkNotesLen As Integer
Dim LeadSpaces As Integer: LeadSpaces = 12
Dim ThisLineLength As Integer
Dim ThisOrderType As Integer
Dim MaxLineLength As Integer: MaxLineLength = 80
Dim ThisSender As String
Dim ThisDTTM As String
Dim ThisEmail As String
Dim eMailSent As Boolean

Dim SendTo As String
Dim SentTo As String
```
**Explanation**:
- Declares working variables for email construction
- Boolean flags track whether section headers have been created to avoid duplicates
- `LineNo` tracks sequential line numbers in the email body
- `LeadSpaces` and `MaxLineLength` control text formatting (80-character email lines with 12-space indentation)
- Note arrays `PkupNoteLines`, `DelNoteLines`, `OrdNoteLines` are declared but never used in this function
- `ThisOrderType` determines which section an order belongs to (10=New, 20=Existing, 30=Insufficient)

### Block 3: Clear Existing Email Body Table
```vba
'empty outlook message table
With eMailBody
    If Not .EOF Then
        .MoveFirst
        Do Until .EOF
            .Delete
            .MoveNext
        Loop
    End If
End With
```
**Explanation**:
- Removes all existing records from the email body table
- Ensures a clean slate for building the new email message
- Classic DAO pattern: check for records, move to first, loop through deleting all
- This prevents old email content from appearing in new messages

### Block 4: Main Processing Loop - Order Type Determination
```vba
With EmailInfo
    If Not .EOF Then
        .MoveFirst
        Do Until .EOF
            NewOrderNo = !oi_orderno
            ThisEmail = !OI_email
            ThisDTTM = !oi_dttm
            ThisSender = !OI_thissender
            If NewOrderNo = 0 And _
                (!OI_CustomerID = 0 Or !OI_PkupID = 0 Or _
                  !OI_DelID = 0 Or Len(Trim(!oi_hawb)) <> 8) Then
                ThisOrderType = 30
            ElseIf NewOrderNo = 0 Then
                ThisOrderType = 10
            Else
                ThisOrderType = 20
            End If
```
**Explanation**:
- Loops through all suggested orders in the `EmailInfo` recordset
- Determines order classification based on order number and data completeness:
  - **Type 30** (Insufficient): NewOrderNo=0 AND missing required data (Customer, Pickup, Delivery, or invalid HAWB)
  - **Type 10** (New Order): NewOrderNo=0 but has all required data
  - **Type 20** (Existing): NewOrderNo exists (order already in system)
- This classification drives which section of the email the order appears in
- HAWB validation requires exactly 8 characters (standard air waybill format)

### Block 5: Section Header Creation - New Orders
```vba
If ThisOrderType = 10 And Not NewOrderHdrCreated Then
    '========== insert new order header if not already done =======
    NewOrderHdrCreated = True
    LineNo = LineNo + 1
    eMailBody.AddNew
        eMailBody!drlinetype = ThisOrderType
        eMailBody!drlineno = LineNo
        eMailBody!drline = ""
    eMailBody.Update  '<== inserts blank line

    LineNo = LineNo + 1
    eMailBody.AddNew
        eMailBody!drlinetype = ThisOrderType
        eMailBody!drlineno = LineNo
        eMailBody!drline = String(70, "=")
    eMailBody.Update

    LineNo = LineNo + 1
    eMailBody.AddNew
        eMailBody!drlinetype = ThisOrderType
        eMailBody!drlineno = LineNo
        eMailBody!drline = String(25, "=") & " New Orders Created " & String(25, "=")
    eMailBody.Update '<== Inserts new order header"

    LineNo = LineNo + 1
    eMailBody.AddNew
        eMailBody!drlinetype = ThisOrderType
        eMailBody!drlineno = LineNo
        eMailBody!drline = String(70, "=")
    eMailBody.Update

    LineNo = LineNo + 1
    eMailBody.AddNew
        eMailBody!drlinetype = ThisOrderType
        eMailBody!drlineno = LineNo
        eMailBody!drline = ""
    eMailBody.Update  '<== inserts blank line
```
**Explanation**:
- Creates section header only once for all new orders (flag pattern)
- Inserts formatted header with visual separators:
  - Blank line
  - 70 equals signs
  - Centered title "New Orders Created" with 25 equals on each side
  - 70 equals signs
  - Blank line
- Each line is a separate database record with `drlinetype`, `drlineno`, and `drline` fields
- `LineNo` increments sequentially to maintain order when email is reconstructed
- This pattern is repeated for other section headers (Existing Orders, Insufficient Info)

### Block 6: Section Header Creation - Existing Orders
```vba
ElseIf ThisOrderType = 20 And Not ExistingOrderHdrCreated Then
    ExistingOrderHdrCreated = True
    '========== insert Existing order header if not already done =======
    NewOrderHdrCreated = True

    LineNo = LineNo + 1
    eMailBody.AddNew
        eMailBody!drlinetype = ThisOrderType
        eMailBody!drlineno = LineNo
    eMailBody.Update  '<== inserts blank line

    LineNo = LineNo + 1
    eMailBody.AddNew
        eMailBody!drlinetype = ThisOrderType
        eMailBody!drlineno = LineNo
        eMailBody!drline = String(70, "=")
    eMailBody.Update

    LineNo = LineNo + 1
    eMailBody.AddNew
        eMailBody!drlinetype = ThisOrderType
        eMailBody!drlineno = LineNo
        eMailBody!drline = String(22, "=") & " Regarding Existing Orders " & String(21, "=")
    eMailBody.Update '<== Inserts new order header"

    LineNo = LineNo + 1
    eMailBody.AddNew
        eMailBody!drlinetype = ThisOrderType
        eMailBody!drlineno = LineNo
        eMailBody!drline = String(70, "=")
    eMailBody.Update

    LineNo = LineNo + 1
    eMailBody.AddNew
        eMailBody!drlinetype = ThisOrderType
        eMailBody!drlineno = LineNo
    eMailBody.Update  '<== inserts blank line
```
**Explanation**:
- Similar structure to New Orders header but for existing orders
- Note: Line 691 sets `NewOrderHdrCreated = True` which appears to be a copy-paste error (should be `ExistingOrderHdrCreated`)
- Creates "Regarding Existing Orders" section with visual separators
- 22 and 21 equals signs balance around the title text

### Block 7: Section Header Creation - Insufficient Information
```vba
ElseIf ThisOrderType = 30 And Not InsufficientInfoHdrCreated Then
    InsufficientInfoHdrCreated = True
    '========== insert Insufficent data order header if not already done =======

    LineNo = LineNo + 1
    eMailBody.AddNew
        eMailBody!drlinetype = ThisOrderType
        eMailBody!drlineno = LineNo
        eMailBody!drline = ""
    eMailBody.Update  '<== inserts blank line

    LineNo = LineNo + 1
    eMailBody.AddNew
        eMailBody!drlinetype = ThisOrderType
        eMailBody!drlineno = LineNo
        eMailBody!drline = String(70, "=")
    eMailBody.Update

    LineNo = LineNo + 1
    eMailBody.AddNew
        eMailBody!drlinetype = ThisOrderType
        eMailBody!drlineno = LineNo
        eMailBody!drline = String(16, "=") & " Insufficient Data to create Order(s) " & String(16, "=")
    eMailBody.Update '<== Inserts new order header"

    LineNo = LineNo + 1
    eMailBody.AddNew
        eMailBody!drlinetype = ThisOrderType
        eMailBody!drlineno = LineNo
        eMailBody!drline = String(70, "=")
    eMailBody.Update

    LineNo = LineNo + 1
    eMailBody.AddNew
        eMailBody!drlinetype = ThisOrderType
        eMailBody!drlineno = LineNo
        eMailBody!drline = ""
    eMailBody.Update  '<== inserts blank line
```
**Explanation**:
- Creates header for orders that cannot be processed due to missing data
- "Insufficient Data to create Order(s)" title with 16 equals on each side
- Alerts dispatcher to orders requiring manual intervention
- Same pattern as previous headers with flag, separators, and blank lines

### Block 8: Create New Order (Type 10 Only)
```vba
'Begin processing the order

If ThisOrderType = 10 Then
'Stop
    Call CreateNewOrder(!OI_CoID, _
                        !OI_BrID, _
                        !OI_CustomerID, _
                        !oi_hawb, !OI_MAWB, _
                        !OI_PkupID, _
                        !OI_PkupDate, !OI_PkupStartTime, !OI_PkupEndTime, _
                        !oi_pkupnotes, _
                        !OI_DelID, _
                        !OI_DelDate, !OI_DelStartTime, !OI_DelEndTime, _
                        !oi_delnotes, _
                        !OI_Pieces, !OI_Weight, _
                        !OI_HAWBNotes, _
                        NewOrderNo, _
                        ThisSender, _
                        ELThisRun, ELThisLineNo, _
                        ThisEmail)
End If
```
**Explanation**:
- Only processes Type 10 orders (new orders with complete data)
- Calls `CreateNewOrder` sub with all order details
- Passes company ID, branch ID, customer info, HAWB/MAWB numbers
- Includes pickup and delivery details (IDs, dates, times, notes)
- Passes package info (pieces, weight, notes)
- Returns `NewOrderNo` which gets updated by the function
- Includes sender and email tracking info for notifications
- Type 20 (existing) and Type 30 (insufficient) orders are NOT created, only reported

### Block 9: Email Title/Subject Line
```vba
'email title

wrkNotes = "Email: " & !oi_dttm & ", " & !OI_email
If Len(wrkNotes) > MaxLineLength Then
    LineNo = LineNo + 1
    eMailBody.AddNew
        eMailBody!drlinetype = ThisOrderType
        eMailBody!drlineno = LineNo
        eMailBody!drline = "Email: " & !oi_dttm
    eMailBody.Update
    LineNo = LineNo + 1
    eMailBody.AddNew
        eMailBody!drlinetype = ThisOrderType
        eMailBody!drlineno = LineNo
        eMailBody!drline = "  " & !OI_email
    eMailBody.Update
Else
    LineNo = LineNo + 1
    eMailBody.AddNew
        eMailBody!drlinetype = ThisOrderType
        eMailBody!drlineno = LineNo
        eMailBody!drline = wrkNotes
    eMailBody.Update
End If
```
**Explanation**:
- Creates the title line for each order entry showing source email and timestamp
- Checks if combined string exceeds 80 characters (`MaxLineLength`)
- If too long: splits into two lines (date/time on first line, email subject on second with 2-space indent)
- If fits: displays on single line
- This handles long email subject lines gracefully

### Block 10: Sender Information
```vba
'Sender'
LineNo = LineNo + 1
eMailBody.AddNew
    eMailBody!drlinetype = ThisOrderType
    eMailBody!drlineno = LineNo
    eMailBody!drline = "From:  " & !OI_thissender
eMailBody.Update

'blank line
LineNo = LineNo + 1
eMailBody.AddNew
    eMailBody!drlinetype = ThisOrderType
    eMailBody!drlineno = LineNo
    eMailBody!drline = ""
eMailBody.Update
```
**Explanation**:
- Adds sender email address line
- Follows with blank line for visual separation
- Simple, straightforward display of who sent the original order email

### Block 11: Order Details - Header Line
```vba
'order details
LineNo = LineNo + 1
eMailBody.AddNew
    eMailBody!drlinetype = ThisOrderType
    eMailBody!drlineno = LineNo
    eMailBody!drline = "Order: " & NewOrderNo & ", " & HTC200F_Custinfo(!OI_CoID, !OI_BrID, !OI_CustomerID)
eMailBody.Update

LineNo = LineNo + 1
eMailBody.AddNew
    eMailBody!drlinetype = ThisOrderType
    eMailBody!drlineno = LineNo
    eMailBody!drline = Space(LeadSpaces) & "HAWB: " & !oi_hawb & ", MAWB: " & IIf(!OI_MAWB = "", "????????", !OI_MAWB) & _
                                        ", Pieces: " & !OI_Pieces & ", Weight: " & !OI_Weight
eMailBody.Update
```
**Explanation**:
- First line shows order number and customer info (via external `HTC200F_Custinfo` function)
- Second line (indented 12 spaces) shows shipment details:
  - HAWB (House Air Waybill)
  - MAWB (Master Air Waybill, displays "????????" if missing)
  - Number of pieces
  - Total weight
- This provides dispatcher with key shipment identifiers

### Block 12: Order Notes with Text Wrapping
```vba
'order notes
wrkNotes = Trim(!OI_HAWBNotes)
'Stop
If Len(wrkNotes) > MaxLineLength - (LeadSpaces + 10) Then
    Do Until wrkNotes = ""
        If Len(wrkNotes) > MaxLineLength - (LeadSpaces + 10) Then
            wrkNotes = Space(LeadSpaces + 10) & Trim(wrkNotes)
            ThisLineLength = HTC200F_SetLineLength(wrkNotes, MaxLineLength)

            If Left(wrkNotes, ThisLineLength) = "" Then Exit Do  ' not sure why this is needed

            LineNo = LineNo + 1
            eMailBody.AddNew
                eMailBody!drlinetype = ThisOrderType
                eMailBody!drlineno = LineNo
                eMailBody!drline = Left(wrkNotes, ThisLineLength)
            eMailBody.Update
            wrkNotes = Trim(Replace(wrkNotes, Left(wrkNotes, ThisLineLength), ""))
        Else
            LineNo = LineNo + 1
            eMailBody.AddNew
                eMailBody!drlinetype = ThisOrderType
                eMailBody!drlineno = LineNo
                eMailBody!drline = Space(LeadSpaces + 10) & wrkNotes
            eMailBody.Update
            wrkNotes = ""
        End If
    Loop
Else
    If wrkNotes <> "" Then
        LineNo = LineNo + 1
        eMailBody.AddNew
            eMailBody!drlinetype = ThisOrderType
            eMailBody!drlineno = LineNo
            eMailBody!drline = Space(LeadSpaces + 10) & wrkNotes
        eMailBody.Update
    End If
End If
```
**Explanation**:
- Handles HAWB notes with intelligent text wrapping
- Calculates available space: `MaxLineLength - (LeadSpaces + 10)` = 80 - 22 = 58 characters
- If notes fit: displays on single line with 22-space indent
- If too long: loops to wrap text across multiple lines:
  - Adds 22-space indent to text
  - Calls `HTC200F_SetLineLength` to find optimal break point (respects word boundaries)
  - Outputs line and removes processed text
  - Continues until all text is output
- Safety check: exits loop if line is empty (prevents infinite loop mentioned in code comment)
- This pattern is repeated multiple times throughout the function for different note fields

### Block 13: Blank Line Separator
```vba
'blank line
LineNo = LineNo + 1
eMailBody.AddNew
    eMailBody!drlinetype = ThisOrderType
    eMailBody!drlineno = LineNo
    eMailBody!drline = ""
eMailBody.Update
```
**Explanation**:
- Inserts blank line for visual separation between sections
- This pattern appears frequently to improve email readability

### Block 14: Pickup Date/Time Information
```vba
'pickup date/time
LineNo = LineNo + 1
eMailBody.AddNew
    eMailBody!drlinetype = ThisOrderType
    eMailBody!drlineno = LineNo
    eMailBody!drline = Space(LeadSpaces) & "Pickup: " & !OI_PkupDate & ", " & !OI_PkupStartTime & " - " & !OI_PkupEndTime
eMailBody.Update
```
**Explanation**:
- Displays pickup scheduling information
- Format: "Pickup: MM/DD/YYYY, HH:MM - HH:MM"
- 12-space indentation for consistency
- Shows date and time window for pickup

### Block 15: Pickup Location with Address Details
```vba
'pickup location
Dim FullAddr As String, AddrName As String, AddrLn1 As String, AddrCity As String
Dim AddrLn2 As String, AddrACIID As Integer
Dim AddrState As String, AddrZip As String, AddrCountry As String
Dim ADDRLat As String, AddrLon As String, AddrCarrierYN As Boolean
Dim AddrIntlYN As Boolean, AddrLocalyn As Boolean, AddrBRanchYN As Boolean
Dim AddrAssessorials As String

Call HTC200F_AddrInfo(!OI_CoID, !OI_BrID, !OI_PkupID, FullAddr, _
     AddrName, AddrLn1, AddrLn2, AddrCity, AddrState, AddrZip, AddrCountry, _
     ADDRLat, AddrLon, _
     AddrACIID, AddrCarrierYN, AddrIntlYN, AddrLocalyn, AddrBRanchYN, AddrAssessorials)

wrkNotes = FullAddr
If Len(wrkNotes) > MaxLineLength - (LeadSpaces + 10) Then
    Do Until wrkNotes = ""
        If Len(wrkNotes) > MaxLineLength - (LeadSpaces + 10) Then
            wrkNotes = Space(LeadSpaces + 10) & wrkNotes
            ThisLineLength = HTC200F_SetLineLength(wrkNotes, MaxLineLength)

            If Left(wrkNotes, ThisLineLength) = "" Then Exit Do  ' not sure why this is needed

            LineNo = LineNo + 1
            eMailBody.AddNew
                eMailBody!drlinetype = ThisOrderType
                eMailBody!drlineno = LineNo
                eMailBody!drline = Left(wrkNotes, ThisLineLength)
            eMailBody.Update
            wrkNotes = Replace(wrkNotes, Left(wrkNotes, ThisLineLength), "")
        Else
            LineNo = LineNo + 1
            eMailBody.AddNew
                eMailBody!drlinetype = ThisOrderType
                eMailBody!drlineno = LineNo
                eMailBody!drline = Space(LeadSpaces + 10) & wrkNotes
            eMailBody.Update
            wrkNotes = ""
        End If
    Loop
Else
    If wrkNotes <> "" Then
        LineNo = LineNo + 1
        eMailBody.AddNew
            eMailBody!drlinetype = ThisOrderType
            eMailBody!drlineno = LineNo
            eMailBody!drline = Space(LeadSpaces + 10) & wrkNotes
        eMailBody.Update
    End If
End If
```
**Explanation**:
- Retrieves complete address information via external `HTC200F_AddrInfo` function
- Gets structured data: name, address lines, city, state, zip, country, lat/lon, flags
- Uses `FullAddr` (formatted address string) for display
- Applies same text wrapping logic as order notes (22-space indent, 58-char lines)
- Although lat/lon and other details are retrieved, only formatted address is displayed
- This ensures dispatcher can locate the pickup point

### Block 16: Pickup Notes with Null Handling
```vba
'Pickup Notes
If IsNull(!oi_pkupnotes) Then
    wrkNotes = ""
Else
    wrkNotes = Trim(!oi_pkupnotes)
End If

If Len(wrkNotes) > MaxLineLength - (LeadSpaces + 10) Then
    Do Until wrkNotes = ""
        If Len(wrkNotes) > MaxLineLength - (LeadSpaces + 10) Then
            wrkNotes = Space(LeadSpaces + 10) & wrkNotes
            ThisLineLength = HTC200F_SetLineLength(wrkNotes, MaxLineLength)
            LineNo = LineNo + 1
            eMailBody.AddNew
                eMailBody!drlinetype = ThisOrderType
                eMailBody!drlineno = LineNo
                eMailBody!drline = Left(wrkNotes, ThisLineLength)
            eMailBody.Update
            wrkNotes = Replace(wrkNotes, Left(wrkNotes, ThisLineLength), "")
        Else

            If Left(wrkNotes, ThisLineLength) = "" Then Exit Do  ' not sure why this is needed

            LineNo = LineNo + 1
            eMailBody.AddNew
                eMailBody!drlinetype = ThisOrderType
                eMailBody!drlineno = LineNo
                eMailBody!drline = Space(LeadSpaces + 10) & wrkNotes
            eMailBody.Update
            wrkNotes = ""
        End If
    Loop
Else
    If wrkNotes <> "" Then
        LineNo = LineNo + 1
        eMailBody.AddNew
            eMailBody!drlinetype = ThisOrderType
            eMailBody!drlineno = LineNo
            eMailBody!drline = Space(LeadSpaces + 10) & wrkNotes
        eMailBody.Update
    End If
End If

'blank line
LineNo = LineNo + 1
eMailBody.AddNew
    eMailBody!drlinetype = ThisOrderType
    eMailBody!drlineno = LineNo
    eMailBody!drline = ""
eMailBody.Update
```
**Explanation**:
- Checks for null pickup notes and converts to empty string
- This prevents VBA errors when working with null database values
- Applies standard text wrapping (22-space indent)
- Version 2.02 notes (line 29-31) mention this null handling was added to prevent processing errors
- Ends with blank line separator
- Safety check in `Else` block positioned differently than previous instances (line 975 vs earlier placements)

### Block 17: Delivery Date/Time Information
```vba
'Delivery date/time
LineNo = LineNo + 1
eMailBody.AddNew
    eMailBody!drlinetype = ThisOrderType
    eMailBody!drlineno = LineNo
    eMailBody!drline = Space(LeadSpaces) & "Delivery: " & !OI_DelDate & ", " & !OI_DelStartTime & " - " & !OI_DelEndTime
eMailBody.Update
```
**Explanation**:
- Mirrors pickup date/time structure
- Format: "Delivery: MM/DD/YYYY, HH:MM - HH:MM"
- Shows delivery time window for dispatcher planning

### Block 18: Delivery Location with Address Details
```vba
'delivery location

Call HTC200F_AddrInfo(!OI_CoID, !OI_BrID, !OI_DelID, FullAddr, _
     AddrName, AddrLn1, AddrLn2, AddrCity, AddrState, AddrZip, AddrCountry, _
     ADDRLat, AddrLon, AddrACIID, _
     AddrCarrierYN, AddrIntlYN, AddrLocalyn, AddrBRanchYN, AddrAssessorials)

wrkNotes = FullAddr

If Len(wrkNotes) > MaxLineLength - (LeadSpaces + 10) Then
    Do Until wrkNotes = ""
        If Len(wrkNotes) > MaxLineLength - (LeadSpaces + 10) Then
            wrkNotes = Space(LeadSpaces + 10) & wrkNotes
            ThisLineLength = HTC200F_SetLineLength(wrkNotes, MaxLineLength)

            If Left(wrkNotes, ThisLineLength) = "" Then Exit Do  ' not sure why this is needed

            LineNo = LineNo + 1
            eMailBody.AddNew
                eMailBody!drlinetype = ThisOrderType
                eMailBody!drlineno = LineNo
                eMailBody!drline = Left(wrkNotes, ThisLineLength)
            eMailBody.Update
            wrkNotes = Replace(wrkNotes, Left(wrkNotes, ThisLineLength), "")
        Else
            LineNo = LineNo + 1
            eMailBody.AddNew
                eMailBody!drlinetype = ThisOrderType
                eMailBody!drlineno = LineNo
                eMailBody!drline = Space(LeadSpaces + 10) & wrkNotes
            eMailBody.Update
            wrkNotes = ""
        End If
    Loop
Else
    If wrkNotes <> "" Then
        LineNo = LineNo + 1
        eMailBody.AddNew
            eMailBody!drlinetype = ThisOrderType
            eMailBody!drlineno = LineNo
            eMailBody!drline = Space(LeadSpaces + 10) & wrkNotes
        eMailBody.Update
    End If
End If
```
**Explanation**:
- Identical structure to pickup location handling
- Retrieves delivery address information via `HTC200F_AddrInfo`
- Uses same text wrapping algorithm (22-space indent, 58-char max)
- Provides dispatcher with delivery destination details

### Block 19: Delivery Notes with Null Handling
```vba
'Delivery Notes
If IsNull(!oi_delnotes) Then
    wrkNotes = ""
Else
    wrkNotes = Trim(!oi_delnotes)
End If

If Len(wrkNotes) > MaxLineLength - (LeadSpaces + 10) Then
    Do Until wrkNotes = ""
        If Len(wrkNotes) > MaxLineLength - (LeadSpaces + 10) Then
            wrkNotes = Space(LeadSpaces + 10) & wrkNotes
            ThisLineLength = HTC200F_SetLineLength(wrkNotes, MaxLineLength)

            If Left(wrkNotes, ThisLineLength) = "" Then Exit Do  ' not sure why this is needed

            LineNo = LineNo + 1
            eMailBody.AddNew
                eMailBody!drlinetype = ThisOrderType
                eMailBody!drlineno = LineNo
                eMailBody!drline = Left(wrkNotes, ThisLineLength)
            eMailBody.Update
            wrkNotes = Replace(wrkNotes, Left(wrkNotes, ThisLineLength), "")
        Else
            If wrkNotes <> "" Then
                LineNo = LineNo + 1
                eMailBody.AddNew
                    eMailBody!drlinetype = ThisOrderType
                    eMailBody!drlineno = LineNo
                    eMailBody!drline = Space(LeadSpaces + 10) & wrkNotes
                eMailBody.Update
                wrkNotes = ""
            End If
        End If
    Loop
Else
    LineNo = LineNo + 1
    eMailBody.AddNew
        eMailBody!drlinetype = ThisOrderType
        eMailBody!drlineno = LineNo
        eMailBody!drline = Space(LeadSpaces + 10)
    eMailBody.Update
End If
```
**Explanation**:
- Handles delivery notes with null checking
- Similar wrapping logic to pickup notes
- Notable difference in `Else` block (lines 1092-1099): always adds a line with just indentation even if notes are empty
- This may be intentional to maintain consistent spacing, or could be a bug (adds blank indented line unnecessarily)
- Version 2.01 notes (lines 25-27) mention extra lines were added to prevent loop issues creating blank lines

### Block 20: Order Separator
```vba
'Dash Line
LineNo = LineNo + 1
eMailBody.AddNew
    eMailBody!drlinetype = ThisOrderType
    eMailBody!drlineno = LineNo
    eMailBody!drline = String(MaxLineLength, "-")
eMailBody.Update

'blank line
LineNo = LineNo + 1
eMailBody.AddNew
    eMailBody!drlinetype = ThisOrderType
    eMailBody!drlineno = LineNo
eMailBody.Update
.MoveNext
Loop
```
**Explanation**:
- Creates visual separator between orders
- 80-character line of dashes followed by blank line
- Moves to next record in `EmailInfo` recordset
- Loop continues until all orders are processed

### Block 21: Email Recipient Determination
```vba
    End If
End With

SendTo = "dispatch@harrahtransportation.com"

If Environ("computername") <> "HARRAHSERVER" Then
    SendTo = "tom.crabtree.2@gmail.com"
End If

Call EmailDispatcher(1, 1, SendTo, eMailSent, SentTo)
```
**Explanation**:
- Ends the main processing loop
- Sets default recipient to production dispatcher email
- Checks environment variable `computername` to detect production vs. test environment
- If not on production server: redirects email to developer's Gmail (test mode)
- Calls `EmailDispatcher` function to send the constructed email
- Passes company/branch IDs (both 1), recipient address, and output flags

### Block 22: Error Handler and Exit
```vba
On Error GoTo 0
Exit Sub

Bld_eMail_Error:

    MsgBox "Error " & Err.Number & " (" & Err.Description & ") in procedure Bld_eMail, line " & Erl & "."
    Stop
End Sub
```
**Explanation**:
- Resets error handler to default VBA behavior
- Normal exit point for successful execution
- Error handler displays message box with error number, description, and line number
- `Stop` statement halts execution for debugging (allows inspection of variable states)
- No error logging to database (unlike other functions in this module)
- Error handler is minimal compared to `CreateNewOrder` which has extensive error logging

## Dependencies

**Database Objects**:
- **Tables**:
  - `HTC200F_G020_T020 Outlook Body` - Email body line storage (written)
  - `HTC300_G040_T010A Open Orders` - Order creation (via CreateNewOrder)
  - `HTC300_G040_T012A Open Order Dims` - Dimension records (via CreateNewOrder)
  - `HTC300_G040_T014A Open Order Attachments` - Attachment tracking (via CreateNewOrder)
  - `HTC300_G040_T030 Orders Update History` - History logging (via CreateNewOrder)
  - `HTC350_G800_T010 ETOLog` - Error and processing log (via CreateNewOrder)

- **Queries**:
  - `HTC200F_G020_Q010 Suggested Orders Sorted` - Source data for email
  - `Htc200F_G020_Q060 Outlook Body Sorted` - Used by EmailDispatcher for sending

**External Dependencies**:
- **Functions/Subs**:
  - `HTC200F_Custinfo()` - Customer information formatting
  - `HTC200F_AddrInfo()` - Address lookup and formatting
  - `HTC200F_SetLineLength()` - Text wrapping line break calculation
  - `HTC350C_SendEmail()` - Email sending functionality
  - `CreateNewOrder()` - Order creation (same file)
  - `EmailDispatcher()` - Email sending to dispatcher (same file)

- **Global/Module Variables**: None explicitly accessed (uses only local and parameter variables)

- **Environment Variables**:
  - `computername` - Determines production vs. test environment for email routing

- **COM Objects**:
  - Likely uses Outlook or CDO for email sending (via HTC350C_SendEmail and EmailDispatcher)

## Migration Notes

**Complexity**: High

**Migration Strategy**: This function requires significant architectural changes for migration. The core logic (formatting and sending dispatcher emails) is sound but the implementation is tightly coupled to Access database patterns. Recommended approach:

1. **Phase 1 - Data Layer**: Replace DAO recordset operations with modern ORM (TypeORM/Prisma) or SQL query builder
2. **Phase 2 - Business Logic**: Extract email formatting logic into a template engine (Handlebars, EJS, React Email)
3. **Phase 3 - Email Service**: Replace Outlook automation with modern email API (SendGrid, AWS SES, nodemailer)
4. **Phase 4 - Testing**: Unit test each section (header creation, order formatting, text wrapping, email sending)

**Challenges**:

1. **Text Wrapping Logic**: The manual text wrapping algorithm (`HTC200F_SetLineLength`) is complex and fragile
   - Modern solution: Use CSS/HTML email templates with automatic wrapping
   - Or: Use a robust word-wrapping library in the target language

2. **Database Record-per-Line Pattern**: Email body is stored as individual database records (one per line)
   - This is inefficient and unusual
   - Modern approach: Store complete email as single text/HTML blob
   - Consider: Is this for audit trail? If so, store complete email + metadata

3. **Stateful Loop Processing**: Function uses flags (`NewOrderHdrCreated`, etc.) to control one-time header insertion
   - Modern approach: Group orders by type first, then iterate sections
   - Or: Use template engine with conditional blocks

4. **Mixed Responsibilities**: Function creates orders AND formats email AND sends email
   - Violates Single Responsibility Principle
   - Migrate: Separate into OrderCreationService, EmailFormattingService, EmailSendingService

5. **Hard-coded Formatting**: Magic numbers (80 chars, 12 spaces, 10 spaces) scattered throughout
   - Migrate: Extract to configuration constants
   - Consider: Make format configurable (dispatcher preferences)

6. **Environment Detection**: Uses Windows environment variable for prod vs. test
   - Modern approach: Use environment variables (NODE_ENV) or config files
   - Better: Inject email service with different implementations per environment

7. **Error Handling**: Minimal error handling compared to rest of module
   - No database logging of errors
   - Stop statement won't work in production
   - Migrate: Add comprehensive error logging and recovery

8. **Null Handling Patterns**: Inconsistent null checking (some places use IsNull, others check values)
   - Modern approach: Use nullable types with consistent null coalescing
   - TypeScript: `value ?? ''` or `value || ''`

9. **External Function Dependencies**: Five external functions must be migrated first
   - Create service interfaces for: CustomerService, AddressService, TextFormattingService, EmailService
   - Mock these during testing

10. **Email Client Dependency**: Likely requires Outlook installed on server
    - Not scalable or cloud-friendly
    - Migrate: Use SMTP or email API service

**Modern Equivalent**:

In a modern TypeScript/Node.js application, this would be implemented as:

```typescript
// Service class
class DispatchEmailService {
  async buildAndSendDispatchEmail(
    runDate: Date,
    orders: SuggestedOrder[]
  ): Promise<EmailResult> {
    // Group orders by type
    const newOrders = orders.filter(o => o.orderNo === 0 && o.isComplete);
    const existingOrders = orders.filter(o => o.orderNo > 0);
    const incompleteOrders = orders.filter(o => o.orderNo === 0 && !o.isComplete);

    // Create orders (delegate to OrderService)
    const createdOrders = await this.orderService.createOrders(newOrders);

    // Format email using template
    const emailHtml = await this.templateEngine.render('dispatcher-notification', {
      newOrders: createdOrders,
      existingOrders,
      incompleteOrders,
      formatAddress: this.addressService.formatFullAddress,
      maxLineLength: 80
    });

    // Send email
    const recipient = this.config.isProduction
      ? 'dispatch@harrahtransportation.com'
      : 'tom.crabtree.2@gmail.com';

    return await this.emailService.send({
      from: 'alert@harrahtransportation.com',
      to: recipient,
      subject: 'Automated eMail Order Processing',
      html: emailHtml
    });
  }
}
```

Template file (Handlebars):
```handlebars
{{#if newOrders.length}}
  <h2>========== New Orders Created ==========</h2>
  {{#each newOrders}}
    <div class="order">
      <p>Email: {{this.email}} - {{this.dateTime}}</p>
      <p>From: {{this.sender}}</p>
      <p>Order: {{this.orderNo}}, {{this.customerName}}</p>
      <p>  HAWB: {{this.hawb}}, MAWB: {{this.mawb}}, Pieces: {{this.pieces}}, Weight: {{this.weight}}</p>
      {{#if this.notes}}
        <p>  {{wordWrap this.notes 58}}</p>
      {{/if}}
      <p>  Pickup: {{this.pickupDate}}, {{this.pickupTimeStart}} - {{this.pickupTimeEnd}}</p>
      <p>    {{formatAddress this.pickupId}}</p>
      <p>  Delivery: {{this.deliveryDate}}, {{this.deliveryTimeStart}} - {{this.deliveryTimeEnd}}</p>
      <p>    {{formatAddress this.deliveryId}}</p>
      <hr>
    </div>
  {{/each}}
{{/if}}
```

This modern approach:
- Separates concerns (order creation, email formatting, email sending)
- Uses template engine for maintainable email layouts
- Handles errors with try/catch and proper logging
- Testable (mock services)
- Scalable (async operations, no database record-per-line)
- Configuration-driven (no hard-coded addresses)

---

## Analysis Summary

✅ **Analysis written to**: C:\Users\TheNo\software_projects\eto_js\docs\vba-analysis\HTC_350C_Sub_2_of_2_CreateOrders\Bld_eMail.md

✅ **Function cross-references identified**:
- **3** same file: CreateNewOrder, EmailDispatcher, (GetOrderNo indirectly)
- **4** external: HTC200F_Custinfo, HTC200F_AddrInfo, HTC200F_SetLineLength, HTC350C_SendEmail
- **Multiple** built-in VBA/Access functions

✅ **Behavioral blocks documented**: 22 detailed blocks covering all function logic from initialization through error handling
