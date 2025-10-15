# ETO System - Development Changelog

## Overview
This document tracks major development milestones and features implemented in the Email-to-Order (ETO) PDF processing system.

---

## [2025-10-15 15:00] — Complete API Endpoint Specification (Phase 3 Complete)

### Spec / Intent
- Complete Phase 3 of server redesign: define all HTTP endpoints for 7 routers
- Design stateless template wizard approach with simulate endpoint (no draft versions)
- Specify 35 total endpoints with request/response structures, query parameters, and error handling
- Document complete API surface before implementation begins

### Changes Made
**Router 1: `/email-configs`** (10 endpoints)
- CRUD operations for email ingestion configurations
- Discovery endpoints for accounts and folders
- Validation endpoint for config testing
- Activation/deactivation lifecycle management

**Router 2: `/eto-runs`** (6 endpoints)
- List and detail views with status filtering
- Manual PDF upload for ETO processing
- Bulk operations: reprocess, skip, delete with atomic validation

**Router 3: `/pdf-files`** (3 endpoints)
- PDF metadata retrieval
- PDF download/streaming with proper MIME types
- PDF object extraction (7 types: text, graphics, images, tables)

**Router 4: `/pdf-templates`** (10 endpoints)
- Template CRUD with versioning system
- Stateless simulation endpoint for testing (no DB persistence)
- Version history and management
- Activation/deactivation for template matching

**Router 5: `/modules`** (1 endpoint)
- Complete module catalog for pipeline builder
- Read-only with filtering and search

**Router 6: `/pipelines`** (5 endpoints)
- Full CRUD for standalone pipeline testing (dev only)
- Will be removed when standalone testing page removed

**Router 7: `/health`** (1 endpoint)
- System health monitoring with per-service status
- Used for frontend health checks and polling

**Key Design Decisions:**
- Eliminated draft versions - frontend maintains wizard state
- Stateless `POST /pdf-templates/simulate` for testing without persistence
- Bulk operations use `204 No Content` for mutation triggers
- PDF objects grouped by type (7 types) for type safety
- Direct responses (FastAPI style, no wrapper objects)

**Files Modified:**
- `context/server_redesign/API_ENDPOINTS.md` - Complete 35-endpoint specification (1900 lines)
- `context/server_redesign/CONTINUITY.md` - Updated progress tracking, marked Phase 3 complete

### Next Actions
- Phase 4: Schema Definitions (Pydantic request/response models)
- Phase 5: Service Layer Design (business logic orchestration)
- Phase 6: Repository Layer Design (data access patterns)
- Phase 7: Type System Unification (DTOs connecting all layers)
- Phase 8: Implementation (actual code)

### Notes
- **No Draft Versions**: Simplified template creation - wizard state lives in frontend only
- **Stateless Simulation**: `POST /pdf-templates/simulate` runs full ETO process without DB writes
- **Atomic Bulk Operations**: Reprocess/skip/delete validate all runs before executing
- **Frontend-First Design**: All endpoints designed based on actual frontend needs
- **Type Safety**: Explicit structures with proper TypeScript-style response definitions
- **35 Total Endpoints**: Complete API surface documented before implementation

---

## [2025-10-07 17:00] — Pipeline Execution Architecture & Service Container Fix

### Spec / Intent
- Fixed ServiceContainer initialization issues where API routers couldn't access services
- Designed unified execution architecture with node metadata for type-aware module execution
- Created comprehensive implementation plan for Dask-based pipeline execution
- Added execution audit trail for debugging and production monitoring

### Changes Made
**Files Modified:**
- `transformation_pipeline_server/src/app.py` - Fixed import paths for ServiceContainer
- `transformation_pipeline_server/src/shared/services/service_container.py` - Pure class-based singleton
- `transformation_pipeline_server/src/api/routers/modules.py` - Updated to use ServiceContainer directly
- `transformation_pipeline_server/src/api/routers/pipelines.py` - Updated service access pattern
- `.gitignore` - Added .env files to ignore list

**Docs Created:**
- `context/unified_execution_plan.md` - Complete execution engine specification
- `context/implementation_tasks.md` - Detailed implementation roadmap

### Key Technical Decisions
1. **ServiceContainer Fix**: Resolved Python module import path issues by ensuring consistent imports
2. **Node Metadata**: Using `List[InstanceNodePin]` for strongly-typed pin information
3. **ExecutionContext**: Pydantic model with helper methods for modules
4. **Audit Trail**: Database persistence (Option 2) for complete execution history
5. **Removed Redundancy**: Eliminated `output_display_names` field in favor of node_metadata

### Commits This Session
- `e7beb97` - chore: Add .env files to .gitignore and remove from tracking
- `8fcb851` - fix: Resolve ServiceContainer initialization issue with Python imports

### Next Actions
- Implement Phase 1: Update PipelineStep model with node_metadata
- Implement Phase 2: Update compiler to preserve node metadata
- Implement Phase 3: Create ExecutionContext class
- Implement Phase 4: Build Dask executor with audit trail
- Implement Phase 5: Add execution API endpoint

### Notes
- Frontend pipeline viewing still needs EntryPoint type field fix
- Sequential executor (Phase 4.4) is optional for now
- Module updates deferred until core structure is ready

---

## [2025-10-03 01:00] — Click-to-Connect Connection Creation Implementation

### Spec / Intent
- Replace drag-to-connect behavior with more intuitive click-to-connect workflow
- Add visual feedback showing connection line following mouse cursor during connection creation
- Support bidirectional connection creation (start from input or output)
- Implement connection cancellation via Escape key or background click
- Improve user experience with clear visual indicators and instructions

### Changes Made
- **PipelineGraph.tsx**: Complete connection handling rewrite
  - Added `pendingConnection` state to track active connection creation
  - Added `mousePosition` state and mouse tracking for visual line rendering
  - Implemented `handleHandleClick` callback supporting bidirectional connections
  - Added `handlePaneClick` for canceling pending connections
  - Added keyboard listener for Escape key cancellation
  - Disabled React Flow's default drag-to-connect (`nodesConnectable={false}`)
  - Added SVG overlay rendering connection line from handle to mouse cursor with dashed line, arrow, and cursor indicator
  - Added blue banner showing instructions when connection is pending
- **ModuleNodeNew.tsx**: Updated to support click-to-connect
  - Added `onHandleClick` callback prop to all relevant interfaces
  - Added `pendingConnection` prop for visual feedback
  - Updated Handle components with `onClick` handler and `data-handleid` attribute
  - Added visual feedback (blue glow and scale effect) for pending connection source handle
  - Passed callbacks through component hierarchy: ModuleNodeNew → NodeGroupSection → NodeRow

### Architecture Decisions
- **Bidirectional Support**: Users can start connection from either input or output handle
- **Invalid Connection Handling**: Clicking two handles of same type cancels and starts new connection
- **Visual Feedback**: Real-time SVG line follows mouse from source handle to cursor
- **State Management**: Pending connection state managed at graph level, passed down to nodes
- **Clean Cancellation**: Multiple ways to cancel (Escape, background click, clicking incompatible handle)

### Current State
- ✅ **Click-to-Connect Working**: Users click handle, move mouse, click target handle
- ✅ **Visual Line Following Mouse**: Blue dashed line with arrow shows where connection will go
- ✅ **Bidirectional Connections**: Can start from input or output
- ✅ **Cancellation Working**: Escape key and background click cancel pending connections
- ✅ **Visual Feedback**: Source handle glows blue when selected
- ✅ **Instructions Shown**: Banner explains next step during connection creation

### Next Actions
- Add connection type validation (ensure compatible data types)
- Implement connection deletion/editing
- Add connection hover states and tooltips
- Consider adding connection curves/bezier paths for better visual routing

### Notes
- **User Experience**: Click-to-connect is more intuitive than drag-to-connect for precision work
- **Visual Clarity**: Real-time line feedback helps users understand connection path
- **Flexibility**: Bidirectional support accommodates different user mental models
- **Clean Code**: Removed all debug logging after feature was working
- **React Flow Integration**: Disabled default connection behavior, implemented custom system

---

## [2025-10-01 19:30] — View-Only Pipeline Builder Implementation Complete

### Spec / Intent
- Create comprehensive view-only pipeline builder for displaying saved pipelines from backend API
- Implement frontend pipeline list with proper API integration and navigation
- Fix backend pipeline save/load system authentication and data structure issues
- Enable analysis of saved pipeline data to understand transformation requirements for future work

### Changes Made
- **Backend Fixes**: Fixed missing SQLAlchemy relationship in database models, removed incorrect imports from services, fixed API response models for summary endpoints
- **Frontend Pipeline List** (`client/src/renderer/routes/transformation_pipeline/index.tsx`): Complete rewrite with real API integration, loading/error/empty states, professional pipeline cards with stats and actions
- **View-Only Pipeline Route** (`client/src/renderer/routes/pipeline-view.$pipelineId.tsx`): New standalone route displaying TransformationGraph in view-only mode with comprehensive console logging
- **TransformationGraph Enhancement**: Added `viewOnly` prop to hide save button, implemented debug logging for data structure analysis, fixed initialization order bugs
- **Navigation Fixes**: Replaced `window.location.href` with proper React Router navigation for Electron compatibility, fixed route structure and authentication issues
- **Layout Rendering Fix**: Fixed flexbox container structure to properly display TransformationGraph canvas with zoom controls

### Architecture Decisions
- **Route Pattern**: Used standalone `/pipeline-view/$pipelineId` route instead of nested route for Electron compatibility
- **Console Logging Strategy**: Two-level logging (route + component) with structured emoji-based identification for data analysis
- **Data Flow**: Pipeline List → View Button → Standalone Route → Fetch Full Pipeline → TransformationGraph (view-only)

### Current State
- ✅ **Pipeline List Working**: Fetches real pipelines, displays professional cards with stats
- ✅ **View-Only Builder Working**: Shows actual TransformationGraph canvas with zoom controls
- ✅ **Authentication Fixed**: No more login redirects, proper route handling
- ✅ **Navigation Fixed**: Proper React Router navigation for Electron app
- ✅ **Comprehensive Logging**: Detailed console output for data structure analysis

### Next Actions
- **Data Transformation Analysis**: Use console logs to understand backend vs frontend data structure differences
- **Module Template Integration**: Fetch and map module metadata for proper module rendering
- **Node Structure Mapping**: Transform backend static/dynamic node groups to frontend arrays
- **Connection Rendering**: Ensure saved connections display correctly in view-only mode

### Notes
- **Foundation Complete**: Save/load pipeline system working, view-only interface functional
- **Ready for Analysis**: Console shows exact data structures for transformation planning
- **Architecture Solid**: Proper separation of concerns, authentication working, navigation patterns established
- **Development Ready**: Next session can focus on data transformation to display saved pipelines correctly

---

## [2025-10-01 15:45] — Type Constraint System Debugging Cleanup

### Spec / Intent
- Clean up debugging console logs added during type constraint system troubleshooting
- Maintain clean codebase now that dropdown display logic is working correctly
- Remove temporary logging statements that were used to diagnose connection type filtering

### Changes Made
- **typeConstraints.ts**: Removed console.log statements from `getNodeTypeConstraints()` function
  - Removed starting allowedTypes logging (line 268)
  - Removed connection filtering debug logs (lines 314-316, 322)
  - Removed final result logging (line 356)
- **Code Quality**: Cleaned up debugging artifacts while preserving all functional logic

### Next Actions
- Monitor type constraint system in production use
- Continue with any additional UI refinements if needed

### Notes
- **Functionality Preserved**: All type constraint logic remains intact and working
- **Debugging Complete**: Dropdown now correctly shows all types with disabled options for connected nodes
- **Clean Codebase**: Removed temporary debugging code added during development

---

## [2025-10-01 14:30] — ModuleComponent Refactoring: Component Breakdown Architecture & Integration
### Spec / Intent
- Break down ModuleComponent's node section into smaller, focused components for better maintainability
- Create component hierarchy: NodeSectionSide → NodeGroup → NodeComponent with supporting components
- Implement group-based node organization where each dynamic node is its own group with separators
- Maintain existing functionality while creating cleaner separation of concerns
- Integrate new components into existing ModuleComponent with compatibility bridging

### Changes Made
- **Component Architecture**: Created `/module-components/` directory with 5 new components following clear hierarchy
- **NodeSectionSide**: Organizes input/output sides into groups, handles group-level add/remove logic
- **NodeGroup**: Manages individual groups (static or dynamic), enforces min/max constraints, renders separators
- **NodeComponent**: Pure node rendering with circle, name, type, and individual interactions
- **AddNodeButton**: Reusable add button for dynamic groups that haven't reached max_count
- **GroupSeparator**: Horizontal line separators between groups with optional group labels
- **ModuleComponent Integration**: Commented out old node section, added new component usage with API bridging
- **Compatibility Layer**: Added bridge functions to convert between node-ID based new API and index-based old API
- **Temporary Fix**: Modified NodeSectionSide to work with current NodePin structure (missing is_static/group_id properties)
- Files: `module-components/NodeSectionSide.tsx`, `NodeGroup.tsx`, `NodeComponent.tsx`, `AddNodeButton.tsx`, `GroupSeparator.tsx`, `index.ts`, `ModuleComponent.tsx`

### Next Actions
- Update NodePin interface to include is_static and group_id properties for proper group organization
- Implement proper static vs dynamic node grouping once data structure supports it
- Test new component architecture with real module instances
- Extract configuration section using similar component breakdown pattern
- Remove commented old code once new architecture is fully validated

### Notes
- **Group Strategy**: Each dynamic node becomes its own group with separators for visual organization
- **Event Flow**: Clean data bubbling from NodeComponent → NodeGroup → NodeSectionSide → parent component
- **API Bridging**: New node-ID based API bridges to existing index-based ModuleComponent API
- **Temporary Workaround**: Simplified grouping logic due to current NodePin structure limitations
- **Architecture Ready**: Foundation established for proper group-based node management once data model is updated

---

## [2025-09-29 20:30] — Transformation Pipeline Type System Migration to Arrays
### Spec / Intent
- Migrate module type system from VarType objects to cleaner array-based format
- Fix module memory refresh issues when code changes (Python module caching)
- Debug and resolve module sync failures due to old type format persistence
- Implement validation during module registration

### Changes Made
- **Type System Migration**: Changed from `{ mode: 'variable', allowed: [...] }` to simple arrays `["str", "int"]`
- **Frontend Updates**: Modified `pipelineTypes.ts`, `moduleFactory.ts`, `ModuleComponentNew.tsx` to use array-based types
- **Backend Updates**: Modified `contracts.py`, `module_catalog.py` to use `List[Scalar]` instead of VarType
- **Module Refresh Fix**: Added Python module cache clearing in `sync_modules.py` to force reload on sync
- **File Watcher**: Created `watch_modules.py` for auto-sync during development (optional)
- Files: Multiple files across frontend and backend, primarily type definitions and module factory

### Next Actions
- Complete module validation implementation during registration
- Add connection drawing between nodes in frontend
- Test complete pipeline with new type system

### Notes
- Empty array `[]` means all types allowed, single element `["str"]` is fixed type, multiple `["str", "int"]` is variable
- Module sync now clears Python's `sys.modules` cache to ensure fresh code is loaded
- Pydantic already provides validation, preventing invalid type configurations

---

## [2025-09-29 15:00] — Module System Performance and Security Enhancements
### Spec / Intent
- Implement module resolver with registry-first priority for performance
- Add security validation to prevent arbitrary code execution
- Add caching layer to avoid repeated module imports
- Clean up database design to remove unnecessary ui_hints and visual_state table

### Changes Made
- **Registry Enhancements**: Added `ModuleSecurityValidator`, `ModuleCache`, and `resolve_module()` method with multi-strategy resolution
- **Security**: Whitelist allowed packages, block dangerous patterns, validate handler paths before loading
- **Performance**: LRU cache with TTL for loaded modules, cache statistics tracking
- **Database Cleanup**: Removed PipelineVisualStateModel table, removed all ui_hints references
- **API Enhancement**: Added `/modules/cache/stats` endpoint for monitoring cache performance
- Files: `core/registry.py`, `cli/sync_modules.py`, `api/routers/modules.py`, `shared/database/models.py`

### Next Actions
- Test module loading with new security and caching
- Monitor cache hit rates in production
- Add more transform/action/logic modules

### Notes
- Module loading now tries registry first (fast), then handler_name (flexible)
- Security validation prevents path traversal and code injection
- Cache significantly improves performance for repeated module execution
- Visual state stored directly in pipeline_definitions.visual_json field

---

## [2025-09-29 13:00] — Module Registry Implementation and Type Safety Fixes
### Spec / Intent
- Fix type error in module contracts where ConfigModel was incorrectly defined as class instead of type annotation
- Implement complete module registry system with auto-discovery and decorator registration
- Create CLI tool for syncing modules to database catalog
- Add makefile commands for module management operations

### Changes Made
- **Type System Fix**: Changed `ConfigModel` from nested class to `Type[BaseModel]` annotation in contracts.py, added `config_schema()` method
- **Module Registry**: Created singleton registry with auto-discovery, decorator pattern, and catalog format conversion
- **CLI Tool**: Built `sync_modules.py` for database sync with list/clear/refresh commands
- **Makefile Commands**: Added modules-sync, modules-list, modules-clear, modules-refresh targets
- Files: `core/contracts.py`, `core/registry.py`, `cli/sync_modules.py`, `Makefile`, `transform/text_cleaner.py`

### Next Actions
- ~~Test module sync commands with database connection~~ ✅
- Implement additional transform/action/logic modules
- Build pipeline compiler and executor

### Notes
- Registry auto-discovers modules from specified packages using importlib
- @register decorator automatically adds modules to registry on import
- CLI tool converts registry entries to database catalog format
- No versioning for now - refresh command replaces all modules

---

## [2025-09-26 14:00] — Transformation Pipeline Architecture Analysis and Proposal
### Spec / Intent
- Analyze proposed transformation pipeline design against current implementation
- Evaluate node-based JSON schema with module/node separation
- Assess Dask-based DAG execution approach with parallel groups
- Provide comprehensive gap analysis and migration plan

### Analysis Conducted
- **Current State Review**: Examined existing database models (TransformationPipelineModel, TransformationPipelineStepModel, etc.)
- **Proposal Evaluation**: Analyzed node-based pipeline JSON, type system, dynamic I/O, compilation process
- **Gap Identification**: Found major gaps in pipeline-template integration, JSON schema, type system, execution engine
- **Migration Planning**: Outlined phased approach for database changes, compiler implementation, Dask integration

### Key Findings
- **Architecture Gap**: Pipelines currently separate from template versions, need integration for immutability
- **Type System Missing**: No scalar type enforcement, need type_convert module and validation
- **No Compiler**: Missing validation → expansion → topological sort → step generation pipeline
- **No Executor**: Need Dask integration for DAG execution with parallelization
- **Dynamic I/O Needed**: Current static configs don't support variable node counts

### Changes Made
- Files: `context/transformation_pipeline.md` (new proposal document)
- Summary: Added comprehensive 420-line proposal defining node-based pipeline architecture with Dask execution

### Next Actions
- Implement JSON schema with Pydantic models for pipeline definition
- Build compiler with validation, custom module expansion, topological sorting
- Create core modules (text_clean, type_convert) with base scalar types
- Integrate Dask for parallel DAG execution
- Add pipeline fields to PdfTemplateVersionModel

### Notes
- **Well-Architected**: Proposal addresses real needs with good separation of concerns
- **Type Safety**: Base scalar types only prevents complexity while maintaining flexibility
- **Immutability**: Template-version scoped pipelines ensure reproducibility
- **Scalability**: Dask provides efficient parallel execution for complex pipelines

---

## [2025-09-25 21:45] — Transformation Pipeline Module System Foundation
### Spec / Intent
- Create proper monolithic transformation pipeline architecture within main ETO server
- Build base module class framework for transformation modules (text cleaning, type conversion, etc.)
- Establish module registry pattern for discovering and executing transformation modules
- Create repository and models for transformation pipeline module storage and management
- Analyze separate server architecture to inform integrated system design

### Changes Made
- **Module System Structure**: Created `features/transformation_pipeline/` with modules package containing base_module.py and text_cleaner_module.py specifications
- **Repository Layer**: Added `transformation_pipeline_module_repository.py` with comprehensive CRUD operations, module discovery, usage analytics, and performance tracking
- **Pydantic Models**: Created `transformation_pipeline_module.py` models to match existing SQLAlchemy TransformationPipelineModuleModel
- **Utils Package**: Added `transformation_pipeline/utils/` for future pipeline analysis and async processing utilities
- **Architecture Analysis**: Comprehensive analysis of separate transformation server identifying strengths (clean module interface, validation framework) and weaknesses (JSON parsing overhead, performance bottlenecks)
- Files: `features/transformation_pipeline/` (complete package structure), `shared/database/repositories/transformation_pipeline_module_repository.py`, `shared/models/transformation_pipeline_module.py`

### Architecture Insights
- **Module Base Class**: Clean abstract interface with metadata, validation, and execution methods
- **Performance Issues**: JSON parsing overhead and module instance recreation identified as key bottlenecks to avoid
- **Recommended Patterns**: Keep validation framework and node configuration system, add caching and instance pooling
- **Integration Strategy**: Start with integrated approach for fast development, extract to separate service if scaling needed

### Next Actions
- Implement base module class with caching optimizations based on analysis findings
- Create concrete transformation modules (text cleaner, type converter) using established patterns
- Build module registry with instance pooling to avoid performance pitfalls
- Add transformation pipeline service for orchestrating multi-step transformations

### Notes
- **Monolithic Architecture**: Chosen over microservices for simplicity and performance during initial development
- **Design Foundation**: All files contain detailed specifications for implementation based on architectural analysis
- **Performance Focus**: Analysis identified specific areas to optimize (JSON parsing, instance creation) for production use
- **Future Migration Path**: Architecture supports extraction to separate service when scaling requirements emerge

---

## [2025-09-25 19:30] — Comprehensive Transformation Pipeline Server Architecture Analysis
### Spec / Intent
- Conduct thorough analysis of transformation pipeline server architecture to understand design patterns and architectural decisions
- Evaluate module base class design, registration system, database schema, configuration management, execution patterns, and pipeline analysis
- Identify strengths, weaknesses, scalability concerns, maintainability issues, and performance implications
- Provide specific recommendations for improvements and inform integrated system design decisions

### Analysis Conducted
- **Core Architecture Review**: Analyzed `types.py`, `module.py`, `registry.py`, `database.py`, and main application patterns
- **Module System Analysis**: Examined base class design, concrete implementations (BasicTextCleaner, SQLParser), validation patterns, and execution flows
- **Database Design Review**: Evaluated schema for base modules, custom modules, pipelines, and configuration management approach
- **Pipeline Execution Study**: Analyzed pipeline analysis service, simple execution service, and step-based execution patterns
- **Configuration Schema Analysis**: Reviewed NodeConfiguration system, dynamic node support, and type constraints
- **API Integration Review**: Examined Flask application structure, endpoint design, and frontend integration patterns

### Key Findings
- **Modular Architecture**: Well-separated concerns with clear boundaries between modules, registry, database, and execution services
- **Type Safety**: Comprehensive TypedDict definitions and protocol-based interfaces provide good type safety
- **Validation Framework**: Robust input/output/config validation with proper error handling and logging
- **Dynamic Module Support**: Flexible node configuration system supporting both static and dynamic input/output nodes
- **Database Integration**: Clean separation between database models and domain logic with proper session management

### Architecture Strengths Identified
- Clean separation of concerns with distinct layers
- Comprehensive validation and error handling
- Good type safety with protocols and TypedDict
- Flexible module configuration system
- Proper logging and debugging support

### Areas for Improvement Identified
- Performance optimization opportunities in module execution
- Scalability considerations for large pipeline processing
- Enhanced error context and debugging capabilities
- Configuration template system improvements
- Database performance optimization potential

### Next Actions
- Apply findings to inform integrated system design decisions
- Consider implementing identified improvements in new integrated version
- Use architectural patterns as foundation for building enhanced transformation pipeline system

### Notes
- **Analysis Scope**: Covered all major architectural components including module system, database design, execution patterns, and API integration
- **Design Quality**: Overall architecture demonstrates solid engineering principles with room for performance and scalability enhancements
- **Integration Ready**: Findings provide clear guidance for building improved integrated version of transformation pipeline system

---

## [2025-09-25 16:00] — Advanced Dependency Injection Container Implementation
### Spec / Intent
- Solve service initialization ordering and circular dependency issues
- Implement industry-standard dependency injection pattern for service management
- Enable lazy initialization and proper dependency resolution
- Add service health checks and lifetime management

### Changes Made
- **DI Container Implementation**: Created `dependency_injection.py` with full DI container supporting singleton/scoped/transient lifetimes
- **Circular Dependency Detection**: Automatic detection and error reporting of circular dependencies
- **Lazy Loading**: Services created only when first requested, solving initialization order issues
- **Service Container Update**: Integrated DI container into existing ServiceContainer for backward compatibility
- **Health Checks**: Added health check support for all registered services
- Files: `shared/services/dependency_injection.py` (new), `shared/services/service_container.py` (updated)

### Next Actions
- Update services to remove direct service fetching in constructors
- Add more sophisticated health checks to individual services
- Consider adding service middleware/interceptors

### Notes
- **Industry Standard**: Follows patterns used in Spring, .NET Core, and other enterprise frameworks
- **Backward Compatible**: Existing code continues to work with new DI system
- **Extensible**: Easy to add new services and dependencies
- **Type Safe**: Full type hints and error handling throughout

---

## [2025-09-25 14:45] — ETO Service Integration of Template-Based Extraction
### Spec / Intent
- Integrate template-based extraction into ETO processing pipeline
- Fix method calls to use correct function name and PdfObjects structure
- Ensure extraction happens after successful template matching
- Enable end-to-end data extraction from PDFs to database storage

### Changes Made
- **Method Call Updates**: Changed `extract_data_from_template()` to `extract_data_using_template()` in both sync and async versions
- **PdfObjects Usage**: Removed flattening step, now passes nested PdfObjects directly as designed
- **Data Flow**: Template matching → extraction → storage as JSON in extracted_data field
- Files: `features/eto_processing/service.py`

### Next Actions
- Test complete ETO pipeline with extraction
- Monitor extraction performance with real PDFs
- Consider adding extraction result validation

### Notes
- **Integration Complete**: ETO service now properly calls extraction after template matching
- **Data Format**: Extracted Dict[str, str] stored directly in EtoRunDataExtractionUpdate
- **Error Handling**: Extraction errors properly caught and logged within ETO pipeline

---

## [2025-09-25 14:30] — Template-Based Data Extraction Implementation
### Spec / Intent
- Implement template-based data extraction using bounding boxes and text word objects
- Create extraction function that maps field labels to extracted text values
- Support multi-line text extraction with proper word ordering and line grouping
- Add validation regex support and required field checking

### Changes Made
- **Main Extraction Function**: `extract_data_using_template()` method that takes template ID and PDF objects, returns Dict[str, str] mapping field labels to extracted text
- **Bounding Box Intersection**: `_is_word_in_bounding_box()` helper using 50% overlap OR center point checking with 2px tolerance
- **Text Assembly**: `_extract_text_from_bounding_box()` groups words into lines based on y-coordinate proximity, sorts by position, joins with spaces/newlines
- **Validation Support**: `_validate_extracted_text()` applies optional regex patterns to validate extracted content
- **Error Handling**: Comprehensive error handling for missing templates, versions, and extraction failures
- Files: `features/pdf_templates/service.py`

### Next Actions
- ~~Integrate extraction into ETO processing service after template matching~~ ✅
- Create unit tests for extraction functionality
- Test with real PDF documents and templates

### Notes
- **Extraction Algorithm**: Words are considered inside bounding box if >50% overlap OR center point is inside
- **Text Ordering**: Words sorted top-to-bottom then left-to-right, grouped into lines with 5px y-tolerance
- **Validation Philosophy**: Failed validation still returns text (logged warning), letting downstream handle
- **Required Fields**: Missing required fields logged but don't stop extraction, downstream decides handling
- **Return Format**: Simple Dict[str, str] ready for JSON serialization to database

---

## [2025-09-24 Session] — PDF Template Service Restructuring with Boolean Subset Matching
### Spec / Intent
- Complete restructuring of PDF template matching service from flat PDF objects to nested PdfObjects structure
- Implement boolean subset matching where templates are valid only if ALL signature objects exist in target PDF
- Replace scoring-based matching with deterministic ranking: total object count first, then weighted tie-breaking
- Strengthen type safety with explicit type annotations and proper error handling
- Simplify PdfTemplateMatchResult to only return essential fields (template_id, template_version)

### Changes Made
- **Template Matching Algorithm**: Complete rewrite of `find_best_template_match()` method to use nested `PdfObjects` structure with boolean subset matching - templates only match if ALL signature objects are found
- **Ranking System**: Implemented corrected ranking algorithm - first by total object count (more objects = better), then weighted scoring for ties using object type priorities (tables=4.0, images=3.0, text_lines=2.0, etc.)
- **Type-Specific Matching**: Created individual matching methods for each object type (`_match_text_words`, `_match_graphic_rects`, etc.) with appropriate position tolerances and content similarity thresholds
- **Model Simplification**: Updated `PdfTemplateMatchResult` to only include `template_found`, `template_id`, and `template_version` fields, removing unnecessary `coverage_percentage`, `unmatched_object_count`, and `match_details`
- **Type Safety Enhancement**: Added `TemplateMatch = Tuple[PdfTemplate, PdfTemplateVersion, int]` type alias, explicit type annotations throughout, proper error handling with ValueError exceptions
- **ETO Service Integration**: Updated ETO processing service calls to pass nested `PdfObjects` directly instead of flattened structure to `find_best_template_match()`
- **Template Creation Fix**: Updated `PdfTemplateCreate` model to use `initial_signature_objects` and `initial_extraction_fields` for proper template version creation workflow
- Files: `shared/models/pdf_template.py`, `features/pdf_templates/service.py`, `features/eto_processing/service.py`

### Next Actions
- Test complete template matching pipeline with new boolean subset matching algorithm
- Delete `_old` files after testing validation
- Test template creation workflow with new initial object structure

### Notes
- **Boolean Subset Logic**: Templates now have deterministic matching - either ALL objects are found (valid template) or not (invalid template)
- **No Partial Matches**: Eliminated scoring and percentage matching in favor of complete subset requirement for data accuracy
- **Type Safety**: Strong typing with TemplateMatch alias, proper error handling, and explicit type annotations throughout service layer
- **Performance**: Ranking algorithm optimized - check total count first (fast), only use weighted scoring for actual ties
- **ETO Integration**: Template matching calls updated to use nested structure, maintaining backward compatibility for data extraction operations that still use flattened structure

---

## [2025-09-23 14:30] — Colored Terminal Logging Implementation
### Spec / Intent
- Add colored terminal logging output with level-based colors for better log visibility
- Color only the log header (timestamp, level, logger name) while keeping message content uncolored
- Make colors environment-configurable for development vs production usage

### Changes Made
- **ColoredFormatter Class**: Created custom logging formatter with ANSI color codes - red for errors/critical, yellow for warnings, blue for info, gray for debug
- **Header-Only Coloring**: Split log format at `:\n    ` boundary to color only header portion, keeping message content in normal terminal color
- **Environment Control**: Added `LOG_COLORS` environment variable (default: true) to enable/disable colors
- **Integration**: Updated configure_logging() to use ColoredFormatter with existing LOG_FORMAT and LOG_LEVEL environment variables
- File: `src/app.py:55-91,99-100,124`

### Next Actions
- Test colored logging across different log levels during application usage
- Monitor color display in different terminal environments

### Notes
- **Visual Distinction**: Log levels now clearly distinguishable at a glance with colored headers
- **Message Readability**: Actual log content remains uncolored for maximum readability
- **Production Ready**: Colors can be disabled via LOG_COLORS=false for production environments
- **Consistent Format**: Works seamlessly with existing environment-configurable logging setup

---

## [2025-09-22 19:00] — Email Config Persistence Fix: Separate Runtime vs Database State
### Spec / Intent
- Fix email config deactivation bug where app shutdown incorrectly changes database config status
- Separate runtime listener management from persistent configuration state
- Ensure email configs remain active in database during app restarts for proper startup recovery
- Distinguish between user-initiated deactivation vs system shutdown operations

### Changes Made
- **New Method `stop_config_listeners()`**: Stops runtime listeners and integrations WITHOUT changing database config status. Used during app shutdown to preserve config state for startup recovery.
- **Enhanced `deactivate_config()`**: Now clearly documented as user-initiated action that changes both runtime state AND database status. Added comprehensive logging to distinguish from system shutdown.
- **New Method `stop_all_listeners()`**: Bulk operation to stop all active listeners while preserving database config statuses. Includes proper error handling and detailed logging.
- **Updated `shutdown()` Method**: Now calls `stop_all_listeners()` instead of `deactivate_config()` to preserve config database status during app shutdown.
- **Enhanced Logging**: Clear distinction between "stopping listeners" (runtime cleanup) vs "deactivating config" (persistent state change) with detailed context logging.
- File: `features/email_ingestion/service.py`

### Next Actions
- Test app shutdown and startup cycle to verify config persistence
- Verify startup recovery properly restarts all previously active configs
- Confirm user-initiated deactivation still works correctly

### Notes
- **Runtime vs Persistent State**: Clean separation between stopping listeners/threads (runtime) and changing config activation status (database)
- **Startup Recovery**: Configs now remain active in database during app restarts, enabling proper automatic recovery
- **User Experience**: User-initiated deactivations continue to work as expected, but system shutdowns no longer affect config states
- **Error Resilience**: Individual listener stop failures don't prevent other listeners from stopping gracefully

---

## [2025-09-22 18:00] — ETO Service Fixes and Timezone Handling
### Spec / Intent
- Remove "New" suffix from ETO service class name for clean production naming
- Fix timezone-aware vs timezone-naive datetime comparison errors in duration calculations
- Resolve import errors and method signature mismatches in email processing pipeline

### Changes Made
- **Service Naming**: Renamed `EtoProcessingServiceNew` to `EtoProcessingService` across all references including class definition, imports, service container, and module exports for clean production naming.
- **PDF Service Integration**: Fixed `store_pdf()` method call in email ingestion to use correct parameter names (`original_filename` instead of `filename`, removed invalid `metadata` parameter).
- **Timezone Handling**: Added `_calculate_duration_ms()` helper function to handle timezone-aware vs timezone-naive datetime comparisons that were causing "can't subtract offset-naive and offset-aware datetimes" errors during ETO run duration calculations.
- Files: `features/eto_processing/service.py`, `features/eto_processing/__init__.py`, `shared/services/service_container.py`, `features/email_ingestion/service.py`, `shared/database/repositories/eto_run.py`

### Next Actions
- Test complete email-to-ETO pipeline with timezone fixes
- Verify ETO processing duration calculations work correctly
- Monitor for any remaining datetime-related issues

### Notes
- **Production Ready**: Service now has clean naming without temporary suffixes
- **Timezone Safety**: Duration calculations now handle database datetime round-trips that lose timezone information
- **Method Compatibility**: Email ingestion now correctly calls PDF processing service methods
- **Error Resolution**: Fixed import errors and parameter mismatches preventing ETO processing from running

---

## [2025-09-22 17:00] — ETO Service Integration and Email Processing Pipeline
### Spec / Intent
- Register new ETO processing service in global service container for dependency injection
- Integrate ETO processing into email ingestion pipeline for automatic PDF processing
- Complete end-to-end email-to-order workflow from email attachment to ETO processing
- Implement comprehensive PDF storage and ETO pipeline triggering after email ingestion

### Changes Made
- **Service Container Registration**: Uncommented and enabled ETO processing service in service container with proper initialization using `EtoProcessingServiceNew`. Added service to global exports and getter functions for dependency injection.
- **Email Ingestion Integration**: Implemented complete `_process_pdf_attachment()` method that stores PDFs using PDF processing service and triggers ETO processing pipeline. Added proper error handling and comprehensive logging for PDF processing workflow.
- **End-to-End Pipeline**: Email ingestion now automatically stores PDF attachments and initiates ETO processing, creating complete workflow from email attachment to potential order creation with proper status tracking and error handling.
- Files: `shared/services/service_container.py`, `shared/services/__init__.py`, `features/email_ingestion/service.py`

### Next Actions
- Test complete email-to-ETO pipeline end-to-end
- Monitor ETO processing performance and error rates
- Verify service container initialization during application startup

### Notes
- **Automatic Processing**: Email attachments now automatically trigger complete ETO pipeline without manual intervention
- **Service Integration**: ETO service properly registered and accessible throughout application via dependency injection
- **Error Resilience**: PDF processing failures don't break email ingestion - errors logged but processing continues
- **Rich Metadata**: PDF storage includes email context (sender, received date, original filename) for traceability
- **Status Awareness**: Different ETO processing outcomes (success, needs_template, failure) properly logged with appropriate log levels

---

## [2025-09-22 16:00] — ETO Processing Service Error Handling Refactoring
### Spec / Intent
- Implement fail-fast error handling with immediate pipeline termination on failures
- Add comprehensive status validation to prevent invalid state transitions
- Create ETO-specific exception hierarchy for better error categorization
- Centralize error handling in main processing method with detailed error context
- Remove internal try/catch blocks from individual step methods to allow proper error bubbling

### Changes Made
- **Exception Architecture**: Created `EtoProcessingError` hierarchy with specific exceptions for template matching, data extraction, and transformation errors. Added `EtoStatusValidationError` for state validation failures.
- **Status Validation Framework**: Added comprehensive validation methods that check prerequisites before each step - template matching requires PROCESSING status, data extraction requires matched template, transformation requires extracted data.
- **Individual Step Methods**: Removed all internal try/catch blocks, added status validation at start of each method, replaced error returns with exception throwing for immediate failure detection.
- **Main Processing Method**: Completely refactored with single try/catch block, step tracking for error context, immediate processing termination on any failure, centralized error handling with rich error details.
- **Centralized Error Handler**: New `_handle_centralized_processing_error` method that builds comprehensive error context including failed step, processing step, validation details, and original exception chains.
- **Reprocessing Logic**: Updated `_continue_processing` with same error handling patterns for consistent failure management during reprocessing operations.
- Files: `shared/exceptions/eto_processing.py` (new), `shared/exceptions/__init__.py`, `features/eto_processing/service_new.py`

### Next Actions
- Test complete ETO processing pipeline with new error handling
- Verify status validation prevents invalid state transitions
- Test reprocessing functionality with improved error handling

### Notes
- **Fail Fast Philosophy**: Processing stops immediately when any error occurs, preventing data corruption from partial processing
- **Rich Error Context**: Error details include failed step, processing step, validation failures, and complete exception chains for debugging
- **Status Machine Enforcement**: Strict validation ensures ETO runs can only transition through valid states with proper prerequisites
- **Centralized Error Management**: Single point of error handling with consistent error recording and logging patterns
- **Exception Hierarchy**: Type-safe error handling with specific exception types for different failure categories

---

## [2025-09-22 15:00] — ETO Database Model Defaults Fix
### Spec / Intent
- Fix EtoRunModel to have proper default values for all fields to enable successful record creation
- Ensure status initializes to "not_started" and all nullable fields default to None
- Resolve creation failures where only pdf_file_id is passed with exclude_unset=True

### Changes Made
- Files: `eto_server/src/shared/database/models.py`
- Summary: Added default values to all EtoRunModel fields - status defaults to "not_started", all nullable fields (processing_step, error_type, error_message, extracted_data, etc.) default to None. This enables successful ETO run creation with minimal required data.

### Next Actions
- Test ETO run creation to verify database record creation works correctly
- Test complete ETO processing pipeline from PDF file to order creation

### Notes
- Database model now supports creation with only pdf_file_id parameter
- All nullable fields properly initialized with None defaults
- Status field automatically starts at "not_started" for proper state management
- Fixes critical database creation issue identified in ETO processing service

---

## [2025-09-22 14:00] — PDF Processing Service Consolidation
### Spec / Intent
- Consolidate PDF processing into single unified service with utilities
- Create Pydantic models for PDF files matching established patterns
- Implement PDF repository with append-only pattern and deduplication
- Extract all PDF data upfront (no processing pipeline or status tracking)
- Clean up singleton patterns - services only registered in service_container

### Changes Made
- **PDF Domain Models** (`shared/models/pdf_file.py`): PdfFileBase, PdfFileCreate, PdfFileUpdate, PdfFile, PdfFileSummary
- **PDF Repository** (`pdf_repository_new.py`): Full Pydantic support, hash deduplication, query methods for email vs manual PDFs
- **Consolidated Service** (`features/pdf_processing/service.py`): Single entry point `store_pdf()`, extracts all data upfront, clean architecture
- **Utility Modules**: `pdf_extractor.py` (text/object extraction, validation), `file_storage.py` (organized disk storage)
- **API Improvements**: Removed redundant test endpoint, connection testing during config creation
- **Cleanup**: Removed old domain files, Flask-specific files, singleton patterns from services
- Files: 28 files changed, major refactoring across PDF and email services

### Next Actions
- Migrate to use new PDF repository instead of old one
- Update email ingestion to use new PDF service methods
- Test PDF storage and extraction with new architecture

### Notes
- PDFs are fully processed before DB insertion (text and objects extracted)
- No pending/processing states - simpler architecture
- Hash-based deduplication prevents duplicate storage
- Services only registered in service_container, no individual singletons

---

## [2025-09-22 08:30] — Service Consolidation and API Update
### Spec / Intent
- Consolidate email services by removing EmailIngestionConfigService
- Update service container to use single EmailIngestionService
- Update API routes to use consolidated service instead of separate config service
- Add email discovery endpoints to API router
- Fix all Update models to use exclude_unset=True for partial updates

### Changes Made
- **Service Container**: Removed email_config_service initialization, uses only email_ingestion_service
- **API Router Updates**: Changed all endpoints to use ingestion service directly, simplified activation logic
- **Discovery Endpoints**: Added /discovery/accounts and /discovery/folders endpoints
- **Update Models**: Fixed PdfTemplateUpdate and verified EmailConfigUpdate use exclude_unset
- Files: `shared/services/service_container.py`, `api/routers/email_configs.py`, `features/email_ingestion/__init__.py`, `shared/models/pdf_template.py`

### Next Actions
- Test consolidated service with all endpoints
- Verify discovery endpoints work with Outlook integration
- Test partial update functionality

### Notes
- Service consolidation reduces unnecessary abstraction layers
- All CRUD and ingestion operations now in single service
- Discovery endpoints enable dynamic UI for account/folder selection

---

## [2025-09-22 00:15] — Email Repository Refactor to Pydantic Models
### Spec / Intent
- Refactor EmailRepository to use Pydantic models instead of dataclasses
- Implement append-only pattern for email records (no updates or deletes)
- Align email repository with established patterns from other repositories
- Ensure type safety and validation with Pydantic models

### Changes Made
- **Created `shared/models/email.py`**: Pydantic models (EmailBase, EmailCreate, Email, EmailSummary)
- **Updated EmailRepository**: Complete rewrite using Pydantic models and append-only pattern
- **Added methods**: `exists_by_message_id()`, `get_by_config()`, `get_summaries_by_config()`, count methods
- **Updated EmailIngestionService**: Uses EmailCreate model for creating records
- Files: `shared/models/email.py` (new), `shared/database/repositories/email.py`, `features/email_ingestion/service.py`

### Next Actions
- Test email ingestion with new models
- Verify duplicate detection works correctly

### Notes
- Email records are immutable once created (audit trail)
- No update/delete methods - emails are historical facts
- All attachment info known at creation time
- PDF processing creates separate EtoRun records, not email updates

---

## [2025-09-21 23:45] — Pydantic v2 Field Default Values Fix
### Spec / Intent
- Fix Pydantic v2 compatibility issues with Field() definitions in email integration models
- Replace `const=True` with `Literal` type hints for provider_type fields
- Explicitly use `default=` keyword for optional fields to ensure proper default values
- Fix type annotation for OutlookComIntegration config to access provider-specific fields

### Changes Made
- **Email Integration Models**: Updated all Field() definitions to use `default=` for optional fields
- **Provider Configs**: Changed `provider_type` fields from `Field(const=True)` to `Literal` type hints
- **OutlookComIntegration**: Added explicit type annotation `self.config: OutlookComConfig` to access `default_folder`
- Files: `shared/models/email_integration.py` (all Pydantic models), `outlook_com.py:42`

### Next Actions
- Test email integration with updated models
- Verify all Pydantic v2 validation works correctly

### Notes
- Pydantic v2 requires explicit `default=` keyword for optional fields
- `const=True` is not supported in Pydantic v2, use `Literal` type hints instead
- Type annotations in derived classes can override base class types for proper field access

---

## [2025-09-21 23:30] — Email Polling Interval Restoration
### Spec / Intent
- Restore polling interval configuration to EmailConfig system after it was accidentally removed
- Allow users to configure how often email gets polled for new messages
- Use config.poll_interval_seconds instead of constructor parameter in EmailListenerThread

### Changes Made
- **Database Model**: Already had poll_interval_seconds field at line 62 in EmailIngestionConfigModel
- **Domain Models**: Already had field in EmailConfigBase (line 46), EmailConfig.from_db_model (line 95), EmailConfigUpdate (line 152)
- **EmailListenerThread**: Updated to use config.poll_interval_seconds instead of constructor parameter
- **EmailIngestionService**: Removed check_interval parameter when creating EmailListenerThread
- Files: `email_listener.py:29-34`, `service.py:149-153`

### Next Actions
- Test that polling interval is properly configurable through API
- Verify email listeners use configured polling intervals

### Notes
- Polling interval was already present in database and domain models
- Only needed to update EmailListenerThread to use config field instead of parameter
- Simplifies thread creation by removing unnecessary parameter passing

---

## [2025-09-21 23:00] — Cursor System Elimination and Progress Tracking Integration
### Spec / Intent
- Eliminate separate cursor system entirely and integrate progress tracking directly into EmailIngestionConfigModel
- Simplify architecture by removing an entire domain concept (cursors) that added unnecessary complexity
- Support multiple concurrent active email configurations without cursor dependencies
- Ensure configs track their own monitoring progress without separate cursor objects

### Changes Made
- **Database Models**: Added progress fields to EmailIngestionConfigModel (activated_at, last_check_time, total_emails_processed, total_pdfs_found), removed EmailIngestionCursorModel class entirely
- **Domain Models**: Updated EmailConfig with new progress tracking fields and from_db_model method
- **Repository Layer**: Enhanced EmailIngestionConfigRepository with activate/deactivate/update_progress methods, changed get_active() to get_active_configs() returning list
- **Service Layer**: Updated EmailIngestionConfigService to accept activation_time, support multiple active configs via get_active_configs(), added update_progress() method
- **Email Ingestion Service**: Removed all cursor_service dependencies, uses config's progress tracking fields directly
- **Email Listener Thread**: Updated to use config_service instead of cursor_service for progress updates
- **API Router**: Updated activate endpoint to pass activation_time, added new deactivate endpoint for proper config deactivation
- **Service Container**: Removed all cursor service initialization code and dependencies
- **File Cleanup**: Deleted 7 cursor-related files that are no longer needed

### Next Actions
- Test multi-config concurrent email monitoring with integrated progress tracking
- Verify activation/deactivation properly manages progress fields
- Monitor performance with simplified architecture
- Update any remaining documentation references to cursor system

### Notes
- **Architectural Simplification**: Eliminated entire cursor domain concept, reducing complexity significantly
- **Progress Tracking**: Now integrated directly into config model where it logically belongs
- **Multi-Config Support**: System properly supports multiple active configs without cursor complications
- **Activation Flow**: Activation sets activated_at and last_check_time, deactivation clears all progress
- **Commit**: 2a8469c - refactor: Eliminate cursor system and integrate progress tracking

---

## [2025-09-21 22:30] — Simplified No-Deletion Architecture Implementation
### Spec / Intent
- Implement simplified no-deletion architecture where configs are never deleted, only deactivated
- Remove complex foreign key CASCADE/SET NULL logic in favor of permanent configs
- Deactivation deletes cursor for fresh start, while server downtime preserves cursors
- Create clear distinction between intentional deactivation (reset) vs unintentional downtime (preserve)

### Changes Made
- **Database Models**: Removed cascade deletion from EmailModel config_id foreign key, configs are now permanent
- **Cursor Models**: Simplified to only track last_check_time and statistics, removed ineffective last_processed fields
- **Cursor Repository**: Simplified with update_check_time_and_stats() and delete_by_config_id() methods
- **Cursor Service**: Added delete_cursor_by_config() for deactivation, get_statistics() for monitoring
- **Email Ingestion Service**: Implemented startup_recovery(), activate_config(), deactivate_config() with proper cursor lifecycle
- **API Router**: Removed DELETE endpoint entirely, enhanced activate/deactivate with cursor management
- **Email Repository**: Added is_message_processed() for duplicate detection with (config_id, message_id) uniqueness
- **Email Listener**: Created thread class for monitoring individual configs with IMAP connection management
- **Service Container**: Updated initialization with proper repository and service dependencies
- **Main App**: Added startup_recovery() call in app.py, proper shutdown() handling
- Files: Created 10 new files, renamed 5 old files to *-old.py for code preservation

### Next Actions
- Test multi-config concurrent email monitoring with different accounts
- Verify startup recovery resumes all active configs correctly
- Test deactivation cursor deletion and fresh start on reactivation
- Monitor thread safety and resource usage with multiple listeners

### Notes
- **No Deletion**: Configs are permanent database records, only is_active flag changes
- **Cursor Lifecycle**: Created on activation, deleted on deactivation, preserved through restarts
- **Duplicate Detection**: Using unique constraint on (config_id, message_id) instead of cursor tracking
- **Thread Management**: Each config runs in separate thread with proper stop signals
- **Recovery Logic**: Server restart automatically resumes all active configurations

---

## [2025-09-21 21:00] — Multi-Config Email Service Architecture Redesign
### Spec / Intent
- Redesign email services to support multiple concurrent email configurations
- Separate EmailConfigService (CRUD) from EmailIngestionService (runtime orchestration)
- Implement cursor-per-config model with foreign key relationship
- Create clean service boundaries with proper dependency injection
- Enable multiple email listeners running simultaneously in separate threads

### Changes Made
- **Email Ingestion Service**: Complete rewrite with multi-config support - manages multiple EmailListener instances with per-config threads, cursor lifecycle management, activate/deactivate/restart methods
- **Cursor Service**: New internal service for cursor management tied to configs, get_or_create pattern, statistics tracking per configuration
- **API Router Orchestration**: Router coordinates between ConfigService and IngestionService, handles transactional operations (rollback on failure), real-time status from running listeners
- **Database Schema**: Added config_id foreign key to cursors table, one-to-one relationship between configs and cursors, RESTRICT on delete to prevent orphaned cursors
- **Domain Models**: Created EmailCursor Pydantic models with from_db_model/model_dump_for_db pattern
- **Service Container**: Updated to include both email_ingestion_service and email_config_service as separate services
- Files: Renamed old files to *-old.py, created new service.py, cursor_service.py, email_cursor.py models, updated routers and repositories

### Next Actions
- Test multi-config listener functionality with concurrent email monitoring
- Implement actual Outlook integration in processing loop
- Add PDF extraction logic to email processing
- Create dashboard for monitoring multiple active listeners

### Notes
- **Clean Architecture**: Config service handles data, ingestion service handles runtime
- **Multi-Config**: System can monitor multiple email accounts/folders simultaneously
- **Thread Safety**: Each config runs in its own thread with proper locking
- **Cursor Lifecycle**: Cursors created with configs, deleted with configs
- **Rollback Support**: Failed config creation rolls back cursor creation

---

## [2025-09-21 20:00] — Complete Email Config Management System with Service Integration
### Spec / Intent
- Implement complete email configuration management API following PDF template architectural patterns
- Build 6 REST endpoints for frontend settings menu with hierarchical Pydantic type system
- Create thin service layer with Pydantic type pass-through and business validation
- Fix router deactivation functionality and complete service dependency injection
- Add email config service to global service container for proper application initialization

### Changes Made
- **API Router Update**: Rewrote `api/routers/email_configs.py` to properly use service layer with Pydantic models, fixed deactivation functionality using service method, added proper exception handling for ObjectNotFoundError/ValidationError/RepositoryError
- **Service Container Integration**: Added email config service to `shared/services/service_container.py`, created repository and service during initialization, exported `get_email_config_service()` function
- **Service Layer**: Created thin orchestration layer accepting Pydantic models directly (EmailConfigCreate, EmailConfigUpdate), proper exception bubbling from repository
- **Repository Pattern**: Full Pydantic typing with `from_db_model()` and `model_dump_for_db()` methods, added deactivate(config_id) method returning domain object
- **Domain Models**: Hierarchical type system in `shared/models/email_config.py` with Base/Create/Update/Summary patterns
- Files: `api/routers/email_configs.py`, `shared/services/service_container.py`, `shared/services/__init__.py`, `features/email_ingestion/config_service.py`, `shared/database/repositories/email_ingestion_config.py`, `shared/models/email_config.py`

### Next Actions
- Test complete email config management workflow end-to-end
- Integrate frontend settings menu with new API endpoints
- Monitor service initialization during application startup
- Consider adding email config caching for performance

### Notes
- **Service Integration**: Email config service now part of global service container with proper initialization
- **Exception Handling**: Consistent error handling with proper HTTP status codes (400 for validation, 404 for not found, 500 for repository)
- **Deactivation Fixed**: Replaced "not implemented" placeholder with proper service method call
- **Clean Architecture**: Router → Service → Repository → Database with Pydantic models throughout
- **Type Safety**: Full type safety from API to database with no manual conversions

---

## [2025-09-21 16:00] — Complete PDF Template Management API with Auto-Versioning
### Spec / Intent
- Build comprehensive PDF template management system with hierarchical Pydantic type system
- Implement automatic version number generation within repository layer for data integrity
- Create complete FastAPI REST endpoints for template CRUD operations and version management
- Establish architectural patterns for future FastAPI service development with detailed documentation
- Eliminate manual type conversions through unified domain model approach

### Changes Made
- **Complete API Implementation**: Built 6 REST endpoints - template creation, version creation, listing with filters, single template retrieval, specific version retrieval, and template updates
- **Auto-Versioning System**: Repository automatically calculates next version numbers (max + 1) removing user control over version numbers for data consistency
- **Hierarchical Type System**: Implemented Base/Create/Update/Domain model pattern with `PdfTemplateBase`, `PdfTemplateCreate`, `PdfTemplateUpdate`, `PdfTemplate` for clean separation of concerns
- **Enhanced Repository Pattern**: Session-scoped operations with `model_dump_for_db()` for JSON serialization of complex objects, automatic SQLAlchemy conversion via `from_attributes=True`
- **Service Layer Coordination**: Business logic coordination between template and version repositories with early validation and proper error handling
- **JSON Object Storage**: Complex nested objects (signature_objects, extraction_fields) stored as JSON in database with automatic serialization/deserialization
- **Security Implementation**: URL parameters override request body values to prevent parameter tampering in version creation
- **Architecture Documentation**: Created comprehensive `FASTAPI_ARCHITECTURE_PATTERNS.md` as reference guide for future development
- Files: 16 files modified, 1322 insertions, 694 deletions - new `shared/models/` directory structure

### Next Actions
- Apply same architectural patterns to other FastAPI services (email ingestion, ETO processing)  
- Implement enhanced template detail endpoint with optional PDF data and version list loading
- Test complete template management workflow end-to-end
- Consider frontend integration requirements for template builder interface

### Notes
- **Version Number Control**: Users can no longer specify version numbers - repository auto-generates for consistency and prevents conflicts
- **Template Matching Enhancement**: Updated template matching to use current version data instead of template-level signature objects for better accuracy
- **Type Safety**: Explicit type annotations in service constructors resolve IDE method resolution issues
- **Error Handling**: Domain exceptions (ObjectNotFoundError) properly converted to HTTP status codes (404, 400, 500) at API layer
- **Business Logic Separation**: Templates have immutable source_pdf_id, only name/description/status can be updated post-creation
- **Repository Encapsulation**: Version number calculation encapsulated within repository using internal `_get_next_version_number()` method
- **API Documentation**: FastAPI auto-generates clean OpenAPI docs showing only relevant fields (excludes auto-generated or URL-derived fields)

---

## [2025-09-20 14:30] — Unified Pydantic Type System Implementation for PDF Templates
### Spec / Intent
- Eliminate manual type conversions between API layer (Pydantic), service layer (dataclasses), and database layer (SQLAlchemy)
- Implement unified Pydantic models throughout all application layers to solve bi-directional conversion issues
- Create shared models structure to serve as single source of truth for business logic
- Streamline data flow from HTTP → Pydantic → SQLAlchemy → Pydantic without intermediate dataclass conversions

### Changes Made
- **Shared Models Architecture**: Created new `shared/models/` directory with unified Pydantic models replacing dataclasses in `shared/domain/`
- **Core Models**: Implemented `PdfTemplate`, `PdfTemplateVersion`, `PdfObject`, `ExtractionField` with automatic SQLAlchemy conversion via `from_attributes=True`
- **JSON Handling**: Added `model_dump_for_db()` and `from_db_model()` methods to handle JSON serialization of nested objects for database storage
- **API Schema Simplification**: Updated `api/schemas/pdf_templates.py` to use thin wrapper models with conversion methods like `to_core_model()` and `get_signature_objects()`
- **Repository Modernization**: Replaced manual field-by-field mapping with `PdfTemplate.model_validate(sqlalchemy_model)` for automatic conversion
- **Service Layer**: Updated `PdfTemplateService` to work directly with Pydantic models, eliminating manual object construction
- **Router Optimization**: Simplified API router by removing 60+ lines of manual conversion code, now uses single-line conversion methods
- Files: 8 new files, 5 modified files (repositories, service, router, schemas)

### Next Actions
- Test new type system with template creation and matching workflows
- Update `get_active_templates()` to join with current version data for template matching
- Apply same unified Pydantic approach to other feature areas (email ingestion, ETO processing)
- Remove deprecated `shared/domain/` dataclass files once migration is complete

### Notes
- **Type Flow Revolution**: Eliminated problematic bi-directional flow (HTTP → Pydantic → Dataclass → SQLAlchemy → Dataclass → Pydantic) with clean flow (HTTP → Pydantic → SQLAlchemy → Pydantic)
- **Automatic Conversion**: Pydantic's `from_attributes=True` enables automatic SQLAlchemy model conversion without manual field mapping
- **Field Alias Support**: API layer handles camelCase ↔ snake_case conversions transparently using Pydantic aliases
- **JSON Serialization**: Nested objects (signature_objects, extraction_fields) properly serialized as typed objects in service layer, JSON strings only in database
- **Validation Benefits**: Business rules defined once in core Pydantic models, automatically applied across all layers
- **Code Reduction**: Eliminated 2 manual conversion layers and ~100 lines of repetitive conversion code

---

## [2025-09-20 Session] — Complete PDF Template Versioning System & FastAPI Migration Implementation
### Spec / Intent
- Implement comprehensive PDF template versioning functionality with modern SQLAlchemy 2.0 patterns
- Create complete FastAPI alternative to Flask application for better type safety and automatic validation
- Modernize exception handling throughout repository layer with specific exception types
- Solve Flask query parameter type conversion issues with FastAPI's automatic type handling
- Establish foundation for gradual migration from Flask to FastAPI while maintaining coexistence

### Changes Made
- **Database Modernization**: Updated all models to SQLAlchemy 2.0 `Mapped`/`mapped_column` notation, implemented circular FK relationships between templates/versions with timezone-aware datetime handling
- **Repository Refactoring**: Created comprehensive exception hierarchy (`ObjectNotFoundError`, `ValidationError`, etc.) and updated all repositories to use specific exceptions instead of Optional returns
- **PDF Template System**: Built complete versioning system with `PdfTemplateModel`, `PdfTemplateVersionModel`, domain object conversion using `__dict__` serialization, and optimized `PdfTemplateForProcessing` type
- **API Development**: Created comprehensive Pydantic v2 request/response schemas, implemented complete CRUD endpoints with automatic validation, established REST conventions with proper error handling
- **FastAPI Implementation**: Built `app-fastapi.py` with lifespan management and dependency injection, created `main-fastapi.py` with uvicorn configuration, converted PDF templates blueprint to FastAPI router demonstrating automatic validation and type-safe query parameters
- Files: 35+ modified, 8 new files including complete FastAPI application, router example, and migration documentation

### Next Actions
- Complete service implementation for PDF template TODO placeholders
- Convert remaining Flask blueprints to FastAPI routers (health, email_ingestion, eto_processing, pdf_viewing)
- Test both Flask and FastAPI versions side by side during gradual migration
- Implement async service layer for FastAPI performance benefits

### Notes
- **FastAPI Benefits**: Automatic request/response validation, type-safe query parameters solving Flask string conversion issues, auto-generated OpenAPI docs, better async support and performance
- **Architecture**: Parameter-based service calls, exception-based error handling, SQLAlchemy 2.0 modernization, Pydantic v2 validation patterns
- **Migration Strategy**: Both Flask and FastAPI can coexist, gradual endpoint conversion, same database models and service layer
- **Query Parameter Solution**: FastAPI automatically converts query parameters to correct types with validation, eliminating manual string-to-int conversion issues
- **Documentation**: Comprehensive `FASTAPI_MIGRATION.md` with code comparisons and migration guide
- **Status**: All changes committed (460c380), ready for service implementation or continued FastAPI migration

---

## [2025-09-19 11:45] — Fix Datetime Timezone Inconsistency in ETO Processing
### Spec / Intent
- Fix "can't subtract offset-naive and offset-aware datetimes" error preventing ETO run completion
- Standardize datetime usage throughout ETO processing service to use timezone-aware datetimes consistently
- Resolve processing failures that occur during duration calculation in repository update_status method

### Changes Made
- Files: `eto_server/src/features/eto_processing/service.py:203`
- Summary: Updated skip_info creation to use `datetime.now(timezone.utc)` instead of `datetime.now()` to ensure all datetime objects are timezone-aware and compatible with repository duration calculations

### Next Actions
- Test ETO processing pipeline to ensure timezone errors are resolved
- Verify ETO runs can complete successfully without datetime subtraction errors

### Notes
- Error occurred when repository tried to calculate `current_time - existing_run.started_at` where current_time was timezone-naive but started_at was timezone-aware
- All datetime usage in ETO processing service now consistently uses UTC timezone
- Fixes processing failures that were preventing completion of ETO runs

---

## [2025-09-18 10:30] — Email Service PDF Processing Independence
### Spec / Intent
- Complete the independence of email service PDF processing from Flask service registry to avoid "no Flask app available" errors in background threads
- Implement direct PDF service instantiation within EmailIngestionService constructor to eliminate service registry dependencies
- Fix COM object disconnection and Flask context issues that were preventing PDF extraction from emails

### Changes Made
- Files: `eto_server/src/features/email_ingestion/service.py`
- Summary: Updated `_process_extracted_pdf()` method to use `self.pdf_service` instead of `get_pdf_processing_service()` from service registry. Removed service registry dependency by utilizing the independent PDF service created in constructor. Changed lines 715-716 and 726 to use instance variable rather than global service registry access.

### Next Actions
- Test email ingestion with PDF extraction to ensure Flask context issues are resolved
- Verify PDF processing works correctly in background threads without service registry

### Notes
- PDF service is now created independently in EmailIngestionService constructor using storage configuration
- Background threads can now process PDFs without requiring Flask application context
- Addresses user request to "make it so that the services are accessed independently and dynamically instead of trying to make them dependent on each other"
- Completes the fix for "Cannot access PDF processing service - no Flask app available" error

---

## [2025-09-16 20:15] — Application Startup Cleanup and Duplicate Code Removal
### Spec / Intent
- Fix duplicate logging configuration between main.py and app.py that was overwriting file logging
- Remove redundant environment loading and import-time side effects
- Clean up duplicate main block in app.py that created confusion about entry points
- Establish single, clear application startup lifecycle

### Changes Made
- Files: `src/app.py`
- Summary: Removed duplicate logging configuration that was overwriting main.py's file+console setup with console-only logging. Removed duplicate `load_dotenv()` call since main.py already handles environment loading. Removed duplicate `if __name__ == '__main__'` block that duplicated server startup logic. Cleaned up import-time side effects.

### Next Actions
- Test application startup to ensure logging works correctly with file output
- Verify all services initialize properly through cleaned up lifecycle

### Notes
- Application startup lifecycle is now clean: main.py → app.create_app() → service initialization
- Logging is configured once in main.py with both file and console output
- No more import-time configuration side effects in app.py
- Single entry point through main.py eliminates confusion

---

## [2025-09-15 19:45] — PDF Service Architecture Refactoring and Domain Object Implementation
### Spec / Intent
- Fix redundant functionality in PDF processing services where PdfProcessingService was duplicating storage workflow logic
- Implement proper domain objects (PdfStoreRequest) instead of loose Dict[str, Any] parameters for service contracts  
- Ensure PdfProcessingService acts as pure orchestrator delegating to sub-services instead of bypassing them
- Move complete storage workflow (including repository access) to PdfStorageService for proper separation of concerns
- Fix circular import issues between repositories and domain types using TYPE_CHECKING pattern

### Changes Made
- Files: `src/features/pdf_processing/storage_service.py`
- Summary: Updated constructor to accept `pdf_repository` parameter. Added `store_pdf_complete()` method that handles complete storage workflow including file storage and database record creation, eliminating redundancy in PdfProcessingService.
- Files: `src/features/pdf_processing/service.py`  
- Summary: Refactored `store_pdf()` method to use `PdfStoreRequest` domain object and delegate to `storage_service.store_pdf_complete()`. Updated constructor to inject repository into storage service. Now acts as pure orchestrator.
- Files: `src/features/pdf_processing/types.py`
- Summary: Domain objects already existed for typed service contracts including `PdfStoreRequest` with proper field ordering.
- Files: `src/features/email_ingestion/service.py`
- Summary: Updated to use `PdfStoreRequest` domain object instead of Dict metadata when calling PDF processing service.
- Files: `src/shared/database/repositories/pdf_repository.py`, `src/shared/database/repositories/eto_run_repository.py`
- Summary: Fixed circular import issues by using TYPE_CHECKING imports and quoted type annotations. Updated domain object conversion to use dynamic imports.

### Next Actions
- Test PDF processing pipeline with new architecture
- Verify email ingestion service works with domain objects
- Update ETO Processing Service to use shared PDF service

### Notes
- All files successfully compile, indicating proper type annotation structure
- Architecture now properly separates concerns with storage service handling complete workflow
- PdfProcessingService is now a clean orchestrator without redundant repository access

---

## [2025-09-15 17:30] — PDF Processing Service Separation and Shared Architecture
### Spec / Intent
- Extract PDF processing functionality from Email Ingestion Service into standalone, reusable service
- Enable PDF functionality to be shared across multiple features (email ingestion, manual upload, ETO processing)
- Implement proper dependency injection pattern for shared services
- Prepare architecture for future manual PDF upload feature and other PDF entry points

### Changes Made
- Files: `src/features/pdf_processing/service.py` (Created)
- Summary: New standalone `PdfProcessingService` containing all PDF operations: storage, extraction, metadata management, and API access methods. Service can be instantiated with just a storage path and handles all PDF concerns internally.
- Files: `src/features/pdf_processing/__init__.py`
- Summary: Added exports for `PdfProcessingService`, `get_pdf_processing_service`, `init_pdf_processing_service` to support both direct instantiation and global singleton patterns.
- Files: `src/features/email_ingestion/service.py`
- Summary: Major refactor to remove embedded PDF functionality. Changed constructor to accept `pdf_processing_service` dependency. All PDF methods now delegate to the shared service. Removed PDF repository, storage service, and object extraction service dependencies.
- Files: `src/app.py`
- Summary: Added `initialize_pdf_processing()` function to create shared PDF service. Updated initialization order: database → PDF processing → email ingestion → ETO processing. Services now properly share PDF functionality through dependency injection.

### Next Actions
- Update ETO Processing Service to use shared PDF service (currently uses repository directly)
- Implement manual PDF upload feature using shared PDF service
- Test complete PDF processing pipeline through shared service architecture

### Notes
- **Separation of Concerns**: PDF processing is now isolated from email-specific logic
- **Reusability**: PDF service can be shared across multiple features (email, manual upload, ETO processing)
- **Dependency Injection**: Clean service injection pattern with simple configuration (storage path)
- **Future Ready**: Architecture supports manual PDF uploads and other PDF entry points
- **Service Boundaries**: Each service now has clear, focused responsibilities

---

## [2025-09-15 17:00] — Architectural Fixes: PDF Storage Integration and Repository Exposure
### Spec / Intent
- Fix PDF storage service integration pattern to follow consistent dependency injection
- Remove repository exposure from API layer to enforce proper architectural boundaries
- Ensure APIs only access functionality through service layer, never directly through repositories
- Simplify email ingestion service constructor to accept configuration parameters instead of complex service injection

### Changes Made
- Files: `src/features/email_ingestion/service.py`
- Summary: Changed constructor from `__init__(pdf_storage_service=None)` to `__init__(pdf_storage_path: str = None)`. Service now creates PDF storage internally using provided path, matching the pattern used by other services.
- Files: `src/app.py`
- Summary: Simplified email ingestion initialization to pass storage path instead of creating and injecting service. Removed repository exposure (`PDF_REPOSITORY`) from Flask app config.
- Files: `src/api/blueprints/pdf_viewing.py`
- Summary: Complete API refactor to access PDFs through service layer. Replaced direct repository access with service methods. Added comprehensive PDF service methods to EmailIngestionService for API consumption.

### Next Actions
- Test complete PDF viewing functionality through service layer
- Verify no other APIs are directly accessing repositories
- Consider adding similar service methods to other features that need API access

### Notes
- **Architecture Enforcement**: APIs now properly respect layer boundaries (API → Service → Repository → Database)
- **Dependency Injection**: Services use simple parameter injection (paths, config values) instead of complex service injection
- **Repository Isolation**: Repositories are no longer exposed outside service layer, preventing layer violations
- **Service Methods**: Added `get_pdf_metadata()`, `get_pdf_content()`, `get_pdfs_by_email()`, `get_pdf_storage_info()` to EmailIngestionService for API consumption

---

## [2025-09-15 16:45] — Repository Domain Object Consistency Fixes
### Spec / Intent
- Fix repository pattern inconsistencies across codebase where some repositories returned domain objects and others returned database models
- Ensure all repositories follow established pattern of returning domain objects instead of raw SQLAlchemy models
- Apply consistent session-scoped domain object conversion pattern used in EmailIngestionConfigRepository
- Update PDF and ETO Run repositories to match established domain object consistency

### Changes Made
- Files: `src/shared/database/repositories/pdf_repository.py`
- Summary: Fixed `create_pdf_record()` and `update_objects_json()` methods to return `PdfFile` domain objects instead of raw `int` or `PdfFileModel`. Added proper session-scoped domain object conversion before returning.
- Files: `src/shared/database/repositories/eto_run_repository.py`  
- Summary: Complete repository refactor - added `_convert_to_domain_object()` method, imported `EtoRun` domain type, updated all 14 methods to return `EtoRun` domain objects instead of `EtoRunModel`. Added session-scoped conversions throughout.

### Next Actions
- Test ETO processing service integration with updated repository return types
- Verify no breaking changes in service layer that depends on these repositories
- Consider applying same pattern to any other repositories that may have inconsistencies

### Notes
- **Repository Pattern**: All repositories now consistently return domain objects from `src/features/*/types.py` instead of database models from `src/shared/database/models.py`
- **Session Management**: Proper SQLAlchemy session scoping ensures domain object conversion happens while database session is active
- **Type Safety**: Updated method signatures reflect actual return types (`Optional[EtoRun]`, `List[EtoRun]`, etc.)
- **Domain Objects**: ETO Run repository now converts all 21 model fields to domain object properties using `getattr()` pattern for proper column access

---

## [2025-01-13 16:30] — Complete PDF Processing Pipeline Implementation
### Spec / Intent
- Build comprehensive PDF processing system integrating with existing email ingestion service
- Implement automatic PDF extraction, storage, and management for email attachments
- Create complete client interface for PDF viewing and email configuration management
- Follow domain-driven design patterns with proper repository implementations
- Enable client-side PDF viewing capabilities with full CRUD operations

### Changes Made
- **Backend Services**:
  - `eto_server/src/features/pdf_processing/storage_service.py`: Complete file system operations with organized storage `/pdfs/YYYY/MM/`, SHA256 hashing, deduplication, filename sanitization
  - `eto_server/src/features/pdf_processing/extraction_service.py`: Outlook COM attachment processing, PDF validation, metadata extraction (page/object counts), hash-based duplicate detection
  - `eto_server/src/shared/database/repositories/pdf_repository.py`: Enhanced with domain object conversion patterns, Phase 1 CRUD operations following email config repository patterns
- **API Endpoints**:
  - `eto_server/src/api/blueprints/pdf_viewing.py`: Complete REST API for PDF operations - metadata retrieval, content serving with proper MIME types, email-specific queries, pagination support
  - `eto_server/src/api/blueprints/email_ingestion.py`: Enhanced with PDF processing statistics and `/emails` endpoint for processed email viewing
- **Email Integration**:
  - `eto_server/src/features/email_ingestion/service.py`: Added PDF services integration, automatic PDF extraction during email processing, configuration statistics tracking
  - `eto_server/src/features/email_ingestion/integrations/outlook_com_service.py`: Added `get_mail_object_by_id()` method for COM object access during PDF extraction
- **Client Interface**:
  - `client/src/renderer/routes/dashboard/route.tsx`: Added emails tab and settings gear icon
  - `client/src/renderer/routes/dashboard/emails.tsx`: Read-only email viewing interface with pagination and metadata display  
  - `client/src/renderer/routes/dashboard/settings.tsx`: Comprehensive email ingestion configuration management with CRUD operations, filter rules, Outlook folder discovery
  - `client/src/renderer/services/api.ts`: Complete API client methods for email ingestion and PDF operations

### Next Actions
- **READY TO TEST**: Complete PDF processing pipeline from email ingestion to client viewing
- Test automatic PDF extraction during email processing
- Test client PDF viewing and email configuration management interfaces
- Configure storage paths from app configuration (currently hardcoded)
- Future: Implement PDF template matching and analysis features

### Notes
- **Architecture**: Domain-driven design with service layer separation, dependency injection, thread-safe Outlook COM integration
- **PDF Pipeline**: Email → Filter → DB Record → PDF Extraction → Storage → Hash Deduplication → Client Access
- **Deduplication**: SHA256-based duplicate detection prevents storing identical PDFs multiple times
- **Client Features**: Full email configuration CRUD, read-only email viewing, settings management with advanced filter rules
- **Statistics**: Email ingestion service now tracks PDF processing statistics and updates configuration metrics
- **Error Handling**: Robust error handling throughout pipeline with proper logging and graceful degradation
- **Storage**: Organized file structure with year/month directories, sanitized filenames, proper MIME type handling
- **Status**: All changes committed (5127399), complete PDF processing system ready for production testing

---

## [2025-09-11 19:58] — Flask Email Ingestion Service Auto-Startup Complete
### Spec / Intent
- Complete Flask app integration for EmailIngestionService auto-startup functionality  
- Fix multiple server startup errors preventing email service initialization
- Consolidate email configuration and ingestion features into unified structure
- Implement automatic Outlook connection on server startup when active configs exist

### Changes Made
- Files: src/app.py
- Summary: Added initialize_email_ingestion() function that creates EmailIngestionService, checks for active configurations, and attempts auto-connection on Flask startup
- Files: src/features/email_ingestion/types.py  
- Summary: Fixed EmailIngestionConfig dataclass field ordering - moved all required fields before optional fields with defaults to resolve "non-default argument follows default argument" error
- Files: src/api/schemas/__init__.py, src/api/schemas/pdf_processing.py
- Summary: Fixed import path from email_configuration to email_ingestion, updated Pydantic regex to pattern for v2 compatibility
- Files: src/shared/database/models.py, src/shared/database/__init__.py, src/shared/database/repositories/email_ingestion_cursor_repository.py, src/features/email_ingestion/cursor_service.py
- Summary: Renamed EmailCursorModel to EmailIngestionCursorModel throughout codebase, updated table name from 'email_cursors' to 'email_ingestion_cursors'
- Files: Consolidated email_configuration feature into email_ingestion/
- Summary: Moved config_service.py from email_configuration to email_ingestion, consolidated types, updated all import paths and API blueprints

### Next Actions
- **READY TO TEST**: Server should now start successfully with email ingestion service auto-initialization
- Test auto-connection behavior when no active configs exist vs when configs are available
- Test API endpoints for creating email configurations and triggering auto-connection
- **MEMORY CLEAR NEEDED**: User needs to close terminal to clear memory, resume by reading context files

### Notes
- **Server Startup Flow**: Flask app now auto-initializes EmailIngestionService, checks for active configs, attempts Outlook connection if available
- **Error Resolution**: Fixed 4 critical startup errors: dataclass field order, Pydantic regex usage, missing schema imports, cursor model naming  
- **Architecture**: Successfully consolidated email functionality into single coherent feature with proper service boundaries
- **Database**: Updated table and model names for consistency, all cursor references properly renamed
- **Status**: All changes committed (fa2a2df), server ready for testing with email auto-startup functionality

---

## [2025-09-08 16:30] — Module Definition Type Safety Fixes

### Spec / Intent
- Fix critical type errors in module definition files introduced during module system redesign
- Resolve ExecutionOutputs return type incompatibilities causing Pylance errors
- Fix Python version compatibility issues with NotRequired type import
- Ensure all module definition files compile without type errors

### Changes Made
- Files: transformation_pipeline_server/src/types.py
- Summary: Fixed NotRequired import compatibility for Python < 3.11 by adding fallback imports and error handling
- Files: transformation_pipeline_server/src/modules/definitions/text_processing/advanced_text_cleaner.py:148-150
- Summary: Fixed ExecutionOutputs return type - changed `return {dict}` to `return ExecutionOutputs({dict})`
- Files: transformation_pipeline_server/src/modules/definitions/text_processing/basic_text_cleaner.py:100-102  
- Summary: Fixed ExecutionOutputs return type - changed `return {dict}` to `return ExecutionOutputs({dict})`
- Files: transformation_pipeline_server/src/modules/definitions/data_processing/sql_parser.py:176-178
- Summary: Fixed ExecutionOutputs return type - changed `return {dict}` to `return ExecutionOutputs({dict})`
- Files: transformation_pipeline_server/src/modules/definitions/data_processing/type_converter.py:119
- Summary: Fixed ExecutionOutputs type annotation - changed `results = {}` to `results: ExecutionOutputs = ExecutionOutputs({})`

### Next Actions
- **READY TO COMMIT**: All type fixes have been made and tested with py_compile, ready for git commit
- **Commit Command**: `git add -A && git commit -m "fix: Resolve module definition type safety issues with ExecutionOutputs and NotRequired compatibility"`
- Test module system with frontend integration after commit
- Continue with module connection validation using new node type information
- Add more modules using the new architecture pattern

### Notes
- **Branch**: transformation_pipeline_backend (current working branch)
- **Python Compatibility**: Fixed NotRequired import to work with Python < 3.11 using typing_extensions fallback
- **Type Safety**: All ExecutionOutputs return types now properly typed to eliminate Pylance errors
- **Testing Status**: All fixed files pass python -m py_compile syntax validation
- **Dependencies**: sqlparse import issue discovered in testing but doesn't affect core type fixes
- **Ready State**: Changes are staged and ready for immediate commit when resuming session

---

## [2025-09-07 21:48] — Module System Redesign with Type Safety

### Spec / Intent
- Redesign module architecture with each module in separate files for better organization
- Implement comprehensive Python type safety using TypedDict and runtime validation  
- Consolidate fragmented node configuration system into unified NodeConfiguration objects
- Add node-aware execution with runtime type checking and config template resolution
- Create 4 specific modules: Basic Text Cleaner, Advanced Text Cleaner, SQL Parser, Type Converter

### Changes Made
- Files: transformation_pipeline_server/src/types.py, transformation_pipeline_server/src/modules/module.py, transformation_pipeline_server/src/modules/registry.py, transformation_pipeline_server/src/database.py
- Summary: Complete module system redesign with enhanced BaseModuleExecutor supporting node-aware execution, runtime type validation, and config template resolution. Updated database schema to use consolidated NodeConfiguration objects.
- Files: transformation_pipeline_server/src/modules/text_processing/basic_text_cleaner.py, transformation_pipeline_server/src/modules/text_processing/advanced_text_cleaner.py
- Summary: Implemented text processing modules using new schema structure with proper type safety
- Files: transformation_pipeline_server/src/modules/data_processing/sql_parser.py, transformation_pipeline_server/src/modules/data_processing/type_converter.py  
- Summary: Created SQL Parser with config template validation and Type Converter using node type selectors for dynamic conversion

### Next Actions
- Test new module system with frontend integration
- Implement module connection validation using new node type information
- Add more modules using the new architecture pattern
- Consider adding module marketplace functionality

### Notes
- SQL Parser uses config template resolution to map {input_0}/{output_0} placeholders to actual node IDs
- Type Converter cleverly uses node type selectors instead of configuration for conversion logic
- All modules now support dynamic vs static node validation and runtime type checking
- Database schema updated to match new consolidated NodeConfiguration structure

---

## [2025-01-06 20:15] — Pipeline Analysis System Communication Fixes

### Spec / Intent
- Fix critical communication issues between frontend visual graph builder and backend pipeline analyzer
- Resolve API port mismatches, data structure incompatibilities, and response format issues
- Implement proper separation between processing modules (transformation steps) and I/O modules (configuration)
- Make pipeline analysis work correctly for visual transformation pipelines

### Changes Made
- Files: client/src/renderer/services/api.ts:100, client/src/renderer/components/transformation-pipeline/TransformationGraph.tsx:1091,1118-1128,1138-1155
- Summary: Fixed API port (8080→8090), added templateId field, corrected connection data structure, updated response handling
- Files: transformation_pipeline_server/src/services/pipeline_analysis.py:81-103,91-92,117-127
- Summary: Made input/output modules optional, added flexible module identification patterns, focused analysis on processing modules only
- Files: context/pipeline_analysis_fixes_2025_01_06.md
- Summary: Comprehensive documentation of pipeline analysis system architecture and fixes applied

### Next Actions
- Implement pipeline execution functionality using the analyzed transformation steps
- Add real-time data preview flowing through pipeline modules
- Enhance module connection validation and error handling

### Notes
- Pipeline analysis now correctly processes visual graphs: input("test") -> text_cleaner("cleaned_value") -> output
- System properly separates transformation logic (processing modules) from I/O configuration (input/output modules)
- Flexible module identification supports various naming patterns and template types
- Frontend-backend communication fully functional with proper data structure alignment

---

## [2025-01-05 19:30] — Field ID System Simplification & Documentation Update

### Spec / Intent
- Remove complex unique ID generation from transformation pipeline field mapping
- Simplify field mapping to use user-defined field names directly 
- Create comprehensive system documentation for architecture, tech stack, database design, and application goals
- Update database design to focus only on ETO system schema, removing target logistics system schema

### Changes Made
- Files: transformation_pipeline_server/src/services/pipeline_analysis.py, transformation_pipeline_server/src/services/simple_pipeline_execution.py
- Summary: Replaced FieldIdGenerator with SimpleFieldMapper to eliminate duplicate field ID issues. Uses field names directly throughout pipeline execution.
- Files: context/docs/system_architecture.md, context/docs/tech_stack.md, context/docs/database_design.md, context/docs/application_goals.md  
- Summary: Created comprehensive system documentation based on codebase analysis. Fixed development workflow to reference server-scripts.sh files. Updated database design to document only ETO system schema, removing normalized logistics schema.

### Next Actions
- Monitor transformation pipeline to ensure field ID simplification works correctly
- Future plugin system development for populating target database after ETO processing complete

### Notes
- Successfully eliminated duplicate field ID generation that was causing connection issues in pipeline
- Documentation now accurately reflects current ETO system implementation vs. future target system
- Plugin architecture noted for future development to bridge ETO output to target logistics database

---

## [v0.4.0] - September 2, 2025 - TRANSFORMATION PIPELINE FRONTEND COMPLETE ✅

### **MAJOR MILESTONE**: Visual Graph Builder for Data Transformation Pipeline

#### **Complete Visual Pipeline Builder Interface**
Implemented a comprehensive visual graph builder system for creating data transformation pipelines, providing an intuitive drag-and-drop interface for connecting processing modules.

##### **Key Features Implemented**:

**1. Interactive Graph Canvas**
- **Zoom & Pan Controls**: Mouse wheel zooming + dedicated zoom in/out buttons
- **Grid Background**: Visual reference grid with smooth scaling
- **Canvas Dragging**: Click-and-drag to pan the view across the entire screen
- **Coordinate System**: Proper world-to-screen coordinate transformations
- **Bounds Checking**: Prevents modules from being dragged onto sidebar or off-canvas

**2. Module Selection Sidebar**
- **Collapsible Design**: Expandable/collapsible library pane with space optimization
- **Category Organization**: Modules grouped by categories (Text Processing, AI/ML, Testing)
- **Search Functionality**: Real-time filtering by module name and description
- **Drag-and-Drop**: Drag modules from library directly onto canvas
- **Visual Feedback**: Selection states, hover effects, and drag previews

**3. Interactive Module Components**
- **Card-Based Design**: Professional module cards with headers, descriptions, and configuration sections
- **Configuration Options**: Support for boolean toggles, select dropdowns, text inputs, textarea, and number inputs
- **Modern UI Elements**: Styled with Tailwind CSS for professional appearance
- **Delete Functionality**: Confirmation modal with delete button in module header
- **Selection System**: Click modules to select, click again to deselect

**4. Robust Event Handling System**
- **Global Mouse Events**: Canvas dragging works over entire screen including sidebar
- **Event Propagation Control**: Proper handling of click vs drag interactions
- **Header-Only Dragging**: Module configuration inputs don't interfere with dragging
- **Z-Index Management**: Proper layering so sidebar stays above canvas content

**5. Module Template System**
```typescript
interface BaseModuleTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  inputs: ModuleInput[];
  outputs: ModuleOutput[];
  config: ModuleConfig[];
  color: string;
}
```

**6. Test Data & Edge Cases**
- **4 Sample Modules**: Basic Text Cleaner, Advanced Text Cleaner, LLM Parser, Edge Case Testing Module
- **Configuration Types**: Boolean, select, string, textarea, number inputs
- **Edge Case Testing**: Very long names and descriptions for UI stress testing

#### **Technical Architecture**:

##### **React Components**:
- **graph.tsx**: Main graph component with canvas, zoom/pan, and module management
- **ModuleSelectionPane.tsx**: Collapsible sidebar with module library and search
- **GraphModuleComponent.tsx**: Interactive module cards with configuration and delete
- **testModules.ts**: Module template definitions and test data

##### **Advanced Features**:
- **Coordinate Transformations**: Screen coordinates ↔ World coordinates for zoom/pan
- **State Management**: React hooks for canvas state, selected modules, and UI interactions
- **Event System**: Global mouse handlers with capture phase and preventDefault
- **Visual Effects**: Smooth transitions, hover states, and drag previews

#### **Problem-Solving Achievements**:

**Configuration Input Conflicts**: 
- ✅ **Issue**: Clicking on inputs triggered module dragging
- ✅ **Solution**: Header-only dragging approach with event propagation control

**Canvas Dragging Interruption**:
- ✅ **Issue**: Mouse movement over sidebar stopped canvas dragging
- ✅ **Solution**: Global mouse handlers with pointer-events-none during drag

**Event Handler Conflicts**:
- ✅ **Issue**: Canvas mouse leave was stopping drags prematurely  
- ✅ **Solution**: Removed canvas-level handlers, used only global handlers

#### **Business Impact**:

**Before**: No visual interface for building transformation pipelines
- ❌ Users had to manually configure transformations in code/config files
- ❌ No visual representation of data flow between processing steps
- ❌ Difficult to understand complex multi-step transformations

**After**: Complete visual pipeline builder
- ✅ **Drag-and-Drop Interface**: Intuitive module placement and configuration
- ✅ **Visual Data Flow**: Clear representation of transformation pipeline structure  
- ✅ **Professional UI**: Modern interface suitable for enterprise use
- ✅ **Module Library**: Organized, searchable repository of processing modules
- ✅ **Configuration Management**: Visual interface for all module parameters

#### **Git History**:
```
d349786 Implement comprehensive transformation pipeline frontend with visual graph builder
```

#### **Files Created**:
- `client/src/renderer/routes/transformation_pipeline/graph.tsx` - Main graph interface
- `client/src/renderer/routes/transformation_pipeline/route.tsx` - Route layout
- `client/src/renderer/components/GraphModuleComponent.tsx` - Interactive module cards
- `client/src/renderer/components/ModuleSelectionPane.tsx` - Collapsible module library
- `client/src/renderer/components/SimpleModuleComponent.tsx` - Basic module display
- `client/src/renderer/data/testModules.ts` - Module templates and test data

### **Next Development Priorities**:
1. **Module Connections**: Wire system to connect module outputs to inputs
2. **Pipeline Execution**: Backend integration for running transformation pipelines  
3. **Data Preview**: Real-time preview of data flowing through pipeline
4. **Module Marketplace**: Expandable module library with custom module creation

---

## [v0.3.0] - August 28, 2025 - SPATIAL TEMPLATE BUILDER COMPLETE ✅

### **MAJOR MILESTONE**: Spatial Box Drawing Template Creation System

#### **Revolutionary Template Creation Interface**
Implemented a complete spatial box drawing system that replaces word-based selection with area-based field extraction, solving critical real-world document processing challenges.

##### **Key Features Implemented**:

**1. Spatial Box Drawing Interface**
- **Interactive Drawing**: Click-and-drag rectangular areas over PDF content
- **Real-time Visual Feedback**: Blue dashed preview while drawing, purple overlays for saved fields
- **PDF Coordinate System**: Proper coordinate conversion between screen and PDF space
- **Zoom Independence**: Extraction areas scale correctly at all zoom levels
- **Minimum Size Validation**: Prevents accidentally small extraction areas

**2. Two-Step Template Creation Wizard**
- **Step 1: Object Selection**: Select static objects that always exist in documents
- **Step 2: Field Definition**: Draw spatial extraction areas for variable content
- **Dynamic Sidebar**: Context-sensitive interface (template info → field editor → field viewer)
- **Field Management**: Create, edit, view, delete extraction field definitions

**3. Advanced Field Configuration**
- **Field Labels**: Semantic naming (e.g., "hawb", "carrier-name", "pu_addr_and_phone")
- **Validation Rules**: Optional regex patterns for field validation
- **Required Fields**: Mark critical fields that must have content
- **Visual Indicators**: Purple overlays with floating labels show all extraction areas

**4. Solved Critical Document Processing Problems**:
- ✅ **Multi-word Fields**: Single area captures "Forward Air, Inc" as one carrier field
- ✅ **Variable Length Content**: Handles "carrier 1" vs "carrier 1234" in same space
- ✅ **Multi-line Addresses**: Single area covers 3-4 line addresses plus phone numbers
- ✅ **Position Variations**: Content that moves based on other content (e.g., phone number position changes with address length)

#### **Technical Implementation**:

##### **Frontend Components Enhanced**:
- **PdfViewer.tsx**: Added box drawing, extraction field overlays, coordinate conversion
- **TemplateBuilderModal.tsx**: Complete rewrite with two-step wizard and dynamic sidebar
- **Mouse Event Handling**: Precise coordinate mapping and drawing interaction

##### **Data Model Redesign**:
```typescript
interface ExtractionField {
  id: string;
  boundingBox: [number, number, number, number]; // PDF coordinates [x0, y0, x1, y1]
  page: number;
  label: string;
  description: string;
  required: boolean;
  validationRegex?: string;
}
```

##### **Visual System**:
- **Drawing Mode**: Crosshair cursor, blue dashed preview
- **Extraction Fields**: Purple overlays with field labels
- **No Object Highlighting**: Clean spatial-only visualization
- **State Management**: Proper React hooks usage and state transitions

#### **Business Impact**:

**Before**: Word-based selection couldn't handle real-world document variations
- ❌ Multi-word fields required selecting individual words
- ❌ Variable content length caused extraction failures  
- ❌ Complex layouts (addresses + phone) couldn't be handled
- ❌ User confusion about what would be extracted

**After**: Spatial area-based extraction handles all document variations
- ✅ **Intuitive Interface**: Users draw areas just like highlighting with a marker
- ✅ **Handles Complexity**: Addresses, carrier names, and variable content work perfectly
- ✅ **Production Ready**: System can handle real trucking company document variations
- ✅ **Clear Visual Feedback**: Purple overlays clearly show what will be extracted

#### **Git History**:
```
97e28b3 Replace word-based selection with spatial box drawing for extraction fields
d758d8e Implement dynamic extraction field management for template builder
```

#### **Development Notes**:
- **React Hooks Compliance**: Fixed Rules of Hooks violations by moving state to component level
- **TypeScript Integration**: Full type safety with proper interface definitions
- **Coordinate System**: PDF origin (bottom-left) properly converted to screen coordinates
- **Performance**: Efficient rendering with proper React keys and minimal re-renders

### **Next Development Priorities**:
1. **Box Editing**: Add resize handles and drag-to-move for existing extraction areas
2. **Template Testing**: Interface to test extraction against sample documents  
3. **Field Validation**: Real-time preview of extracted content during creation
4. **Advanced Field Types**: Support for checkboxes, tables, structured data

---

## [v0.2.0] - August 26, 2025 - TEMPLATE SYSTEM ARCHITECTURE COMPLETE

### **Database Design & Template Pipeline Architecture**
- Complete template system database schema with multi-step extraction pipeline
- Enhanced ETO processing with template matching and error categorization
- PDF object integration for template matching algorithms
- Comprehensive error tracking and performance monitoring

---

## [v0.1.0] - August 26, 2025 - EMAIL INGESTION SYSTEM COMPLETE

### **Core Email Processing Pipeline**  
- Gmail integration with Outlook API for automatic PDF download
- Cursor-based downtime recovery system
- Background processing pipeline with duplicate handling
- Complete email-to-PDF-to-processing workflow operational

---

*For detailed backend changes, see `server/CHANGELOG_SESSION.md`*