# Function: `prep_AllParsedPDFs`

**Type**: Sub
**File**: HTC_350C_Sub_1_of_2_translation.vba
**Analyzed**: 2025-11-11

## Signature
```vba
Sub prep_AllParsedPDFs(AlertTrigger As String, CoID As String, BrID As String, ELThisLineNbr As Integer, NormalEnd As Boolean)
```

---

## Purpose & Overview

**Primary Purpose**: This function processes parsed PDF data to expand SOS Alert documents that contain multiple Delivery Receipts into separate Alert entries, with one Delivery Receipt per Alert. This normalization ensures each Alert document has a 1:1 relationship with a Delivery Receipt for downstream processing.

**Input**:
- `AlertTrigger` (String): The signature pattern that identifies an SOS Alert document (typically "AAA LL EEEEEEEEE RRRRRRRR TTTTTTTTTT")
- `CoID` (String): Company ID for logging purposes
- `BrID` (String): Branch ID for logging purposes
- `ELThisLineNbr` (Integer): Current line number in the ETO log (passed by reference)
- `NormalEnd` (Boolean): Output parameter indicating whether processing completed successfully

**Output**:
- Modifies the `AllParsedPDFs` table by removing multi-delivery-receipt Alerts and replacing them with individual Alert entries
- Updates the `NormalEnd` parameter to indicate success or failure
- Creates log entries in the ETOLog table if errors occur

**Side Effects**:
- Modifies database tables: `HTC200F_G030_Q000B All ParsedPDFs Sorted`, `HTC200F_G030_T010 SvdAlertHdrs`, `HTC200F_G030_T020 addonParsedpdfs`
- Runs an append query to merge addon records back into the main table
- Creates error log entries if processing fails

---

## Function Cross-References

### Functions in Same File
None - This is a standalone sub within the file

### External Functions (NOT in this file)
None directly called

### Built-in VBA/Access Functions
- `CurrentDb()` - Opens reference to current Access database
- `OpenRecordset()` - Opens DAO recordsets for table manipulation
- `Left()`, `Right()`, `Len()`, `Trim()`, `InStr()` - String manipulation functions
- `IsNull()` - Checks for null values
- `Val()` - Converts string to numeric value
- `Format()` - Formats date/time values
- `DoCmd.SetWarnings` - Controls Access warning dialogs
- `DoCmd.OpenQuery` - Executes saved Access query

### Database Operations
- **Query**: `HTC200F_G030_Q020 Append AddOnParsedPDFs` - Appends processed Alert entries back to main table

---

## Detailed Behavioral Breakdown

### Block 1: Error Handler Setup and Database Connection
```vba
On Error GoTo prep_AllParsedPDFs_Error
Dim db As Database: Set db = CurrentDb
```
**Explanation**:
- Sets up error handling to jump to custom error handler at end of function
- Establishes connection to current Access database for all subsequent operations

---

### Block 2: Open Required Recordsets
```vba
Dim APPDFs As Recordset
Set APPDFs = db.OpenRecordset("HTC200F_G030_Q000B All ParsedPDFs Sorted", dbOpenDynaset)

Dim SvdAlertInfo As Recordset
Set SvdAlertInfo = db.OpenRecordset("HTC200F_G030_T010 SvdAlertHdrs", dbOpenTable)

Dim AddonParsedPDFS As Recordset
Set AddonParsedPDFS = db.OpenRecordset("HTC200F_G030_T020 addonParsedpdfs", dbOpenTable)

Dim Logfile As Recordset
Set Logfile = db.OpenRecordset("HTC350_G800_T010 ETOLog", dbOpenDynaset)
```
**Explanation**:
- Opens four recordsets for the processing pipeline:
  1. **APPDFs**: The main sorted table of all parsed PDF text lines
  2. **SvdAlertInfo**: Temporary storage for Alert header lines that will be reused
  3. **AddonParsedPDFS**: Temporary storage for new Alert entries being created
  4. **Logfile**: Error logging table
- Uses `dbOpenDynaset` for updateable sorted queries and `dbOpenTable` for direct table access

---

### Block 3: Variable Declarations
```vba
Dim StartLineNbr As Integer
Dim LineNbr As Integer
Dim EndLineNbr As Integer
Dim SvdFileHdr As String
Dim SvdFileEnd As String
Dim SvdAlertPreface As String
Dim DlvrRcptFlag As String: DlvrRcptFlag = "D E L I V E R Y   R E C E I P T"
Dim X As Integer
Dim AddOnStarted As Boolean
Dim SvdFN As Integer
Dim SvdLN As Integer
Dim DTRNbr As Integer
Dim PDFHdr As Variant      ' bookmark for beginning of current File Number
Dim PDFTrailer As Variant  ' bookmark last line of current file number
Dim ErrMsg As String
Dim AtLeastOneDRFound As Boolean: AtLeastOneDRFound = False
Dim BackToLineNbr As Integer
```
**Explanation**:
- Sets up tracking variables for processing state
- `DlvrRcptFlag` is the signature text that identifies a Delivery Receipt section
- `PDFHdr` and `PDFTrailer` store DAO Bookmark objects for navigating recordsets
- `DTRNbr` (Delivery/Transaction Number) tracks how many separate documents are created from one Alert
- `AtLeastOneDRFound` prevents processing Alerts that don't actually contain Delivery Receipts

---

### Block 4: Validate Input and Clear Addon Table
```vba
With APPDFs
    If .RecordCount = 0 Then
        ErrMsg = "There are no PDF's to process, ETO is terminated"
        GoTo prep_AllParsedPDFs_Error
    End If

    'Empty the AddonParsedPDFs table
    If Not AddonParsedPDFS.EOF Then
        AddonParsedPDFS.MoveFirst
        Do Until AddonParsedPDFS.EOF
            AddonParsedPDFS.Delete
            AddonParsedPDFS.MoveNext
        Loop
    End If
```
**Explanation**:
- Checks if there are any PDFs to process; exits with error if table is empty
- Clears the addon table from any previous run to ensure clean processing
- Uses standard DAO pattern: MoveFirst, loop until EOF, delete each record

---

### Block 5: Main Processing Loop - File Header Detection
```vba
If Not .EOF Then
    .MoveFirst
End If

If Not .EOF Then
    Do Until .EOF
        If Left(!txtline, 13) = "**FileStart**" Then
            SvdFN = !FN
            SvdFileHdr = !txtline
            PDFHdr = .Bookmark
            DTRNbr = 0
        End If

        .MoveNext
```
**Explanation**:
- Begins main loop through all parsed PDF records
- When a file header ("**FileStart**") is encountered:
  - Saves the file number (FN)
  - Saves the complete header line
  - Creates a bookmark to this position for later navigation
  - Resets the delivery/transaction counter to 0
- This sets up the context for processing each individual PDF document

---

### Block 6: Alert Pattern Detection and Validation
```vba
If Trim(!txtline) = AlertTrigger Then
    AtLeastOneDRFound = False
    Do Until Left(!txtline, 11) = "**FileEnd**"
        .MoveNext
        If InStr(!txtline, DlvrRcptFlag) > 0 Then AtLeastOneDRFound = True
    Loop

    If Not AtLeastOneDRFound Then
        'Same thing that happens if it's not an alerttrigger.
        .Bookmark = PDFHdr: .MoveNext   'move to the line AFTER the PDF Header
        GoTo TheresNoDR
    End If
```
**Explanation**:
- Checks if the current line matches the Alert trigger pattern
- Scans through the entire file to verify at least one Delivery Receipt exists
- This is a critical validation: prevents processing Alerts that don't have delivery information
- If no Delivery Receipt found, jumps to `TheresNoDR` label to skip this document
- Otherwise, continues with Alert splitting logic

---

### Block 7: Save File Boundaries
```vba
SvdLN = !LN
SvdFileEnd = !txtline
PDFTrailer = .Bookmark
```
**Explanation**:
- At this point, recordset is positioned at the "**FileEnd**" line
- Saves the line number, content, and bookmark position
- These will be used when reconstructing each individual Alert document

---

### Block 8: Clear and Populate Alert Header Storage
```vba
'Empty the SvdAlertHdrs table from last encounter with an alert pdf
If Not SvdAlertInfo.EOF Then
    SvdAlertInfo.MoveFirst
    Do Until SvdAlertInfo.EOF
        SvdAlertInfo.Delete
        SvdAlertInfo.MoveNext
    Loop
End If

.Bookmark = PDFHdr
DTRNbr = DTRNbr + 1

Do Until Left(!txtline, Len(DlvrRcptFlag)) = DlvrRcptFlag
    SvdAlertInfo.AddNew
        SvdAlertInfo!svdalertFN = !FN
        SvdAlertInfo!svdalertdtrn = DTRNbr
        SvdAlertInfo!svdalertln = !LN
        SvdAlertInfo!svdalerthdr = !txtline
    SvdAlertInfo.Update
    .MoveNext
Loop
```
**Explanation**:
- Clears the saved Alert header table from previous Alert processing
- Returns to the beginning of this Alert document using the saved bookmark
- Increments DTRNbr to 1 (first delivery transaction)
- Copies all lines from the Alert start up to (but not including) the first Delivery Receipt flag
- These header lines contain common Alert information that will be prepended to each split document
- This is the "reusable template" that gets duplicated for each Delivery Receipt

---

### Block 9: Split Alert into Multiple Documents
```vba
AddOnStarted = False

Do Until Left(!txtline, 11) = "**Fileend**"
    If Left(!txtline, Len(DlvrRcptFlag)) = DlvrRcptFlag Then
        If AddOnStarted Then
            AddonParsedPDFS.AddNew
                AddonParsedPDFS!FN = SvdFN
                AddonParsedPDFS!DTRN = DTRNbr
                AddonParsedPDFS!LN = SvdLN
                AddonParsedPDFS!addonparsedpdf = SvdFileEnd
            AddonParsedPDFS.Update
            DTRNbr = DTRNbr + 1
        Else
            AddOnStarted = True
        End If
```
**Explanation**:
- Main splitting logic that creates individual documents
- When a Delivery Receipt flag is encountered:
  - If this is NOT the first one (`AddOnStarted = True`), close out the previous document by adding a file trailer
  - Increment DTRNbr to prepare for the next document
  - If this IS the first one, just set the flag to indicate processing has started
- This creates a file trailer for document N-1 when starting document N

---

### Block 10: Copy Alert Header and Current Line to Addon Table
```vba
'Copy the Alert leading rows to the addon parsed pdf table
SvdAlertInfo.MoveFirst
Do Until SvdAlertInfo.EOF
    AddonParsedPDFS.AddNew
        AddonParsedPDFS!FN = SvdAlertInfo!svdalertFN
        AddonParsedPDFS!DTRN = DTRNbr
        AddonParsedPDFS!LN = SvdAlertInfo!svdalertln
        AddonParsedPDFS!addonparsedpdf = SvdAlertInfo!svdalerthdr
    AddonParsedPDFS.Update
    SvdAlertInfo.MoveNext
Loop

'Copy the txt line containing the DlvrRcptFlag to to the addon parsed pdf table
AddonParsedPDFS.AddNew
    AddonParsedPDFS!FN = !FN
    AddonParsedPDFS!DTRN = DTRNbr
    AddonParsedPDFS!LN = !LN
    AddonParsedPDFS!addonparsedpdf = !txtline
AddonParsedPDFS.Update
```
**Explanation**:
- For each new Delivery Receipt document being created:
  1. Copies all saved Alert header lines from the SvdAlertInfo table
  2. Each line gets the current DTRNbr (so they're grouped together)
  3. Copies the Delivery Receipt flag line itself
- This creates the document structure: Alert Header + Delivery Receipt Flag + (subsequent lines until next flag or end)

---

### Block 11: Copy Remaining Lines
```vba
Else
    AddonParsedPDFS.AddNew
        AddonParsedPDFS!FN = !FN
        AddonParsedPDFS!DTRN = DTRNbr
        AddonParsedPDFS!LN = !LN
        AddonParsedPDFS!addonparsedpdf = !txtline
    AddonParsedPDFS.Update
End If
.MoveNext
Loop
```
**Explanation**:
- For all lines that are NOT Delivery Receipt flags, simply copy them to the addon table
- They belong to the current document being built (identified by current DTRNbr)
- Continues until the file end marker is reached

---

### Block 12: Add Final File Trailer
```vba
AddonParsedPDFS.AddNew
    AddonParsedPDFS!FN = SvdFN
    AddonParsedPDFS!DTRN = DTRNbr
    AddonParsedPDFS!LN = SvdLN
    AddonParsedPDFS!addonparsedpdf = SvdFileEnd
AddonParsedPDFS.Update
```
**Explanation**:
- Adds the final file trailer to close out the last Delivery Receipt document
- Uses the saved file end marker from the original document

---

### Block 13: Clean Up Saved Alert Headers
```vba
SvdAlertInfo.MoveFirst
Do Until SvdAlertInfo.EOF
    SvdAlertInfo.Delete
    SvdAlertInfo.MoveNext
Loop
```
**Explanation**:
- Clears the saved Alert header table now that processing is complete
- Prepares it for the next Alert document (if any)

---

### Block 14: Mark Original Records for Deletion
```vba
'mark the original AllParsedPDFs for this alert for deletion
.Bookmark = PDFHdr  'Mark the header
.Edit
    !deleterow = True
.Update
.MoveNext

Do Until Left(!txtline, 11) = "**FileEnd**" ' Mark everything after the header
    .Edit                                   ' and b4 the trailer
        !deleterow = True
    .Update
    .MoveNext
Loop
.Edit   'Mark the trailer
    !deleterow = True
.Update
.MoveNext
```
**Explanation**:
- Returns to the beginning of the original Alert document
- Marks ALL records (header, body, trailer) with `deleterow = True`
- These will be removed later after the split documents have been added back
- This ensures the original multi-delivery-receipt Alert is replaced by individual documents

---

### Block 15: Handle Non-Alert Documents
```vba
Else
TheresNoDR:
    Do Until Left(!txtline, 11) = "**FileEnd**"
        .MoveNext: LineNbr = LineNbr + 1
    Loop
    .MoveNext
    If Not .EOF Then
        LineNbr = LineNbr + 1
    Else
        Exit Do
    End If
End If
```
**Explanation**:
- For documents that either:
  1. Don't match the Alert trigger pattern, OR
  2. Are Alerts but don't contain any Delivery Receipts
- Simply skip through all lines until the file end
- These documents are left unchanged in the table

---

### Block 16: Handle Edge Case (Empty Initial Table)
```vba
Else
    If AddonParsedPDFS.RecordCount > 0 Then
        AddonParsedPDFS.MoveFirst
        Do Until AddonParsedPDFS.EOF
            .AddNew
                !FN = AddonParsedPDFS!FN
                !DTRN = DTRNbr
                !LN = AddonParsedPDFS!LN
                !txtline = AddonParsedPDFS!addonparsedpdf
            .Update
        Loop
    End If
End If
```
**Explanation**:
- This appears to be legacy/defensive code for an edge case
- If the APPDFs table was initially empty, but AddonParsedPDFS has records, copy them over
- In practice, this block is unlikely to execute due to the empty table check at the start

---

### Block 17: Delete Marked Records
```vba
'remove the Alerts still existing in the input table

.MoveFirst: LineNbr = 0
Do Until .EOF
    If !deleterow Then .Delete
    .MoveNext: LineNbr = LineNbr + 1
Loop

If Not .EOF Then .MoveLast  'position at the end of the current
```
**Explanation**:
- Loops through entire APPDFs table
- Deletes any record marked with `deleterow = True` (the original multi-delivery-receipt Alerts)
- Positions at the end of the recordset for next operation

---

### Block 18: Append Split Documents Back to Main Table
```vba
End With

DoCmd.SetWarnings False
    DoCmd.OpenQuery "HTC200F_G030_Q020 Append AddOnParsedPDFs"
DoCmd.SetWarnings True
```
**Explanation**:
- Closes the With block for APPDFs recordset
- Runs an append query that adds all records from AddonParsedPDFS back into APPDFs
- Suppresses Access warnings during query execution
- This completes the replacement: removed multi-delivery-receipt Alerts, added individual ones

---

### Block 19: Clean Up Null Values
```vba
'Make sure there are NO rows with a null !txtline

With APPDFs
    .MoveFirst
    Do Until .EOF
        If IsNull(!txtline) Then
            .Edit
                !txtline = ""
            .Update
        End If
        .MoveNext
    Loop
End With
```
**Explanation**:
- Defensive programming: ensures no null values exist in the txtline field
- Converts any null values to empty strings
- Prevents downstream processing errors that might not handle nulls correctly

---

### Block 20: Success Exit
```vba
On Error GoTo 0
NormalEnd = True
Exit Sub
```
**Explanation**:
- Disables error handler
- Sets output parameter to indicate successful completion
- Exits the subroutine normally

---

### Block 21: Error Handler
```vba
prep_AllParsedPDFs_Error:

With Logfile
    ELThisLineNo = ELThisLineNo + 1
    .AddNew
        !etolog_coid = Val(CoID)
        !etolog_brid = Val(BrID)
        !etolog_thisrun = ELThisRun
        !etolog_emailid = Format(Now(), "mm/dd/yyyy; hh:mm:ss")
        !etolog_lineno = ELThisLineNo
        !etolog_filepath = ""
        !etolog_sender = ""
        !etolog_customerid = ""
        !etolog_hawb = ""
        !etolog_ordercreated = False
        !etolog_orderno = 0
        !etolog_processedok = False
        If Msg <> "" Then Msg = Msg & "; " & vbCrLf
        If Err.Number > 0 Then
            Msg = "Error " & Err.Number & " (" & Err.Description & ") in procedure prep_AllParsedPDFs, line " & Erl & "."
        Else
            Msg = ErrMsg
        End If
        !etolog_comment = Msg
    .Update
    NormalEnd = False
End With
```
**Explanation**:
- Error handler that catches any runtime errors or custom error conditions
- Creates a detailed log entry with:
  - Company and Branch IDs
  - Current timestamp
  - Error number and description
  - Line number where error occurred (Erl)
- Sets `NormalEnd = False` to signal failure to calling code
- Allows calling code to decide whether to continue or abort

---

## Dependencies

### Database Objects

**Tables**:
- `HTC200F_G030_Q000B All ParsedPDFs Sorted` (Query/Table) - Main source of parsed PDF text lines
- `HTC200F_G030_T010 SvdAlertHdrs` - Temporary storage for Alert header lines
- `HTC200F_G030_T020 addonParsedpdfs` - Temporary storage for split documents
- `HTC350_G800_T010 ETOLog` - Error and process logging table

**Queries**:
- `HTC200F_G030_Q020 Append AddOnParsedPDFs` - Appends split documents back to main table

**Forms**: None

**Reports**: None

### External Dependencies
- **DAO Library**: Uses DAO recordsets (Database, Recordset, Bookmark objects)
- **Global Variables**:
  - `ELThisRun` (Date) - Current run timestamp
  - `Msg` (String) - Message accumulator for error reporting

### Field Dependencies
Expected fields in recordsets:
- APPDFs: `FN`, `DTRN`, `LN`, `txtline`, `deleterow`
- SvdAlertInfo: `svdalertFN`, `svdalertdtrn`, `svdalertln`, `svdalerthdr`
- AddonParsedPDFS: `FN`, `DTRN`, `LN`, `addonparsedpdf`
- Logfile: `etolog_coid`, `etolog_brid`, `etolog_thisrun`, `etolog_emailid`, `etolog_lineno`, etc.

---

## Migration Notes

**Complexity**: Medium-High

**Migration Strategy**:
This function should be decomposed into a multi-stage data transformation pipeline:
1. Parser/filter stage to identify Alert documents
2. Validation stage to check for Delivery Receipts
3. Splitting stage to create individual documents
4. Merge stage to update the main dataset

**Challenges**:

1. **Recordset Bookmarks**: VBA uses DAO Bookmark objects for navigation. Modern equivalents:
   - Python: Store array indices or use pandas DataFrame with `iloc`
   - TypeScript/JavaScript: Store array indices or use cursor patterns with generators

2. **In-Place Table Modification**: VBA directly modifies database tables with Add/Edit/Delete. Modern approach:
   - Use immutable data transformations
   - Build new collections rather than modifying in place
   - Use database transactions for atomicity

3. **Multiple Recordsets in Memory**: Opens 4 recordsets simultaneously. Modern equivalent:
   - Load datasets into memory as arrays/DataFrames
   - Use streaming for large datasets
   - Consider memory constraints

4. **State Management**: Uses multiple mutable variables (`AddOnStarted`, `DTRNbr`, etc.). Modern approach:
   - Encapsulate state in objects/classes
   - Use functional programming patterns with reduce/fold operations
   - Make state transitions explicit

5. **Error Handling**: VBA's `On Error GoTo` pattern. Modern equivalent:
   - Try-catch blocks with specific exception types
   - Result/Either types for functional error handling
   - Logging middleware for consistent error capture

6. **String Pattern Matching**: Uses simple `Left()`, `InStr()` checks. Modern approach:
   - Regular expressions for more robust pattern matching
   - Parser libraries for structured text processing

7. **Procedural Logic**: Deeply nested loops with GoTo statements. Modern refactoring:
   - Extract into smaller, testable functions
   - Use state machine pattern for document processing
   - Replace GoTo with early returns or structured control flow

**Modern Equivalent**:

In Python with pandas:
```python
def split_alert_documents(pdf_data: pd.DataFrame, alert_trigger: str) -> pd.DataFrame:
    """Split multi-delivery-receipt Alerts into individual documents."""

    # Identify documents
    documents = group_by_file_markers(pdf_data)

    # Process each document
    result_frames = []
    for doc in documents:
        if is_alert_with_multiple_receipts(doc, alert_trigger):
            split_docs = split_by_delivery_receipt(doc)
            result_frames.extend(split_docs)
        else:
            result_frames.append(doc)

    return pd.concat(result_frames, ignore_index=True)
```

In TypeScript with functional approach:
```typescript
interface ParsedPDFLine {
  fn: number;
  dtrn: number;
  ln: number;
  txtline: string;
}

function splitAlertDocuments(
  pdfData: ParsedPDFLine[],
  alertTrigger: string
): ParsedPDFLine[] {
  return pdfData
    .reduce(groupIntoDocuments, [])
    .flatMap(doc =>
      isMultiReceiptAlert(doc, alertTrigger)
        ? splitByDeliveryReceipt(doc)
        : [doc]
    )
    .flat();
}
```

**Key Architecture Improvements**:
- Use streaming/chunking for large datasets
- Implement unit tests for each transformation stage
- Add validation schema for input/output data structures
- Use database transactions to ensure atomicity
- Implement retry logic for database operations
- Add comprehensive logging at each stage
- Consider using message queue for async processing if volume is high

**Data Quality Considerations**:
- The original code has minimal validation of data integrity
- Modern implementation should validate:
  - Every FileStart has a matching FileEnd
  - Delivery Receipt markers are properly formatted
  - No orphaned records after splitting
  - Line numbers are sequential
- Consider adding data quality metrics/monitoring

**Performance Considerations**:
- Original: O(n²) due to nested loops and repeated recordset navigation
- Modern: Can achieve O(n) with single-pass algorithms and proper indexing
- Consider batch processing for very large datasets
- Use database indexes on FN, DTRN, LN fields
