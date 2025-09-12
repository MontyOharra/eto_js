# ETO Server Architecture

This document outlines the complete architecture of the unified ETO server, including structural organization, coding conventions, and implementation patterns.

## Project Structure

The ETO server follows a **feature-based architecture** with clean separation of concerns:

```
eto_server/
├── src/
│   ├── shared/                    # Cross-cutting concerns
│   │   ├── database/              # Database infrastructure
│   │   │   ├── connection.py      # Connection management
│   │   │   ├── models.py          # SQLAlchemy models
│   │   │   └── repositories/      # Data access layer
│   │   ├── types/                 # Shared domain types
│   │   └── orchestration/         # System orchestration
│   │
│   ├── features/                  # Business features
│   │   ├── email_configuration/   # Email ingestion config
│   │   │   ├── types.py           # Feature domain objects
│   │   │   └── service.py         # Business logic
│   │   ├── email_processing/      # Email processing
│   │   ├── template_management/   # PDF templates
│   │   └── eto_processing/        # ETO run processing
│   │
│   └── api/                       # REST API layer
│       ├── schemas/               # Pydantic validation
│       ├── blueprints/            # Flask route handlers
│       └── app.py                 # Flask application
│
├── scripts/                       # Operational scripts
└── main.py                        # Application entry point
```

## Architectural Layers

### 1. **Shared Infrastructure Layer** (`src/shared/`)

#### Database Layer
- **Connection Management**: `DatabaseConnectionManager` with session lifecycle
- **Models**: SQLAlchemy ORM models with proper relationships
- **Repositories**: Data access objects returning SQLAlchemy models
- **Base Repository**: Generic CRUD operations with type safety

#### Types Layer
- **Common Types**: Shared domain objects and enums
- **Feature Types**: Cross-feature domain objects

### 2. **Feature Layer** (`src/features/`)

Each feature is self-contained with:
- **Domain Types**: Feature-specific domain objects (dataclasses)
- **Service Layer**: Business logic and orchestration
- **Clean Dependencies**: Features depend only on shared layer

### 3. **API Layer** (`src/api/`)

- **Schemas**: Pydantic models for request/response validation
- **Blueprints**: Flask route handlers with minimal business logic
- **Application Factory**: Flask app configuration and initialization

## Coding Conventions

### Repository Pattern

**Purpose**: Repositories handle data access and return SQLAlchemy models.

```python
class EmailIngestionConfigRepository(BaseRepository[EmailIngestionConfigModel]):
    def get_active_config(self) -> Optional[EmailIngestionConfigModel]:
        """Get currently active configuration"""
        try:
            with self.connection_manager.session_scope() as session:
                config = session.query(self.model_class).filter(
                    self.model_class.is_active == True
                ).first()
                
                if not config:
                    return None
                
                # Force load all attributes while session is active
                _ = config.filter_rules  # Load relationships
                _ = config.name
                
                # Remove from session but keep loaded data
                session.expunge(config)
                return config
```

**Key Patterns**:
- Return SQLAlchemy models, not domain objects
- Use `session.expunge()` for detached objects
- Force-load relationships before detaching
- Handle session scope within repository methods

### Service Layer Pattern

**Purpose**: Services handle business logic and model-to-domain conversion.

```python
class EmailConfigurationService:
    def get_active_configuration(self) -> Optional[EmailIngestionConfig]:
        """Get currently active configuration as domain object"""
        config_model = self.config_repo.get_active_config()
        
        if not config_model:
            return None
        
        return self._convert_to_domain_object(config_model)
    
    def _convert_to_domain_object(self, config_model: EmailIngestionConfigModel) -> EmailIngestionConfig:
        """Convert database model to domain object. Must be called within session scope."""
        # Extract all values to force SQLAlchemy type evaluation
        config_data = {
            'id': config_model.id,                    # Column[int] -> int
            'name': config_model.name,                # Column[str] -> str
            'is_active': config_model.is_active,      # Column[bool] -> bool
            'filter_rules': [
                EmailFilterRule(
                    field=rule.field,
                    operation=rule.operation,
                    value=rule.value,
                    case_sensitive=rule.case_sensitive
                ) for rule in config_model.filter_rules
            ],
            # ... all other fields
        }
        return EmailIngestionConfig(**config_data)
```

**Key Patterns**:
- Services call repositories and convert models to domain objects
- Use dictionary extraction to avoid `Column[Type]` IDE warnings
- Access relationships while models are still attached to session
- Domain objects are pure Python dataclasses

### Atomic Operations Pattern

**Purpose**: Complex operations should be atomic and encapsulated in repositories.

```python
# Repository Layer - Atomic Operation
def delete_if_inactive(self, config_id: int) -> Dict[str, Any]:
    """Delete configuration only if it's not active. Returns result with name for logging."""
    try:
        with self.connection_manager.session_scope() as session:
            # Get config to check if it exists and is not active
            config = session.query(self.model_class).get(config_id)
            
            if not config:
                return {"success": False, "message": f"Configuration with ID {config_id} not found"}
            
            # Extract values while still in session
            is_active = config.is_active
            config_name = config.name
            
            if is_active:
                return {"success": False, "message": "Cannot delete active configuration"}
            
            # Delete the configuration
            session.delete(config)
            session.commit()
            
            return {"success": True, "name": config_name}
```

```python
# Service Layer - Simple Orchestration
def delete_configuration(self, config_id: int) -> Dict[str, Any]:
    """Delete an email ingestion configuration"""
    result = self.config_repo.delete_if_inactive(config_id)
    
    if not result["success"]:
        raise Exception(result["message"])
    
    return {
        "success": True,
        "config_id": config_id,
        "name": result["name"],
        "message": "Configuration deleted successfully"
    }
```

**Benefits**:
- Single database transaction
- No race conditions
- Clear separation of data operations vs business logic

### API Layer Pattern

**Purpose**: APIs handle HTTP concerns and delegate to services.

```python
@email_ingestion_bp.route('/configurations/active', methods=['GET'])
@cross_origin()
def get_active_configuration():
    """Get currently active email ingestion configuration"""
    try:
        config = config_service.get_active_configuration()
        
        if not config:
            return jsonify({
                "success": False,
                "error": "No active configuration found",
                "message": "No configuration is currently active"
            }), 404
        
        # Convert domain object to response schema
        config_response = EmailConfigDetailResponse(
            id=config.id,
            name=config.name,
            is_active=config.is_active,
            # ... all fields
        )
        
        return jsonify({
            "success": True,
            "data": config_response.dict()
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting active configuration: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to get active configuration"
        }), 500
```

**Key Patterns**:
- Minimal business logic in API handlers
- Consistent error response format
- Pydantic schema validation for requests/responses
- Service layer handles all business logic

## Type Safety and IDE Conventions

### Avoiding SQLAlchemy Column Type Warnings

**Problem**: SQLAlchemy model attributes return `Column[Type]` which causes IDE warnings.

**Solution**: Extract values into dictionaries before using them.

```python
# ❌ Direct access causes IDE warnings
domain_object = DomainObject(
    id=model.id,           # Column[int] assigned to int field
    name=model.name        # Column[str] assigned to str field  
)

# ✅ Extract values first
data = {
    'id': model.id,        # Column[int] -> int
    'name': model.name     # Column[str] -> str
}
domain_object = DomainObject(**data)
```

### Domain Object Conventions

```python
@dataclass
class EmailIngestionConfig:
    """Email ingestion configuration domain object"""
    id: Optional[int]
    name: str
    description: Optional[str]
    email_address: Optional[str]
    folder_name: str
    filter_rules: List[EmailFilterRule]
    is_active: bool = True
    created_at: datetime
    updated_at: datetime
    # ... other fields
```

**Characteristics**:
- Pure Python dataclasses
- No database dependencies
- Explicit typing
- Business-focused structure

## Database Architecture

### Connection Management

```python
# Singleton pattern with thread safety
connection_manager = get_connection_manager()

# Session scope management
with connection_manager.session_scope() as session:
    # Automatic transaction management
    # Exception handling with rollback
    pass
```

### Repository Hierarchy

```python
class BaseRepository[T]:
    """Generic base repository with common CRUD operations"""
    
    def create(self, data: Dict[str, Any]) -> T: ...
    def get_by_id(self, id: int) -> Optional[T]: ...
    def update(self, id: int, data: Dict[str, Any]) -> Optional[T]: ...
    def delete(self, id: int) -> bool: ...

class EmailIngestionConfigRepository(BaseRepository[EmailIngestionConfigModel]):
    """Specific repository with business-focused methods"""
    
    def get_active_config(self) -> Optional[EmailIngestionConfigModel]: ...
    def get_all_configs(self) -> List[EmailIngestionConfigModel]: ...
    def set_config_active(self, config_id: int) -> Optional[EmailIngestionConfigModel]: ...
```

## Error Handling Patterns

### Repository Layer
```python
try:
    with self.connection_manager.session_scope() as session:
        # Database operations
        pass
except SQLAlchemyError as e:
    logger.error(f"Database error: {e}")
    raise RepositoryError(f"Failed to perform operation: {e}") from e
```

### Service Layer
```python
try:
    result = self.repository.some_operation()
    return self._convert_to_domain_object(result)
except RepositoryError:
    raise  # Re-raise repository errors
except Exception as e:
    logger.error(f"Service error: {e}")
    raise ServiceError(f"Business logic error: {e}") from e
```

### API Layer
```python
try:
    result = service.business_operation()
    return jsonify({"success": True, "data": result}), 200
except Exception as e:
    logger.error(f"API error: {e}")
    return jsonify({
        "success": False,
        "error": str(e),
        "message": "Operation failed"
    }), 500
```

## Testing Patterns

### Repository Testing
- Test against real database connections
- Use transaction rollback for test isolation
- Mock connection manager for unit tests

### Service Testing
- Mock repository dependencies
- Test domain object conversion
- Verify business logic rules

### API Testing
- Mock service dependencies
- Test HTTP status codes and response formats
- Validate request/response schemas

## Key Design Principles

1. **Feature-Based Organization** - Group related functionality together
2. **Clean Architecture** - Dependencies flow inward (API → Service → Repository → Database)
3. **Single Responsibility** - Each layer has one clear purpose
4. **Type Safety** - Explicit typing throughout with proper IDE support
5. **Atomic Operations** - Complex database operations are transaction-safe
6. **Separation of Concerns** - Clear boundaries between layers
7. **Domain-Driven Design** - Business concepts represented as domain objects
8. **Fail-Fast** - Explicit error handling at each layer
9. **Testability** - Each layer can be tested in isolation

## Implementation Status

**Current Status**: Feature-Based Architecture Complete

- ✅ **Feature-based project structure**
- ✅ **Repository pattern with proper model handling**
- ✅ **Service layer with domain object conversion**
- ✅ **API layer with Pydantic validation**
- ✅ **Type-safe coding conventions**
- ✅ **Atomic operation patterns**
- ✅ **Error handling strategies**
- ✅ **Email ingestion configuration feature complete**
- 🔄 **Additional feature implementations ongoing**