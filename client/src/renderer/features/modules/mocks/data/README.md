# Mock Module Catalog Data

This directory contains mock data for the module catalog API used during frontend development and testing.

## File Structure

```
modules.json - Complete module catalog with 10 representative modules
```

## Data Format

The `modules.json` file contains a module catalog matching the backend API response format:

```typescript
{
  "modules": [
    {
      "id": string,              // Unique module identifier
      "version": string,         // Semantic version (e.g., "1.0.0")
      "title": string,           // Display name for UI
      "description": string,     // User-facing description
      "kind": string,            // "transform" | "action" | "logic" | "entry_point"
      "category": string,        // Category for grouping (e.g., "Text", "Gate", "Data")
      "color": string,           // Hex color code for UI display
      "meta": {
        "io_shape": {
          "inputs": {
            "nodes": [
              {
                "label": string,        // Display label for node group
                "min_count": number,    // Minimum pins required
                "max_count": number | null,  // Maximum pins (null = unlimited)
                "typing": {
                  "allowed_types": string[] | null,  // Allowed types (e.g., ["str", "int"])
                  "type_var": string | null          // Type variable (e.g., "T")
                }
              }
            ]
          },
          "outputs": { /* same structure as inputs */ },
          "type_params": {
            "T": []  // Type variable domains (optional)
          }
        }
      },
      "config_schema": object    // JSON Schema for module configuration
    }
  ]
}
```

## Modules Included

### Transform Modules
1. **basic_text_cleaner** - Clean and normalize text
2. **data_duplicator** - Duplicate data to multiple outputs
3. **type_converter** - Convert between data types

### Logic Modules
4. **boolean_and** - Logical AND gate
5. **boolean_or** - Logical OR gate
6. **boolean_not** - Logical NOT (inversion)
7. **if_selector** - Conditional value selection

### Action Modules
8. **print_action** - Print to server logs

### Comparator Modules
9. **string_equals** - String equality comparison
10. **number_greater_than** - Numeric comparison

## Module Kinds

- **transform**: Data transformation modules (input → processing → output)
- **action**: Side-effect modules (input → action, no output)
- **logic**: Logic/control flow modules (conditionals, gates, selectors)
- **entry_point**: Pipeline entry points (not included in mock data)

## Categories

Modules are grouped by category for UI organization:
- **Text**: Text processing and manipulation
- **Data**: Data transformation and manipulation
- **Gate**: Boolean logic gates
- **Selector**: Conditional selection
- **Print**: Output/logging actions
- **Comparator**: Comparison operations

## Type System

### Fixed Types
Modules with `allowed_types` have fixed input/output types:
```json
"typing": {
  "allowed_types": ["str"]
}
```

### Type Variables
Modules with `type_var` use generic type parameters:
```json
"typing": {
  "type_var": "T"
}
```

This allows the same module to work with any type, with the constraint that all pins using the same type variable must have the same runtime type.

### Dynamic Node Counts
Some modules support variable numbers of inputs/outputs:
```json
{
  "label": "Duplication",
  "min_count": 2,
  "max_count": null  // Unlimited outputs
}
```

## Configuration Schemas

Each module includes a JSON Schema describing its configuration options. This is used to dynamically generate configuration forms in the UI.

Example:
```json
"config_schema": {
  "type": "object",
  "properties": {
    "strip_whitespace": {
      "type": "boolean",
      "title": "Strip Whitespace",
      "description": "Remove leading/trailing whitespace",
      "default": true
    }
  }
}
```

## Usage

Import and use via the mock API hook:

```typescript
import { useMockModulesApi } from '../mocks/useMockModulesApi';

function MyComponent() {
  const { getModules, isLoading, error } = useMockModulesApi();

  useEffect(() => {
    async function loadModules() {
      const response = await getModules();
      console.log(response.modules);
    }
    loadModules();
  }, []);

  // ...
}
```

## Filtering

The API supports filtering by:
- **module_kind**: Filter by module type
- **category**: Filter by category
- **search**: Text search on title and description

Example:
```typescript
// Get only transform modules
const response = await getModules({ module_kind: 'transform' });

// Search for "text" modules
const response = await getModules({ search: 'text' });
```

## Source

This mock data is based on actual module implementations from the backend:
- `server/src/features/modules/transform/`
- `server/src/features/modules/logic/`
- `server/src/features/modules/action/`

The data matches the backend database schema (`ModuleCatalogModel`) and API response format from `server/src/api/routers/modules.py`.

## Updating

To add new mock modules:
1. Add a new module object to the `modules` array in `modules.json`
2. Ensure it follows the schema format above
3. Match the structure of backend module implementations
4. Include appropriate `meta.io_shape` and `config_schema`
