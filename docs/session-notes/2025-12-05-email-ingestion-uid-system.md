# Session Notes: Email Ingestion UID-Based System

**Date:** 2025-12-05

## Summary

This session focused on building a new UID-based email ingestion system to replace the old datetime-based polling approach. The key insight is that IMAP UIDs provide reliable incremental tracking - we fetch emails with `UID > last_processed_uid` instead of filtering by date.

## Completed Work

### 1. Base Integration Interface Updates
**File:** `server/src/features/email/integrations/base_integration.py`

Added:
- `EmailMessage` dataclass with `uid` as a required field for tracking
- `get_emails_since_uid(folder_name, since_uid, limit)` abstract method
- `get_highest_uid(folder_name)` abstract method (for initializing new configs)

### 2. IMAP Integration Implementation
**File:** `server/src/features/email/integrations/imap_integration.py`

Implemented:
- `get_emails_since_uid()` - Uses IMAP `UID SEARCH` and `UID FETCH` commands
- `get_highest_uid()` - Returns highest UID in folder
- `_fetch_email_by_uid()` - Fetches single email by UID
- `_parse_email_message()` - Parses raw email into `EmailMessage` dataclass
- `_decode_header_value()` - Handles RFC 2047 encoded headers

### 3. Ingestion Module Skeleton
**File:** `server/src/features/email/ingestion/__init__.py`

Created module structure (implementation pending).

## Planned Architecture (Not Yet Implemented)

### IngestionListener (one per active config)
- Owns a single IMAP connection
- Runs in its own thread
- Poll loop: `get_emails_since_uid()` → process → update `last_processed_uid` → sleep → repeat
- Handles reconnection on connection drops

### IngestionManager (singleton)
- Manages all active listeners (`config_id → IngestionListener` dict)
- Methods:
  - `activate_config(config_id)` - Create & start listener
  - `deactivate_config(config_id)` - Stop & remove listener
  - `get_active_configs()` - List running listeners
  - `shutdown()` - Stop all listeners
- On startup, restores listeners for configs with `is_active=True`

### EmailService Additions
Add to `server/src/features/email/service.py`:
- `activate_ingestion_config(config_id)` - Calls manager, sets `is_active=True`
- `deactivate_ingestion_config(config_id)` - Calls manager, sets `is_active=False`

### API Endpoints
Add to `server/src/api/routers/email_ingestion_configs.py`:
- `POST /api/email-ingestion-configs/{id}/activate`
- `POST /api/email-ingestion-configs/{id}/deactivate`

## Data Flow

```
API: POST /activate
        │
        ▼
EmailService.activate_ingestion_config(config_id)
        │
        ▼
IngestionManager.activate_config(config_id)
  - Load config + account from DB
  - Create ImapIntegration with credentials
  - Create & start IngestionListener thread
  - Update DB: is_active=True, activated_at=now
        │
        ▼
IngestionListener (thread)
  - connect()
  - loop:
      get_emails_since_uid(folder, last_processed_uid)
      for each email: process, update last_processed_uid
      sleep(poll_interval_seconds)
```

## Key Files Modified

| File | Changes |
|------|---------|
| `server/src/features/email/integrations/base_integration.py` | Added `EmailMessage` dataclass, abstract UID methods |
| `server/src/features/email/integrations/imap_integration.py` | Implemented UID-based fetch methods |
| `server/src/features/email/ingestion/__init__.py` | Created module (skeleton) |

## Related Existing Types

- `EmailIngestionConfig` in `server/src/shared/types/email_ingestion_configs.py`
  - Has `last_processed_uid: int | None` field
  - Has `is_active: bool` field
  - Has `poll_interval_seconds: int` field

- `EmailAccount` in `server/src/shared/types/email_accounts.py`
  - Has credentials and provider settings needed to create integrations

## Next Steps

1. Implement `IngestionListener` class with threading
2. Implement `IngestionManager` singleton
3. Add activate/deactivate methods to `EmailService`
4. Add API endpoints for activate/deactivate
5. Add email processing callback (filter rules, PDF extraction)
6. Wire up manager initialization on server startup

## Notes

- IMAP requires persistent connections - each listener maintains its own connection
- Graph API (future) can use stateless calls since it's REST-based
- The `use_idle` config field is for future IMAP IDLE support (push notifications instead of polling)
