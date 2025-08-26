# ETO System - Session Changes Summary

## Overview
This document summarizes the major changes made to the Email-to-Order (ETO) PDF extraction system during this development session.

## Key Issues Addressed

### 1. Email Cursor Tracking for Downtime Recovery
**Problem**: System couldn't recover emails sent during server downtime.

**Solution**: Implemented comprehensive cursor tracking system.

#### Database Changes:
- **New Table**: `email_cursors`
  - `email_address`, `folder_name` (unique combination)
  - `last_processed_message_id`, `last_processed_received_date`
  - Processing statistics (`total_emails_processed`, `total_pdfs_found`)
  - Timestamps for tracking

#### Email Processing Enhancements:
- **Startup cursor initialization**: Resume from last processed email
- **Missed email processing**: Automatically detects and processes emails sent during downtime
- **Real-time cursor updates**: Updates cursor after each email processed
- **Timezone handling**: Proper conversion between Outlook timezone-aware and database naive datetimes

#### New API Endpoint:
- `GET /api/email/cursor` - View cursor status for current monitoring session

### 2. Timezone Comparison Error Fixes
**Problem**: `can't compare offset-naive and offset-aware datetimes` errors preventing missed email processing.

**Solution**: 
- Convert both Outlook datetimes (timezone-aware) and cursor datetimes (naive) to naive before comparison
- Added error handling for comparison failures
- Ensured consistent datetime storage in cursors

### 3. Email-Based ETO Run System Restructure
**Problem**: ETO runs were PDF-based, meaning duplicate PDFs wouldn't be processed even if they came in different emails representing separate business transactions.

**Solution**: Restructured system to be email-centric.

#### Database Schema Changes:
```sql
-- ETO Runs table updates
ALTER TABLE eto_runs ADD COLUMN email_id INT NOT NULL;
ALTER TABLE eto_runs ADD COLUMN is_duplicate_pdf BOOLEAN DEFAULT FALSE;
ALTER TABLE eto_runs ADD COLUMN duplicate_handling_result VARCHAR(100);

-- Added relationships
Email ↔ EtoRun (direct relationship)
```

#### Processing Logic Changes:
- **Always creates ETO run** for each email with PDFs, even if PDF is duplicate
- **Duplicate detection**: Checks if PDF hash already exists in system
- **Duplicate flagging**: Marks runs with duplicate status but processes them anyway
- **Email context preservation**: Maintains email-to-run relationship throughout processing pipeline

#### API Updates:
- Updated `/api/eto-runs` to show direct email information
- Added duplicate status fields in API responses
- Better email-PDF-run relationship tracking

## Technical Implementation Details

### Files Modified:

#### `src/database.py`
- Added `EmailCursor` model with unique constraints
- Updated `EtoRun` model to include `email_id` and duplicate tracking fields
- Added email cursor management methods:
  - `get_or_create_email_cursor()`
  - `update_email_cursor()`
  - `increment_cursor_pdf_count()`

#### `src/outlook_service.py`
- Enhanced connection methods with cursor initialization
- Added `_process_missed_emails_since_cursor()` method
- Added `_check_if_duplicate_pdf()` method
- Fixed timezone handling in cursor updates
- Updated ETO run creation to include email context

#### `src/processing_worker.py`
- Updated `_create_data_extraction_run()` to include email_id
- Fixed JSON import that was missing

#### `src/app.py`
- Added `/api/email/cursor` endpoint
- Updated `/api/eto-runs` to show email-based data structure
- Added duplicate status fields to API responses

### Key Technical Concepts Implemented:

#### 1. Cursor-Based Email Recovery
```python
# Startup process:
1. Get/create cursor for email/folder combination
2. If cursor exists: process missed emails since cursor timestamp
3. Set poll time to NOW for future real-time monitoring
4. Update cursor after each processed email
```

#### 2. Timezone-Safe Datetime Handling
```python
# Convert timezone-aware to naive for comparison
if hasattr(datetime_obj, 'replace') and datetime_obj.tzinfo is not None:
    datetime_obj = datetime_obj.replace(tzinfo=None)
```

#### 3. Email-Centric Processing Model
```python
# Old: PDF-based runs
ETO Run → PDF File

# New: Email-based runs  
Email → ETO Run → PDF File
```

## Business Impact

### Before Changes:
- ❌ Emails sent during downtime were lost
- ❌ Duplicate PDFs in different emails weren't processed
- ❌ No audit trail of email-to-processing relationship
- ❌ System couldn't recover from outages gracefully

### After Changes:
- ✅ **Downtime Recovery**: System automatically catches up on missed emails
- ✅ **Email-Centric Processing**: Every email with PDFs gets processed individually
- ✅ **Duplicate Awareness**: System knows when PDFs are duplicates but processes them anyway
- ✅ **Audit Trail**: Clear relationship between emails and processing runs
- ✅ **Robust Operations**: System handles outages and restarts gracefully

## Usage Examples

### Starting Email Monitoring (with automatic recovery):
```bash
curl -X POST http://localhost:8080/api/email/start \
  -H "Content-Type: application/json" \
  -d '{"email_address": "em.harrah.business@gmail.com", "folder_name": "test"}'
```

### Checking Cursor Status:
```bash
curl http://localhost:8080/api/email/cursor
```

### Viewing ETO Runs (now with email context):
```bash
curl http://localhost:8080/api/eto-runs?limit=10
```

Response now includes:
```json
{
  "email_id": 123,
  "is_duplicate_pdf": false,
  "duplicate_handling_result": "processed_as_new",
  "email": {
    "subject": "Order #123",
    "sender_email": "customer@company.com"
  }
}
```

## System Behavior Changes

### Workflow Example:
```
1. Email A: "Order #123" with PDF (hash: abc123...)
   → Creates ETO Run #1 (email_id=1, is_duplicate=false)

2. Email B: "Resend Order #123" with same PDF (hash: abc123...)  
   → Creates ETO Run #2 (email_id=2, is_duplicate=true)
   → Both runs process, system flags #2 as duplicate

3. Server goes down, Email C arrives
   → On restart, system detects missed Email C and processes it automatically
```

## Notes for Future Development

### PDF Object Storage Discussion:
Current JSON approach works well for typical business documents. If performance issues arise with very large PDFs (>50MB with thousands of objects), consider implementing normalized table structure:

```sql
CREATE TABLE pdf_objects (
    id INT PRIMARY KEY,
    pdf_file_id INT,
    object_type VARCHAR(50),
    page_number INT,
    bbox_x1 FLOAT, bbox_y1 FLOAT,
    bbox_x2 FLOAT, bbox_y2 FLOAT,
    properties JSON,
    signature_hash VARCHAR(64)
);
```

### Next Development Phase:
- Wire up client application for template creation from unrecognized PDFs
- Implement actual data extraction functionality (currently placeholder)
- Build template creation UI for PDFs marked as "needs_template"

## Testing Recommendations

1. **Test downtime recovery**: Stop server, send emails, restart server, verify processing
2. **Test duplicate handling**: Send same PDF in different emails, verify both are processed
3. **Test cursor persistence**: Verify cursor survives server restarts
4. **Test timezone handling**: Test with different system timezones

---

## Current Session: January 26, 2025

### Session Status: Email Ingestion Implementation

#### Session Goal: 
**Get email ingestion and processing working end-to-end**

#### Target Workflow:
1. **Server Startup**: No email processing initially
2. **API Start Call**: `/api/email/start` with config (email, folder, PDF filter)
3. **Cursor Recovery**: Check database for most recent cursor, process missed emails immediately
4. **Real-time Monitoring**: Process new emails as they arrive, updating cursor each time
5. **Graceful Stop/Restart**: Maintain cursor state for downtime recovery

#### Completed:
- ✅ **System Architecture Analysis**: Complete functionality review of ETO PDF processing system
- ✅ **Component Documentation**: Documented all 7 major system components and their interactions
- ✅ **API Endpoint Mapping**: Catalogued all REST endpoints and their purposes
- ✅ **Current Issues Identified**: Database schema mismatch and connection problems

#### Current Issues Being Addressed:
1. **Database Schema Problems**: 
   - Missing columns in `eto_runs` table causing processing worker failures
   - SQL Server authentication issues with 'test' user credentials
   
2. **Email Ingestion Configuration**:
   - Target email: `em.harrah.business@gmail.com`
   - Target folder: `test`
   - Filter: emails with PDF attachments only
   - Server running on: `http://localhost:8080`

#### Progress Update:
- ✅ **RESOLVED**: Database connection and schema issues resolved
- ✅ **EMAIL SERVICE CONNECTED**: Successfully connected to Gmail "test" folder  
- ✅ **COM Reconnection Working**: Automatic reconnection logic functioning properly
- ✅ **EMAIL INGESTION WORKING**: Successfully processing emails with PDFs
- ✅ **PDF EXTRACTION WORKING**: 8434 objects extracted from 18-page test PDF
- ✅ **BACKGROUND WORKER FUNCTIONING**: ETO runs created and processed
- ✅ **TEMPLATE MATCHING WORKING**: Correctly marked as "needs_template"

#### Issues Fixed This Session:
1. **Duplicate PDF Constraint**: Removed unique constraint on `sha256_hash` to allow same PDF in different emails
2. **Duplicate Email Processing**: Fixed issue where missed emails were processed twice (once in recovery, once in real-time)

#### Next Steps (Priority Order):
- [x] ~~Test email detection and cursor recovery~~ ✅ Working
- [ ] Test with multiple emails containing same PDF (after server restart)
- [ ] Verify template creation workflow
- [ ] Test complete end-to-end processing pipeline

---

## Future Containerization Plan

### **Current Decision**: Continue with COM approach for prototype testing

### **Future Migration Path** (When ready to containerize):

#### **Recommended Approach: Microsoft Graph API**
- **Cost**: FREE using Microsoft 365 Developer Program
- **Benefits**: Full containerization, cross-platform, more reliable
- **Setup**: 
  1. Sign up for M365 Developer Program (free 90-day renewable tenant)
  2. Replace `outlook_service.py` with `graph_api_service.py` 
  3. Implement OAuth2 authentication flow
  4. Replace COM calls with Graph API REST calls

#### **Migration Effort**: ~1 week
- Graph API integration: 2-3 days
- Containerization: 1 day  
- Testing: 1-2 days

#### **Key Graph API Endpoints (All Free)**:
```
GET /me/mailFolders           # List folders
GET /me/messages              # Get emails  
GET /me/messages/{id}/attachments  # Download PDFs
```

#### **Alternative Options**:
- **Hybrid**: Containerize everything except Outlook COM
- **Windows Containers**: High complexity, requires Windows host
- **IMAP/Exchange**: Limited functionality compared to Graph API

**Decision**: Proceed with COM for now, migrate to Graph API when containerization becomes priority

#### Context Files Created:
- This changelog updated for session tracking and context preservation

---

*Session started: January 26, 2025*
*Previous changes documented: August 24-25, 2025*