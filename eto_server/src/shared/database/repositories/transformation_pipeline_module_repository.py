"""
Transformation Pipeline Module Repository

This repository provides data access layer for transformation pipeline modules stored in the database.

The repository should handle:

1. **Module CRUD Operations**:
   - create_module(module_data): Insert new transformation module into database
   - get_module_by_id(module_id): Retrieve specific module by unique ID
   - get_all_modules(): Retrieve all registered modules with optional filtering
   - update_module(module_id, update_data): Update existing module configuration
   - delete_module(module_id): Remove module from database (soft delete preferred)
   - activate_module(module_id): Mark module as active/available for use
   - deactivate_module(module_id): Mark module as inactive/disabled

2. **Module Discovery and Filtering**:
   - get_modules_by_category(category): Filter modules by category (Text Processing, Data Processing, etc.)
   - get_active_modules(): Return only modules marked as active
   - search_modules(query): Search modules by name, description, or tags
   - get_modules_by_version(version_pattern): Filter by version numbers
   - get_recently_used_modules(limit): Return most recently executed modules

3. **Module Metadata Management**:
   - get_module_schema(module_id): Retrieve input/output/config schemas for a module
   - update_module_schema(module_id, schema_data): Update module's schema definitions
   - get_module_usage_stats(module_id): Return usage statistics and performance data
   - increment_usage_count(module_id): Track module usage for analytics
   - update_last_used_timestamp(module_id): Update when module was last executed

4. **Module Registration and Discovery**:
   - register_builtin_modules(): Populate database with system-provided modules
   - register_custom_module(module_class): Add user-defined modules to registry
   - validate_module_registration(module_data): Ensure module data is valid before registration
   - get_module_dependencies(module_id): Return modules that this module depends on
   - check_module_compatibility(module_id, target_version): Version compatibility checking

5. **Configuration and Schema Handling**:
   - store_module_configuration(module_id, config_json): Store module's config schema as JSON
   - retrieve_module_configuration(module_id): Parse and return configuration schema
   - validate_module_schema(schema_data): Ensure schema follows expected format
   - migrate_module_schema(old_version, new_version): Handle schema migrations

6. **Performance and Analytics**:
   - track_execution_time(module_id, execution_time_ms): Record performance metrics
   - get_module_performance_stats(module_id): Return average execution times, success rates
   - get_module_error_history(module_id): Return recent errors and failure patterns
   - cleanup_old_usage_data(retention_days): Remove old analytics data

7. **Database Model Integration**:
   - Map to TransformationPipelineModuleModel SQLAlchemy model
   - Handle JSON serialization/deserialization for schema fields
   - Manage database transactions and error handling
   - Implement proper indexing for performance queries
   - Handle database connection pooling and session management

8. **Caching and Performance**:
   - Cache frequently accessed module definitions in memory
   - Implement cache invalidation when modules are updated
   - Batch operations for bulk module operations
   - Optimize queries for module discovery and filtering

The repository should inherit from base_repository and follow the established patterns
for database access, error handling, and transaction management used throughout the ETO system.
It should provide both synchronous and asynchronous operation support where appropriate.
"""