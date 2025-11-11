# VBA Analysis: EmailDispatcher

**File**: vba-code/HTC_350C_Sub_2_of_2_CreateOrders.vba
**Last Updated**: 2025-11-11

## Table of Contents
- [Function: EmailDispatcher](#function-emaildispatcher)

---

# Function: `EmailDispatcher`

**Type**: Sub
**File**: HTC_350C_Sub_2_of_2_CreateOrders.vba
**Analyzed**: 2025-11-11

## Signature
```vba
Sub EmailDispatcher(sCoID As Integer, sBrID As Integer, SendToAddress As String, eMailSent As Boolean, Sent As String)
```

## Purpose & Overview

**Primary Purpose**: Sends an automated email to the dispatcher containing the formatted order information that was built by the `Bld_eMail` subroutine. This function retrieves the pre-formatted message body from the database and sends it using Outlook automation.

**Input**:
- `sCoID` - Company ID (Integer)
- `sBrID` - Branch ID (Integer)
- `SendToAddress` - Email address to send the message to (String)
- `eMailSent` - Output parameter indicating whether email was successfully sent (Boolean, ByRef)
- `Sent` - Output parameter for the address the email was actually sent to (String, ByRef)

**Output**:
- Returns `eMailSent` (Boolean) indicating success/failure
- Returns `Sent` (String) with the actual recipient address used

**Side Effects**:
- Sends an email via Outlook to the dispatcher
- Conditionally modifies the recipient address for testing purposes (non-production environment)

## Function Cross-References

### Functions in Same File
None - This function does not call any other functions within the same file.

### External Functions (NOT in this file)
- `HTC350C_SendEmail()` - **⚠️ EXTERNAL** - Sends email using Outlook automation; takes from address, to address, subject, body, and returns success status and actual recipient

### Built-in VBA/Access Functions
- `CurrentDb()` - Returns the current Access database object
- `OpenRecordset()` - Opens a database recordset
- `Environ()` - Retrieves environment variable values (used to check computer name)
- `MsgBox()` - Displays error messages
- `Err.Number` / `Err.Description` - Error object properties
- `Erl` - Returns the line number where error occurred

## Detailed Behavioral Breakdown

### Block 1: Error Handler Setup and Database Connection
```vba
On Error GoTo EmailDispatcher_Error
Dim db As Database: Set db = CurrentDb

Dim MsgLines As Recordset
Set MsgLines = db.OpenRecordset("Htc200F_G020_Q060 Outlook Body Sorted", dbOpenDynaset)
```
**Explanation**:
- Establishes error handling that will jump to the `EmailDispatcher_Error` label if any error occurs
- Creates a connection to the current Access database
- Opens a dynaset recordset from the query "Htc200F_G020_Q060 Outlook Body Sorted" which contains the pre-formatted email body lines
- The query name suggests it returns the message lines sorted by line number for proper ordering

### Block 2: Variable Declarations
```vba
Dim eMsubject As String
Dim eMbody As String
Dim eEditable As Boolean: eEditable = False
Dim SentTo As String

eMsubject = "Automated eMail Order Processing"

eMbody = ""
```
**Explanation**:
- Declares local variables for email subject, body, editability flag, and actual recipient
- Sets the email subject to a fixed string "Automated eMail Order Processing"
- Initializes the email body as an empty string
- `eEditable` is declared and set to False but never used (likely vestigial code)

### Block 3: Build Email Body from Database Records
```vba
If MsgLines.RecordCount > 0 Then

    MsgLines.MoveFirst
    Do Until MsgLines.EOF
        eMbody = eMbody & MsgLines!drline & vbCrLf
        MsgLines.MoveNext
    Loop
```
**Explanation**:
- Checks if there are any records in the MsgLines recordset (RecordCount > 0)
- If records exist, moves to the first record
- Loops through all records until end-of-file (EOF)
- Concatenates each line (`drline` field) to the email body with a carriage return/line feed
- This builds the complete formatted email message from database-stored lines

### Block 4: Testing Environment Override
```vba
'Stop
'Test Test Test
If Environ("computername") <> "HARRAHSERVER" Then
    SendToAddress = "tom.crabtree.2@gmail.com"
End If
'Test Test Test
```
**Explanation**:
- Checks if the code is running on the production server ("HARRAHSERVER")
- If NOT on the production server, redirects email to a test Gmail address
- This is a safety mechanism to prevent accidental emails to real dispatchers during development/testing
- Comments indicate this is explicitly for testing purposes
- Note: The `Stop` statement is commented out, which would have been used for debugging

### Block 5: Send Email via External Function
```vba
Call HTC350C_SendEmail("alert@HarrahTransportation.com", _
                       SendToAddress, _
                       eMsubject, _
                       eMbody, _
                       eMailSent, _
                       SentTo)
```
**Explanation**:
- Calls the external `HTC350C_SendEmail` function to actually send the email
- Parameters passed:
  - From address: "alert@HarrahTransportation.com"
  - To address: `SendToAddress` (possibly modified for testing)
  - Subject: "Automated eMail Order Processing"
  - Body: The concatenated message body from database
  - Output: `eMailSent` (Boolean success flag)
  - Output: `SentTo` (actual recipient used)
- The function handles the Outlook automation to send the message

### Block 6: Commented Parameter Documentation
```vba
        'sFrom As String, _
        'sSendTo As String, _
        'sSubject As String, _
        'sBody As String, _
        'seMailSent As Boolean, _
        'sSentTo As String
```
**Explanation**:
- Commented documentation showing the parameter names and types for `HTC350C_SendEmail`
- Useful for developers to understand the function signature without looking up the implementation
- Shows good documentation practice

### Block 7: Normal Exit
```vba
End If


On Error GoTo 0
Exit Sub
```
**Explanation**:
- Closes the `If MsgLines.RecordCount > 0` block
- Disables error handling with `On Error GoTo 0`
- Exits the subroutine normally

### Block 8: Error Handler
```vba
EmailDispatcher_Error:

MsgBox "Error " & Err.Number & " (" & Err.Description & ") in procedure EmailDispatcher, line " & Erl & "."
Stop
End Sub
```
**Explanation**:
- Error handler label that is jumped to if any error occurs
- Displays a message box with the error number, description, and line number
- Uses `Stop` to halt execution for debugging purposes
- Ends the subroutine

## Dependencies

**Database Objects**:
- **Queries**: `Htc200F_G020_Q060 Outlook Body Sorted` - Contains the formatted email body lines sorted by line number
- **Tables**: None directly accessed (query may access underlying tables)

**External Dependencies**:
- **External Function**: `HTC350C_SendEmail()` - Sends email via Outlook automation
- **Environment Variables**: `computername` - Used to detect production vs. test environment
- **Email System**: Microsoft Outlook (implied by the external function)

## Migration Notes

**Complexity**: Low

**Migration Strategy**:
This is a straightforward email sending function that can be replaced with a modern email service. The main logic is simple: read formatted lines from database, concatenate into body, send email.

**Challenges**:
1. **Database Query Dependency**: The function relies on a specific Access query (`Htc200F_G020_Q060 Outlook Body Sorted`) that returns pre-formatted email lines. The new system needs to either:
   - Create equivalent SQL queries against the modernized database
   - Store formatted email content in a different structure (JSON, template system)
   - Build the email body directly in code rather than storing in database

2. **VBA Recordset Iteration**: The Do/Loop pattern for iterating records is VBA-specific. Modern equivalents:
   - TypeScript/Node.js: Use array `.forEach()` or `for...of` loops with query results
   - Python: Use list comprehension or `for` loop with database cursor

3. **Environment Detection**: The `Environ("computername")` check for production vs. test is Windows-specific. Modern alternatives:
   - Use environment variables (process.env.NODE_ENV, os.environ)
   - Configuration files with environment-specific settings
   - Deployment configuration (dev, staging, production)

4. **External Email Function**: The `HTC350C_SendEmail()` function likely uses Outlook automation (COM objects). This needs complete replacement:
   - Node.js: Use nodemailer, SendGrid, AWS SES
   - Python: Use smtplib, sendmail, or email service libraries
   - Consider modern email templating systems (Handlebars, Pug)

5. **ByRef Parameters**: VBA's `ByRef` parameters (`eMailSent`, `Sent`) that allow the function to return multiple values need to be handled differently:
   - TypeScript: Return an object `{ emailSent: boolean, sentTo: string }`
   - Python: Return a tuple or named tuple `(email_sent, sent_to)`

6. **Error Handling**: VBA's `On Error GoTo` with `MsgBox` needs modernization:
   - Use try/catch blocks with structured error handling
   - Replace MsgBox with proper logging (Winston, Bunyan, Python logging)
   - Consider error monitoring services (Sentry, Rollbar)

**Modern Equivalent**:

**TypeScript/Node.js Example**:
```typescript
interface EmailResult {
  emailSent: boolean;
  sentTo: string;
}

async function emailDispatcher(
  coId: number,
  brId: number,
  sendToAddress: string
): Promise<EmailResult> {
  try {
    // Get formatted email lines from database
    const msgLines = await db.query(
      'SELECT drline FROM outlook_body ORDER BY drlineno'
    );

    // Build email body
    const emailBody = msgLines.rows
      .map(row => row.drline)
      .join('\n');

    // Environment-based recipient override
    let recipient = sendToAddress;
    if (process.env.NODE_ENV !== 'production') {
      recipient = 'test@example.com';
    }

    // Send email using modern email service
    const result = await sendEmail({
      from: 'alert@harrahtransportation.com',
      to: recipient,
      subject: 'Automated eMail Order Processing',
      text: emailBody
    });

    return {
      emailSent: result.success,
      sentTo: recipient
    };
  } catch (error) {
    logger.error('EmailDispatcher failed', { error, coId, brId });
    throw error;
  }
}
```

**Python Example**:
```python
from dataclasses import dataclass
from typing import Tuple
import os
import logging

@dataclass
class EmailResult:
    email_sent: bool
    sent_to: str

def email_dispatcher(
    co_id: int,
    br_id: int,
    send_to_address: str
) -> EmailResult:
    try:
        # Get formatted email lines from database
        cursor = db.execute(
            "SELECT drline FROM outlook_body ORDER BY drlineno"
        )
        msg_lines = cursor.fetchall()

        # Build email body
        email_body = '\n'.join(row['drline'] for row in msg_lines)

        # Environment-based recipient override
        recipient = send_to_address
        if os.environ.get('ENV') != 'production':
            recipient = 'test@example.com'

        # Send email using modern email service
        result = send_email(
            from_addr='alert@harrahtransportation.com',
            to_addr=recipient,
            subject='Automated eMail Order Processing',
            body=email_body
        )

        return EmailResult(
            email_sent=result.success,
            sent_to=recipient
        )
    except Exception as e:
        logging.error(f'EmailDispatcher failed: {e}',
                     extra={'co_id': co_id, 'br_id': br_id})
        raise
```

**Key Improvements in Modern Implementation**:
1. Async/await for non-blocking email operations
2. Structured return types instead of ByRef parameters
3. Environment-based configuration instead of hardcoded checks
4. Proper logging instead of MsgBox
5. Modern email services (SendGrid, AWS SES) instead of Outlook automation
6. Parameterized queries for database access
7. Type safety with TypeScript or Python type hints
