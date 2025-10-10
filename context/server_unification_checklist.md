# Server Unification Checklist
**Migration: eto_server → transformation_pipeline_server**

This checklist tracks the progress of merging the eto_server into transformation_pipeline_server to create a unified system.

---

## Root Directory Files - Merge Configuration and Setup Files

- [ ] **Root directory files - Merge configuration and setup files**
  - [X] `.env` - Merge environment variables from both servers
  - [X] `requirements.txt` - Merge Python dependencies
  - [X] `Makefile`

---

## Application Core

- [X] **src/app.py - Merge application initialization and startup logic**

---

## API Layer Merge

- [ ] **src/api/ - API layer merge**
  - [ ] **src/api/routers/ - Add ETO routers to transformation pipeline**
    - [ ] `email_configs.py` - Copy from eto_server
    - [ ] `eto.py` - Copy from eto_server
    - [ ] `pdf_templates.py` - Copy from eto_server
    - [ ] Update `__init__.py` to export all routers
  - [ ] **src/api/schemas/ - Add ETO schemas**
    - [ ] `common.py` - Copy from eto_server
    - [ ] `eto.py` - Copy from eto_server
    - [ ] `pdf_templates.py` - Copy from eto_server
    - [ ] Update `__init__.py` to export all schemas

---

## Features Layer Merge

- [ ] **src/features/ - Features layer merge**
  - [ ] `src/features/email_ingestion/` - Copy entire directory from eto_server
  - [ ] `src/features/eto_processing/` - Copy entire directory from eto_server
  - [ ] `src/features/pdf_processing/` - Copy entire directory from eto_server
  - [ ] `src/features/pdf_templates/` - Copy entire directory from eto_server
  - [ ] Update `src/features/__init__.py` to export ETO features

---

## Database Layer Merge

- [ ] **src/shared/database/ - Database layer merge**
  - [ ] `src/shared/database/models.py` - Merge all database models (ETO + Pipeline)
  - [ ] `src/shared/database/connection.py` - Verify compatibility
  - [ ] **src/shared/database/repositories/ - Add ETO repositories**
    - [ ] `email.py` - Copy from eto_server
    - [ ] `email_config.py` - Copy from eto_server
    - [ ] `eto_run.py` - Copy from eto_server
    - [ ] `pdf_file.py` - Copy from eto_server
    - [ ] `pdf_template.py` - Copy from eto_server
    - [ ] `pdf_template_version.py` - Copy from eto_server
    - [ ] Update `__init__.py` to export all repositories

---

## Exceptions Merge

- [ ] **src/shared/exceptions/ - Exceptions merge**
  - [ ] `domain.py` - Copy from eto_server
  - [ ] `eto_processing.py` - Copy from eto_server
  - [ ] `service.py` - Copy from eto_server
  - [ ] Update `__init__.py` to export all exceptions

---

## Services Merge

- [ ] **src/shared/services/ - Services merge**
  - [ ] `service_container.py` - Add ETO services to existing container
  - [ ] Update `__init__.py` to export service container

---

## Types/Models Merge

- [ ] **src/shared/types/ - Types/Models merge**
  - [ ] **Copy ETO models from shared/models/ to shared/types/**
    - [ ] `email.py` - Copy and adapt
    - [ ] `email_config.py` - Copy and adapt
    - [ ] `email_integration.py` - Copy and adapt
    - [ ] `eto_run.py` - Copy and adapt
    - [ ] `pdf_file.py` - Copy and adapt
    - [ ] `pdf_processing.py` - Copy and adapt
    - [ ] `pdf_template.py` - Copy and adapt
    - [ ] `status.py` - Copy and adapt
    - [ ] `pipeline.py` - Copy and adapt (if no conflicts)
  - [ ] Update `src/shared/types/__init__.py` to export all types

---

## Utils Merge

- [ ] **src/shared/utils/ - Utils merge**
  - [ ] `datetime.py` - Copy from eto_server
  - [ ] `storage_config.py` - Copy from eto_server
  - [ ] Update `__init__.py` to export all utils

---

## Application Startup Updates

- [ ] **Update app.py startup - Add ETO worker initialization**
  - [ ] Add email ingestion startup recovery
  - [ ] Add ETO worker auto-start with config flag
  - [ ] Add graceful shutdown for workers

---

## Application Metadata Updates

- [ ] **Update app.py metadata - Change to Unified ETO Server**
  - [ ] Update title to 'Unified ETO Server'
  - [ ] Update description to include both systems
  - [ ] Update info endpoint with all endpoints

---

## Database Migrations

- [ ] **Database migrations - Create migration for ETO tables**

---

## Testing

- [ ] **Testing - Verify all systems work together**
  - [ ] Test pipeline execution
  - [ ] Test module management
  - [ ] Test email ingestion
  - [ ] Test ETO processing
  - [ ] Test PDF processing
  - [ ] Test PDF templates

---

## Documentation

- [ ] **Documentation - Update README and docs**

---

## Notes

### Key Design Decisions
- Using transformation_pipeline_server as the base (better ServiceContainer design)
- Moving ETO models from `shared/models/` to `shared/types/` (better naming)
- Keeping ETO's worker management patterns (startup recovery, graceful shutdown)
- Merging best logging features from both servers

### Service Container Updates Needed
Add to `ServiceContainer._register_service_definitions()`:
- `email_ingestion` service
- `eto_processing` service
- `pdf_processing` service
- `pdf_template` service

### Database Models to Merge
**ETO Models (8):**
- EmailModel
- EmailConfigModel
- ETORunModel
- PDFFileModel
- PDFTemplateModel
- PDFTemplateVersionModel

**Pipeline Models (5):**
- ModuleCatalogModel
- PipelineDefinitionModel
- PipelineDefinitionStepModel
- PipelineExecutionRunModel
- PipelineExecutionStepModel

**Total: 13 models in unified system**

---

## Progress Tracking

**Total Tasks:** 71
**Completed:** 0
**In Progress:** 0
**Remaining:** 71

---

*Last Updated: 2025-10-10*
