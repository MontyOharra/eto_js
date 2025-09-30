# Frontend Migration Guide: Old vs New Transformation Pipeline Server

## Overview
This document outlines the key differences between the old and new transformation pipeline servers and what needs to be updated in the frontend.

## Key API Differences

### 1. Module Catalog Structure

#### Old Server Response (`/api/modules`)
```json
{
  "id": "text_cleaner",
  "name": "Text Cleaner",
  "description": "...",
  "category": "Text Processing",
  "color": "#3B82F6",
  "version": "1.0.0",
  "inputConfig": {
    "nodes": [...],
    "dynamic": {...},
    "allowedTypes": [...]
  },
  "outputConfig": {
    "nodes": [...],
    "dynamic": {...}
  },
  "config": [...]  // Array of config items
}
```

#### New Server Response (`/api/modules`)
```json
{
  "modules": [
    {
      "module_ref": "basic_text_cleaner:1.0.0",
      "id": "basic_text_cleaner",
      "version": "1.0.0",
      "title": "Basic Text Cleaner",  // Note: 'title' not 'name'
      "description": "...",
      "kind": "transform",  // New: module type
      "meta": {  // New: I/O metadata
        "inputs": {
          "allow": true,
          "min_count": 1,
          "max_count": 1,
          "type": "str"
        },
        "outputs": {
          "allow": true,
          "min_count": 1,
          "max_count": 1,
          "type": "str"
        }
      },
      "config_schema": {  // JSON Schema format
        "type": "object",
        "properties": {
          "strip_whitespace": {
            "type": "boolean",
            "default": true,
            "description": "..."
          }
        }
      }
    }
  ],
  "total_count": 2,
  "stats": {...}
}
```

### 2. Key Structural Changes

| Old Server | New Server | Impact |
|------------|------------|---------|
| `input_schema`, `output_schema` (JSON strings) | `meta.inputs`, `meta.outputs` (structured objects) | Frontend needs to parse differently |
| `config_schema` (array) | `config_schema` (JSON Schema object) | Config form generation needs update |
| `name` | `title` | Field rename |
| `dynamic_inputs`, `dynamic_outputs` | `meta.inputs.allow`, `meta.inputs.max_count` | Dynamic I/O handling simplified |
| `handler_name` | Optional or removed | Not needed by frontend |
| No module type | `kind`: "transform", "action", "logic" | New categorization |

### 3. Module Execution API

#### New Execution Endpoint
```bash
POST /api/modules/execute
{
  "module_id": "basic_text_cleaner",
  "inputs": {
    "input_1": "text to clean"
  },
  "config": {
    "strip_whitespace": true
  }
}
```

Response:
```json
{
  "success": true,
  "module_id": "basic_text_cleaner",
  "outputs": {
    "output_1": "cleaned text"
  },
  "error": null,
  "performance_ms": 2.5,
  "cache_used": true
}
```

## Frontend Components That Need Updates

### 1. `moduleTransformService.ts`
**Current Issues:**
- Expects old field names (`input_schema`, `output_schema`, `config_schema`)
- Parses JSON strings instead of objects
- Maps to wrong field names

**Required Changes:**
```typescript
// Update BackendModuleData interface
interface BackendModuleData {
  id: string;
  title: string;  // was 'name'
  description: string;
  version: string;
  kind: 'transform' | 'action' | 'logic';  // new
  meta: {  // new structure
    inputs: DynamicSide;
    outputs: DynamicSide;
  };
  config_schema: object;  // JSON Schema, not string
  // Remove: input_schema, output_schema, handler_name, etc.
}
```

### 2. Module Components
- Update to handle `meta.inputs/outputs` instead of `inputConfig/outputConfig`
- Parse `config_schema` as JSON Schema instead of array
- Handle new `kind` field for module categorization

### 3. API Client Updates
Need to:
- Update endpoint paths if needed
- Handle new response wrapper structure (`{ modules: [...] }`)
- Parse new metadata format

## Migration Steps

### Step 1: Update Service Layer
1. Create new API service for v2 server
2. Update type definitions to match new structure
3. Create adapter function to convert new format to existing frontend format (temporary)

### Step 2: Update Components Gradually
1. Start with module catalog display
2. Update module configuration forms
3. Update pipeline execution

### Step 3: Remove Old Code
1. Remove old transformation service
2. Clean up unused type definitions
3. Update all imports

## Immediate Issues to Fix

### 1. Server Not Loading Modules at Startup
The new server needs to auto-discover modules when the service initializes:

```python
# In ModulesService.__init__()
def __init__(self):
    self.registry = ModuleRegistry()
    # Add auto-discovery
    self.registry.auto_discover([
        "src.features.modules.transform",
        "src.features.modules.action",
        "src.features.modules.logic"
    ])
```

### 2. Frontend Type Mismatch
The frontend expects different field names and structures. Options:
1. Update frontend to match new API (recommended)
2. Add compatibility layer in server
3. Create adapter in frontend (temporary)

## Testing Strategy

1. **Module Loading**: Test that modules appear in catalog
2. **Module Execution**: Test execution via new API
3. **Configuration Forms**: Test that config forms render correctly with JSON Schema
4. **Pipeline Building**: Test drag-drop and connections
5. **Pipeline Execution**: Test full pipeline execution

## Benefits of New Structure

1. **Better Type Safety**: Structured metadata instead of JSON strings
2. **Standard JSON Schema**: Better validation and UI generation
3. **Module Categories**: Transform vs Action vs Logic
4. **Performance**: Built-in caching and optimization
5. **Security**: Validated module loading
6. **Flexibility**: Dynamic I/O with clear constraints