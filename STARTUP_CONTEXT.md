# ETO System - Startup Context

**Last Updated**: January 26, 2025 at 3:47 PM EST  
**Current Branch**: `email_ingestion_service`  
**Server**: `http://localhost:8080`

---

## **CRITICAL BEHAVIORS FOR EVERY CONVERSATION**

### **🚀 Conversation Startup (MANDATORY)**
- **ALWAYS** read `server/CHANGELOG_SESSION.md` after reading this startup context
- **IMMEDIATELY** provide a detailed summary of where we left off in the most recent conversation
- Include current status, completed tasks, pending issues, and next steps from the changelog
- This summary helps maintain continuity across conversations

### **📝 Changelog Management (MANDATORY)**
- **ALWAYS** update `server/CHANGELOG_SESSION.md` during EVERY conversation
- Add new context, progress, issues encountered, and resolutions to the current session section
- Update session status and next steps
- Document any code changes, bug fixes, or new features implemented
- Track current todo items and their completion status

### **🔄 Git Commit Behavior**
- Ask user "Do you want me to commit these changes?" whenever changes are substantial enough
- Substantial changes include: new features, bug fixes, configuration changes, multiple file edits
- Use proper commit message format with Claude Code attribution
- Always run `git status` and `git diff` before proposing commits
- Never commit without explicit user approval

### **📋 Task Management**
- Always use `TodoWrite` tool for tracking tasks throughout conversations
- Mark tasks as `in_progress` before starting work
- Mark tasks as `completed` immediately after finishing
- Update todos based on new issues discovered or user requests

---

## **Project Overview**

### **System Purpose**
Email-to-Order (ETO) PDF processing system that:
- Monitors Gmail for emails with PDF attachments
- Extracts structured data from PDF documents  
- Processes orders/documents through template matching
- Provides REST API for system management and data access
- Maintains cursor-based email tracking for downtime recovery

### **Current Architecture**
```
Gmail Email → Outlook COM → PDF Storage → Object Extraction → Template Matching → Data Extraction
     ↓              ↓             ↓              ↓                ↓                ↓
Database Cursor → Email Table → PDF Files → PDF Objects → ETO Runs → Extracted Data
```

---

## **Current System State**

### **✅ What's Working**
- **Email Ingestion**: Successfully monitoring `em.harrah.business@gmail.com` in "test" folder
- **PDF Processing**: Extracting thousands of objects from multi-page PDFs (8434 objects from 18-page test)
- **Cursor Tracking**: Downtime recovery and missed email processing
- **Background Workers**: Processing ETO runs asynchronously
- **Template Matching**: Correctly identifying PDFs that need templates
- **Duplicate Handling**: Same PDF in different emails processed separately
- **Database Schema**: Full SQLAlchemy models with proper relationships

### **⚙️ Current Configuration**
- **Target Email**: `em.harrah.business@gmail.com`
- **Target Folder**: `test`
- **Server Port**: `8080`
- **Database**: SQL Server with `eto_new` database
- **Storage Path**: `./storage` for PDF files
- **Processing**: Email-centric (not PDF-centric) approach

### **🔧 System Components**
1. **Flask Server** (`src/app.py`) - REST API endpoints
2. **Email Service** (`src/outlook_service.py`) - Gmail monitoring via COM
3. **Database Layer** (`src/database.py`) - SQLAlchemy models and connections
4. **PDF Storage** (`src/pdf_storage.py`) - File system management
5. **PDF Extractor** (`src/pdf_objects.py`) - Object extraction from PDFs
6. **Template Matcher** (`src/template_matching.py`) - Document classification
7. **Processing Worker** (`src/processing_worker.py`) - Background job processing

---

## **Key API Endpoints**

### **Email Management**
- `POST /api/email/start` - Start email monitoring with cursor recovery
- `POST /api/email/stop` - Stop email monitoring
- `GET /api/email/cursor` - View cursor status and statistics

### **System Status**
- `GET /health` - Server health check
- `GET /api/system/stats` - Database and storage statistics
- `GET /api/eto-runs` - View processing runs with email context

### **Testing & Development**
- `GET /api/recent-emails` - View recent processed emails

---

## **Current Priority Tasks**

### **Next Steps (From Changelog)**
1. **Test server restart and cursor recovery** with multiple emails containing same PDF
2. **Verify template creation workflow** for PDFs marked as "needs_template"  
3. **Test complete end-to-end processing pipeline**

### **Future Development Phase**
- Wire up client application for template creation from unrecognized PDFs
- Implement actual data extraction functionality (currently placeholder)
- Build template creation UI for PDFs marked as "needs_template"

---

## **Development Guidelines**

### **🚨 Important Rules**
- **Server Management**: User handles all server starting/stopping/testing - DO NOT use Bash to start servers
- **Code Conventions**: Always check existing code style and follow patterns
- **Database**: Never assume schema - always check current state
- **File Edits**: Always use Read tool before editing files
- **Design Evaluation**: Provide accurate, balanced assessments of code and design quality. Be neither overly critical nor overly praising. Focus on objective analysis of strengths, weaknesses, and improvement opportunities based on actual technical merit.

### **🔍 Before Starting Work**
1. Check current git status with `git status`
2. Review `server/CHANGELOG_SESSION.md` for latest context
3. Use TodoWrite to plan tasks if complex work is needed
4. Read relevant files to understand current state

### **💾 File Locations**
- **Main Server**: `server/src/app.py`
- **Email Processing**: `server/src/outlook_service.py`
- **Database Models**: `server/src/database.py`  
- **Session Changelog**: `server/CHANGELOG_SESSION.md`
- **Environment Config**: `server/.env`
- **Database Scripts**: `server/scripts/create-database.py`

---

## **Known Issues & Status**

### **✅ Recently Resolved**
- Database connection and schema issues
- Timezone handling in cursor comparisons
- Duplicate PDF constraint conflicts
- Email processing during downtime recovery

### **⚠️ Watch Out For**
- COM interface can be unstable - automatic reconnection implemented
- SQL Server authentication with 'test' user credentials
- Timezone-aware vs naive datetime comparisons
- Background worker thread management

---

## **Testing Approach**

### **Quick Start Command**
When user asks for "email service start testing request":
```bash
curl -X POST http://localhost:8080/api/email/start \
  -H "Content-Type: application/json" \
  -d '{"email_address": "em.harrah.business@gmail.com", "folder_name": "test"}'
```

### **Comprehensive Testing Protocol**
**Process**: After each step, check database to verify proper ingestion.

1. **Basic Service Test**: Start email service, send one email with unique PDF
2. **Real-time Processing**: With service running, send two emails with unique PDFs  
3. **Duplicate Handling (Live)**: With service running, send two emails (one duplicate PDF, one unique)
4. **Simple Downtime Recovery**: Stop email service, send one email with unique PDF, start email service
5. **Multiple Missed Emails**: Stop email service, send two emails with unique PDFs, start email service
6. **Duplicate During Downtime**: Stop email service, send two emails (one duplicate PDF, one unique), start email service
7. **Full Server Restart**: Stop server, send two emails (one duplicate PDF, one unique), start server, start email service

### **Manual Testing Workflow**
1. User starts server manually
2. Call `/api/email/start` with configuration
3. System processes missed emails first (cursor recovery)
4. System monitors for new real-time emails
5. Verify processing through `/api/eto-runs` and `/api/system/stats`

### **Test Scenarios**
- Server restart with missed emails
- Same PDF in multiple emails
- Template creation workflow
- Complete pipeline from email → extracted data

---

**Remember**: Update this file and the changelog during every conversation!