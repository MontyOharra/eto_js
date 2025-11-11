# VBA Analysis: HTC_350C_Sub_2_of_2_CreateOrders.vba

**File**: vba-code/HTC_350C_Sub_2_of_2_CreateOrders.vba
**Last Updated**: 2025-11-11

## Table of Contents
- [Function: CreateNewOrder](#function-createneworder)

---

# Function: `CreateNewOrder`

**Type**: Sub
**File**: HTC_350C_Sub_2_of_2_CreateOrders.vba
**Analyzed**: 2025-11-11

## Signature
```vba
Sub CreateNewOrder(sCoID As Integer, _
                   sBrID As Integer, _
                   sCustomerID As Integer, _
                   SHAWB As String, sMAWB As String, _
                   sPkupID As Double, _
                   sPkupDate As String, sPkupStartTime As String, sPkupEndTime As String, _
                   sPkupNotes As String, _
                   sDelID As Double, _
                   sDelDate As String, sDelStartTime As String, sDelEndTime As String, _
                   sDelNotes As String, _
                   sPieces As Integer, sWeight As Integer, _
                   sHAWBNotes As String, _
                   NewOrderNo As Double, _
                   sSender As String, _
                   ELThisRun As Date, ELThisLineNo As Integer, OIThiseMail As String)
```

## Purpose & Overview

**Primary Purpose**: Creates a new order record in the HTC system based on parsed email data, including building the order record, dimensions, attachments, order history, and sending confirmation emails to both the customer and dispatcher.

**Input**:
- Company/Branch/Customer identifiers (sCoID, sBrID, sCustomerID)
- Air waybill numbers (SHAWB, sMAWB)
- Pickup information (ID, date, times, notes)
- Delivery information (ID, date, times, notes)
- Shipment details (pieces, weight, notes)
- Email processing metadata (sender, run date, line number, email ID)
- NewOrderNo (passed by reference to return the created order number)

**Output**:
- NewOrderNo is updated with the newly created order number
- Returns order creation status implicitly through database changes and log entries

**Side Effects**:
- Creates records in multiple database tables: Orders, Dims, Attachments, History, HAWB Values
- Updates Last Order Number and Orders In Work tables
- Sends confirmation emails to customer and dispatcher
- Writes comprehensive log entries tracking success/failure of each operation
- Copies PDF attachments from source to storage location

## Function Cross-References

### Functions in Same File
- None - This function does not call other functions defined in the same VBA file

### External Functions (NOT in this file)
- `HTC200_GetCusName()` - **EXTERNAL** - Retrieves customer name, tariff, QuickBooks info, and assessorials
- `HTC200F_AddrInfo()` - **EXTERNAL** - Retrieves complete address information including lat/lon for pickup and delivery
- `HTC200_GetACIArea()` - **EXTERNAL** - Gets ACI (Air Cargo Inc) area code from ACI ID
- `HTC200F_SetOrderType()` - **EXTERNAL** - Determines order type based on pickup/delivery locations and carrier flags (defined later in same file, lines 1818-1882)
- `HTC200F_NextOrderNo()` - **EXTERNAL** - Generates next available order number and updates Orders In Work table
- `HTC200_StoreAttachment()` - **EXTERNAL** - Copies PDF attachment from source to storage and validates file operation
- `HTC200_PosttoLON()` - **EXTERNAL** - Posts to Last Order Number table
- `HTC200_RemoveOIW()` - **EXTERNAL** - Removes entry from Orders In Work table
- `HTC350C_SendEmail()` - **EXTERNAL** - Sends email using CDO (Collaboration Data Objects)

### Built-in VBA/Access Functions
- `CurrentDb()` - Access function to get current database object
- `OpenRecordset()` - DAO method to open database recordsets
- `DateAdd()` - VBA date manipulation function
- `IsDate()` - VBA function to validate date values
- `IsNumeric()` - VBA function to validate numeric values
- `Len()`, `Trim()`, `Left()`, `Right()`, `Mid()`, `Replace()` - String manipulation functions
- `IIf()` - VBA inline conditional function
- `IsNull()` - VBA null checking function
- `Now()` - VBA function returning current date/time
- `FileLen()` - VBA function to get file size
- `Environ()` - VBA function to get environment variables
- `MsgBox()` - VBA message box display function
- `FormatCurrency()` - VBA number formatting function

## Detailed Behavioral Breakdown

### Block 1: Error Handler Setup and Variable Declarations (Lines 1155-1278)
```vba
On Error GoTo CreateNewOrder_Error
' ----------------------------------------------------------------
' Procedure Name: CreateNewOrder
' Purpose: Build a new order in HTC along with 1 dim, history recd,
'          one hawb employed record, and 1 attachment per attachment
'          in the sponsoring email.
' [Version history and comments]
' ----------------------------------------------------------------

Dim db As Database: Set db = CurrentDb

Dim NOrder As Recordset
Set NOrder = db.OpenRecordset("HTC300_G040_T010A Open Orders", dbOpenDynaset)

Dim NDim As Recordset
Set NDim = db.OpenRecordset("HTC300_G040_T012A Open Order Dims", dbOpenDynaset)

[... additional recordset declarations ...]

Dim DfltAgent As Integer: DfltAgent = 159
```
**Explanation**:
- Sets up comprehensive error handling that jumps to `CreateNewOrder_Error` label on any error
- Establishes database connection using DAO (Data Access Objects)
- Opens multiple recordsets for different database tables that will be modified during order creation
- Declares extensive working variables for address info, flags, and tracking order creation steps
- Sets default agent to 159 (SOS default agent)
- This block demonstrates the complexity of the operation - requiring access to 10+ different database tables

### Block 2: Retrieve Customer and Address Information (Lines 1279-1293)
```vba
Call HTC200_GetCusName(sCoID, sBrID, sCustomerID, wrkCusName, wrkCusTariff, wrkCusQBID, wrkCusQBName, wrkCusAssessorials)

Call HTC200F_AddrInfo(sCoID, sBrID, sPkupID, wrkPUFullAddr, _
     wrkPUAddrname, wrkPUAddrLn1, wrkPUAddrLn2, wrkPUAddrCity, wrkPUAddrState, _
     wrkPUAddrZip, wrkPUCountry, wrkPULat, wrkPULon, wrkPUACIID, _
     wrkPUCarrierYN, wrkPUIntlYN, wrkPULocalYN, wrkPUBranchYn, wrkAssessorial)

wrkPUACI = HTC200_GetACIArea(wrkPUACIID)

Call HTC200F_AddrInfo(sCoID, sBrID, sDelID, wrkDelFullAddr, _
     [... delivery address parameters ...])

wrkDelACI = HTC200_GetACIArea(wrkdelACIID)
```
**Explanation**:
- Retrieves customer information including name, pricing tariff, QuickBooks integration data, and assessorial charges
- Makes two calls to `HTC200F_AddrInfo()` - once for pickup location, once for delivery location
- Each address retrieval gets comprehensive data: full formatted address, individual components (name, line1, line2, city, state, zip, country), geographical coordinates (lat/lon), ACI ID, and boolean flags for carrier/international/local/branch
- Converts ACI IDs to ACI area codes (likely single-letter codes like "A", "B", "C", "D")
- This data is essential for determining order type and populating the order record

### Block 3: Determine Order Type (Lines 1296-1297)
```vba
wrkOrderType = HTC200F_SetOrderType(wrkPUACI, wrkPUBranchYn, wrkPUCarrierYN, _
                                   wrkDelACI, wrkDelBranchYn, wrkDelCarrierYN)
```
**Explanation**:
- Calls external function to determine the order type (Recovery, Drop, Point-to-Point, Hot Shot, Dock Transfer, Services, Storage, Transfer, Pickup, Delivery)
- Order type is determined by analyzing pickup/delivery ACI areas and whether locations are carriers, branches, etc.
- This is a critical business logic function that affects pricing and routing
- The function is defined later in the same file (lines 1818-1882)

### Block 4: Validate and Correct Pickup Date/Time (Lines 1301-1338)
```vba
If Not (IsDate(sPkupDate)) Then
    If Msg <> "" Then exMsg = exMsg & "; "
    exMsg = exMsg & "Bad Pkup Date (" & sPkupDate & "). "
    exMsg = exMsg & " Set to next business day (" & DateAdd("d", 1, Date) & ")"
    sPkupDate = DateAdd("d", 1, Date)
End If

If Len(Trim(sPkupStartTime)) = 5 Then
    If Not IsNumeric(Left(sPkupStartTime, 2)) Or _
       Not IsNumeric(Right(sPkupStartTime, 2)) Or _
       Mid(sPkupStartTime, 3, 1) <> ":" Then
          If exMsg <> "" Then exMsg = exMsg & "; "
          exMsg = exMsg & "Invalid pickup start time (" & sPkupStartTime & "). "
          exMsg = exMsg & "Standard start time (" & StdStartTime & ") used."
          sPkupStartTime = StdStartTime
    End If
Else
    If exMsg <> "" Then exMsg = exMsg & "; "
    exMsg = exMsg & "Invalid pickup time (" & sPkupStartTime & ").  "
    exMsg = exMsg & "Standard start time (" & StdStartTime & ") used."
    sPkupStartTime = StdStartTime
End If
```
**Explanation**:
- Comprehensive validation of pickup date and time values extracted from emails
- If pickup date is not a valid date, defaults to tomorrow (next business day)
- Validates time format is exactly "HH:MM" with numeric hours/minutes and colon separator
- If invalid, uses standard business hours (09:00 for start, 17:00 for end)
- Accumulates error messages in `exMsg` variable for logging
- This defensive programming ensures order creation succeeds even with malformed email data
- Similar validation is performed for pickup end time

### Block 5: Validate and Correct Delivery Date/Time (Lines 1340-1375)
```vba
If Not (IsDate(sDelDate)) Then
    If Msg <> "" Then exMsg = exMsg & "; "
    exMsg = exMsg & "Bad Delivery Date (" & sDelDate & "). "
    exMsg = exMsg & "Day after pickup date (" & DateAdd("d", 1, sPkupDate) & ") used."
    sDelDate = DateAdd("d", 1, sPkupDate)
End If

If Len(Trim(sDelStartTime)) = 5 Then
    If Not IsNumeric(Left(sDelStartTime, 2)) Or _
       Not IsNumeric(Right(sDelStartTime, 2)) Or _
       Mid(sDelStartTime, 3, 1) <> ":" Then
          [... correction logic ...]
    End If
Else
    [... default standard time ...]
End If
```
**Explanation**:
- Validates delivery date and times using same logic as pickup validation
- If delivery date is invalid, defaults to day after pickup date
- If delivery times are invalid, defaults to standard business hours (09:00-17:00)
- Continues accumulating error messages for logging
- This ensures logical date progression (delivery after pickup) even with bad data

### Block 6: Initialize Order Creation Tracking Flags (Lines 1378-1380)
```vba
OrderCreated = False: DimCreated = False: HistCreated = False
CustHAWBCreated = False: LonUpdated = False: AttachmentMade = False
OIWUpdated = False: eMailSent = False: SentTo = ""
```
**Explanation**:
- Initializes boolean flags to track success/failure of each order creation step
- These flags are used later to determine overall success and generate detailed log entries
- Allows atomic tracking of which operations succeeded even if later operations fail
- Critical for troubleshooting and audit trail

### Block 7: Create Order Record (Lines 1382-1462)
```vba
With NOrder
    NOrder.AddNew
        !M_COID = sCoID
        !M_BrID = sBrID
        !m_Orderno = NewOrderNo
        !M_OrderType = wrkOrderType
        !m_customerid = sCustomerID
        !m_customer = wrkCusName
        !M_CustAgent = DfltAgent
        !m_Tariff = wrkCusTariff
        !M_CustAssessorials = wrkCusAssessorials
        !M_HAWB = Trim(SHAWB)
        !M_MAWB = sMAWB
        !M_ProNbr = ""
        !M_OrderNotes = sHAWBNotes
        !M_PUDate = sPkupDate
        !M_PUTimeStart = sPkupStartTime
        !M_PUTimeEnd = sPkupEndTime
        [... pickup location details ...]
        !M_PUID = sPkupID
        !M_PUCo = wrkPUAddrname
        !M_PULocn = wrkPUAddrLn1 & ", " & IIf(Len(wrkPUAddrLn2) > 0, wrkPUAddrLn2 & ", ", "") & _
                    wrkPUAddrCity & ", " & wrkPUAddrState & ", " & wrkPUCountry
        !M_PUZip = wrkPUAddrZip
        !m_pulatitude = wrkPULat
        !m_pulongitude = wrkPULon
        [... delivery location details ...]
        !m_status = "ETO Generated": Svd_Status = !m_status
        !m_statseq = 35: Svd_StatSeq = !m_statseq
        !m_rate = 0
        !m_fsc = 0
        !m_services = 0
        !m_StorageChgs = 0
        !m_adjustments = 0
        !M_Charges = !m_rate + !m_fsc + !m_services + !m_adjustments + !m_StorageChgs
        !M_Costs = 0
        !M_QBCustomerListID = wrkCusQBID
        !M_QBCustFullName = wrkCusQBName
        !M_AutoAssessYN = False
        !M_WgtChgsCalcYN = False
    .Update
    OrderCreated = True
End With
```
**Explanation**:
- Creates the main order record in "HTC300_G040_T010A Open Orders" table
- Populates 60+ fields with validated data from email parsing and external lookups
- Sets order status to "ETO Generated" with status sequence 35 (indicating email-to-order automation)
- Builds formatted pickup/delivery location strings from address components
- Initializes all financial fields (rate, fuel surcharge, services, charges) to zero - will be calculated later
- Sets QuickBooks integration fields for invoicing
- Concatenates address line 2 only if it exists using IIf()
- Stores latitude/longitude for both pickup and delivery (added in version 2.0)
- Sets OrderCreated flag to True only after successful .Update
- This is the core database operation that creates the order

### Block 8: Create Dimension Record (Lines 1464-1482)
```vba
If OrderCreated Then
    ' Build and insert new dim
    With NDim
        .AddNew
            !od_coid = sCoID
            !od_brid = sBrID
            !od_orderno = NewOrderNo
            !od_dimid = 1
            !od_unittype = "EA"
            !od_unitqty = sPieces
            !od_unitheight = 1
            !od_unitlength = 1
            !od_Unitwidth = 1
            !od_unitweight = sWeight
            !od_unitdimweight = 0
        .Update
        DimCreated = True
    End With
End If
```
**Explanation**:
- Only executes if order was successfully created (OrderCreated = True)
- Creates a single dimension record for the order in "HTC300_G040_T012A Open Order Dims" table
- Sets unit type to "EA" (Each)
- Uses piece count from email (sPieces)
- Defaults dimensional measurements to 1x1x1 (actual dimensions not extracted from email)
- Records actual weight from email (sWeight)
- Sets dimensional weight to 0 (would need to be calculated based on volume)
- DimID is set to 1 (first/only dimension for this order)
- Sets DimCreated flag on success

### Block 9: Process and Attach PDF Files (Lines 1484-1527)
```vba
If OrderCreated Then
    LastPDFStoredThisOrder = ""
    With PDFs
        .MoveFirst
        AttachCount = 0
        Do Until .EOF
            If !txtemailhdr = OIThiseMail And _
                !pdfaddress <> LastPDFStoredThisOrder And _
                !txtcustomerid <> 0 Then
                    PDFFileName = Replace(!pdfaddress, "C:\HTC_EmailToParse\", "")
                    Call HTC200_StoreAttachment(DocSource & "\" & PDFFileName, _
                                                DocStorage, _
                                                sCoID, _
                                                sBrID, _
                                                sCustomerID, _
                                                NewOrderNo, _
                                                PDFFileName, _
                                                PDFDocPath, _
                                                FileStoreOK, _
                                                ELThisRun, _
                                                OIThiseMail, _
                                                ELThisLineNo, _
                                                sSender, _
                                                SHAWB)
                    If FileStoreOK Then
                        Attachments.AddNew
                            Attachments!att_coid = sCoID
                            Attachments!att_brid = sBrID
                            Attachments!att_orderno = NewOrderNo
                            Attachments!att_custid = sCustomerID
                            Attachments!att_path = PDFDocPath
                            Attachments!att_size = FileLen(PDFDocPath) / 1024
                        Attachments.Update
                        LastPDFStoredThisOrder = !pdfaddress
                        AttachCount = AttachCount + 1
                    End If
            End If
            .MoveNext
        Loop
    End With
    If AttachCount > 0 Then AttachmentMade = True
End If
```
**Explanation**:
- Only executes if order was successfully created
- Loops through all PDFs in "HTC200F_TxtFileNames" table
- Filters PDFs matching current email ID (OIThiseMail) and valid customer ID
- Prevents duplicate attachment storage using LastPDFStoredThisOrder tracking
- Calls external function `HTC200_StoreAttachment()` to copy PDF from source (C:\HTC_EmailToParse) to storage location
- If file copy succeeds (FileStoreOK), creates attachment record in "HTC300_G040_T014A Open Order Attachments"
- Records file path and size (converted to KB) in attachment record
- Increments AttachCount for each successful attachment
- Sets AttachmentMade flag if at least one attachment was stored
- DocSource and DocStorage paths are retrieved from Branch Info table in Block 1

### Block 10: Update Last Order Number and Orders In Work (Lines 1531-1535)
```vba
If OrderCreated Then
    ' post to Last Order Number; Remove oiw entry
    Call HTC200_PosttoLON(sCoID, sBrID, NewOrderNo, LonUpdated)
    Call HTC200_RemoveOIW(sCoID, sBrID, NewOrderNo, OIWUpdated)
End If
```
**Explanation**:
- Only executes if order was successfully created
- Calls external function to update Last Order Number table with the newly created order number
- Removes the order number from Orders In Work table (since it's now a real order, not a pending one)
- Both functions return success status through ByRef parameters (LonUpdated, OIWUpdated)
- This bookkeeping ensures order number tracking remains consistent

### Block 11: Save Customer/HAWB Association (Lines 1538-1561)
```vba
If OrderCreated Then
    'Try to save the customer/hawb value.
    'In certain cases, reusing the Customer/HAWB value is OK, hence the 'on error' action

    On Error GoTo 0
        If Len(Trim(SHAWB)) > 0 Then
           Dim UsedHAWBs As Recordset
           Set UsedHAWBs = db.OpenRecordset("HTC300_G040_T040 HAWB Values", dbOpenDynaset)

           On Error Resume Next
                With UsedHAWBs
                     .AddNew
                         !existinghawbvalues = SHAWB
                         !hawbcoid = sCoID
                         !hawbbrid = sBrID
                         !hawbcustomerid = sCustomerID
                         !hawborder = NewOrderNo
                     .Update
                    .Close
                 End With
           On Error GoTo CreateNewOrder_Error
           CustHAWBCreated = True
        End If
End If
```
**Explanation**:
- Only executes if order was successfully created and HAWB is not empty
- Records customer/HAWB association in "HTC300_G040_T040 HAWB Values" table
- Uses "On Error Resume Next" to allow duplicate HAWB values (comment indicates reuse is sometimes acceptable)
- This prevents the same customer from using the same HAWB twice (or logs when they do)
- Restores error handler to CreateNewOrder_Error after this operation
- Sets CustHAWBCreated flag (always True if reached, even if update fails silently)
- HAWB (House Air Waybill) is a unique identifier for air shipments

### Block 12: Create Order History Record (Lines 1563-1582)
```vba
If OrderCreated Then
    ' Build and insert history
    With Hist
        .AddNew
            !Orders_UpdtDate = Now()
            !Orders_UpdtLID = "HarrahServer ETO"
            !Orders_CoID = sCoID
            !Orders_BrID = sBrID
            !Orders_OrderNbr = NewOrderNo
            !Orders_Changes = "Order #" & NewOrderNo & " Customer: " & wrkCusName & " (#" & _
                              sCustomerID & ") Created with 1 Dim, " & _
                                        "0 Assessorials, 0 Drivers, and " & AttachCount & " Attachments, assigned " & _
                                        FormatCurrency(0) & " using the " & wrkCusTariff & " tariff; " & _
                                        "Status = " & Svd_Status & "(" & Svd_StatSeq & ") & From eMail rec'd " & _
                                        sDtTm & ", " & OIThiseMail
        .Update
        HistCreated = True
    End With
End If
```
**Explanation**:
- Only executes if order was successfully created
- Creates audit trail record in "HTC300_G040_T030 Orders Update History" table
- Records current timestamp and user identifier ("HarrahServer ETO" indicates automated creation)
- Builds comprehensive change description including:
  - Order number and customer name/ID
  - Count of dimensions (1), assessorials (0), drivers (0), and attachments (AttachCount)
  - Initial charges ($0), tariff used, status, and source email
- This history record provides full audit trail for compliance and troubleshooting
- Sets HistCreated flag on success

### Block 13: Send Confirmation Email to Customer (Lines 1584-1601)
```vba
If OrderCreated Then
    If sSender <> "" Then
        wrkEMSubject = "Regarding your email dated " & Trim(sDtTm) & vbCrLf & "Subject " & _
                sSubject & vbCrLf & vbCrLf & " Concerning MAWB: " & IIf(sMAWB = "", "????????", sMAWB) _
                 & "  HAWB: " & SHAWB & vbCrLf & vbCrLf & "HTC order number " & NewOrderNo & " has been created " & _
                 "and forwarded to dispatch." & vbCrLf & vbCrLf & "Thank you for your business."
        'Test Test Test
        If Environ("computername") <> "HARRAHSERVER" Then
            sSender = "tom.crabtree.2@gmail.com"
        End If
        'Test Test Test
        Call HTC350C_SendEmail("Dispatch@HarrahTransportation.com", _
                               sSender, _
                               "Auto Response from Harrah Transportation", _
                               wrkEMSubject, eMailSent, SentTo)
    End If
End If
```
**Explanation**:
- Only executes if order was successfully created and sender email address is provided
- Builds confirmation email with order details: original email date/subject, MAWB/HAWB numbers, and new order number
- Uses "????????" placeholder if MAWB is blank
- Includes test mode logic: if not running on HARRAHSERVER, sends to developer email instead of customer
- Calls external email function with From address "Dispatch@HarrahTransportation.com"
- Sets eMailSent flag and SentTo address based on success
- Provides customer with immediate confirmation that their order was processed

### Block 14: Create Action Tracking Array (Lines 1603-1612)
```vba
Dim ActionArray As String: ActionArray = "........"
If OrderCreated Then Mid(ActionArray, 1, 1) = "X"
If DimCreated Then Mid(ActionArray, 2, 1) = "X"
If HistCreated Then Mid(ActionArray, 3, 1) = "X"
If CustHAWBCreated Then Mid(ActionArray, 4, 1) = "X"
If LonUpdated Then Mid(ActionArray, 5, 1) = "X"
If AttachmentMade Then Mid(ActionArray, 6, 1) = "X"
If OIWUpdated Then Mid(ActionArray, 7, 1) = "X"
If eMailSent Then Mid(ActionArray, 8, 1) = "X"
```
**Explanation**:
- Creates a visual representation of which operations succeeded
- Each position represents one operation: Order, Dim, Hist, HAWB, LON, Attachments, OIW, Email
- "X" indicates success, "." indicates failure or not attempted
- "XXXXXXXX" means complete success
- This provides a compact way to track partial failures for logging
- Used in next block to determine overall success and generate appropriate log messages

### Block 15: Write Comprehensive Log Entry - Success Path (Lines 1616-1633)
```vba
With Logfile
    ELThisLineNo = ELThisLineNo + 1
    .AddNew
        !etolog_coid = sCoID
        !etolog_brid = sBrID
        !etolog_thisrun = ELThisRun
        !etolog_emailid = OIThiseMail
        !etolog_lineno = ELThisLineNo
        !etolog_filepath = ""
        !etolog_sender = sSender
        !etolog_customerid = sCustomerID
        !etolog_hawb = SHAWB
        !etolog_orderno = NewOrderNo
        If ActionArray = "XXXXXXXX" Then
            !etolog_processedok = True
            !etolog_ordercreated = True
            !etolog_comment = "Order = " & NewOrderNo & " created and email sent to " & SentTo
```
**Explanation**:
- Writes to ETOLog table tracking email-to-order processing
- Increments line number for this processing run
- Records all key identifiers: company, branch, run date, email ID, customer, HAWB, order number
- If ActionArray = "XXXXXXXX" (all operations succeeded):
  - Marks processedok and ordercreated as True
  - Writes simple success message with order number and email recipient
- This log entry provides audit trail for successful order creation

### Block 16: Write Comprehensive Log Entry - Failure Path (Lines 1635-1717)
```vba
        Else
            !etolog_processedok = False
            !etolog_ordercreated = False
            wCmt = ""

            If Not OrderCreated Then
                If wCmt <> "" Then wCmt = wCmt & "; "
                wCmt = wCmt & "The order wasn't created."
            End If

            If OrderCreated Then
                If Not DimCreated Then
                    If wCmt <> "" Then wCmt = wCmt & "; "
                    wCmt = wCmt & "Order was created, dim was not" & vbCrLf
                End If
                [... similar checks for Hist, HAWB, LON, OIW, Attachments, Email ...]
            Else
                If DimCreated Then
                    If wCmt <> "" Then wCmt = wCmt & "; "
                    wCmt = wCmt & "Order wasn't created but Dim was," & vbCrLf
                End If
                [... similar checks for other operations ...]
            End If
            !etolog_comment = wCmt
        End If
    .Update
End With
```
**Explanation**:
- Handles cases where ActionArray is not "XXXXXXXX" (partial or complete failure)
- Marks processedok and ordercreated as False
- Builds detailed comment string explaining exactly which operations failed
- First checks if order wasn't created (primary failure)
- Then checks for two scenarios:
  1. Order WAS created but subsequent operations failed (e.g., "Order was created, dim was not")
  2. Order was NOT created but subsequent operations somehow succeeded (data inconsistency, e.g., "Order wasn't created but Dim was")
- Concatenates all failure messages with semicolons and line breaks
- Provides detailed troubleshooting information for administrators
- This logging is critical for diagnosing partial failures

### Block 17: Error Handler (Lines 1724-1755)
```vba
CreateNewOrder_Error:

    MsgBox "Error " & Err.Number & " (" & Err.Description & ") in procedure CreateNewOrder, line " & Erl & "."
  'Stop
    With Logfile
        ELThisLineNo = ELThisLineNo + 1
        .AddNew
            !etolog_coid = sCoID
            !etolog_brid = sBrID
            !etolog_thisrun = ELThisRun
            !etolog_emailid = OIThiseMail
            !etolog_lineno = ELThisLineNo
            !etolog_filepath = ""
            !etolog_sender = ""
            !etolog_customerid = 0
            !etolog_hawb = ""
            !etolog_ordercreated = False
            !etolog_orderno = 0
            !etolog_processedok = False
            !etolog_comment = "Module: " & ModuleName & ": LocationMark:" & ModLocnMark & _
                        ": Line No: " & Erl & _
                        " failed with error " & Err.Number & "; " & Err.Description
        .Update
    End With

    If AbortOrder Or (Err.Number > 0 And Err.Number <> 3022) Then '
        Stop
        Resume Next
    Else
        Resume Next
    End If
```
**Explanation**:
- Catches all runtime errors from the function
- Displays error message box with error number, description, and line number
- Writes error log entry with cleared/zeroed fields (since order creation failed)
- Records error number, description, and line number from Erl (Error Line)
- Special handling for error 3022 (duplicate key violation) - resumes without stopping
- For other errors or if AbortOrder flag is set, triggers Stop statement (debug mode) then resumes
- "Resume Next" continues execution rather than crashing the entire process
- The "Stop" statement is for debugging - it breaks execution in VBA IDE
- This ensures email processing continues even if one order fails

## Dependencies

**Database Objects**:

Tables:
- `HTC300_G040_T010A Open Orders` - Main orders table
- `HTC300_G040_T012A Open Order Dims` - Order dimensions/items table
- `HTC300_G040_T014A Open Order Attachments` - PDF attachments table
- `HTC300_G040_T030 Orders Update History` - Order audit trail
- `HTC300_G040_T040 HAWB Values` - Used HAWB numbers tracking
- `HTC300_G040_T000 Last OrderNo Assigned` - Last order number counter
- `HTC300_G040_T005 Orders In Work` - Pending orders being created
- `HTC350_G800_T010 ETOLog` - Email-to-order processing log
- `HTC300_G000_T020 Branch Info` - Branch configuration including document storage paths
- `HTC200F_TxtFileNames` - Parsed email data and PDF paths

Queries:
- None directly used (queries are used by external functions)

Forms:
- None

Reports:
- None

**External Dependencies**:
- CDO (Collaboration Data Objects) - Used by HTC350C_SendEmail for sending emails
- File System - FileLen() function to get file sizes, file copy operations
- Environment Variables - Environ("computername") to detect production vs. test environment
- External Functions - Approximately 9 external helper functions (detailed in Cross-References section)

**Global Variables/State**:
- ModuleName - Referenced in error handler but not declared in this function (likely module-level variable)
- ModLocnMark - Referenced in error handler but not declared in this function (likely module-level variable)
- sDtTm - Referenced but not declared in this function (likely passed from calling context)
- sSubject - Referenced but not declared in this function (likely passed from calling context)
- Msg - Referenced but not properly initialized (line 1302, 1341 - should be exMsg)
- LONumberUpdated - Variable misspelling on line 1267 (declared as LonUpdated elsewhere)

## Migration Notes

**Complexity**: High

**Migration Strategy**:
This function should be decomposed into multiple smaller functions/services in the modern system:
1. Order validation service (validates dates, times, addresses)
2. Order creation service (creates order record with transaction)
3. Attachment service (handles file storage and database records)
4. Email notification service (sends confirmations)
5. Audit logging service (tracks all operations)

Consider using a database transaction to ensure atomicity - either all operations succeed or all are rolled back. The current VBA implementation tracks individual operation success but doesn't rollback on partial failure.

**Challenges**:

1. **DAO to Modern ORM**: The function uses DAO (Data Access Objects) with recordsets. Modern migration would use an ORM like Prisma (TypeScript) or SQLAlchemy (Python) with parameterized queries and models.

2. **Transaction Management**: Currently, there's no explicit transaction. Each database operation commits independently. Modern implementation should wrap all operations in a single database transaction for atomicity.

3. **Complex Business Logic**: The function performs 8 distinct operations with interdependencies. Need to preserve the logic: "if order created, then create dim, then attach files, then update tracking tables, then send emails." This state machine should be explicitly modeled.

4. **Error Handling Philosophy**: VBA uses "On Error Resume Next" and tracks partial failures. Modern approach would use try/catch with explicit rollback and error accumulation.

5. **String Manipulation**: Heavy use of VBA string functions (Left, Right, Mid, Replace, Trim) for address formatting and validation. Modern languages have better string handling and regex support.

6. **File Operations**: Direct file system access using VBA functions. Modern implementation would use file storage service (AWS S3, Azure Blob Storage) with proper error handling and virus scanning.

7. **Email Sending**: Uses CDO (legacy Microsoft technology). Modern implementation would use SendGrid, Amazon SES, or similar email service APIs with proper templating and delivery tracking.

8. **Environment Detection**: Uses Environ("computername") to detect production vs. test. Modern approach uses environment variables (process.env) or configuration management.

9. **Synchronous Operations**: All operations are synchronous and blocking. Modern implementation could use async/await for file operations and email sending to improve performance.

10. **Hardcoded Business Rules**: Default agent ID (159), standard business hours (09:00-17:00), status codes ("ETO Generated", 35) are hardcoded. Should be configuration or constants.

11. **Date/Time Validation**: Custom validation logic for "HH:MM" format. Modern approach would use date/time libraries (date-fns, moment.js, datetime in Python) with proper timezone handling.

12. **Action Tracking Array**: Uses string manipulation to track operation success ("........" → "XXXXXXXX"). Modern approach would use a structured object or array of operation results.

13. **Recordset Navigation**: Loops through recordsets with .MoveFirst, .EOF pattern. Modern ORM would return arrays/collections that can be iterated with forEach/map.

14. **Variable Naming**: Mix of Hungarian notation (wrkPUAddr) and abbreviated names (sBrID, sCoID). Modern style guides prefer clear, descriptive names.

15. **Global Variable Dependencies**: References undefined variables (ModuleName, ModLocnMark, sDtTm, sSubject, Msg) that must exist in calling context. Modern approach uses dependency injection or explicit parameters.

**Modern Equivalent**:

In a TypeScript/Node.js system with Prisma ORM:

```typescript
async function createNewOrder(
  orderData: OrderCreationDTO,
  emailMetadata: EmailMetadata
): Promise<OrderCreationResult> {
  const { company, branch, customer, hawb, mawb, pickup, delivery, shipment, sender } = orderData;

  // Start database transaction
  return await prisma.$transaction(async (tx) => {
    const result: OrderCreationResult = {
      success: false,
      orderNumber: null,
      operations: {
        orderCreated: false,
        dimCreated: false,
        historyCreated: false,
        hawbSaved: false,
        attachmentsProcessed: false,
        emailSent: false
      },
      errors: []
    };

    try {
      // Validate and correct input data
      const validatedData = await validateOrderData(orderData);

      // Get next order number
      const orderNumber = await getNextOrderNumber(company.id, branch.id);

      // Retrieve customer and address info
      const customerInfo = await getCustomerInfo(customer.id);
      const pickupAddress = await getAddressInfo(pickup.id);
      const deliveryAddress = await getAddressInfo(delivery.id);

      // Determine order type
      const orderType = determineOrderType(pickupAddress, deliveryAddress);

      // Create order record
      const order = await tx.order.create({
        data: {
          companyId: company.id,
          branchId: branch.id,
          orderNumber: orderNumber,
          orderType: orderType,
          customerId: customer.id,
          hawb: hawb,
          mawb: mawb,
          status: OrderStatus.ETO_GENERATED,
          // ... all other fields
        }
      });
      result.operations.orderCreated = true;
      result.orderNumber = orderNumber;

      // Create dimension record
      await tx.orderDimension.create({
        data: {
          orderId: order.id,
          dimId: 1,
          unitType: 'EA',
          quantity: shipment.pieces,
          weight: shipment.weight,
          // ... other dimension fields
        }
      });
      result.operations.dimCreated = true;

      // Process attachments
      const attachments = await processAttachments(
        emailMetadata.attachments,
        order.id,
        customer.id
      );
      result.operations.attachmentsProcessed = attachments.length > 0;

      // Save HAWB association
      await saveHAWBAssociation(tx, customer.id, hawb, orderNumber);
      result.operations.hawbSaved = true;

      // Update tracking tables
      await updateOrderTracking(tx, company.id, branch.id, orderNumber);

      // Create history record
      await tx.orderHistory.create({
        data: {
          orderId: order.id,
          updatedBy: 'ETO_System',
          changes: buildHistoryMessage(order, attachments.length),
          createdAt: new Date()
        }
      });
      result.operations.historyCreated = true;

      // Send confirmation email (async, outside transaction)
      setImmediate(async () => {
        try {
          await sendOrderConfirmation(sender, order, emailMetadata);
          result.operations.emailSent = true;
        } catch (emailError) {
          logger.error('Failed to send confirmation email', { error: emailError, orderNumber });
        }
      });

      // Log success
      await logOrderCreation(tx, {
        emailId: emailMetadata.id,
        orderNumber: orderNumber,
        success: true,
        operations: result.operations
      });

      result.success = true;
      return result;

    } catch (error) {
      // Log detailed error
      await logOrderCreation(tx, {
        emailId: emailMetadata.id,
        orderNumber: null,
        success: false,
        error: error.message,
        operations: result.operations
      });

      result.errors.push(error.message);
      throw error; // Rollback transaction
    }
  });
}
```

This modern implementation provides:
- Explicit transaction management with automatic rollback
- Async/await for non-blocking operations
- Strongly typed data structures (DTOs)
- Structured error handling
- Separation of concerns (validation, data retrieval, business logic)
- Proper logging and audit trail
- Email sending outside transaction to avoid delays

---
