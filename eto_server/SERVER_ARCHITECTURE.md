# ETO Server Architecture

This document outlines the complete architecture of the unified ETO server, including API design, database architecture, and system organization.

## API Endpoints

The unified ETO server provides 47 endpoints organized across 9 blueprints for clean separation of concerns.

### Health Blueprint
**Base URL**: `/`

- `GET /health` - Unified health check with service identification

### Email Blueprint  
**Base URL**: `/api/emails`

- `POST /api/emails/start` - Start email monitoring with optional email/folder specification
- `POST /api/emails/stop` - Stop email monitoring and disconnect from Outlook
- `GET /api/emails/status` - Get current email monitoring status
- `GET /api/emails/recent` - Get recent emails for testing (with limit parameter)
- `GET /api/emails/cursor` - Get email cursor information for current session
- `GET /api/emails` - Get recent email records from database

### Templates Blueprint
**Base URL**: `/api/templates`

- `GET /api/templates` - Get PDF templates with filtering and pagination
- `POST /api/templates` - Create a new PDF template
- `POST /api/templates/reprocess` - Manually trigger reprocessing of unrecognized runs
- `GET /api/templates/<int:template_id>/view` - Get detailed template data for viewing

### PDF Files Blueprint
**Base URL**: `/api/pdf`

- `GET /api/pdf/<int:pdf_id>` - Serve PDF file by ID
- `GET /api/pdf/<int:pdf_id>/objects` - Get extracted PDF objects by PDF ID
- `GET /api/pdf/<int:pdf_id>/debug` - Debug PDF file paths
- `GET /api/pdf/<int:pdf_id>/download` - Download PDF file by ID

### ETO Runs Blueprint
**Base URL**: `/api/eto-runs`

- `GET /api/eto-runs` - Get ETO processing runs with filtering
- `GET /api/eto-runs/<int:run_id>/processing-details` - Get detailed processing information for an ETO run
- `POST /api/eto-runs/<int:run_id>/skip` - Skip an ETO run (mark as skipped status)
- `DELETE /api/eto-runs/<int:run_id>` - Permanently delete an ETO run and associated data
- `POST /api/eto-runs/<int:run_id>/reprocess` - Reprocess a skipped ETO run (reset to not_started status)
- `GET /api/eto-runs/<int:run_id>/pdf-data` - Get complete PDF data (file + objects) for an ETO run
- `GET /api/eto-runs/<int:run_id>/extraction-results` - Get extraction results for a successful ETO run

### Modules Blueprint
**Base URL**: `/api/modules`

- `POST /api/modules/populate` - Populate database with all registered base modules
- `GET /api/modules` - Get all available base modules from database
- `POST /api/modules/<module_id>/execute` - Execute a specific module

### Pipelines Blueprint
**Base URL**: `/api/pipeline`

- `POST /api/pipeline/analyze` - Analyze pipeline for execution planning with steps
- `POST /api/pipeline/execute` - Execute complete transformation pipeline (simple)
- `POST /api/pipeline/validate` - Validate pipeline structure and requirements
- `POST /api/pipeline/execute-steps` - Execute pipeline using step-based dependency analysis

### System Blueprint
**Base URL**: `/api`

- `GET /api/system/stats` - Get comprehensive system statistics (database counts, storage stats, monitoring status)
- `GET /api/processing/stats` - Get processing worker statistics
- `POST /api/test/extract-fields` - Test field extraction from PDF using template
- `POST /api/test/template-match` - Test if PDF matches template (debugging)

### Processing Blueprint
**Base URL**: `/api/processing`

- `POST /api/processing/start` - Start background processing worker
- `POST /api/processing/stop` - Stop background processing worker
- `GET /api/processing/status` - Get processing worker status and statistics
- `POST /api/processing/trigger` - Manually trigger processing of pending runs

## Database Architecture

The ETO server uses a clean, layered database architecture with strict separation of concerns.

### **Connection Management**

#### **DatabaseConnectionManager**
- **Purpose**: Manages SQL Server connections and session creation
- **Key Features**:
  - Thread-safe singleton pattern
  - SQL Server optimized connection pooling
  - Fail-fast design - never creates databases
  - Credential masking in logs
  - Session lifecycle management with context managers

```python
# Usage in application services
connection_manager = init_database_connection(database_url)
with connection_manager.session_scope() as session:
    # Automatic transaction management
```

#### **DatabaseCreator (Script Utilities)**
- **Purpose**: Database and table creation for scripts only
- **Key Methods**:
  - `create_database_with_tables()` - Complete database setup
  - `reset_database()` - Drop and recreate everything
  - `create_tables()` - Create tables from models
  - `database_exists()` - Check database status

### **Repository Layer**

Clean data access layer with one repository per model:

#### **BaseRepository**
- Abstract base class with common CRUD operations
- Generic typing for type safety
- Consistent session management

#### **Specific Repositories**
- `EmailRepository` - Email records and queries
- `PdfRepository` - PDF file operations
- `TemplateRepository` - Template management
- `EtoRunRepository` - Processing run tracking
- `ModuleRepository` - Transformation modules
- `PipelineRepository` - Pipeline definitions
- `CursorRepository` - Email cursor management

### **Database Models**

#### **Email Processing Models**
- `Email` - Email records from Outlook monitoring
- `PdfFile` - PDF files extracted from emails
- `PdfTemplate` - PDF templates for pattern matching
- `TemplateExtractionRule` - Multi-step data transformation rules
- `TemplateExtractionStep` - Individual transformation steps
- `EtoRun` - ETO processing run tracking
- `EmailCursor` - Email processing cursors for recovery

#### **Transformation Pipeline Models**
- `BaseModule` - Developer-defined transformation modules
- `Pipeline` - Data transformation pipeline definitions

### **Service Layer Integration**

Application services receive repositories directly (not through a monolithic database service):

```python
# Clean dependency injection
class OutlookService:
    def __init__(self, email_repo: EmailRepository, pdf_repo: PdfRepository):
        self.email_repo = email_repo
        self.pdf_repo = pdf_repo

# Each service only gets the repositories it needs
outlook_service = OutlookService(email_repo, pdf_repo, eto_repo)
template_service = TemplateMatchingService(template_repo, pdf_repo)
```

### **Database Management Scripts**

#### **Scripts Organization**
```
scripts/
└── database/
    ├── manage-database.sh      # Bash interface
    └── database_manager.py     # Python implementation
```

#### **Usage Examples**
```bash
# Create database with all tables
./scripts/database/manage-database.sh create

# Reset database (development)
./scripts/database/manage-database.sh reset --confirm

# For build scripts (non-interactive)
./scripts/database/manage-database.sh reset --confirm --silent
```

#### **Integration with Build Scripts**
```bash
# In server-scripts.sh
case "$1" in
    "resetdb")
        ./eto_server/scripts/database/manage-database.sh reset "$@"
        ;;
esac
```

### **Key Design Principles**

1. **Separation of Concerns**: Connection management, data access, and business logic are cleanly separated
2. **SQL Server First**: No fallback databases, proper error handling for missing databases
3. **Fail-Fast**: Connection manager never creates databases - scripts handle database lifecycle
4. **Direct Repository Usage**: Application services use repositories directly, not through a monolithic service
5. **Thread Safety**: All components safe for Flask multi-threading
6. **Script Automation**: Database operations easily integrated into build and deployment workflows

## Implementation Status

**Current Status**: Core Database Architecture Complete
- ✅ All blueprint files created with proper URL prefixes
- ✅ All 47 endpoints defined with function stubs
- ✅ Flask application factory configured
- ✅ **Database connection architecture implemented**
- ✅ **Repository layer with type-safe CRUD operations**
- ✅ **Unified database models (10 tables)**
- ✅ **Database management scripts for automation**
- ✅ **SQL Server integration with proper error handling**
- ⏳ Repository implementations - *Pending*
- ⏳ Application service layer - *Pending*
- ⏳ Blueprint functionality implementation - *Pending*

## Next Steps

1. Implement repository CRUD operations
2. Create application service layer for business logic
3. Implement core functionality for each blueprint
4. Add authentication and security middleware
5. Add comprehensive error handling and logging
6. Set up background processing workers
7. Integrate with existing modules system