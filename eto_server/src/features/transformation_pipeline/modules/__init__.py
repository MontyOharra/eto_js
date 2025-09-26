"""
Transformation Modules

This package contains the base module class and all specific transformation module implementations.

The modules system provides:
- Base abstract class that defines the interface all transformation modules must implement
- Built-in modules for common transformation operations (text cleaning, type conversion, etc.)
- Module registry and discovery system
- Input/output validation and type checking
- Configuration schema management
- Error handling and logging for transformation operations

Each module should inherit from the base module class and implement:
- get_module_info(): Returns metadata about the module (ID, name, description, etc.)
- get_input_schema(): Defines expected input structure and types
- get_output_schema(): Defines output structure and types
- get_config_schema(): Defines configuration options and validation
- execute(): Performs the actual transformation logic
- validate_inputs(): Custom input validation (optional)
- validate_config(): Custom configuration validation (optional)
"""