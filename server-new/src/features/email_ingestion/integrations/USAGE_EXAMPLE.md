# Email Integration Registry - Usage Examples

This document demonstrates how to use the new registry-based email integration system.

## Overview

The new system uses:
- **Dataclasses** for domain types (lightweight, no validation overhead)
- **Registry Pattern** for provider management (self-registering, extensible)
- **Simple kwargs** for configuration (no heavyweight Pydantic configs)

## Basic Usage

### 1. List Available Providers

```python
from features.email_ingestion.integrations import IntegrationRegistry

# Get all registered providers
providers = IntegrationRegistry.get_available_providers()
print(providers)  # ['outlook_com']

# Check if specific provider is supported
if IntegrationRegistry.is_supported("outlook_com"):
    print("Outlook COM is available!")

# Get provider metadata
info = IntegrationRegistry.get_all_provider_info()
for provider_type, metadata in info.items():
    print(f"{provider_type}: {metadata.get('name')}")
    # outlook_com: Microsoft Outlook (Local)
```

### 2. Create Integration Instance

```python
from features.email_ingestion.integrations import IntegrationRegistry

# Create Outlook COM integration
integration = IntegrationRegistry.create(
    provider_type="outlook_com",
    email_address="user@example.com",
    folder_name="Inbox"
)

# Connect and use
if integration.connect():
    print("Connected successfully!")

    # Discover accounts
    accounts = integration.discover_accounts()
    for account in accounts:
        print(f"Account: {account.email_address} ({account.display_name})")

    # Get recent emails
    emails = integration.get_recent_emails(limit=10)
    for email in emails:
        print(f"Email: {email.subject} from {email.sender_email}")
        # Attachments are already cached!
        for att in email.cached_attachments:
            print(f"  - Attachment: {att.filename} ({att.size_bytes} bytes)")

    integration.disconnect()
```

### 3. Type Conversion (Dataclass ↔ Pydantic)

In your service layer, you work with dataclasses. At the API boundary, convert to Pydantic:

```python
from shared.types.email_integrations import EmailAccount  # Dataclass
from api.schemas.email_configs import EmailAccount as EmailAccountResponse  # Pydantic

# Service layer returns dataclass
accounts = integration.discover_accounts()  # List[EmailAccount] (dataclass)

# API endpoint converts to Pydantic
api_response = [
    EmailAccountResponse.model_validate(account)  # Pydantic auto-converts
    for account in accounts
]
```

### 4. Using in EmailIngestionService

```python
class EmailIngestionService:
    def discover_email_accounts(self, provider_type: str = "outlook_com"):
        """Discover available email accounts"""
        # Create temporary integration for discovery
        integration = IntegrationRegistry.create(
            provider_type=provider_type,
            email_address=None
        )

        # Returns List[EmailAccount] (dataclass)
        return integration.discover_accounts()

    def activate_config(self, config_id: int):
        """Activate email monitoring"""
        config = self.config_repository.get_by_id(config_id)

        # Create integration with config params
        integration = IntegrationRegistry.create(
            provider_type="outlook_com",  # Could be stored in config
            email_address=config.email_address,
            folder_name=config.folder_name
        )

        if integration.connect():
            # Start listener with this integration
            # ...
```

## Adding a New Provider

To add a new email provider (e.g., Gmail API):

### 1. Create Integration Class

```python
# features/email_ingestion/integrations/gmail_api.py
from .registry import IntegrationRegistry
from .base_integration import BaseEmailIntegration
from shared.types.email_integrations import EmailMessage, EmailAccount

@IntegrationRegistry.register(
    "gmail_api",
    name="Gmail API",
    description="Connect to Gmail using Google API with OAuth2",
    requires_local_install=False,
    platforms=["windows", "mac", "linux"],
    authentication="OAuth2"
)
class GmailApiIntegration(BaseEmailIntegration):
    def __init__(self, credentials_path: str, token_path: str, email_address: str = None):
        super().__init__(
            credentials_path=credentials_path,
            token_path=token_path,
            email_address=email_address
        )
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.email_address = email_address

    def connect(self, account_identifier=None):
        # Implement Gmail OAuth2 connection
        pass

    def get_recent_emails(self, folder_name="INBOX", ...):
        # Implement Gmail API email retrieval
        # Return List[EmailMessage] (dataclass)
        pass

    # ... implement other abstract methods
```

### 2. Import in __init__.py

```python
# features/email_ingestion/integrations/__init__.py
from .gmail_api import GmailApiIntegration  # Auto-registers on import
```

### 3. Use Immediately

```python
# No changes needed to registry or service!
integration = IntegrationRegistry.create(
    provider_type="gmail_api",
    credentials_path="credentials.json",
    token_path="token.json",
    email_address="user@gmail.com"
)
```

## Key Differences from Old System

### Old Factory Pattern (server/)

```python
# ❌ Required heavyweight Pydantic config
config = OutlookComConfig(
    provider_type=EmailProvider.OUTLOOK_COM,
    account_identifier="user@example.com",
    default_folder="Inbox"
)

# ❌ Factory with isinstance checks
integration = EmailIntegrationFactory.create_integration(config)

# ❌ Returns Pydantic models
emails = integration.get_recent_emails()  # List[EmailMessage(BaseModel)]
```

### New Registry Pattern (server-new/)

```python
# ✅ Simple kwargs, no config object needed
integration = IntegrationRegistry.create(
    provider_type="outlook_com",
    email_address="user@example.com",
    folder_name="Inbox"
)

# ✅ Returns lightweight dataclasses
emails = integration.get_recent_emails()  # List[EmailMessage] (dataclass)
```

## Performance Benefits

| Aspect | Old (Pydantic) | New (Dataclass) |
|--------|----------------|-----------------|
| Instantiation | ~50μs | ~5μs |
| Attribute access | Validated | Direct |
| Memory usage | Higher | Lower |
| Serialization | Built-in | Manual (at API boundary) |
| **Best for** | API validation | Domain logic |

## Testing Example

```python
def test_outlook_integration():
    # Clear registry if needed (for test isolation)
    IntegrationRegistry.clear_registry()

    # Import to register
    from features.email_ingestion.integrations import OutlookComIntegration

    # Verify registered
    assert IntegrationRegistry.is_supported("outlook_com")

    # Create and test
    integration = IntegrationRegistry.create(
        provider_type="outlook_com",
        email_address="test@example.com"
    )

    assert integration.email_address == "test@example.com"
    assert integration.folder_name == "Inbox"
```
