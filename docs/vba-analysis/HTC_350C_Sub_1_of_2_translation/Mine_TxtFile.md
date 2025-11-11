# Function: `Mine_TxtFile`

**Type**: Sub
**File**: HTC_350C_Sub_1_of_2_translation.vba
**Analyzed**: 2025-11-11

## Signature
```vba
Sub Mine_TxtFile(ELThisRun As Date, ELThiseMail As String, ELThisLineNo As Integer, _
                 wThisFileWithPath As String, wThisSender As String, _
                 wCoID As Integer, wBrID As Integer, _
                 wFormatName As String, _
                 wtxtCustomerID As Integer, wtxtCustomer As String, _
                 wtxtHAWB As String, wtxtMAWB As String, _
                 wtxtPkupFromID As Double, _
                 wtxtPkupFromName As String, _
                 wtxtPkupFromAddress As String, _
                 wtxtPkupFromNotes As String, _
                 wtxtPkupDate As String, _
                 wtxtPkupTime As String, _
                 wtxtDelToID As Double, _
                 wtxtDelToName As String, _
                 wtxtDelToAddress As String, _
                 wtxtDelToNotes As String, _
                 wtxtDelDate As String, _
                 wtxtDelTime As String, _
                 wtxtQty As Integer, _
                 wtxtWeight As Integer, _
                 wtxtComments As String, _
                 wtxtProcessYN As Boolean _
                 )
```

## Purpose & Overview

**Primary Purpose**: This function acts as a routing dispatcher that delegates PDF text file processing to specialized handler functions based on the identified document format type. It serves as the central coordinator that matches each parsed PDF/TXT file to its appropriate processing module.

**Input**:
- `ELThisRun` - Timestamp identifying this execution run
- `ELThiseMail` - Email identifier (date & subject)
- `ELThisLineNo` - Log line sequence number
- `wThisFileWithPath` - Full file path to the .txt file being processed
- `wThisSender` - Email sender address
- `wCoID` / `wBrID` - Company and Branch identifiers
- `wFormatName` - Document format identifier (e.g., "SOS Routing", "SOS BOL", "SOS Alert")
- `wtxt*` parameters - Output parameters for extracted shipping/order data (all passed by reference)

**Output**:
- Populates the output parameters (wtxt* variables) with extracted data from the parsed text file
- Sets `wtxtProcessYN` to indicate whether the document contains actionable order information

**Side Effects**:
- Calls specialized processing functions that may:
  - Read from database tables (HTC200F_G030_Q030 WrkTxtFile)
  - Write to log tables (HTC350_G800_T010 ETOLog)
  - Update global state through the output parameters

## Function Cross-References

### Functions in Same File
- None - This function delegates all work to external functions

### External Functions (NOT in this file)
- `HTC200F_SOS_Routing()` - **⚠️ EXTERNAL** - Processes SOS Routing instruction forms
- `HTC200F_SOS_BOL()` - **⚠️ EXTERNAL** - Processes SOS Bill of Lading forms (format 1)
- `HTC200F_SOS_BOL2()` - **⚠️ EXTERNAL** - Processes SOS Bill of Lading forms (format 2)
- `HTC200F_SOS_BOL3()` - **⚠️ EXTERNAL** - Processes SOS Bill of Lading forms (format 3)
- `HTC200F_SOS_Dlvry_Rcpt()` - **⚠️ EXTERNAL** - Processes SOS Delivery Receipt forms
- `HTC200F_SOS_Alert()` - **⚠️ EXTERNAL** - Processes SOS Alert forms
- `HTC200F_SOS_MAWB()` - **⚠️ EXTERNAL** - Processes SOS Master Air Waybill forms (handles MAWB1 and MAWB2)
- `HTC200F_FA_FastBook()` - **⚠️ EXTERNAL** - Processes SOS Forward Air FastBook forms
- `HTC200F_SOS_BatteryAdvisory2()` - **⚠️ EXTERNAL** - Processes SOS Battery Advisory 2 forms
- `HTC200F_SOS_No_Format()` - **⚠️ EXTERNAL** - Handles unrecognized document formats

### Built-in VBA/Access Functions
- `MsgBox()` - Displays error messages to user

## Detailed Behavioral Breakdown

### Block 1: Error Handling Setup
```vba
On Error GoTo Mine_TxtFile_Error

Dim ModuleName As String: ModuleName = "HTC350C_1of2 Translation/MineTxtFile"
Dim ModLocnMark As String: ModLocnMark = "Module start"
```
**Explanation**:
- Sets up centralized error handling that jumps to `Mine_TxtFile_Error` label on any error
- Initializes module identification variables for error logging and diagnostics
- These variables help track which module and location failed if an error occurs

### Block 2: SOS Routing Format Handler
```vba
If wFormatName = "SOS Routing" Then
    Call HTC200F_SOS_Routing(ELThisRun, ELThiseMail, ELThisLineNo, _
                             wThisFileWithPath, wThisSender, _
                             wCoID, wBrID, _
                             wFormatName, _
                             wtxtCustomerID, wtxtCustomer, _
                             wtxtHAWB, wtxtMAWB, _
                             wtxtPkupFromID, _
                             wtxtPkupFromName, _
                             wtxtPkupFromAddress, _
                             wtxtPkupFromNotes, _
                             wtxtPkupDate, _
                             wtxtPkupTime, _
                             wtxtDelToID, _
                             wtxtDelToName, _
                             wtxtDelToAddress, _
                             wtxtDelToNotes, _
                             wtxtDelDate, _
                             wtxtDelTime, _
                             wtxtQty, wtxtWeight, _
                             wtxtComments, _
                             wtxtProcessYN)
```
**Explanation**:
- Checks if the identified format is "SOS Routing" (routing instruction forms)
- Delegates processing to the specialized `HTC200F_SOS_Routing` function
- Passes all input parameters and output parameter references to the handler
- The handler will populate the wtxt* output parameters with extracted data

### Block 3: SOS BOL Format Handlers (Three Variants)
```vba
ElseIf wFormatName = "SOS BOL" Then
    Dim Skip2ndLine As Boolean: Skip2ndLine = False
    Dim ExtraCharacterln1 As Boolean: ExtraCharacterln1 = False

    Call HTC200F_SOS_BOL(ELThisRun, ELThiseMail, ELThisLineNo, _
                         [... parameters ...], _
                         Skip2ndLine, _
                         ExtraCharacterln1)

ElseIf wFormatName = "SOS BOL2" Then
    Call HTC200F_SOS_BOL2([... parameters ...])

ElseIf wFormatName = "SOS BOL3" Then
    Call HTC200F_SOS_BOL3([... parameters ...])
```
**Explanation**:
- Handles three different Bill of Lading format variants (BOL, BOL2, BOL3)
- Each BOL format has slight structural differences requiring separate handlers
- BOL format 1 requires two additional boolean flags (`Skip2ndLine`, `ExtraCharacterln1`) to handle parsing variations
- BOL2 and BOL3 use simplified parameter lists without the special flags
- These handlers extract shipping information from bill of lading documents

### Block 4: SOS Delivery Receipt Handler
```vba
ElseIf wFormatName = "SOS Dlvry Rcpt" Then
    Call HTC200F_SOS_Dlvry_Rcpt(ELThisRun, ELThiseMail, ELThisLineNo, _
                                wThisFileWithPath, wThisSender, _
                                [... parameters ...])
```
**Explanation**:
- Processes "Delivery Receipt" forms that confirm package delivery
- Extracts delivery confirmation information and related shipping details
- Delegates to `HTC200F_SOS_Dlvry_Rcpt` specialized handler

### Block 5: SOS Alert Handler
```vba
ElseIf wFormatName = "SOS Alert" Then
    Call HTC200F_SOS_Alert(ELThisRun, ELThiseMail, ELThisLineNo, _
                           wThisFileWithPath, wThisSender, _
                           [... parameters ...])
```
**Explanation**:
- Processes "Alert" forms that contain special notifications or shipment alerts
- These forms may contain multiple delivery receipts (handled by prep_AllParsedPDFs earlier)
- Extracts alert details and associated shipping information

### Block 6: MAWB (Master Air Waybill) Handler
```vba
ElseIf Left(wFormatName, 8) = "SOS MAWB" Then
    Call HTC200F_SOS_MAWB(ELThisRun, ELThiseMail, ELThisLineNo, _
                          wThisFileWithPath, wThisSender, _
                          [... parameters ...])
```
**Explanation**:
- Handles Master Air Waybill documents (both MAWB1 and MAWB2 formats)
- Uses `Left()` function to match both "SOS MAWB1" and "SOS MAWB2" format names
- MAWBs are airline shipping documents that contain master tracking information
- Single handler function processes both MAWB format variants

### Block 7: Forward Air FastBook Handler
```vba
ElseIf wFormatName = "SOS Forward Air Fast Book" Then
    Call HTC200F_FA_FastBook(ELThisRun, ELThiseMail, ELThisLineNo, _
                             wThisFileWithPath, wThisSender, _
                             [... parameters ...])
```
**Explanation**:
- Processes Forward Air FastBook shipping forms
- Forward Air is a specific freight carrier service
- Extracts carrier-specific shipping details and routing information

### Block 8: Battery Advisory 2 Handler
```vba
ElseIf wFormatName = "SOS Battery Advisory 2" Then
    Call HTC200F_SOS_BatteryAdvisory2(ELThisRun, ELThiseMail, ELThisLineNo, _
                             wThisFileWithPath, wThisSender, _
                             [... parameters ...])
```
**Explanation**:
- Processes "Battery Advisory 2" forms related to hazardous materials shipping
- Batteries require special handling and documentation for air freight
- Extracts order numbers and HAWB information from advisory forms
- This is a specialized format that was added to handle battery shipping regulations

### Block 9: Unknown Format Handler (Else Clause)
```vba
Else
    Call HTC200F_SOS_No_Format(ELThisRun, ELThiseMail, ELThisLineNo, _
                          wThisFileWithPath, wThisSender, _
                          [... parameters ...])
```
**Explanation**:
- Catch-all handler for documents that don't match any known format
- Calls `HTC200F_SOS_No_Format` to log the unrecognized document
- Prevents the process from failing when encountering unexpected document types
- These files are typically moved to the "Unrecognized Attachment" folder

### Block 10: Normal Exit and Error Handler
```vba
On Error GoTo 0
Exit Sub

Mine_TxtFile_Error:
    MsgBox "Error " & Err.Number & " (" & Err.Description & ") in procedure Mine_TxtFile, line " & Erl & "."
Stop
```
**Explanation**:
- `On Error GoTo 0` resets error handling to default VBA behavior
- `Exit Sub` ensures normal execution doesn't fall through to error handler
- Error handler displays a message box with error number, description, and line number
- `Stop` statement pauses execution for debugging purposes
- The `Erl` function returns the line number where the error occurred (requires line numbers in source)

## Dependencies

### Database Objects
- **Tables**:
  - HTC200F_G030_Q030 WrkTxtFile (read by specialized handler functions)
  - HTC350_G800_T010 ETOLog (written by specialized handler functions)
  - HTC200F_TxtFileNames (populated by parent function after Mine_TxtFile returns)

- **Queries**: None directly used by this function

- **Forms**: None directly accessed by this function

- **Reports**: None

### External Dependencies
- **COM Objects / Libraries**: None directly used
- **External files or connections**:
  - Reads parsed .txt files from C:\HTC_Parsed_PDF\
  - References related .pdf files in C:\HTC_EmailToParse\
- **Global variables or module-level state**:
  - Uses module-level `Msg` and `MsgTitle` variables (declared at top of module)
  - Relies on parent function's database connection and recordsets

## Migration Notes

### Complexity
**High** - This is a critical routing function with 10+ specialized handlers

### Migration Strategy
**Strategy of Record Pattern (Router/Dispatcher)**

This function should be migrated as a router/dispatcher that uses a strategy pattern or factory pattern:

```typescript
// Modern equivalent structure
type DocumentHandler = (
  context: ProcessingContext,
  params: DocumentParams
) => Promise<ExtractedData>;

const documentHandlers: Record<string, DocumentHandler> = {
  'SOS Routing': handleSOSRouting,
  'SOS BOL': handleSOSBOL,
  'SOS BOL2': handleSOSBOL2,
  'SOS BOL3': handleSOSBOL3,
  'SOS Dlvry Rcpt': handleSOSDeliveryReceipt,
  'SOS Alert': handleSOSAlert,
  'SOS MAWB1': handleSOSMAWB,
  'SOS MAWB2': handleSOSMAWB,
  'SOS Forward Air Fast Book': handleFAFastBook,
  'SOS Battery Advisory 2': handleBatteryAdvisory2,
};

async function mineTxtFile(
  context: ProcessingContext,
  params: DocumentParams
): Promise<ExtractedData> {
  const handler = documentHandlers[params.formatName] || handleUnknownFormat;
  return await handler(context, params);
}
```

### Challenges

1. **Multiple Format Handlers**: The function delegates to 10+ different specialized handlers that each need to be analyzed and migrated separately. Each handler likely contains complex parsing logic.

2. **Parameter Passing by Reference**: VBA passes all wtxt* output parameters by reference, allowing the called functions to modify them. In TypeScript/Python, this pattern needs to be replaced with return values or mutable objects.

3. **Error Handling Differences**: VBA's `On Error GoTo` pattern with line numbers (`Erl`) doesn't translate directly to modern try-catch. Need structured error handling with proper error types.

4. **Format Name Matching Logic**: The MAWB handler uses `Left(wFormatName, 8) = "SOS MAWB"` to match both MAWB1 and MAWB2. This string-prefix matching needs to be replaced with more explicit logic (regex or exact string matching).

5. **Special Parameter Variations**: The BOL handler requires two additional boolean parameters (`Skip2ndLine`, `ExtraCharacterln1`) that other handlers don't use, indicating format-specific parsing quirks that need careful handling.

6. **Debugging Support**: The `Stop` statement in the error handler was used for interactive debugging. Modern equivalents would use debugger breakpoints or structured logging.

7. **Message Box UI**: The `MsgBox` call in error handler assumes a GUI environment. In a modern web/server context, errors should be logged or returned as structured data.

8. **Synchronous Processing**: All handlers are called synchronously. Modern implementation should support async/await for better scalability, especially if handlers perform I/O operations.

### Modern Equivalent

```typescript
interface ProcessingContext {
  thisRun: Date;
  email: string;
  lineNo: number;
  filePath: string;
  sender: string;
  companyId: number;
  branchId: number;
}

interface ExtractedData {
  formatName: string;
  customerId: number;
  customer: string;
  hawb: string;
  mawb: string;
  pickupFromId: number;
  pickupFromName: string;
  pickupFromAddress: string;
  pickupFromNotes: string;
  pickupDate: string;
  pickupTime: string;
  deliverToId: number;
  deliverToName: string;
  deliverToAddress: string;
  deliverToNotes: string;
  deliverDate: string;
  deliverTime: string;
  quantity: number;
  weight: number;
  comments: string;
  processYN: boolean;
}

class DocumentProcessingError extends Error {
  constructor(
    message: string,
    public moduleName: string,
    public locationMark: string,
    public originalError?: Error
  ) {
    super(message);
    this.name = 'DocumentProcessingError';
  }
}

async function mineTxtFile(
  context: ProcessingContext,
  formatName: string
): Promise<ExtractedData> {
  const moduleName = 'DocumentProcessor/mineTxtFile';
  const locationMark = 'Module start';

  try {
    // Initialize result with default values
    const result: ExtractedData = {
      formatName,
      customerId: 0,
      customer: '',
      hawb: '',
      mawb: '',
      pickupFromId: 0,
      pickupFromName: '',
      pickupFromAddress: '',
      pickupFromNotes: '',
      pickupDate: '',
      pickupTime: '',
      deliverToId: 0,
      deliverToName: '',
      deliverToAddress: '',
      deliverToNotes: '',
      deliverDate: '',
      deliverTime: '',
      quantity: 0,
      weight: 0,
      comments: '',
      processYN: false,
    };

    // Route to appropriate handler
    if (formatName === 'SOS Routing') {
      return await handleSOSRouting(context, result);
    } else if (formatName === 'SOS BOL') {
      return await handleSOSBOL(context, result, false, false);
    } else if (formatName === 'SOS BOL2') {
      return await handleSOSBOL2(context, result);
    } else if (formatName === 'SOS BOL3') {
      return await handleSOSBOL3(context, result);
    } else if (formatName === 'SOS Dlvry Rcpt') {
      return await handleSOSDeliveryReceipt(context, result);
    } else if (formatName === 'SOS Alert') {
      return await handleSOSAlert(context, result);
    } else if (formatName.startsWith('SOS MAWB')) {
      return await handleSOSMAWB(context, result);
    } else if (formatName === 'SOS Forward Air Fast Book') {
      return await handleFAFastBook(context, result);
    } else if (formatName === 'SOS Battery Advisory 2') {
      return await handleBatteryAdvisory2(context, result);
    } else {
      return await handleUnknownFormat(context, result);
    }
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);

    // Log error instead of showing message box
    console.error(`Error in ${moduleName} at ${locationMark}:`, errorMessage);

    throw new DocumentProcessingError(
      errorMessage,
      moduleName,
      locationMark,
      error instanceof Error ? error : undefined
    );
  }
}
```

### Key Improvements in Modern Implementation

1. **Type Safety**: TypeScript interfaces define clear contracts for all data structures
2. **Async/Await**: Handlers can perform async operations without blocking
3. **Structured Errors**: Custom error class with module context instead of message boxes
4. **Return Values**: Functions return data objects instead of modifying parameters by reference
5. **Logging**: Console/structured logging instead of interactive message boxes
6. **String Matching**: Explicit logic with `startsWith()` for format matching
7. **Testability**: Pure functions with clear inputs/outputs are easier to unit test
8. **Maintainability**: Handler registry pattern makes it easy to add new document formats
