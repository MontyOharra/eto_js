# 🏗️ ETO Processing Implementation Plan

## Overview
This document outlines the complete implementation plan for porting the proven ETO processing functionality from `eto_js/server` to the new unified `eto_server` architecture, leveraging advanced patterns like repository design, feature-based structure, and domain-driven design.

## Current State
- **eto_js/server**: Complete working ETO processing pipeline with template matching, data extraction, and transformation
- **eto_server**: Advanced email ingestion with immediate PDF extraction, but missing ETO processing components
- **Goal**: Bridge the gap by implementing ETO processing in the new architecture

---

## Phase 1: Core ETO Processing Service Architecture

### 1.1 ETO Processing Service (`src/features/eto_processing/service.py`)
**Port from:** `eto_js/server/src/processing_worker.py`
- Background worker service with threading
- Polls `EtoRunModel` records with status `NOT_STARTED`
- Orchestrates 3-step pipeline: template_matching → data_extraction → data_transformation
- Uses repository pattern for database operations
- Integrates with Flask app lifecycle

### 1.2 ETO Run Repository Enhancement (`src/shared/database/repositories/eto_run_repository.py`)
**Add missing methods:**
- `get_pending_runs()` - Get runs with status `NOT_STARTED`
- `update_processing_step()` - Update status and processing step atomically
- `mark_as_failed()` - Set failure status with error details
- `get_runs_by_status()` - Filter by processing status

---

## Phase 2: Template Matching Engine

### 2.1 Template Matching Service (`src/features/eto_processing/template_matching_service.py`)
**Port from:** `eto_js/server/src/template_matching.py`
- Exact subset matching algorithm for PDF objects
- Spatial bounding box field extraction
- Template coverage calculation
- Repository-based template operations

### 2.2 Template Repository Enhancement (`src/shared/database/repositories/template_repository.py`)
**Add methods:**
- `get_all_active_templates()` - Get templates for matching
- `get_template_with_extraction_fields()` - Include extraction field definitions
- `update_usage_statistics()` - Track template usage
- `search_by_signature_objects()` - Find templates by object signatures

---

## Phase 3: Data Extraction Engine

### 3.1 Data Extraction Service (`src/features/eto_processing/data_extraction_service.py`)
**New service based on template matching logic:**
- Spatial bounding box field extraction from PDF objects
- Multi-step extraction rules processing
- Field validation and transformation
- Error handling and fallback mechanisms

### 3.2 Extraction Rule Repository (`src/shared/database/repositories/extraction_rule_repository.py`)
**New repository for template extraction rules:**
- `get_rules_by_template()` - Get extraction rules for template
- `get_steps_by_rule()` - Get ordered extraction steps
- `update_step_performance()` - Track execution times
- `get_failed_steps()` - Get steps that commonly fail

---

## Phase 4: Auto-Trigger Integration

### 4.1 PDF → ETO Run Creation (`src/features/email_ingestion/service.py`)
**Enhance existing service:**
- After PDF record creation, automatically create `EtoRunModel`
- Set initial status as `NOT_STARTED`
- Link to email_id and pdf_file_id
- Trigger immediate processing if worker is running

### 4.2 ETO Processing Integration (`src/app.py`)
**Service registration and startup:**
- Initialize ETO processing service after email ingestion
- Start background worker thread
- Graceful shutdown handling
- Service health monitoring

---

## Phase 5: Data Transformation Pipeline

### 5.1 Transformation Service (`src/features/eto_processing/transformation_service.py`)
**New service for data transformation:**
- Apply business rules to extracted data
- Data validation and normalization
- Target format transformation (order structure)
- Audit trail creation

### 5.2 Pipeline Module Integration (`src/features/pipeline_execution/`)
**Leverage existing transformation pipeline:**
- Connect ETO extracted data to transformation modules
- Dynamic pipeline execution
- Rule-based data processing
- Output validation

---

## Phase 6: Service Orchestration & Monitoring

### 6.1 ETO Processing Manager (`src/features/eto_processing/manager.py`)
**High-level orchestration service:**
- Coordinate all ETO processing services
- Handle service dependencies and initialization
- Monitor processing health and performance
- Restart failed processing jobs

### 6.2 Processing Status Service (`src/features/eto_processing/status_service.py`)
**Real-time status tracking:**
- Track processing queue depth
- Monitor success/failure rates
- Performance metrics collection
- Alert handling for stuck jobs

---

## Phase 7: Error Handling & Recovery

### 7.1 Error Recovery Service (`src/features/eto_processing/error_recovery_service.py`)
**Intelligent error handling:**
- Retry logic for transient failures
- Dead letter queue for repeated failures
- Manual intervention workflows
- Error pattern analysis

### 7.2 Processing Retry Logic
**Built into ETO Processing Service:**
- Exponential backoff for retries
- Max retry limits
- Error categorization (template_missing, extraction_failed, etc.)
- Manual reprocess capability via API

---

## Phase 8: Integration Points

### 8.1 Email Ingestion Integration
```python
# In email_ingestion/service.py after PDF creation:
if pdf_record:
    eto_run = self.eto_run_repo.create({
        'email_id': email_id,
        'pdf_file_id': pdf_record['id'], 
        'status': 'not_started'
    })
    logger.info(f"Created ETO run {eto_run.id} for PDF {pdf_record['id']}")
```

### 8.2 Flask App Integration
```python
# In app.py initialization:
from src.features.eto_processing import EtoProcessingManager

eto_manager = EtoProcessingManager(
    connection_manager=get_connection_manager(),
    pdf_storage_service=pdf_storage_service
)
eto_manager.start()
```

### 8.3 API Enhancement
**Existing API endpoints** (`src/api/blueprints/eto_processing.py`) already exist

**Add endpoints:**
- `POST /api/eto-runs/process-all` - Trigger bulk processing
- `GET /api/eto-runs/queue-status` - Get processing queue status
- `POST /api/eto-runs/{id}/force-retry` - Force retry failed run

---

## Phase 9: Configuration & Settings

### 9.1 Processing Configuration (`src/features/eto_processing/config.py`)
**Configuration management:**
- Worker thread pool size
- Polling intervals
- Retry limits and backoff settings
- Template matching thresholds

### 9.2 Environment Variables (`.env`)
```bash
# ETO Processing Settings
ETO_WORKER_ENABLED=true
ETO_POLL_INTERVAL=10
ETO_MAX_RETRIES=3
ETO_TEMPLATE_MATCH_THRESHOLD=0.6
ETO_BATCH_SIZE=5
```

---

## Phase 10: Testing & Validation

### 10.1 Unit Tests
- Template matching algorithm tests
- Data extraction validation
- Error handling scenarios
- Repository operation tests

### 10.2 Integration Tests
- End-to-end PDF → Order processing
- Service startup/shutdown
- Error recovery workflows
- Performance under load

---

## Implementation Priority Order

1. **Phase 1** - Core service architecture (foundation)
2. **Phase 2** - Template matching (core algorithm)
3. **Phase 4** - Auto-trigger integration (immediate value)
4. **Phase 3** - Data extraction engine
5. **Phase 6** - Service orchestration
6. **Phase 5** - Data transformation
7. **Phase 7** - Error handling
8. **Phases 8-10** - Integration, config, testing

---

## Technical Notes

### Key Architecture Decisions
- Use repository pattern for all database operations
- Maintain separation of concerns between services
- Leverage existing infrastructure (connection manager, logging, etc.)
- Port proven algorithms while adapting to new patterns
- Ensure backwards compatibility with existing API endpoints

### Performance Considerations
- Background processing to avoid blocking email ingestion
- Batch processing for efficiency
- Configurable polling intervals
- Resource management for PDF processing operations

### Error Handling Strategy
- Comprehensive error categorization
- Retry mechanisms with exponential backoff
- Dead letter queue for manual intervention
- Detailed logging and audit trails

---

## Success Criteria

1. **Functional**: Complete PDF → Order processing pipeline working
2. **Performance**: Comparable or better performance than original system
3. **Reliability**: Robust error handling and recovery mechanisms
4. **Maintainability**: Clean architecture following established patterns
5. **Monitoring**: Full visibility into processing status and performance
6. **Integration**: Seamless integration with existing email ingestion

---

*This plan builds upon the proven functionality of the original eto_js/server implementation while leveraging the advanced architectural patterns of the new eto_server system.*