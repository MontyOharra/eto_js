"""
Base Transformation Module

This file contains the abstract base class that all transformation modules must inherit from.

The base module class should provide:

1. **Abstract Interface**:
   - Define required methods that all modules must implement
   - get_module_info(): Returns module metadata (ID, name, description, version, category, etc.)
   - get_input_schema(): Returns schema defining expected input fields and types
   - get_output_schema(): Returns schema defining output fields and types
   - get_config_schema(): Returns schema defining configuration options
   - execute(inputs, config): Performs the actual transformation

2. **Input/Output Management**:
   - Standardized input/output field definitions with types (string, number, boolean, etc.)
   - Support for required vs optional fields
   - Default value handling
   - Multiple input/output support with cardinality (single, multiple, variable)

3. **Configuration System**:
   - Schema-driven configuration with validation
   - Support for different config types (text, number, boolean, select, etc.)
   - Default values and required/optional settings
   - Configuration validation before execution

4. **Validation Framework**:
   - Input validation against schema before execution
   - Configuration validation against schema
   - Type checking and conversion
   - Custom validation hooks for complex requirements

5. **Error Handling**:
   - Standardized exception types for different error scenarios
   - Validation errors, execution errors, configuration errors
   - Detailed error messages with context
   - Logging integration for debugging

6. **Metadata Management**:
   - Module registration information (unique ID, display name, description)
   - Versioning support
   - Category/tagging system for organization
   - Usage tracking and statistics

7. **Execution Context**:
   - Thread-safe execution
   - Logging integration with module context
   - Performance tracking and metrics
   - Resource management and cleanup

The base class should be abstract and force implementation of core methods while providing
common functionality like validation, logging, and error handling that all modules can inherit.
"""