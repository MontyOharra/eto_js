# CHANGELOG

## [2025-11-11] — VBA to Modern System Comparison Analysis

### Spec / Intent
- Analyze current TypeScript/Python codebase to understand ingestion and template matching functionality
- Compare with legacy VBA/MS Access system documented in VBA analysis
- Identify discrepancies and missing functionalities between systems
- Create comprehensive comparison document for migration planning

### Changes Made
- Files Created:
  - `docs/version_comparison/ingestion-and-templates.md` - Comprehensive VBA vs Modern system comparison (1029 lines)

### Analysis Completed

**Current System Analysis** (via Explore agent):
- Template system architecture (versioning, signature objects, extraction fields)
- Document ingestion/processing (pdfplumber, PDF object extraction)
- Template matching algorithm (fuzzy matching, ranked results, bbox-based)
- Data extraction (bbox-based, multiple strategies)
- Pipeline system (Dask execution, visual builder, module catalog)
- Complete ETO workflow (matching → extraction → pipeline execution)
- Database schema (PostgreSQL with JSONB)
- Frontend architecture (React, TypeScript, React Flow)
- Backend architecture (FastAPI, Pydantic, async workers)

**VBA System Analysis** (from existing documentation):
- HTC350C_1of2_Translation (1,653 lines) - main orchestrator
- Character-by-character pattern matching (14 hard-coded formats)
- Line/char position-based data extraction
- 10+ format-specific parser functions
- File system-based workflow
- Access forms for UI
- WhosLoggedIn session locking
- 31-day retention policy with file deletion

### Key Findings

#### ✅ Modern System Advantages:
1. **Version Control** - Immutable template versions, comparison, rollback
2. **Visual Pipeline Builder** - Drag-and-drop, live simulation, reusable modules
3. **Fuzzy Matching** - Confidence scores, OCR tolerance, ranked results
4. **Scalability** - Parallel workers, no hard limits (VBA had 1000 PDF max)
5. **Modern Architecture** - Service-based, API-first, Docker containers
6. **Multi-user Web UI** - Accessible anywhere, real-time collaboration
7. **Type Safety** - Pydantic/TypeScript validation throughout

#### ⚠️ Missing from Modern System:
1. **Pre-built Document Handlers** - VBA has 14 format parsers (SOS Routing, BOL variants, Alert, MAWB, etc.)
   - Modern system has generic template system but zero pre-built templates
   - **Action Required**: Create templates for each VBA format in template builder

2. **Multi-Delivery Alert Expansion** - VBA `prep_AllParsedPDFs()` expands Alerts with multiple delivery receipts
   - **Action Required**: Implement as custom pipeline module

3. **31-Day Retention Policy** - VBA auto-deletes old logs and files
   - **Action Required**: Add scheduled job for retention/archival

4. **Single-Process Enforcement** - VBA WhosLoggedIn table prevents concurrent runs
   - Modern system supports parallel processing (may or may not need single-process constraint)

#### Architectural Comparison:

| Feature | VBA | Modern | Winner |
|---------|-----|--------|--------|
| Pattern Matching | Exact sequential | Fuzzy bbox | Modern |
| Data Extraction | Line/char positions | Bbox coordinates | Modern |
| Configuration | Hard-coded in VBA | Database + UI | Modern |
| Scalability | Single-thread, max 1000 | Parallel, unlimited | Modern |
| Extensibility | Requires coding | Add modules | Modern |
| Format Support | 14 pre-built | 0 pre-built | VBA (temporary) |

### Recommendations

**Immediate Actions**:
1. Create modern templates for 14 VBA document formats using template builder
2. Implement multi-delivery alert expansion as pipeline module
3. Add retention policy scheduled job
4. Document migration path for each VBA format

**Migration Strategy**:
- Side-by-side testing (run both systems in parallel)
- Gradual rollout (migrate one format at a time)
- Comprehensive test suite with sample production PDFs
- One-time template creation effort, then modern system is superior

### Next Actions
- Begin creating templates for VBA formats (start with most common: SOS Routing, SOS BOL, SOS Alert)
- Implement custom pipeline modules for VBA-specific logic (alert expansion)
- Add retention/archival scheduled jobs
- Build test suite with sample PDFs from each format

### Notes
- Migration is feasible - modern system has equivalent or superior capabilities
- Key risk: Ensuring 14 VBA formats are correctly translated to templates
- Comprehensive comparison document ready for stakeholder review
- Modern system architecture is significantly more maintainable and scalable

---

## [2025-11-10 19:30] — Template Version Editing & VBA Migration Setup
### Spec / Intent
- Fix config editability in view mode for pipeline viewer
- Fix connection validation for initialized modules in template builder
- Preserve current step when switching template versions
- Set up VBA migration infrastructure and documentation

### Changes Made
- Files Modified:
  - `client/src/renderer/features/pipelines/components/PipelineGraph/ConfigSection.tsx`
  - `client/src/renderer/features/pipelines/components/PipelineGraph/ModuleConfig.tsx`
  - `client/src/renderer/features/pipelines/components/PipelineGraph/PipelineGraph.tsx`
  - `client/src/renderer/features/templates/components/TemplateDetail/TemplateDetailModal.tsx`

- Files Created:
  - `context/docs/CLAUDE_CODE_SLASH_COMMANDS.md` - Comprehensive guide to slash commands for VBA analysis
  - `vba-code/HTC_350C_Sub_1_of_2_translation.vba` - Original VBA code for migration
  - `vba-code/HTC_350C_Sub_2_of_2_createorders.vba` - Original VBA code for migration

### Summary of Fixes

#### 1. Config Editability in View Mode (commit: 6259021)
**Problem**: Config inputs were editable in view mode because ModuleConfig always passed a wrapper function to ConfigSection.
**Solution**: Made onConfigChange optional in ConfigSectionProps, conditionally pass undefined in view mode.

#### 2. Connection Validation for Initialized Modules (commit: 56a0703)
**Problem**: Connection validation used raw pipelineState lacking enriched metadata (allowed_types, direction, label, type_var), causing validation failures.
**Solution**: Updated all validation and type system operations to use enrichedPipelineState:
- `isValidConnection`: Uses enriched state for correct allowed_types
- `onConnect`: Validates with enriched state, persists to raw state
- `handleUpdateNode`: Calculates propagation with enriched state
- `effectiveTypesCache`: Computed from enriched state
Pattern: Read from enriched (for metadata), write to raw (for persistence).

#### 3. Template Version Step Preservation (commit: 6e5db09)
**Problem**: Switching template versions reset to signature-objects step, disrupting workflow.
**Solution**: Removed step reset from handleVersionChange to preserve current view.

### Next Actions
- Create `.claude/commands/` directory with VBA analysis slash commands
- Run `/vba-inventory` to analyze VBA codebase structure
- Begin systematic VBA to Python/TypeScript migration
- Define new pipeline module definitions for database writing

### Notes
- VBA migration is full rewrite of previous MS Access/VBA system
- VBA code stored in `vba-code/` directory for analysis
- Slash commands documented in `context/docs/CLAUDE_CODE_SLASH_COMMANDS.md`
- All recent commits ready to push to remote
