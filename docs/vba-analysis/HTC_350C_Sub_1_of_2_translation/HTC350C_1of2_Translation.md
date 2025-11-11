# VBA Analysis: HTC_350C_Sub_1_of_2_translation.vba

**File**: vba-code/HTC_350C_Sub_1_of_2_translation.vba
**Last Updated**: 2025-11-11

## Table of Contents
- [Function: HTC350C_1of2_Translation](#function-htc350c_1of2_translation)

---

# Function: `HTC350C_1of2_Translation`

**Type**: Sub
**File**: HTC_350C_Sub_1_of_2_translation.vba
**Analyzed**: 2025-11-11

## Signature
```vba
Sub HTC350C_1of2_Translation()
```

## Purpose & Overview

**Primary Purpose**: This is the main entry point for the Email-to-Order (ETO) process. It interprets SOS forms attached to emails to create new orders or add/alter information on existing orders. The function parses PDF documents converted to text files, identifies their format using pattern matching, extracts relevant shipping information, and prepares data for order creation.

**Input**: No direct parameters. Uses global module-level variables and reads from:
- Database tables (HTC000 WhosLoggedIn, HTC350_G800_T010 ETOLog, HTC200F_TxtFileNames)
- Parsed text files in C:\HTC_Parsed_PDF\
- File system objects for PDF/TXT file management

**Output**:
- Populates HTC200F_TxtFileNames table with extracted shipping information
- Creates entries in ETOLog table for audit trail
- Calls HTC350C_2of2_CreateOrders to create actual orders
- Moves processed files between directories

**Side Effects**:
- Creates/deletes records in WhosLoggedIn table (session management)
- Deletes old log file records and associated PDF/TXT files (>31 days old)
- Opens and updates form "HTC200F_G010_F010A Position" to show progress
- Terminates the Access application with Application.Quit when complete
- Extensive database modifications across multiple tables

## Function Cross-References

### Functions in Same File
- `Mine_TxtFile()` - Dispatches PDF processing to format-specific handlers based on pattern match
- `prep_AllParsedPDFs()` - Expands SOS Alerts with multiple delivery receipts into separate alert records

### External Functions (NOT in this file)
- `HTC200F_RemoveEmptyTxtFiles()` - **⚠️ EXTERNAL** - Removes null lines and empty files from parsed input
- `HTC200F_EM_DtTm()` - **⚠️ EXTERNAL** - Extracts date/time from filename
- `HTC200F_EM_Subject()` - **⚠️ EXTERNAL** - Extracts email subject and sender from filename
- `HTC200F_Wait()` - **⚠️ EXTERNAL** - Delay/wait function
- `HTC350C_2of2_CreateOrders()` - **⚠️ EXTERNAL** - Second step: creates orders from extracted data
- `HTC350C_PurgePDFFiles()` - **⚠️ EXTERNAL** - Purges old PDF files from processed directories
- `HTC200F_SOS_Routing()` - **⚠️ EXTERNAL** - Processes SOS Routing forms
- `HTC200F_SOS_BOL()` - **⚠️ EXTERNAL** - Processes SOS Bill of Lading forms (variant 1)
- `HTC200F_SOS_BOL2()` - **⚠️ EXTERNAL** - Processes SOS BOL variant 2
- `HTC200F_SOS_BOL3()` - **⚠️ EXTERNAL** - Processes SOS BOL variant 3
- `HTC200F_SOS_Dlvry_Rcpt()` - **⚠️ EXTERNAL** - Processes SOS Delivery Receipt forms
- `HTC200F_SOS_Alert()` - **⚠️ EXTERNAL** - Processes SOS Alert forms
- `HTC200F_SOS_MAWB()` - **⚠️ EXTERNAL** - Processes SOS Master Air Waybill forms
- `HTC200F_FA_FastBook()` - **⚠️ EXTERNAL** - Processes SOS Forward Air Fast Book forms
- `HTC200F_SOS_BatteryAdvisory2()` - **⚠️ EXTERNAL** - Processes SOS Battery Advisory forms
- `HTC200F_SOS_No_Format()` - **⚠️ EXTERNAL** - Handles unrecognized formats

### Built-in VBA/Access Functions
- `CurrentDb()` - Gets current database object
- `OpenRecordset()` - Opens database recordsets
- `DoCmd.SetWarnings`, `DoCmd.OpenQuery`, `DoCmd.OpenForm` - Access DoCmd operations
- `MsgBox()` - Display message boxes
- `Now()`, `Date()`, `DateDiff()`, `IsDate()`, `CDate()` - Date/time functions
- `Trim()`, `Left()`, `Right()`, `Mid()`, `Len()`, `InStr()`, `Replace()` - String manipulation
- `Val()`, `Format()` - Type conversion/formatting
- `Environ()` - Gets environment variables
- `Kill` - Deletes files
- `FileSystemObject` - File system operations

## Detailed Behavioral Breakdown

### Block 1: Version and Variable Initialization (Lines 139-155)
```vba
VersionID = "Version ID = 2.24, 2025-07-01 10:59 AM"

Dim ModuleName As String
Dim ModLocnMark As String

ModuleName = "HTC350C_1of2_Translation"
ModLocnMark = "MLC 01"

On Error GoTo ModuleFailed

Dim Msg As String: Msg = ""
Dim HAWBProcessed As Boolean

ELThisRun = Now()
ELThisLineNo = 0

MsgTitle = "HTC350C_1of2_Translation"
```
**Explanation**:
- Sets version ID to track code version throughout execution (displayed on forms and in logs)
- Initializes error tracking variables (ModuleName, ModLocnMark) used in error handler to identify where failures occur
- Sets up global error handler with `On Error GoTo ModuleFailed`
- Initializes ELThisRun timestamp to uniquely identify this execution run across all log entries
- ELThisLineNo tracks sequential log entry numbers for this run

### Block 2: Database Connection and Session Management Setup (Lines 159-194)
```vba
Dim db As Database: Set db = CurrentDb

Dim xServerName As String: xServerName = "HarrahServer"
Dim xPCName As String: xPCName = "HarrahServer"
Dim xPCLID As String: xPCLID = "ETOProcess"
Dim xWhosLoggedIn As String: xWhosLoggedIn = "HarrahServer"

Dim WLI As Recordset
Set WLI = db.OpenRecordset("HTC000 WhosLoggedIn", dbOpenDynaset)

With WLI
    .AddNew
        !wli_company = 1
        !wli_branch = 1
        !wli_homeserver = xServerName
        !wli_servertype = "network"
        !wli_staffid = 0
        !pcname = xPCName
        !pclid = xPCLID
        !WhosLoggedIn = xWhosLoggedIn
        !securitylevel = 10
        !logintime = Now()
    .Update
    .MoveFirst
    Do Until !wli_company = 1 And !wli_branch = 1 And _
             !pcname = Environ("computername") And _
             !pclid = Environ("username") And _
             !wli_staffid = 0
             Exit Do
        .MoveNext
    Loop
    If .EOF Then
        Msg = "Can't find WhosLoggedIn Just created"
        Ans = MsgBox(Msg, vbOKOnly, MsgTitle)
    End If
End With
```
**Explanation**:
- Opens connection to current Access database
- Creates a "session login" record in WhosLoggedIn table to track that the ETO process is running
- Uses hard-coded server name "HarrahServer" and process ID "ETOProcess" with security level 10
- This acts as a locking/tracking mechanism to prevent multiple simultaneous ETO processes
- Attempts to verify the record was created by searching for it (though the search logic appears to have issues with environment variable comparison)
- This session record will be deleted at the end of the process (Block 19)

### Block 3: Extract Session Variables and Configure Retention (Lines 197-210)
```vba
Dim wCoID As String: wCoID = WLI!wli_company
Dim wBrID As String: wBrID = WLI!wli_branch
Dim wHomeServer As String: wHomeServer = WLI!wli_homeserver
Dim wServerType As String: wServerType = WLI!wli_servertype
Dim wStaffID As Integer: wStaffID = WLI!wli_staffid
Dim wPCName As String: wPCName = WLI!pcname
Dim wPCLid As String: wPCLid = WLI!pclid
Dim wWhosLoggedIn As String: wWhosLoggedIn = WLI!WhosLoggedIn
Dim wSecLvl As Integer: wSecLvl = WLI!securitylevel
Dim DaysLogFileRecordLives As Integer

DaysLogFileRecordLives = 31
```
**Explanation**:
- Extracts session information from the WhosLoggedIn record just created
- Stores company ID (1), branch ID (1), and other session metadata in local variables
- Sets log file retention period to 31 days - older records and associated files will be purged
- These session variables (wCoID, wBrID, etc.) are passed to many sub-functions throughout the process

### Block 4: Additional Variable Declarations and Path Setup (Lines 212-271)
```vba
Dim X As Integer, MaxX As Integer, EndX As Integer
Dim Y As Integer, EndY As Integer
Dim Z As Integer, MaxZ As Integer, EndZ As Integer

Dim Logfile As Recordset
Set Logfile = db.OpenRecordset("HTC350_G800_T010 ETOLog", dbOpenDynaset)

' ... more variable declarations ...

InitialPath = "C:\HTC_Parsed"
Processpath = "C:\HTC_Processed Attachments"
UnrecognizedPath = "C:\HTC_Unrecognized Attachment"
```
**Explanation**:
- X, Y, Z variables used for nested loops: X=pattern index, Y=line in pattern, Z=character position
- Opens the ETOLog recordset for logging all operations and errors
- Declares numerous working variables for pattern matching, file processing, and data extraction
- Sets up three directory paths:
  - InitialPath: where parsed PDFs (as TXT) are initially placed
  - Processpath: where successfully processed files are moved
  - UnrecognizedPath: where unrecognized format files are moved

### Block 5: Log File Maintenance - Delete Old Records (Lines 276-310)
```vba
Dim fso As FileSystemObject
With Logfile
    If Not .EOF Then
        .MoveFirst
        On Error Resume Next
        Do Until .EOF
            For X = 1 To Len(Trim(!etolog_thisrun))
                If Mid(!etolog_thisrun, X, 1) = " " Then Exit For
            Next X
            wrkArea = Left(!etolog_thisrun, X - 1)
            If IsDate(wrkArea) Then
                ETO_Date = CDate(wrkArea)
                If DateDiff("d", ETO_Date, Date) > DaysLogFileRecordLives Then
                    wrkFilePath = Replace(!etolog_filepath, InitialPath, Processpath)
                    If fso.FileExists(wrkFilePath) Then Kill wrkFilePath
                    wrkFilePath = Replace(wrkFilePath, ".txt", ".pdf")
                    If fso.FileExists(wrkFilePath) Then Kill wrkFilePath

                    wrkFilePath = Replace(!etolog_filepath, InitialPath, UnrecognizedPath)
                    If fso.FileExists(wrkFilePath) Then Kill wrkFilePath
                    wrkFilePath = Replace(wrkFilePath, ".txt", ".pdf")
                    If fso.FileExists(wrkFilePath) Then Kill wrkFilePath

                    .Delete
                End If
            End If
            .MoveNext
        Loop
    End If
End With
On Error GoTo ModuleFailed
```
**Explanation**:
- Housekeeping operation that runs at the start of each ETO execution
- Parses the etolog_thisrun field to extract the date portion
- For records older than DaysLogFileRecordLives (31 days):
  - Deletes associated TXT and PDF files from Processpath directory
  - Deletes associated TXT and PDF files from UnrecognizedPath directory
  - Deletes the log record itself
- Uses "On Error Resume Next" to ignore errors if files don't exist
- Returns to normal error handling afterward

### Block 6: Query Execution and Input Table Preparation (Lines 320-333)
```vba
Dim EachPDF As Recordset
Set EachPDF = db.OpenRecordset("HTC200F_TxtFileNames", dbOpenTable)

DoCmd.SetWarnings False
    DoCmd.OpenQuery "HTC200F_G030_Q000A AllParsedPDFs Tbl Created"
DoCmd.SetWarnings True
```
**Explanation**:
- Opens the EachPDF recordset which will store the final extracted data from all PDFs
- Runs a query that creates/rebuilds the AllParsedPDFs table from source parsed text files
- SetWarnings False suppresses Access confirmation dialogs during query execution
- This table contains all parsed PDF lines with file number (FN), delivery receipt number (DTRN), and line number (LN) indexing

### Block 7: Define Pattern Signatures for Document Identification (Lines 335-408)
```vba
MaxX = 100

TxtFormatSig(1) = "SOS GLOBAL EXPRESS INC ROUTING INSTRUCTIONS"
TxtFormatName(1) = "SOS Routing"
TxtFormatHasInfo(1) = True
TxtFormatCustomer(1) = "SOSGlobal"

TxtFormatSig(2) = "##|########"
TxtFormatName(2) = "SOS BOL"
TxtFormatHasInfo(2) = True
TxtFormatCustomer(2) = "SOSGlobal"

' ... 12 more pattern definitions ...

TxtFormatSig(14) = "###   ###   #### ####                                       ### #### ####"
TxtFormatName(14) = "SOS MAWB2"
TxtFormatHasInfo(14) = True
TxtFormatCustomer(14) = "SOSGlobal"

EndX = 14
```
**Explanation**:
- Defines 14 document format signatures used for pattern matching
- Each signature has:
  - TxtFormatSig: Pattern to match (# = any alphanumeric, exact text must match, | separates lines)
  - TxtFormatName: Human-readable format name
  - TxtFormatHasInfo: Boolean indicating if format contains order information (vs. informational only)
  - TxtFormatCustomer: Customer identifier (all currently "SOSGlobal")
- Supported formats include: Routing, BOL (3 variants), Delivery Receipt, Alert, MAWB (2 variants), Cargo Acceptance, Battery Advisory (2 variants), Forward Air Fast Book, Inspection Notification
- EndX=14 defines how many patterns are active
- Comments show version history of pattern additions/changes

### Block 8: Validate Input and Remove Empty Files (Lines 410-433)
```vba
Dim AllParsedPDFsName As String: AllParsedPDFsName = "AllParsedPDFs"

Dim allparsedpdfs As Recordset
Set allparsedpdfs = db.OpenRecordset(AllParsedPDFsName, dbOpenDynaset)

allparsedpdfs.MoveFirst
allparsedpdfs.MoveLast
If allparsedpdfs.RecordCount = 0 Then
    With Logfile
        .AddNew
            !etolog_thisrun = ELThisRun
            !etolog_lineno = ELThisLineNo
            !etolog_emailid = "PDF Folder is empty"
            !etolog_processedok = True
            !etolog_comment = "There are no PDF's to process. This run is closed."
        .Update
    End With
    Application.Quit
End If

Call HTC200F_RemoveEmptyTxtFiles
```
**Explanation**:
- Opens the AllParsedPDFs table that was just created by the query
- Checks if there are any records to process (RecordCount = 0 means no PDFs)
- If no PDFs to process:
  - Logs a "normal" entry indicating empty folder
  - Immediately quits the Access application
- If PDFs exist, calls HTC200F_RemoveEmptyTxtFiles to clean up:
  - Empty lines from parsed text files
  - Files that contain nothing between **FileStart** and **FileEnd** markers

### Block 9: Identify and Log Empty Text Files (Lines 439-482)
```vba
Dim AllParsedPDF_Sorted As Recordset
Set AllParsedPDF_Sorted = db.OpenRecordset("HTC200F_G030_Q000B All ParsedPDFs Sorted", dbOpenDynaset)

With AllParsedPDF_Sorted
    .MoveFirst
    Do Until .EOF
        If Left(!txtline, 13) = "**Filestart**" Then
            .MoveNext
            wrkArea = !txtline
            If Left(wrkArea, 11) = "**FileEnd**" Then
                Logfile.AddNew
                    ELThisLineNo = ELThisLineNo + 1
                    Logfile!etolog_thisrun = ELThisRun
                    Logfile!etolog_emailid = Mid(wrkArea, InStr(wrkArea, "DTR_"), InStr(wrkArea, "_xxx_") - 1)
                    Logfile!etolog_lineno = ELThisLineNo
                    ' ... extract file path, sender, etc ...
                    Logfile!etolog_comment = "No Parsed Records between the file markers"
                Logfile.Update
                .MovePrevious
                .Delete
                .MoveNext
                .Delete
            Else
                .MoveNext
            End If
        End If
        .MoveNext
    Loop
End With
```
**Explanation**:
- Opens a sorted view of the parsed PDFs ordered by File Number, DTRN, Line Number
- Scans for files where **FileStart** is immediately followed by **FileEnd** (empty content)
- For each empty file found:
  - Extracts email identifier and file path from the markers
  - Creates a log entry marking it as processed unsuccessfully
  - Deletes both the FileStart and FileEnd markers from the input table
- This prevents empty files from being sent to the pattern matching process

### Block 10: Prepare Alert Processing and Pattern Table Building (Lines 490-616)
```vba
Call prep_AllParsedPDFs(TxtFormatSig(4), wCoID, wBrID, ELThisLineNo, NormalEnd)
If Not NormalEnd Then
    DoCmd.OpenForm "HTC200F_G010_F010A Position"
    With Forms![HTC200F_G010_F010A Position]
        !lbl_FilePosition.Caption = vbCrLf & "Process Terminated" & vbCrLf & _
                                    "Empty input or Code Error, See ETO Log"
        !lbl_Version.Caption = VersionID
        .Refresh
        .Repaint
    End With
    Call HTC200F_Wait(5)
    Application.Quit
End If

' ... Pattern table building code ...

For X = 1 To EndX
    wrkSigLine = TxtFormatSig(X)
    Y = 1
    For Z = 1 To Len(Trim(wrkSigLine))
        If Mid(wrkSigLine, Z, 1) = "|" Then
            Y = Y + 1
        Else
            PatternLn(X, Y) = PatternLn(X, Y) & Mid(wrkSigLine, Z, 1)
        End If
    Next Z
    Y = Y + 1
    PatternLn(X, Y) = "End of Pattern"
Next X
```
**Explanation**:
- Calls prep_AllParsedPDFs with pattern #4 (SOS Alert) to handle special Alert processing
- prep_AllParsedPDFs expands Alerts with multiple delivery receipts into separate alert records
- If prep_AllParsedPDFs fails (NormalEnd = False):
  - Opens progress form with error message
  - Waits 5 seconds for user to see the message
  - Quits application
- Builds PatternLn(X,Y) 2D array from TxtFormatSig strings:
  - X dimension = pattern number (1-14)
  - Y dimension = line number within pattern
  - Splits TxtFormatSig on "|" character to separate lines
  - Adds "End of Pattern" marker to signal end of each pattern

### Block 11: Build File List Array (Lines 518-568)
```vba
With AllTXTs
    f = 0
    .MoveFirst
    Do Until .EOF
        If f > MaxF Then
            Msg = ELThisRun & "; 1 of 2 Translation: The number of parsed PDFs exceed maximum of " & MaxF

            Do Until Left(!txtline, 11) = "**FileEnd**"
                .MovePrevious
            Loop

            ELThisFilePath = Replace(!txtline, "**FileEnd**", "")

            Msg = Msg & " PDF's. The last email processed was stamped " & Mid(!txtline, InStr(!txtline, "DTR_" + 4, InStr(!txline, "_xxx_") - 1))

            .MoveNext

            Do Until .EOF
                .Delete
                .MoveNext
            Loop

            ELThisLineNo = ELThisLineNo + 1
            Logfile.AddNew
                ' ... log the overflow condition ...
            Logfile.Update
            Exit Do
        Else
            If Left(!txtline, 13) = "**FileStart**" Then
                f = f + 1: F_FNs(f) = !FN: F_DTRNs(f) = !DTRN
            End If
            .MoveNext
        End If
    Loop
    EndF = f
End With
```
**Explanation**:
- Scans AllTXTs recordset to build arrays of File Numbers and DTRN numbers to process
- F_FNs(f) stores File Numbers, F_DTRNs(f) stores corresponding DTRN numbers
- Enforces maximum of MaxF (1000) PDFs per run
- If limit exceeded:
  - Backs up to last complete file (finds **FileEnd**)
  - Deletes all incomplete/overflow records
  - Logs the overflow condition
  - Continues processing with the files that fit within limit
- EndF stores the total count of files to process
- This creates the master list that drives the main processing loop

### Block 12: Empty EachPDF Table and Initialize Pattern Arrays (Lines 572-594)
```vba
With EachPDF
    If Not .EOF Then
        .MoveFirst
        Do Until .EOF
            .Delete
            .MoveNext
        Loop
    End If
End With

Dim PatternLn(25, 25) As String
Dim LineMatches(25, 25) As Boolean

For X = 1 To EndX
    For Y = 1 To 25
        PatternLn(X, Y) = ""
        LineMatches(X, Y) = False
    Next Y
Next X
```
**Explanation**:
- Clears the EachPDF table which stores final extracted data
- This ensures the table only contains results from the current run
- Declares and initializes PatternLn(25,25) and LineMatches(25,25) 2D arrays
- PatternLn stores the pattern text for matching
- LineMatches tracks which lines have successfully matched during pattern detection
- Arrays are zeroed out for clean state before processing

### Block 13: Open Progress Form and Begin File Processing Loop (Lines 631-650)
```vba
Dim FileToProcess As Recordset
Set FileToProcess = db.OpenRecordset("HTC200F_G030_T030 File To Process", dbOpenTable)

Dim Txts As Recordset
Set Txts = db.OpenRecordset("HTC200F_G030_Q030 WrkTxtFile", dbOpenDynaset)

DoCmd.OpenForm "HTC200F_G010_F010A Position"
Forms![HTC200F_G010_F010A Position]!Label3.Caption = "HTC Email to Order, Step 1 of 2"
Forms![HTC200F_G010_F010A Position]!lbl_Version.Caption = VersionID
Forms![HTC200F_G010_F010A Position].Repaint

For f = 1 To EndF
    Forms![HTC200F_G010_F010A Position]!lbl_FilePosition.Caption = F_FNs(f) & " - " & F_DTRNs(f)
    Forms![HTC200F_G010_F010A Position]!lbl_Version.Caption = VersionID
    Forms![HTC200F_G010_F010A Position].Repaint

    ' Clear wrk fields
    wrk_txtdoctype = "": wrk_TxtCustomerID = 0: wrk_TxtCustomer = ""
    ' ... clear all working variables ...
```
**Explanation**:
- Opens FileToProcess table (single-row table that acts as a parameter holder for queries)
- Opens Txts recordset which queries based on FileToProcess to get current file's lines
- Opens progress form to display status to user during processing
- Sets form title to "Step 1 of 2" (this module is first step, order creation is second)
- Displays version ID on form
- Begins main processing loop: For f = 1 To EndF (processes each PDF file)
- Updates form with current file's FN and DTRN being processed
- Clears all working variables that will be populated with extracted data

### Block 14: Load Current File into FileToProcess Table (Lines 665-680)
```vba
If FileToProcess.RecordCount > 0 Then
    FileToProcess.MoveFirst
    Do Until FileToProcess.EOF
        FileToProcess.Delete
        FileToProcess.MoveNext
    Loop
End If
FileToProcess.AddNew
    FileToProcess!currFN = F_FNs(f)
    FileToProcess!currdrtn = F_DTRNs(f)
FileToProcess.Update

Txts.Requery
```
**Explanation**:
- FileToProcess is a single-row parameter table that drives the WrkTxtFile query
- Deletes any existing record from FileToProcess
- Adds new record with current file's FN and DTRN
- This acts as query parameters: WrkTxtFile query uses these values to filter AllParsedPDFs
- Calls Txts.Requery to reload the Txts recordset with current file's lines
- This is a clever pattern for parameterizing queries in Access without stored procedures

### Block 15: Validate File Header and Extract Metadata (Lines 682-716)
```vba
With Txts
    .MoveFirst
    If Left(!wrktxtline, 13) <> "**FileStart**" Then
        Msg = "A. The first line of the work file is NOT a file header"
        Ans = MsgBox(Msg, vbOKOnly, MsgTitle)
        If Not .EOF Then
            .MoveFirst
            Do Until Left(!wrktxtline, 13) = "**FileStart**"
              .MoveNext
            Loop
        End If
        GoTo ModuleFailed
    End If

    ThisFileName = Trim(Right(!wrktxtline, Len(!wrktxtline) - 13))
    ELThisFilePath = ThisFileName
    ELThisFilePath = Replace(!wrktxtline, "**FileStart**", "")
    ELThiseMail = HTC200F_EM_DtTm(ThisFileName) & " " & HTC200F_EM_Subject(ThisFileName, ThisSender)
    ThisFileName = Replace(ThisFileName, "C:\HTC_Parsed_PDF\", "")
    ThisTxtFileName = Left(ThisFileName, InStr(ThisFileName, "_xxx_") - 1)

    X = InStr(ThisFileName, "_xxx_") + 5
    wrkArea = Right(ThisFileName, Len(ThisFileName) - X + 1)
    ThisSender = Left(wrkArea, InStr(wrkArea, "_xxx_") - 1)

    Forms![HTC200F_G010_F010A Position]!lbl_FilePosition.Caption = !wrktxtfn & " - " & !wrktxtdtrn & " ==> " & ThisFileName
```
**Explanation**:
- Validates that first line is **FileStart** marker - if not, shows error and tries to recover
- Extracts full file path from FileStart line
- Parses filename to extract:
  - Email date/time using HTC200F_EM_DtTm function
  - Email subject using HTC200F_EM_Subject function
  - Sender email address (stored between _xxx_ delimiters)
- Filename format appears to be: DTR_[timestamp]_xxx_[sender]_xxx_[etc].txt
- Updates progress form with current file being processed
- These extracted values (ELThiseMail, ThisSender, etc.) are used for logging and passed to processing functions

### Block 16: Pattern Matching Algorithm (Lines 718-762)
```vba
X = 1: Y = 1

ThisPDFName = ThisFileName
.MoveNext

Do Until PatternLn(X, Y) = "End of Pattern"
    If Len(Trim(PatternLn(X, Y))) <> Len(Trim(!wrktxtline)) Then
        PatternMatches = False
    Else
        If Len(!wrktxtline) > 0 Then
            For Z = 1 To Len(Trim(PatternLn(X, Y)))
                If Mid(PatternLn(X, Y), Z, 1) = Mid(!wrktxtline, Z, 1) Then
                    PatternMatches = True
                ElseIf Mid(PatternLn(X, Y), Z, 1) = "#" And InStr(AlphaStuff & IIf(X = 5, " ", ""), Mid(!wrktxtline, Z, 1)) > 0 Then
                    PatternMatches = True
                Else
                    PatternMatches = False
                    Exit For
                End If
             Next Z
        Else
            PatternMatches = True
        End If
    End If

    If PatternMatches Then
        LineMatches(X, Y) = True
        Y = Y + 1
        .MoveNext
    Else
        If Y > 1 Then
            For Z = Y - 1 To 1 Step -1
                .MovePrevious
            Next Z
        End If
        X = X + 1
        If X > EndX Then Exit Do
        Y = 1
    End If
Loop
```
**Explanation**:
- Core pattern matching engine that identifies document format
- Starting with pattern X=1, Y=1 (first line of first pattern)
- Compares each line of input against pattern lines character by character:
  - Exact character matches count as match
  - "#" in pattern matches any alphanumeric (from AlphaStuff string)
  - Special case: Pattern 5 (MAWB) allows spaces in # positions
- If entire line matches: marks LineMatches(X,Y) = True, advances to next line
- If line doesn't match: resets input position, tries next pattern (X=X+1)
- Continues until either:
  - Full pattern matches (reaches "End of Pattern" marker)
  - All patterns exhausted (X > EndX)
- This is a sequential pattern matcher that must match ALL lines in sequence

### Block 17: Execute Format-Specific Processing (Lines 766-913)
```vba
Forms![HTC200F_G010_F010A Position]!lbl_FilePosition.Caption = !wrktxtfn & " - " & !wrktxtdtrn & " ==> " & ThisFileName & " (" & TxtFormatName(X) & ")"

If PatternMatches Then
    Call Mine_TxtFile(ELThisRun, ELThiseMail, ELThisLineNo, _
                      ELThisFilePath, ThisSender, _
                      Val(wCoID), Val(wBrID), TxtFormatName(X), _
                      wrk_TxtCustomerID, wrk_TxtCustomer, _
                      ' ... many more parameters ...
                      wrk_TxtProcessYN)

    If TxtFormatHasInfo(X) And wrk_TxtProcessYN Then
        EachPDF.AddNew
            EachPDF!txtemailhdr = ELThiseMail
            EachPDF!txtwhensent = HTC200F_EM_DtTm(ELThisFilePath)
            EachPDF!TxtCoID = Val(wCoID)
            EachPDF!TxtBrID = Val(wBrID)
            EachPDF!txtfilename = ThisFileName
            EachPDF!TxtDocType = TxtFormatName(X)
            EachPDF!txtcustomerid = wrk_TxtCustomerID
            ' ... all extracted fields ...
            EachPDF!txtaddress = "C:\HTC_Parsed_PDF\" & ThisFileName
            EachPDF!pdfaddress = "C:\HTC_EmailToParse\" & Replace(ThisFileName, ".txt", ".pdf")
        EachPDF.Update

        Logfile.AddNew
            ' ... log successful processing ...
            Logfile!etolog_comment = TxtFormatName(X) & " processed Successfully."
        Logfile.Update
```
**Explanation**:
- Updates progress form with identified document type
- If pattern matched: calls Mine_TxtFile with all extracted and session parameters
- Mine_TxtFile dispatches to format-specific handler (HTC200F_SOS_Routing, HTC200F_SOS_BOL, etc.)
- Format handler populates wrk_* variables with extracted data (HAWB, addresses, dates, etc.)
- If format has order info (TxtFormatHasInfo=True) AND processing succeeded (wrk_TxtProcessYN=True):
  - Creates new record in EachPDF table with all extracted shipping information
  - Truncates fields to database limits (100 chars for names, 255 for addresses)
  - Stores both TXT and PDF file paths
  - Creates log entry marking successful processing
- If format has no order info (like Battery Advisory):
  - Still creates EachPDF record but with minimal data
  - Logs as "marked as having no info of value"

### Block 18: Handle Unrecognized Documents (Lines 881-913)
```vba
Else   'Don't know what this document is
    wrk_TxtProcessYN = False
    EachPDF.AddNew
        EachPDF!txtemailhdr = ELThiseMail
        EachPDF!txtwhensent = HTC200F_EM_DtTm(ELThisFilePath)
        EachPDF!TxtCoID = Val(wCoID)
        EachPDF!TxtBrID = Val(wBrID)
        EachPDF!txtfilename = ThisFileName
        EachPDF!TxtDocType = TxtFormatName(X)
        EachPDF!txtcustomerid = wrk_TxtCustomerID
        EachPDF!txtCustomer = wrk_TxtCustomer
        EachPDF!TxtNotes = wrk_TxtComments
        EachPDF!txtprocessyn = wrk_TxtProcessYN
        EachPDF!txtaddress = "C:\HTC_Parsed_PDF\" & ThisFileName
        EachPDF!pdfaddress = "C:\HTC_EmailToParse\" & Replace(ThisFileName, ".txt", ".pdf")
        EachPDF!txtthissender = ThisSender
    EachPDF.Update

    ELThisLineNo = ELThisLineNo + 1
    Logfile.AddNew
        Logfile!etolog_thisrun = ELThisRun
        Logfile!etolog_emailid = ThisTxtFileName
        Logfile!etolog_lineno = ELThisLineNo
        Logfile!etolog_filepath = ELThisFilePath
        Logfile!etolog_sender = ""
        Logfile!etolog_customerid = 0
        Logfile!etolog_hawb = ""
        Logfile!etolog_ordercreated = False
        Logfile!etolog_orderno = 0
        Logfile!etolog_processedok = False
        Logfile!etolog_comment = "This txt file does not match a defined pattern."
    Logfile.Update
End If
```
**Explanation**:
- Handles case where no pattern matched (PatternMatches = False)
- Sets wrk_TxtProcessYN = False to indicate processing failure
- Still creates EachPDF record with minimal metadata:
  - Email header, timestamp, file paths, sender
  - No order information since format wasn't recognized
  - txtprocessyn = False to flag it as unprocessed
- Creates log entry marking unsuccessful processing:
  - etolog_processedok = False
  - etolog_comment = "This txt file does not match a defined pattern."
- These files would typically be moved to UnrecognizedPath folder later
- Allows the process to continue with remaining files rather than failing completely

### Block 19: Call Order Creation and Cleanup (Lines 917-926)
```vba
FinishUP:

ModLocnMark = "MLC 08"

Call HTC350C_2of2_CreateOrders(ELThisRun, ELThiseMail, ELThisLineNo, VersionID, HAWBProcessed)

ModLocnMark = "MLC 09"

Call HTC350C_PurgePDFFiles(ELThisRun, ELThiseMail, ELThisLineNo)
```
**Explanation**:
- FinishUP label: allows error handler to jump here to complete processing even after errors
- Updates ModLocnMark for error tracking
- Calls HTC350C_2of2_CreateOrders: the second step that creates actual orders in the system
  - Uses data from EachPDF table populated by this function
  - Passes run timestamp, email ID, line number for logging
  - Returns HAWBProcessed boolean indicating success
- Calls HTC350C_PurgePDFFiles: cleanup function that:
  - Moves processed PDF/TXT files to appropriate directories
  - Removes old files beyond retention period
  - Updates file paths in database records

### Block 20: Delete WhosLoggedIn Session Records (Lines 928-953)
```vba
With WLI
    If Not .EOF Then
        .MoveFirst
        Do Until .EOF
            If !wli_company = Val(wCoID) And _
               !wli_branch = Val(wBrID) And _
               !pcname = xPCName And _
               !pclid = xPCLID And _
               !wli_staffid = 0 And _
               !WhosLoggedIn = xWhosLoggedIn Then
                    .Delete
            End If
            .MoveNext
        Loop
    End If
End With
```
**Explanation**:
- Cleanup of session management records created at beginning of function (Block 2)
- Searches WhosLoggedIn table for ALL records matching this ETO process:
  - Company ID = 1, Branch ID = 1
  - PCName = "HarrahServer", PCLID = "ETOProcess"
  - StaffID = 0 (indicates automated process)
  - WhosLoggedIn = "HarrahServer"
- Deletes ALL matching records (not just first one)
- Changed in version 2.04 to delete all instances (comment mentions residual logins from previous crashes)
- This "unlocks" the system to allow another ETO run

### Block 21: Display Completion and Exit (Lines 955-966)
```vba
With Forms![HTC200F_G010_F010A Position]
    !lbl_FilePosition.Caption = vbCrLf & "Process complete" & vbCrLf
    !lbl_Version.Caption = VersionID
    .Refresh
    .Repaint
End With

Call HTC200F_Wait(5)

Application.Quit
```
**Explanation**:
- Updates progress form with completion message
- Displays version ID for reference
- Calls Refresh and Repaint to force form update immediately
- Waits 5 seconds to allow user to see completion message
- Calls Application.Quit to close the Access application
- This is the normal exit path after successful processing
- Access application closes automatically, ending the ETO process

### Block 22: Error Handler (Lines 969-1001)
```vba
ModuleFailed:

With Logfile
    ELThisLineNo = ELThisLineNo + 1
    .AddNew
        !etolog_coid = wCoID
        !etolog_brid = wBrID
        !etolog_thisrun = ELThisRun
        !etolog_emailid = ELThiseMail
        !etolog_lineno = ELThisLineNo
        !etolog_filepath = ELThisFilePath
        !etolog_sender = ""
        !etolog_customerid = 0
        !etolog_hawb = ""
        !etolog_ordercreated = False
        !etolog_orderno = 0
        !etolog_processedok = False
        If Msg <> "" Then Msg = Msg & "; " & vbCrLf
        Msg = Msg & "Module: " & ModuleName & ": LocationMark:" & ModLocnMark & _
                    ": Line No: " & Erl & _
                    " failed with error " & Err.Number & "; " & Err.Description
        !etolog_comment = Msg
    .Update
End With

If InStr(Msg, "A. The first line of the work file is NOT a file header") > 0 Then GoTo FinishUP

Resume Next
```
**Explanation**:
- Global error handler for the entire function (On Error GoTo ModuleFailed from Block 1)
- Creates detailed log entry capturing error information:
  - Session and run identifiers
  - Current file being processed (ELThiseMail, ELThisFilePath)
  - Module name and location mark (ModLocnMark tracks which section failed)
  - Line number where error occurred (Erl)
  - Error number and description (Err.Number, Err.Description)
  - etolog_processedok = False to mark failure
- Special handling for "first line not file header" error:
  - Jumps to FinishUP label to continue with order creation and cleanup
  - Allows partial recovery from file structure errors
- Ends with "Resume Next" to continue processing remaining files
- This allows the process to be fault-tolerant: one bad file doesn't stop entire batch

### Block 23: Mine_TxtFile Dispatcher Function (Lines 1005-1310)
```vba
Sub Mine_TxtFile(ELThisRun As Date, ELThiseMail As String, ELThisLineNo As Integer, _
                 wThisFileWithPath As String, wThisSender As String, _
                 wCoID As Integer, wBrID As Integer, _
                 wFormatName As String, _
                 wtxtCustomerID As Integer, wtxtCustomer As String, _
                 ' ... many more parameters ...
                 wtxtProcessYN As Boolean)

On Error GoTo Mine_TxtFile_Error

If wFormatName = "SOS Routing" Then
    Call HTC200F_SOS_Routing(ELThisRun, ELThiseMail, ELThisLineNo, _
                             wThisFileWithPath, wThisSender, _
                             ' ... all parameters passed through ...)
ElseIf wFormatName = "SOS BOL" Then
    Call HTC200F_SOS_BOL(...)
' ... 10 more ElseIf clauses for different formats ...
Else
    Call HTC200F_SOS_No_Format(...)
End If
```
**Explanation**:
- Dispatcher/router function that receives identified format name and extracted data
- Takes 26+ parameters including session info, file paths, and reference parameters for extracted data
- Uses If/ElseIf chain to route to appropriate format-specific processing function:
  - SOS Routing → HTC200F_SOS_Routing
  - SOS BOL (3 variants) → HTC200F_SOS_BOL/BOL2/BOL3
  - SOS Dlvry Rcpt → HTC200F_SOS_Dlvry_Rcpt
  - SOS Alert → HTC200F_SOS_Alert
  - SOS MAWB (2 variants) → HTC200F_SOS_MAWB
  - SOS Forward Air Fast Book → HTC200F_FA_FastBook
  - SOS Battery Advisory 2 → HTC200F_SOS_BatteryAdvisory2
  - Unrecognized → HTC200F_SOS_No_Format
- All parameters passed through to format handlers
- Format handlers populate the wtxt* reference parameters with extracted data
- Has its own error handler that displays MsgBox and stops execution

### Block 24: prep_AllParsedPDFs Function (Lines 1312-1652)
```vba
Sub prep_AllParsedPDFs(AlertTrigger As String, CoID As String, BrID As String, ELThisLineNbr As Integer, NormalEnd As Boolean)

On Error GoTo prep_AllParsedPDFs_Error

Dim APPDFs As Recordset
Set APPDFs = db.OpenRecordset("HTC200F_G030_Q000B All ParsedPDFs Sorted", dbOpenDynaset)

Dim SvdAlertInfo As Recordset
Set SvdAlertInfo = db.OpenRecordset("HTC200F_G030_T010 SvdAlertHdrs", dbOpenTable)

Dim AddonParsedPDFS As Recordset
Set AddonParsedPDFS = db.OpenRecordset("HTC200F_G030_T020 addonParsedpdfs", dbOpenTable)
```
**Explanation**:
- Specialized function that handles SOS Alert documents with multiple delivery receipts
- SOS Alerts can contain multiple delivery receipts in a single PDF
- This function splits them into separate "virtual" files - one alert per delivery receipt
- Opens three recordsets:
  - APPDFs: The main parsed PDFs table (input/output)
  - SvdAlertInfo: Temporary storage for alert header lines
  - AddonParsedPDFS: Staging area for newly created split records
- AlertTrigger parameter is the pattern that identifies alert documents
- Returns NormalEnd boolean to indicate success/failure

### Block 25: Alert Splitting Logic (Lines 1369-1586)
```vba
With APPDFs
    If .RecordCount = 0 Then
        ErrMsg = "There are no PDF's to process, ETO is terminated"
        GoTo prep_AllParsedPDFs_Error
    End If

    Do Until .EOF
        If Left(!txtline, 13) = "**FileStart**" Then
            SvdFN = !FN
            SvdFileHdr = !txtline
            PDFHdr = .Bookmark
            DTRNbr = 0
        End If

        .MoveNext

        If Trim(!txtline) = AlertTrigger Then
            ' Save alert header lines to SvdAlertInfo
            Do Until Left(!wrktxtline, Len(DlvrRcptFlag)) = DlvrRcptFlag
                SvdAlertInfo.AddNew
                    SvdAlertInfo!svdalertFN = !FN
                    SvdAlertInfo!svdalertdtrn = DTRNbr
                    SvdAlertInfo!svdalertln = !LN
                    SvdAlertInfo!svdalerthdr = !txtline
                SvdAlertInfo.Update
                .MoveNext
            Loop

            ' For each delivery receipt found, create new file
            Do Until Left(!txtline, 11) = "**Fileend**"
                If Left(!txtline, Len(DlvrRcptFlag)) = DlvrRcptFlag Then
                    ' Copy alert header + this delivery receipt to AddonParsedPDFS
                    ' Increment DTRNbr for next delivery receipt
                End If
                .MoveNext
            Loop

            ' Mark original alert records for deletion
            .Bookmark = PDFHdr
            .Edit: !deleterow = True: .Update
            ' ... mark all lines for deletion ...
        End If
    Loop
End With
```
**Explanation**:
- Main splitting algorithm for SOS Alerts with multiple delivery receipts
- For each file that matches AlertTrigger pattern:
  1. Saves the alert header lines (everything before first "DELIVERY RECEIPT")
  2. Finds each "DELIVERY RECEIPT" section in the file
  3. For each delivery receipt:
     - Creates FileStart marker
     - Copies saved alert header
     - Copies delivery receipt section
     - Creates FileEnd marker
     - Assigns unique DTRN number
  4. Marks original consolidated alert for deletion
  5. Stores split records in AddonParsedPDFS staging table
- Uses Bookmark to save positions for navigation back
- DTRNbr increments for each delivery receipt (DTRN = Delivery Receipt Number)
- This allows each delivery receipt to be processed as a separate order

### Block 26: Finalize Alert Splitting (Lines 1588-1618)
```vba
' Remove marked records
.MoveFirst: LineNbr = 0
Do Until .EOF
    If !deleterow Then .Delete
    .MoveNext: LineNbr = LineNbr + 1
Loop

' Re-add the split Alert records
DoCmd.SetWarnings False
    DoCmd.OpenQuery "HTC200F_G030_Q020 Append AddOnParsedPDFs"
DoCmd.SetWarnings True

' Make sure there are NO rows with a null !txtline
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
- Cleanup and finalization of alert splitting process
- Deletes all records marked with deleterow = True (the original consolidated alerts)
- Runs append query to add split alert records from AddonParsedPDFS back to APPDFs
- Validates data quality by replacing NULL txtline fields with empty strings
- This prevents downstream processing errors from NULL values
- At this point, APPDFs contains:
  - All original non-alert files unchanged
  - Split alert files (one per delivery receipt instead of multi-receipt files)
- Sets NormalEnd = True to signal success
- Process can now continue with pattern matching on the modified dataset

## Dependencies

**Database Objects**:
- **Tables**:
  - HTC000 WhosLoggedIn (session management)
  - HTC350_G800_T010 ETOLog (audit log)
  - HTC200F_TxtFileNames (extracted PDF data)
  - HTC200F_G030_T030 File To Process (parameter table)
  - HTC200F_G030_T010 SvdAlertHdrs (temporary alert headers)
  - HTC200F_G030_T020 addonParsedpdfs (temporary split alerts)
  - AllParsedPDFs (dynamically created table of all parsed text)

- **Queries**:
  - HTC200F_G030_Q000A AllParsedPDFs Tbl Created (creates/rebuilds AllParsedPDFs table)
  - HTC200F_G030_Q000B All ParsedPDFs Sorted (sorted view of AllParsedPDFs)
  - HTC200F_G030_Q030 WrkTxtFile (filtered view based on FileToProcess parameters)
  - HTC200F_G030_Q020 Append AddOnParsedPDFs (appends split alerts back to main table)

- **Forms**:
  - HTC200F_G010_F010A Position (progress display form)

**External Dependencies**:
- **File System**:
  - C:\HTC_Parsed_PDF\ (input directory for parsed text files)
  - C:\HTC_EmailToParse\ (input directory for original PDF files)
  - C:\HTC_Processed Attachments (output for successfully processed files)
  - C:\HTC_Unrecognized Attachment (output for unrecognized formats)
- **COM Objects**: FileSystemObject (file existence checks and deletion)
- **Environment Variables**:
  - Environ("computername") - used in WhosLoggedIn validation
  - Environ("username") - used in WhosLoggedIn validation
- **Global/Module Variables**:
  - VersionID, VersionChange (module-level)
  - Msg, MsgTitle, Ans (module-level)
  - F_FNs(), F_DTRNs() (module-level arrays for file tracking)
  - MaxF, f, EndF (module-level counters)
  - ELThis* variables (module-level logging context)

## Migration Notes

**Complexity**: High

**Migration Strategy**:
This function should be decomposed into multiple TypeScript/Python services with clear separation of concerns:
1. **Session Management Service** - Handle process locking and concurrency
2. **File Processing Service** - Scan directories, validate files, manage file lifecycle
3. **Pattern Matching Service** - Identify document types using configurable patterns
4. **Document Extraction Service** - Extract data from identified document types
5. **Log Management Service** - Centralized logging with retention policies
6. **Progress Tracking Service** - Status updates (replace Access form with web UI/API)

**Challenges**:

1. **Monolithic Architecture**:
   - Single 1000+ line function doing initialization, file management, pattern matching, extraction, logging, and UI updates
   - Needs decomposition into multiple services with defined interfaces
   - Module-level global variables create hidden state dependencies

2. **Database-Centric Design**:
   - Extensive use of recordsets for data manipulation
   - Queries used as parameterized procedures (FileToProcess table pattern)
   - Need ORM or query builder (TypeORM, Prisma, SQLAlchemy)
   - Consider migrating from Access to PostgreSQL/MySQL

3. **Pattern Matching System**:
   - Custom character-by-character matching algorithm
   - Should be replaced with regex patterns or parser combinator library
   - Pattern definitions in code - should be externalized to configuration
   - Consider parser generator (ANTLR) or structured document parsing (PDFBox, Tika)

4. **File System Dependencies**:
   - Hard-coded Windows paths (C:\HTC_Parsed_PDF\)
   - File-based inter-process communication
   - Should use configurable paths, cloud storage abstraction (S3, Azure Blob)
   - Consider message queue (RabbitMQ, SQS) instead of file system coordination

5. **Error Handling**:
   - Global error handler with Resume Next (masks errors)
   - ModLocnMark breadcrumb tracking is primitive
   - Need structured error handling with proper exception types
   - Add structured logging (Winston, Python logging) with correlation IDs

6. **VBA-Specific Patterns**:
   - Recordset navigation (MoveFirst, MoveNext, .EOF, .Bookmark)
   - Field access with ! operator (!etolog_thisrun)
   - With blocks for repeated object access
   - DoCmd for Access operations
   - Application.Quit for process termination

7. **Session Management**:
   - WhosLoggedIn table used for process locking
   - Race conditions possible with manual lock management
   - Should use proper distributed locking (Redis locks, database advisory locks)
   - Consider container orchestration (Kubernetes) for process management

8. **PDF Processing**:
   - Assumes PDFs already converted to text elsewhere
   - Need PDF parsing library (pdf-parse, PyPDF2, Apache PDFBox)
   - Pattern matching on raw text is fragile
   - Consider OCR for scanned documents (Tesseract)

9. **Progress UI**:
   - Access form updated synchronously during processing
   - Blocks processing, creates tight coupling
   - Should use async progress updates (WebSocket, SSE, polling API)
   - Separate frontend from backend processing

10. **Transaction Management**:
    - No explicit transaction boundaries
    - Partial updates possible on error
    - Need proper transaction management with rollback capability
    - Consider saga pattern for multi-step processes

11. **Testing**:
    - Difficult to unit test due to tight coupling to Access
    - No dependency injection
    - File system and database dependencies hard-coded
    - Need refactoring for testability with mocks/stubs

12. **Scalability**:
    - Single-threaded, synchronous processing
    - MaxF limit of 1000 PDFs
    - Should use worker queue pattern (Bull, Celery) for parallel processing
    - Consider batch processing frameworks (Spring Batch, AWS Batch)

**Modern Equivalent**:

A modern implementation would be:

```typescript
// TypeScript/Node.js example structure

interface DocumentPattern {
  id: string;
  name: string;
  customer: string;
  hasOrderInfo: boolean;
  patterns: RegExp[];
}

class DocumentProcessor {
  constructor(
    private db: Database,
    private storage: StorageService,
    private logger: Logger,
    private progressTracker: ProgressTracker
  ) {}

  async processDocuments(): Promise<ProcessingResult> {
    const session = await this.createSession();

    try {
      await this.cleanupOldFiles(31); // retention days

      const documents = await this.storage.listDocuments('parsed-pdfs');

      if (documents.length === 0) {
        await this.logger.info('No documents to process');
        return { success: true, processed: 0 };
      }

      const patterns = await this.loadPatternDefinitions();
      const results = [];

      for (const doc of documents) {
        this.progressTracker.update({ current: doc.id, total: documents.length });

        const content = await this.storage.readDocument(doc.id);
        const pattern = this.matchPattern(content, patterns);

        if (pattern) {
          const extracted = await this.extractData(content, pattern);
          await this.db.saveExtractedData(extracted);
          await this.logger.info(`Processed ${doc.id} as ${pattern.name}`);
          results.push({ doc: doc.id, success: true });
        } else {
          await this.logger.warn(`Unrecognized format: ${doc.id}`);
          await this.storage.moveDocument(doc.id, 'unrecognized');
          results.push({ doc: doc.id, success: false });
        }
      }

      await this.createOrders(results);
      await this.cleanupProcessedFiles();

      return { success: true, processed: results.length };

    } finally {
      await this.releaseSession(session);
    }
  }

  private matchPattern(content: string, patterns: DocumentPattern[]): DocumentPattern | null {
    for (const pattern of patterns) {
      if (pattern.patterns.every((regex, idx) =>
        regex.test(content.split('\n')[idx] || '')
      )) {
        return pattern;
      }
    }
    return null;
  }
}

// With modern infrastructure:
// - Run as containerized service (Docker/Kubernetes)
// - Use message queue for document processing jobs
// - Store patterns in database/config files
// - Web UI for progress tracking via WebSocket
// - Cloud storage (S3) for documents
// - PostgreSQL for structured data
// - Distributed tracing (OpenTelemetry)
// - Metrics and alerting (Prometheus/Grafana)
```

The modern version would be event-driven, scalable, testable, and maintain clear separation between document processing, data extraction, order creation, and file management concerns.
