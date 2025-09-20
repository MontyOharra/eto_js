# FastAPI Migration Guide

This document outlines the migration from Flask to FastAPI for the Unified ETO Server, including benefits, implementation details, and migration steps.

## Overview

The ETO Server has been designed with a FastAPI alternative to provide:
- Better type safety and automatic validation
- Automatic OpenAPI documentation
- Better async support
- Modern Python web framework patterns
- Simplified query parameter handling

## Files Structure

### New FastAPI Files
- `src/app-fastapi.py` - FastAPI application factory (equivalent to `src/app.py`)
- `main-fastapi.py` - FastAPI entry point with uvicorn (equivalent to `main.py`)
- `src/api/routers/` - FastAPI routers (equivalent to `src/api/blueprints/`)
- `src/api/routers/pdf_templates.py` - Example converted router

### Dependencies Added
```
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
```

## Key Differences from Flask

### 1. Application Factory Pattern

**Flask (`app.py`):**
```python
def create_app(config_name: str = 'development') -> Flask:
    app = Flask(__name__)
    # Configuration and setup
    return app
```

**FastAPI (`app-fastapi.py`):**
```python
def create_app() -> FastAPI:
    app = FastAPI(
        title="Unified ETO Server",
        description="...",
        version="2.0.0",
        lifespan=lifespan  # Startup/shutdown events
    )
    return app
```

### 2. Startup/Shutdown Management

**Flask:** Uses application context and manual initialization
**FastAPI:** Uses lifespan context manager for clean startup/shutdown:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await initialize_database_connection()
    await initialize_services()
    yield
    # Shutdown
    await cleanup_services()
```

### 3. Route Definition and Validation

**Flask Blueprint:**
```python
@pdf_templates_bp.route('/', methods=['POST'])
@cross_origin()
def create_template():
    try:
        request_data = PdfTemplateCreateRequest(**request.get_json())
    except ValidationError as e:
        return ErrorResponse(...).model_dump_json(), 400
    # ... rest of implementation
```

**FastAPI Router:**
```python
@router.post("/", response_model=PdfTemplateCreateResponse, status_code=201)
async def create_template(request_data: PdfTemplateCreateRequest):
    # Automatic validation, no try/catch needed for validation
    # ... implementation
```

### 4. Query Parameters

**Flask:** Manual conversion and validation:
```python
def convert_query_params(args_dict: Dict[str, str]) -> Dict[str, Any]:
    converted = {}
    for key, value in args_dict.items():
        if key in ['page', 'limit']:
            try:
                converted[key] = int(value)
            except ValueError:
                converted[key] = value
    return converted

request_data = TemplateListRequest(**convert_query_params(request.args.to_dict()))
```

**FastAPI:** Automatic type conversion with dependencies:
```python
def convert_query_params_to_template_list_request(
    status_filter: Optional[str] = Query(None, regex="^(active|inactive)$"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
) -> TemplateListRequest:
    return TemplateListRequest(status=status_filter, page=page, limit=limit)

@router.get("/")
async def list_templates(query_params: TemplateListRequest = Depends(convert_query_params_to_template_list_request)):
    # query_params is automatically validated and typed
```

### 5. Error Handling

**Flask:** Manual JSON responses:
```python
return ErrorResponse(
    error="Validation error",
    message=f"Request validation failed: {e.errors()}"
).model_dump_json(), 400
```

**FastAPI:** HTTP exceptions with automatic JSON serialization:
```python
raise HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail="Request validation failed"
)
```

### 6. CORS Configuration

**Flask:**
```python
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE"],
        # ... more config
    }
})
```

**FastAPI:**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    # ... more config
)
```

## Migration Benefits

### 1. Type Safety
- Automatic request/response validation
- Better IDE support with type hints
- Runtime type checking

### 2. Documentation
- Automatic OpenAPI schema generation
- Interactive Swagger UI at `/docs`
- ReDoc documentation at `/redoc`

### 3. Performance
- Built on Starlette (faster than Flask)
- Native async support
- Better handling of concurrent requests

### 4. Developer Experience
- Less boilerplate code
- Automatic validation error messages
- Better error messages and debugging

### 5. Query Parameter Handling
- Automatic type conversion (no more string-to-int conversion issues)
- Built-in validation with clear error messages
- Dependency injection pattern for reusable parameter sets

## Running the FastAPI Version

### Development
```bash
python main-fastapi.py
```

### Production with Uvicorn
```bash
uvicorn src.app-fastapi:create_app --factory --host 0.0.0.0 --port 8080
```

### Environment Variables
Same as Flask version:
- `DATABASE_URL` - Database connection string
- `PORT` - Server port (default: 8080)
- `HOST` - Server host (default: 0.0.0.0)
- `DEBUG` - Debug mode (default: false)
- `LOG_LEVEL` - Logging level (default: DEBUG)

Additional FastAPI-specific:
- `RELOAD` - Enable auto-reload (default: same as DEBUG)
- `WORKERS` - Number of worker processes (default: 1)

## Migration Steps

### Phase 1: Basic Setup ✅
- [x] Create `app-fastapi.py` with application factory
- [x] Create `main-fastapi.py` entry point
- [x] Add FastAPI dependencies to requirements.txt
- [x] Create example router conversion (PDF templates)

### Phase 2: Router Conversion (TODO)
- [ ] Convert `health_bp` to `health_router`
- [ ] Convert `email_ingestion_bp` to `email_ingestion_router`
- [ ] Convert `eto_processing_bp` to `eto_processing_router`
- [ ] Convert `eto_service_bp` to `eto_service_router`
- [ ] Convert `pdf_viewing_bp` to `pdf_viewing_router`

### Phase 3: Service Integration (TODO)
- [ ] Implement FastAPI dependency injection for services
- [ ] Convert service layer to async (optional)
- [ ] Update error handling patterns

### Phase 4: Testing and Validation (TODO)
- [ ] Test all endpoints with automatic validation
- [ ] Verify OpenAPI documentation accuracy
- [ ] Performance testing and comparison
- [ ] Update client integration

## Example Usage

### Starting the Server
```bash
# Development with auto-reload
DEBUG=true python main-fastapi.py

# Production
python main-fastapi.py
```

### API Documentation
- Swagger UI: http://localhost:8080/docs
- ReDoc: http://localhost:8080/redoc
- OpenAPI JSON: http://localhost:8080/openapi.json

### Example Request
```bash
# Create PDF template - automatic validation
curl -X POST "http://localhost:8080/api/pdf_templates/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Invoice Template",
    "description": "Template for invoice processing",
    "source_pdf_id": 123,
    "selected_objects": [...],
    "extraction_fields": [...]
  }'
```

## Compatibility Notes

- Both Flask and FastAPI versions can coexist
- Same database models and service layer
- Same environment configuration
- Gradual migration possible (run both servers during transition)

## Performance Comparison

FastAPI typically shows:
- 2-3x better performance for API endpoints
- Better memory efficiency
- Improved concurrent request handling
- Faster startup time (with proper async usage)

## Next Steps

1. **Complete Router Conversion**: Convert remaining Flask blueprints to FastAPI routers
2. **Service Layer Updates**: Consider making service layer async for better performance
3. **Testing**: Implement comprehensive testing for FastAPI endpoints
4. **Documentation**: Update API documentation and client integration guides
5. **Deployment**: Update deployment scripts and Docker configurations for FastAPI