# Server Redesign - Service Layer Design V2

## Overview

This document defines the service layer architecture for the redesigned server, focusing on service separation, responsibilities, and dependencies.

**Architecture Pattern:**
```
API Layer (FastAPI Routers)
    ↕ Pydantic Models (HTTP request/response validation only)
Mapper Functions (explicit conversion)
    ↕ Dataclasses (frozen, internal data structures)
Service Layer (business logic)
    ↕ Dataclasses (frozen, internal data structures)
Repository Layer (data access)
    ↕ Dataclasses ↔ SQLAlchemy ORM Models
```

---

## Design Principles

1. **Pydantic at API Boundary Only**: Pydantic models are used exclusively in the API layer for HTTP request validation and response serialization
2. **Dataclasses for Internal Use**: Services and repositories use frozen dataclasses for all internal data transfer
3. **Explicit Mapping**: Routers contain explicit mapper functions to convert between Pydantic models (API boundary) and dataclasses (internal)
4. **Service Orchestration**: Services coordinate business logic, handle transactions, and call multiple repositories
5. **Single Responsibility**: Each service has a clear, focused responsibility
6. **Dependency Injection**: Services receive dependencies via constructor
7. **Error Bubbling**: Repository errors bubble up through services to API layer
8. **Universal Dataclass Return**: ALL service methods return dataclasses (or primitives)

---

## Error Handling Strategy

### Exception Hierarchy

All services use domain-specific exceptions defined in `shared/exceptions.py`:

```python
class AppException(Exception):
    """Base exception for all application exceptions"""
    pass


# ========== Client Errors (4xx) ==========

class ClientError(AppException):
    """Base for client-side errors - maps to 4xx status codes"""
    pass


class ObjectNotFoundError(ClientError):
    """
    Resource not found (404)

    Use when:
    - GET /resources/123 but resource 123 doesn't exist
    - User references a non-existent foreign key

    Examples:
    - "Configuration 123 not found"
    - "Template 456 not found"
    - "PDF file 789 not found"
    """
    pass


class ConflictError(ClientError):
    """
    State conflict (409) - request conflicts with current resource state

    Use when:
    - Cannot perform operation due to current state
    - State transition not allowed
    - Resource already in target state
    - Business rules prevent the operation

    Examples:
    - "Configuration is already active"
    - "Cannot update active configuration. Deactivate first."
    - "Cannot delete active configuration. Deactivate first."
    - "Template already has version 1"
    - "Cannot reprocess run with status 'processing'"
    """
    pass


class ValidationError(ClientError):
    """
    Business validation error (400) - request data is semantically invalid

    Use when:
    - Business validation rules fail (beyond Pydantic schema)
    - Invalid combinations of parameters
    - Custom validation logic fails

    Examples:
    - "Invalid email provider: 'unknown'"
    - "poll_interval_seconds must be at least 5"
    - "Signature objects must reference valid PDF objects"

    Note: Pydantic schema validation automatically returns 422, not 400
          This is for business validation that happens in services
    """
    pass


# ========== Server Errors (5xx) ==========

class ServerError(AppException):
    """Base for server-side errors - maps to 5xx status codes"""
    pass


class ServiceError(ServerError):
    """
    Service operation failed (500) - infrastructure or external service failure

    Use when:
    - Database operations fail unexpectedly
    - External integrations fail (email, file system)
    - Background services fail to start/stop
    - Unexpected runtime errors

    Examples:
    - "Failed to start email monitoring: Connection refused"
    - "Failed to compile pipeline: Dask compilation error"
    - "Failed to store PDF: Disk full"
    - "Failed to connect to email provider"
    """
    pass


class ServiceUnavailableError(ServerError):
    """
    Service temporarily unavailable (503)

    Use when:
    - Database is down
    - Required external service is down
    - System is in maintenance mode
    - Rate limit exceeded (external service)

    Examples:
    - "Database connection unavailable"
    - "Email service is temporarily down"
    """
    pass
```

### Decision Tree for Choosing Exceptions

```
Is it a missing resource?
  → ObjectNotFoundError (404)

Is it a state conflict (resource exists but current state doesn't allow operation)?
  → ConflictError (409)

Is it invalid request data (custom business validation)?
  → ValidationError (400)

Is it an infrastructure/external service failure?
  → ServiceError (500)

Is it a temporary service outage?
  → ServiceUnavailableError (503)
```

### Service Layer Error Handling Rules

**Rule 1: Simple Repository Passthroughs**
- Methods that directly call a single repository method
- **NO try-except blocks** - let exceptions propagate naturally
- Examples: `get_config()`, `list_configs_summary()`, `create_config()`

```python
# CORRECT - No error handling needed
def get_config(self, config_id: int) -> Optional[EmailConfig]:
    return self.config_repository.get_by_id(config_id)

# WRONG - Redundant try-except
def get_config(self, config_id: int) -> Optional[EmailConfig]:
    try:
        return self.config_repository.get_by_id(config_id)
    except Exception as e:
        raise e  # ← Completely redundant!
```

**Rule 2: Business Validation**
- Check conditions and throw domain-specific exceptions
- Use `ObjectNotFoundError` for missing resources (→ 404)
- Use `ConflictError` for state conflicts (→ 409)
- Use `ValidationError` for business validation errors (→ 400)

```python
# CORRECT - Explicit validation with domain exceptions
def delete_config(self, config_id: int) -> EmailConfig:
    config = self.config_repository.get_by_id(config_id)

    # Missing resource → 404
    if not config:
        raise ObjectNotFoundError(f"Configuration {config_id} not found")

    # Store config before deletion
    config_to_delete = config

    # State conflict → 409
    if config.is_active:
        raise ConflictError("Cannot delete active configuration. Deactivate first.")

    self.config_repository.delete(config_id)
    return config_to_delete

# CORRECT - Input validation
def discover_email_accounts(self, provider_type: str) -> list[EmailAccount]:
    # Invalid parameter → 400
    if not IntegrationRegistry.is_supported(provider_type):
        available = IntegrationRegistry.get_available_providers()
        raise ValidationError(
            f"Provider '{provider_type}' is not supported. "
            f"Available providers: {', '.join(available)}"
        )
    # ...
```

**Rule 3: Complex Operations with External Integrations**
- Methods with external integrations, multi-step logic, or transformations
- **DO use try-except** to add logging context and wrap low-level exceptions
- Preserve domain exceptions (ObjectNotFoundError, ConflictError, ValidationError) by re-raising
- Wrap unexpected infrastructure failures in `ServiceError` (→ 500)

```python
# CORRECT - Add context and wrap exceptions
def activate_config(self, config_id: int) -> EmailConfig:
    try:
        config = self.config_repository.get_by_id(config_id)

        # Missing resource → 404
        if not config:
            raise ObjectNotFoundError(f"Configuration {config_id} not found")

        # State conflict → 409
        if config.is_active:
            raise ConflictError("Configuration is already active")

        # Start monitoring (infrastructure operation - can fail with ServiceError)
        self.ingestion_service.start_monitoring(config)

        # Update database
        updated_config = self.config_repository.update(
            config_id,
            EmailConfigUpdate(is_active=True, activated_at=datetime.now(timezone.utc))
        )

        logger.info(f"Activated configuration {config_id}")
        return updated_config

    except ObjectNotFoundError:
        # Preserve 404 errors unchanged
        raise

    except ConflictError:
        # Preserve 409 errors unchanged
        raise

    except Exception as e:
        # Wrap infrastructure failures → 500
        logger.error(f"Failed to activate config {config_id}: {e}", exc_info=True)
        raise ServiceError(f"Failed to start email monitoring: {str(e)}") from e
```

### API Layer Exception Handlers

The API layer uses global exception handlers to map service exceptions to HTTP status codes:

```python
# In server-new/src/api/exception_handlers.py
from fastapi import Request, status
from fastapi.responses import JSONResponse
from shared.exceptions import (
    ObjectNotFoundError,
    ConflictError,
    ValidationError,
    ServiceError,
    ServiceUnavailableError
)
import logging

logger = logging.getLogger(__name__)

def register_exception_handlers(app):
    """Register global exception handlers for FastAPI app"""

    @app.exception_handler(ObjectNotFoundError)
    def handle_not_found(request: Request, exc: ObjectNotFoundError):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": str(exc)}
        )

    @app.exception_handler(ConflictError)
    def handle_conflict(request: Request, exc: ConflictError):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": str(exc)}
        )

    @app.exception_handler(ValidationError)
    def handle_validation_error(request: Request, exc: ValidationError):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc)}
        )

    @app.exception_handler(ServiceError)
    def handle_service_error(request: Request, exc: ServiceError):
        # Log server errors (infrastructure failures - not client's fault)
        logger.error(f"Service error: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(exc)}
        )

    @app.exception_handler(ServiceUnavailableError)
    def handle_unavailable(request: Request, exc: ServiceUnavailableError):
        # Log service availability issues
        logger.error(f"Service unavailable: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": str(exc)}
        )

    @app.exception_handler(Exception)
    def handle_generic_error(request: Request, exc: Exception):
        # Catch-all for unexpected errors
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"}
        )

# In server-new/src/main.py
from api.exception_handlers import register_exception_handlers

app = FastAPI()
register_exception_handlers(app)
```

### Router Implementation - Clean and Simple

With global exception handlers, routers don't need try-except blocks:

```python
# In server-new/src/api/routers/email_configs.py

@router.get("/{id}", response_model=EmailConfigDetail)
def get_email_config(
    id: int,
    config_service: EmailConfigService = Depends(...)
) -> EmailConfigDetail:
    """Get email configuration details"""

    # Just call the service - exceptions handled globally!
    config = config_service.get_config(id)

    if not config:
        raise ObjectNotFoundError(f"Configuration {id} not found")

    return EmailConfigDetail(**config.model_dump())

@router.delete("/{id}")
def delete_config(
    id: int,
    config_service: EmailConfigService = Depends(...)
):
    """Delete email configuration"""

    # Service throws ObjectNotFoundError → 404
    # Service throws ConflictError → 409
    # Any unexpected exception → 500
    config_service.delete_config(id)

    return Response(status_code=204)
```

---

## Service 1: Email Configuration Service

**Location**: `server-new/src/features/email_configs/service.py`

**Purpose**: Outward-facing service that manages email configuration CRUD operations and lifecycle. Serves as the primary interface for the email-configs API router. Coordinates configuration validation and delegates activation/deactivation to the Email Ingestion Service. Does not manage listener threads or integrations directly.

**Dependencies**:
- `DatabaseConnectionManager` - For database access and transaction management
- `EmailConfigRepository` - For email configuration CRUD operations
- `EmailIngestionService` - For starting/stopping email monitoring during activation/deactivation

**Responsibilities**:
- Email configuration CRUD operations (create, read, update, delete, list)
- Configuration lifecycle management (activate, deactivate)
- Business validation (e.g., cannot update active config)
- Coordination between repository layer and ingestion service
- Does NOT handle: Discovery, connection testing, listener management (those are in EmailIngestionService)

**Constructor**:
```python
def __init__(
    self,
    connection_manager: DatabaseConnectionManager,
    ingestion_service: EmailIngestionService
):
    self.connection_manager = connection_manager
    self.ingestion_service = ingestion_service
    self.config_repository = EmailConfigRepository(connection_manager=connection_manager)
```

**Public Methods**:

### 1. `list_configs_summary(order_by, desc)` → list[EmailConfigSummary]

**Called by**: Router endpoint `GET /email-configs`

**Purpose**: List all email configurations with summary information

**Implementation**:
```python
def list_configs_summary(
    self,
    order_by: str = "name",
    desc: bool = False
) -> list[EmailConfigSummary]:
    """
    List all email configurations with summary information.

    Args:
        order_by: Field to sort by ("name", "is_active", "last_check_time")
        desc: Sort descending if True

    Returns:
        List of EmailConfigSummary dataclasses
    """
    return self.config_repository.get_all_summaries(order_by, desc)
```

**Repository calls**: `config_repository.get_all_summaries()`

---

### 2. `get_config(config_id)` → Optional[EmailConfig]

**Called by**: Router endpoint `GET /email-configs/{id}`

**Purpose**: Get email configuration by ID

**Implementation**:
```python
def get_config(self, config_id: int) -> Optional[EmailConfig]:
    """
    Get email configuration by ID.

    Args:
        config_id: Configuration ID

    Returns:
        EmailConfig dataclass or None if not found
    """
    return self.config_repository.get_by_id(config_id)
```

**Repository calls**: `config_repository.get_by_id()`

**Note**: Router enriches response with `is_running` status by calling `EmailIngestionService.is_listener_active()` directly (see API Integration section)

---

### 3. `create_config(config_data)` → EmailConfig

**Called by**: Router endpoint `POST /email-configs`

**Purpose**: Create new email configuration

**Implementation**:
```python
def create_config(self, config_data: EmailConfigCreate) -> EmailConfig:
    """
    Create new email configuration.

    Config starts as inactive (is_active=False).
    No connection validation on creation - user must activate to start monitoring.

    Args:
        config_data: EmailConfigCreate dataclass with configuration data

    Returns:
        Created EmailConfig dataclass
    """
    return self.config_repository.create(config_data)
```

**Repository calls**: `config_repository.create()`

---

### 4. `update_config(config_id, config_update)` → EmailConfig

**Called by**: Router endpoint `PUT /email-configs/{id}`

**Purpose**: Update email configuration

**Implementation**:
```python
def update_config(
    self,
    config_id: int,
    config_update: EmailConfigUpdate
) -> EmailConfig:
    """
    Update email configuration.

    Validation:
    - Config must exist (raises ObjectNotFoundError)
    - Config must be inactive (raises ConflictError if active)

    Args:
        config_id: Configuration ID
        config_update: EmailConfigUpdate dataclass with fields to update

    Returns:
        Updated EmailConfig dataclass

    Raises:
        ObjectNotFoundError: If config not found
        ConflictError: If config is active (cannot update active config)
    """
    # Get config to validate
    config = self.config_repository.get_by_id(config_id)
    if not config:
        raise ObjectNotFoundError(f"Configuration {config_id} not found")

    # Business validation - cannot update active config (state conflict)
    if config.is_active:
        raise ConflictError(
            "Cannot update active configuration. Deactivate first."
        )

    # Perform update
    return self.config_repository.update(config_id, config_update)
```

**Repository calls**: `config_repository.get_by_id()`, `config_repository.update()`

---

### 5. `delete_config(config_id)` → EmailConfig

**Called by**: Router endpoint `DELETE /email-configs/{id}`

**Purpose**: Delete email configuration

**Implementation**:
```python
def delete_config(self, config_id: int) -> EmailConfig:
    """
    Delete email configuration.

    Validation:
    - Config must exist (raises ObjectNotFoundError)
    - Config must be inactive (raises ConflictError if active)

    If config is active, automatically deactivates it first.

    Args:
        config_id: Configuration ID

    Returns:
        EmailConfig dataclass of the deleted configuration

    Raises:
        ObjectNotFoundError: If config not found
        ServiceError: If failed to stop monitoring
    """
    # Get config to validate
    config = self.config_repository.get_by_id(config_id)
    if not config:
        raise ObjectNotFoundError(f"Configuration {config_id} not found")

    # Store config before deletion (for return value)
    config_to_delete = config

    # If active, deactivate first
    if config.is_active:
        try:
            # Stop listener
            self.ingestion_service.stop_monitoring(config_id)
        except Exception as e:
            logger.error(f"Failed to stop monitoring for config {config_id}: {e}", exc_info=True)
            raise ServiceError(f"Failed to stop email monitoring: {str(e)}") from e

        # Update DB to mark inactive
        self.config_repository.update(
            config_id,
            EmailConfigUpdate(is_active=False)
        )

    # Delete config
    self.config_repository.delete(config_id)

    logger.info(f"Deleted configuration {config_id}")
    return config_to_delete
```

**Repository calls**: `config_repository.get_by_id()`, `config_repository.update()`, `config_repository.delete()`

**Service calls**: `ingestion_service.stop_monitoring()`

---

### 6. `activate_config(config_id)` → EmailConfig

**Called by**: Router endpoint `POST /email-configs/{id}/activate`

**Purpose**: Activate email configuration (starts email monitoring)

**Implementation**:
```python
def activate_config(self, config_id: int) -> EmailConfig:
    """
    Activate email configuration (starts email monitoring).

    Process:
    1. Get config from repository
    2. Validate config exists and is inactive
    3. Delegate to EmailIngestionService to start listener
    4. Update config in DB (is_active=True, activated_at=now)
    5. Return updated config

    Args:
        config_id: Configuration ID

    Returns:
        Updated EmailConfig dataclass with is_active=True

    Raises:
        ObjectNotFoundError: If config not found
        ConflictError: If already active
        ServiceError: If activation fails (infrastructure failure)
    """
    try:
        # Get config
        config = self.config_repository.get_by_id(config_id)
        if not config:
            raise ObjectNotFoundError(f"Configuration {config_id} not found")

        # Validate not already active (state conflict)
        if config.is_active:
            raise ConflictError("Configuration is already active")

        # Start monitoring via ingestion service (infrastructure operation)
        listener_status = self.ingestion_service.start_monitoring(config)

        # Update DB status
        updated_config = self.config_repository.update(
            config_id,
            EmailConfigUpdate(
                is_active=True,
                activated_at=datetime.now(timezone.utc)
            )
        )

        logger.info(f"Activated configuration {config_id}")
        return updated_config

    except ObjectNotFoundError:
        # Preserve 404 errors
        raise

    except ConflictError:
        # Preserve 409 errors
        raise

    except Exception as e:
        # Wrap infrastructure failures as 500
        logger.error(f"Failed to activate config {config_id}: {e}", exc_info=True)
        raise ServiceError(f"Failed to start email monitoring: {str(e)}") from e
```

**Repository calls**: `config_repository.get_by_id()`, `config_repository.update()`

**Service calls**: `ingestion_service.start_monitoring()`

---

### 7. `deactivate_config(config_id)` → EmailConfig

**Called by**: Router endpoint `POST /email-configs/{id}/deactivate`

**Purpose**: Deactivate email configuration (stops email monitoring)

**Implementation**:
```python
def deactivate_config(self, config_id: int) -> EmailConfig:
    """
    Deactivate email configuration (stops email monitoring).

    Process:
    1. Get config from repository
    2. Validate config exists and is active
    3. Delegate to EmailIngestionService to stop listener
    4. Update config in DB (is_active=False)
    5. Return updated config

    Args:
        config_id: Configuration ID

    Returns:
        Updated EmailConfig dataclass with is_active=False

    Raises:
        ObjectNotFoundError: If config not found
        ConflictError: If not active
        ServiceError: If deactivation fails (infrastructure failure)
    """
    try:
        # Get config
        config = self.config_repository.get_by_id(config_id)
        if not config:
            raise ObjectNotFoundError(f"Configuration {config_id} not found")

        # Validate is active (state conflict if not)
        if not config.is_active:
            raise ConflictError("Configuration is not active")

        # Stop monitoring via ingestion service (infrastructure operation)
        self.ingestion_service.stop_monitoring(config_id)

        # Update DB status
        updated_config = self.config_repository.update(
            config_id,
            EmailConfigUpdate(is_active=False)
        )

        logger.info(f"Deactivated configuration {config_id}")
        return updated_config

    except ObjectNotFoundError:
        # Preserve 404 errors
        raise

    except ConflictError:
        # Preserve 409 errors
        raise

    except Exception as e:
        # Wrap infrastructure failures as 500
        logger.error(f"Failed to deactivate config {config_id}: {e}", exc_info=True)
        raise ServiceError(f"Failed to stop email monitoring: {str(e)}") from e
```

**Repository calls**: `config_repository.get_by_id()`, `config_repository.update()`

**Service calls**: `ingestion_service.stop_monitoring()`

---

**Internal Methods**:

None - All logic is in public methods or delegated to repositories/ingestion service

---

**Dataclasses Used**:

**Input types** (from `shared/types/`):
- `EmailConfigCreate` - Data for creating new config
- `EmailConfigUpdate` - Data for updating existing config (partial)

**Output types** (from `shared/types/`):
- `EmailConfig` - Full configuration data
- `EmailConfigSummary` - Summary view for list endpoint

---

**API Integration**:

**Router depends on this service for these endpoints:**
- `GET /email-configs` → `list_configs_summary()`
- `GET /email-configs/{id}` → `get_config()` (also injects `EmailIngestionService` for `is_listener_active()`)
- `POST /email-configs` → `create_config()`
- `PUT /email-configs/{id}` → `update_config()`
- `DELETE /email-configs/{id}` → `delete_config()`
- `POST /email-configs/{id}/activate` → `activate_config()`
- `POST /email-configs/{id}/deactivate` → `deactivate_config()`

**Router does NOT call this service for:**
- `GET /email-configs/discovery/accounts` → Calls `EmailIngestionService` directly
- `GET /email-configs/discovery/folders` → Calls `EmailIngestionService` directly
- `POST /email-configs/validate` → Calls `EmailIngestionService` directly

**Router dependency injection:**
```python
# Most endpoints inject EmailConfigService only
@router.post("")
def create_email_config(
    request: CreateEmailConfigRequest,
    config_service: EmailConfigService = Depends(
        lambda: ServiceContainer.get_email_config_service()
    )
):
    # Calls config_service methods

# GET /{id} injects BOTH services for is_running enrichment
@router.get("/{id}", response_model=EmailConfigDetail)
def get_email_config(
    id: int,
    config_service: EmailConfigService = Depends(
        lambda: ServiceContainer.get_email_config_service()
    ),
    ingestion_service: EmailIngestionService = Depends(
        lambda: ServiceContainer.get_email_ingestion_service()
    )
) -> EmailConfigDetail:
    """Get email configuration details with is_running status"""

    # Get config data
    config = config_service.get_config(id)
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")

    # Get running status directly from ingestion service
    is_running = ingestion_service.is_listener_active(id)

    return EmailConfigDetail(
        **config.model_dump(),
        is_running=is_running
    )

# Discovery endpoints inject EmailIngestionService only
@router.get("/discovery/accounts")
def discover_email_accounts(
    ingestion_service: EmailIngestionService = Depends(
        lambda: ServiceContainer.get_email_ingestion_service()
    )
):
    # Calls ingestion_service methods directly
```

---

## Service 2: Email Ingestion Service

**Location**: `server-new/src/features/email_ingestion/service.py`

**Purpose**: Internal service that manages email monitoring, listener threads, and email processing. Handles email provider integrations via the IntegrationRegistry, account/folder discovery, connection testing, and the email-to-PDF-to-ETO processing pipeline. Manages the lifecycle of active listener threads and background email polling.

**Dependencies**:
- `DatabaseConnectionManager` - For database access
- `PdfFilesService` - For storing PDF attachments
- `EtoProcessingService` - For triggering ETO processing
- `EmailConfigRepository` - For email config queries during processing
- `EmailRepository` - For storing processed emails

**Responsibilities**:
- Email provider integration via IntegrationRegistry (temporary connections)
- Account discovery and folder discovery (wizard steps 1 & 2)
- Connection testing and validation (wizard step 4)
- Listener thread lifecycle management (create, start, stop)
- Email monitoring and polling
- Email processing pipeline (email → PDF → ETO)
- Active listener state management (thread-safe)
- Startup recovery (reactivate configs that were active before shutdown)

**Constructor**:
```python
def __init__(
    self,
    connection_manager: DatabaseConnectionManager,
    pdf_service: PdfFilesService,
    eto_service: EtoProcessingService
):
    self.connection_manager = connection_manager
    self.pdf_service = pdf_service
    self.eto_service = eto_service

    self.config_repository = EmailConfigRepository(connection_manager=connection_manager)
    self.email_repository = EmailRepository(connection_manager=connection_manager)

    # Active listener state (thread-safe)
    self.active_integrations: dict[int, BaseEmailIntegration] = {}
    self.active_listeners: dict[int, EmailListenerThread] = {}
    self.lock = threading.RLock()
```

**Public Methods**:

### 1. `discover_email_accounts(provider_type)` → list[EmailAccount]

**Called by**: Router endpoint `GET /email-configs/discovery/accounts` (DIRECTLY - not via EmailConfigService)

**Purpose**: Discover available email accounts for provider (wizard step 1)

**Status**: ✅ Already implemented

**Implementation**:
```python
def discover_email_accounts(
    self,
    provider_type: str = "outlook_com"
) -> list[EmailAccount]:
    """
    Discover available email accounts for the specified provider.

    Creates temporary integration, queries provider, returns accounts.
    No persistent connection or database state.

    Args:
        provider_type: Email provider (default: "outlook_com")

    Returns:
        List of EmailAccount dataclasses

    Raises:
        ValidationError: If provider not supported
        ServiceError: If discovery fails
    """
    try:
        # Validate provider
        if not IntegrationRegistry.is_supported(provider_type):
            available = IntegrationRegistry.get_available_providers()
            raise ValidationError(
                f"Provider '{provider_type}' is not supported. "
                f"Available providers: {', '.join(available)}"
            )

        # Create temporary integration
        integration = IntegrationRegistry.create(
            provider_type=provider_type,
            email_address=None,
            folder_name=None
        )

        # Discover accounts (no connection needed for Outlook COM)
        accounts = integration.discover_accounts()

        logger.info(f"Discovered {len(accounts)} email account(s) for provider '{provider_type}'")
        return accounts

    except ValidationError:
        # Preserve validation errors unchanged
        raise

    except Exception as e:
        logger.error(f"Error discovering email accounts for provider '{provider_type}': {e}", exc_info=True)
        raise ServiceError(f"Failed to discover email accounts: {str(e)}") from e
```

**Integration calls**: `IntegrationRegistry.create()`, `integration.discover_accounts()`

---

### 2. `discover_folders(email_address, provider_type)` → list[EmailFolder]

**Called by**: Router endpoint `GET /email-configs/discovery/folders` (DIRECTLY - not via EmailConfigService)

**Purpose**: Discover available folders for email account (wizard step 2)

**Status**: ✅ Already implemented

**Implementation**:
```python
def discover_folders(
    self,
    email_address: str,
    provider_type: str = "outlook_com"
) -> list[EmailFolder]:
    """
    Discover available folders for a specific email account.

    Creates temporary integration, connects, discovers folders, disconnects.
    No persistent connection or database state.

    Args:
        email_address: Email address to discover folders for
        provider_type: Email provider (default: "outlook_com")

    Returns:
        List of EmailFolder dataclasses

    Raises:
        ValidationError: If email_address missing or provider not supported
        ServiceError: If connection or discovery fails
    """
    try:
        # Validate inputs
        if not email_address:
            raise ValidationError("email_address is required")

        if not IntegrationRegistry.is_supported(provider_type):
            available = IntegrationRegistry.get_available_providers()
            raise ValidationError(
                f"Provider '{provider_type}' is not supported. "
                f"Available providers: {', '.join(available)}"
            )

        # Create temporary integration
        integration = IntegrationRegistry.create(
            provider_type=provider_type,
            email_address=email_address,
            folder_name="Inbox"
        )

        # Connect to provider (infrastructure operation)
        if not integration.connect(email_address):
            raise ServiceError(
                f"Failed to connect to email account '{email_address}'. "
                f"Please verify the account exists and is accessible."
            )

        try:
            # Discover folders while connected
            folders = integration.discover_folders(email_address)

            logger.info(f"Discovered {len(folders)} folder(s) for '{email_address}'")
            return folders
        finally:
            # Always disconnect, even on error
            try:
                integration.disconnect()
            except Exception as disconnect_error:
                logger.warning(f"Error disconnecting from {email_address}: {disconnect_error}")

    except ValidationError:
        # Preserve validation errors unchanged
        raise

    except ServiceError:
        # Preserve service errors unchanged
        raise

    except Exception as e:
        logger.error(f"Error discovering folders for '{email_address}': {e}", exc_info=True)
        raise ServiceError(f"Failed to discover folders: {str(e)}") from e
```

**Integration calls**: `IntegrationRegistry.create()`, `integration.connect()`, `integration.discover_folders()`, `integration.disconnect()`

---

### 3. `test_connection(email_address, folder_name, provider_type)` → ConnectionTestResult

**Called by**: Router endpoint `POST /email-configs/validate` (DIRECTLY - not via EmailConfigService)

**Purpose**: Test connection to email account and folder (wizard step 4 validation)

**Status**: ⚠️ Needs implementation

**Implementation**:
```python
def test_connection(
    self,
    email_address: str,
    folder_name: str,
    provider_type: str = "outlook_com"
) -> ConnectionTestResult:
    """
    Test connection to email account and folder.

    Creates temporary integration, tests connection, tests folder access.
    Returns result with success/error information.

    Args:
        email_address: Email address to test
        folder_name: Folder name to test access
        provider_type: Email provider (default: "outlook_com")

    Returns:
        ConnectionTestResult dataclass with:
        - success: bool
        - error_message: Optional[str]
        - tested_at: datetime

    Raises:
        ValueError: If inputs invalid
    """
    try:
        # Validate inputs
        if not email_address:
            raise ValueError("email_address is required")
        if not folder_name:
            raise ValueError("folder_name is required")

        # Create temporary integration
        integration = IntegrationRegistry.create(
            provider_type=provider_type,
            email_address=email_address,
            folder_name=folder_name
        )

        # Test connection
        if not integration.connect(email_address):
            return ConnectionTestResult(
                success=False,
                error_message=f"Cannot connect to email account '{email_address}'",
                tested_at=datetime.now(timezone.utc)
            )

        try:
            # Test folder access
            folder_accessible = integration.test_folder_access(folder_name)

            if not folder_accessible:
                return ConnectionTestResult(
                    success=False,
                    error_message=f"Folder '{folder_name}' does not exist or is not accessible",
                    tested_at=datetime.now(timezone.utc)
                )

            # Success
            return ConnectionTestResult(
                success=True,
                error_message=None,
                tested_at=datetime.now(timezone.utc)
            )

        finally:
            integration.disconnect()

    except Exception as e:
        logger.error(f"Error testing connection: {e}", exc_info=True)
        return ConnectionTestResult(
            success=False,
            error_message=f"Connection test failed: {str(e)}",
            tested_at=datetime.now(timezone.utc)
        )
```

**Integration calls**: `IntegrationRegistry.create()`, `integration.connect()`, `integration.test_folder_access()`, `integration.disconnect()`

---

### 4. `start_monitoring(config)` → ListenerStatus

**Called by**: EmailConfigService.activate_config() (NOT by router)

**Purpose**: Start email monitoring for a configuration (creates listener thread)

**Status**: ⚠️ Needs implementation

**Implementation**:
```python
def start_monitoring(self, config: EmailConfig) -> ListenerStatus:
    """
    Start email monitoring for a configuration.

    Creates integration, connects, creates and starts listener thread.
    Thread-safe operation.

    Args:
        config: EmailConfig dataclass with configuration to monitor

    Returns:
        ListenerStatus dataclass with thread information

    Raises:
        ServiceError: If startup fails (connection, thread creation)
    """
    with self.lock:
        # Check if already running
        if config.id in self.active_listeners:
            raise ServiceError(f"Configuration {config.id} is already being monitored")

        try:
            # Create persistent integration
            integration = IntegrationRegistry.create(
                provider_type=config.provider_type,
                email_address=config.email_address,
                folder_name=config.folder_name
            )

            # Connect to provider
            if not integration.connect(config.email_address):
                raise ServiceError(
                    f"Failed to connect to email account '{config.email_address}'"
                )

            # Create listener thread
            listener = EmailListenerThread(
                config_id=config.id,
                integration=integration,
                filter_rules=config.filter_rules,
                poll_interval=config.poll_interval_seconds,
                process_callback=partial(self._process_email, config.id),
                error_callback=partial(self._handle_listener_error, config.id)
            )

            # Start thread
            listener.start()

            # Track active listener
            self.active_integrations[config.id] = integration
            self.active_listeners[config.id] = listener

            logger.info(f"Started monitoring for config {config.id}")

            # Return status
            return ListenerStatus(
                config_id=config.id,
                email_address=config.email_address,
                folder_name=config.folder_name,
                is_active=True,
                is_running=True,
                start_time=datetime.now(timezone.utc),
                last_check_time=None,
                error_count=0,
                emails_processed=0,
                pdfs_found=0
            )

        except Exception as e:
            logger.error(f"Failed to start monitoring for config {config.id}: {e}")
            raise ServiceError(f"Failed to start monitoring: {str(e)}")
```

**Integration calls**: `IntegrationRegistry.create()`, `integration.connect()`

**Creates**: EmailListenerThread instance (background thread)

---

### 5. `stop_monitoring(config_id)` → bool

**Called by**: EmailConfigService.deactivate_config(), EmailConfigService.delete_config() (NOT by router)

**Purpose**: Stop email monitoring for a configuration (stops listener thread)

**Status**: ⚠️ Needs implementation

**Implementation**:
```python
def stop_monitoring(self, config_id: int) -> bool:
    """
    Stop email monitoring for a configuration.

    Stops listener thread, disconnects integration, cleans up resources.
    Thread-safe operation.

    Args:
        config_id: Configuration ID to stop monitoring

    Returns:
        True if stopped successfully, False if not running

    Raises:
        ServiceError: If shutdown fails (thread won't stop)
    """
    with self.lock:
        # Check if running
        if config_id not in self.active_listeners:
            logger.warning(f"Config {config_id} is not being monitored")
            return False

        try:
            # Stop listener thread
            listener = self.active_listeners[config_id]
            listener.stop()
            listener.join(timeout=5.0)  # Wait up to 5 seconds

            if listener.is_alive():
                logger.error(f"Listener thread for config {config_id} did not stop")
                raise ServiceError("Listener thread did not stop gracefully")

            # Disconnect integration
            integration = self.active_integrations[config_id]
            integration.disconnect()

            # Remove from active tracking
            del self.active_listeners[config_id]
            del self.active_integrations[config_id]

            logger.info(f"Stopped monitoring for config {config_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to stop monitoring for config {config_id}: {e}")
            raise ServiceError(f"Failed to stop monitoring: {str(e)}")
```

**Calls**: `listener.stop()`, `listener.join()`, `integration.disconnect()`

---

### 6. `is_listener_active(config_id)` → bool

**Called by**: Router endpoint `GET /email-configs/{id}` (directly for is_running enrichment)

**Purpose**: Check if listener thread is running for a configuration

**Status**: ⚠️ Needs implementation

**Implementation**:
```python
def is_listener_active(self, config_id: int) -> bool:
    """
    Check if listener thread is running for a configuration.

    Thread-safe operation.

    Args:
        config_id: Configuration ID to check

    Returns:
        True if listener is active and running, False otherwise
    """
    with self.lock:
        if config_id not in self.active_listeners:
            return False

        listener = self.active_listeners[config_id]
        return listener.is_alive()
```

---

**Internal Methods**:

### `_process_email(config_id, email_msg, attachments)` → None

**Called by**: EmailListenerThread (background thread callback)

**Purpose**: Process single email from listener (store email, extract PDFs, trigger ETO)

**Status**: ⚠️ Needs implementation

**Implementation**:
```python
def _process_email(
    self,
    config_id: int,
    email_msg: EmailMessage,
    attachments: list[EmailAttachment]
) -> None:
    """
    Process single email from listener thread.

    Pipeline:
    1. Check for duplicates (by message_id)
    2. Store email record in database
    3. For each PDF attachment:
       - Store PDF via pdf_service
       - Trigger ETO processing via eto_service
    4. Update config statistics

    Args:
        config_id: Configuration ID that received this email
        email_msg: EmailMessage dataclass
        attachments: List of EmailAttachment dataclasses

    Note: Called from background thread - must be thread-safe
    """
    try:
        # Check for duplicate
        existing = self.email_repository.get_by_message_id(email_msg.message_id)
        if existing:
            logger.debug(f"Email {email_msg.message_id} already processed")
            return

        # Store email record
        email_create = EmailCreate(
            config_id=config_id,
            message_id=email_msg.message_id,
            sender_email=email_msg.sender_email,
            subject=email_msg.subject,
            received_date=email_msg.received_date,
            folder_name=email_msg.folder_name
        )
        email_record = self.email_repository.create(email_create)

        # Process PDF attachments
        pdf_count = 0
        for attachment in attachments:
            if attachment.is_pdf:
                # Store PDF
                pdf_record = self.pdf_service.store_pdf(
                    file_bytes=attachment.content,
                    filename=attachment.filename,
                    email_id=email_record.id
                )

                # Trigger ETO processing
                self.eto_service.process_pdf(pdf_record.id)

                pdf_count += 1

        logger.info(
            f"Processed email {email_msg.message_id} "
            f"(config {config_id}): {pdf_count} PDFs"
        )

    except Exception as e:
        logger.error(f"Error processing email: {e}", exc_info=True)
        self._handle_listener_error(config_id, e)
```

---

### `_handle_listener_error(config_id, error)` → None

**Called by**: EmailListenerThread (background thread callback on errors)

**Purpose**: Handle errors from listener threads

**Status**: ⚠️ Needs implementation

**Implementation**:
```python
def _handle_listener_error(self, config_id: int, error: Exception) -> None:
    """
    Handle errors from listener threads.

    Logs error, updates config error tracking, potentially stops listener if too many errors.

    Args:
        config_id: Configuration ID that encountered error
        error: Exception that occurred

    Note: Called from background thread - must be thread-safe
    """
    logger.error(
        f"Listener error for config {config_id}: {error}",
        exc_info=True
    )

    try:
        # Update config error tracking
        # (Could implement retry logic, error counting, auto-deactivation, etc.)
        pass

    except Exception as e:
        logger.error(f"Error handling listener error: {e}")
```

---

**Dataclasses Used**:

**Input types** (from `shared/types/email_integrations.py`):
- `EmailMessage` - Email from integration (transient)
- `EmailAttachment` - Attachment from integration (transient)

**Output types** (from `shared/types/email_integrations.py`):
- `EmailAccount` - Discovered account info (transient)
- `EmailFolder` - Discovered folder info (transient)
- `ConnectionTestResult` - Connection test result (transient)

**Internal types** (defined in service.py):
- `ListenerStatus` - Status of active listener (dataclass, lines 52-64)

**Database types** (from `shared/types/`):
- `EmailConfig` - Full config (used for start_monitoring)
- `EmailCreate` - For creating email records
- `Email` - Email record

---

**API Integration**:

**Router calls this service DIRECTLY for these endpoints:**
- `GET /email-configs/discovery/accounts` → `discover_email_accounts()`
- `GET /email-configs/discovery/folders` → `discover_folders()`
- `POST /email-configs/validate` → `test_connection()`

**EmailConfigService calls this service for:**
- `activate_config()` → `start_monitoring()`
- `deactivate_config()` → `stop_monitoring()`
- `delete_config()` → `stop_monitoring()` (if active)

**Router calls this service directly for:**
- `GET /email-configs/{id}` → `is_listener_active()` (for is_running enrichment)

**Router dependency injection example:**
```python
# Router injects this service directly for discovery/validation endpoints
@router.get("/discovery/accounts")
def discover_email_accounts(
    ingestion_service: EmailIngestionService = Depends(
        lambda: ServiceContainer.get_email_ingestion_service()
    )
) -> DiscoverEmailAccountsResponse:
    accounts = ingestion_service.discover_email_accounts()
    # Map dataclass → Pydantic
    return DiscoverEmailAccountsResponse(...)
```

---

## Service 3: PDF Files Service

**Location**: `server-new/src/features/pdf_files/service.py`

**Purpose**: Manages PDF file storage, object extraction, and retrieval. Handles filesystem operations with date-based organization, SHA-256 hash-based deduplication, and automatic object extraction using pdfplumber. Provides querying capabilities for PDFs and their extracted objects. Orchestrates PDF lifecycle from storage through object extraction.

**Dependencies**:
- `DatabaseConnectionManager` - For database access and transaction management
- `PdfRepository` - For PDF metadata CRUD operations (objects stored as JSON in pdf_files table)
- `StorageConfig` - Configuration for filesystem storage paths (from config/settings)

**Responsibilities**:
- PDF file storage with SHA-256 hash-based deduplication
- Date-based filesystem organization (YYYY/MM/DD/hash.pdf)
- PDF metadata management (database records)
- Object extraction using pdfplumber (tables, text blocks, images)
- PDF retrieval (metadata and file bytes)
- Object querying and retrieval
- Temporary object extraction (from bytes without persistent storage)
- Storage path resolution and validation

**Constructor**:
```python
def __init__(
    self,
    connection_manager: DatabaseConnectionManager,
    storage_config: StorageConfig
):
    self.connection_manager = connection_manager
    self.storage_config = storage_config

    self.pdf_repository = PdfRepository(connection_manager=connection_manager)
    # No pdf_object_repository - objects stored as JSON in pdf_files table

    # Storage settings
    self.base_storage_path = Path(storage_config.pdf_storage_path)
    self.base_storage_path.mkdir(parents=True, exist_ok=True)
```

**Public Methods**:

### 1. `get_pdf_metadata(pdf_id)` → Optional[PdfMetadata]

**Called by**: Router endpoint `GET /pdf-files/{id}`

**Purpose**: Get PDF metadata by ID

**Implementation**:
```python
def get_pdf_metadata(self, pdf_id: int) -> Optional[PdfMetadata]:
    """
    Get PDF metadata by ID.

    Returns complete metadata including file information, hash,
    storage path, and timestamps.

    Args:
        pdf_id: PDF record ID

    Returns:
        PdfMetadata dataclass or None if not found
    """
    return self.pdf_repository.get_by_id(pdf_id)
```

**Repository calls**: `pdf_repository.get_by_id()`

---

### 2. `get_pdf_file_bytes(pdf_id)` → tuple[bytes, str]

**Called by**: Router endpoint `GET /pdf-files/{id}/download`

**Purpose**: Get PDF file bytes for streaming/download

**Implementation**:
```python
def get_pdf_file_bytes(self, pdf_id: int) -> tuple[bytes, str]:
    """
    Get PDF file bytes for streaming/download.

    Process:
    1. Get metadata from database
    2. Resolve filesystem path
    3. Read file bytes
    4. Return bytes + filename for Content-Disposition header

    Args:
        pdf_id: PDF record ID

    Returns:
        Tuple of (file_bytes, original_filename)

    Raises:
        ObjectNotFoundError: If PDF record not found
        FileNotFoundError: If file missing from filesystem
        ServiceError: If file read fails
    """
    # Get metadata
    metadata = self.pdf_repository.get_by_id(pdf_id)
    if not metadata:
        raise ObjectNotFoundError(f"PDF {pdf_id} not found")

    # Resolve file path
    file_path = self.base_storage_path / metadata.file_path

    # Validate file exists
    if not file_path.exists():
        logger.error(f"PDF file missing: {file_path}")
        raise FileNotFoundError(
            f"PDF file not found on filesystem (database record exists but file is missing)"
        )

    # Read file
    try:
        with open(file_path, 'rb') as f:
            file_bytes = f.read()

        return file_bytes, metadata.original_filename

    except Exception as e:
        logger.error(f"Error reading PDF file {file_path}: {e}")
        raise ServiceError(f"Failed to read PDF file: {str(e)}")
```

**Repository calls**: `pdf_repository.get_by_id()`

**Filesystem operations**: Read file bytes

---

### 3. `get_pdf_objects(pdf_id, object_type)` → dict

**Called by**: Router endpoint `GET /pdf-files/{id}/objects`

**Purpose**: Get all extracted objects for a PDF

**Implementation**:
```python
def get_pdf_objects(
    self,
    pdf_id: int,
    object_type: Optional[str] = None
) -> dict:
    """
    Get all extracted objects for a PDF.

    Objects are returned as grouped dict (same format as storage and API response).

    Args:
        pdf_id: PDF record ID
        object_type: Optional filter by type key (e.g., "text_words", "tables")

    Returns:
        Dict with grouped objects:
        {
            "text_words": [...],
            "text_lines": [...],
            "graphic_rects": [...],
            "graphic_lines": [...],
            "graphic_curves": [...],
            "images": [...],
            "tables": [...]
        }
        Or subset if object_type specified.

    Raises:
        ObjectNotFoundError: If PDF not found
    """
    # Get PDF metadata (contains extracted_objects JSON)
    metadata = self.pdf_repository.get_by_id(pdf_id)
    if not metadata:
        raise ObjectNotFoundError(f"PDF {pdf_id} not found")

    # Return extracted_objects dict directly
    objects = metadata.extracted_objects

    # Optional filtering - return subset of dict
    if object_type:
        return {object_type: objects.get(object_type, [])}

    return objects
```

**Repository calls**: `pdf_repository.get_by_id()`

---

### 4. `extract_objects_from_bytes(pdf_bytes, filename)` → dict

**Called by**: Router endpoint `POST /pdf-files/process-objects`

**Purpose**: Extract objects from PDF bytes (temporary extraction, no persistent storage)

**Implementation**:
```python
def extract_objects_from_bytes(
    self,
    pdf_bytes: bytes,
    filename: str
) -> dict:
    """
    Extract objects from PDF bytes without storing the PDF.

    This is for temporary/preview extraction. Objects are returned
    but not stored in database. PDF file is not saved to filesystem.

    Process:
    1. Write bytes to temporary file
    2. Extract objects using pdfplumber (returns grouped dict)
    3. Delete temporary file
    4. Return extracted objects dict (not persisted)

    Args:
        pdf_bytes: Raw PDF file bytes
        filename: Original filename (for logging/error messages)

    Returns:
        Dict with grouped objects (same format as storage/API response)

    Raises:
        ServiceError: If extraction fails
    """
    import tempfile

    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_path = Path(tmp_file.name)
            tmp_file.write(pdf_bytes)

        try:
            # Extract objects from temporary file (returns dict)
            extracted_objects = self._extract_objects_from_file(
                tmp_path,
                filename
            )

            return extracted_objects

        finally:
            # Always delete temporary file
            if tmp_path.exists():
                tmp_path.unlink()

    except Exception as e:
        logger.error(f"Error extracting objects from {filename}: {e}")
        raise ServiceError(f"Failed to extract PDF objects: {str(e)}")
```

**Internal calls**: `_extract_objects_from_file()`

**Filesystem operations**: Temporary file creation/deletion

---

### 5. `store_pdf(file_bytes, filename, email_id)` → PdfMetadata

**Called by**: EmailIngestionService._process_email() (NOT by router - internal service call)

**Purpose**: Store PDF file and extract objects (full persistent storage)

**Implementation**:
```python
def store_pdf(
    self,
    file_bytes: bytes,
    filename: str,
    email_id: Optional[int] = None
) -> PdfMetadata:
    """
    Store PDF file with hash-based deduplication and extract objects.

    Process:
    1. Calculate SHA-256 hash
    2. Check if hash already exists (deduplication)
    3. If exists: return existing metadata
    4. If new:
       - Save file to date-based path (YYYY/MM/DD/hash.pdf)
       - Extract objects using pdfplumber (returns grouped dict)
       - Create database record with extracted_objects JSON
       - Return metadata

    Args:
        file_bytes: Raw PDF file bytes
        filename: Original filename
        email_id: Optional email_id (source tracking)

    Returns:
        PdfMetadata dataclass with complete metadata

    Raises:
        ServiceError: If storage or extraction fails
    """
    try:
        # Calculate hash
        file_hash = hashlib.sha256(file_bytes).hexdigest()

        # Check for existing PDF with same hash
        existing = self.pdf_repository.get_by_hash(file_hash)
        if existing:
            logger.info(f"PDF {filename} already exists (hash: {file_hash[:8]}...)")
            return existing

        # Generate storage path: YYYY/MM/DD/hash.pdf
        now = datetime.now(timezone.utc)
        relative_path = Path(
            str(now.year),
            f"{now.month:02d}",
            f"{now.day:02d}",
            f"{file_hash}.pdf"
        )
        full_path = self.base_storage_path / relative_path

        # Create directory structure
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file to filesystem
        with open(full_path, 'wb') as f:
            f.write(file_bytes)

        logger.info(f"Stored PDF at {relative_path}")

        # Extract objects (returns grouped dict)
        extracted_objects_dict = self._extract_objects_from_file(
            full_path,
            filename
        )

        # Count total objects for logging
        total_objects = sum(len(objects) for objects in extracted_objects_dict.values())

        # Create database record with extracted_objects JSON
        pdf_create = PdfCreate(
            original_filename=filename,
            file_hash=file_hash,
            file_size_bytes=len(file_bytes),
            file_path=str(relative_path),
            email_id=email_id,
            stored_at=now,
            extracted_objects=extracted_objects_dict  # JSON dict
        )

        # Single repository call - no UoW needed
        pdf_metadata = self.pdf_repository.create(pdf_create)

        logger.info(
            f"Extracted {total_objects} objects from {filename} "
            f"(PDF ID: {pdf_metadata.id})"
        )

        return pdf_metadata

    except Exception as e:
        logger.error(f"Error storing PDF {filename}: {e}", exc_info=True)
        raise ServiceError(f"Failed to store PDF: {str(e)}")
```

**Repository calls**: `pdf_repository.get_by_hash()`, `pdf_repository.create()`

**Internal calls**: `_extract_objects_from_file()`

**Filesystem operations**: Write PDF file

**Transaction**: Single repository call (no UoW needed - single record creation)

---

**Internal Methods**:

### `_extract_objects_from_file(file_path, filename)` → dict

**Called by**: `store_pdf()`, `extract_objects_from_bytes()`

**Purpose**: Extract objects from PDF file using pdfplumber

**Implementation**:
```python
def _extract_objects_from_file(
    self,
    file_path: Path,
    filename: str
) -> dict:
    """
    Extract objects from PDF file using pdfplumber.

    Returns dict directly in grouped format (matches storage and API response).
    No conversions needed - extract directly to final structure.

    Extracts:
    - Text words (text, fontname, fontsize)
    - Text lines (bbox only)
    - Graphic rectangles (bbox, linewidth)
    - Graphic lines (bbox, linewidth)
    - Graphic curves (bbox, points, linewidth)
    - Images (metadata: format, colorspace, bits)
    - Tables (bbox, rows, cols)

    Args:
        file_path: Path to PDF file on filesystem
        filename: Original filename (for logging)

    Returns:
        Dict with grouped objects:
        {
            "text_words": [{page, bbox, text, fontname, fontsize}, ...],
            "text_lines": [{page, bbox}, ...],
            "graphic_rects": [{page, bbox, linewidth}, ...],
            "graphic_lines": [{page, bbox, linewidth}, ...],
            "graphic_curves": [{page, bbox, points, linewidth}, ...],
            "images": [{page, bbox, format, colorspace, bits}, ...],
            "tables": [{page, bbox, rows, cols}, ...]
        }

    Raises:
        ServiceError: If extraction fails
    """
    import pdfplumber

    # Initialize grouped structure
    objects = {
        "text_words": [],
        "text_lines": [],
        "graphic_rects": [],
        "graphic_lines": [],
        "graphic_curves": [],
        "images": [],
        "tables": []
    }

    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_num = page.page_number - 1  # 0-indexed

                # Extract text words
                words = page.extract_words()
                for word in words:
                    objects["text_words"].append({
                        "page": page_num,
                        "bbox": [word['x0'], word['top'], word['x1'], word['bottom']],
                        "text": word['text'],
                        "fontname": word.get('fontname'),
                        "fontsize": word.get('size')
                    })

                # Extract lines
                lines = page.lines
                for line in lines:
                    objects["text_lines"].append({
                        "page": page_num,
                        "bbox": [line['x0'], line['top'], line['x1'], line['bottom']]
                    })

                # Extract rectangles
                rects = page.rects
                for rect in rects:
                    objects["graphic_rects"].append({
                        "page": page_num,
                        "bbox": [rect['x0'], rect['top'], rect['x1'], rect['bottom']],
                        "linewidth": rect.get('linewidth', 1.0)
                    })

                # Extract curves
                curves = page.curves
                for curve in curves:
                    objects["graphic_curves"].append({
                        "page": page_num,
                        "bbox": [curve['x0'], curve['top'], curve['x1'], curve['bottom']],
                        "points": curve.get('points', []),
                        "linewidth": curve.get('linewidth', 1.0)
                    })

                # Extract images
                images = page.images
                for img in images:
                    objects["images"].append({
                        "page": page_num,
                        "bbox": [img['x0'], img['top'], img['x1'], img['bottom']],
                        "format": img.get('name', '').split('.')[-1].upper(),
                        "colorspace": img.get('colorspace'),
                        "bits": img.get('bits')
                    })

                # Extract tables
                tables = page.find_tables()
                for table in tables:
                    table_data = table.extract()
                    objects["tables"].append({
                        "page": page_num,
                        "bbox": list(table.bbox),
                        "rows": len(table_data),
                        "cols": len(table_data[0]) if table_data else 0
                    })

        total_objects = sum(len(obj_list) for obj_list in objects.values())
        logger.debug(
            f"Extracted {total_objects} objects from {filename} "
            f"({len(pdf.pages)} pages)"
        )

        return objects

    except Exception as e:
        logger.error(f"Error extracting objects from {filename}: {e}")
        raise ServiceError(f"PDF extraction failed: {str(e)}")
```

**External dependencies**: pdfplumber library

---

**Dataclasses Used**:

**Input types** (from `shared/types/`):
- `PdfCreate` - Data for creating new PDF record (includes extracted_objects dict)

**Output types** (from `shared/types/`):
- `PdfMetadata` - Complete PDF metadata (includes file info, hash, path, timestamps, extracted_objects dict)

**Note**: PDF objects are stored as JSON in the `extracted_objects` field. No separate PdfObject or PdfObjectCreate types needed.

---

**API Integration**:

**Router depends on this service for these endpoints:**
- `GET /pdf-files/{id}` → `get_pdf_metadata()`
- `GET /pdf-files/{id}/download` → `get_pdf_file_bytes()`
- `GET /pdf-files/{id}/objects` → `get_pdf_objects()`
- `POST /pdf-files/process-objects` → `extract_objects_from_bytes()`

**Other services call this service:**
- EmailIngestionService._process_email() → `store_pdf()` (when processing email attachments)
- EtoProcessingService (future) → `get_pdf_objects()` (for extraction pipeline)

**Router dependency injection:**
```python
@router.get("/{id}")
def get_pdf_file(
    id: int,
    pdf_service: PdfFilesService = Depends(
        lambda: ServiceContainer.get_pdf_files_service()
    )
) -> PdfFileDetailResponse:
    metadata = pdf_service.get_pdf_metadata(id)
    # Map dataclass → Pydantic
    return PdfFileDetailResponse(...)

@router.get("/{id}/download")
def download_pdf_file(
    id: int,
    pdf_service: PdfFilesService = Depends(
        lambda: ServiceContainer.get_pdf_files_service()
    )
):
    file_bytes, filename = pdf_service.get_pdf_file_bytes(id)

    return Response(
        content=file_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )
```

---

## Service 4: ETO Processing Service

**Location**: `server-new/src/features/eto_processing/service.py`

**Purpose**: Orchestrates the Extract-Transform-Output (ETO) pipeline execution. Manages template matching, data extraction from PDFs, transformation via pipelines, and output generation. Coordinates ETO run lifecycle including status tracking, result storage, and error handling. Integrates with Template Management Service for matching and Pipeline Service for transformation execution.

**Dependencies**:
- `DatabaseConnectionManager` - For database access and transaction management
- `PdfFilesService` - For retrieving PDF objects for matching and extraction
- `TemplateManagementService` - For retrieving active templates for matching
- `PipelineService` - For executing transformation pipelines
- `EtoRunRepository` - For ETO run CRUD operations
- `EtoRunStageRepository` - For stage result tracking (template_matching, data_extraction, pipeline_execution)

**Responsibilities**:
- ETO run lifecycle management (create, list, get details, reprocess, skip, delete)
- ETO run status tracking (not_started, processing, success, failure, needs_template, skipped)
- Template matching orchestration (Stage 1)
- Data extraction orchestration (Stage 2)
- Pipeline execution orchestration (Stage 3)
- Stage result storage and error tracking
- Bulk operations with atomic validation (reprocess multiple, skip multiple, delete multiple)
- Background processing coordination (process_run called by worker)

**Constructor**:
```python
def __init__(
    self,
    connection_manager: DatabaseConnectionManager,
    pdf_service: PdfFilesService,
    template_service: TemplateManagementService,
    pipeline_service: PipelineService
):
    self.connection_manager = connection_manager
    self.pdf_service = pdf_service
    self.template_service = template_service
    self.pipeline_service = pipeline_service

    self.eto_run_repository = EtoRunRepository(connection_manager=connection_manager)
    self.stage_repository = EtoRunStageRepository(connection_manager=connection_manager)
```

**Public Methods**:

### 1. `list_runs(status, sort_by, sort_order, limit, offset)` → EtoRunListResult

**Called by**: Router endpoint `GET /eto-runs`

**Purpose**: List ETO runs with filtering, sorting, and pagination

**Implementation**:
```python
def list_runs(
    self,
    status: Optional[str] = None,
    sort_by: str = "started_at",
    sort_order: str = "desc",
    limit: int = 50,
    offset: int = 0
) -> EtoRunListResult:
    """
    List ETO runs with summary information.

    Args:
        status: Filter by status (not_started, processing, success, failure, needs_template, skipped)
        sort_by: Field to sort by (created_at, started_at, completed_at, status)
        sort_order: Sort order (asc, desc)
        limit: Max results (default 50, max 200)
        offset: Pagination offset

    Returns:
        EtoRunListResult dataclass with items, total, limit, offset
    """
    # Validate limit
    if limit > 200:
        limit = 200

    # Get paginated runs from repository
    runs, total = self.eto_run_repository.list_with_pagination(
        status_filter=status,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=limit,
        offset=offset
    )

    return EtoRunListResult(
        items=runs,
        total=total,
        limit=limit,
        offset=offset
    )
```

**Repository calls**: `eto_run_repository.list_with_pagination()`

---

### 2. `get_run_details(run_id)` → EtoRunDetail

**Called by**: Router endpoint `GET /eto-runs/{id}`

**Purpose**: Get full ETO run details including all stage results

**Implementation**:
```python
def get_run_details(self, run_id: int) -> EtoRunDetail:
    """
    Get full ETO run details including all processing stages.

    Retrieves:
    - Core run info (status, timestamps, error info)
    - PDF info (id, filename, page_count)
    - Source info (manual/email with metadata)
    - Template matching stage results
    - Data extraction stage results
    - Pipeline execution stage results (with steps)

    Args:
        run_id: ETO run ID

    Returns:
        EtoRunDetail dataclass with complete run information

    Raises:
        ObjectNotFoundError: If run not found
    """
    # Get run from repository
    run = self.eto_run_repository.get_by_id_with_stages(run_id)
    if not run:
        raise ObjectNotFoundError(f"ETO run {run_id} not found")

    return run
```

**Repository calls**: `eto_run_repository.get_by_id_with_stages()`

**Note**: Repository method `get_by_id_with_stages()` performs joins to load all stage data in single query for efficiency

---

### 3. `create_run_from_upload(pdf_id)` → EtoRunCreated

**Called by**: Router endpoint `POST /eto-runs/upload`

**Purpose**: Create new ETO run from manual PDF upload

**Implementation**:
```python
def create_run_from_upload(self, pdf_id: int) -> EtoRunCreated:
    """
    Create new ETO run from manually uploaded PDF.

    Process:
    1. Validate PDF exists
    2. Create ETO run record (status=not_started, source_type=manual)
    3. Return created run summary

    Args:
        pdf_id: PDF file ID

    Returns:
        EtoRunCreated dataclass with run ID and initial status

    Raises:
        ObjectNotFoundError: If PDF not found
    """
    # Validate PDF exists
    pdf = self.pdf_service.get_pdf_metadata(pdf_id)
    if not pdf:
        raise ObjectNotFoundError(f"PDF file {pdf_id} not found")

    # Create run record
    run_create = EtoRunCreate(
        pdf_id=pdf_id,
        source_type="manual",
        status="not_started",
        processing_step=None
    )

    run = self.eto_run_repository.create(run_create)

    logger.info(f"Created ETO run {run.id} from manual upload (PDF {pdf_id})")

    return EtoRunCreated(
        id=run.id,
        pdf_file_id=pdf_id,
        status="not_started",
        processing_step=None,
        started_at=None,
        completed_at=None
    )
```

**Service calls**: `pdf_service.get_pdf_metadata()`

**Repository calls**: `eto_run_repository.create()`

---

### 4. `reprocess_runs(run_ids)` → None

**Called by**: Router endpoint `POST /eto-runs/reprocess`

**Purpose**: Reprocess runs (bulk) - reset to not_started, clear stages

**Implementation**:
```python
def reprocess_runs(self, run_ids: list[int]) -> None:
    """
    Reprocess multiple runs (bulk operation).

    Validation (atomic - all or nothing):
    - All runs must exist
    - No run can have status=processing
    - No run can have status=success

    Process:
    1. Validate all runs
    2. Reset status to not_started
    3. Clear all stage records
    4. Clear processing_step, error fields, timestamps

    Args:
        run_ids: List of run IDs to reprocess

    Returns:
        None

    Raises:
        ObjectNotFoundError: If any run not found
        ServiceError: If validation fails (processing or successful runs)
    """
    with self.connection_manager.unit_of_work() as uow:
        # Validate all runs exist and can be reprocessed
        runs = uow.eto_runs.get_by_ids(run_ids)

        if len(runs) != len(run_ids):
            found_ids = {r.id for r in runs}
            missing_ids = set(run_ids) - found_ids
            raise ObjectNotFoundError(
                f"One or more runs not found: {sorted(missing_ids)}"
            )

        # Check for invalid statuses
        processing_runs = [r.id for r in runs if r.status == "processing"]
        if processing_runs:
            raise ServiceError(
                f"Cannot reprocess runs that are currently processing: {processing_runs}"
            )

        successful_runs = [r.id for r in runs if r.status == "success"]
        if successful_runs:
            raise ServiceError(
                f"Cannot reprocess successful runs: {successful_runs}"
            )

        # Reset each run
        for run_id in run_ids:
            # Clear stage records
            uow.stages.delete_by_run_id(run_id)

            # Reset run status
            uow.eto_runs.update(
                run_id,
                EtoRunUpdate(
                    status="not_started",
                    processing_step=None,
                    started_at=None,
                    completed_at=None,
                    error_type=None,
                    error_message=None
                )
            )

        logger.info(f"Reprocessed {len(run_ids)} run(s): {run_ids}")
```

**Repository calls**: `uow.eto_runs.get_by_ids()`, `uow.stages.delete_by_run_id()`, `uow.eto_runs.update()`

**Transaction**: Uses Unit of Work to ensure atomic validation and updates

---

### 5. `skip_runs(run_ids)` → None

**Called by**: Router endpoint `POST /eto-runs/skip`

**Purpose**: Skip runs (bulk) - set status to skipped

**Implementation**:
```python
def skip_runs(self, run_ids: list[int]) -> None:
    """
    Skip multiple runs (bulk operation).

    Validation (atomic - all or nothing):
    - All runs must exist
    - No run can have status=processing
    - No run can have status=success

    Process:
    1. Validate all runs
    2. Set status to skipped

    Args:
        run_ids: List of run IDs to skip

    Returns:
        None

    Raises:
        ObjectNotFoundError: If any run not found
        ServiceError: If validation fails
    """
    with self.connection_manager.unit_of_work() as uow:
        # Validate all runs
        runs = uow.eto_runs.get_by_ids(run_ids)

        if len(runs) != len(run_ids):
            found_ids = {r.id for r in runs}
            missing_ids = set(run_ids) - found_ids
            raise ObjectNotFoundError(
                f"One or more runs not found: {sorted(missing_ids)}"
            )

        # Check for invalid statuses
        processing_runs = [r.id for r in runs if r.status == "processing"]
        if processing_runs:
            raise ServiceError(
                f"Cannot skip runs that are currently processing: {processing_runs}"
            )

        successful_runs = [r.id for r in runs if r.status == "success"]
        if successful_runs:
            raise ServiceError(
                f"Cannot skip successful runs: {successful_runs}"
            )

        # Update all runs to skipped
        for run_id in run_ids:
            uow.eto_runs.update(
                run_id,
                EtoRunUpdate(status="skipped")
            )

        logger.info(f"Skipped {len(run_ids)} run(s): {run_ids}")
```

**Repository calls**: `uow.eto_runs.get_by_ids()`, `uow.eto_runs.update()`

**Transaction**: Uses Unit of Work for atomic operation

---

### 6. `delete_runs(run_ids)` → None

**Called by**: Router endpoint `DELETE /eto-runs`

**Purpose**: Delete runs (bulk) - permanently remove (only skipped runs)

**Implementation**:
```python
def delete_runs(self, run_ids: list[int]) -> None:
    """
    Delete multiple runs (bulk operation).

    Validation (atomic - all or nothing):
    - All runs must exist
    - All runs must have status=skipped

    Process:
    1. Validate all runs exist and are skipped
    2. Delete stage records
    3. Delete run records

    Args:
        run_ids: List of run IDs to delete

    Returns:
        None

    Raises:
        ObjectNotFoundError: If any run not found
        ServiceError: If any run is not skipped
    """
    with self.connection_manager.unit_of_work() as uow:
        # Validate all runs
        runs = uow.eto_runs.get_by_ids(run_ids)

        if len(runs) != len(run_ids):
            found_ids = {r.id for r in runs}
            missing_ids = set(run_ids) - found_ids
            raise ObjectNotFoundError(
                f"One or more runs not found: {sorted(missing_ids)}"
            )

        # Check all runs are skipped
        non_skipped = [r.id for r in runs if r.status != "skipped"]
        if non_skipped:
            raise ServiceError(
                f"Can only delete skipped runs. Invalid runs: {non_skipped}"
            )

        # Delete stage records and runs
        for run_id in run_ids:
            uow.stages.delete_by_run_id(run_id)
            uow.eto_runs.delete(run_id)

        logger.info(f"Deleted {len(run_ids)} run(s): {run_ids}")
```

**Repository calls**: `uow.eto_runs.get_by_ids()`, `uow.stages.delete_by_run_id()`, `uow.eto_runs.delete()`

**Transaction**: Uses Unit of Work for atomic deletion

---

### 7. `reprocess_run(run_id)` → None

**Called by**: Router endpoint `POST /eto-runs/{id}/reprocess`

**Purpose**: Reprocess single run (convenience endpoint)

**Implementation**:
```python
def reprocess_run(self, run_id: int) -> None:
    """
    Reprocess single run (convenience wrapper for bulk operation).

    Args:
        run_id: Run ID to reprocess

    Returns:
        None

    Raises:
        ObjectNotFoundError: If run not found
        ServiceError: If validation fails
    """
    # Delegate to bulk operation
    self.reprocess_runs([run_id])
```

**Service calls**: `reprocess_runs()`

---

### 8. `process_run(run_id)` → None

**Called by**: Background worker (NOT by router)

**Purpose**: Execute full ETO pipeline for a run (orchestration method)

**Implementation**:
```python
def process_run(self, run_id: int) -> None:
    """
    Execute full ETO pipeline for a run.

    Pipeline stages:
    1. Template Matching - Find matching template from active templates
    2. Data Extraction - Extract data using template's extraction fields
    3. Pipeline Execution - Transform extracted data via template's pipeline

    This method is called by a background worker, not directly by the API.

    Process:
    1. Update status to processing
    2. Execute Stage 1: Template Matching
    3. Execute Stage 2: Data Extraction
    4. Execute Stage 3: Pipeline Execution
    5. Update status to success/failure

    Args:
        run_id: ETO run ID to process

    Returns:
        None (updates run status in database)

    Note: Exceptions are caught and stored as errors in the run record
    """
    try:
        # Update status to processing
        self.eto_run_repository.update(
            run_id,
            EtoRunUpdate(
                status="processing",
                processing_step="template_matching",
                started_at=datetime.now(timezone.utc)
            )
        )

        logger.info(f"Starting ETO processing for run {run_id}")

        # Get run details
        run = self.eto_run_repository.get_by_id(run_id)
        if not run:
            raise ObjectNotFoundError(f"Run {run_id} not found")

        # Get PDF objects for matching and extraction
        pdf_objects = self.pdf_service.get_pdf_objects(run.pdf_id)

        # Stage 1: Template Matching
        matched_template = self._match_template(run_id, pdf_objects)

        if not matched_template:
            # No template found
            self.eto_run_repository.update(
                run_id,
                EtoRunUpdate(
                    status="needs_template",
                    processing_step=None,
                    completed_at=datetime.now(timezone.utc)
                )
            )
            logger.warning(f"No template matched for run {run_id}")
            return

        # Update processing step
        self.eto_run_repository.update(
            run_id,
            EtoRunUpdate(processing_step="data_extraction")
        )

        # Stage 2: Data Extraction
        extracted_data = self._extract_data(run_id, matched_template, pdf_objects)

        # Update processing step
        self.eto_run_repository.update(
            run_id,
            EtoRunUpdate(processing_step="data_transformation")
        )

        # Stage 3: Pipeline Execution
        self._execute_pipeline(run_id, matched_template, extracted_data)

        # Success
        self.eto_run_repository.update(
            run_id,
            EtoRunUpdate(
                status="success",
                processing_step=None,
                completed_at=datetime.now(timezone.utc)
            )
        )

        logger.info(f"Successfully completed ETO processing for run {run_id}")

    except Exception as e:
        # Failure - record error
        logger.error(f"Error processing run {run_id}: {e}", exc_info=True)

        self.eto_run_repository.update(
            run_id,
            EtoRunUpdate(
                status="failure",
                processing_step=None,
                completed_at=datetime.now(timezone.utc),
                error_type=type(e).__name__,
                error_message=str(e)
            )
        )
```

**Service calls**: `pdf_service.get_pdf_objects()`

**Internal calls**: `_match_template()`, `_extract_data()`, `_execute_pipeline()`

**Repository calls**: `eto_run_repository.update()`, `eto_run_repository.get_by_id()`

---

**Internal Methods**:

### `_match_template(run_id, pdf_objects)` → Optional[TemplateVersion]

**Called by**: `process_run()`

**Purpose**: Match PDF against active templates (Stage 1)

**Implementation**:
```python
def _match_template(
    self,
    run_id: int,
    pdf_objects: list[PdfObject]
) -> Optional[TemplateVersion]:
    """
    Match PDF against active templates.

    Process:
    1. Get all active templates from template service
    2. For each template, check if signature objects match
    3. Return first matched template (or None)
    4. Store matching result in stage table

    Args:
        run_id: ETO run ID
        pdf_objects: Extracted PDF objects

    Returns:
        Matched TemplateVersion or None if no match

    Note: Stores stage result in database
    """
    try:
        # Get active templates
        active_templates = self.template_service.get_active_templates()

        if not active_templates:
            # No templates available
            self.stage_repository.create_stage_result(
                EtoStageResultCreate(
                    run_id=run_id,
                    stage_name="template_matching",
                    status="failure",
                    error_message="No active templates available",
                    completed_at=datetime.now(timezone.utc)
                )
            )
            return None

        # Try to match each template
        for template in active_templates:
            if self.template_service.check_signature_match(
                template.signature_objects,
                pdf_objects
            ):
                # Match found
                self.stage_repository.create_stage_result(
                    EtoStageResultCreate(
                        run_id=run_id,
                        stage_name="template_matching",
                        status="success",
                        matched_template_id=template.template_id,
                        matched_version_id=template.id,
                        completed_at=datetime.now(timezone.utc)
                    )
                )

                logger.info(
                    f"Run {run_id} matched template {template.template_id} "
                    f"version {template.version_num}"
                )

                return template

        # No match found
        self.stage_repository.create_stage_result(
            EtoStageResultCreate(
                run_id=run_id,
                stage_name="template_matching",
                status="failure",
                error_message="No matching template found",
                completed_at=datetime.now(timezone.utc)
            )
        )

        return None

    except Exception as e:
        logger.error(f"Error in template matching for run {run_id}: {e}")

        self.stage_repository.create_stage_result(
            EtoStageResultCreate(
                run_id=run_id,
                stage_name="template_matching",
                status="failure",
                error_message=f"Template matching error: {str(e)}",
                completed_at=datetime.now(timezone.utc)
            )
        )

        raise
```

**Service calls**: `template_service.get_active_templates()`, `template_service.check_signature_match()`

**Repository calls**: `stage_repository.create_stage_result()`

---

### `_extract_data(run_id, template_version, pdf_objects)` → dict

**Called by**: `process_run()`

**Purpose**: Extract data from PDF using template's extraction fields (Stage 2)

**Implementation**:
```python
def _extract_data(
    self,
    run_id: int,
    template_version: TemplateVersion,
    pdf_objects: list[PdfObject]
) -> dict[str, Any]:
    """
    Extract data from PDF using template's extraction fields.

    Process:
    1. For each extraction field in template:
       - Find PDF objects within bbox
       - Extract text content
       - Validate against field rules (required, regex)
    2. Store extracted data in stage table
    3. Return extracted data dict

    Args:
        run_id: ETO run ID
        template_version: Matched template version with extraction fields
        pdf_objects: Extracted PDF objects

    Returns:
        Dictionary of extracted data (field_label → value)

    Raises:
        ServiceError: If required fields missing or validation fails

    Note: Stores stage result in database
    """
    try:
        extracted_data = {}

        # Extract each field
        for field in template_version.extraction_fields:
            # Find objects within field's bbox
            field_objects = [
                obj for obj in pdf_objects
                if obj.page_number == field.page
                and self._bbox_overlaps(obj.bbox, field.bbox)
            ]

            # Extract text from objects
            field_value = self._extract_text_from_objects(field_objects)

            # Validate
            if field.required and not field_value:
                raise ServiceError(
                    f"Required field '{field.label}' is empty"
                )

            if field.validation_regex and field_value:
                import re
                if not re.match(field.validation_regex, field_value):
                    raise ServiceError(
                        f"Field '{field.label}' failed validation (regex: {field.validation_regex})"
                    )

            extracted_data[field.label] = field_value

        # Success - store result
        self.stage_repository.create_stage_result(
            EtoStageResultCreate(
                run_id=run_id,
                stage_name="data_extraction",
                status="success",
                extracted_data=extracted_data,
                completed_at=datetime.now(timezone.utc)
            )
        )

        logger.info(
            f"Extracted {len(extracted_data)} fields for run {run_id}"
        )

        return extracted_data

    except Exception as e:
        logger.error(f"Error in data extraction for run {run_id}: {e}")

        self.stage_repository.create_stage_result(
            EtoStageResultCreate(
                run_id=run_id,
                stage_name="data_extraction",
                status="failure",
                error_message=f"Data extraction error: {str(e)}",
                completed_at=datetime.now(timezone.utc)
            )
        )

        raise
```

**Internal calls**: `_bbox_overlaps()`, `_extract_text_from_objects()`

**Repository calls**: `stage_repository.create_stage_result()`

---

### `_execute_pipeline(run_id, template_version, extracted_data)` → None

**Called by**: `process_run()`

**Purpose**: Execute template's transformation pipeline (Stage 3)

**Implementation**:
```python
def _execute_pipeline(
    self,
    run_id: int,
    template_version: TemplateVersion,
    extracted_data: dict[str, Any]
) -> None:
    """
    Execute template's transformation pipeline.

    Process:
    1. Get pipeline definition from template version
    2. Execute pipeline via pipeline service
    3. Collect step results and action executions
    4. Store pipeline execution result in stage table

    Args:
        run_id: ETO run ID
        template_version: Matched template version with pipeline reference
        extracted_data: Extracted data dictionary

    Returns:
        None

    Raises:
        ServiceError: If pipeline execution fails

    Note: Stores stage result with steps in database
    """
    try:
        # Execute pipeline
        pipeline_result = self.pipeline_service.execute_pipeline(
            pipeline_id=template_version.pipeline_definition_id,
            input_data=extracted_data
        )

        # Determine status
        stage_status = "success" if pipeline_result.success else "failure"

        # Store result with steps
        self.stage_repository.create_stage_result(
            EtoStageResultCreate(
                run_id=run_id,
                stage_name="pipeline_execution",
                status=stage_status,
                pipeline_definition_id=template_version.pipeline_definition_id,
                executed_actions=pipeline_result.executed_actions,
                execution_steps=pipeline_result.steps,
                error_message=pipeline_result.error_message,
                completed_at=datetime.now(timezone.utc)
            )
        )

        if pipeline_result.success:
            logger.info(
                f"Pipeline execution completed for run {run_id} "
                f"({len(pipeline_result.steps)} steps, "
                f"{len(pipeline_result.executed_actions)} actions)"
            )
        else:
            logger.error(
                f"Pipeline execution failed for run {run_id}: "
                f"{pipeline_result.error_message}"
            )
            raise ServiceError(f"Pipeline execution failed: {pipeline_result.error_message}")

    except Exception as e:
        logger.error(f"Error in pipeline execution for run {run_id}: {e}")

        self.stage_repository.create_stage_result(
            EtoStageResultCreate(
                run_id=run_id,
                stage_name="pipeline_execution",
                status="failure",
                error_message=f"Pipeline execution error: {str(e)}",
                completed_at=datetime.now(timezone.utc)
            )
        )

        raise
```

**Service calls**: `pipeline_service.execute_pipeline()`

**Repository calls**: `stage_repository.create_stage_result()`

---

### Helper Methods

```python
def _bbox_overlaps(self, bbox1: tuple, bbox2: tuple) -> bool:
    """Check if two bounding boxes overlap"""
    x1_min, y1_min, x1_max, y1_max = bbox1
    x2_min, y2_min, x2_max, y2_max = bbox2

    return not (
        x1_max < x2_min or x2_max < x1_min or
        y1_max < y2_min or y2_max < y1_min
    )

def _extract_text_from_objects(self, objects: list[PdfObject]) -> str:
    """Extract and concatenate text from PDF objects"""
    text_parts = []

    for obj in objects:
        if obj.object_type == "text":
            text_parts.append(obj.content_json.get("text", ""))
        elif obj.object_type == "table":
            # Extract text from table cells
            table_data = obj.content_json.get("table", [])
            for row in table_data:
                for cell in row:
                    if cell:
                        text_parts.append(str(cell))

    return " ".join(text_parts).strip()
```

---

**Dataclasses Used**:

**Input types** (from `shared/types/`):
- `EtoRunCreate` - Data for creating new run
- `EtoRunUpdate` - Data for updating run (status, timestamps, errors)
- `EtoStageResultCreate` - Data for creating stage result

**Output types** (from `shared/types/`):
- `EtoRunListResult` - Paginated list result (items, total, limit, offset)
- `EtoRunSummary` - Summary view for list (in items array)
- `EtoRunDetail` - Complete run with all stages
- `EtoRunCreated` - Response for create endpoint
- `TemplateVersion` - Matched template version
- `PdfObject` - PDF objects for matching/extraction

---

**API Integration**:

**Router depends on this service for these endpoints:**
- `GET /eto-runs` → `list_runs()`
- `GET /eto-runs/{id}` → `get_run_details()`
- `POST /eto-runs/upload` → `create_run_from_upload()`
- `POST /eto-runs/reprocess` → `reprocess_runs()`
- `POST /eto-runs/skip` → `skip_runs()`
- `DELETE /eto-runs` → `delete_runs()`
- `POST /eto-runs/{id}/reprocess` → `reprocess_run()`

**Background worker calls this service:**
- `process_run()` - Triggered when run status changes to not_started (NOT called by router)

**Router dependency injection:**
```python
@router.get("")
def list_eto_runs(
    status: Optional[str] = None,
    sort_by: str = "started_at",
    sort_order: str = "desc",
    limit: int = 50,
    offset: int = 0,
    eto_service: EtoProcessingService = Depends(
        lambda: ServiceContainer.get_eto_processing_service()
    )
) -> EtoRunListResponse:
    result = eto_service.list_runs(status, sort_by, sort_order, limit, offset)
    # Map dataclass → Pydantic
    return EtoRunListResponse(...)

@router.post("/upload")
def upload_pdf_for_processing(
    pdf_file: UploadFile,
    eto_service: EtoProcessingService = Depends(
        lambda: ServiceContainer.get_eto_processing_service()
    ),
    pdf_service: PdfFilesService = Depends(
        lambda: ServiceContainer.get_pdf_files_service()
    )
) -> EtoRunCreatedResponse:
    # Store PDF first
    pdf_metadata = pdf_service.store_pdf(
        file_bytes=pdf_file.read(),
        filename=pdf_file.filename
    )

    # Create run
    run = eto_service.create_run_from_upload(pdf_metadata.id)

    # Map dataclass → Pydantic
    return EtoRunCreatedResponse(...)
```

---

## Service 5: Template Management Service

**Location**: `server-new/src/features/template_management/service.py`

**Purpose**: Manages template lifecycle including creation, versioning, activation, and archival. Handles signature object definitions (for PDF matching), extraction field definitions (for data extraction), and transformation pipeline associations. Provides template matching capabilities and validation. Serves as the central service for template configuration and metadata management.

**Dependencies**:
- `DatabaseConnectionManager` - For database access and transaction management
- `PdfFilesService` - For PDF operations during template creation
- `PipelineService` - For pipeline compilation and validation
- `TemplateRepository` - For template CRUD operations
- `TemplateVersionRepository` - For version management
- `PdfRepository` - For source PDF associations

**Responsibilities**:
- Template CRUD operations (create, read, update, delete, list)
- Template versioning (create new version, list versions, get version details)
- Template lifecycle management (activate, deactivate)
- Signature object matching logic (used by ETO Processing Service)
- Extraction field validation
- Template simulation (test full ETO pipeline without persistence)
- Active template queries (for ETO matching)

**Constructor**:
```python
def __init__(
    self,
    connection_manager: DatabaseConnectionManager,
    pdf_service: PdfFilesService,
    pipeline_service: PipelineService
):
    self.connection_manager = connection_manager
    self.pdf_service = pdf_service
    self.pipeline_service = pipeline_service

    self.template_repository = TemplateRepository(connection_manager=connection_manager)
    self.version_repository = TemplateVersionRepository(connection_manager=connection_manager)
    self.pdf_repository = PdfRepository(connection_manager=connection_manager)
```

**Public Methods**:

### 1. `list_templates(status, sort_by, sort_order, limit, offset)` → TemplateListResult

**Called by**: Router endpoint `GET /pdf-templates`

**Purpose**: List templates with summary information

**Implementation**:
```python
def list_templates(
    self,
    status: Optional[str] = None,
    sort_by: str = "name",
    sort_order: str = "asc",
    limit: int = 50,
    offset: int = 0
) -> TemplateListResult:
    """
    List templates with pagination and filtering.

    Args:
        status: Filter by status (active, inactive)
        sort_by: Sort field (name, status, usage_count)
        sort_order: Sort order (asc, desc)
        limit: Max results (default 50, max 200)
        offset: Pagination offset

    Returns:
        TemplateListResult with items, total, limit, offset
    """
    if limit > 200:
        limit = 200

    templates, total = self.template_repository.list_with_pagination(
        status_filter=status,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=limit,
        offset=offset
    )

    return TemplateListResult(
        items=templates,
        total=total,
        limit=limit,
        offset=offset
    )
```

**Repository calls**: `template_repository.list_with_pagination()`

---

### 2. `get_template(template_id)` → TemplateDetail

**Called by**: Router endpoint `GET /pdf-templates/{id}`

**Purpose**: Get template with current version details

**Implementation**:
```python
def get_template(self, template_id: int) -> TemplateDetail:
    """
    Get template with current version details.

    Includes:
    - Template metadata (id, name, description, status)
    - Current version data (signature objects, extraction fields, pipeline reference)
    - Version history summary

    Args:
        template_id: Template ID

    Returns:
        TemplateDetail dataclass

    Raises:
        ObjectNotFoundError: If template not found
    """
    template = self.template_repository.get_by_id_with_current_version(template_id)
    if not template:
        raise ObjectNotFoundError(f"Template {template_id} not found")

    return template
```

**Repository calls**: `template_repository.get_by_id_with_current_version()`

---

### 3. `create_template(template_data, pdf_file_bytes)` → TemplateCreated

**Called by**: Router endpoint `POST /pdf-templates`

**Purpose**: Create template with initial version

**Implementation**:
```python
def create_template(
    self,
    template_data: TemplateCreate,
    pdf_file_bytes: Optional[bytes] = None
) -> TemplateCreated:
    """
    Create template with initial version (version 1).

    Process:
    1. Store PDF if uploaded (or use existing source_pdf_id)
    2. Validate signature objects and extraction fields
    3. Compile pipeline
    4. Create template + version 1 atomically
    5. Set status to inactive (must be activated)

    Args:
        template_data: TemplateCreate with all wizard data
        pdf_file_bytes: Optional PDF bytes (if uploading new PDF)

    Returns:
        TemplateCreated with template ID, version info, pipeline ID

    Raises:
        ServiceError: If validation or compilation fails
    """
    with self.connection_manager.unit_of_work() as uow:
        # Handle PDF
        if pdf_file_bytes:
            # Store new PDF
            pdf_metadata = self.pdf_service.store_pdf(
                file_bytes=pdf_file_bytes,
                filename=template_data.name + ".pdf"
            )
            source_pdf_id = pdf_metadata.id
        elif template_data.source_pdf_id:
            # Validate existing PDF
            pdf = uow.pdfs.get_by_id(template_data.source_pdf_id)
            if not pdf:
                raise ObjectNotFoundError(
                    f"PDF {template_data.source_pdf_id} not found"
                )
            source_pdf_id = template_data.source_pdf_id
        else:
            raise ServiceError("Must provide either pdf_file or source_pdf_id")

        # Validate signature objects and extraction fields
        self._validate_template_fields(
            template_data.signature_objects,
            template_data.extraction_fields
        )

        # Compile pipeline
        pipeline_id = self.pipeline_service.compile_pipeline(
            template_data.pipeline_state,
            template_data.visual_state
        )

        # Create template
        template_create = TemplateCreateInternal(
            name=template_data.name,
            description=template_data.description,
            source_pdf_id=source_pdf_id,
            status="inactive",  # Always starts inactive
            current_version_id=None  # Will be set after version creation
        )

        template = uow.templates.create(template_create)

        # Create version 1
        version_create = TemplateVersionCreate(
            template_id=template.id,
            version_num=1,
            signature_objects=template_data.signature_objects,
            extraction_fields=template_data.extraction_fields,
            pipeline_definition_id=pipeline_id,
            usage_count=0
        )

        version = uow.template_versions.create(version_create)

        # Update template with current_version_id
        uow.templates.update(
            template.id,
            TemplateUpdate(current_version_id=version.id)
        )

        logger.info(
            f"Created template {template.id} with version 1 (pipeline {pipeline_id})"
        )

        return TemplateCreated(
            id=template.id,
            name=template.name,
            status="inactive",
            current_version_id=version.id,
            current_version_num=1,
            pipeline_definition_id=pipeline_id
        )
```

**Service calls**: `pdf_service.store_pdf()`, `pipeline_service.compile_pipeline()`

**Internal calls**: `_validate_template_fields()`

**Repository calls**: `uow.pdfs.get_by_id()`, `uow.templates.create()`, `uow.template_versions.create()`, `uow.templates.update()`

**Transaction**: Uses Unit of Work for atomic template + version creation

---

### 4. `update_template(template_id, template_data)` → TemplateUpdated

**Called by**: Router endpoint `PUT /pdf-templates/{id}`

**Purpose**: Update template by creating new version

**Implementation**:
```python
def update_template(
    self,
    template_id: int,
    template_data: TemplateUpdate
) -> TemplateUpdated:
    """
    Update template by creating new version.

    Process:
    1. Get current template
    2. Validate fields
    3. Compile pipeline
    4. Create new version (increment version_num)
    5. Update template's current_version_id
    6. Optionally update template metadata (name, description)

    Args:
        template_id: Template ID
        template_data: TemplateUpdate with new version data

    Returns:
        TemplateUpdated with updated info

    Raises:
        ObjectNotFoundError: If template not found
        ServiceError: If validation fails
    """
    with self.connection_manager.unit_of_work() as uow:
        # Get template
        template = uow.templates.get_by_id(template_id)
        if not template:
            raise ObjectNotFoundError(f"Template {template_id} not found")

        # Get current version to determine next version_num
        current_version = uow.template_versions.get_by_id(
            template.current_version_id
        )

        next_version_num = current_version.version_num + 1

        # Validate fields
        self._validate_template_fields(
            template_data.signature_objects,
            template_data.extraction_fields
        )

        # Compile pipeline
        pipeline_id = self.pipeline_service.compile_pipeline(
            template_data.pipeline_state,
            template_data.visual_state
        )

        # Create new version
        version_create = TemplateVersionCreate(
            template_id=template_id,
            version_num=next_version_num,
            signature_objects=template_data.signature_objects,
            extraction_fields=template_data.extraction_fields,
            pipeline_definition_id=pipeline_id,
            usage_count=0
        )

        new_version = uow.template_versions.create(version_create)

        # Update template
        template_update_data = TemplateUpdate(
            current_version_id=new_version.id
        )

        # Optionally update name/description
        if template_data.name:
            template_update_data.name = template_data.name
        if template_data.description is not None:
            template_update_data.description = template_data.description

        updated_template = uow.templates.update(
            template_id,
            template_update_data
        )

        logger.info(
            f"Updated template {template_id} to version {next_version_num} "
            f"(pipeline {pipeline_id})"
        )

        return TemplateUpdated(
            id=template_id,
            name=updated_template.name,
            status=updated_template.status,
            current_version_id=new_version.id,
            current_version_num=next_version_num,
            pipeline_definition_id=pipeline_id
        )
```

**Service calls**: `pipeline_service.compile_pipeline()`

**Internal calls**: `_validate_template_fields()`

**Repository calls**: `uow.templates.get_by_id()`, `uow.template_versions.get_by_id()`, `uow.template_versions.create()`, `uow.templates.update()`

**Transaction**: Uses Unit of Work

---

### 5. `delete_template(template_id)` → None

**Called by**: Router endpoint `DELETE /pdf-templates/{id}`

**Purpose**: Delete template (only if never used)

**Implementation**:
```python
def delete_template(self, template_id: int) -> None:
    """
    Delete template.

    Validation:
    - Template must exist
    - No version can have usage_count > 0

    Args:
        template_id: Template ID

    Returns:
        None

    Raises:
        ObjectNotFoundError: If template not found
        ServiceError: If template has usage history
    """
    with self.connection_manager.unit_of_work() as uow:
        # Get template
        template = uow.templates.get_by_id(template_id)
        if not template:
            raise ObjectNotFoundError(f"Template {template_id} not found")

        # Check all versions for usage
        versions = uow.template_versions.get_by_template_id(template_id)

        used_versions = [v.version_num for v in versions if v.usage_count > 0]
        if used_versions:
            raise ServiceError(
                f"Cannot delete template with usage history. "
                f"Versions with usage: {used_versions}. "
                f"Deactivate instead."
            )

        # Delete versions first (foreign key)
        for version in versions:
            uow.template_versions.delete(version.id)

        # Delete template
        uow.templates.delete(template_id)

        logger.info(f"Deleted template {template_id} and {len(versions)} versions")
```

**Repository calls**: `uow.templates.get_by_id()`, `uow.template_versions.get_by_template_id()`, `uow.template_versions.delete()`, `uow.templates.delete()`

**Transaction**: Uses Unit of Work

---

### 6. `activate_template(template_id)` → TemplateStatusChanged

**Called by**: Router endpoint `POST /pdf-templates/{id}/activate`

**Purpose**: Activate template for ETO matching

**Implementation**:
```python
def activate_template(self, template_id: int) -> TemplateStatusChanged:
    """
    Activate template (makes it available for ETO matching).

    Args:
        template_id: Template ID

    Returns:
        TemplateStatusChanged with updated status

    Raises:
        ObjectNotFoundError: If template not found
        ServiceError: If no finalized versions
    """
    # Get template
    template = self.template_repository.get_by_id(template_id)
    if not template:
        raise ObjectNotFoundError(f"Template {template_id} not found")

    # Validate has at least one version
    if not template.current_version_id:
        raise ServiceError("Template has no finalized versions")

    # Update status
    updated = self.template_repository.update(
        template_id,
        TemplateUpdate(status="active")
    )

    logger.info(f"Activated template {template_id}")

    return TemplateStatusChanged(
        id=template_id,
        status="active",
        current_version_id=updated.current_version_id
    )
```

**Repository calls**: `template_repository.get_by_id()`, `template_repository.update()`

---

### 7. `deactivate_template(template_id)` → TemplateStatusChanged

**Called by**: Router endpoint `POST /pdf-templates/{id}/deactivate`

**Purpose**: Deactivate template (archive)

**Implementation**:
```python
def deactivate_template(self, template_id: int) -> TemplateStatusChanged:
    """
    Deactivate template (removes from ETO matching).

    Args:
        template_id: Template ID

    Returns:
        TemplateStatusChanged with updated status

    Raises:
        ObjectNotFoundError: If template not found
    """
    template = self.template_repository.get_by_id(template_id)
    if not template:
        raise ObjectNotFoundError(f"Template {template_id} not found")

    updated = self.template_repository.update(
        template_id,
        TemplateUpdate(status="inactive")
    )

    logger.info(f"Deactivated template {template_id}")

    return TemplateStatusChanged(
        id=template_id,
        status="inactive",
        current_version_id=updated.current_version_id
    )
```

**Repository calls**: `template_repository.get_by_id()`, `template_repository.update()`

---

### 8. `list_versions(template_id)` → list[TemplateVersionSummary]

**Called by**: Router endpoint `GET /pdf-templates/{id}/versions`

**Purpose**: List all versions for template

**Implementation**:
```python
def list_versions(self, template_id: int) -> list[TemplateVersionSummary]:
    """
    List all versions for a template.

    Returns versions ordered by version_num DESC (newest first).

    Args:
        template_id: Template ID

    Returns:
        List of TemplateVersionSummary

    Raises:
        ObjectNotFoundError: If template not found
    """
    # Validate template exists
    template = self.template_repository.get_by_id(template_id)
    if not template:
        raise ObjectNotFoundError(f"Template {template_id} not found")

    # Get versions
    versions = self.version_repository.get_by_template_id(
        template_id,
        order_by="version_num",
        desc=True
    )

    # Mark current version
    summaries = [
        TemplateVersionSummary(
            version_id=v.id,
            version_num=v.version_num,
            usage_count=v.usage_count,
            last_used_at=v.last_used_at,
            is_current=(v.id == template.current_version_id)
        )
        for v in versions
    ]

    return summaries
```

**Repository calls**: `template_repository.get_by_id()`, `version_repository.get_by_template_id()`

---

### 9. `get_version(template_id, version_id)` → TemplateVersionDetail

**Called by**: Router endpoint `GET /pdf-templates/{id}/versions/{version_id}`

**Purpose**: Get specific version details

**Implementation**:
```python
def get_version(
    self,
    template_id: int,
    version_id: int
) -> TemplateVersionDetail:
    """
    Get specific version details.

    Args:
        template_id: Template ID (for validation)
        version_id: Version ID

    Returns:
        TemplateVersionDetail with full version data

    Raises:
        ObjectNotFoundError: If template or version not found
        ServiceError: If version doesn't belong to template
    """
    # Get version
    version = self.version_repository.get_by_id(version_id)
    if not version:
        raise ObjectNotFoundError(f"Version {version_id} not found")

    # Validate belongs to template
    if version.template_id != template_id:
        raise ServiceError(
            f"Version {version_id} does not belong to template {template_id}"
        )

    # Get template for current_version_id check
    template = self.template_repository.get_by_id(template_id)

    return TemplateVersionDetail(
        version_id=version.id,
        template_id=template_id,
        version_num=version.version_num,
        usage_count=version.usage_count,
        last_used_at=version.last_used_at,
        is_current=(version.id == template.current_version_id),
        signature_objects=version.signature_objects,
        extraction_fields=version.extraction_fields,
        pipeline_definition_id=version.pipeline_definition_id
    )
```

**Repository calls**: `version_repository.get_by_id()`, `template_repository.get_by_id()`

---

### 10. `simulate_template(template_data, pdf_bytes, pdf_id)` → SimulationResult

**Called by**: Router endpoint `POST /pdf-templates/simulate`

**Purpose**: Simulate ETO pipeline without persistence

**Implementation**:
```python
def simulate_template(
    self,
    template_data: TemplateSimulationRequest,
    pdf_bytes: Optional[bytes] = None,
    pdf_id: Optional[int] = None
) -> SimulationResult:
    """
    Simulate full ETO pipeline without persistence.

    Process:
    1. Get PDF objects (from stored PDF or uploaded bytes)
    2. Template matching (always succeeds in simulation)
    3. Data extraction with validation
    4. Pipeline execution (transformations run, actions simulated)

    Args:
        template_data: Template definition to test
        pdf_bytes: PDF bytes (if uploaded)
        pdf_id: PDF ID (if using stored PDF)

    Returns:
        SimulationResult with stage results

    Raises:
        ServiceError: If simulation fails
    """
    try:
        # Get PDF objects
        if pdf_bytes:
            pdf_objects = self.pdf_service.extract_objects_from_bytes(
                pdf_bytes,
                "simulation.pdf"
            )
        elif pdf_id:
            pdf_objects = self.pdf_service.get_pdf_objects(pdf_id)
        else:
            raise ServiceError("Must provide either pdf_bytes or pdf_id")

        # Stage 1: Template Matching (always succeeds)
        matching_result = SimulationStageResult(
            status="success",
            message="Simulation mode - template matching skipped"
        )

        # Stage 2: Data Extraction
        extraction_result = self._simulate_extraction(
            template_data.extraction_fields,
            pdf_objects
        )

        # Stage 3: Pipeline Execution
        if extraction_result.status == "success":
            pipeline_result = self.pipeline_service.simulate_pipeline(
                template_data.pipeline_state,
                extraction_result.extracted_data
            )
        else:
            pipeline_result = SimulationStageResult(
                status="skipped",
                message="Skipped due to extraction failure"
            )

        return SimulationResult(
            template_matching=matching_result,
            data_extraction=extraction_result,
            pipeline_execution=pipeline_result
        )

    except Exception as e:
        logger.error(f"Error in template simulation: {e}")
        raise ServiceError(f"Simulation failed: {str(e)}")
```

**Service calls**: `pdf_service.extract_objects_from_bytes()`, `pdf_service.get_pdf_objects()`, `pipeline_service.simulate_pipeline()`

**Internal calls**: `_simulate_extraction()`

---

### 11. `get_active_templates()` → list[TemplateVersion]

**Called by**: EtoProcessingService._match_template() (NOT by router)

**Purpose**: Get all active templates for ETO matching

**Implementation**:
```python
def get_active_templates(self) -> list[TemplateVersion]:
    """
    Get all active templates with current version data.

    Used by ETO Processing Service for template matching.

    Returns:
        List of TemplateVersion (current versions of active templates)
    """
    return self.template_repository.get_active_with_current_versions()
```

**Repository calls**: `template_repository.get_active_with_current_versions()`

---

### 12. `check_signature_match(signature_objects, pdf_objects)` → bool

**Called by**: EtoProcessingService._match_template() (NOT by router)

**Purpose**: Check if PDF matches template's signature objects

**Implementation**:
```python
def check_signature_match(
    self,
    signature_objects: list[SignatureObject],
    pdf_objects: list[PdfObject]
) -> bool:
    """
    Check if PDF contains template's signature objects.

    Matching logic:
    - All signature objects must be found in PDF
    - Object type must match
    - Object must be on correct page
    - Bbox must overlap (within tolerance)

    Args:
        signature_objects: Template's signature objects
        pdf_objects: PDF's extracted objects

    Returns:
        True if all signature objects found, False otherwise
    """
    for sig_obj in signature_objects:
        # Find matching PDF object
        found = False

        for pdf_obj in pdf_objects:
            if (
                pdf_obj.object_type == sig_obj.object_type
                and pdf_obj.page_number == sig_obj.page
                and self._bbox_matches(pdf_obj.bbox, sig_obj.bbox, tolerance=5.0)
            ):
                found = True
                break

        if not found:
            # Signature object not found - no match
            return False

    # All signature objects found
    return True
```

**Internal calls**: `_bbox_matches()`

---

**Internal Methods**:

### `_validate_template_fields(signature_objects, extraction_fields)` → None

```python
def _validate_template_fields(
    self,
    signature_objects: list[SignatureObject],
    extraction_fields: list[ExtractionField]
) -> None:
    """
    Validate signature objects and extraction fields.

    Checks:
    - At least 1 signature object
    - At least 1 extraction field
    - Valid object types
    - Valid bbox coordinates

    Raises:
        ServiceError: If validation fails
    """
    if not signature_objects:
        raise ServiceError("Must have at least one signature object")

    if not extraction_fields:
        raise ServiceError("Must have at least one extraction field")

    # Additional validation...
```

### `_simulate_extraction(extraction_fields, pdf_objects)` → SimulationStageResult

```python
def _simulate_extraction(
    self,
    extraction_fields: list[ExtractionField],
    pdf_objects: list[PdfObject]
) -> SimulationStageResult:
    """
    Simulate data extraction stage.

    Returns extraction result with validation info.
    """
    # Implementation similar to EtoProcessingService._extract_data()
    # but returns SimulationStageResult instead of raising exceptions
```

### `_bbox_matches(bbox1, bbox2, tolerance)` → bool

```python
def _bbox_matches(
    self,
    bbox1: tuple,
    bbox2: tuple,
    tolerance: float = 5.0
) -> bool:
    """
    Check if two bboxes match within tolerance.

    Args:
        bbox1: First bbox (x0, y0, x1, y1)
        bbox2: Second bbox
        tolerance: Allowed pixel difference

    Returns:
        True if bboxes match within tolerance
    """
    x1_0, y1_0, x1_1, y1_1 = bbox1
    x2_0, y2_0, x2_1, y2_1 = bbox2

    return (
        abs(x1_0 - x2_0) <= tolerance
        and abs(y1_0 - y2_0) <= tolerance
        and abs(x1_1 - x2_1) <= tolerance
        and abs(y1_1 - y2_1) <= tolerance
    )
```

---

**Dataclasses Used**:

**Input types** (from `shared/types/`):
- `TemplateCreate` - Data for creating template
- `TemplateUpdate` - Data for updating template
- `TemplateSimulationRequest` - Data for simulation
- `SignatureObject` - Signature object definition
- `ExtractionField` - Extraction field definition

**Output types** (from `shared/types/`):
- `TemplateListResult` - Paginated list result
- `TemplateSummary` - Summary for list view
- `TemplateDetail` - Full template with current version
- `TemplateCreated` - Response for create
- `TemplateUpdated` - Response for update
- `TemplateStatusChanged` - Response for activate/deactivate
- `TemplateVersionSummary` - Version summary
- `TemplateVersionDetail` - Full version data
- `TemplateVersion` - Version data for ETO matching
- `SimulationResult` - Simulation response
- `PdfObject` - PDF objects

---

**API Integration**:

**Router depends on this service for these endpoints:**
- `GET /pdf-templates` → `list_templates()`
- `GET /pdf-templates/{id}` → `get_template()`
- `POST /pdf-templates` → `create_template()`
- `PUT /pdf-templates/{id}` → `update_template()`
- `DELETE /pdf-templates/{id}` → `delete_template()`
- `POST /pdf-templates/{id}/activate` → `activate_template()`
- `POST /pdf-templates/{id}/deactivate` → `deactivate_template()`
- `GET /pdf-templates/{id}/versions` → `list_versions()`
- `GET /pdf-templates/{id}/versions/{version_id}` → `get_version()`
- `POST /pdf-templates/simulate` → `simulate_template()`

**ETO Processing Service calls this service:**
- `get_active_templates()` - Get templates for matching
- `check_signature_match()` - Check if PDF matches template

**Router dependency injection:**
```python
@router.post("")
def create_template(
    request: CreateTemplateRequest,
    pdf_file: Optional[UploadFile] = None,
    template_service: TemplateManagementService = Depends(
        lambda: ServiceContainer.get_template_service()
    )
) -> CreateTemplateResponse:
    # Handle PDF file if uploaded
    pdf_bytes = None
    if pdf_file:
        pdf_bytes = pdf_file.read()

    # Create template
    template = template_service.create_template(
        template_data=map_to_dataclass(request),
        pdf_file_bytes=pdf_bytes
    )

    # Map dataclass → Pydantic
    return CreateTemplateResponse(...)
```

---

## Service 6: Pipeline Service

**Location**: `server-new/src/features/pipeline_management/service.py`

**Purpose**: Manages data transformation pipeline creation, editing, compilation, and execution. Handles pipeline definition (JSON-based), module orchestration, and validation. Provides pipeline execution runtime for transforming extracted data. Integrates with Module Catalog Service for module discovery and validation. Compiles declarative pipeline definitions into executable transformation sequences.

**Dependencies**:
- `DatabaseConnectionManager` - For database access and transaction management
- `ModuleCatalogService` - For module validation and metadata
- `PipelineRepository` - For pipeline definition CRUD
- `CompiledPlanRepository` - For compiled execution plan storage
- `DaskCompiler` - For compiling pipeline to Dask DAG (internal utility)

**Responsibilities**:
- Pipeline CRUD operations (create, read, update, delete, list)
- Pipeline compilation (declarative JSON → executable Dask DAG)
- Pipeline validation (module references, connections, types)
- Pipeline execution (run Dask DAG with input data)
- Pipeline simulation (execute with action modules simulated)
- Compiled plan caching and deduplication
- Module instance configuration management

**Constructor**:
```python
def __init__(
    self,
    connection_manager: DatabaseConnectionManager,
    module_catalog_service: ModuleCatalogService
):
    self.connection_manager = connection_manager
    self.module_catalog_service = module_catalog_service

    self.pipeline_repository = PipelineRepository(connection_manager=connection_manager)
    self.compiled_plan_repository = CompiledPlanRepository(connection_manager=connection_manager)

    # Dask compiler for pipeline → DAG conversion
    self.dask_compiler = DaskCompiler()
```

**Public Methods**:

### 1. `list_pipelines(sort_by, sort_order, limit, offset)` → PipelineListResult

**Called by**: Router endpoint `GET /pipelines`

**Purpose**: List pipeline definitions

**Implementation**:
```python
def list_pipelines(
    self,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    limit: int = 50,
    offset: int = 0
) -> PipelineListResult:
    """
    List pipeline definitions with pagination.

    Args:
        sort_by: Sort field (id, created_at)
        sort_order: Sort order (asc, desc)
        limit: Max results (default 50, max 200)
        offset: Pagination offset

    Returns:
        PipelineListResult with items, total, limit, offset
    """
    if limit > 200:
        limit = 200

    pipelines, total = self.pipeline_repository.list_with_pagination(
        sort_by=sort_by,
        sort_order=sort_order,
        limit=limit,
        offset=offset
    )

    return PipelineListResult(
        items=pipelines,
        total=total,
        limit=limit,
        offset=offset
    )
```

**Repository calls**: `pipeline_repository.list_with_pagination()`

---

### 2. `get_pipeline(pipeline_id)` → PipelineDetail

**Called by**: Router endpoint `GET /pipelines/{id}`

**Purpose**: Get pipeline definition with visual state

**Implementation**:
```python
def get_pipeline(self, pipeline_id: int) -> PipelineDetail:
    """
    Get pipeline definition including pipeline_state and visual_state.

    Args:
        pipeline_id: Pipeline definition ID

    Returns:
        PipelineDetail with full pipeline data

    Raises:
        ObjectNotFoundError: If pipeline not found
    """
    pipeline = self.pipeline_repository.get_by_id(pipeline_id)
    if not pipeline:
        raise ObjectNotFoundError(f"Pipeline {pipeline_id} not found")

    return pipeline
```

**Repository calls**: `pipeline_repository.get_by_id()`

---

### 3. `create_pipeline(pipeline_state, visual_state)` → PipelineCreated

**Called by**: Router endpoint `POST /pipelines`

**Purpose**: Create standalone pipeline (dev/testing)

**Implementation**:
```python
def create_pipeline(
    self,
    pipeline_state: dict,
    visual_state: dict
) -> PipelineCreated:
    """
    Create standalone pipeline definition.

    Process:
    1. Validate pipeline structure
    2. Validate module references
    3. Create pipeline definition record
    4. Return created pipeline info

    Note: Compilation happens lazily on first execution

    Args:
        pipeline_state: Pipeline logical structure
        visual_state: Pipeline visual layout

    Returns:
        PipelineCreated with pipeline ID

    Raises:
        ServiceError: If validation fails
    """
    # Validate pipeline
    self._validate_pipeline(pipeline_state)

    # Create pipeline
    pipeline_create = PipelineCreate(
        pipeline_state=pipeline_state,
        visual_state=visual_state,
        compiled_plan_id=None  # Compiled on first use
    )

    pipeline = self.pipeline_repository.create(pipeline_create)

    logger.info(f"Created pipeline {pipeline.id}")

    return PipelineCreated(
        id=pipeline.id,
        compiled_plan_id=None
    )
```

**Internal calls**: `_validate_pipeline()`

**Repository calls**: `pipeline_repository.create()`

---

### 4. `update_pipeline(pipeline_id, pipeline_state, visual_state)` → PipelineUpdated

**Called by**: Router endpoint `PUT /pipelines/{id}`

**Purpose**: Update pipeline definition

**Implementation**:
```python
def update_pipeline(
    self,
    pipeline_id: int,
    pipeline_state: dict,
    visual_state: dict
) -> PipelineUpdated:
    """
    Update pipeline definition.

    Process:
    1. Get pipeline
    2. Validate new pipeline structure
    3. Update pipeline definition
    4. Clear compiled_plan_id (will recompile on next use)

    Args:
        pipeline_id: Pipeline ID
        pipeline_state: New pipeline structure
        visual_state: New visual layout

    Returns:
        PipelineUpdated with pipeline ID

    Raises:
        ObjectNotFoundError: If pipeline not found
        ServiceError: If validation fails or pipeline is in use
    """
    # Get pipeline
    pipeline = self.pipeline_repository.get_by_id(pipeline_id)
    if not pipeline:
        raise ObjectNotFoundError(f"Pipeline {pipeline_id} not found")

    # Check if used by templates (cannot update if finalized)
    is_template_pipeline = self.pipeline_repository.is_used_by_template(
        pipeline_id
    )
    if is_template_pipeline:
        raise ServiceError(
            "Cannot update pipeline associated with finalized template version"
        )

    # Validate new pipeline
    self._validate_pipeline(pipeline_state)

    # Update
    updated = self.pipeline_repository.update(
        pipeline_id,
        PipelineUpdate(
            pipeline_state=pipeline_state,
            visual_state=visual_state,
            compiled_plan_id=None  # Clear - will recompile
        )
    )

    logger.info(f"Updated pipeline {pipeline_id}")

    return PipelineUpdated(
        id=pipeline_id,
        compiled_plan_id=None
    )
```

**Internal calls**: `_validate_pipeline()`

**Repository calls**: `pipeline_repository.get_by_id()`, `pipeline_repository.is_used_by_template()`, `pipeline_repository.update()`

---

### 5. `delete_pipeline(pipeline_id)` → None

**Called by**: Router endpoint `DELETE /pipelines/{id}`

**Purpose**: Delete standalone pipeline

**Implementation**:
```python
def delete_pipeline(self, pipeline_id: int) -> None:
    """
    Delete pipeline definition.

    Validation:
    - Pipeline must exist
    - Pipeline must NOT be used by any template

    Args:
        pipeline_id: Pipeline ID

    Returns:
        None

    Raises:
        ObjectNotFoundError: If pipeline not found
        ServiceError: If pipeline is used by templates
    """
    # Get pipeline
    pipeline = self.pipeline_repository.get_by_id(pipeline_id)
    if not pipeline:
        raise ObjectNotFoundError(f"Pipeline {pipeline_id} not found")

    # Check if used by templates
    is_template_pipeline = self.pipeline_repository.is_used_by_template(
        pipeline_id
    )
    if is_template_pipeline:
        raise ServiceError(
            "Cannot delete pipeline associated with template versions"
        )

    # Delete
    self.pipeline_repository.delete(pipeline_id)

    logger.info(f"Deleted pipeline {pipeline_id}")
```

**Repository calls**: `pipeline_repository.get_by_id()`, `pipeline_repository.is_used_by_template()`, `pipeline_repository.delete()`

---

### 6. `compile_pipeline(pipeline_state, visual_state)` → int

**Called by**: TemplateManagementService (NOT by router)

**Purpose**: Compile pipeline and return pipeline definition ID

**Implementation**:
```python
def compile_pipeline(
    self,
    pipeline_state: dict,
    visual_state: dict
) -> int:
    """
    Compile pipeline definition and return pipeline_definition_id.

    Process:
    1. Validate pipeline
    2. Compile to Dask DAG
    3. Check for existing identical compiled plan (deduplication)
    4. Create pipeline_definition record
    5. Create or reuse compiled_plan record
    6. Update pipeline with compiled_plan_id

    Used by Template Management Service during template creation.

    Args:
        pipeline_state: Pipeline logical structure
        visual_state: Pipeline visual layout

    Returns:
        Pipeline definition ID

    Raises:
        ServiceError: If validation or compilation fails
    """
    with self.connection_manager.unit_of_work() as uow:
        # Validate
        self._validate_pipeline(pipeline_state)

        # Compile to Dask DAG
        dask_dag = self.dask_compiler.compile(pipeline_state)

        # Check for existing identical plan (deduplication)
        dag_hash = self._hash_dag(dask_dag)
        existing_plan = uow.compiled_plans.get_by_hash(dag_hash)

        if existing_plan:
            # Reuse existing plan
            compiled_plan_id = existing_plan.id
            logger.debug(f"Reusing compiled plan {compiled_plan_id}")
        else:
            # Create new plan
            plan_create = CompiledPlanCreate(
                dask_dag=dask_dag,
                dag_hash=dag_hash
            )
            compiled_plan = uow.compiled_plans.create(plan_create)
            compiled_plan_id = compiled_plan.id
            logger.debug(f"Created compiled plan {compiled_plan_id}")

        # Create pipeline definition
        pipeline_create = PipelineCreate(
            pipeline_state=pipeline_state,
            visual_state=visual_state,
            compiled_plan_id=compiled_plan_id
        )

        pipeline = uow.pipelines.create(pipeline_create)

        logger.info(
            f"Compiled pipeline {pipeline.id} "
            f"(compiled plan {compiled_plan_id})"
        )

        return pipeline.id
```

**Internal calls**: `_validate_pipeline()`, `_hash_dag()`

**Repository calls**: `uow.compiled_plans.get_by_hash()`, `uow.compiled_plans.create()`, `uow.pipelines.create()`

**Transaction**: Uses Unit of Work

**Note**: This is the main compilation method used by templates

---

### 7. `execute_pipeline(pipeline_id, input_data)` → PipelineExecutionResult

**Called by**: EtoProcessingService._execute_pipeline() (NOT by router)

**Purpose**: Execute pipeline with real data

**Implementation**:
```python
def execute_pipeline(
    self,
    pipeline_id: int,
    input_data: dict[str, Any]
) -> PipelineExecutionResult:
    """
    Execute pipeline with input data.

    Process:
    1. Get pipeline and compiled plan
    2. If not compiled, compile now
    3. Execute Dask DAG with input data
    4. Collect step results and action executions
    5. Return execution result

    Used by ETO Processing Service during ETO runs.

    Args:
        pipeline_id: Pipeline definition ID
        input_data: Input data dict (field_label → value)

    Returns:
        PipelineExecutionResult with steps, actions, success status

    Raises:
        ObjectNotFoundError: If pipeline not found
        ServiceError: If execution fails
    """
    # Get pipeline
    pipeline = self.pipeline_repository.get_by_id(pipeline_id)
    if not pipeline:
        raise ObjectNotFoundError(f"Pipeline {pipeline_id} not found")

    # Get or create compiled plan
    if not pipeline.compiled_plan_id:
        # Compile on first use
        dask_dag = self.dask_compiler.compile(pipeline.pipeline_state)

        dag_hash = self._hash_dag(dask_dag)
        existing_plan = self.compiled_plan_repository.get_by_hash(dag_hash)

        if existing_plan:
            compiled_plan_id = existing_plan.id
        else:
            plan = self.compiled_plan_repository.create(
                CompiledPlanCreate(dask_dag=dask_dag, dag_hash=dag_hash)
            )
            compiled_plan_id = plan.id

        # Update pipeline
        self.pipeline_repository.update(
            pipeline_id,
            PipelineUpdate(compiled_plan_id=compiled_plan_id)
        )

        compiled_plan = self.compiled_plan_repository.get_by_id(compiled_plan_id)
    else:
        compiled_plan = self.compiled_plan_repository.get_by_id(
            pipeline.compiled_plan_id
        )

    # Execute DAG
    try:
        execution_result = self._execute_dask_dag(
            compiled_plan.dask_dag,
            input_data,
            simulate_actions=False
        )

        logger.info(
            f"Executed pipeline {pipeline_id}: "
            f"{len(execution_result.steps)} steps, "
            f"{len(execution_result.executed_actions)} actions"
        )

        return execution_result

    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}", exc_info=True)
        return PipelineExecutionResult(
            success=False,
            steps=[],
            executed_actions=[],
            error_message=str(e)
        )
```

**Internal calls**: `_hash_dag()`, `_execute_dask_dag()`

**Repository calls**: `pipeline_repository.get_by_id()`, `compiled_plan_repository.get_by_hash()`, `compiled_plan_repository.create()`, `pipeline_repository.update()`, `compiled_plan_repository.get_by_id()`

---

### 8. `simulate_pipeline(pipeline_state, input_data)` → PipelineExecutionResult

**Called by**: TemplateManagementService.simulate_template() (NOT by router)

**Purpose**: Simulate pipeline without persistence

**Implementation**:
```python
def simulate_pipeline(
    self,
    pipeline_state: dict,
    input_data: dict[str, Any]
) -> PipelineExecutionResult:
    """
    Simulate pipeline execution without persistence.

    Process:
    1. Validate pipeline
    2. Compile to Dask DAG (in-memory)
    3. Execute with action modules simulated
    4. Return execution result

    Used by Template Management Service during template testing.

    Args:
        pipeline_state: Pipeline definition (not yet persisted)
        input_data: Input data dict

    Returns:
        PipelineExecutionResult with simulation results

    Raises:
        ServiceError: If simulation fails
    """
    try:
        # Validate
        self._validate_pipeline(pipeline_state)

        # Compile (in-memory)
        dask_dag = self.dask_compiler.compile(pipeline_state)

        # Execute with action simulation
        execution_result = self._execute_dask_dag(
            dask_dag,
            input_data,
            simulate_actions=True
        )

        logger.info(
            f"Simulated pipeline: "
            f"{len(execution_result.steps)} steps, "
            f"{len(execution_result.executed_actions)} actions (simulated)"
        )

        return execution_result

    except Exception as e:
        logger.error(f"Pipeline simulation failed: {e}", exc_info=True)
        return PipelineExecutionResult(
            success=False,
            steps=[],
            executed_actions=[],
            error_message=str(e)
        )
```

**Internal calls**: `_validate_pipeline()`, `_execute_dask_dag()`

---

**Internal Methods**:

### `_validate_pipeline(pipeline_state)` → None

```python
def _validate_pipeline(self, pipeline_state: dict) -> None:
    """
    Validate pipeline structure.

    Checks:
    - All module references exist in catalog
    - All connections are valid (from_node exists, to_node exists)
    - No cycles in graph
    - Entry points are valid
    - Module configurations match schemas

    Raises:
        ServiceError: If validation fails
    """
    # Get all modules from catalog
    catalog_modules = self.module_catalog_service.get_all_modules()
    catalog_ids = {m.id for m in catalog_modules}

    # Validate module references
    for module_instance in pipeline_state.get("modules", []):
        module_id = module_instance.get("module_id")
        if module_id not in catalog_ids:
            raise ServiceError(
                f"Unknown module '{module_id}' in pipeline"
            )

        # Validate config against module schema
        module_def = next(m for m in catalog_modules if m.id == module_id)
        config = module_instance.get("config", {})

        self.module_catalog_service.validate_config(module_id, config)

    # Validate connections
    # ... additional validation logic
```

### `_hash_dag(dask_dag)` → str

```python
def _hash_dag(self, dask_dag: dict) -> str:
    """
    Calculate hash of Dask DAG for deduplication.

    Args:
        dask_dag: Compiled Dask DAG

    Returns:
        SHA-256 hash string
    """
    import hashlib
    import json

    # Serialize DAG deterministically
    dag_json = json.dumps(dask_dag, sort_keys=True)

    # Hash
    return hashlib.sha256(dag_json.encode()).hexdigest()
```

### `_execute_dask_dag(dask_dag, input_data, simulate_actions)` → PipelineExecutionResult

```python
def _execute_dask_dag(
    self,
    dask_dag: dict,
    input_data: dict[str, Any],
    simulate_actions: bool
) -> PipelineExecutionResult:
    """
    Execute Dask DAG with input data.

    Args:
        dask_dag: Compiled Dask DAG
        input_data: Input data
        simulate_actions: If True, action modules return simulation info instead of executing

    Returns:
        PipelineExecutionResult with step-by-step execution trace
    """
    import dask

    try:
        # Execute DAG
        # This is where the actual Dask execution happens
        # Collect step results, action executions, etc.

        steps = []
        executed_actions = []

        # ... Dask execution logic ...

        return PipelineExecutionResult(
            success=True,
            steps=steps,
            executed_actions=executed_actions,
            error_message=None
        )

    except Exception as e:
        logger.error(f"DAG execution error: {e}")
        raise
```

---

**Dataclasses Used**:

**Input types** (from `shared/types/`):
- `PipelineCreate` - Data for creating pipeline
- `PipelineUpdate` - Data for updating pipeline
- `CompiledPlanCreate` - Data for creating compiled plan

**Output types** (from `shared/types/`):
- `PipelineListResult` - Paginated list result
- `PipelineSummary` - Summary for list view
- `PipelineDetail` - Full pipeline with states
- `PipelineCreated` - Response for create
- `PipelineUpdated` - Response for update
- `PipelineExecutionResult` - Execution result with steps and actions

---

**API Integration**:

**Router depends on this service for these endpoints:**
- `GET /pipelines` → `list_pipelines()`
- `GET /pipelines/{id}` → `get_pipeline()`
- `POST /pipelines` → `create_pipeline()`
- `PUT /pipelines/{id}` → `update_pipeline()`
- `DELETE /pipelines/{id}` → `delete_pipeline()`

**Template Management Service calls this service:**
- `compile_pipeline()` - Compile pipeline during template creation
- `simulate_pipeline()` - Simulate pipeline during template testing

**ETO Processing Service calls this service:**
- `execute_pipeline()` - Execute pipeline during ETO runs

**Router dependency injection:**
```python
@router.post("")
def create_pipeline(
    request: CreatePipelineRequest,
    pipeline_service: PipelineService = Depends(
        lambda: ServiceContainer.get_pipeline_service()
    )
) -> CreatePipelineResponse:
    pipeline = pipeline_service.create_pipeline(
        pipeline_state=request.pipeline_state,
        visual_state=request.visual_state
    )

    return CreatePipelineResponse(...)
```

---

## Service 7: Module Catalog Service

**Location**: `server-new/src/features/module_catalog/service.py`

**Purpose**: Provides discovery, registration, and metadata management for pipeline transformation modules. Maintains a catalog of available modules with their schemas, parameters, and capabilities. Handles module validation and compatibility checking. Serves as the authoritative source for module information used by the Pipeline Service during pipeline construction and validation.

**Dependencies**:
- `DatabaseConnectionManager` - Database connection management
- `ModuleCatalogRepository` - Module catalog data access

**Responsibilities**:
- Provide complete module catalog for pipeline builder UI
- Filter modules by kind, category, or search query
- Validate module configurations against JSON schemas
- Return module metadata (I/O definitions, config schemas, display info)
- Support pipeline construction with module information

---

### Constructor

```python
def __init__(
    self,
    connection_manager: DatabaseConnectionManager
):
    """
    Initialize module catalog service

    Args:
        connection_manager: Database connection manager
    """
    self.connection_manager = connection_manager
    self.module_repository = ModuleCatalogRepository(
        connection_manager=connection_manager
    )

    logger.info("ModuleCatalogService initialized")
```

---

### Public Methods

#### 1. `get_all_modules()` - Get filtered module catalog

```python
def get_all_modules(
    self,
    module_kind: str | None = None,
    category: str | None = None,
    search: str | None = None
) -> list[ModuleDetail]:
    """
    Get all active modules with optional filtering.

    Returns complete module catalog for pipeline builder UI.
    No pagination - returns all active modules in single request for frontend caching.
    Frontend can cache this result and use it offline for pipeline construction.

    Args:
        module_kind: Filter by module kind (transform, action, logic, entry_point)
        category: Filter by category (e.g., "Text Processing", "Data Validation")
        search: Text search on name and description (case-insensitive)

    Returns:
        List of ModuleDetail with all metadata, I/O definitions, and config schemas

    Raises:
        ServiceError: If database query fails

    Called by:
        - Router: GET /modules
    """
    try:
        logger.info(
            f"Getting module catalog "
            f"(kind={module_kind}, category={category}, search={search})"
        )

        # Get all active modules
        all_modules = self.module_repository.get_all_active()

        logger.debug(f"Retrieved {len(all_modules)} active modules")

        # Apply filters
        filtered_modules = self._filter_modules(
            modules=all_modules,
            module_kind=module_kind,
            category=category,
            search=search
        )

        logger.info(
            f"Returning {len(filtered_modules)} modules after filtering"
        )

        return filtered_modules

    except Exception as e:
        logger.error(f"Error getting module catalog: {e}", exc_info=True)
        raise ServiceError(f"Failed to get module catalog: {str(e)}") from e
```

---

#### 2. `validate_config()` - Validate module configuration

```python
def validate_config(
    self,
    module_id: str,
    config: dict
) -> bool:
    """
    Validate module configuration against module's JSON schema.

    Used by Pipeline Service during pipeline compilation to ensure
    all module configurations are valid before creating pipeline.

    Args:
        module_id: Module identifier (e.g., "string_concat", "send_email")
        config: Module configuration dictionary to validate

    Returns:
        True if configuration is valid

    Raises:
        ObjectNotFoundError: If module does not exist
        ValueError: If configuration is invalid (with details)
        ServiceError: If validation process fails

    Called by:
        - Pipeline Service: compile_pipeline() - During pipeline compilation

    Example:
        # Validate a string_concat module configuration
        is_valid = module_catalog_service.validate_config(
            module_id="string_concat",
            config={"separator": " "}
        )
    """
    try:
        logger.debug(f"Validating config for module '{module_id}'")

        # Get module (including schema)
        module = self.module_repository.get_by_id(module_id)

        if not module:
            raise ObjectNotFoundError(f"Module '{module_id}' not found")

        # Validate config against schema
        self._validate_against_schema(
            config=config,
            schema=module.config_schema,
            module_id=module_id
        )

        logger.debug(f"Config validation passed for module '{module_id}'")
        return True

    except ObjectNotFoundError:
        raise

    except ValueError:
        # Re-raise validation errors as-is
        raise

    except Exception as e:
        logger.error(
            f"Error validating config for module '{module_id}': {e}",
            exc_info=True
        )
        raise ServiceError(
            f"Failed to validate module configuration: {str(e)}"
        ) from e
```

---

### Internal Methods

#### 1. `_filter_modules()` - Apply filters to module list

```python
def _filter_modules(
    self,
    modules: list[ModuleDetail],
    module_kind: str | None,
    category: str | None,
    search: str | None
) -> list[ModuleDetail]:
    """
    Apply filters to module list.

    Filters are applied server-side to reduce payload size and improve performance.
    All filters are optional and can be combined.

    Args:
        modules: Complete list of active modules
        module_kind: Filter by module kind (exact match)
        category: Filter by category (exact match)
        search: Text search on name/description (case-insensitive partial match)

    Returns:
        Filtered list of modules
    """
    filtered = modules

    # Filter by module_kind
    if module_kind:
        filtered = [m for m in filtered if m.module_kind == module_kind]
        logger.debug(f"After module_kind filter: {len(filtered)} modules")

    # Filter by category
    if category:
        filtered = [m for m in filtered if m.category == category]
        logger.debug(f"After category filter: {len(filtered)} modules")

    # Filter by search (name + description)
    if search:
        search_lower = search.lower()
        filtered = [
            m for m in filtered
            if search_lower in m.name.lower()
            or search_lower in (m.description or "").lower()
        ]
        logger.debug(f"After search filter: {len(filtered)} modules")

    return filtered
```

---

#### 2. `_validate_against_schema()` - Validate config against JSON Schema

```python
def _validate_against_schema(
    self,
    config: dict,
    schema: dict,
    module_id: str
) -> None:
    """
    Validate configuration dictionary against JSON Schema.

    Uses jsonschema library to validate module configuration.
    Raises detailed error messages for invalid configurations.

    Args:
        config: Configuration dictionary to validate
        schema: JSON Schema definition
        module_id: Module identifier (for error messages)

    Raises:
        ValueError: If configuration does not match schema

    Implementation:
        import jsonschema
        from jsonschema import ValidationError

        try:
            jsonschema.validate(instance=config, schema=schema)
        except ValidationError as e:
            # Extract useful error information
            error_path = " → ".join(str(p) for p in e.path)
            raise ValueError(
                f"Invalid configuration for module '{module_id}': "
                f"{e.message} (at {error_path or 'root'})"
            )
    """
    import jsonschema
    from jsonschema import ValidationError

    try:
        jsonschema.validate(instance=config, schema=schema)

    except ValidationError as e:
        # Build readable error path (e.g., "inputs → separator → type")
        error_path = " → ".join(str(p) for p in e.path) if e.path else "root"

        raise ValueError(
            f"Invalid configuration for module '{module_id}': "
            f"{e.message} (at {error_path})"
        )

    except Exception as e:
        # Handle schema-related errors (malformed schema, etc.)
        logger.error(
            f"Schema validation error for module '{module_id}': {e}",
            exc_info=True
        )
        raise ValueError(
            f"Schema validation failed for module '{module_id}': {str(e)}"
        )
```

---

**Dataclasses Used**:

**Output types** (from `shared/types/`):
- `ModuleDetail` - Complete module information with metadata, I/O, and schema

---

**API Integration**:

**Router depends on this service for these endpoints:**
- `GET /modules` → `get_all_modules()`

**Pipeline Service calls this service:**
- `validate_config()` - Validate module configurations during compilation

**Router dependency injection:**
```python
@router.get("", response_model=list[ModuleDetail])
def list_modules(
    module_kind: str | None = None,
    category: str | None = None,
    search: str | None = None,
    module_catalog_service: ModuleCatalogService = Depends(
        lambda: ServiceContainer.get_module_catalog_service()
    )
) -> list[ModuleDetail]:
    """List all active modules with optional filtering"""

    modules = module_catalog_service.get_all_modules(
        module_kind=module_kind,
        category=category,
        search=search
    )

    return modules
```

---

## Transaction Management Patterns

We use the **Unit of Work (UoW)** pattern for transaction management. This provides clean separation between single-operation calls and multi-table transactions without requiring duplicate repository methods.

### Core Concept

- **Unit of Work**: Manages a database transaction and provides access to all repositories within that transaction
- **Single Implementation**: Each repository method has ONE implementation that works both standalone and in transactions
- **Explicit Transactions**: Services explicitly show when operations need to be atomic via `unit_of_work()` context manager

### Architecture Components

#### 1. Unit of Work Class

**Location**: `shared/database/unit_of_work.py`

```python
class UnitOfWork:
    """
    Unit of Work manages a transaction and provides repository access.
    All repositories within this UoW share the same session.
    """

    def __init__(self, session: Session):
        self.session = session

        # Lazy-load repositories as needed
        self._template_repository = None
        self._template_version_repository = None
        self._pdf_repository = None
        self._email_config_repository = None
        # ... add properties for each repository

    @property
    def templates(self) -> TemplateRepository:
        """Access to template repository within this transaction"""
        if not self._template_repository:
            self._template_repository = TemplateRepository(session=self.session)
        return self._template_repository

    @property
    def template_versions(self) -> TemplateVersionRepository:
        """Access to template version repository within this transaction"""
        if not self._template_version_repository:
            self._template_version_repository = TemplateVersionRepository(session=self.session)
        return self._template_version_repository

    @property
    def pdfs(self) -> PdfRepository:
        """Access to PDF repository within this transaction"""
        if not self._pdf_repository:
            self._pdf_repository = PdfRepository(session=self.session)
        return self._pdf_repository

    # ... add property for each repository

    def commit(self):
        """Manually commit transaction (usually not needed - context manager handles this)"""
        self.session.commit()

    def rollback(self):
        """Manually rollback transaction (usually not needed - context manager handles this)"""
        self.session.rollback()
```

#### 2. ConnectionManager Integration

**Location**: `shared/database/connection.py`

```python
class DatabaseConnectionManager:

    @contextmanager
    def unit_of_work(self) -> UnitOfWork:
        """
        Create a Unit of Work with automatic transaction management.
        Auto-commits on success, auto-rolls back on exception.

        Usage:
            with connection_manager.unit_of_work() as uow:
                result1 = uow.templates.create(data1)
                result2 = uow.template_versions.create(data2)
                # Both commit together automatically
        """
        session = self.session_factory()
        uow = UnitOfWork(session)
        try:
            yield uow
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
```

#### 3. Repository Base Class

**Location**: `shared/database/repositories/base_repository.py`

```python
class BaseRepository:
    """
    Base repository that works both standalone and within Unit of Work.
    """

    def __init__(
        self,
        session: Optional[Session] = None,
        connection_manager: Optional[DatabaseConnectionManager] = None
    ):
        """
        Initialize repository.

        Args:
            session: If provided, use this session (we're in a UoW)
            connection_manager: If no session, use this to create sessions per-operation

        Note: Either session OR connection_manager must be provided
        """
        if session is None and connection_manager is None:
            raise ValueError("Must provide either session or connection_manager")

        self.session = session
        self.connection_manager = connection_manager
        self._owns_session = session is None

    @contextmanager
    def _get_session(self):
        """
        Get session for an operation.
        If we have a session (in UoW), use it.
        Otherwise create a new session for this operation.
        """
        if self.session:
            # We're in a UoW - use the UoW's session
            # Don't commit - UoW will handle that
            yield self.session
        else:
            # Standalone operation - create our own session
            with self.connection_manager.session() as session:
                yield session
                # Session auto-commits on context exit
```

#### 4. Concrete Repository Implementation

**Example**: `shared/database/repositories/template_repository.py`

```python
class TemplateRepository(BaseRepository):
    """
    Template repository with methods that work both standalone and in transactions.
    Each method has ONE implementation.
    """

    def create(self, data: TemplateCreate) -> Template:
        """
        Create template record.
        Works standalone OR within a Unit of Work transaction.
        """
        with self._get_session() as session:
            orm_model = TemplateORM(
                name=data.name,
                description=data.description,
                created_at=datetime.now(timezone.utc),
                # ... other fields
            )
            session.add(orm_model)
            session.flush()  # Get ID without committing
            session.refresh(orm_model)  # Load any DB-generated fields
            return self._to_dataclass(orm_model)

    def get_by_id(self, template_id: int) -> Optional[Template]:
        """
        Get template by ID.
        Works standalone OR within a Unit of Work transaction.
        """
        with self._get_session() as session:
            orm_model = session.get(TemplateORM, template_id)
            if not orm_model:
                return None
            return self._to_dataclass(orm_model)

    def update(self, template_id: int, data: TemplateUpdate) -> Template:
        """
        Update template.
        Works standalone OR within a Unit of Work transaction.
        """
        with self._get_session() as session:
            orm_model = session.get(TemplateORM, template_id)
            if not orm_model:
                raise ObjectNotFoundError(f"Template {template_id} not found")

            # Update fields
            for field, value in data.dict(exclude_unset=True).items():
                setattr(orm_model, field, value)

            session.flush()
            session.refresh(orm_model)
            return self._to_dataclass(orm_model)

    def _to_dataclass(self, orm_model: TemplateORM) -> Template:
        """Convert ORM model to dataclass"""
        return Template(
            id=orm_model.id,
            name=orm_model.name,
            description=orm_model.description,
            # ... map all fields
        )
```

### Usage Patterns

#### Pattern 1: Multi-Table Transaction (Use Unit of Work)

**Use Case**: Operations that span multiple tables and must be atomic (e.g., creating template + initial version)

**Service Implementation**:
```python
class TemplateService:
    def __init__(self, connection_manager: DatabaseConnectionManager):
        self.connection_manager = connection_manager

        # For standalone operations
        self.template_repository = TemplateRepository(connection_manager=connection_manager)
        self.version_repository = TemplateVersionRepository(connection_manager=connection_manager)

    def create_template(self, template_data: TemplateCreate) -> Template:
        """
        Create template with initial version.
        Multi-table transaction - if either fails, both rollback.
        """
        with self.connection_manager.unit_of_work() as uow:
            # Create template using UoW's repository
            template = uow.templates.create(template_data)

            # Create initial version using UoW's repository
            version_data = TemplateVersionCreate(
                template_id=template.id,
                version_number=1,
                is_active=True,
                created_by=template_data.created_by
            )
            version = uow.template_versions.create(version_data)

            # Both operations commit together automatically
            return template

        # If any exception occurs, both operations roll back
```

**Complex Example**:
```python
def activate_template_version(
    self,
    template_id: int,
    version_id: int
) -> TemplateVersion:
    """
    Activate a template version.
    Must: deactivate old version + activate new version + update template reference
    All must happen atomically.
    """
    with self.connection_manager.unit_of_work() as uow:
        # Step 1: Get current active version
        current_active = uow.template_versions.get_active_version(template_id)

        # Step 2: Deactivate old version if exists
        if current_active:
            uow.template_versions.update(
                current_active.id,
                TemplateVersionUpdate(is_active=False)
            )

        # Step 3: Activate new version
        new_version = uow.template_versions.update(
            version_id,
            TemplateVersionUpdate(is_active=True)
        )

        # Step 4: Update template's active_version_id
        uow.templates.update(
            template_id,
            TemplateUpdate(active_version_id=version_id)
        )

        # All 4 operations commit together
        return new_version
```

#### Pattern 2: Single Repository Operation (No Unit of Work)

**Use Case**: Simple CRUD operations on a single table

**Service Implementation**:
```python
def get_template(self, template_id: int) -> Optional[Template]:
    """
    Simple read operation - no transaction needed.
    Uses service's standalone repository.
    """
    return self.template_repository.get_by_id(template_id)

def list_templates(self) -> list[Template]:
    """
    Simple query operation - no transaction needed.
    """
    return self.template_repository.get_all()

def update_template_name(self, template_id: int, new_name: str) -> Template:
    """
    Single-table update - no transaction needed.
    Repository auto-commits this operation.
    """
    return self.template_repository.update(
        template_id,
        TemplateUpdate(name=new_name)
    )
```

#### Pattern 3: Error Handling and Rollback

**Use Case**: Complex validation that might fail partway through

**Service Implementation**:
```python
def create_template_with_validation(
    self,
    template_data: TemplateCreate
) -> Template:
    """
    Create template with complex business validation.
    If validation fails, transaction rolls back automatically.
    """
    try:
        with self.connection_manager.unit_of_work() as uow:
            # Business rule validation
            existing = uow.templates.get_by_name(template_data.name)
            if existing:
                raise ServiceError(f"Template '{template_data.name}' already exists")

            # Create template
            template = uow.templates.create(template_data)

            # More validation
            if not self._validate_template_structure(template):
                raise ServiceError("Invalid template structure")

            # Create version
            version_data = TemplateVersionCreate(
                template_id=template.id,
                version_number=1,
                is_active=True
            )
            uow.template_versions.create(version_data)

            # Success - auto-commits
            return template

    except ServiceError:
        # Business logic errors - let them bubble up (already rolled back)
        raise
    except Exception as e:
        # Unexpected errors
        logger.error(f"Error creating template: {e}", exc_info=True)
        raise ServiceError(f"Failed to create template: {str(e)}") from e
```

#### Pattern 4: Read-Only Queries (No Transaction Needed)

**Use Case**: Queries that don't modify data and don't need consistency across multiple reads

**Service Implementation**:
```python
def get_template_statistics(self, template_id: int) -> TemplateStatistics:
    """
    Gather statistics from multiple repositories.
    No consistency requirements - each query can be independent.
    """
    # Each repository call uses its own session
    template = self.template_repository.get_by_id(template_id)
    if not template:
        raise ObjectNotFoundError(f"Template {template_id} not found")

    version_count = self.version_repository.count_by_template(template_id)
    usage_count = self.eto_run_repository.count_by_template(template_id)

    return TemplateStatistics(
        template_id=template_id,
        version_count=version_count,
        usage_count=usage_count
    )
```

### Key Benefits

1. **Single Implementation**: Each repository method has ONE implementation (no duplication)
2. **Works Both Ways**: Same methods work standalone OR in transactions
3. **Explicit Transactions**: Service code clearly shows what needs to be atomic
4. **Automatic Rollback**: Context manager handles rollback on any exception
5. **Well-Established Pattern**: Unit of Work is proven in enterprise applications
6. **Clean Code**: No boilerplate, methods look natural

### Guidelines

**Use Unit of Work when:**
- Creating/updating multiple related records that must be atomic
- Complex operations with validation between steps
- Operations where partial success is unacceptable

**Use standalone repository when:**
- Simple single-record CRUD operations
- Read-only queries
- Operations where each step can succeed independently

---

## Service Dependencies Graph

```
[To be filled in with dependency relationships between services]
```

---

## ServiceContainer Registration

**Location**: `server-new/src/shared/services/service_container.py`

**Registration Order**:

```python
[To be filled in with service registration methods]
```

---

## Notes

- All services follow the same architectural pattern
- Services use dependency injection for testability
- Each service is responsible for its own transaction management
- Cross-service operations are coordinated by the calling service
