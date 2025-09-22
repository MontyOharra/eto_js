# Next Steps - PDF Processing Service Migration

## Current State (2025-09-22)
We've completed a major refactoring of the PDF processing and email ingestion services:
- ✅ Created Pydantic models for all domain objects
- ✅ Consolidated services to reduce abstraction layers
- ✅ Implemented new PDF repository with proper patterns
- ✅ Created utility modules for PDF extraction and file storage
- ✅ Removed singleton patterns from services

## Immediate Next Steps

### 1. Complete PDF Repository Migration
The new PDF repository (`pdf_repository_new.py`) needs to replace the old one:
- Rename `pdf_repository_new.py` to `pdf_repository.py`
- Update imports in service_container.py
- Remove the old pdf_repository.py file

### 2. Update Email Ingestion Service
The email ingestion service needs to use the new PDF service methods:
- Update `store_pdf()` calls to use new signature (file_content, original_filename, email_id)
- Remove any references to old PDF domain objects
- Update to use new PdfFile model instead of old domain objects

### 3. Database Migration
Create migration for pdf_files table if needed:
- The new models expect `email_id` field (nullable)
- Ensure `extracted_text` and `objects_json` columns exist
- Check indexes on `file_hash` for deduplication

### 4. API Updates
Update PDF-related API endpoints:
- Use new PdfFile models in responses
- Update any endpoints that create PDFs to use new service methods
- Test PDF viewing endpoints with new service

### 5. Testing
Test the complete flow:
- Email ingestion → PDF extraction → Storage
- Manual PDF upload (when implemented)
- PDF retrieval and viewing
- Template creation from PDFs

## Architecture Decisions Made

### Service Consolidation
- Single service per domain (EmailIngestionService, PdfProcessingService, etc.)
- Services handle all operations for their domain
- No separate config/runtime services

### PDF Processing
- PDFs are fully processed upfront (no async/background processing)
- All text and objects extracted before DB insertion
- Hash-based deduplication at service level
- Organized file storage: pdfs/YYYY/MM/

### Domain Models
- All models use Pydantic for validation
- Repository pattern with domain object conversion
- Append-only patterns for audit trails (emails, PDFs)
- Update models use `exclude_unset=True` for partial updates

### Service Registration
- All services registered in service_container only
- No singleton patterns in individual services
- Services initialized during app startup

## Files to Review
1. `shared/models/pdf_file.py` - New PDF domain models
2. `shared/database/repositories/pdf_repository_new.py` - New repository implementation
3. `features/pdf_processing/service.py` - Consolidated PDF service
4. `features/pdf_processing/utils/` - Extraction and storage utilities
5. `features/email_ingestion/service.py` - Consolidated email service

## Known Issues
- Old pdf_repository.py still exists alongside pdf_repository_new.py
- Service container imports may need updating after repository rename
- Some imports still reference old domain objects that were deleted

## Environment Notes
- Working directory: C:\Users\Owner\Software_Projects\eto_js
- Branch: server_unification
- Python environment uses Pydantic v2
- Using pdfplumber for PDF extraction