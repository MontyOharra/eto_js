# Session Continuity Document

## Current Status (2025-12-05)

### Session Summary

This session focused on building out the **Email Account and Ingestion Config API layer**:
1. **Email Ingestion Configs API** - Full CRUD endpoints for managing email folder monitoring configs
2. **Email Account Folders API** - New endpoint to list IMAP folders from connected accounts
3. **IMAP Integration Enhancements** - Added folder listing and email fetching capabilities

---

## Recently Completed

### 1. Email Ingestion Configs API Layer

Created full API layer for managing email ingestion configurations:

**Files Created:**
- `server/src/api/schemas/email_ingestion_configs.py` - Pydantic models for API requests/responses
- `server/src/api/mappers/email_ingestion_configs.py` - Domain-to-API conversion functions
- `server/src/api/routers/email_ingestion_configs.py` - REST endpoints

**Endpoints Available:**
- `POST /api/email-ingestion-configs/validate` - Validate config before creation
- `GET /api/email-ingestion-configs` - List all configs with account info
- `GET /api/email-ingestion-configs/{id}` - Get single config
- `POST /api/email-ingestion-configs` - Create new config
- `PATCH /api/email-ingestion-configs/{id}` - Update config
- `DELETE /api/email-ingestion-configs/{id}` - Delete config

**Key Schema Types:**
- `FilterRuleSchema` - Email filter rules (sender, subject, date, attachments)
- `CreateIngestionConfigRequest` - name, account_id, folder_name, filter_rules, poll settings
- `IngestionConfigResponse` - Full config with all fields including timestamps

### 2. Email Account Folders Endpoint

Added ability to list available folders from a connected email account:

**Files Modified:**
- `server/src/api/schemas/email_accounts.py` - Added `FolderListResponse` schema
- `server/src/api/routers/email_accounts.py` - Added `GET /{account_id}/folders` endpoint
- `server/src/features/email/service.py` - Added `list_account_folders()` method

**Endpoint:**
- `GET /api/email-accounts/{account_id}/folders`
- Returns: `{ "account_id": 1, "folders": ["INBOX", "INBOX.Sent", ...] }`

### 3. IMAP Integration Enhancements

Enhanced the IMAP integration with folder listing and email fetching:

**`list_folders()` Method:**
- Properly parses IMAP LIST response format
- Handles both quoted and unquoted folder names
- Skips empty folder names (root namespace)
- Returns alphabetically sorted folder list (case-insensitive)

**Email Fetching Methods (added in parallel session):**
- `get_emails_since_uid(folder, since_uid, limit)` - UID-based email retrieval
- `get_highest_uid(folder)` - Get highest UID in folder
- `_fetch_email_by_uid(uid, folder)` - Fetch single email
- `_parse_email_message(msg, uid, folder)` - Parse to EmailMessage dataclass
- `_decode_header_value(value)` - RFC 2047 header decoding

**EmailMessage Dataclass** (in base_integration.py):
- uid, message_id, subject, sender_email, sender_name
- received_date, folder_name, body_text, body_html
- has_attachments, attachment_count, attachment_filenames

### 4. Type Narrowing Fix

Fixed Pylance type error for `get_capabilities()` call:

**Problem:** After `isinstance(integration, ImapIntegration)` check, Pylance still thought `integration` was `BaseEmailIntegration`.

**Solution:** Assign to typed local variable after isinstance check:
```python
if isinstance(integration, ImapIntegration):
    imap_integration: ImapIntegration = integration
    capabilities = imap_integration.get_capabilities()
```

---

## Architecture Notes

### Email System Architecture

The email system has been restructured to separate concerns:

```
EmailAccount (credentials)
  └─ Stores: host, port, email_address, password, capabilities
  └─ Validation: test connection before saving
  └─ One account can have multiple ingestion configs

EmailIngestionConfig (monitoring settings)
  └─ References: account_id (FK to email_accounts)
  └─ Stores: folder_name, filter_rules, poll_interval, use_idle
  └─ Activation: is_active flag, activated_at timestamp
  └─ State: last_check_time, last_processed_uid, last_error
```

### IMAP Folder Hierarchy

IMAP uses a delimiter character (usually `.` or `/`) for folder hierarchy:
- `INBOX` - Root inbox
- `INBOX.Sent` - Subfolder under INBOX
- `INBOX.SOS GLOBAL` - Another subfolder

The API returns full folder paths. Frontend can split on delimiter for tree display.

### UID-Based Polling

Email ingestion uses UID-based polling for efficiency:
1. Store `last_processed_uid` per config
2. Query: `SEARCH UID {last_uid+1}:*`
3. Server returns only new emails (no date comparison needed)
4. UIDs are unique and monotonically increasing per folder

---

## Important Files Reference

### Email Service Layer
- `server/src/features/email/service.py` - EmailService with account + ingestion config methods
- `server/src/features/email/integrations/imap_integration.py` - IMAP implementation
- `server/src/features/email/integrations/base_integration.py` - Abstract base class

### Email API Layer
- `server/src/api/routers/email_accounts.py` - Account endpoints including folders
- `server/src/api/routers/email_ingestion_configs.py` - Ingestion config endpoints
- `server/src/api/schemas/email_accounts.py` - Account schemas
- `server/src/api/schemas/email_ingestion_configs.py` - Ingestion config schemas
- `server/src/api/mappers/email_accounts.py` - Account mappers
- `server/src/api/mappers/email_ingestion_configs.py` - Ingestion config mappers

### Database Layer
- `server/src/shared/database/models.py` - EmailAccountModel, EmailIngestionConfigModel
- `server/src/shared/database/repositories/email_account.py` - Account repository
- `server/src/shared/database/repositories/email_ingestion_config.py` - Config repository

### Type Definitions
- `server/src/shared/types/email_accounts.py` - Account domain types
- `server/src/shared/types/email_ingestion_configs.py` - Config domain types

---

## Next Session Priorities

### High Priority
1. **Email Ingestion Runtime**
   - Build polling service that uses ingestion configs
   - Process emails matching filter rules
   - Track UIDs and update last_processed_uid

2. **Activate/Deactivate Config Endpoints**
   - `POST /api/email-ingestion-configs/{id}/activate`
   - `POST /api/email-ingestion-configs/{id}/deactivate`
   - Start/stop monitoring for specific configs

### Medium Priority
3. **Frontend for Email Configuration**
   - Account management UI (add/edit/delete accounts)
   - Ingestion config UI (folder selection, filter rules)
   - Config activation controls

4. **Filter Rule Implementation**
   - Apply filter rules to fetched emails
   - Filter by sender, subject, attachments, date

### Low Priority
5. **Email Attachment Handling**
   - Extract PDF attachments from emails
   - Store and process through ETO pipeline

---

## Testing Commands

```bash
# Test folder listing
curl http://localhost:8000/api/email-accounts/1/folders

# List ingestion configs
curl http://localhost:8000/api/email-ingestion-configs

# Create ingestion config
curl -X POST http://localhost:8000/api/email-ingestion-configs \
  -H "Content-Type: application/json" \
  -d '{
    "name": "SOS Orders",
    "account_id": 1,
    "folder_name": "INBOX.SOS GLOBAL",
    "poll_interval_seconds": 60
  }'
```

---

**Last Updated:** 2025-12-05
**Next Session:** Build email polling runtime and activation endpoints

**Session Notes:**
- Email account/ingestion config separation is complete
- Folder listing works with proper IMAP parsing and sorting
- UID-based email fetching infrastructure ready
- Full CRUD API available for ingestion configs
