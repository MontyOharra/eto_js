# User Authentication & Activity Tracking - Design Spec

## Overview

This design covers user authentication for the ETO system, enabling tracking of which user approves pending updates. The system integrates with existing HTC Access database tables for user management.

---

## Goals

1. **Identify the current user** - via auto-auth or manual login
2. **Persist user context in session** - available throughout app lifetime
3. **Record user ID on pending update approvals** - for audit trail

---

## Database Tables (Access DB: HTC000_Data_Staff.accdb)

### HTC000 WhosLoggedIn
Tracks users currently logged into HTC system.

| Column | Type | Purpose |
|--------|------|---------|
| WLI_StaffID | SMALLINT | Links to Staff.Staff_EmpID |
| PCName | VARCHAR(255) | Computer name |
| PCLid | VARCHAR(255) | Windows login ID |
| LogInTime | DATETIME | Login timestamp |

### HTC000_G090_T010 Staff
User credentials and profile.

| Column | Type | Purpose |
|--------|------|---------|
| Staff_EmpID | SMALLINT | **Primary identifier** (unique) |
| Staff_Login | VARCHAR(100) | Username for manual login |
| Staff_Password | VARCHAR(50) | Password (plain text) |
| Staff_FirstName | VARCHAR(50) | Display name |
| Staff_LastName | VARCHAR(50) | Display name |
| Staff_PC_LID | VARCHAR(255) | Windows login ID |
| Staff_Active | BIT | Is user active |

**Note:** `Staff_CoID` and `Staff_BrID` are always 1, so only `Staff_EmpID` is needed for identification.

---

## Authentication Flows

### Flow 1: Auto-Authentication (Primary)

On app startup, attempt automatic login using the HTC WhosLoggedIn table.

```
┌─────────────────────────────────────────────────────────────────┐
│                        APP STARTUP                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  1. Get current machine info:                                    │
│     - PCName = os.hostname()                                     │
│     - PCLid = os.userInfo().username                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. Query WhosLoggedIn:                                          │
│     SELECT WLI_StaffID FROM [HTC000 WhosLoggedIn]                │
│     WHERE PCName = ? AND PCLid = ?                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │                   │
               Found?              Not Found
                    │                   │
                    ▼                   ▼
┌──────────────────────────┐  ┌──────────────────────────┐
│  3. Lookup Staff details │  │  Show Login Page         │
│     by WLI_StaffID       │  │  (Manual auth required)  │
└──────────────────────────┘  └──────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. Store in session:                                            │
│     - staff_emp_id                                               │
│     - display_name (FirstName + LastName)                        │
│  5. Navigate to Dashboard                                        │
└─────────────────────────────────────────────────────────────────┘
```

### Flow 2: Manual Login (Fallback)

When auto-auth fails or user explicitly logs out.

```
┌─────────────────────────────────────────────────────────────────┐
│                       LOGIN PAGE                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Username: [_______________]                             │    │
│  │  Password: [_______________]                             │    │
│  │                                                          │    │
│  │  [Sign In]                                               │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  1. Query Staff table:                                           │
│     SELECT Staff_EmpID, Staff_FirstName, Staff_LastName          │
│     FROM [HTC000_G090_T010 Staff]                                │
│     WHERE Staff_Login = ?                                        │
│       AND Staff_Password = ?                                     │
│       AND Staff_Active = True                                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │                   │
               Found?              Not Found
                    │                   │
                    ▼                   ▼
┌──────────────────────────┐  ┌──────────────────────────┐
│  2. Store in session:    │  │  Show error:             │
│     - staff_emp_id       │  │  "Invalid credentials"   │
│     - display_name       │  └──────────────────────────┘
│  3. Navigate to Dashboard│
└──────────────────────────┘
```

---

## Session Management

### Session Storage

The authenticated user is stored in **React Context** (in-memory only).

```typescript
interface AuthSession {
  staffEmpId: number;
  displayName: string;
  loginMethod: 'auto' | 'manual';
  loginTime: Date;
}
```

**Key behaviors:**
- **No persistence** - User must re-authenticate on every app restart
- **Auto-auth is attempted first** - Only shows login page if auto-auth fails
- **Logout clears session** - Returns to login page

### Auth Context

```typescript
interface AuthContextValue {
  session: AuthSession | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}
```

---

## Logout Flow

1. User clicks "Logout" button in Settings
2. Clear session from React Context
3. Navigate to Login page
4. Next app interaction requires re-authentication

**Note:** We do NOT modify the WhosLoggedIn table - it's managed by the main HTC system.

---

## Backend API Endpoints

### POST /api/auth/auto-login

Attempt auto-authentication using machine credentials.

**Request:**
```json
{
  "pcName": "WORKSTATION-01",
  "pcLid": "john.smith"
}
```

**Response (success):**
```json
{
  "success": true,
  "user": {
    "staffEmpId": 42,
    "displayName": "John Smith"
  }
}
```

**Response (not found):**
```json
{
  "success": false,
  "error": "No active session found for this machine"
}
```

### POST /api/auth/login

Manual username/password authentication.

**Request:**
```json
{
  "username": "jsmith",
  "password": "secret123"
}
```

**Response (success):**
```json
{
  "success": true,
  "user": {
    "staffEmpId": 42,
    "displayName": "John Smith"
  }
}
```

**Response (failure):**
```json
{
  "success": false,
  "error": "Invalid username or password"
}
```

### GET /api/auth/session

Get current session info (for re-validation).

**Response:**
```json
{
  "authenticated": true,
  "user": {
    "staffEmpId": 42,
    "displayName": "John Smith"
  }
}
```

---

## Integration: Pending Update Approvals

When a user approves a pending update, include their Staff_EmpID.

### Frontend

```typescript
// In approve mutation
const approveUpdate = useMutation({
  mutationFn: (updateId: number) =>
    api.post(`/pending-updates/${updateId}/approve`, {
      approvedBy: session.staffEmpId  // Include user ID
    })
});
```

### Backend

```python
# In approve_pending_update endpoint
@router.post("/pending-updates/{update_id}/approve")
async def approve_pending_update(
    update_id: int,
    request: ApproveRequest,  # Contains approved_by: int
):
    # ... existing approval logic ...

    # Record who approved in history
    service.record_update_approval(
        update_id=update_id,
        approved_by=request.approved_by,
        approved_at=datetime.now()
    )
```

### History Table Addition

Add `approved_by` column to track the staff member who approved updates.

```sql
-- Conceptual - actual implementation in app database
ALTER TABLE pending_update_history
ADD COLUMN approved_by INTEGER;  -- Staff_EmpID
```

---

## Implementation Tasks

### Backend

1. **Add Auth Router** (`server/src/api/routers/auth.py`)
   - POST `/auth/auto-login` - Query WhosLoggedIn table
   - POST `/auth/login` - Query Staff table
   - GET `/auth/session` - Validate session

2. **Add Auth Service** (`server/src/features/auth/service.py`)
   - `attempt_auto_login(pc_name, pc_lid)` - Check WhosLoggedIn
   - `login(username, password)` - Validate credentials
   - `get_staff_by_id(emp_id)` - Get staff details

3. **Add Staff Repository** (`server/src/shared/database/repositories/staff.py`)
   - Query HTC000_G090_T010 Staff table
   - Query HTC000 WhosLoggedIn table

4. **Update Pending Update Approval**
   - Add `approved_by` field to approval request
   - Record in history table

### Frontend

1. **Add Auth Context** (`client/src/renderer/contexts/AuthContext.tsx`)
   - Provide session state to entire app
   - Handle login/logout methods

2. **Update Login Page** (`client/src/renderer/pages/login.tsx`)
   - Attempt auto-login on mount
   - Show login form only if auto-login fails
   - Handle manual login submission

3. **Add Auth Guard** (`client/src/renderer/components/AuthGuard.tsx`)
   - Wrap dashboard routes
   - Redirect to login if not authenticated

4. **Add Logout Button** (Settings page)
   - Clear session and navigate to login

5. **Update Pending Update Approval**
   - Include `staffEmpId` in approve request

### Electron (Main Process)

1. **Add IPC handlers for machine info**
   - `get-machine-info` → returns { pcName, pcLid }
   - Uses `os.hostname()` and `os.userInfo().username`

---

## Security Considerations

1. **Passwords are plain text** - This is a legacy constraint from the Access database. Consider:
   - HTTPS for API communication
   - Don't log passwords
   - Future migration to hashed passwords

2. **No session tokens** - Session is in-memory only, no cookies or tokens stored
   - Low risk since Electron app is local
   - Re-auth required on each app restart

3. **WhosLoggedIn is read-only** - We don't modify this table
   - Avoids conflicts with main HTC system
   - User must be logged into HTC system for auto-auth to work

---

## File Structure

```
server/src/
├── api/
│   └── routers/
│       └── auth.py                 # Auth endpoints
├── features/
│   └── auth/
│       └── service.py              # Auth business logic
└── shared/
    └── database/
        └── repositories/
            └── staff.py            # Staff table queries

client/src/renderer/
├── contexts/
│   └── AuthContext.tsx             # Auth state provider
├── components/
│   └── AuthGuard.tsx               # Route protection
├── pages/
│   └── login.tsx                   # Updated login page
└── features/
    └── settings/
        └── components/
            └── LogoutButton.tsx    # Logout functionality
```

---

## Open Questions

1. Should we show the user's name somewhere in the UI (header/navbar)?
2. Should failed login attempts be logged/limited?
3. Any timeout for session inactivity?
