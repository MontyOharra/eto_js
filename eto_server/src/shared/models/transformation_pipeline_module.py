"""
Transformation Pipeline Module Pydantic Models

Basic Pydantic models that correspond to the SQLAlchemy TransformationPipelineModuleModel.

This file should contain:

1. **Base Model Classes**:
   - TransformationPipelineModuleBase: Core fields shared across create/update/response models
   - Fields: id, name, description, version, input_config, output_config, config_schema
   - Fields: service_endpoint, handler_name, color, category
   - Proper field validation and constraints

2. **CRUD Operation Models**:
   - TransformationPipelineModuleCreate: For creating new modules (excludes DB-generated fields)
   - TransformationPipelineModuleUpdate: For updating existing modules (optional fields)
   - TransformationPipelineModule: Full model including DB-generated fields (id, timestamps, etc.)

3. **Field Definitions and Validation**:
   - module_id: String field with proper length constraints and pattern validation
   - name: Display name with length constraints
   - description: Optional longer text field
   - version: Version string with semantic versioning validation
   - input_config: JSON string containing input schema definition
   - output_config: JSON string containing output schema definition
   - config_schema: JSON string containing configuration options schema
   - handler_name: Python class name for the module implementation
   - color: Hex color code for UI theming
   - category: Module category for organization and filtering

4. **Database Integration Methods**:
   - from_db_model(db_model): Class method to convert SQLAlchemy model to Pydantic
   - to_db_dict(): Instance method to convert Pydantic model to dict for database insertion
   - JSON parsing for schema fields (input_config, output_config, config_schema)
   - Proper datetime handling with timezone awareness

5. **Validation and Business Logic**:
   - Custom field validators for JSON schema fields
   - Validation that handler_name follows Python class naming conventions
   - Color code validation (hex format)
   - Version string validation (semantic versioning)
   - Category validation against allowed categories

6. **Response Models**:
   - Simple response models for API endpoints
   - Models for bulk operations (list of modules, search results)
   - Summary models for module listings (subset of fields for performance)
   - Error response models for validation failures

The models should follow the established patterns in the ETO codebase for Pydantic model
organization, validation, and database integration. They should be compatible with
FastAPI automatic OpenAPI documentation generation and provide proper type hints
for development tooling.
"""