# Python Typing Best Practices Guide

## Overview

This guide covers how to use Python type hints effectively in the ETO transformation pipeline project.

## 1. File Organization

### Type Definitions Location
- **Central types file**: `src/types.py` - All shared types, aliases, and protocols
- **Module-specific types**: Within each module for types used only there
- **API types**: In API-related modules for request/response types

### Import Structure
```python
# Standard library types
from typing import Dict, List, Optional, Union, Any, Protocol, TypedDict
from typing import Literal, NotRequired, Generic, TypeVar
from abc import abstractmethod

# Project-specific types
from ..types import ModuleID, ExecutionInputs, ExecutionOutputs
```

## 2. Type Definition Patterns

### A. Type Aliases
Use for commonly used complex types:
```python
# Simple aliases
ModuleID = str
NodeType = Literal['string', 'number', 'boolean', 'datetime']

# Complex aliases
ConfigDict = Dict[str, Union[str, int, bool, List[str]]]
```

### B. TypedDict for Structured Data
Use instead of regular dictionaries for known structures:
```python
class ModuleInfo(TypedDict):
    id: str
    name: str
    description: str
    # Optional fields (Python 3.11+)
    version: NotRequired[str]
    # Or for older Python versions
    version: Optional[str]  # But this allows None, not missing key
```

### C. Protocols for Interface Definitions
Use for duck typing and interface contracts:
```python
class Executable(Protocol):
    @abstractmethod
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        ...
    
    def validate(self, data: Any) -> bool:
        # Default implementation
        return True
```

### D. Literal Types for Constrained Values
```python
from typing import Literal

Status = Literal['active', 'inactive', 'pending']
LogLevel = Literal['DEBUG', 'INFO', 'WARNING', 'ERROR']
```

## 3. Function and Method Typing

### Basic Function Typing
```python
def process_data(items: List[str], max_count: int = 100) -> Dict[str, int]:
    """Process a list of strings and return counts."""
    pass

# With optional parameters
def connect_db(url: str, timeout: Optional[int] = None) -> Connection:
    pass

# With union types
def parse_value(value: Union[str, int, float]) -> str:
    return str(value)
```

### Method Typing in Classes
```python
class DataProcessor:
    def __init__(self, config: ConfigDict) -> None:
        self._config = config
    
    def process(self, data: List[Any]) -> ProcessingResult:
        pass
    
    @classmethod
    def from_config_file(cls, path: str) -> 'DataProcessor':
        # Use quotes for forward references
        pass
```

### Generic Functions
```python
from typing import TypeVar, Generic

T = TypeVar('T')

def get_first_item(items: List[T]) -> Optional[T]:
    return items[0] if items else None

class Container(Generic[T]):
    def __init__(self) -> None:
        self._items: List[T] = []
    
    def add(self, item: T) -> None:
        self._items.append(item)
```

## 4. Error Handling with Types

### Custom Exception Types
```python
class ModuleError(Exception):
    """Base exception for module-related errors"""
    def __init__(self, message: str, module_id: Optional[str] = None) -> None:
        super().__init__(message)
        self.module_id = module_id

class ValidationError(ModuleError):
    """Raised when validation fails"""
    pass
```

### Exception Handling in Typed Functions
```python
def execute_module(module_id: str, inputs: Dict[str, Any]) -> ExecutionResult:
    try:
        # ... execution logic
        return ExecutionResult(success=True, data=result)
    except ValidationError as e:
        logger.error(f"Validation failed: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise ModuleExecutionError(f"Failed to execute {module_id}: {str(e)}")
```

## 5. API Endpoint Typing

### Request/Response Types
```python
class CreateModuleRequest(TypedDict):
    name: str
    description: str
    config: Dict[str, Any]

class ApiResponse(TypedDict):
    success: bool
    message: NotRequired[str]
    error: NotRequired[str]

class ModuleResponse(ApiResponse):
    module: NotRequired[ModuleInfo]

# Flask route with typing
from flask import request, jsonify

@app.post("/api/modules")
def create_module() -> Tuple[Dict[str, Any], int]:
    try:
        data: CreateModuleRequest = request.get_json()
        # ... validation and processing
        
        response: ModuleResponse = {
            "success": True,
            "module": created_module_info
        }
        return response, 201
        
    except ValidationError as e:
        error_response: ApiResponse = {
            "success": False,
            "error": str(e)
        }
        return error_response, 400
```

## 6. Database Integration Typing

### SQLAlchemy with Types
```python
from typing import Optional
from sqlalchemy.orm import Session

def get_module_by_id(session: Session, module_id: str) -> Optional[BaseModule]:
    return session.query(BaseModule).filter(BaseModule.id == module_id).first()

def create_module(session: Session, module_info: ModuleInfo) -> BaseModule:
    module = BaseModule(**module_info)
    session.add(module)
    session.commit()
    return module
```

## 7. Configuration and Settings

### Settings with Types
```python
class DatabaseConfig(TypedDict):
    url: str
    pool_size: int
    echo: bool

class ServerConfig(TypedDict):
    host: str
    port: int
    debug: bool
    database: DatabaseConfig

def load_config(config_path: str) -> ServerConfig:
    # ... loading logic
    pass
```

## 8. Async Code Typing

### Async Functions
```python
from typing import Awaitable
import asyncio

async def fetch_data(url: str) -> Dict[str, Any]:
    # ... async logic
    pass

async def process_multiple(urls: List[str]) -> List[Dict[str, Any]]:
    tasks: List[Awaitable[Dict[str, Any]]] = [
        fetch_data(url) for url in urls
    ]
    return await asyncio.gather(*tasks)
```

## 9. Testing with Types

### Test Function Typing
```python
import pytest
from typing import Any, Dict

def test_module_execution() -> None:
    # Test data with proper typing
    test_inputs: Dict[str, Any] = {"text": "hello world"}
    test_config: Dict[str, Any] = {"clean": True}
    
    result = execute_module("text_cleaner", test_inputs, test_config)
    
    assert isinstance(result, dict)
    assert "cleaned_text" in result

@pytest.fixture
def sample_module() -> BaseModuleExecutor:
    return BasicTextCleanerModule()
```

## 10. Tools and Validation

### MyPy Configuration (`mypy.ini`)
```ini
[mypy]
python_version = 3.9
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True
disallow_incomplete_defs = True

[mypy-sqlalchemy.*]
ignore_missing_imports = True

[mypy-flask.*]
ignore_missing_imports = True
```

### Running Type Checks
```bash
# Install mypy
pip install mypy

# Check specific file
mypy src/modules/registry.py

# Check entire project
mypy src/

# With specific configuration
mypy --config-file mypy.ini src/
```

## 11. Best Practices Summary

1. **Use Type Aliases**: For commonly used complex types
2. **TypedDict over Dict**: For structured data with known keys
3. **Protocols over ABC**: For interface definitions when possible
4. **Literal Types**: For constrained string/int values
5. **Optional vs NotRequired**: Use NotRequired for missing dictionary keys
6. **Forward References**: Use quotes for self-references
7. **Generic Types**: For reusable containers and functions
8. **Consistent Error Types**: Define custom exceptions with proper typing
9. **API Response Types**: Always type request/response data
10. **Validate at Boundaries**: Type check data coming from external sources

## 12. Common Patterns in This Project

```python
# Module execution pattern
def execute_with_validation(
    module_id: ModuleID,
    inputs: ExecutionInputs,
    config: ExecutionConfig
) -> ExecutionOutputs:
    # Validate inputs
    if not validate_inputs(inputs):
        raise ValidationError("Invalid inputs")
    
    # Execute with proper error handling
    try:
        return execute_module(module_id, inputs, config)
    except Exception as e:
        raise ModuleExecutionError(f"Execution failed: {e}")

# Database operation pattern
def safe_database_operation(
    operation: Callable[[Session], T]
) -> Optional[T]:
    session = get_session()
    try:
        result = operation(session)
        session.commit()
        return result
    except Exception as e:
        session.rollback()
        logger.error(f"Database operation failed: {e}")
        return None
    finally:
        session.close()
```

This approach provides:
- **Better IDE support** with autocomplete and error detection
- **Runtime safety** with validation at boundaries
- **Documentation** through type hints
- **Maintainability** with clear interfaces and contracts